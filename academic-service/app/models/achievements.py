"""
Achievement models: AchievementType, Achievement, AchievementEvidence.
"""
from sqlalchemy import Boolean, Column, Date, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


# ---------------------------------------------------------------------------
# Achievement Type
# ---------------------------------------------------------------------------
class AchievementType(BaseModel):
    """
    Lookup table for achievement/award categories.
    Examples: ACADEMIC_EXCELLENCE, SPORTS, ARTS, SCIENCE_OLYMPIAD, LEADERSHIP, COMMUNITY
    """
    __tablename__ = "achievement_types"
    __table_args__ = {"schema": "academic", "comment": "Achievement category definitions"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    type_code = Column(String(50), nullable=False, index=True)
    type_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, comment="ACADEMIC | SPORTS | ARTS | CULTURAL | LEADERSHIP | COMMUNITY | SCIENCE | OTHER")
    icon_url = Column(Text, nullable=True, comment="Icon for UI display")
    color_code = Column(String(10), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    achievements = relationship("Achievement", back_populates="achievement_type")

    def __repr__(self):
        return f"<AchievementType(code={self.type_code})>"


# ---------------------------------------------------------------------------
# Achievement
# ---------------------------------------------------------------------------
class Achievement(BaseModel):
    """
    Student achievement or award record.

    Rules:
    - Award date cannot be future
    - Must have valid achievement type
    - Evidence/proof can be attached
    - Visible to student, parent, and academic staff
    """
    __tablename__ = "achievements"
    __table_args__ = {"schema": "academic", "comment": "Student achievement and award records"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)
    achievement_type_id = Column(UUID(as_uuid=True), ForeignKey("academic.achievement_types.id", ondelete="SET NULL"), nullable=True, index=True)

    # Achievement Details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    achievement_date = Column(Date, nullable=False, index=True, comment="Date of achievement (cannot be future)")

    # Level / Scope
    achievement_level = Column(String(30), nullable=True, comment="CLASS | SCHOOL | DISTRICT | STATE | NATIONAL | INTERNATIONAL")
    position = Column(String(20), nullable=True, comment="1ST | 2ND | 3RD | MERIT | PARTICIPATION")
    award_name = Column(String(500), nullable=True, comment="Official award name")
    awarding_body = Column(String(255), nullable=True, comment="Organization that gave the award")

    # Certificate/Evidence
    certificate_url = Column(Text, nullable=True, comment="Certificate/proof CDN URL")

    # Recorded by
    recorded_by_user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    recorded_by_role = Column(String(30), nullable=True)

    # Subject association (optional)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("academic.subjects.id", ondelete="SET NULL"), nullable=True)

    # Visibility
    is_visible_to_student = Column(Boolean, default=True)
    is_visible_to_parent = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False, comment="Featured on school notice board / dashboard")

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    student = relationship("AcademicProfile", back_populates="achievements")
    achievement_type = relationship("AchievementType", back_populates="achievements")
    evidence_items = relationship("AchievementEvidence", back_populates="achievement")

    def __repr__(self):
        return f"<Achievement(student_id={self.student_id}, title={self.title})>"


# ---------------------------------------------------------------------------
# Achievement Evidence
# ---------------------------------------------------------------------------
class AchievementEvidence(BaseModel):
    """
    Supporting evidence files for achievements (photos, certificates, news articles).
    References media-service for actual file storage.
    """
    __tablename__ = "achievement_evidence"
    __table_args__ = {"schema": "academic", "comment": "Supporting evidence for student achievements"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    achievement_id = Column(UUID(as_uuid=True), ForeignKey("academic.achievements.id", ondelete="CASCADE"), nullable=False, index=True)

    # File reference (media-service)
    media_file_id = Column(UUID(as_uuid=True), nullable=True, comment="media-service file UUID")
    file_name = Column(String(500), nullable=False)
    file_type = Column(String(100), nullable=True)
    file_url = Column(Text, nullable=False)
    file_size_bytes = Column(String(20), nullable=True)

    evidence_type = Column(String(30), default="CERTIFICATE", comment="CERTIFICATE | PHOTO | VIDEO | NEWS_ARTICLE | LETTER")
    description = Column(Text, nullable=True)

    uploaded_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    achievement = relationship("Achievement", back_populates="evidence_items")

    def __repr__(self):
        return f"<AchievementEvidence(achievement_id={self.achievement_id}, type={self.evidence_type})>"
