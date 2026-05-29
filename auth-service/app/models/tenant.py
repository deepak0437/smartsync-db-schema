"""
Tenant model for multi-tenant school organizations.
"""
from sqlalchemy import Boolean, Column, Date, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import TenantBaseModel


class Tenant(TenantBaseModel):
    """
    Multi-tenant school organizations with subscription management.

    Each school is a separate tenant with fully isolated row-level data.
    tenant_code is globally unique across all tenants.
    """
    __tablename__ = "tenants"
    __table_args__ = {"schema": "auth", "comment": "School/organization tenant registry"}

    # Basic Information
    tenant_code = Column(String(50), unique=True, nullable=False, index=True, comment="Unique tenant slug (e.g. SPRINGFIELD_HIGH)")
    tenant_name = Column(String(255), nullable=False, comment="Full school name")
    tenant_type = Column(String(50), nullable=False, default="SCHOOL", comment="SCHOOL | DISTRICT | ENTERPRISE")

    # Domain & Branding
    domain = Column(String(255), nullable=True, comment="Custom domain for the tenant")
    subdomain = Column(String(100), unique=True, nullable=True, index=True, comment="Subdomain (e.g. springfield.smartsync.ai)")
    logo_url = Column(Text, nullable=True, comment="Logo URL (CDN path)")

    # Contact Information
    primary_contact_name = Column(String(255), nullable=True)
    primary_contact_email = Column(String(255), nullable=True)
    primary_contact_phone = Column(String(20), nullable=True)

    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    postal_code = Column(String(20), nullable=True)

    # Localization
    timezone = Column(String(50), default="Asia/Kolkata", comment="IANA timezone string")
    locale = Column(String(10), default="en_IN")
    currency = Column(String(10), default="INR")

    # Subscription
    subscription_plan = Column(String(50), default="BASIC", comment="BASIC | STANDARD | PREMIUM | ENTERPRISE")
    subscription_status = Column(String(50), default="TRIAL", comment="TRIAL | ACTIVE | SUSPENDED | EXPIRED")
    subscription_start_date = Column(Date, nullable=True)
    subscription_end_date = Column(Date, nullable=True)

    # Capacity Limits
    max_students = Column(Integer, default=500)
    max_teachers = Column(Integer, default=50)
    max_staff = Column(Integer, default=20)

    # Configuration
    features = Column(JSONB, default={}, comment="Feature flags per tenant")
    settings = Column(JSONB, default={}, comment="Tenant-specific configuration")
    metadata = Column(JSONB, default={})

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(code={self.tenant_code}, name={self.tenant_name})>"
