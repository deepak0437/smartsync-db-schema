"""SubscriptionHistory model — append-only, strictly immutable audit log.

No UPDATEs, no DELETEs.  No ``updated_at``, no ``deleted_at``.
Every subscription lifecycle event is captured as a new row with
snapshotted commercial terms at the moment of the event.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PlatformBase
from app.db.mixins import AuditOnlyMixin, PrimaryKeyMixin
from app.models.enums import HistoryEventType

if TYPE_CHECKING:
    from app.models.expansion_addon import ExpansionAddon
    from app.models.school import School
    from app.models.school_subscription import SchoolSubscription


class SubscriptionHistory(PrimaryKeyMixin, AuditOnlyMixin, PlatformBase):
    """Append-only audit log for all subscription lifecycle events.

    Each row captures a snapshot of the subscription state at the moment
    of the event.  This table intentionally has:

    - **No ``updated_at``** — rows are never modified.
    - **No ``deleted_at``** — audit records are permanent and cannot be soft-deleted.

    Note: This model inherits directly from ``PrimaryKeyMixin + AuditOnlyMixin
    + PlatformBase`` instead of ``BaseModel`` because it is append-only and
    must not include ``SoftDeleteMixin``.
    """

    __tablename__ = "subscription_history"
    __table_args__ = (
        # Chronological event retrieval per subscription
        Index(
            "ix_history_subscription_performed",
            "subscription_id",
            "performed_at",
        ),
        # School-level audit trail
        Index(
            "ix_history_school_performed",
            "school_id",
            "performed_at",
        ),
        # Filter by event type for analytics
        Index(
            "ix_history_event_type",
            "event_type",
        ),
    )

    # ── Foreign keys ─────────────────────────────────────────────────────
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id"),
        nullable=False,
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schools.id"),
        nullable=False,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plans.id"),
        nullable=False,
    )

    # ── Event classification ─────────────────────────────────────────────
    event_type: Mapped[HistoryEventType] = mapped_column(
        SAEnum(
            HistoryEventType,
            name="history_event_type",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
    )

    # ── Snapshotted state at event time ──────────────────────────────────
    tenure_months: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )
    max_user_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    effective_max_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    remaining_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    price_per_user_per_month: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # ── Optional addon reference ─────────────────────────────────────────
    addon_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("expansion_addons.id"),
        nullable=True,
    )

    # ── Event metadata ───────────────────────────────────────────────────
    change_summary: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="Before/after deltas, e.g. {'previous_max_users': 50, 'new_max_users': 100}",
    )
    performed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        nullable=True,
        comment="UUID of the user/admin who triggered this event (loose — no FK to avoid cross-schema coupling)",
    )
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ────────────────────────────────────────────────────
    subscription: Mapped["SchoolSubscription"] = relationship(
        "SchoolSubscription",
        back_populates="history_entries",
        lazy="noload",
    )
    school: Mapped["School"] = relationship(
        "School",
        lazy="noload",
    )
    addon: Mapped[Optional["ExpansionAddon"]] = relationship(
        "ExpansionAddon",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<SubscriptionHistory id={self.id!s} "
            f"event={self.event_type.value} sub={self.subscription_id!s}>"
        )
