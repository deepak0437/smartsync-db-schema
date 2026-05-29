"""
Reviews and Remarks models: StudentReview, StudentRemark, ReviewAcknowledgment.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


# ---------------------------------------------------------------------------
# Student Review
# ---------------------------------------------------------------------------
class StudentReview(BaseModel):
    """
    Holistic teacher assessment/review of a student.

    Rules:
    - Class Teacher can write overall student reviews
    - Subject Teacher can write subject-specific reviews
    - Parent must acknowledge review within 7 days
    - Cannot delete after parent acknowledgment
    - Negative reviews require HOD approval before publishing
    """
    __tablename__ = "student_reviews"
    __table_args__ = {"schema": "academic", "comment": "Teacher periodic assessments of students"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)

    # Optional subject scope (null = overall student review)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("academic.subjects.id", ondelete="SET NULL"), nullable=True, index=True)

    # Author
    reviewer_user_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="Teacher who wrote this review")
    reviewer_role = Column(String(30), nullable=False, comment="CLASS_TEACHER | SUBJECT_TEACHER | HOD")

    # Review Content
    review_type = Column(String(30), nullable=False, comment="ACADEMIC | BEHAVIORAL | OVERALL | SUBJECT_SPECIFIC | PERIODIC")
    period = Column(String(30), nullable=True, comment="MONTHLY | QUARTERLY | SEMESTER | ANNUAL | WEEKLY")
    title = Column(String(500), nullable=True)
    review_text = Column(Text, nullable=False)

    # Ratings (optional 1-5 scale)
    academic_rating = Column(Integer, nullable=True, comment="1–5 rating for academic performance")
    behavior_rating = Column(Integer, nullable=True, comment="1–5 rating for behavior")
    overall_rating = Column(Integer, nullable=True, comment="1–5 overall rating")

    # Sentiment
    sentiment = Column(String(20), nullable=True, comment="POSITIVE | NEUTRAL | NEGATIVE")

    # Visibility
    is_visible_to_student = Column(Boolean, default=True)
    is_visible_to_parent = Column(Boolean, default=True)

    # HOD Approval (for negative reviews)
    requires_hod_approval = Column(Boolean, default=False)
    hod_approved = Column(Boolean, default=False)
    hod_approved_by = Column(UUID(as_uuid=True), nullable=True)
    hod_approved_at = Column(DateTime(timezone=True), nullable=True)
    hod_approval_notes = Column(Text, nullable=True)

    # Status
    status = Column(String(20), default="DRAFT", comment="DRAFT | PUBLISHED | ARCHIVED")
    published_at = Column(DateTime(timezone=True), nullable=True)

    extra_metadata = Column(JSONB, default={})

    # Relationships
    student = relationship("AcademicProfile", back_populates="student_reviews")
    acknowledgments = relationship("ReviewAcknowledgment", back_populates="review")

    def __repr__(self):
        return f"<StudentReview(student_id={self.student_id}, type={self.review_type})>"


# ---------------------------------------------------------------------------
# Student Remark
# ---------------------------------------------------------------------------
class StudentRemark(BaseModel):
    """
    Short teacher remarks/comments on a student (day-to-day observations).
    More granular than a review — quick notes for parents and records.

    Rules:
    - Any assigned teacher can write remarks
    - Subject teachers write subject-specific remarks
    - Class teachers write general remarks
    - HOD can write remarks on any student in their department
    """
    __tablename__ = "student_remarks"
    __table_args__ = {"schema": "academic", "comment": "Short teacher remarks/observations on students"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)

    # Optional subject context
    subject_id = Column(UUID(as_uuid=True), ForeignKey("academic.subjects.id", ondelete="SET NULL"), nullable=True, index=True)

    # Author
    remarked_by_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    remarked_by_role = Column(String(30), nullable=False, comment="CLASS_TEACHER | SUBJECT_TEACHER | HOD | PRINCIPAL")

    # Remark
    remark_type = Column(String(30), nullable=False, comment="ACADEMIC | BEHAVIORAL | ATTENDANCE | GENERAL | POSITIVE | CONCERN")
    remark_text = Column(Text, nullable=False)

    # Visibility
    is_visible_to_parent = Column(Boolean, default=True)
    is_visible_to_student = Column(Boolean, default=False, comment="Typically hidden from students")

    # Parent Acknowledgment
    is_acknowledged_by_parent = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by_user_id = Column(UUID(as_uuid=True), nullable=True)

    extra_metadata = Column(JSONB, default={})

    # Relationships
    student = relationship("AcademicProfile", back_populates="student_remarks")

    def __repr__(self):
        return f"<StudentRemark(student_id={self.student_id}, type={self.remark_type})>"


# ---------------------------------------------------------------------------
# Review Acknowledgment (Parent)
# ---------------------------------------------------------------------------
class ReviewAcknowledgment(BaseModel):
    """
    Parent acknowledgment of a student review.
    Parents must acknowledge reviews within 7 days.
    Supports parent response/comments back to teacher.
    """
    __tablename__ = "review_acknowledgments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "review_id", "parent_user_id", name="uq_academic_review_acknowledgment"),
        {"schema": "academic", "comment": "Parent acknowledgment of teacher reviews"},
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    review_id = Column(UUID(as_uuid=True), ForeignKey("academic.student_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_user_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="Parent who acknowledged")

    # Acknowledgment
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    # Parent Response
    parent_response = Column(Text, nullable=True, comment="Optional parent comments/response to teacher")
    parent_agrees = Column(Boolean, nullable=True, comment="Parent agrees/disagrees with review")

    extra_metadata = Column(JSONB, default={})

    # Relationships
    review = relationship("StudentReview", back_populates="acknowledgments")

    def __repr__(self):
        return f"<ReviewAcknowledgment(review_id={self.review_id}, parent_id={self.parent_user_id})>"
