"""PaymentWebhook model — logs raw incoming gateway webhooks for audit and idempotency."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from smartsync_db.base import Base, AuditMixin
from .enums import PaymentGateway


class PaymentWebhook(AuditMixin, Base):
    """Raw, append-only webhook inbox — the idempotency source of truth for
    gateway retries. ``uq_payment_webhooks_gateway_event_id`` is the concrete
    mechanism: insert-or-ignore on delivery, only ever process a given event
    once even if the gateway retries it.
    """

    __tablename__ = "payment_webhooks"
    __table_args__ = (
        Index(
            "uq_payment_webhooks_gateway_event_id",
            "gateway",
            "event_id",
            unique=True,
        ),
        Index("ix_payment_webhooks_event_type", "event_type"),
        {"schema": "payment"},
    )

    gateway: Mapped[PaymentGateway] = mapped_column(
        SAEnum(PaymentGateway, name="payment_gateway", schema="payment", create_type=False),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    signature: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    processed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<PaymentWebhook id={self.id!s} gateway={self.gateway.value} event={self.event_type}>"
