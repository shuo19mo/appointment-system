"""SQLAlchemy models for the education scheduling domain."""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.types import TypeDecorator


Base = declarative_base()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Persist one instant consistently, including on SQLite.

    SQLite discards offsets from ``DateTime(timezone=True)``. This type converts
    every input to UTC, stores naive UTC only on SQLite, and always restores an
    aware UTC value. API serializers are responsible for business-time display.
    """

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(DateTime(timezone=dialect.name != "sqlite"))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime must include a timezone")
        normalized = value.astimezone(timezone.utc)
        return normalized.replace(tzinfo=None) if dialect.name == "sqlite" else normalized

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Campus(Base):
    __tablename__ = "campuses"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    address = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    bio = Column(Text, nullable=False, default="")
    specialties = Column(Text, nullable=False, default="")
    max_daily_minutes = Column(Integer, nullable=False, default=360)
    is_active = Column(Boolean, nullable=False, default=True)
    courses = relationship("TeacherCourse", cascade="all, delete-orphan")
    campuses = relationship("TeacherCampus", cascade="all, delete-orphan")
    availability = relationship("TeacherAvailability", cascade="all, delete-orphan")


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False)
    subject = Column(String(50), nullable=False, index=True)
    grade = Column(String(50), nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=False, default=90)
    description = Column(Text, nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)


class TeacherCourse(Base):
    __tablename__ = "teacher_courses"
    __table_args__ = (UniqueConstraint("teacher_id", "course_id"),)
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)


class TeacherCampus(Base):
    __tablename__ = "teacher_campuses"
    __table_args__ = (UniqueConstraint("teacher_id", "campus_id"),)
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    campus_id = Column(Integer, ForeignKey("campuses.id"), nullable=False, index=True)


class TeacherAvailability(Base):
    __tablename__ = "teacher_availability"
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    start_at = Column(UTCDateTime(), nullable=False, index=True)
    end_at = Column(UTCDateTime(), nullable=False, index=True)


class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    grade = Column(String(50), nullable=False)
    contact = Column(String(100), nullable=False, default="")
    preferred_teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class ClassBooking(Base):
    __tablename__ = "class_bookings"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    campus_id = Column(Integer, ForeignKey("campuses.id"), nullable=False, index=True)
    start_at = Column(UTCDateTime(), nullable=False, index=True)
    end_at = Column(UTCDateTime(), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="confirmed", index=True)
    notes = Column(Text, nullable=False, default="")
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)
    student = relationship("Student")
    teacher = relationship("Teacher")
    course = relationship("Course")
    campus = relationship("Campus")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    keywords = Column(JSON, nullable=False, default=list)
    embedding = Column(JSON, nullable=True)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)
    updated_at = Column(UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now)
    is_active = Column(Boolean, nullable=False, default=True)


class StudentBehavior(Base):
    __tablename__ = "student_behaviors"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)
    action_type = Column(String(50), nullable=False)
    action_data = Column(JSON, nullable=False, default=dict)
    session_id = Column(String(100), nullable=True, index=True)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)


class StudentPreference(Base):
    __tablename__ = "student_preferences"
    __table_args__ = (UniqueConstraint("student_id", "preference_type"),)
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    preference_type = Column(String(50), nullable=False)
    preference_value = Column(String(255), nullable=False)
    confidence_score = Column(Integer, nullable=False, default=1)
    updated_at = Column(UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now)
