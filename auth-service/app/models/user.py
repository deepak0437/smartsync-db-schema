"""
User Model — Auth Service

Stores ONLY identity and security data.
Business information (DOB, address, qualification) lives in domain services:
  - Student details → Academic Service (StudentProfile)
  - Teacher details → HR Service (EmployeeProfile)
  - Parent details  → Academic Service (ParentProfile)

Multi-Tenancy Model:
  Users belong to both a Tenant (org boundary) and a School (operational boundary).
  username is unique within a (tenant_id, school_id) scope.

No-Signup Architecture:
  Users are always created by a School Admin.
  There is no self-registration flow.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class User(BaseModel):
    """
    Central identity table for ALL users across all roles.

    Username conventions (set at creation, never changed):
        STUDENT      → Admission Number         (e.g. "ADM-2024-001")
        TEACHER      → Employee Code            (e.g. "EMP-0042")
        PARENT       → Auto-generated           (e.g. "PAR-0091")
        ADMIN        → Email prefix             (e.g. "principal@gvs")
        SUPER_ADMIN  → Assigned by Platform     (e.g. "admin@smartsync")

    Scope:
        username is unique within (tenant_id, school_id).
        The same person (e.g. a parent with children in two schools)
        has TWO separate user rows — one per school.
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "school_id", "username",
            name="uq_auth_user_username",
        ),
        UniqueConstraint(
            "tenant_id", "school_id", "email",
            name="uq_auth_user_email",
        ),
        {
            "schema": "auth",
            "comment": (
                "Central identity table. One row per user per school. "
                "No business data stored here."
            ),
        },
    )

    # ── Tenant & School Scoping ────────────────────────────────────────────────
    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment=(
            "Owning tenant (organization). Soft FK → platform.tenants.id. "
            "Not a hard FK to avoid cross-service constraints."
        ),
    )
    school_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment=(
            "Owning school (operational unit). Soft FK → platform.schools.id. "
            "Users exist at school scope, not just tenant scope."
        ),
    )

    # ── Authentication Credentials ────────────────────────────────────────────
    username = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Unique login username within the school scope",
    )
    email = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Optional email. Used for password reset and notifications.",
    )
    phone = Column(
        String(20),
        nullable=True,
        index=True,
        comment="Optional phone number. Used for SMS OTP.",
    )
    password_hash = Column(
        Text,
        nullable=False,
        comment="Argon2id hash of the password",
    )
    password_salt = Column(
        Text,
        nullable=False,
        comment="Unique per-user cryptographic salt",
    )

    # ── User Type ─────────────────────────────────────────────────────────────
    user_type = Column(
        String(30),
        nullable=False,
        index=True,
        comment=(
            "Broad user category. Determines which domain service holds "
            "their business profile. "
            "STUDENT | TEACHER | PARENT | ADMIN | SUPER_ADMIN | STAFF"
        ),
    )

    # ── Display Identity (minimal — no business data) ─────────────────────────
    display_name = Column(
        String(255),
        nullable=False,
        comment=(
            "Human-readable name shown in UI. Synced from domain service "
            "profile on creation. E.g. 'Rahul Sharma'"
        ),
    )
    avatar_url = Column(
        Text,
        nullable=True,
        comment="Profile picture CDN URL (from Media Service)",
    )

    # ── Preferences ───────────────────────────────────────────────────────────
    language_preference = Column(
        String(10),
        nullable=False,
        default="en",
        comment="ISO 639-1 language code. E.g. 'en', 'hi', 'ta'",
    )
    timezone = Column(
        String(50),
        nullable=False,
        default="Asia/Kolkata",
        comment="User timezone for displaying timestamps",
    )

    # ── Account Status ────────────────────────────────────────────────────────
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="False = account disabled (deactivated by admin)",
    )
    is_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True after email/phone OTP verification",
    )
    is_locked = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True after too many failed login attempts",
    )
    is_password_expired = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True when password has passed its expiry date",
    )
    must_change_password = Column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "True on first login — user must set their own password "
            "before accessing the system."
        ),
    )

    # ── Login Security ─────────────────────────────────────────────────────────
    failed_login_attempts = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Consecutive failed login attempts since last success",
    )
    last_login_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of most recent successful login",
    )
    last_login_ip = Column(
        String(45),
        nullable=True,
        comment="IP address of most recent successful login (IPv4 or IPv6)",
    )
    last_password_change_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the user last changed their password",
    )
    password_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp after which the password must be changed",
    )
    account_locked_until = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Lockout expiry. Null = not locked or permanent lock.",
    )
    email_verified_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When email OTP was verified. Null = not verified.",
    )
    phone_verified_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When phone OTP was verified. Null = not verified.",
    )

    # ── Two-Factor Authentication ─────────────────────────────────────────────
    two_factor_enabled = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether 2FA is enabled for this user",
    )
    two_factor_method = Column(
        String(10),
        nullable=True,
        comment="Active 2FA method: SMS | EMAIL | TOTP",
    )

    # ── Flexible Storage ──────────────────────────────────────────────────────
    extra_metadata = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Extensible key-value store for future fields. "
            "E.g. {sso_google_sub: '...', impersonated_from: '...'}"
        ),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user_roles = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="UserRole.user_id",
    )
    sessions = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    mfa_settings = relationship(
        "UserMFA",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    devices = relationship(
        "UserDevice",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    login_history = relationship(
        "UserLoginHistory",
        back_populates="user",
        foreign_keys="UserLoginHistory.user_id",
    )
    password_resets = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    password_history = relationship(
        "PasswordHistory",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="PasswordHistory.user_id",
    )

    def __repr__(self) -> str:
        return (
            f"<User username={self.username!r} "
            f"type={self.user_type} "
            f"school_id={self.school_id}>"
        )
