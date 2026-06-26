"""Plan model — immutable product catalog.

Plans are never updated in place.  Old plans are archived (``is_active=False``)
and new plans are created.  This preserves historical pricing fidelity.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SAEnum,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from base import Base
from enums import PlanType, PlanVariant


class Plan(Base):
    """Immutable product catalog entry.

    Defines a plan tier (CORE / GROWTH), pricing variant (ENTRY / SCALABLE),
    allowed user counts, tenure, and per-user pricing.
    """

    __tablename__ = "plans"
    __table_args__ = (
        # Deactivated plans cannot be publicly listed
        CheckConstraint(
            "NOT (is_active = FALSE AND is_public = TRUE)",
            name="active_before_public",
        ),
        # Tenure boundary: 1–60 months
        CheckConstraint(
            "tenure_months > 0 AND tenure_months <= 60",
            name="valid_tenure_range",
        ),
        # Positive pricing
        CheckConstraint(
            "price_per_user_per_month > 0",
            name="positive_price",
        ),
        # Non-empty allowed user counts
        CheckConstraint(
            "jsonb_array_length(allowed_user_counts) > 0",
            name="non_empty_user_counts",
        ),
        # Unique plan name among live plans
        Index(
            "uq_plans_name_active",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        # Storefront query index
        Index(
            "ix_plans_type_variant_active",
            "plan_type",
            "plan_variant",
            postgresql_where=text("is_active = TRUE AND deleted_at IS NULL"),
        ),
    )

    # ── Columns ──────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    plan_type: Mapped[PlanType] = mapped_column(
        SAEnum(
            PlanType,
            name="plan_type",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
    )
    plan_variant: Mapped[PlanVariant] = mapped_column(
        SAEnum(
            PlanVariant,
            name="plan_variant",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
    )
    allowed_user_counts: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        comment="Sorted array of valid max_user_count values, e.g. [25, 50, 100]",
    )
    tenure_months: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )
    price_per_user_per_month: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
        comment=(
            "Controls public visibility on the pricing page. "
            "TRUE = visible to all visitors. FALSE = hidden, admin-assignable only "
            "(e.g. custom enterprise deals, internal pilot plans). "
            "CHECK constraint prevents is_public=TRUE when is_active=FALSE."
        ),
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    features: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        comment="Feature flag list, e.g. ['attendance', 'gradebook', 'transport']",
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment=(
            "Extensible plan attributes. "
            "Expected keys: internal_code (str), sales_team (str), "
            "launch_date (str, ISO 8601), sunset_date (str|null), "
            "display_order (int), badge (str, e.g. 'most-popular'). "
            "Governed by application-layer Pydantic validation."
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Plan id={self.id!s} name={self.name!r} "
            f"type={self.plan_type.value} variant={self.plan_variant.value}>"
        )
