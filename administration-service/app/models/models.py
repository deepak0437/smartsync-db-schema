"""
Administration Service Models — Admissions, documents, ID cards, onboarding.
"""
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship
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


class AdmissionEnquiry(BaseModel):
    """Student admission enquiry (pre-admission)."""
    __tablename__ = "admission_enquiries"
    __table_args__ = {"schema": "administration"}
    enquiry_number = Column(String(50), unique=True, nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    applying_for_class = Column(String(50), nullable=False)
    student_name = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)
    father_name = Column(String(255), nullable=True)
    mother_name = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=False)
    contact_email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    previous_school = Column(String(255), nullable=True)
    previous_class = Column(String(50), nullable=True)
    source = Column(String(50), nullable=True, comment="WALK_IN | ONLINE | REFERRAL | ADVERTISEMENT")
    enquiry_date = Column(Date, nullable=False)
    status = Column(String(20), default="NEW", comment="NEW | FOLLOWED_UP | CONVERTED | REJECTED | DROPPED")
    assigned_to_user_id = Column(UUID(as_uuid=True), nullable=True)
    follow_up_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    extra_metadata = Column(JSONB, default={})


class Admission(BaseModel):
    """Student admission record."""
    __tablename__ = "admissions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "admission_number", name="uq_admin_admission_number"),
        {"schema": "administration"},
    )
    enquiry_id = Column(UUID(as_uuid=True), ForeignKey("administration.admission_enquiries.id", ondelete="SET NULL"), nullable=True)
    admission_number = Column(String(50), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    admitted_to_class = Column(String(50), nullable=False)
    admitted_to_section = Column(String(10), nullable=True)
    admission_date = Column(Date, nullable=False)
    # Student basic info (before user account creation)
    student_name = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)
    blood_group = Column(String(5), nullable=True)
    nationality = Column(String(50), default="Indian")
    religion = Column(String(50), nullable=True)
    caste_category = Column(String(20), nullable=True, comment="GENERAL | OBC | SC | ST | OTHER")
    mother_tongue = Column(String(50), nullable=True)
    # Parents
    father_name = Column(String(255), nullable=True)
    father_occupation = Column(String(100), nullable=True)
    father_phone = Column(String(20), nullable=True)
    mother_name = Column(String(255), nullable=True)
    mother_occupation = Column(String(100), nullable=True)
    mother_phone = Column(String(20), nullable=True)
    guardian_name = Column(String(255), nullable=True)
    guardian_phone = Column(String(20), nullable=True)
    # Address
    address_line1 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    # Previous School
    previous_school_name = Column(String(255), nullable=True)
    previous_school_board = Column(String(50), nullable=True)
    tc_number = Column(String(100), nullable=True, comment="Transfer Certificate number")
    tc_date = Column(Date, nullable=True)
    # User account created
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True, comment="Auth service user_id after account creation")
    user_created_at = Column(DateTime(timezone=True), nullable=True)
    # Status
    status = Column(String(20), default="PENDING", comment="PENDING | DOCUMENTS_PENDING | CONFIRMED | CANCELLED")
    extra_metadata = Column(JSONB, default={})
    documents = relationship("AdmissionDocument", back_populates="admission")


class DocumentType(BaseModel):
    """Document type definitions for admissions and records."""
    __tablename__ = "document_types"
    __table_args__ = (
        UniqueConstraint("tenant_id", "doc_type_code", name="uq_admin_doc_type"),
        {"schema": "administration"},
    )
    doc_type_code = Column(String(50), nullable=False)
    doc_type_name = Column(String(255), nullable=False)
    is_mandatory = Column(Boolean, default=False)
    applicable_to = Column(String(20), nullable=False, comment="STUDENT | EMPLOYEE | BOTH")
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class AdmissionDocument(BaseModel):
    """Documents submitted during admission."""
    __tablename__ = "admission_documents"
    __table_args__ = {"schema": "administration"}
    admission_id = Column(UUID(as_uuid=True), ForeignKey("administration.admissions.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type_id = Column(UUID(as_uuid=True), ForeignKey("administration.document_types.id"), nullable=True)
    document_name = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=False, comment="CDN URL from media-service")
    media_file_id = Column(UUID(as_uuid=True), nullable=True)
    verification_status = Column(String(20), default="PENDING", comment="PENDING | VERIFIED | REJECTED")
    verified_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    extra_metadata = Column(JSONB, default={})
    admission = relationship("Admission", back_populates="documents")


class IDCard(BaseModel):
    """Generated ID cards for students and staff."""
    __tablename__ = "id_cards"
    __table_args__ = {"schema": "administration"}
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_type = Column(String(20), nullable=False, comment="STUDENT | TEACHER | STAFF")
    academic_year_id = Column(UUID(as_uuid=True), nullable=True)
    card_number = Column(String(50), unique=True, nullable=False)
    template_id = Column(String(50), nullable=True)
    front_image_url = Column(Text, nullable=True)
    back_image_url = Column(Text, nullable=True)
    qr_code_data = Column(Text, nullable=True)
    barcode_data = Column(Text, nullable=True)
    valid_from = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)
    is_printed = Column(Boolean, default=False)
    printed_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class StaffOnboarding(BaseModel):
    """Staff onboarding workflow tracking."""
    __tablename__ = "staff_onboarding"
    __table_args__ = {"schema": "administration"}
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True, comment="Created after user account")
    employee_name = Column(String(255), nullable=False)
    designation = Column(String(100), nullable=True)
    joining_date = Column(Date, nullable=False)
    status = Column(String(20), default="INITIATED", comment="INITIATED | DOCUMENTS_PENDING | HR_REVIEW | COMPLETED")
    checklist = Column(JSONB, default={}, comment="Onboarding checklist completion status")
    assigned_to_user_id = Column(UUID(as_uuid=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    extra_metadata = Column(JSONB, default={})
