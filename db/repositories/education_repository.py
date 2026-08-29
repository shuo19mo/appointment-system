"""Transaction-oriented repository for education scheduling data."""

from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import joinedload

from db.models import Campus, ClassBooking, Course, KnowledgeDocument, Student, Teacher, TeacherAvailability, TeacherCampus, TeacherCourse


ACTIVE_BOOKING_STATUSES = ("confirmed", "pending")


class EducationRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    @contextmanager
    def transaction(self, *, immediate: bool = False):
        session = self.session_factory()
        try:
            if immediate and session.get_bind().dialect.name == "sqlite":
                session.execute(text("BEGIN IMMEDIATE"))
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _create(self, model):
        with self.transaction() as session:
            session.add(model)
            session.flush()
            session.refresh(model)
            return model

    def create_campus(self, name: str, address: str) -> Campus:
        return self._create(Campus(name=name, address=address))

    def create_course(self, name: str, subject: str, grade: str, duration_minutes: int = 90, description: str = "") -> Course:
        return self._create(Course(name=name, subject=subject, grade=grade, duration_minutes=duration_minutes, description=description))

    def create_student(self, name: str, grade: str, contact: str = "") -> Student:
        return self._create(Student(name=name, grade=grade, contact=contact))

    def create_teacher(self, name: str, bio: str = "", specialties: str = "") -> Teacher:
        return self._create(Teacher(name=name, bio=bio, specialties=specialties))

    def qualify_teacher(self, teacher_id: int, course_id: int) -> TeacherCourse:
        return self._create(TeacherCourse(teacher_id=teacher_id, course_id=course_id))

    def assign_teacher_to_campus(self, teacher_id: int, campus_id: int) -> TeacherCampus:
        return self._create(TeacherCampus(teacher_id=teacher_id, campus_id=campus_id))

    def add_teacher_availability(self, teacher_id: int, start_at: datetime, end_at: datetime) -> TeacherAvailability:
        if end_at <= start_at:
            raise ValueError("教师可用结束时间必须晚于开始时间")
        return self._create(TeacherAvailability(teacher_id=teacher_id, start_at=start_at, end_at=end_at))

    def create_booking(self, *, student_id: int, teacher_id: int, course_id: int, campus_id: int, start_at: datetime, end_at: datetime, status: str = "confirmed", notes: str = "") -> ClassBooking:
        return self._create(ClassBooking(student_id=student_id, teacher_id=teacher_id, course_id=course_id, campus_id=campus_id, start_at=start_at, end_at=end_at, status=status, notes=notes))

    def create_booking_checked(self, **values) -> ClassBooking:
        if values.get("student_id") is None:
            raise ValueError("创建课程安排必须指定学生")
        try:
            with self.transaction(immediate=True) as session:
                if session.get_bind().dialect.name != "sqlite":
                    session.query(Teacher).filter(Teacher.id == values["teacher_id"]).with_for_update().one()
                    session.query(Student).filter(Student.id == values["student_id"]).with_for_update().one()
                if self._conflict_query(session, teacher_id=values["teacher_id"], start_at=values["start_at"], end_at=values["end_at"]).first():
                    raise RepositoryConflict("teacher")
                if self._conflict_query(session, student_id=values["student_id"], start_at=values["start_at"], end_at=values["end_at"]).first():
                    raise RepositoryConflict("student")
                booking = ClassBooking(**values)
                session.add(booking)
                session.flush()
                session.refresh(booking)
                return booking
        except OperationalError as exc:
            if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                raise RepositoryConflict("database_busy") from exc
            raise

    @staticmethod
    def _conflict_query(session, *, start_at, end_at, teacher_id=None, student_id=None):
        query = session.query(ClassBooking).filter(ClassBooking.status.in_(ACTIVE_BOOKING_STATUSES), ClassBooking.start_at < end_at, ClassBooking.end_at > start_at)
        if teacher_id is not None:
            query = query.filter(ClassBooking.teacher_id == teacher_id)
        if student_id is not None:
            query = query.filter(ClassBooking.student_id == student_id)
        return query

    def has_teacher_conflict(self, teacher_id: int, start_at: datetime, end_at: datetime) -> bool:
        with self.transaction() as session:
            return self._conflict_query(session, teacher_id=teacher_id, start_at=start_at, end_at=end_at).first() is not None

    def has_student_conflict(self, student_id: int, start_at: datetime, end_at: datetime) -> bool:
        with self.transaction() as session:
            return self._conflict_query(session, student_id=student_id, start_at=start_at, end_at=end_at).first() is not None

    def eligible_teachers(self, course_id: int, campus_id: int, start_at: datetime, end_at: datetime) -> list[Teacher]:
        with self.transaction() as session:
            teachers = session.query(Teacher).join(TeacherCourse, TeacherCourse.teacher_id == Teacher.id).join(TeacherCampus, TeacherCampus.teacher_id == Teacher.id).join(TeacherAvailability, TeacherAvailability.teacher_id == Teacher.id).filter(Teacher.is_active.is_(True), TeacherCourse.course_id == course_id, TeacherCampus.campus_id == campus_id, TeacherAvailability.start_at <= start_at, TeacherAvailability.end_at >= end_at).distinct().all()
            return [teacher for teacher in teachers if not self._conflict_query(session, teacher_id=teacher.id, start_at=start_at, end_at=end_at).first()]

    def teacher_daily_minutes(self, teacher_id: int, start_at: datetime) -> int:
        day_start = start_at.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = start_at.replace(hour=23, minute=59, second=59, microsecond=999999)
        with self.transaction() as session:
            bookings = session.query(ClassBooking).filter(ClassBooking.teacher_id == teacher_id, ClassBooking.status.in_(ACTIVE_BOOKING_STATUSES), ClassBooking.start_at >= day_start, ClassBooking.start_at <= day_end).all()
            return int(sum((item.end_at - item.start_at).total_seconds() / 60 for item in bookings))

    def get_teacher(self, teacher_id: int):
        with self.transaction() as session:
            return session.get(Teacher, teacher_id)

    def get_course(self, course_id: int):
        with self.transaction() as session:
            return session.get(Course, course_id)

    def get_campus(self, campus_id: int):
        with self.transaction() as session:
            return session.get(Campus, campus_id)

    def get_student(self, student_id: int):
        with self.transaction() as session:
            return session.get(Student, student_id)

    def find_student(self, name: str):
        with self.transaction() as session:
            return session.query(Student).filter(Student.name == name, Student.is_active.is_(True)).first()

    def find_campus(self, name: str):
        with self.transaction() as session:
            return session.query(Campus).filter(Campus.name == name, Campus.is_active.is_(True)).first()

    def find_course(self, subject: str, grade: str):
        with self.transaction() as session:
            return session.query(Course).filter(Course.subject == subject, Course.grade == grade, Course.is_active.is_(True)).first()

    def find_teacher(self, name: str):
        with self.transaction() as session:
            return session.query(Teacher).filter(Teacher.name == name, Teacher.is_active.is_(True)).first()

    def set_student_preferred_teacher(self, student_id: int, teacher_id: int):
        with self.transaction() as session:
            student = session.get(Student, student_id)
            if student is None:
                return None
            student.preferred_teacher_id = teacher_id
            session.flush()
            session.refresh(student)
            return student

    def update_campus(self, campus_id: int, **values):
        return self._update(Campus, campus_id, values)

    def update_course(self, course_id: int, **values):
        return self._update(Course, course_id, values)

    def update_teacher(self, teacher_id: int, **values):
        return self._update(Teacher, teacher_id, values)

    def update_student(self, student_id: int, **values):
        return self._update(Student, student_id, values)

    def _update(self, model, item_id: int, values: dict):
        with self.transaction() as session:
            item = session.get(model, item_id)
            if item is None:
                return None
            for key, value in values.items():
                if value is not None and hasattr(item, key):
                    setattr(item, key, value)
            session.flush()
            session.refresh(item)
            return item

    def deactivate_campus(self, campus_id: int):
        return self._update(Campus, campus_id, {"is_active": False})

    def deactivate_course(self, course_id: int):
        return self._update(Course, course_id, {"is_active": False})

    def deactivate_teacher(self, teacher_id: int):
        return self._update(Teacher, teacher_id, {"is_active": False})

    def deactivate_student(self, student_id: int):
        return self._update(Student, student_id, {"is_active": False})

    def remove_teacher_course(self, teacher_id: int, course_id: int) -> bool:
        return self._delete_where(TeacherCourse, teacher_id=teacher_id, course_id=course_id)

    def remove_teacher_campus(self, teacher_id: int, campus_id: int) -> bool:
        return self._delete_where(TeacherCampus, teacher_id=teacher_id, campus_id=campus_id)

    def remove_teacher_availability(self, teacher_id: int, availability_id: int) -> bool:
        return self._delete_where(TeacherAvailability, id=availability_id, teacher_id=teacher_id)

    def _delete_where(self, model, **filters) -> bool:
        with self.transaction() as session:
            item = session.query(model).filter_by(**filters).first()
            if item is None:
                return False
            session.delete(item)
            return True

    def list_campuses(self):
        with self.transaction() as session:
            return session.query(Campus).filter(Campus.is_active.is_(True)).order_by(Campus.id).all()

    def list_courses(self):
        with self.transaction() as session:
            return session.query(Course).filter(Course.is_active.is_(True)).order_by(Course.id).all()

    def list_teachers(self):
        with self.transaction() as session:
            return session.query(Teacher).filter(Teacher.is_active.is_(True)).order_by(Teacher.id).all()

    def list_teachers_for_course(self, subject: str, grade: str, campus_name: str | None = None):
        with self.transaction() as session:
            query = (
                session.query(Teacher)
                .join(TeacherCourse, TeacherCourse.teacher_id == Teacher.id)
                .join(Course, Course.id == TeacherCourse.course_id)
                .filter(
                    Teacher.is_active.is_(True),
                    Course.is_active.is_(True),
                    Course.subject == subject,
                    Course.grade == grade,
                )
            )
            if campus_name:
                query = (
                    query.join(TeacherCampus, TeacherCampus.teacher_id == Teacher.id)
                    .join(Campus, Campus.id == TeacherCampus.campus_id)
                    .filter(Campus.is_active.is_(True), Campus.name == campus_name)
                )
            return query.distinct().order_by(Teacher.id).all()

    def list_students(self):
        with self.transaction() as session:
            return session.query(Student).filter(Student.is_active.is_(True)).order_by(Student.id).all()

    def list_teacher_availability(self, teacher_id: int):
        with self.transaction() as session:
            return session.query(TeacherAvailability).filter(TeacherAvailability.teacher_id == teacher_id).order_by(TeacherAvailability.start_at).all()

    def list_bookings(self, *, student_id: int | None = None, teacher_id: int | None = None):
        with self.transaction() as session:
            query = session.query(ClassBooking).options(joinedload(ClassBooking.student), joinedload(ClassBooking.teacher), joinedload(ClassBooking.course), joinedload(ClassBooking.campus))
            if student_id is not None:
                query = query.filter(ClassBooking.student_id == student_id)
            if teacher_id is not None:
                query = query.filter(ClassBooking.teacher_id == teacher_id)
            return query.order_by(ClassBooking.start_at).all()

    def cancel_booking(self, booking_id: int):
        with self.transaction() as session:
            booking = session.get(ClassBooking, booking_id)
            if booking is None:
                return None
            booking.status = "cancelled"
            session.flush()
            session.refresh(booking)
            return booking

    def add_knowledge(self, content: str, category: str, keywords: list[str] | None = None):
        return self._create(KnowledgeDocument(content=content, category=category, keywords=keywords or []))

    def list_knowledge(self, category: str | None = None, limit: int = 100):
        with self.transaction() as session:
            query = session.query(KnowledgeDocument).filter(KnowledgeDocument.is_active.is_(True))
            if category:
                query = query.filter(KnowledgeDocument.category == category)
            return query.order_by(KnowledgeDocument.id).limit(limit).all()

    def search_knowledge(self, query: str, category: str | None = None, limit: int = 5):
        with self.transaction() as session:
            db_query = session.query(KnowledgeDocument).filter(KnowledgeDocument.is_active.is_(True))
            if category:
                db_query = db_query.filter(KnowledgeDocument.category == category)
            documents = db_query.all()
        def score(document):
            return sum(5 for keyword in document.keywords or [] if keyword in query) + len(set(query) & set(document.content))
        ranked = sorted(documents, key=lambda item: (-score(item), item.id))
        return [item for item in ranked if score(item) > 0][:limit]


class RepositoryConflict(RuntimeError):
    def __init__(self, resource: str):
        self.resource = resource
        super().__init__(resource)
