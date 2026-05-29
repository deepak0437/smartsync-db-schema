"""
Session, MFA, device, login history and password management models.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class UserSession(BaseModel):
    """
    Active user sessions for authentication and session management.

    Supports:
    - JWT access tokens + refresh tokens
    - Device tracking
    - Concurrent session limits (max 5 per user)
    - Session expiry (8 hours access / 30 days refresh)
    """
    __tablename__ = "user_sessions"
    __table_args__ = {"schema": "auth", "comment": "Active user authentication sessions"}

    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Tokens
    session_token = Column(Text, unique=True, nullable=False, index=True, comment="Hashed JWT access token")
    refresh_token = Column(Text, unique=True, nullable=True, index=True, comment="Hashed refresh token")

    # Device Information
    device_id = Column(String(255), nullable=True)
    device_name = Column(String(255), nullable=True)
    device_type = Column(String(50), nullable=True, comment="WEB | MOBILE | TABLET | DESKTOP")
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)

    # Network Information
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)

    # Location (plain strings — no PostGIS required)
    location_country = Column(String(100), nullable=True)
    location_city = Column(String(100), nullable=True)
    location_latitude = Column(String(20), nullable=True)
    location_longitude = Column(String(20), nullable=True)

    # Session Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_trusted_device = Column(Boolean, default=False, nullable=False)

    # Timestamps
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    refresh_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Extra Metadata
    extra_metadata = Column(JSONB, default={})

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, device={self.device_type})>"


class UserMFA(BaseModel):
    """
    Multi-factor authentication settings for users.

    Supports: SMS | EMAIL | TOTP | BACKUP_CODES
    """
    __tablename__ = "user_mfa"
    __table_args__ = {"schema": "auth", "comment": "MFA configurations per user"}

    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True)

    # MFA Method
    mfa_method = Column(String(20), nullable=False, comment="SMS | EMAIL | TOTP | BACKUP_CODES")

    # MFA Credentials
    mfa_secret = Column(Text, nullable=True, comment="TOTP base32 secret (encrypted at rest)")
    phone_number = Column(String(20), nullable=True, comment="Phone for SMS OTP")
    email_address = Column(String(255), nullable=True, comment="Email for email OTP")
    backup_codes = Column(JSONB, default=[], comment="Hashed backup codes array")

    # Status
    is_primary = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Extra Metadata
    extra_metadata = Column(JSONB, default={})
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="mfa_settings")

    def __repr__(self):
        return f"<UserMFA(user_id={self.user_id}, method={self.mfa_method})>"


class UserDevice(BaseModel):
    """
    Trusted devices for users (skip MFA on trusted devices).
    """
    __tablename__ = "user_devices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "device_id", name="uq_auth_user_device"),
        {"schema": "auth", "comment": "Trusted device registry per user"},
    )

    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Device Information
    device_id = Column(String(255), nullable=False, comment="Hardware/browser fingerprint ID")
    device_name = Column(String(255), nullable=True)
    device_type = Column(String(50), nullable=True, comment="WEB | MOBILE | TABLET | DESKTOP")
    device_fingerprint = Column(Text, nullable=True)

    # Device Details
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    os_version = Column(String(50), nullable=True)
    app_version = Column(String(50), nullable=True)

    # Trust Status
    is_trusted = Column(Boolean, default=False, nullable=False)
    trusted_at = Column(DateTime(timezone=True), nullable=True)

    # Usage
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_ip_address = Column(String(45), nullable=True)

    # Extra Metadata
    extra_metadata = Column(JSONB, default={})
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="devices")

    def __repr__(self):
        return f"<UserDevice(user_id={self.user_id}, device={self.device_name})>"


class UserLoginHistory(BaseModel):
    """
    Audit trail of all user login attempts (successful and failed).
    High-volume table — consider partitioning by month.
    """
    __tablename__ = "user_login_history"
    __table_args__ = {"schema": "auth", "comment": "Login audit trail — partitioned by month in production"}

    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Login Information
    username_attempted = Column(String(100), nullable=True, comment="Username as typed (for failed attempts)")
    login_status = Column(String(20), nullable=False, index=True, comment="SUCCESS | FAILED | BLOCKED | MFA_REQUIRED")
    failure_reason = Column(String(255), nullable=True)

    # Network Information
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)

    # Device Information
    device_type = Column(String(50), nullable=True)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)

    # Location
    location_country = Column(String(100), nullable=True)
    location_city = Column(String(100), nullable=True)

    # MFA
    mfa_used = Column(Boolean, default=False, nullable=False)
    mfa_method = Column(String(20), nullable=True)

    # Session reference
    session_id = Column(UUID(as_uuid=True), nullable=True)

    # Extra Metadata
    extra_metadata = Column(JSONB, default={})

    # Relationships
    user = relationship("User", back_populates="login_history", foreign_keys=[user_id])

    def __repr__(self):
        return f"<UserLoginHistory(username={self.username_attempted}, status={self.login_status})>"


class PasswordResetToken(BaseModel):
    """
    Password reset tokens for secure account recovery.
    Tokens expire after 15 minutes. Only one active token per user.
    """
    __tablename__ = "password_reset_tokens"
    __table_args__ = {"schema": "auth", "comment": "Short-lived password reset tokens"}

    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Token (store hash, never plaintext)
    token_hash = Column(Text, unique=True, nullable=False, index=True, comment="SHA-256 hash of the reset token")

    # Expiry
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Usage
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Extra Metadata
    extra_metadata = Column(JSONB, default={})

    # Relationships
    user = relationship("User", back_populates="password_resets")

    def __repr__(self):
        return f"<PasswordResetToken(user_id={self.user_id}, used={self.is_used})>"


class PasswordHistory(BaseModel):
    """
    Password history to enforce password reuse policy (cannot reuse last 5 passwords).
    """
    __tablename__ = "password_history"
    __table_args__ = {"schema": "auth", "comment": "Password history for reuse prevention"}

    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Password
    password_hash = Column(Text, nullable=False)
    password_salt = Column(Text, nullable=False)

    # Change Information
    changed_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=True)
    changed_reason = Column(String(100), nullable=True, comment="RESET | EXPIRED | USER_INITIATED | ADMIN_RESET")

    # Request context
    ip_address = Column(String(45), nullable=True)

    # Relationships
    user = relationship("User", back_populates="password_history", foreign_keys=[user_id])

    def __repr__(self):
        return f"<PasswordHistory(user_id={self.user_id}, reason={self.changed_reason})>"
