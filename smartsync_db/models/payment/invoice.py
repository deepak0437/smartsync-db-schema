"""Invoice model — records billing details and generated receipt references."""

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
from .enums import InvoiceStatus

if TYPE_CHECKING:
    from .payment import Payment


class Invoice(AuditMixin, Base):
    """Billing and payment invoice record. One invoice per successful payment."""

    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="chk_invoices_subtotal_non_negative"),
        CheckConstraint("discount >= 0", name="chk_invoices_discount_non_negative"),
        CheckConstraint("tax >= 0", name="chk_invoices_tax_non_negative"),
        CheckConstraint("total >= 0", name="chk_invoices_total_non_negative"),
        Index("uq_invoices_invoice_number", "invoice_number", unique=True),
        Index("uq_invoices_payment_id", "payment_id", unique=True),
        Index("ix_invoices_school_id", "school_id"),
        {"schema": "payment"},
    )

    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)

    payment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("payment.payments.id", name="fk_invoices_payment_id"),
        nullable=False,
    )

    school_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment=(
            "Soft FK -> platform.schools.id. Nullable because the school may not "
            "exist yet at invoice-generation time (checkout precedes onboarding)."
        ),
    )

    billing_name: Mapped[str] = mapped_column(String(255), nullable=False)
    billing_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    billing_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gst_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    tax: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    invoice_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    status: Mapped[InvoiceStatus] = mapped_column(
        SAEnum(InvoiceStatus, name="invoice_status", schema="payment", create_type=False),
        nullable=False,
        default=InvoiceStatus.ISSUED,
        server_default=text("'ISSUED'"),
    )

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # ── Relationships ────────────────────────────────────────────────────
    payment: Mapped["Payment"] = relationship(
        "Payment",
        back_populates="invoice",
    )

    def __repr__(self) -> str:
        return f"<Invoice id={self.id!s} number={self.invoice_number} total={self.total!s}>"
