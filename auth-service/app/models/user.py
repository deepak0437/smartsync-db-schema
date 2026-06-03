"""
Auth Service — User Models

Three tables. One file. One concern per table.

┌─────────────────────────────────────────────────────────────────────┐
│                       auth.users                                    │
│  Identity anchor — rarely changes after creation                    │
│  username · email · phone · display_name · is_active · 2FA flags   │
├─────────────────────────────────────────────────────────────────────┤
│                   auth.user_credentials                             │
│  Password state — changes only on reset / expiry                    │
│  password_hash · password_salt · must_change · expires_at           │
├─────────────────────────────────────────────────────────────────────┤
│                    auth.user_security                               │
│  Live counters — changes on every failed login attempt              │
│  failed_login_attempts · is_locked · locked_until · last_login_*   │
└─────────────────────────────────────────────────────────────────────┘

Why three tables instead of one?
---------------------------------
Postgres uses MVCC (Multi-Version Concurrency Control).
Every UPDATE creates a new full row version — the old version stays
on disk until VACUUM cleans it up.

  - users: login, display_name, email almost never change.
    Low-churn. Fits perfectly in buffer cache. Rarely bloated.

  - user_credentials: password_hash changes maybe once a year.
    Separating it means password resets don't bloat the identity row.

  - user_security: failed_login_attempts resets on every login.
    At 500,000 users with brute-force protection this table gets
    a lot of tiny writes. Keeping it separate means those rapid
    counter updates never bloat the identity or password rows.

Login hot-path (read):
    Two queries — users + user_security (or a single JOIN, still fast).
    Credentials only fetched after username/lock checks pass.

No user_type column:
    Removed. The primary UserRole record tells you the person's
    category (STUDENT, TEACHER, etc.). The API layer reads the
    primary role to route profile fetches to the right domain service.

Multi-Tenancy:
    Users are scoped to (tenant_id, school_id).
    A parent with children in two schools has two rows in each table.

No public signup:
    All users created by School Admin.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE 1 — USERS
# Identity anchor. Rarely mutated after creation.
# ═══════════════════════════════════════════════════════════════════════════════

class User(BaseModel):
    """
    Identity record — one row per person per school.

    Holds only stable identity fields:
        - Login handle (username)
        - Contact channels (email, phone)
        - Display name and avatar
        - Account active flag
        - 2FA on/off state (secrets live in user_mfa)

    Does NOT hold:
        - Password fields         → user_credentials
        - Failed attempt counters → user_security
        - Business data           → domain services (academic, hr, etc.)

    Username conventions (set at creation, never changed):
        STUDENT  → Admission Number   ADM-2024-001
        TEACHER  → Employee Code      EMP-0042
        PARENT   → System-generated   PAR-20240901-7391
        ADMIN    → Assigned by staff  admin.greenvalley
        STAFF    → Employee Code      STF-0019
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
        # Primary login lookup
        Index("ix_auth_user_login", "school_id", "username", "is_deleted"),
        # List all active users in a school
        Index("ix_auth_user_school_active", "school_id", "is_active", "is_deleted"),
        {
            "schema": "auth",
            "comment": (
                "User identity anchor. One row per person per school. "
                "Low-churn: only stable identity fields. "
                "Credentials and security counters are in satellite tables."
            ),
        },
    )

    # ── Scoping ────────────────────────────────────────────────────────────────
    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment=(
            "Org boundary. Soft FK → platform.tenants.id. "
            "No hard FK — avoid cross-service constraint."
        ),
    )
    school_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment=(
            "School boundary. Soft FK → platform.schools.id. "
            "RBAC and billing are scoped here, not at tenant level."
        ),
    )

    # ── Login Handle ──────────────────────────────────────────────────────────
    username = Column(
        String(100),
        nullable=False,
        comment="Unique login handle within the school. Immutable after creation.",
    )

    # ── Contact Channels ──────────────────────────────────────────────────────
    email = Column(
        String(255),
        nullable=True,
        comment="Optional. Used for password reset and notifications.",
    )
    phone = Column(
        String(20),
        nullable=True,
        index=True,
        comment="Optional. Used for SMS OTP.",
    )

    # ── Display ───────────────────────────────────────────────────────────────
    display_name = Column(
        String(255),
        nullable=False,
        comment=(
            "Name shown in UI. Synced from domain service at creation. "
            "E.g. 'Rahul Sharma'. Not the legal-name source of truth."
        ),
    )
    avatar_url = Column(
        Text,
        nullable=True,
        comment="CDN URL of profile picture. Managed by media-service.",
    )

    # ── Account Gate ──────────────────────────────────────────────────────────
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="False = deactivated by admin. User cannot log in.",
    )
    is_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True after email or phone OTP is confirmed.",
    )
    email_verified_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    phone_verified_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── 2FA State Flags ───────────────────────────────────────────────────────
    # Flags live here (read on every login). Secrets live in user_mfa.
    two_factor_enabled = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="2FA is enabled. Check user_mfa for the active secret.",
    )
    two_factor_method = Column(
        String(10),
        nullable=True,
        comment="Active 2FA channel: SMS | EMAIL | TOTP. Null if disabled.",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    credentials = relationship(
        "UserCredentials",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="select",
    )
    security = relationship(
        "UserSecurity",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="select",
    )
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
    mfa_configs = relationship(
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
            f"school_id={self.school_id} "
            f"active={self.is_active}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE 2 — USER CREDENTIALS
# Password state. Changes only on reset / expiry. Low write frequency.
# ═══════════════════════════════════════════════════════════════════════════════

class UserCredentials(BaseModel):
    """
    Password hash and policy state — one row per user.

    Separated from users so password resets don't cause MVCC bloat
    on the identity row. Password changes ~1-2 times per year per user.

    The password_hash uses Argon2id. The salt is embedded in the hash
    string by the Argon2id spec, but stored separately here for explicit
    access during verification.

    This row is fetched AFTER the lock-check passes in user_security.
    If the account is locked, we never touch this table at all.
    """

    __tablename__ = "user_credentials"
    __table_args__ = {
        "schema": "auth",
        "comment": (
            "Password hash and policy flags. 1-to-1 with users. "
            "Separated to prevent password resets bloating the identity row."
        ),
    }

    # ── Parent FK ─────────────────────────────────────────────────────────────
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="FK → auth.users.id",
    )

    # ── Password Hash ─────────────────────────────────────────────────────────
    password_hash = Column(
        Text,
        nullable=False,
        comment=(
            "Argon2id hash of the password. "
            "Format: $argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>"
        ),
    )
    password_salt = Column(
        Text,
        nullable=False,
        comment="Per-user salt. Embedded in Argon2id output but stored explicitly.",
    )

    # ── Password Policy ───────────────────────────────────────────────────────
    must_change_password = Column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "True on first login or after admin reset. "
            "User must set a new password before accessing the system."
        ),
    )
    is_password_expired = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True when password has passed its expiry date.",
    )
    password_changed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the user last changed their password.",
    )
    password_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the current password expires. Null = no expiry policy.",
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    user = relationship(
        "User",
        back_populates="credentials",
        foreign_keys=[user_id],
    )

    def __repr__(self) -> str:
        return (
            f"<UserCredentials user_id={self.user_id} "
            f"expired={self.is_password_expired} "
            f"must_change={self.must_change_password}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE 3 — USER SECURITY
# Live counters. Updated on every login attempt. High write frequency.
# ═══════════════════════════════════════════════════════════════════════════════

class UserSecurity(BaseModel):
    """
    Brute-force protection counters and lock state — one row per user.

    This is the MOST frequently written table in the auth service.
    failed_login_attempts is incremented on every failed attempt and
    reset to 0 on every success. At 500K users, keeping these small
    integer updates isolated means the MVCC dead-tuple bloat from
    these rapid writes stays on this narrow table, not on the wide
    users row.

    Login sequence:
        1. SELECT users WHERE username = ? AND school_id = ?    (users)
        2. SELECT * FROM user_security WHERE user_id = ?        (this table)
           → if is_locked AND locked_until > NOW(): reject early
        3. SELECT password_hash FROM user_credentials ...       (credentials)
           → verify password
        4. On success: reset failed_login_attempts, set last_login_*
        5. On failure: increment failed_login_attempts, maybe set is_locked
    """

    __tablename__ = "user_security"
    __table_args__ = (
        Index("ix_auth_user_security_locked", "is_locked", "locked_until"),
        {
            "schema": "auth",
            "comment": (
                "Brute-force protection state. 1-to-1 with users. "
                "High-churn: updated on every login attempt. "
                "Separated to prevent rapid writes bloating the identity row."
            ),
        },
    )

    # ── Parent FK ─────────────────────────────────────────────────────────────
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="FK → auth.users.id",
    )

    # ── Brute-Force Counters ──────────────────────────────────────────────────
    failed_login_attempts = Column(
        Integer,
        nullable=False,
        default=0,
        comment=(
            "Consecutive failures since last success. "
            "Reset to 0 on success. "
            "Triggers lock when it exceeds the school's threshold (default: 5)."
        ),
    )
    is_locked = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="True = account is locked. Check locked_until for auto-unlock time.",
    )
    locked_until = Column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "When the lock expires. "
            "Null = not locked, or permanent admin-lock. "
            "If locked_until < NOW() the lock is lifted automatically."
        ),
    )

    # ── Last Login Snapshot ───────────────────────────────────────────────────
    last_login_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of most recent successful login.",
    )
    last_login_ip = Column(
        String(45),
        nullable=True,
        comment="IP of most recent successful login. IPv4 or IPv6.",
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    user = relationship(
        "User",
        back_populates="security",
        foreign_keys=[user_id],
    )

    def __repr__(self) -> str:
        return (
            f"<UserSecurity user_id={self.user_id} "
            f"locked={self.is_locked} "
            f"attempts={self.failed_login_attempts}>"
        )
