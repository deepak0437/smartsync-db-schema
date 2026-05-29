"""
Management Service Models — Org structure, departments, designations, reporting hierarchy.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey, UniqueConstraint
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


class OrgUnit(BaseModel):
    """Organizational unit (school, wing, department, class-group)."""
    __tablename__ = "org_units"
    __table_args__ = {"schema": "management"}
    unit_code = Column(String(50), nullable=False)
    unit_name = Column(String(255), nullable=False)
    unit_type = Column(String(30), nullable=False, comment="SCHOOL | WING | DEPARTMENT | CLASS_GROUP")
    parent_unit_id = Column(UUID(as_uuid=True), ForeignKey("management.org_units.id", ondelete="SET NULL"), nullable=True)
    head_user_id = Column(UUID(as_uuid=True), nullable=True, comment="Head of this unit")
    level = Column(Integer, default=1, comment="Hierarchy depth")
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    children = relationship("OrgUnit", foreign_keys=[parent_unit_id])


class ManagementDepartment(BaseModel):
    """Management departments (broader than academic departments)."""
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "dept_code", name="uq_mgmt_department"),
        {"schema": "management"},
    )
    dept_code = Column(String(50), nullable=False)
    dept_name = Column(String(255), nullable=False)
    dept_type = Column(String(30), nullable=False, comment="ACADEMIC | ADMINISTRATIVE | OPERATIONAL | SUPPORT")
    org_unit_id = Column(UUID(as_uuid=True), ForeignKey("management.org_units.id", ondelete="SET NULL"), nullable=True)
    head_user_id = Column(UUID(as_uuid=True), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class ManagementDesignation(BaseModel):
    """Designation/job title management."""
    __tablename__ = "designations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "designation_code", name="uq_mgmt_designation"),
        {"schema": "management"},
    )
    designation_code = Column(String(50), nullable=False)
    designation_name = Column(String(255), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("management.departments.id", ondelete="SET NULL"), nullable=True)
    grade = Column(String(20), nullable=True, comment="Pay grade/band")
    level = Column(Integer, default=1, comment="Hierarchy level (1=lowest)")
    is_leadership = Column(Boolean, default=False)
    is_teaching = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class ReportingHierarchy(BaseModel):
    """Reporting relationship between employees."""
    __tablename__ = "reporting_hierarchy"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_user_id", name="uq_mgmt_reporting"),
        {"schema": "management"},
    )
    employee_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    reports_to_user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    designation_id = Column(UUID(as_uuid=True), ForeignKey("management.designations.id", ondelete="SET NULL"), nullable=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("management.departments.id", ondelete="SET NULL"), nullable=True)
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_until = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class SchoolCalendar(BaseModel):
    """School academic calendar with holidays, events."""
    __tablename__ = "school_calendar"
    __table_args__ = {"schema": "management"}
    academic_year_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_date = Column(DateTime(timezone=True), nullable=False, index=True)
    event_end_date = Column(DateTime(timezone=True), nullable=True)
    event_type = Column(String(30), nullable=False, comment="HOLIDAY | EXAM | EVENT | HALF_DAY | SPECIAL")
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    is_holiday = Column(Boolean, default=False)
    is_school_wide = Column(Boolean, default=True)
    applicable_classes = Column(JSONB, default=[], comment="Array of class IDs (empty = all)")
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
