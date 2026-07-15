"""PaymentTransaction model — money ledger auditing transactions."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smartsync_db.base import Base, AuditMixin
from .enums import TransactionType, TransactionStatus

if TYPE_CHECKING:
    from .payment import Payment


class PaymentTransaction(AuditMixin, Base):
    """Immutable ledger entry of money movement against a payment.

    Plays the same role for financial state changes that ``auth.auth_events``
    plays for identity events — this table **is** the audit trail, never
    updated or deleted once written.
    """

    __tablename__ = "payment_transactions"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_payment_transactions_amount_non_negative"),
        Index("ix_payment_transactions_payment_id", "payment_id"),
        Index("ix_payment_transactions_type", "transaction_type"),
        Index("ix_payment_transactions_gateway_transaction_id", "gateway_transaction_id"),
        {"schema": "payment"},
    )

    payment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("payment.payments.id", name="fk_payment_transactions_payment_id"),
        nullable=False,
    )

    transaction_type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType, name="transaction_type", schema="payment", create_type=False),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    status: Mapped[TransactionStatus] = mapped_column(
        SAEnum(TransactionStatus, name="transaction_status", schema="payment", create_type=False),
        nullable=False,
    )

    gateway_transaction_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    payment: Mapped["Payment"] = relationship(
        "Payment",
        back_populates="transactions",
    )

    def __repr__(self) -> str:
        return f"<PaymentTransaction id={self.id!s} type={self.transaction_type.value} amount={self.amount!s}>"
