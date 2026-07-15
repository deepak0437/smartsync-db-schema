"""PaymentOrder model — checkout records prior to gateway involvement."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum as SAEnum,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smartsync_db.base import Base, AuditMixin
from .enums import PaymentOrderStatus

if TYPE_CHECKING:
    from .payment import Payment


class PaymentOrder(AuditMixin, Base):
    """Business-level checkout attempt record.

    Created before any gateway involvement, one row per checkout attempt.
    A prospect may retry payment against the same order — each attempt is
    its own :class:`Payment` row (see ``payments`` below).
    """

    __tablename__ = "payment_orders"
    __table_args__ = (
        CheckConstraint("subtotal_amount >= 0", name="chk_payment_orders_subtotal"),
        CheckConstraint("discount_amount >= 0", name="chk_payment_orders_discount"),
        CheckConstraint("tax_amount >= 0", name="chk_payment_orders_tax"),
        CheckConstraint("total_amount >= 0", name="chk_payment_orders_total"),
        Index("ix_payment_orders_mobile_number", "mobile_number"),
        Index("ix_payment_orders_plan_id", "plan_id"),
        Index(
            "uq_payment_orders_gateway_order_id",
            "gateway_order_id",
            unique=True,
            postgresql_where=text("gateway_order_id IS NOT NULL"),
        ),
        Index("ix_payment_orders_status_created_at", "status", "created_at"),
        {"schema": "payment"},
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    mobile_number: Mapped[str] = mapped_column(String(20), nullable=False)
    school_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    plan_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Soft FK -> platform.plans.id. No hard FK across service database boundaries.",
    )
    addon_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Soft FK -> platform.expansion_addons.id. No hard FK across service database boundaries.",
    )

    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    gateway_order_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[PaymentOrderStatus] = mapped_column(
        SAEnum(PaymentOrderStatus, name="payment_order_status", schema="payment", create_type=False),
        nullable=False,
        default=PaymentOrderStatus.PENDING,
        server_default=text("'PENDING'"),
    )

    # ── Relationships ────────────────────────────────────────────────────
    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="payment_order",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PaymentOrder id={self.id!s} status={self.status.value} total={self.total_amount!s}>"
