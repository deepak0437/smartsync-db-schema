"""
User model for central identity management.
"""
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class User(BaseModel):
    """
    Central user identity table for all user types.

    User types: STUDENT | TEACHER | PARENT | ADMIN | SUPER_ADMIN
    Username format varies by role:
    - Student:    Admission Number
    - Teacher:    Employee ID
    - Parent:     Phone Number
    - Admin:      Email
    """
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_auth_tenant_username"),
        UniqueConstraint("tenant_id", "email", name="uq_auth_tenant_email"),
        UniqueConstraint("tenant_id", "phone", name="uq_auth_tenant_phone"),
        {"schema": "auth", "comment": "Central identity table for all system users"},
    )

    # Foreign Keys
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owning tenant (school)",
    )

    # Authentication
    username = Column(String(100), nullable=False, index=True, comment="Unique username per tenant")
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True, index=True)
    password_hash = Column(Text, nullable=False)
    password_salt = Column(Text, nullable=False)

    # User Type
    user_type = Column(
        String(50), nullable=False, index=True,
        comment="STUDENT | TEACHER | PARENT | ADMIN | SUPER_ADMIN",
    )

    # Personal Information
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=False)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)

    # Demographics
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True, comment="MALE | FEMALE | OTHER")
    blood_group = Column(String(10), nullable=True)
    nationality = Column(String(100), default="Indian")

    # Preferences
    language_preference = Column(String(10), default="en")
    timezone = Column(String(50), default="Asia/Kolkata")
    preferences = Column(JSONB, default={})

    # Account Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    is_password_expired = Column(Boolean, default=False, nullable=False)
    must_change_password = Column(Boolean, default=True, nullable=False, comment="Force password change on first login")

    # Security Tracking
    failed_login_attempts = Column(Integer, default=0)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    last_password_change_at = Column(DateTime(timezone=True), nullable=True)
    password_expires_at = Column(DateTime(timezone=True), nullable=True)
    account_locked_until = Column(DateTime(timezone=True), nullable=True)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    phone_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Two-Factor Authentication
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_method = Column(String(20), nullable=True, comment="SMS | EMAIL | TOTP | NONE")

    # Extra Metadata
    extra_metadata = Column(JSONB, default={}, comment="Flexible metadata storage")

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan", foreign_keys="UserRole.user_id")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    mfa_settings = relationship("UserMFA", back_populates="user", cascade="all, delete-orphan")
    devices = relationship("UserDevice", back_populates="user", cascade="all, delete-orphan")
    login_history = relationship("UserLoginHistory", back_populates="user", foreign_keys="UserLoginHistory.user_id")
    password_resets = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    password_history = relationship("PasswordHistory", back_populates="user", cascade="all, delete-orphan", foreign_keys="PasswordHistory.user_id")
    user_permissions = relationship("UserPermission", back_populates="user", cascade="all, delete-orphan", foreign_keys="UserPermission.user_id")

    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<User(username={self.username}, type={self.user_type})>"
