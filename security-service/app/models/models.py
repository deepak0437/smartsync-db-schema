"""
Security Service Models — Visitors, gate passes, access logs, CCTV incidents.
"""
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase
from uuid import uuid4
from sqlalchemy import func


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)


class VisitorRegistration(BaseModel):
    """Visitor entry registration."""
    __tablename__ = "visitor_registrations"
    __table_args__ = {"schema": "security"}
    visitor_name = Column(String(255), nullable=False)
    visitor_phone = Column(String(20), nullable=False, index=True)
    visitor_id_type = Column(String(30), nullable=True, comment="AADHAR | PAN | PASSPORT | DRIVING_LICENSE")
    visitor_id_number = Column(String(50), nullable=True)
    visitor_photo_url = Column(Text, nullable=True)
    purpose = Column(String(50), nullable=False, comment="PARENT_MEETING | DELIVERY | OFFICIAL | MAINTENANCE | OTHER")
    purpose_description = Column(Text, nullable=True)
    person_to_meet_user_id = Column(UUID(as_uuid=True), nullable=True, comment="Staff being visited")
    person_to_meet_name = Column(String(255), nullable=True)
    student_id = Column(UUID(as_uuid=True), nullable=True, comment="If visiting a student")
    entry_time = Column(DateTime(timezone=True), nullable=False, index=True)
    expected_exit_time = Column(DateTime(timezone=True), nullable=True)
    actual_exit_time = Column(DateTime(timezone=True), nullable=True, index=True)
    gate_pass_number = Column(String(50), nullable=True, unique=True)
    badge_number = Column(String(20), nullable=True)
    vehicle_number = Column(String(20), nullable=True)
    status = Column(String(20), default="INSIDE", comment="INSIDE | EXITED | OVERSTAY | DENIED")
    approved_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    security_guard_user_id = Column(UUID(as_uuid=True), nullable=True)
    remarks = Column(Text, nullable=True)
    extra_metadata = Column(JSONB, default={})


class GatePass(BaseModel):
    """Gate pass for student exit during school hours."""
    __tablename__ = "gate_passes"
    __table_args__ = {"schema": "security"}
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    pass_number = Column(String(50), unique=True, nullable=False)
    issue_date = Column(Date, nullable=False, index=True)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    expected_return_time = Column(DateTime(timezone=True), nullable=True)
    actual_return_time = Column(DateTime(timezone=True), nullable=True)
    reason = Column(Text, nullable=False)
    pass_type = Column(String(20), nullable=False, comment="MEDICAL | FAMILY_EMERGENCY | EARLY_LEAVE | FIELD_TRIP")
    issued_by_user_id = Column(UUID(as_uuid=True), nullable=False)
    parent_authorized = Column(Boolean, default=False)
    parent_user_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(String(20), default="ACTIVE", comment="ACTIVE | RETURNED | EXPIRED | CANCELLED")
    extra_metadata = Column(JSONB, default={})


class AccessLog(BaseModel):
    """RFID/biometric access control logs."""
    __tablename__ = "access_logs"
    __table_args__ = {"schema": "security"}
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    access_point = Column(String(100), nullable=False, comment="MAIN_GATE | HOSTEL | LAB | LIBRARY | ...")
    access_type = Column(String(10), nullable=False, comment="ENTRY | EXIT")
    access_method = Column(String(20), nullable=False, comment="RFID | BIOMETRIC | MANUAL | QRCODE")
    credential_id = Column(String(100), nullable=True, comment="RFID card number or biometric ID")
    access_granted = Column(Boolean, nullable=False)
    denial_reason = Column(String(255), nullable=True)
    access_time = Column(DateTime(timezone=True), nullable=False, index=True)
    device_id = Column(String(100), nullable=True, comment="Access control device ID")
    extra_metadata = Column(JSONB, default={})


class CCTVIncident(BaseModel):
    """CCTV-based security incident records."""
    __tablename__ = "cctv_incidents"
    __table_args__ = {"schema": "security"}
    camera_id = Column(String(100), nullable=False)
    camera_location = Column(String(255), nullable=False)
    incident_type = Column(String(50), nullable=False)
    incident_time = Column(DateTime(timezone=True), nullable=False, index=True)
    description = Column(Text, nullable=False)
    footage_url = Column(Text, nullable=True, comment="CDN URL to incident footage")
    reported_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    assigned_to_user_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(String(20), default="OPEN", comment="OPEN | INVESTIGATING | RESOLVED | CLOSED | ESCALATED")
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    extra_metadata = Column(JSONB, default={})
