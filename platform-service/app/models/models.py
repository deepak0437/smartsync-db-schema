"""
Platform Service Models — Tenant management, subscriptions, feature flags.
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
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)


class Tenant(Base):
    """
    Master tenant (school) registry. Source of truth for all tenants.
    Auth service also maintains a copy for authentication purposes.
    """
    __tablename__ = "tenants"
    __table_args__ = {"schema": "platform"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_code = Column(String(50), unique=True, nullable=False, index=True)
    tenant_name = Column(String(255), nullable=False)
    tenant_type = Column(String(50), default="SCHOOL")
    domain = Column(String(255), nullable=True, unique=True)
    subdomain = Column(String(100), nullable=True, unique=True)
    logo_url = Column(Text, nullable=True)
    primary_contact_name = Column(String(255), nullable=True)
    primary_contact_email = Column(String(255), nullable=True)
    primary_contact_phone = Column(String(20), nullable=True)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    postal_code = Column(String(20), nullable=True)
    timezone = Column(String(50), default="Asia/Kolkata")
    locale = Column(String(10), default="en_IN")
    currency = Column(String(10), default="INR")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    extra_metadata = Column(JSONB, default={})
    subscriptions = relationship("TenantSubscription", back_populates="tenant")
    settings = relationship("TenantSettings", back_populates="tenant", uselist=False)
    feature_flags = relationship("TenantFeatureFlag", back_populates="tenant")


class SubscriptionPlan(Base):
    """Subscription plan definitions (BASIC, STANDARD, PREMIUM, ENTERPRISE)."""
    __tablename__ = "subscription_plans"
    __table_args__ = {"schema": "platform"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    plan_code = Column(String(50), unique=True, nullable=False)
    plan_name = Column(String(255), nullable=False)
    plan_description = Column(Text, nullable=True)
    max_students = Column(Integer, default=500)
    max_teachers = Column(Integer, default=50)
    max_staff = Column(Integer, default=20)
    max_storage_gb = Column(Integer, default=10)
    price_monthly = Column(Integer, default=0, comment="Price in paise (INR)")
    price_annual = Column(Integer, default=0)
    features = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TenantSubscription(BaseModel):
    """Active subscription record for a tenant."""
    __tablename__ = "tenant_subscriptions"
    __table_args__ = {"schema": "platform"}
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("platform.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("platform.subscription_plans.id"), nullable=False)
    status = Column(String(20), default="TRIAL", comment="TRIAL | ACTIVE | SUSPENDED | EXPIRED | CANCELLED")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    trial_end_date = Column(Date, nullable=True)
    auto_renew = Column(Boolean, default=True)
    payment_reference = Column(String(255), nullable=True)
    extra_metadata = Column(JSONB, default={})
    tenant = relationship("Tenant", back_populates="subscriptions")


class TenantSettings(BaseModel):
    """Per-tenant configuration settings."""
    __tablename__ = "tenant_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_platform_tenant_settings"),
        {"schema": "platform"},
    )
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("platform.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_start_month = Column(Integer, default=4, comment="Month (1-12) when academic year starts")
    working_days = Column(JSONB, default=["MON", "TUE", "WED", "THU", "FRI"])
    school_start_time = Column(String(10), default="09:00")
    school_end_time = Column(String(10), default="15:30")
    attendance_grace_period_days = Column(Integer, default=7)
    min_attendance_percentage = Column(Integer, default=75)
    max_concurrent_sessions = Column(Integer, default=5)
    password_expiry_days = Column(Integer, default=90)
    logo_url = Column(Text, nullable=True)
    primary_color = Column(String(10), nullable=True)
    secondary_color = Column(String(10), nullable=True)
    extra_settings = Column(JSONB, default={})
    tenant = relationship("Tenant", back_populates="settings")


class Feature(Base):
    """Global feature flag definitions."""
    __tablename__ = "features"
    __table_args__ = {"schema": "platform"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    feature_code = Column(String(100), unique=True, nullable=False)
    feature_name = Column(String(255), nullable=False)
    feature_description = Column(Text, nullable=True)
    module = Column(String(50), nullable=False, comment="ACADEMIC | FINANCE | HR | HOSTEL | TRANSPORT | LMS | ...")
    is_enabled_by_default = Column(Boolean, default=False)
    min_plan = Column(String(50), default="BASIC", comment="Minimum plan required: BASIC | STANDARD | PREMIUM | ENTERPRISE")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    tenant_flags = relationship("TenantFeatureFlag", back_populates="feature")


class TenantFeatureFlag(BaseModel):
    """Per-tenant feature enable/disable overrides."""
    __tablename__ = "tenant_feature_flags"
    __table_args__ = (
        UniqueConstraint("tenant_id", "feature_id", name="uq_platform_tenant_feature"),
        {"schema": "platform"},
    )
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("platform.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_id = Column(UUID(as_uuid=True), ForeignKey("platform.features.id", ondelete="CASCADE"), nullable=False, index=True)
    is_enabled = Column(Boolean, default=False, nullable=False)
    enabled_at = Column(DateTime(timezone=True), nullable=True)
    enabled_by = Column(UUID(as_uuid=True), nullable=True)
    extra_metadata = Column(JSONB, default={})
    tenant = relationship("Tenant", back_populates="feature_flags")
    feature = relationship("Feature", back_populates="tenant_flags")


class PlatformEvent(BaseModel):
    """Event outbox for platform-level events."""
    __tablename__ = "platform_events"
    __table_args__ = {"schema": "platform"}
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_version = Column(String(10), default="1.0")
    aggregate_type = Column(String(100), nullable=False)
    aggregate_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_data = Column(JSONB, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    extra_metadata = Column(JSONB, default={})
