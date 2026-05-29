"""
Task models: StudentTask (personal), AcademicTask (teacher-assigned).
"""
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


# ---------------------------------------------------------------------------
# Student Task (Personal / Self-Created)
# ---------------------------------------------------------------------------
class StudentTask(BaseModel):
    """
    Personal tasks created by students for themselves.
    Private to the student — visible only to the student.
    Examples: Revision tasks, study goals, personal reminders.
    """
    __tablename__ = "student_tasks"
    __table_args__ = {"schema": "academic", "comment": "Student personal tasks (self-created, private)"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)

    # Optional subject linkage
    subject_id = Column(UUID(as_uuid=True), ForeignKey("academic.subjects.id", ondelete="SET NULL"), nullable=True)

    # Task Details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(10), default="MEDIUM", comment="LOW | MEDIUM | HIGH | URGENT")

    # Dates
    due_date = Column(Date, nullable=True)
    reminder_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(String(20), default="PENDING", comment="PENDING | IN_PROGRESS | COMPLETED | CANCELLED")
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completion_notes = Column(Text, nullable=True)

    # Sort
    display_order = Column(Integer, default=0)

    extra_metadata = Column(JSONB, default={})

    # Relationships
    student = relationship("AcademicProfile", back_populates="student_tasks")

    def __repr__(self):
        return f"<StudentTask(student_id={self.student_id}, title={self.title}, status={self.status})>"


# ---------------------------------------------------------------------------
# Academic Task (Teacher-Created)
# ---------------------------------------------------------------------------
class AcademicTask(BaseModel):
    """
    Tasks created by teachers/HOD assigned to students or the teacher themselves.
    Different from homework — these are operational/academic management tasks.
    Examples: Project tasks, research assignments, academic planning tasks.
    """
    __tablename__ = "academic_tasks"
    __table_args__ = {"schema": "academic", "comment": "Teacher-assigned academic tasks and department tasks"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Context
    class_id = Column(UUID(as_uuid=True), ForeignKey("academic.classes.id", ondelete="SET NULL"), nullable=True)
    section_id = Column(UUID(as_uuid=True), ForeignKey("academic.sections.id", ondelete="SET NULL"), nullable=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("academic.subjects.id", ondelete="SET NULL"), nullable=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)

    # Created by (teacher/HOD user_id)
    created_by_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_by_role = Column(String(30), nullable=False, comment="TEACHER | HOD | PRINCIPAL | CLASS_TEACHER")

    # Task Details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(30), nullable=False, comment="ACADEMIC | DEPARTMENT | CLASS | STUDENT | ADMINISTRATIVE")
    priority = Column(String(10), default="MEDIUM", comment="LOW | MEDIUM | HIGH | URGENT")

    # Dates
    due_date = Column(Date, nullable=True)

    # Assignment scope
    assigned_to_scope = Column(String(20), default="TEACHER", comment="TEACHER | CLASS | SECTION | STUDENT | DEPARTMENT")
    assigned_user_ids = Column(JSONB, default=[], comment="Array of assigned user_ids (for individual assignments)")

    # Status
    status = Column(String(20), default="PENDING", comment="PENDING | IN_PROGRESS | COMPLETED | CANCELLED | OVERDUE")
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completion_notes = Column(Text, nullable=True)

    extra_metadata = Column(JSONB, default={})

    def __repr__(self):
        return f"<AcademicTask(title={self.title}, type={self.task_type}, status={self.status})>"
