from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Boolean,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from base import Base
from .enums import SubscriptionStatus

if TYPE_CHECKING:
    from .expansion_addon import ExpansionAddon
    from .plan import Plan
    from .school import School
    from .tenant import Tenant


class SchoolSubscription(Base):
    """A school's active service agreement.

    At most **one** active subscription per school is enforced by a
    partial unique index on ``(school_id) WHERE status = 'ACTIVE'``.

    Subscriptions cannot be cancelled midway — they either expire
    naturally or are superseded by an upgrade.
    """

    __tablename__ = "school_subscription"
    __table_args__ = (
        # ── CHECK constraints ────────────────────────────────────────────
        CheckConstraint(
            "remaining_users >= 0",
            name="remaining_non_negative",
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

    addon_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("expansion_addons.id"),
        nullable=True,
        comment="Addon plan ID - null by default"
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

    remaining_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="effective_max_users - current_assigned_user_count",
    )

    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    expires: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
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
    addon: Mapped[Optional["ExpansionAddon"]] = relationship(
        "ExpansionAddon",
        foreign_keys=[addon_id],
        lazy="selectin",
    )
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<SchoolSubscription id={self.id!s} school_id={self.school_id!s} "
            f"status={self.status.value} users={self.remaining_users}/"
            f"{self.effective_max_users}>"
        )

