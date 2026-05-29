"""
Notification Service Models — Templates, logs, push tokens, preferences.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from uuid import uuid4
from sqlalchemy import func


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)


class NotificationTemplate(BaseModel):
    """Notification templates for all event types."""
    __tablename__ = "notification_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "template_code", "channel", name="uq_notif_template"),
        {"schema": "notification"},
    )
    template_code = Column(String(100), nullable=False)
    template_name = Column(String(255), nullable=False)
    channel = Column(String(20), nullable=False, comment="EMAIL | SMS | PUSH | IN_APP | WHATSAPP")
    event_type = Column(String(100), nullable=False, comment="Event that triggers this notification")
    subject = Column(String(500), nullable=True, comment="Email subject (with variables)")
    body = Column(Text, nullable=False, comment="Template body with {{variable}} placeholders")
    available_variables = Column(JSONB, default=[], comment="List of available template variables")
    language = Column(String(10), default="en")
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class NotificationLog(BaseModel):
    """Log of all sent notifications."""
    __tablename__ = "notification_logs"
    __table_args__ = {"schema": "notification"}
    template_id = Column(UUID(as_uuid=True), ForeignKey("notification.notification_templates.id", ondelete="SET NULL"), nullable=True)
    recipient_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    channel = Column(String(20), nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    recipient_email = Column(String(255), nullable=True)
    recipient_phone = Column(String(20), nullable=True)
    recipient_device_token = Column(Text, nullable=True)
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=False)
    status = Column(String(20), default="PENDING", comment="PENDING | SENT | DELIVERED | FAILED | BOUNCED")
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    external_message_id = Column(String(255), nullable=True, comment="Provider message ID (SMS gateway, FCM, etc.)")
    retry_count = Column(Integer, default=0)
    related_entity_type = Column(String(50), nullable=True, comment="HOMEWORK | REVIEW | ATTENDANCE | ...")
    related_entity_id = Column(UUID(as_uuid=True), nullable=True)
    extra_metadata = Column(JSONB, default={})


class PushToken(BaseModel):
    """Device push notification tokens (FCM/APNs)."""
    __tablename__ = "push_tokens"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "device_token", name="uq_notif_push_token"),
        {"schema": "notification"},
    )
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    device_token = Column(Text, nullable=False)
    platform = Column(String(10), nullable=False, comment="ANDROID | IOS | WEB")
    app_version = Column(String(20), nullable=True)
    device_model = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    extra_metadata = Column(JSONB, default={})


class NotificationPreference(BaseModel):
    """User notification preferences per channel and event type."""
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "event_type", "channel", name="uq_notif_preference"),
        {"schema": "notification"},
    )
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    channel = Column(String(20), nullable=False)
    is_enabled = Column(Boolean, default=True)
    quiet_hours_start = Column(String(5), nullable=True, comment="HH:MM")
    quiet_hours_end = Column(String(5), nullable=True)
    extra_metadata = Column(JSONB, default={})


class InAppNotification(BaseModel):
    """In-app notification inbox per user."""
    __tablename__ = "in_app_notifications"
    __table_args__ = {"schema": "notification"}
    recipient_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    icon = Column(String(50), nullable=True)
    action_url = Column(Text, nullable=True, comment="Deep link URL for the notification action")
    event_type = Column(String(100), nullable=False)
    related_entity_type = Column(String(50), nullable=True)
    related_entity_id = Column(UUID(as_uuid=True), nullable=True)
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    extra_metadata = Column(JSONB, default={})
