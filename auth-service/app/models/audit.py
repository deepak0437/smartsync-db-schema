"""
API keys, IP whitelist, audit logs and event outbox models.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class APIKey(BaseModel):
    """
    API keys for service-to-service authentication and external integrations.
    Key value is NEVER stored — only a SHA-256 hash is persisted.
    """
    __tablename__ = "api_keys"
    __table_args__ = {"schema": "auth", "comment": "Service-to-service and integration API keys"}

    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Key Information
    key_name = Column(String(255), nullable=False, comment="Human-readable key name")
    key_hash = Column(Text, unique=True, nullable=False, index=True, comment="SHA-256 hash of the actual API key")
    key_prefix = Column(String(20), nullable=False, comment="First 8 chars for UI identification (ss_xxxx...)")

    # Service context
    service_name = Column(String(100), nullable=True, comment="Calling service name (e.g. academic-service)")
    description = Column(Text, nullable=True)

    # Scopes
    scopes = Column(ARRAY(Text), default=[], comment="Allowed permission scopes")

    # Rate Limiting
    rate_limit_per_hour = Column(Integer, default=1000, comment="Requests per hour limit")

    # IP Allowlist
    allowed_ips = Column(ARRAY(Text), default=[], comment="Allowed source IPs (empty = all allowed)")

    # Expiry
    expires_at = Column(DateTime(timezone=True), nullable=True, comment="Key expiry (null = never expires)")

    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0)

    # Extra Metadata
    extra_metadata = Column(JSONB, default={})
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<APIKey(name={self.key_name}, service={self.service_name})>"


class IPWhitelist(BaseModel):
    """
    IP address whitelist for tenant-level access control.
    Restricts logins to specific IPs or ranges.
    """
    __tablename__ = "ip_whitelist"
    __table_args__ = {"schema": "auth", "comment": "IP whitelist for tenant access control"}

    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # IP Information
    ip_address = Column(String(45), nullable=True, index=True, comment="Single IP address (IPv4 or IPv6)")
    cidr_notation = Column(String(50), nullable=True, comment="CIDR range e.g. 192.168.1.0/24")
    ip_range_start = Column(String(45), nullable=True, comment="IP range start")
    ip_range_end = Column(String(45), nullable=True, comment="IP range end")

    # Description
    label = Column(String(255), nullable=True, comment="Human-readable label e.g. 'School Campus LAN'")
    description = Column(Text, nullable=True)

    # Added By
    added_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=True)

    # Extra Metadata
    extra_metadata = Column(JSONB, default={})
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<IPWhitelist(ip={self.ip_address}, cidr={self.cidr_notation})>"


class AuditLog(BaseModel):
    """
    Comprehensive audit trail for all system actions.
    High-volume table — partition by month in production.
    Immutable — records are never updated or deleted.
    """
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "auth", "comment": "Immutable audit trail — partitioned by month"}

    # Context
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Action
    action = Column(String(100), nullable=False, index=True, comment="CREATE | UPDATE | DELETE | LOGIN | LOGOUT | APPROVE ...")
    resource_type = Column(String(100), nullable=False, index=True, comment="USER | ROLE | PERMISSION | TENANT ...")
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Data snapshots
    old_values = Column(JSONB, nullable=True, comment="JSON snapshot before change")
    new_values = Column(JSONB, nullable=True, comment="JSON snapshot after change")

    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(100), nullable=True, index=True, comment="Correlation request ID")
    session_id = Column(UUID(as_uuid=True), nullable=True)

    # Result
    status = Column(String(20), nullable=True, comment="SUCCESS | FAILED")
    error_message = Column(Text, nullable=True)

    # Extra Metadata
    extra_metadata = Column(JSONB, default={})

    def __repr__(self):
        return f"<AuditLog(action={self.action}, resource={self.resource_type})>"


class AuthEvent(BaseModel):
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
    __table_args__ = {"schema": "auth", "comment": "Event outbox for reliable async event publishing"}

    # Context
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=True, index=True)

    # Event Information
    event_type = Column(String(100), nullable=False, index=True, comment="USER_CREATED | ROLE_ASSIGNED | ...")
    event_version = Column(String(10), default="1.0", comment="Schema version of event_data")

    # Aggregate
    aggregate_type = Column(String(100), nullable=False, index=True, comment="USER | ROLE | TENANT")
    aggregate_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="ID of the aggregate root")

    # Payload
    event_data = Column(JSONB, nullable=False, comment="Full event payload (immutable once written)")

    # Causation chain
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True, comment="User who triggered the event")
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True, comment="Groups related events (e.g. one request)")
    causation_id = Column(UUID(as_uuid=True), nullable=True, comment="ID of the event that caused this event")

    # Publishing status
    is_published = Column(Boolean, default=False, nullable=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True, comment="Exponential backoff next retry")

    # Extra Metadata
    extra_metadata = Column(JSONB, default={})

    def __repr__(self):
        return f"<AuthEvent(type={self.event_type}, aggregate={self.aggregate_type})>"
