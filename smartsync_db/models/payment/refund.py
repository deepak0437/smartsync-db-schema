"""Refund model — records payment refund requests and status."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smartsync_db.base import Base, AuditMixin
from .enums import RefundStatus

if TYPE_CHECKING:
    from .payment import Payment


class Refund(AuditMixin, Base):
    """Refund transaction record."""

    __tablename__ = "refunds"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_refunds_amount_non_negative"),
        Index("ix_refunds_payment_id", "payment_id"),
        Index(
            "uq_refunds_gateway_refund_id",
            "gateway_refund_id",
            unique=True,
            postgresql_where=text("gateway_refund_id IS NOT NULL"),
        ),
        Index("ix_refunds_status", "status"),
        {"schema": "payment"},
    )

    payment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("payment.payments.id", name="fk_refunds_payment_id"),
        nullable=False,
    )

    gateway_refund_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[RefundStatus] = mapped_column(
        SAEnum(RefundStatus, name="refund_status", schema="payment", create_type=False),
        nullable=False,
        default=RefundStatus.REQUESTED,
        server_default=text("'REQUESTED'"),
    )

    requested_by: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Soft FK -> auth.users.id. The platform admin who requested the refund.",
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    payment: Mapped["Payment"] = relationship(
        "Payment",
        back_populates="refunds",
    )

    def __repr__(self) -> str:
        return f"<Refund id={self.id!s} status={self.status.value} amount={self.amount!s}>"
