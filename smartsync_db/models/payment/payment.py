"""Payment model — records gateway payment attempts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smartsync_db.base import Base, AuditMixin
from .enums import PaymentGateway, PaymentMethod, PaymentStatus

if TYPE_CHECKING:
    from .invoice import Invoice
    from .payment_order import PaymentOrder
    from .payment_transaction import PaymentTransaction
    from .refund import Refund


class Payment(AuditMixin, Base):
    """One gateway payment attempt against a :class:`PaymentOrder`.

    Supports retries — a prospect can abandon the checkout widget and
    re-attempt; each attempt gets its own row against the same order.
    """

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_payments_amount_non_negative"),
        CheckConstraint(
            "gateway_fee IS NULL OR gateway_fee >= 0",
            name="chk_payments_gateway_fee_non_negative",
        ),
        CheckConstraint(
            "tax_amount IS NULL OR tax_amount >= 0",
            name="chk_payments_tax_amount_non_negative",
        ),
        Index("ix_payments_payment_order_id", "payment_order_id"),
        Index(
            "uq_payments_gateway_payment_id",
            "gateway_payment_id",
            unique=True,
            postgresql_where=text("gateway_payment_id IS NOT NULL"),
        ),
        Index("ix_payments_payment_status", "payment_status"),
        Index("ix_payments_paid_at", "paid_at"),
        {"schema": "payment"},
    )

    payment_order_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("payment.payment_orders.id", name="fk_payments_payment_order_id"),
        nullable=False,
    )

    gateway: Mapped[PaymentGateway] = mapped_column(
        SAEnum(PaymentGateway, name="payment_gateway", schema="payment", create_type=False),
        nullable=False,
    )

    gateway_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(
        SAEnum(PaymentMethod, name="payment_method", schema="payment", create_type=False),
        nullable=True,
    )

    payment_status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status", schema="payment", create_type=False),
        nullable=False,
        default=PaymentStatus.INITIATED,
        server_default=text("'INITIATED'"),
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="INR", server_default=text("'INR'")
    )

    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    gateway_fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    tax_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    gateway_response: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    payment_order: Mapped["PaymentOrder"] = relationship(
        "PaymentOrder",
        back_populates="payments",
    )
    transactions: Mapped[List["PaymentTransaction"]] = relationship(
        "PaymentTransaction",
        back_populates="payment",
        lazy="selectin",
    )
    invoice: Mapped[Optional["Invoice"]] = relationship(
        "Invoice",
        back_populates="payment",
        uselist=False,
    )
    refunds: Mapped[List["Refund"]] = relationship(
        "Refund",
        back_populates="payment",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Payment id={self.id!s} status={self.payment_status.value} amount={self.amount!s}>"
