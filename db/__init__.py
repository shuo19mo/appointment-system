"""Education scheduling database package."""

from db.db_router import DatabaseRouter
from db.models import Base, Campus, ClassBooking, Course, KnowledgeDocument, Student, StudentBehavior, StudentPreference, Teacher, TeacherAvailability, TeacherCampus, TeacherCourse
from db.repositories.education_repository import EducationRepository

__all__ = ["Base", "Campus", "ClassBooking", "Course", "DatabaseRouter", "EducationRepository", "KnowledgeDocument", "Student", "StudentBehavior", "StudentPreference", "Teacher", "TeacherAvailability", "TeacherCampus", "TeacherCourse"]
