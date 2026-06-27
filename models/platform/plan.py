"""Plan model — immutable product catalog.

Plans are never updated in place.  Old plans are archived (``is_active=False``)
and new plans are created.  This preserves historical pricing fidelity.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SAEnum,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from base import Base, SoftDeleteMixin, AuditMixin
from .enums import PlanType, PlanVariant, TenureMonths, StorageLimit, UserCount


class Plan(SoftDeleteMixin, AuditMixin, Base):
    """Immutable product catalog entry.

    Defines a plan tier (CORE / GROWTH), pricing variant (ENTRY / SCALABLE),
    user counts, tenure, and pricing.
    """

    __tablename__ = "plans"
    __table_args__ = (
        # Positive pricing
        CheckConstraint(
            "price > 0",
            name="positive_price",
        ),
        # Unique plan code among live plans
        Index(
            "uq_plans_code_active",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        # Storefront query index
        Index(
            "ix_plans_type_variant_active",
            "type",
            "variant",
            postgresql_where=text("is_active = TRUE AND deleted_at IS NULL"),
        ),
    )

    # ── Columns ──────────────────────────────────────────────────────────
    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Unique plan code for multi-tenant support"
    )

    type: Mapped[PlanType] = mapped_column(
        SAEnum(
            PlanType,
            name="plan_type",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
    )

    variant: Mapped[PlanVariant] = mapped_column(
        SAEnum(
            PlanVariant,
            name="plan_variant",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
    )
    
    user_count: Mapped[UserCount] = mapped_column(
        SAEnum(
            UserCount,
            name="plan_user_count",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
        comment="Allowed user count for the plan"
    )

    tenure: Mapped[TenureMonths] = mapped_column(
        SAEnum(
            TenureMonths,
            name="plan_tenure",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
        comment="Tenure duration in months"
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Pricing or MRP per user per month"
    )

    discount_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Discounted price per user per month"
    )

    discount_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Discount percentage"
    )

    storage: Mapped[StorageLimit] = mapped_column(
        SAEnum(
            StorageLimit,
            name="storage_limit",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
        comment="Storage limit in GB"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Plan id={self.id!s} code={self.code!r} "
            f"type={self.type.value} variant={self.variant.value}>"
        )

