"""EmailTemplate model — reusable subject+body content admins can save and
reuse from the Platform > Emails > Compose screen.

Distinct from smartsync-notification-service's own filesystem Jinja2
templates (transactional, developer-maintained: welcome, password_reset,
payment_confirmation, ...). These rows are admin-authored HTML content,
owned by platform-service, with zero involvement from notification-service
beyond the one generic `admin_broadcast` template that wraps whichever
EmailTemplate/ad-hoc content is being sent.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from smartsync_db.base import Base, SoftDeleteMixin, AuditMixin


class EmailTemplate(SoftDeleteMixin, AuditMixin, Base):
    """A saved, reusable subject+body pair for Compose to prefill from."""

    __tablename__ = "email_templates"
    __table_args__ = (
        Index(
            "uq_email_templates_name_active",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"schema": "platform"},
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Admin-facing template name, unique among non-deleted templates",
    )

    subject: Mapped[str] = mapped_column(String(500), nullable=False)

    body_html: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Rich-text-editor HTML, rendered as-is (marked `| safe`) into admin_broadcast",
    )

    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<EmailTemplate id={self.id!s} name={self.name!r}>"
