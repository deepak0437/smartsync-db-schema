"""
Homework models: Homework, HomeworkSubmission, HomeworkAttachment.
"""
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


# ---------------------------------------------------------------------------
# Homework
# ---------------------------------------------------------------------------
class Homework(BaseModel):
    """
    Homework/assignment created by teachers.

    Assignment scope can be:
    - CLASS level (all students in a class)
    - SECTION level (specific section)
    - INDIVIDUAL level (specific student)

    Rules:
    - Due date must be future at time of creation
    - Only assigned teacher can create for their subject
    - Cannot modify after due date (closed automatically)
    - Late submissions auto-flagged
    """
    __tablename__ = "homework"
    __table_args__ = {"schema": "academic", "comment": "Homework/assignments created by teachers"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Assignment context
    class_id = Column(UUID(as_uuid=True), ForeignKey("academic.classes.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(UUID(as_uuid=True), ForeignKey("academic.sections.id", ondelete="SET NULL"), nullable=True, index=True, comment="Null = all sections in class")
    subject_id = Column(UUID(as_uuid=True), ForeignKey("academic.subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)

    # Teacher who created
    created_by_teacher_user_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="Subject teacher who created this homework")

    # Homework Details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)

    # Assignment Scope
    assignment_scope = Column(String(20), default="SECTION", comment="CLASS | SECTION | INDIVIDUAL")

    # Dates
    assigned_date = Column(Date, nullable=False, comment="Date homework was assigned")
    due_date = Column(Date, nullable=False, index=True, comment="Submission deadline")

    # Submission
    max_marks = Column(Integer, nullable=True, comment="Maximum marks (null = no grading)")
    allow_late_submission = Column(Boolean, default=False)
    late_submission_penalty = Column(Integer, default=0, comment="Marks deducted for late submission")

    # Status
    status = Column(String(20), default="ACTIVE", comment="ACTIVE | CLOSED | CANCELLED | DRAFT")
    closed_at = Column(DateTime(timezone=True), nullable=True)

    extra_metadata = Column(JSONB, default={})

    # Relationships
    submissions = relationship("HomeworkSubmission", back_populates="homework")
    attachments = relationship("HomeworkAttachment", back_populates="homework")
    student_assignments = relationship("HomeworkStudentAssignment", back_populates="homework")

    def __repr__(self):
        return f"<Homework(title={self.title}, due={self.due_date})>"


# ---------------------------------------------------------------------------
# Homework Student Assignment (individual-level scope)
# ---------------------------------------------------------------------------
class HomeworkStudentAssignment(BaseModel):
    """
    Maps specific students to homework when scope = INDIVIDUAL.
    Also used to track which students have been assigned class/section-level homework.
    """
    __tablename__ = "homework_student_assignments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "homework_id", "student_id", name="uq_academic_homework_student"),
        {"schema": "academic", "comment": "Student-level homework assignment tracking"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    homework_id = Column(UUID(as_uuid=True), ForeignKey("academic.homework.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    homework = relationship("Homework", back_populates="student_assignments")

    def __repr__(self):
        return f"<HomeworkStudentAssignment(homework_id={self.homework_id}, student_id={self.student_id})>"


# ---------------------------------------------------------------------------
# Homework Submission
# ---------------------------------------------------------------------------
class HomeworkSubmission(BaseModel):
    """
    Student submission for a homework assignment.

    Tracks:
    - Submission status (PENDING, SUBMITTED, LATE_SUBMITTED, GRADED)
    - Marks awarded
    - Teacher feedback
    - Late submission flag
    """
    __tablename__ = "homework_submissions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "homework_id", "student_id", name="uq_academic_homework_submission"),
        {"schema": "academic", "comment": "Student homework submissions and grading"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    homework_id = Column(UUID(as_uuid=True), ForeignKey("academic.homework.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    # Submission
    status = Column(String(20), default="PENDING", comment="PENDING | SUBMITTED | LATE_SUBMITTED | GRADED | EXCUSED | MISSED")
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    is_late = Column(Boolean, default=False, nullable=False)
    late_by_days = Column(Integer, default=0)

    # Student work
    submission_text = Column(Text, nullable=True)
    submission_notes = Column(Text, nullable=True)

    # Grading
    marks_obtained = Column(Integer, nullable=True)
    grade = Column(String(5), nullable=True, comment="Letter grade if applicable")
    teacher_feedback = Column(Text, nullable=True)
    graded_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    graded_at = Column(DateTime(timezone=True), nullable=True)

    extra_metadata = Column(JSONB, default={})

    # Relationships
    homework = relationship("Homework", back_populates="submissions")
    student = relationship("AcademicProfile", back_populates="homework_submissions")
    attachments = relationship("HomeworkAttachment", back_populates="submission")

    def __repr__(self):
        return f"<HomeworkSubmission(homework_id={self.homework_id}, student_id={self.student_id}, status={self.status})>"


# ---------------------------------------------------------------------------
# Homework Attachment
# ---------------------------------------------------------------------------
class HomeworkAttachment(BaseModel):
    """
    File attachments for homework questions or student submissions.
    Actual files stored in media-service; this stores references.
    """
    __tablename__ = "homework_attachments"
    __table_args__ = {"schema": "academic", "comment": "File attachments for homework and submissions"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    homework_id = Column(UUID(as_uuid=True), ForeignKey("academic.homework.id", ondelete="CASCADE"), nullable=True, index=True, comment="Null if attached to submission")
    submission_id = Column(UUID(as_uuid=True), ForeignKey("academic.homework_submissions.id", ondelete="CASCADE"), nullable=True, index=True, comment="Null if attached to homework question")

    # File reference (from media-service)
    media_file_id = Column(UUID(as_uuid=True), nullable=True, comment="media-service file UUID")
    file_name = Column(String(500), nullable=False)
    file_type = Column(String(100), nullable=True, comment="MIME type")
    file_size_bytes = Column(Integer, nullable=True)
    file_url = Column(Text, nullable=False, comment="CDN URL for the file")

    # Attachment type
    attachment_type = Column(String(20), default="QUESTION", comment="QUESTION | ANSWER | REFERENCE")

    uploaded_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    homework = relationship("Homework", back_populates="attachments")
    submission = relationship("HomeworkSubmission", back_populates="attachments")

    def __repr__(self):
        return f"<HomeworkAttachment(file={self.file_name})>"
