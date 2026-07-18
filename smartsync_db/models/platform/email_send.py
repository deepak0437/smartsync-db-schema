"""EmailSend / EmailSendRecipient — append-only history of admin-composed
broadcast emails.

A send is immutable once created: `subject`/`body_html` are a snapshot at
send time (never re-rendered from a linked EmailTemplate, so later template
edits never rewrite history). Per-recipient rows track each individual
notification-api call's outcome, refreshed on demand by polling
notification-service's internal status endpoint via `notification_event_id`.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smartsync_db.base import Base
from .enums import EmailRecipientStatus

if TYPE_CHECKING:
    from .email_template import EmailTemplate


class EmailSend(Base):
    """One admin "Send" action — may fan out to many recipients."""

    __tablename__ = "email_sends"
    __table_args__ = (
        CheckConstraint("recipient_count > 0", name="positive_recipient_count"),
        Index("ix_email_sends_sent_by", "sent_by"),
        Index("ix_email_sends_created_at", "created_at"),
        {"schema": "platform"},
    )

    template_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("platform.email_templates.id", ondelete="SET NULL"),
        nullable=True,
        comment="Template this send was composed from, if any — ad-hoc sends leave this null",
    )

    subject: Mapped[str] = mapped_column(String(500), nullable=False)

    body_html: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Snapshot at send time — independent of any later edit to the source template",
    )

    sent_by: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Soft FK -> auth.users.id, no hard FK across service database boundaries",
    )

    recipient_count: Mapped[int] = mapped_column(Integer, nullable=False)

    template: Mapped[Optional["EmailTemplate"]] = relationship(
        "EmailTemplate",
        lazy="noload",
    )
    recipients: Mapped[list["EmailSendRecipient"]] = relationship(
        "EmailSendRecipient",
        back_populates="email_send",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<EmailSend id={self.id!s} subject={self.subject!r} recipients={self.recipient_count!s}>"


class EmailSendRecipient(Base):
    """One recipient's outcome within an EmailSend."""

    __tablename__ = "email_send_recipients"
    __table_args__ = (
        Index("ix_email_send_recipients_email_send_id", "email_send_id"),
        Index("ix_email_send_recipients_event_id", "notification_event_id"),
        {"schema": "platform"},
    )

    email_send_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("platform.email_sends.id", ondelete="CASCADE"),
        nullable=False,
    )

    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)

    recipient_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    notification_event_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="Null means the notification-api publish call itself failed to queue",
    )

    status: Mapped[EmailRecipientStatus] = mapped_column(
        SAEnum(
            EmailRecipientStatus,
            name="email_recipient_status",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
        server_default=EmailRecipientStatus.QUEUED.value,
    )

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    email_send: Mapped["EmailSend"] = relationship(
        "EmailSend",
        back_populates="recipients",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<EmailSendRecipient id={self.id!s} email={self.recipient_email!r} status={self.status.value}>"
