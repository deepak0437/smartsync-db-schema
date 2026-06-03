"""
Auth Service — Session, MFA, Device & Password Models

Tables in this file
-------------------
UserSession         Active JWT / refresh token sessions
UserMFA             MFA secret storage (TOTP, backup codes — cold, sensitive)
UserDevice          Trusted device registry (skip MFA on known devices)
UserLoginHistory    Login attempt audit trail (append-only, high-volume)
PasswordResetToken  Short-lived tokens for the password reset flow
PasswordHistory     Previous password hashes for reuse-prevention policy

Separation rationale
--------------------
These tables are all correctly separated from auth.users because:

  UserSession      → Written/read frequently, but only for the session-owner.
                     Partitioned by tenant. Expire-and-delete strategy.

  UserMFA          → Contains TOTP base32 secret (encrypted at rest).
                     Read only during 2FA verification, not on every login.
                     The *state* (is_enabled, method) lives in users table.

  UserDevice       → Rarely read (only on first login from a new device).

  UserLoginHistory → Append-only audit log. Very high write volume.
                     Will be partitioned by month in production.
                     Never part of the auth hot-path.

  PasswordResetToken → Short-lived (15 min TTL). Tiny table.

  PasswordHistory  → Checked only during password change, not during login.
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


# ═══════════════════════════════════════════════════════════════════════════════
# USER SESSION
# ═══════════════════════════════════════════════════════════════════════════════

class UserSession(BaseModel):
    """
    One active authenticated session per device per user.

    Lifecycle:
        Created  → on successful login (+ MFA if enabled)
        Updated  → last_activity_at refreshed on each API call
        Expired  → when expires_at passes or refresh_token_expires_at passes
        Revoked  → on logout, password change, account lock, or admin action

    Token storage:
        The raw JWT is NEVER stored. We store a SHA-256 hash so that
        a database breach does not yield usable tokens.

    Concurrent session limit:
        Enforced at the application layer (query count before creating new session).
        Configurable per tenant (default: 5 sessions per user).
    """

    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_auth_session_user_active", "user_id", "is_active"),
        Index("ix_auth_session_school_active", "school_id", "is_active"),
        Index("ix_auth_session_expires", "expires_at"),
        {
            "schema": "auth",
            "comment": "Active user sessions. One row per login per device.",
        },
    )

    # ── Scoping ────────────────────────────────────────────────────────────────
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    school_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Token References ───────────────────────────────────────────────────────
    session_token_hash = Column(
        Text,
        unique=True,
        nullable=False,
        index=True,
        comment=(
            "SHA-256 hash of the JWT access token. "
            "Raw token is never stored. "
            "Used to validate incoming tokens and revoke sessions."
        ),
    )
    refresh_token_hash = Column(
        Text,
        unique=True,
        nullable=True,
        index=True,
        comment=(
            "SHA-256 hash of the refresh token. "
            "Null if refresh tokens are not used for this session."
        ),
    )

    # ── Device Context ─────────────────────────────────────────────────────────
    device_id = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Client-generated device fingerprint or hardware ID.",
    )
    device_name = Column(
        String(255),
        nullable=True,
        comment="Human-readable device name. E.g. 'Chrome on Windows 11'",
    )
    device_type = Column(
        String(20),
        nullable=True,
        comment="WEB | MOBILE | TABLET | DESKTOP",
    )
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)

    # ── Network Context ────────────────────────────────────────────────────────
    ip_address = Column(
        String(45),
        nullable=True,
        index=True,
        comment="Client IP at login time. IPv4 or IPv6.",
    )
    user_agent = Column(Text, nullable=True)

    # ── Location (GeoIP — no PostGIS required) ─────────────────────────────────
    location_country = Column(String(100), nullable=True)
    location_city = Column(String(100), nullable=True)

    # ── Session State ──────────────────────────────────────────────────────────
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    is_trusted_device = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True = device is in UserDevice trusted registry. Skip MFA next time.",
    )

    # ── Timestamps ─────────────────────────────────────────────────────────────
    last_activity_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Updated on each authenticated API request. Used for idle timeout.",
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Access token expiry. Default: 8 hours from login.",
    )
    refresh_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Refresh token expiry. Default: 30 days from login. Null = no refresh.",
    )

    # ── Relationship ───────────────────────────────────────────────────────────
    user = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return (
            f"<UserSession user_id={self.user_id} "
            f"device={self.device_type!r} active={self.is_active}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# USER MFA
# ═══════════════════════════════════════════════════════════════════════════════

class UserMFA(BaseModel):
    """
    MFA secret storage per user per method.

    One row per method the user has enrolled.
    A user might have both TOTP and SMS enrolled (primary + backup).

    The is_enabled / method flags live in auth.users for fast login checks.
    This table holds the secrets — read only during 2FA verification.

    Security:
        mfa_secret (TOTP base32 key) MUST be encrypted at rest
        using application-level encryption before storing.
    """

    __tablename__ = "user_mfa"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "mfa_method",
            name="uq_auth_user_mfa_method",
        ),
        Index("ix_auth_user_mfa_user", "user_id", "is_active"),
        {
            "schema": "auth",
            "comment": (
                "MFA secret storage. One row per method per user. "
                "TOTP secrets encrypted at rest."
            ),
        },
    )

    # ── Scoping ────────────────────────────────────────────────────────────────
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Method & Secrets ───────────────────────────────────────────────────────
    mfa_method = Column(
        String(20),
        nullable=False,
        comment="SMS | EMAIL | TOTP | BACKUP_CODES",
    )
    mfa_secret = Column(
        Text,
        nullable=True,
        comment=(
            "TOTP base32 secret. Encrypted at rest with app-level key. "
            "Null for SMS and EMAIL methods."
        ),
    )
    phone_number = Column(
        String(20),
        nullable=True,
        comment="Destination phone for SMS OTP. Null for TOTP.",
    )
    email_address = Column(
        String(255),
        nullable=True,
        comment="Destination email for EMAIL OTP. Null for TOTP.",
    )
    backup_codes = Column(
        JSONB,
        nullable=False,
        default=list,
        comment="Array of hashed one-time backup codes. Each used code removed.",
    )

    # ── Enrollment State ───────────────────────────────────────────────────────
    is_primary = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True = this is the user's primary 2FA method.",
    )
    is_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True after user successfully completes first verification.",
    )
    verified_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # ── Relationship ───────────────────────────────────────────────────────────
    user = relationship("User", back_populates="mfa_configs")

    def __repr__(self) -> str:
        return (
            f"<UserMFA user_id={self.user_id} "
            f"method={self.mfa_method!r} primary={self.is_primary}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# USER DEVICE
# ═══════════════════════════════════════════════════════════════════════════════

class UserDevice(BaseModel):
    """
    Trusted device registry.

    When a device is trusted, 2FA is skipped on subsequent logins from it.
    Trust is granted manually by the user or automatically based on policy.

    On login: check if device_id is in this table with is_trusted = True.
    If found → set session.is_trusted_device = True → skip 2FA step.
    """

    __tablename__ = "user_devices"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "device_id",
            name="uq_auth_user_device",
        ),
        Index("ix_auth_user_device_lookup", "user_id", "device_id", "is_trusted"),
        {
            "schema": "auth",
            "comment": "Trusted device registry. Devices here skip 2FA on login.",
        },
    )

    # ── Scoping ────────────────────────────────────────────────────────────────
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Device Identification ──────────────────────────────────────────────────
    device_id = Column(
        String(255),
        nullable=False,
        comment="Client-generated device fingerprint. Must be stable across sessions.",
    )
    device_name = Column(
        String(255),
        nullable=True,
        comment="Human-readable label. E.g. 'Chrome on MacBook Pro'",
    )
    device_type = Column(
        String(20),
        nullable=True,
        comment="WEB | MOBILE | TABLET | DESKTOP",
    )
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    os_version = Column(String(50), nullable=True)
    app_version = Column(String(50), nullable=True, comment="Mobile app version if applicable")

    # ── Trust Status ───────────────────────────────────────────────────────────
    is_trusted = Column(Boolean, nullable=False, default=False)
    trusted_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_ip = Column(String(45), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # ── Relationship ───────────────────────────────────────────────────────────
    user = relationship("User", back_populates="devices")

    def __repr__(self) -> str:
        return (
            f"<UserDevice user_id={self.user_id} "
            f"device={self.device_name!r} trusted={self.is_trusted}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# USER LOGIN HISTORY
# ═══════════════════════════════════════════════════════════════════════════════

class UserLoginHistory(BaseModel):
    """
    Append-only audit trail of every login attempt.

    Records both successes and failures. Immutable once written.

    High-volume table — partition by month in production:
        CREATE TABLE user_login_history_2024_01 PARTITION OF user_login_history
        FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

    user_id is nullable (SET NULL) so failed attempts for unknown usernames
    are still recorded for security monitoring even without a user_id.
    """

    __tablename__ = "user_login_history"
    __table_args__ = (
        Index("ix_auth_login_history_user", "user_id", "created_at"),
        Index("ix_auth_login_history_school", "school_id", "created_at"),
        Index("ix_auth_login_history_ip", "ip_address", "created_at"),
        {
            "schema": "auth",
            "comment": (
                "Login attempt audit trail. Append-only. "
                "Partition by month in production for performance."
            ),
        },
    )

    # ── Scoping ────────────────────────────────────────────────────────────────
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    school_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Null for failed attempts with unknown username.",
    )

    # ── Attempt Details ────────────────────────────────────────────────────────
    username_attempted = Column(
        String(100),
        nullable=True,
        comment="Raw username as typed. Useful for detecting enumeration attacks.",
    )
    login_status = Column(
        String(20),
        nullable=False,
        index=True,
        comment="SUCCESS | FAILED | BLOCKED | MFA_REQUIRED | MFA_FAILED",
    )
    failure_reason = Column(
        String(100),
        nullable=True,
        comment="WRONG_PASSWORD | USER_NOT_FOUND | ACCOUNT_LOCKED | ACCOUNT_INACTIVE | MFA_FAILED",
    )

    # ── Network & Device ───────────────────────────────────────────────────────
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    device_type = Column(String(20), nullable=True)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    location_country = Column(String(100), nullable=True)
    location_city = Column(String(100), nullable=True)

    # ── MFA Context ────────────────────────────────────────────────────────────
    mfa_used = Column(Boolean, nullable=False, default=False)
    mfa_method = Column(String(20), nullable=True)

    # ── Session Reference ──────────────────────────────────────────────────────
    session_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="FK → user_sessions.id for successful logins.",
    )

    # ── Relationship ───────────────────────────────────────────────────────────
    user = relationship(
        "User",
        back_populates="login_history",
        foreign_keys=[user_id],
    )

    def __repr__(self) -> str:
        return (
            f"<UserLoginHistory username={self.username_attempted!r} "
            f"status={self.login_status}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PASSWORD RESET TOKEN
# ═══════════════════════════════════════════════════════════════════════════════

class PasswordResetToken(BaseModel):
    """
    Short-lived token for the password reset flow.

    Flow:
        1. User requests reset (by email or phone).
        2. System creates this row with a 15-minute expiry.
        3. System sends token to user's email/phone (raw token, not the hash).
        4. User submits token → we hash it, look it up, verify expiry.
        5. Password updated → is_used = True, used_at = now().

    Security:
        The raw token is NEVER stored. Only a SHA-256 hash.
        Only one active (unused, unexpired) token per user should exist —
        enforced at the application layer before creation.
    """

    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("ix_auth_prt_user_active", "user_id", "is_used", "expires_at"),
        {
            "schema": "auth",
            "comment": "Short-lived password reset tokens. 15-minute TTL.",
        },
    )

    # ── Scoping ────────────────────────────────────────────────────────────────
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Token ──────────────────────────────────────────────────────────────────
    token_hash = Column(
        Text,
        unique=True,
        nullable=False,
        index=True,
        comment="SHA-256 hash of the reset token sent to user.",
    )
    delivery_channel = Column(
        String(10),
        nullable=False,
        comment="How the token was delivered: EMAIL | SMS",
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Token becomes invalid after this time. Default: 15 minutes.",
    )

    # ── Usage State ────────────────────────────────────────────────────────────
    is_used = Column(Boolean, nullable=False, default=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    # ── Request Context ────────────────────────────────────────────────────────
    requested_from_ip = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # ── Relationship ───────────────────────────────────────────────────────────
    user = relationship("User", back_populates="password_resets")

    def __repr__(self) -> str:
        return (
            f"<PasswordResetToken user_id={self.user_id} "
            f"used={self.is_used} expires={self.expires_at}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PASSWORD HISTORY
# ═══════════════════════════════════════════════════════════════════════════════

class PasswordHistory(BaseModel):
    """
    Previous password hashes for reuse-prevention policy.

    On each password change, the old hash is saved here.
    When user sets a new password, the new hash is checked against the last N rows
    (N is configurable per tenant, default: 5).

    Only the hash is stored — the raw password never appears here.
    """

    __tablename__ = "password_history"
    __table_args__ = (
        Index("ix_auth_pw_history_user", "user_id", "created_at"),
        {
            "schema": "auth",
            "comment": "Previous password hashes. Used to prevent reuse of recent passwords.",
        },
    )

    # ── Scoping ────────────────────────────────────────────────────────────────
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Stored Hash ────────────────────────────────────────────────────────────
    password_hash = Column(
        Text,
        nullable=False,
        comment="Argon2id hash of the previous password.",
    )
    password_salt = Column(
        Text,
        nullable=False,
        comment="Salt used with this hash.",
    )

    # ── Change Metadata ────────────────────────────────────────────────────────
    changed_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=True,
        comment="Who triggered the change: the user themselves or an admin.",
    )
    change_reason = Column(
        String(30),
        nullable=True,
        comment="USER_INITIATED | ADMIN_RESET | EXPIRED | FIRST_LOGIN",
    )
    changed_from_ip = Column(String(45), nullable=True)

    # ── Relationship ───────────────────────────────────────────────────────────
    user = relationship(
        "User",
        back_populates="password_history",
        foreign_keys=[user_id],
    )

    def __repr__(self) -> str:
        return (
            f"<PasswordHistory user_id={self.user_id} "
            f"reason={self.change_reason!r}>"
        )
