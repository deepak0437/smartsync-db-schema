"""
Finance Service Models — Fee structures, collections, invoices, payments.
"""
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Numeric, String, Text, ForeignKey, UniqueConstraint
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


class FeeCategory(BaseModel):
    """Fee category definitions (e.g., TUITION, TRANSPORT, HOSTEL, EXAM)."""
    __tablename__ = "fee_categories"
    __table_args__ = (
        UniqueConstraint("tenant_id", "category_code", name="uq_finance_fee_category"),
        {"schema": "finance"},
    )
    category_code = Column(String(50), nullable=False)
    category_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_mandatory = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    fee_structures = relationship("FeeStructure", back_populates="category")


class FeeStructure(BaseModel):
    """Fee structure per class per academic year."""
    __tablename__ = "fee_structures"
    __table_args__ = (
        UniqueConstraint("tenant_id", "academic_year_id", "class_id", "category_id", name="uq_finance_fee_structure"),
        {"schema": "finance"},
    )
    academic_year_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), nullable=True, index=True, comment="Null = all classes")
    category_id = Column(UUID(as_uuid=True), ForeignKey("finance.fee_categories.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False, comment="Amount in INR")
    due_date = Column(Date, nullable=True)
    installments_allowed = Column(Boolean, default=False)
    max_installments = Column(Integer, default=1)
    late_fee_per_day = Column(Numeric(8, 2), default=0)
    discount_eligible = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    category = relationship("FeeCategory", back_populates="fee_structures")
    fee_collections = relationship("FeeCollection", back_populates="fee_structure")


class FeeDiscount(BaseModel):
    """Fee discount definitions (scholarships, sibling discounts, etc.)."""
    __tablename__ = "fee_discounts"
    __table_args__ = {"schema": "finance"}
    discount_code = Column(String(50), nullable=False)
    discount_name = Column(String(255), nullable=False)
    discount_type = Column(String(20), nullable=False, comment="PERCENTAGE | FIXED")
    discount_value = Column(Numeric(8, 2), nullable=False)
    applicable_categories = Column(JSONB, default=[], comment="Array of fee_category_ids")
    valid_from = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class StudentFeeAccount(BaseModel):
    """Student fee ledger account."""
    __tablename__ = "student_fee_accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "student_id", "academic_year_id", name="uq_finance_student_fee_account"),
        {"schema": "finance"},
    )
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="academic_profile.id")
    academic_year_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    total_fees_due = Column(Numeric(12, 2), default=0)
    total_fees_paid = Column(Numeric(12, 2), default=0)
    total_discount = Column(Numeric(12, 2), default=0)
    total_waiver = Column(Numeric(12, 2), default=0)
    outstanding_balance = Column(Numeric(12, 2), default=0)
    last_payment_date = Column(Date, nullable=True)
    is_defaulter = Column(Boolean, default=False)
    extra_metadata = Column(JSONB, default={})
    collections = relationship("FeeCollection", back_populates="fee_account")


class FeeCollection(BaseModel):
    """Individual fee payment collection record."""
    __tablename__ = "fee_collections"
    __table_args__ = {"schema": "finance"}
    fee_account_id = Column(UUID(as_uuid=True), ForeignKey("finance.student_fee_accounts.id"), nullable=False, index=True)
    fee_structure_id = Column(UUID(as_uuid=True), ForeignKey("finance.fee_structures.id"), nullable=True)
    receipt_number = Column(String(50), unique=True, nullable=False, index=True)
    amount_paid = Column(Numeric(12, 2), nullable=False)
    late_fee_charged = Column(Numeric(8, 2), default=0)
    discount_applied = Column(Numeric(8, 2), default=0)
    payment_date = Column(Date, nullable=False, index=True)
    payment_mode = Column(String(30), nullable=False, comment="CASH | CHEQUE | ONLINE | UPI | NEFT | DD")
    payment_reference = Column(String(255), nullable=True, comment="Transaction ID / Cheque number")
    payment_status = Column(String(20), default="SUCCESS", comment="SUCCESS | PENDING | FAILED | REFUNDED")
    collected_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    remarks = Column(Text, nullable=True)
    extra_metadata = Column(JSONB, default={})
    fee_account = relationship("StudentFeeAccount", back_populates="collections")
    fee_structure = relationship("FeeStructure", back_populates="fee_collections")


class Invoice(BaseModel):
    """Fee invoice generated for students."""
    __tablename__ = "invoices"
    __table_args__ = {"schema": "finance"}
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), default="UNPAID", comment="UNPAID | PARTIAL | PAID | OVERDUE | CANCELLED")
    invoice_data = Column(JSONB, nullable=False, comment="Line items snapshot")
    extra_metadata = Column(JSONB, default={})


class FinanceEvent(BaseModel):
    """Finance service event outbox."""
    __tablename__ = "finance_events"
    __table_args__ = {"schema": "finance"}
    event_type = Column(String(100), nullable=False, index=True)
    event_version = Column(String(10), default="1.0")
    aggregate_type = Column(String(100), nullable=False)
    aggregate_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_data = Column(JSONB, nullable=False)
    is_published = Column(Boolean, default=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    extra_metadata = Column(JSONB, default={})
