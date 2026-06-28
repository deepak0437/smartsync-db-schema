"""
Auth & RBAC Service — Session & Password Lifecycle Models
===========================================================
File: app/models/session.py

WHAT THIS FILE BELONGS TO
--------------------------
This file is part of the **Auth & RBAC Service**. It defines the runtime
security layer that surrounds the identity model in `user.py`:

    User (identity)  ←──  UserSession (active JWT sessions)
                     ←──  UserOTP (generic OTP store — verification + reset)

This file does NOT contain:
  - User identity, profile, or contact info (see user.py)
  - Role definitions or permission grants (see roles.py)
  - Login audit trail (see user.py — UserLoginHistory)
  - MFA / 2FA enrollment (not required for this school product)
  - Trusted device registry (not required — no MFA to skip)

WHY NO MFA OR DEVICE TABLES
------------------------------
The school product login flow is deliberately simple:

    Username + Password → Session JWT

There is no OTP, no TOTP, no SMS 2FA, no biometric, no trusted device
bypass. Adding tables for features we will not ship is worse than adding
them later when needed — unused columns create migration burden and
confuse new developers reading the schema.

If 2FA is ever added for teachers/admins, these tables can be re-introduced
in a migration at that time.

TOKEN STORAGE
-------------
We NEVER store raw JWTs or raw reset tokens. We store a SHA-256 hash so
that a database breach does not yield usable bearer tokens.
"""

from __future__ import annotations

import datetime
import enum
import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smartsync_db.base import Base, SoftDeleteMixin


if TYPE_CHECKING:
    from .user import User 


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS FOR OTP SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class OTPType(str, enum.Enum):
    """
    Purpose of the OTP.
    
    EMAIL_VERIFY    → Email address verification during signup or email change
    MOBILE_VERIFY   → Mobile number verification during signup or phone change
    PASSWORD_RESET  → Password reset flow (forgot password)
    """
    EMAIL_VERIFY = "EMAIL_VERIFY"
    MOBILE_VERIFY = "MOBILE_VERIFY"
    PASSWORD_RESET = "PASSWORD_RESET"


class OTPChannel(str, enum.Enum):
    """
    Delivery channel for the OTP.
    
    EMAIL → Sent via email service
    SMS   → Sent via SMS gateway (Twilio, AWS SNS, etc.)
    """
    EMAIL = "EMAIL"
    SMS = "SMS"


# ═══════════════════════════════════════════════════════════════════════════════
# USER SESSION — Active JWT / Refresh Token Sessions
# ═══════════════════════════════════════════════════════════════════════════════

class UserSession(Base):
    """
    One active authenticated session per device per user.

    Lifecycle:
        Created  → on successful username + password login
        Updated  → last_activity_at refreshed on each authenticated request
        Expired  → when refresh_expires_at passes
        Revoked  → on logout, password change, account lock, or admin action

    Token storage:
        The raw JWT is NEVER stored. We store a SHA-256 hash so that a
        database breach does not yield usable tokens.

    Concurrent session limit:
        Enforced at the application layer (query count before creating new
        session). Configurable per tenant (default: 5 sessions per user).
    """

    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_auth_session_tenant_school", "tenant_id", "school_id"),
        Index("ix_auth_session_user_active", "user_id", "refresh_expires_at"),
        Index("ix_auth_session_school_active", "school_id", "refresh_expires_at"),
        Index("ix_auth_session_refresh_expires", "refresh_expires_at"),
        {
            "comment": (
                "Active user sessions. One row per login per device. "
                "Refresh tokens live here, not in the users table."
            ),
            "schema": "auth",
        },
    )

    # ── Tenant & School Scoping ────────────────────────────────────────────────
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment=(
            "Owning tenant. Soft FK → platform.tenants.id. "
            "Denormalized here (not joined through users) so that "
            "admin dashboards can list all active sessions in a tenant without "
            "a cross-table join. Required for efficient data isolation queries."
        ),
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment=(
            "Owning school. Soft FK → platform.schools.id. "
            "Denormalized for school-level session analytics and admin dashboards "
            "(e.g., 'active sessions in this school' without joining to users table)."
        ),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK → users.id. CASCADE deletes all sessions when the user is deleted.",
    )

    # ── Token References (hashed, never raw) ───────────────────────────────────
    refresh_token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment=(
            "SHA-256 hash of the opaque refresh token. "
            "The raw refresh token is returned once to the client on login and "
            "is never stored in plaintext. Used by the /auth/refresh endpoint to "
            "issue a new access token and rotate the refresh token."
        ),
    )

    # ── Device Context (minimal) ───────────────────────────────────────────────
    device_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Client-generated device fingerprint. Optional — used for 'log out all devices' and limiting concurrent sessions.",
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Raw User-Agent header from the login request. Shown in 'active sessions' list.",
    )

    # ── Network Context ────────────────────────────────────────────────────────
    ip_address: Mapped[Optional[str]] = mapped_column(
        INET,
        nullable=True,
        comment="Client IP at login time. From request.remote_addr or X-Forwarded-For.",
    )

    # ── Timestamps ─────────────────────────────────────────────────────────────
    last_activity_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Updated on each authenticated API request. Used for idle timeout.",
    )
    refresh_expires_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Refresh token expiry. Default: 30 days from login.",
    )

    # ── Relationship ───────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="sessions")

    def __repr__(self) -> str:
        return (
            f"<UserSession user_id={self.user_id} "
            f"device_id={self.device_id!r} active={getattr(self, 'is_active', None)}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# USER OTP — Generic One-Time Password Storage
# ═══════════════════════════════════════════════════════════════════════════════

class UserOTP(Base):
    """
    Generic OTP storage for all verification and password-reset flows.

    Redis is the primary delivery and validation layer (fast, TTL-backed),
    but this table is the **durable source of truth** for:
      a) Attempt tracking and brute-force blocking
      b) Redis failure fallback (query this table if Redis is down)
      c) Audit trail of what was sent to whom and when

    Flow (Redis as primary):
        1. Generate 6-digit OTP + store hash in Redis (TTL = 5 min).
        2. INSERT row here with code_hash, expires_at, attempts_used = 0.
        3. Send OTP to user via email/SMS.
        4. User submits OTP → check Redis first (fast path).
        5. If Redis miss (or Redis down) → check this table (slow path).
        6. On success → mark is_used = True, update used_at.
        7. On failure → increment attempts_used, possibly block.

    Flow (Redis completely unavailable):
        1. Same as above, but steps 4-5 skip Redis and query this table directly.
        2. The table is indexed on (user_id, otp_type, is_used) for fast lookup.

    Why a single generic table instead of separate tables per flow:
        - All flows share the same pattern: generate, send, attempt, verify, expire.
        - Brute-force protection (attempts, blocking) is identical across flows.
        - One query path for Redis fallback, one admin dashboard for "all OTPs sent".
    """

    __tablename__ = "user_otps"
    __table_args__ = (
        Index("ix_auth_otp_user_type", "user_id", "otp_type", "is_used"),
        Index("ix_auth_otp_expires", "expires_at"),
        Index("ix_auth_otp_target", "target_address", "created_at"),
        Index("ix_auth_otp_tenant_school", "tenant_id", "school_id", "created_at"),
        {
            "comment": (
                "Generic OTP store. Redis is primary; this is the durable fallback "
                "and attempt-tracking source of truth."
            ),
            "schema": "auth",
        },
    )

    # ── Tenant & School Scoping ────────────────────────────────────────────────
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment=(
            "Owning tenant. Soft FK → platform.tenants.id. "
            "Denormalized here for efficient multi-tenant queries and data isolation."
        ),
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment=(
            "Owning school. Soft FK → platform.schools.id. "
            "Denormalized for admin dashboards and school-level OTP analytics."
        ),
    )

    # ── Link ───────────────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK → users.id. CASCADE deletes OTP rows when the user is deleted.",
    )

    # ── OTP Type & Target ──────────────────────────────────────────────────────
    otp_type: Mapped[OTPType] = mapped_column(
        Enum(OTPType, name="otp_type_enum", schema="auth"),
        nullable=False,
        comment=(
            "Purpose of this OTP. "
            "EMAIL_VERIFY    → Email verification during signup or email change. "
            "MOBILE_VERIFY   → Mobile number verification during signup or phone change. "
            "PASSWORD_RESET  → Password reset flow (forgot password)."
        ),
    )
    target_channel: Mapped[OTPChannel] = mapped_column(
        Enum(OTPChannel, name="otp_channel_enum", schema="auth"),
        nullable=False,
        comment=(
            "Delivery channel for this OTP. "
            "EMAIL → Sent via email service. "
            "SMS   → Sent via SMS gateway (Twilio, AWS SNS, etc.)."
        ),
    )
    target_address: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment=(
            "The email address or mobile number the OTP was sent to. "
            "Kept for audit even if the user later changes their email/mobile. "
            "Format: email@example.com for EMAIL, +919876543210 for SMS."
        ),
    )

    # ── Code Security ──────────────────────────────────────────────────────────
    code_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment=(
            "SHA-256 hash of the OTP code. The raw 6-digit code is returned once "
            "to the delivery channel (email/SMS) and is never stored in plaintext."
        ),
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="OTP is invalid after this time. Default: 5 minutes from creation.",
    )

    # ── Attempt Tracking & Brute-Force Protection ────────────────────────────────
    attempts_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of wrong OTP attempts submitted by the user. Resets to 0 on success.",
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        comment="Maximum allowed attempts before the OTP is blocked. Configurable per tenant.",
    )
    is_blocked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True after attempts_used >= max_attempts. Blocks further validation attempts.",
    )
    blocked_until: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Cooldown timestamp after which the user can request a new OTP. "
            "NULL if not blocked. Default cooldown: 15 minutes."
        ),
    )

    # ── Usage State ────────────────────────────────────────────────────────────
    is_used: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="True once the OTP has been successfully validated and consumed.",
    )
    used_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the OTP was successfully consumed.",
    )

    # ── Request Context ────────────────────────────────────────────────────────
    ip_address: Mapped[Optional[str]] = mapped_column(
        INET,
        nullable=True,
        comment="IP address of the client that requested the OTP.",
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="User-Agent from the OTP request.",
    )

    # ── Relationship ───────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="otps")

    def __repr__(self) -> str:
        return (
            f"<UserOTP user_id={self.user_id} "
            f"type={self.otp_type!r} channel={self.target_channel!r}>"
        )
