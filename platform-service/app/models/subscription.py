"""Subscription model — at most one active subscription per school.

Commercial terms (tenure, max_user_count, pricing) are snapshotted at
creation time from the plan catalog (ADR-2).  The ``plan_id`` FK is retained
for traceability but is never re-read for mutable plan fields at runtime.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PlatformBase
from app.db.mixins import PrimaryKeyMixin, SoftDeleteMixin
from app.models.enums import SubscriptionStatus

if TYPE_CHECKING:
    from app.models.expansion_addon import ExpansionAddon
    from app.models.plan import Plan
    from app.models.school import School
    from app.models.subscription_history import SubscriptionHistory
    from app.models.tenant import Tenant


class Subscription(PrimaryKeyMixin, SoftDeleteMixin, PlatformBase):
    """A school's active service agreement.

    At most **one** active subscription per school is enforced by a
    partial unique index on ``(school_id) WHERE status = 'ACTIVE'``.
    """

    __tablename__ = "subscriptions"
    __table_args__ = (
        # ── CHECK constraints ────────────────────────────────────────────
        CheckConstraint(
            "tenure_months > 0",
            name="positive_tenure",
        ),
        CheckConstraint(
            "max_user_count > 0",
            name="positive_max_users",
        ),
        CheckConstraint(
            "price_per_user_per_month > 0",
            name="positive_price",
        ),
        CheckConstraint(
            "effective_max_users >= max_user_count",
            name="effective_gte_base",
        ),
        CheckConstraint(
            "remaining_users >= 0",
            name="remaining_non_negative",
        ),
        CheckConstraint(
            "remaining_users <= effective_max_users",
            name="remaining_lte_effective",
        ),
        CheckConstraint(
            "expires_at > starts_at",
            name="expiry_after_start",
        ),
        # ── Indexes ──────────────────────────────────────────────────────
        # Enforces max ONE active subscription per school at DB level
        Index(
            "uq_subscriptions_school_id_active",
            "school_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE' AND deleted_at IS NULL"),
        ),
        # Expiration batch jobs
        Index(
            "ix_subscriptions_expires_at_active",
            "expires_at",
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        # Plan usage analytics
        Index(
            "ix_subscriptions_plan_id",
            "plan_id",
        ),
        # Tenant-scoped active subscription queries
        Index(
            "ix_subscriptions_tenant_id_active",
            "tenant_id",
            postgresql_where=text("status = 'ACTIVE' AND deleted_at IS NULL"),
        ),
    )

    # ── Columns ──────────────────────────────────────────────────────────
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schools.id"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"),
        nullable=False,
        comment="Denormalized from school.tenant_id for tenant-scoped queries and future sharding",
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plans.id"),
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(
            SubscriptionStatus,
            name="subscription_status",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
        server_default=SubscriptionStatus.ACTIVE.value,
    )

    # ── Snapshotted commercial terms (ADR-2) ─────────────────────────────
    tenure_months: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )
    max_user_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Base user count from plan at subscription time",
    )
    price_per_user_per_month: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # ── Live capacity counters ───────────────────────────────────────────
    effective_max_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="max_user_count + sum(active addon additional_user_count)",
    )
    remaining_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="effective_max_users - current_assigned_user_count",
    )

    # ── Temporal ─────────────────────────────────────────────────────────
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    # ── Relationships ────────────────────────────────────────────────────
    school: Mapped["School"] = relationship(
        "School",
        back_populates="subscriptions",
        lazy="joined",
    )
    plan: Mapped["Plan"] = relationship(
        "Plan",
        lazy="joined",
    )
    addons: Mapped[List["ExpansionAddon"]] = relationship(
        "ExpansionAddon",
        back_populates="subscription",
        lazy="selectin",
    )
    history_entries: Mapped[List["SubscriptionHistory"]] = relationship(
        "SubscriptionHistory",
        back_populates="subscription",
        lazy="noload",
    )
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<Subscription id={self.id!s} school_id={self.school_id!s} "
            f"status={self.status.value} users={self.remaining_users}/"
            f"{self.effective_max_users}>"
        )
