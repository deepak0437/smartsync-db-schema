"""
Behavior and Discipline tracking models.
"""
from sqlalchemy import Boolean, Column, DateTime, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


# ---------------------------------------------------------------------------
# Behavior Type
# ---------------------------------------------------------------------------
class BehaviorType(BaseModel):
    """
    Lookup table for behavioral incident types.
    Examples: DISRUPTION, BULLYING, TARDINESS, RESPECTFUL, HELPFUL, EXCELLENT_WORK
    """
    __tablename__ = "behavior_types"
    __table_args__ = {"schema": "academic", "comment": "Behavioral incident type definitions"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    type_code = Column(String(50), nullable=False, index=True)
    type_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(20), nullable=False, comment="POSITIVE | NEGATIVE | NEUTRAL")
    severity_level = Column(String(20), nullable=True, comment="LOW | MEDIUM | HIGH | CRITICAL (for negative)")
    requires_parent_notification = Column(Boolean, default=False)
    requires_hod_approval = Column(Boolean, default=False)
    color_code = Column(String(10), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    behavior_records = relationship("BehaviorRecord", back_populates="behavior_type")

    def __repr__(self):
        return f"<BehaviorType(code={self.type_code}, category={self.category})>"


# ---------------------------------------------------------------------------
# Behavior Record
# ---------------------------------------------------------------------------
class BehaviorRecord(BaseModel):
    """
    Individual behavioral incident record for a student.

    Rules:
    - Any assigned teacher can raise a behavioral concern
    - HIGH/CRITICAL severity incidents require immediate HOD notification
    - Parents must be notified within 24 hours of HIGH/CRITICAL incidents
    - Records cannot be deleted (only soft-deleted)
    - Positive records are also tracked (encouragement system)
    """
    __tablename__ = "behavior_records"
    __table_args__ = {"schema": "academic", "comment": "Student behavioral incident records (positive and negative)"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)
    behavior_type_id = Column(UUID(as_uuid=True), ForeignKey("academic.behavior_types.id", ondelete="SET NULL"), nullable=True, index=True)

    # Incident context
    incident_date = Column(DateTime(timezone=True), nullable=False, index=True)
    incident_location = Column(String(100), nullable=True, comment="CLASSROOM | PLAYGROUND | CAFETERIA | CORRIDOR | ONLINE")

    # Subject context (if in class)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("academic.subjects.id", ondelete="SET NULL"), nullable=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("academic.classes.id", ondelete="SET NULL"), nullable=True)
    section_id = Column(UUID(as_uuid=True), ForeignKey("academic.sections.id", ondelete="SET NULL"), nullable=True)

    # Reporter
    reported_by_user_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="Teacher who reported this incident")
    reported_by_role = Column(String(30), nullable=False)

    # Details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, comment="LOW | MEDIUM | HIGH | CRITICAL")
    category = Column(String(20), nullable=False, comment="POSITIVE | NEGATIVE | NEUTRAL")

    # Witnesses
    witness_user_ids = Column(JSONB, default=[], comment="Array of witness user_ids")

    # Actions taken
    action_taken = Column(Text, nullable=True)
    follow_up_required = Column(Boolean, default=False)
    follow_up_date = Column(DateTime(timezone=True), nullable=True)
    follow_up_notes = Column(Text, nullable=True)

    # Notifications
    parent_notified = Column(Boolean, default=False)
    parent_notified_at = Column(DateTime(timezone=True), nullable=True)
    hod_notified = Column(Boolean, default=False)
    hod_notified_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(String(20), default="OPEN", comment="OPEN | RESOLVED | ESCALATED | CLOSED")
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id = Column(UUID(as_uuid=True), nullable=True)

    extra_metadata = Column(JSONB, default={})

    # Relationships
    student = relationship("AcademicProfile", back_populates="behavior_records")
    behavior_type = relationship("BehaviorType", back_populates="behavior_records")
    discipline_records = relationship("DisciplineRecord", back_populates="behavior_record")

    def __repr__(self):
        return f"<BehaviorRecord(student_id={self.student_id}, severity={self.severity}, category={self.category})>"


# ---------------------------------------------------------------------------
# Discipline Type
# ---------------------------------------------------------------------------
class DisciplineType(BaseModel):
    """
    Lookup table for disciplinary action types.
    Examples: VERBAL_WARNING, WRITTEN_WARNING, DETENTION, SUSPENSION, EXPULSION
    """
    __tablename__ = "discipline_types"
    __table_args__ = {"schema": "academic", "comment": "Disciplinary action type definitions"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    type_code = Column(String(50), nullable=False, index=True)
    type_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity_level = Column(String(20), nullable=False, comment="LOW | MEDIUM | HIGH | CRITICAL")
    requires_hod_approval = Column(Boolean, default=False)
    requires_principal_approval = Column(Boolean, default=False)
    requires_parent_meeting = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True, nullable=False)
    extra_metadata = Column(JSONB, default={})

    # Relationships
    discipline_records = relationship("DisciplineRecord", back_populates="discipline_type")

    def __repr__(self):
        return f"<DisciplineType(code={self.type_code})>"


# ---------------------------------------------------------------------------
# Discipline Record
# ---------------------------------------------------------------------------
class DisciplineRecord(BaseModel):
    """
    Formal disciplinary action record for a student.
    Linked to a behavior record (the triggering incident).

    Workflow:
    1. Teacher raises behavioral concern
    2. Class Teacher / HOD decides disciplinary action
    3. HOD or Principal approves (for HIGH/CRITICAL)
    4. Parent must be notified and sign acknowledgment
    5. Record permanently archived (cannot be deleted)
    """
    __tablename__ = "discipline_records"
    __table_args__ = {"schema": "academic", "comment": "Formal disciplinary action records — immutable after closure"}

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic.academic_years.id", ondelete="CASCADE"), nullable=False, index=True)
    behavior_record_id = Column(UUID(as_uuid=True), ForeignKey("academic.behavior_records.id", ondelete="SET NULL"), nullable=True, index=True)
    discipline_type_id = Column(UUID(as_uuid=True), ForeignKey("academic.discipline_types.id", ondelete="SET NULL"), nullable=True, index=True)

    # Action Details
    action_date = Column(DateTime(timezone=True), nullable=False, index=True)
    action_description = Column(Text, nullable=False)
    duration_days = Column(String(50), nullable=True, comment="Duration if applicable (e.g. 3 days suspension)")

    # Issued by
    issued_by_user_id = Column(UUID(as_uuid=True), nullable=False, comment="Who issued the disciplinary action")
    issued_by_role = Column(String(30), nullable=False)

    # Approval
    requires_approval = Column(Boolean, default=False)
    approved_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    approved_by_role = Column(String(30), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)
    approval_status = Column(String(20), default="PENDING", comment="PENDING | APPROVED | REJECTED")

    # Parent Communication
    parent_notified = Column(Boolean, default=False)
    parent_notified_at = Column(DateTime(timezone=True), nullable=True)
    parent_meeting_required = Column(Boolean, default=False)
    parent_meeting_date = Column(DateTime(timezone=True), nullable=True)
    parent_meeting_notes = Column(Text, nullable=True)
    parent_acknowledgment_required = Column(Boolean, default=True)
    parent_acknowledged = Column(Boolean, default=False)
    parent_acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(String(20), default="ACTIVE", comment="ACTIVE | SERVED | REVOKED | ESCALATED | CLOSED")
    closed_at = Column(DateTime(timezone=True), nullable=True)

    extra_metadata = Column(JSONB, default={})

    # Relationships
    student = relationship("AcademicProfile", back_populates="discipline_records")
    behavior_record = relationship("BehaviorRecord", back_populates="discipline_records")
    discipline_type = relationship("DisciplineType", back_populates="discipline_records")

    def __repr__(self):
        return f"<DisciplineRecord(student_id={self.student_id}, status={self.status})>"
