"""
Communication Service Models — Announcements, circulars, messages, threads.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey
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


class Announcement(BaseModel):
    """School-wide or targeted announcements."""
    __tablename__ = "announcements"
    __table_args__ = {"schema": "communication"}
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    announcement_type = Column(String(30), nullable=False, comment="GENERAL | ACADEMIC | EXAM | SPORTS | CULTURAL | HOLIDAY | EMERGENCY")
    priority = Column(String(10), default="NORMAL", comment="LOW | NORMAL | HIGH | URGENT")
    published_by_user_id = Column(UUID(as_uuid=True), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    target_audience = Column(JSONB, default={"all": True}, comment="Target: {all: true} or {roles: [], classes: [], sections: []}")
    attachments = Column(JSONB, default=[], comment="Array of {file_name, file_url}")
    is_pinned = Column(Boolean, default=False)
    status = Column(String(20), default="DRAFT", comment="DRAFT | PUBLISHED | ARCHIVED | EXPIRED")
    extra_metadata = Column(JSONB, default={})
    reads = relationship("AnnouncementRead", back_populates="announcement")


class AnnouncementRead(BaseModel):
    """Tracks who has read each announcement."""
    __tablename__ = "announcement_reads"
    __table_args__ = {"schema": "communication"}
    announcement_id = Column(UUID(as_uuid=True), ForeignKey("communication.announcements.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=False)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    announcement = relationship("Announcement", back_populates="reads")


class Circular(BaseModel):
    """Official school circulars/notices."""
    __tablename__ = "circulars"
    __table_args__ = {"schema": "communication"}
    circular_number = Column(String(50), nullable=False, unique=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    circular_type = Column(String(30), nullable=False, comment="ACADEMIC | ADMINISTRATIVE | EXAM | HOLIDAY | FEE | GENERAL")
    issued_by_user_id = Column(UUID(as_uuid=True), nullable=False)
    issued_date = Column(DateTime(timezone=True), nullable=False)
    target_audience = Column(JSONB, default={"all": True})
    attachment_urls = Column(JSONB, default=[])
    requires_acknowledgment = Column(Boolean, default=False)
    acknowledgment_deadline = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="PUBLISHED")
    extra_metadata = Column(JSONB, default={})


class MessageThread(BaseModel):
    """Parent-teacher or admin-parent message thread."""
    __tablename__ = "message_threads"
    __table_args__ = {"schema": "communication"}
    subject = Column(String(500), nullable=False)
    thread_type = Column(String(30), nullable=False, comment="PARENT_TEACHER | ADMIN_PARENT | TEACHER_HOD | GENERAL")
    initiator_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    recipient_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), nullable=True, comment="Optional: about which student")
    status = Column(String(20), default="ACTIVE", comment="ACTIVE | CLOSED | ARCHIVED")
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    unread_count_initiator = Column(Integer, default=0)
    unread_count_recipient = Column(Integer, default=0)
    extra_metadata = Column(JSONB, default={})
    messages = relationship("Message", back_populates="thread")


class Message(BaseModel):
    """Individual message within a thread."""
    __tablename__ = "messages"
    __table_args__ = {"schema": "communication"}
    thread_id = Column(UUID(as_uuid=True), ForeignKey("communication.message_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    message_text = Column(Text, nullable=False)
    attachments = Column(JSONB, default=[])
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime(timezone=True), nullable=True)
    extra_metadata = Column(JSONB, default={})
    thread = relationship("MessageThread", back_populates="messages")


class NoticeBoard(BaseModel):
    """Digital notice board posts."""
    __tablename__ = "notice_board"
    __table_args__ = {"schema": "communication"}
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(30), nullable=False, comment="LOST_AND_FOUND | FOR_SALE | JOBS | EVENTS | GENERAL")
    posted_by_user_id = Column(UUID(as_uuid=True), nullable=False)
    target_audience = Column(JSONB, default={"all": True})
    expires_at = Column(DateTime(timezone=True), nullable=True)
    attachment_urls = Column(JSONB, default=[])
    is_approved = Column(Boolean, default=False)
    approved_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(String(20), default="PENDING", comment="PENDING | APPROVED | REJECTED | EXPIRED")
    extra_metadata = Column(JSONB, default={})
