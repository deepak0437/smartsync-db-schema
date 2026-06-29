"""
Auth & RBAC Service — User Identity Models
============================================
File: app/models/user.py

WHAT THIS FILE BELONGS TO
--------------------------
This file is part of the **Auth & RBAC Service**. It defines the complete
identity layer for every human who logs into SmartSync — students, parents,
teachers, HODs, school admins, and platform admins alike. One row in `users`
exists per login-capable person per school.

This file does NOT contain:
  - Role definitions, permissions, or role assignments (see roles.py — discussed separately)
  - Business profile data (a student's class/section lives in Academic Service,
    a teacher's department lives in HR Service — never here)

SCHEMA SEPARATION RATIONALE
-----------------------------
The single flat `users` table you originally listed mixes three workloads with
very different read/write patterns. Splitting them into four tables is not
over-engineering — it is what makes the most frequent operation (login) fast
and lock-free against the least frequent operation (profile lookup).

    ┌─────────────────────┬──────────────────────────┬───────────────────────┐
    │ Table                │ Written                  │ Read                  │
    ├─────────────────────┼──────────────────────────┼───────────────────────┤
    │ User                 │ Rarely (signup, profile  │ Constantly — every    │
    │                      │ edit)                    │ request needs name,   │
    │                      │                          │ email, school_id      │
    ├─────────────────────┼──────────────────────────┼───────────────────────┤
    │ UserCredentials      │ Every login attempt      │ Only at login time    │
    │                      │ (failed_login_attempts,  │                       │
    │                      │ last_login_at), every    │                       │
    │                      │ password change          │                       │
    ├─────────────────────┼──────────────────────────┼───────────────────────┤
    │ UserVerification     │ Once per channel (email  │ Rarely — only during  │
    │                      │ verify, phone verify)    │ verification flow     │
    ├─────────────────────┼──────────────────────────┼───────────────────────┤
    │ UserLoginHistory     │ Every single login       │ Almost never — only   │
    │                      │ attempt (success/fail)   │ security audits       │
    └─────────────────────┴──────────────────────────┴───────────────────────┘

Why this matters for performance:
  - A profile page request (GET /users/me) only touches `users`. It never
    locks rows that a concurrent login attempt is updating in `user_credentials`.
  - `user_login_history` is insert-only and grows fast (millions of rows at
    scale). Keeping it separate means it never bloats the `users` table's
    row size, which would otherwise slow down every single SELECT on `users`.
  - `password_hash` is the single most sensitive column in the entire service.
    Isolating it in `user_credentials` means a accidental `SELECT *` on `users`
    in application code can never leak a password hash into a log or API
    response — the column simply isn't there.

REFRESH TOKEN — WHY IT IS NOT A COLUMN HERE
---------------------------------------------
Your original column list included `refresh_token` as a single column on the
user row. This does not survive multi-device login (a teacher logged in on
both their phone and laptop would overwrite each other's token). Refresh
tokens belong in the session/device model (`session.py`, covered separately
in this service) where one row exists per active device/session, not one
column per user. This file does not define that table.

PASSWORD DELIVERY FLOW (per your requirement)
------------------------------------------------
School admin creates a user → system generates a random alphanumeric
password → password is sent via email + SMS → `must_change_password = True`
is set → on first successful login, the user is forced through the change
password flow before reaching their dashboard. No reset link is used for the
very first password (your instinct that a link is awkward for a young
student user is correct — a typed temporary password is simpler on a school
shared/parent device). Reset *links* are still used later for forgotten
password recovery (see endpoint list below), since at that point the user
already has a verified email to receive the link on.

ALL MODELS IN THIS FILE
-------------------------
    User               → users table              (identity, profile)
    UserCredentials    → user_credentials table    (password, lockout, login security)
    UserVerification   → user_verifications table   (email/phone verification status)
    UserLoginHistory    → user_login_history table   (append-only login audit trail)
"""

from __future__ import annotations

import datetime
import enum
import uuid
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from smartsync_db.base import Base, SoftDeleteMixin, AuditMixin

if TYPE_CHECKING:
    from .session import UserSession, UserOTP
    from .role import UserRole
   

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class LoginFailureReason(str, enum.Enum):
    """
    Classifies why a login attempt failed. Stored on UserLoginHistory.
    Used for security analytics (e.g. detecting brute-force patterns) and
    for showing the user a precise-enough-but-not-too-precise error message.
    """
    BAD_PASSWORD = "BAD_PASSWORD"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    PASSWORD_EXPIRED = "PASSWORD_EXPIRED"
    OTP_INVALID = "OTP_INVALID"
    OTP_EXPIRED = "OTP_EXPIRED"


# ═══════════════════════════════════════════════════════════════════════════════
# USER — Identity & Profile (read-heavy, write-rare)
# ═══════════════════════════════════════════════════════════════════════════════

class User(Base):
    """
    Central identity record. One row per login-capable person per school.

    A person with children in two different schools (e.g. a parent) gets
    TWO separate User rows — one per (tenant_id, school_id) scope — never
    one row shared across schools. This keeps every authorization decision
    scoped to a single school without cross-school leakage risk.

    This table is intentionally "thin." It holds only what is needed to:
      a) identify who this person is (name, contact info)
      b) know which tenant/school they belong to
      c) render their profile in a UI (photo, display name)

    It holds NO password, NO verification status, NO login security state —
    those live in the sibling tables below, looked up only when actually
    needed (i.e. at login time, not on every profile page view).

    Username convention (set once at creation, never changed):
        STUDENT      → Admission Number   (e.g. "ADM-2024-001")
        TEACHER/STAFF → Employee Code     (e.g. "EMP-0042")
        PARENT       → Phone number or auto-generated "PAR-0091"
        SCHOOL_ADMIN → Email prefix or platform-assigned
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "school_id", "username", name="uq_users_tenant_school_username"),
        UniqueConstraint("tenant_id", "school_id", "email", name="uq_users_tenant_school_email"),
        UniqueConstraint("tenant_id", "school_id", "mobile_number", name="uq_users_tenant_school_mobile"),
        Index("idx_users_tenant_school", "tenant_id", "school_id"),
        Index("idx_users_tenant_school_active", "tenant_id", "school_id", "is_active"),
        Index("idx_users_name", "last_name", "first_name"),
        {
            "comment": (
                "Central identity table. One row per user per school. "
                "Holds profile/contact info only — no password, no login security state."
            ),
            "schema": "auth",
        },
    )

    # ── Tenant & School Scoping ────────────────────────────────────────────────
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
        comment=(
            "Owning tenant. Soft FK → platform.tenants.id (no hard FK across "
            "service database boundaries)."
        ),
    )
    school_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
        comment="Owning school. Soft FK → platform.schools.id.",
    )

    # ── Login Identity ─────────────────────────────────────────────────────────
    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment=(
            "Unique login handle within (tenant_id, school_id). Set once at "
            "creation by the school admin or onboarding flow. Never changed "
            "after creation — see PATCH /users/:id/username being intentionally "
            "absent from the endpoint list below."
        ),
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment=(
            "Contact + recovery email. Nullable because young students may not "
            "have one — in that case a parent's email is typically used for "
            "notifications instead, tracked at the Academic Service profile level."
        ),
    )
    mobile_number: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="E.164 format, e.g. '+919876543210'. Used for SMS OTP and password delivery.",
    )

    # ── Profile ────────────────────────────────────────────────────────────────
    first_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="Given name.")
    middle_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="Optional middle name.")
    last_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="Family/surname.")

    # ── Status ────────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment=(
            "False = account disabled by school admin (does not delete the row; "
            "use is_deleted from BaseModel for actual removal)."
            "True for every admin-created user at creation time. Forces the "
            "mandatory change-password step on first successful login before "
            "any other endpoint becomes accessible. Set to False once the "
            "user completes their first self-chosen password."
        ),
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment=(
            "Derived/cached flag: True only when at least the primary contact "
            "channel (email OR mobile, per tenant policy) is verified. The "
            "authoritative per-channel state lives on UserVerification — this "
            "column exists purely so list/filter queries on `users` don't need "
            "a join to UserVerification for the common case."
        ),
    )

   # ── Relationships ──────────────────────────────────────────────────────────
    credentials: Mapped[Optional["UserCredentials"]] = relationship(
        "UserCredentials",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    verification: Mapped[Optional["UserVerification"]] = relationship(
        "UserVerification",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    otps: Mapped[List["UserOTP"]] = relationship(
        "UserOTP",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    tokens: Mapped[List["UserToken"]] = relationship(
        "UserToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    user_role: Mapped[Optional["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} school_id={self.school_id}>"


# ═══════════════════════════════════════════════════════════════════════════════
# USER CREDENTIALS — Password & Login Security (write-heavy, narrow read)
# ═══════════════════════════════════════════════════════════════════════════════

class UserCredentials(Base):
    """
    Password and login-security state for one user. Strict 1-to-1 with User.

    This table absorbs every write that happens on EVERY login attempt
    (success or failure) — failed_login_attempt increments, last_login_at
    updates, is_locked toggles. By isolating these hot writes here, a
    profile read (`SELECT * FROM users WHERE id = ...`) never contends with
    a concurrent login attempt's row lock on this table.

    password_hash is the only column in the entire service that should ever
    contain password material, and it is always a hash (Argon2id), never
    plaintext. The random alphanumeric password generated at user creation
    time is hashed before this row is even written — it exists in plaintext
    only transiently in the email/SMS dispatch payload, never persisted.
    """

    __tablename__ = "user_credentials"
    __table_args__ = (
        {
            "comment": (
                "1-to-1 with users. Password hash and all login-security "
                "counters. Isolated so login writes never lock profile reads."
            ),
            "schema": "auth",
        },
    )

    # ── Link ──────────────────────────────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="FK → users.id. Unique enforces strict 1-to-1.",
    )

    # ── Password ──────────────────────────────────────────────────────────────
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment=(
            "Argon2id hash of the current password. The school-admin-generated "
            "random alphanumeric temporary password is hashed into this field "
            "immediately on user creation — never stored in plaintext anywhere."
        ),
    )
    password_expired_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Timestamp after which the password must be changed (tenant-level "
            "password-age policy, if enabled). NULL = no expiry enforced."
        ),
    )
    password_changed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the password was last changed by the user themselves.",
    )
    password_change_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        comment="Lifetime count of password changes. Useful for security analytics.",
    )
    
    # max session ──────────────────────────────────────────────────────────────
    max_concurrent_sessions: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        default=None,
        comment=(
            "Per-user override for max concurrent sessions. "
            "NULL = use tenant default. Checked at login time before creating "
            "a new session row. If user already has N active sessions and "
            "this limit is reached, oldest session is revoked (or login is blocked "
            "based on tenant policy)."
        ),
    )

    # ── Login Security / Lockout ──────────────────────────────────────────────
    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment=(
            "True after failed_login_attempt crosses the configured threshold. "
            "Blocks login entirely until unlocked by admin or lockout window "
            "elapses (see locked_until)."
        ),
    )
    locked_until: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Auto-unlock timestamp for time-based lockouts (e.g. 15-minute "
            "lockout after 5 failed attempts). NULL with is_locked=True means "
            "a permanent lock requiring manual admin unlock."
        ),
    )
    failed_login_attempt: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        comment="Consecutive failed attempts since the last successful login. Resets to 0 on success.",
    )

    # ── Last Successful Login ─────────────────────────────────────────────────
    last_login_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the most recent successful login.",
    )
    last_login_ip: Mapped[Optional[str]] = mapped_column(
        INET,
        nullable=True,
        comment="IP address of the most recent successful login.",
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="credentials")

    def __repr__(self) -> str:
        return f"<UserCredentials user_id={self.user_id} locked={self.is_locked}>"


# ═══════════════════════════════════════════════════════════════════════════════
# USER ONBOARDING & PASSWORD RESET
# ═══════════════════════════════════════════════════════════════════════════════

class UserToken(Base):
    """
    Short-lived single-use token for onboarding (set password) and 
    password reset flows. One row per issued token.
    Deleted immediately after use.
    """

    __tablename__ = "user_tokens"
    __table_args__ = (
        Index("idx_user_token_jti", "jti"),
        {
            "comment": "Single-use tokens for onboarding and password reset links.",
            "schema": "auth",
        },
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    jti: Mapped[str] = mapped_column(
        String(36),  # UUID
        nullable=False,
        unique=True,
        comment="JWT ID. Used for single-use enforcement and revocation.",
    )
    purpose: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="ONBOARDING | PASSWORD_RESET",
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Token hard expiry. 48hr for onboarding, 1hr for password reset.",
    )
    used_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When token was consumed. NULL = not yet used.",
    )
    
    user: Mapped["User"] = relationship("User", back_populates="tokens")


# ═══════════════════════════════════════════════════════════════════════════════
# USER VERIFICATION — Email & Mobile Verification State
# ═══════════════════════════════════════════════════════════════════════════════

class UserVerification(Base):
    """
    Tracks email and mobile verification independently, since a user may
    verify one channel before (or without ever verifying) the other.

    Kept separate from UserCredentials deliberately: verification is a
    once-per-channel write event, while credentials absorb a write on
    every login attempt. Mixing them would mean a verification-status
    read takes on lock contention from unrelated login traffic.

    The actual OTP codes / verification tokens sent to the user are NOT
    stored here — they live in a short-lived, TTL-backed Redis key (or a
    dedicated otp_requests table if durability across Redis restarts is
    required). This table only records the OUTCOME (verified yes/no, when).
    """

    __tablename__ = "user_verifications"
    __table_args__ = (
        {
            "comment": (
                "1-to-1 with users. Per-channel verification outcome only — "
                "OTP codes themselves live in Redis, not here."
            ),
            "schema": "auth",
        },
    )

    # ── Link ──────────────────────────────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="FK → users.id. Unique enforces strict 1-to-1.",
    )

    # ── Email Verification ────────────────────────────────────────────────────
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True once the user has confirmed access to the email on their User row.",
    )
    email_verified_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When email verification completed.",
    )

    # ── Mobile Verification ───────────────────────────────────────────────────
    mobile_number_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True once the user has confirmed access to the mobile number via OTP.",
    )
    mobile_number_verified_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When mobile verification completed.",
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="verification")

    def __repr__(self) -> str:
        return (
            f"<UserVerification user_id={self.user_id} "
            f"email={self.email_verified} mobile={self.mobile_number_verified}>"
        )

