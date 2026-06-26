"""ExpansionAddon model — mid-term capacity booster.

Tied to the active base subscription's remaining tenure.  The addon's
``expires_at`` must be ≤ the parent subscription's ``expires_at`` — this
invariant is enforced at the service layer since cross-table CHECK
constraints are not supported in PostgreSQL.

Once purchased, addons cannot be cancelled — they run until expiry.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.models.enums import AddonStatus

if TYPE_CHECKING:
    from app.models.plan import Plan
    from app.models.school_subscription import SchoolSubscription


class ExpansionAddon(BaseModel):
    """Mid-term capacity booster attached to an active subscription.

    Adds ``additional_user_count`` users to the subscription's
    ``effective_max_users`` for the remaining tenure.
    """

    __tablename__ = "expansion_addons"
    __table_args__ = (
        # ── CHECK constraints ────────────────────────────────────────────
        CheckConstraint(
            "additional_user_count > 0",
            name="positive_addon_users",
        ),
        CheckConstraint(
            "price_per_user_per_month > 0",
            name="positive_addon_price",
        ),
        CheckConstraint(
            "expires_at > starts_at",
            name="addon_expiry_after_start",
        ),
        # ── Indexes ──────────────────────────────────────────────────────
        Index(
            "ix_addons_subscription_active",
            "subscription_id",
            postgresql_where=text("status = 'ACTIVE' AND deleted_at IS NULL"),
        ),
        Index(
            "ix_addons_expires_at_active",
            "expires_at",
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        # Prevent duplicate active addons of the same plan on the same subscription
        Index(
            "uq_addons_subscription_plan_active",
            "subscription_id",
            "plan_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE' AND deleted_at IS NULL"),
        ),
    )

    # ── Columns ──────────────────────────────────────────────────────────
    # create a code column for plan to be used in the future for multi-tenant support(string of 100 characters)
    # expansion_type, expansion_pack, tenure, user_count, discount, discount_percentage, is_active
    subscription_id: Mapped[uuid.UUID] = mapped_column( # not required 
        ForeignKey("subscriptions.id"), 
        nullable=False,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(  # not required 
        ForeignKey("plans.id"),
        nullable=False,
    )
    status: Mapped[AddonStatus] = mapped_column(
        SAEnum(
            AddonStatus,
            name="addon_status",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
        server_default=AddonStatus.ACTIVE.value,
    )
    additional_user_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    price_per_user_per_month: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment=(
            "Extensible addon attributes. "
            "Expected keys: payment_reference (str), purchase_order_number (str), "
            "approval_notes (str). "
            "Governed by application-layer Pydantic validation."
        ),
    )

    # ── Relationships ────────────────────────────────────────────────────
    subscription: Mapped["SchoolSubscription"] = relationship(
        "SchoolSubscription",
        back_populates="addons",
        lazy="joined",
    )
    plan: Mapped["Plan"] = relationship(
        "Plan",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<ExpansionAddon id={self.id!s} subscription={self.subscription_id!s} "
            f"+{self.additional_user_count} users status={self.status.value}>"
        )
