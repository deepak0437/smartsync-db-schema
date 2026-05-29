"""
HR Service Models — Employee management, payroll, staff leave, performance.
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


class Designation(BaseModel):
    """Job designations (Principal, Vice Principal, HOD, Teacher, etc.)."""
    __tablename__ = "designations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "designation_code", name="uq_hr_designation"),
        {"schema": "hr"},
    )
    designation_code = Column(String(50), nullable=False)
    designation_name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=True)
    grade = Column(String(20), nullable=True)
    is_teaching = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class Employee(BaseModel):
    """HR employee master record."""
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_code", name="uq_hr_employee_code"),
        UniqueConstraint("tenant_id", "user_id", name="uq_hr_employee_user"),
        {"schema": "hr"},
    )
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="Auth service user_id")
    employee_code = Column(String(50), nullable=False, index=True)
    designation_id = Column(UUID(as_uuid=True), ForeignKey("hr.designations.id", ondelete="SET NULL"), nullable=True)
    department = Column(String(100), nullable=True)
    employee_type = Column(String(30), default="FULL_TIME", comment="FULL_TIME | PART_TIME | CONTRACT | VISITING")
    joining_date = Column(Date, nullable=False)
    confirmation_date = Column(Date, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)
    blood_group = Column(String(5), nullable=True)
    pan_number = Column(String(20), nullable=True, comment="Encrypted at rest")
    aadhar_number = Column(String(20), nullable=True, comment="Encrypted at rest")
    bank_account_number = Column(String(30), nullable=True, comment="Encrypted at rest")
    bank_ifsc = Column(String(20), nullable=True)
    bank_name = Column(String(100), nullable=True)
    highest_qualification = Column(String(100), nullable=True)
    specialization = Column(String(255), nullable=True)
    experience_years = Column(Integer, default=0)
    employment_status = Column(String(20), default="ACTIVE", comment="ACTIVE | ON_LEAVE | RESIGNED | TERMINATED | RETIRED")
    resignation_date = Column(Date, nullable=True)
    last_working_date = Column(Date, nullable=True)
    address_line1 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    payroll_records = relationship("PayrollRecord", back_populates="employee")
    leave_records = relationship("StaffLeave", back_populates="employee")
    performance_reviews = relationship("EmployeePerformanceReview", back_populates="employee")


class PayrollStructure(BaseModel):
    """Payroll component structures (salary components)."""
    __tablename__ = "payroll_structures"
    __table_args__ = {"schema": "hr"}
    structure_name = Column(String(255), nullable=False)
    basic_percentage = Column(Numeric(5, 2), default=50.0, comment="Basic as % of CTC")
    hra_percentage = Column(Numeric(5, 2), default=20.0)
    da_percentage = Column(Numeric(5, 2), default=10.0)
    ta_percentage = Column(Numeric(5, 2), default=5.0)
    pf_percentage = Column(Numeric(5, 2), default=12.0, comment="Employee PF contribution")
    employer_pf_percentage = Column(Numeric(5, 2), default=12.0)
    esi_percentage = Column(Numeric(5, 2), default=0.75)
    other_allowances = Column(JSONB, default={})
    other_deductions = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class EmployeeSalary(BaseModel):
    """Employee salary configuration."""
    __tablename__ = "employee_salaries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", name="uq_hr_employee_salary"),
        {"schema": "hr"},
    )
    employee_id = Column(UUID(as_uuid=True), ForeignKey("hr.employees.id", ondelete="CASCADE"), nullable=False)
    payroll_structure_id = Column(UUID(as_uuid=True), ForeignKey("hr.payroll_structures.id"), nullable=True)
    ctc_annual = Column(Numeric(12, 2), nullable=False, comment="Annual CTC in INR")
    ctc_monthly = Column(Numeric(10, 2), nullable=False)
    basic = Column(Numeric(10, 2), nullable=False)
    hra = Column(Numeric(10, 2), default=0)
    da = Column(Numeric(10, 2), default=0)
    ta = Column(Numeric(10, 2), default=0)
    other_allowances = Column(JSONB, default={})
    effective_from = Column(Date, nullable=False)
    effective_until = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class PayrollRecord(BaseModel):
    """Monthly payroll record per employee."""
    __tablename__ = "payroll_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", "payroll_month", "payroll_year", name="uq_hr_payroll_record"),
        {"schema": "hr"},
    )
    employee_id = Column(UUID(as_uuid=True), ForeignKey("hr.employees.id", ondelete="CASCADE"), nullable=False, index=True)
    payroll_month = Column(Integer, nullable=False)
    payroll_year = Column(Integer, nullable=False)
    working_days = Column(Integer, nullable=False)
    present_days = Column(Integer, nullable=False)
    leave_days = Column(Integer, default=0)
    gross_salary = Column(Numeric(10, 2), nullable=False)
    total_deductions = Column(Numeric(10, 2), default=0)
    net_salary = Column(Numeric(10, 2), nullable=False)
    pf_deduction = Column(Numeric(10, 2), default=0)
    esi_deduction = Column(Numeric(10, 2), default=0)
    tds_deduction = Column(Numeric(10, 2), default=0)
    other_deductions = Column(JSONB, default={})
    other_allowances = Column(JSONB, default={})
    payment_status = Column(String(20), default="PENDING", comment="PENDING | PROCESSED | PAID | FAILED")
    payment_date = Column(Date, nullable=True)
    payment_reference = Column(String(255), nullable=True)
    remarks = Column(Text, nullable=True)
    extra_metadata = Column(JSONB, default={})
    employee = relationship("Employee", back_populates="payroll_records")


class LeaveType(BaseModel):
    """Staff leave type definitions."""
    __tablename__ = "leave_types"
    __table_args__ = (
        UniqueConstraint("tenant_id", "leave_code", name="uq_hr_leave_type"),
        {"schema": "hr"},
    )
    leave_code = Column(String(20), nullable=False)
    leave_name = Column(String(100), nullable=False)
    max_days_per_year = Column(Integer, default=0)
    is_paid = Column(Boolean, default=True)
    carry_forward = Column(Boolean, default=False)
    max_carry_forward_days = Column(Integer, default=0)
    requires_document = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class StaffLeave(BaseModel):
    """Staff leave request and tracking."""
    __tablename__ = "staff_leaves"
    __table_args__ = {"schema": "hr"}
    employee_id = Column(UUID(as_uuid=True), ForeignKey("hr.employees.id", ondelete="CASCADE"), nullable=False, index=True)
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("hr.leave_types.id"), nullable=False)
    academic_year_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    from_date = Column(Date, nullable=False, index=True)
    to_date = Column(Date, nullable=False)
    total_days = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    document_url = Column(Text, nullable=True)
    status = Column(String(20), default="PENDING", comment="PENDING | APPROVED | REJECTED | CANCELLED")
    approved_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    extra_metadata = Column(JSONB, default={})
    employee = relationship("Employee", back_populates="leave_records")


class LeaveBalance(BaseModel):
    """Staff leave balance per academic year."""
    __tablename__ = "leave_balances"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", "leave_type_id", "academic_year_id", name="uq_hr_leave_balance"),
        {"schema": "hr"},
    )
    employee_id = Column(UUID(as_uuid=True), ForeignKey("hr.employees.id", ondelete="CASCADE"), nullable=False, index=True)
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("hr.leave_types.id"), nullable=False)
    academic_year_id = Column(UUID(as_uuid=True), nullable=False)
    total_allocated = Column(Integer, default=0)
    total_used = Column(Integer, default=0)
    total_pending = Column(Integer, default=0)
    carried_forward = Column(Integer, default=0)
    balance_remaining = Column(Integer, default=0)
    extra_metadata = Column(JSONB, default={})


class EmployeePerformanceReview(BaseModel):
    """Annual employee performance review."""
    __tablename__ = "employee_performance_reviews"
    __table_args__ = {"schema": "hr"}
    employee_id = Column(UUID(as_uuid=True), ForeignKey("hr.employees.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    review_period = Column(String(30), nullable=False, comment="ANNUAL | SEMI_ANNUAL | QUARTERLY")
    reviewer_user_id = Column(UUID(as_uuid=True), nullable=False)
    teaching_effectiveness = Column(Integer, nullable=True, comment="1-5 rating")
    student_engagement = Column(Integer, nullable=True)
    punctuality = Column(Integer, nullable=True)
    teamwork = Column(Integer, nullable=True)
    professional_development = Column(Integer, nullable=True)
    overall_rating = Column(Integer, nullable=True)
    strengths = Column(Text, nullable=True)
    areas_for_improvement = Column(Text, nullable=True)
    goals_for_next_period = Column(Text, nullable=True)
    employee_comments = Column(Text, nullable=True)
    status = Column(String(20), default="DRAFT", comment="DRAFT | SUBMITTED | ACKNOWLEDGED | FINALIZED")
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    extra_metadata = Column(JSONB, default={})
    employee = relationship("Employee", back_populates="performance_reviews")


class HREvent(BaseModel):
    """HR service event outbox."""
    __tablename__ = "hr_events"
    __table_args__ = {"schema": "hr"}
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
