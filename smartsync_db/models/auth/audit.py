"""
API keys, IP whitelist, audit logs and event outbox models.
"""
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from smartsync_db.base import Base, SoftDeleteMixin, AuditMixin 



class APIKey(SoftDeleteMixin, AuditMixin, Base):
    """
    API keys for service-to-service authentication and external integrations.
    Key value is NEVER stored — only a SHA-256 hash is persisted.
    """
    __tablename__ = "api_keys"
    __table_args__ = {
        "comment": "Service-to-service and integration API keys",
        "schema": "auth",
    }

    # Foreign Keys
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="Owning tenant. Soft FK -> platform.tenants.id")

    # Key Information
    key_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Human-readable key name")
    key_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True, comment="SHA-256 hash of the actual API key")
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False, comment="First 8 chars for UI identification (ss_xxxx...)")

    # Service context
    service_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Calling service name (e.g. academic-service)")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Scopes
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=[], comment="Allowed permission scopes")

    # Rate Limiting
    rate_limit_per_hour: Mapped[int] = mapped_column(Integer, default=1000, comment="Requests per hour limit")

    # IP Allowlist
    allowed_ips: Mapped[list[str]] = mapped_column(ARRAY(Text), default=[], comment="Allowed source IPs (empty = all allowed)")

    # Expiry
    expires_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="Key expiry (null = never expires)")

    # Usage tracking
    last_used_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)

    # Extra Metadata
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<APIKey(name={self.key_name}, service={self.service_name})>"


class IPWhitelist(SoftDeleteMixin, AuditMixin, Base):
    """
    IP address whitelist for tenant-level access control.
    Restricts logins to specific IPs or ranges.
    """
    __tablename__ = "ip_whitelist"
    __table_args__ = {"comment": "IP whitelist for tenant access control"}

    # Foreign Keys
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="Owning tenant. Soft FK -> platform.tenants.id")

    # IP Information
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True, comment="Single IP address (IPv4 or IPv6)")
    cidr_notation: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="CIDR range e.g. 192.168.1.0/24")
    ip_range_start: Mapped[str | None] = mapped_column(String(45), nullable=True, comment="IP range start")
    ip_range_end: Mapped[str | None] = mapped_column(String(45), nullable=True, comment="IP range end")

    # Description
    label: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Human-readable label e.g. 'School Campus LAN'")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Added By
    added_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.users.id"), nullable=True)

    # Extra Metadata
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<IPWhitelist(ip={self.ip_address}, cidr={self.cidr_notation})>"


class AuditLog(Base):
    """
    Comprehensive audit trail for all system actions.
    High-volume table — partition by month in production.
    Immutable — records are never updated or deleted.
    """
    __tablename__ = "audit_logs"
    __table_args__ = {"comment": "Immutable audit trail — partitioned by month"}

    # Context
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True, comment="Owning tenant. Soft FK -> platform.tenants.id")
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Action
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="CREATE | UPDATE | DELETE | LOGIN | LOGOUT | APPROVE ...")
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="USER | ROLE | PERMISSION | TENANT ...")
    resource_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)

    # Data snapshots
    old_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, comment="JSON snapshot before change")
    new_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, comment="JSON snapshot after change")

    # Request context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True, comment="Correlation request ID")
    session_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Result
    status: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="SUCCESS | FAILED")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extra Metadata
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})

    def __repr__(self):
        return f"<AuditLog(action={self.action}, resource={self.resource_type})>"


class AuthEvent(Base):
    """
    Transactional Outbox Pattern for reliable event publishing.

    Events are written atomically with the triggering transaction.
    A separate relay process reads unpublished events and publishes to Kafka/RabbitMQ.

    Published events:
    - USER_CREATED, USER_UPDATED, USER_DEACTIVATED, USER_DELETED
    - ROLE_ASSIGNED, ROLE_REVOKED
    - USER_LOGGED_IN, USER_LOGGED_OUT
    - PASSWORD_CHANGED, MFA_ENABLED
    - TENANT_CREATED, TENANT_SUSPENDED
    """
    __tablename__ = "auth_events"
    __table_args__ = {"comment": "Event outbox for reliable async event publishing"}

    # Context
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True, comment="Owning tenant. Soft FK -> platform.tenants.id")

    # Event Information
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="USER_CREATED | ROLE_ASSIGNED | ...")
    event_version: Mapped[str] = mapped_column(String(10), default="1.0", comment="Schema version of event_data")

    # Aggregate
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="USER | ROLE | TENANT")
    aggregate_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="ID of the aggregate root")

    # Payload
    event_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, comment="Full event payload (immutable once written)")

    # Causation chain
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True, comment="User who triggered the event")
    correlation_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True, comment="Groups related events (e.g. one request)")
    causation_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="ID of the event that caused this event")

    # Publishing status
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    published_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="Exponential backoff next retry")

    # Extra Metadata
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})

    def __repr__(self):
        return f"<AuthEvent(type={self.event_type}, aggregate={self.aggregate_type})>"