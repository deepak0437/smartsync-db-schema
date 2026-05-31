"""
Subscription History Model - Audit Trail for Subscription Changes.

Module Purpose:
  Tracks every change to school subscriptions for audit and analytics.
  Maintains complete history of upgrades, downgrades, renewals, and cancellations.
  Enables billing reconciliation and usage trend analysis.

Architecture:
  - SubscriptionHistory (child) -> SchoolSubscription (parent, many-to-one)
  - Immutable audit trail (insert-only, no updates)
  - Links to old and new SubscriptionPlans
  - Financial snapshot at time of change

Key Features:
  - Action tracking (CREATE, UPGRADE, DOWNGRADE, RENEWAL, CANCEL, PRICE_CHANGE)
  - Plan version tracking (old plan vs new plan)
  - Financial impact recording (price before/after)
  - Timestamp with timezone
  - Admin/system tracking for accountability
  - Reason for change (user request, auto-renewal, system action)

Usage:
  Every subscription change creates a new history record.
  Query to get subscription timeline or billing audit trail.
  Analyze upgrade patterns and customer churn reasons.

Examples:
  School upgrades from PROFESSIONAL to ENTERPRISE
  Annual renewal of current plan
  System downgrade due to failed payment
  Price increase on plan renewal
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class SubscriptionAction(str, enum.Enum):
    """
    Type of subscription change event.

    Actions:
        CREATE: New subscription purchased
        UPGRADE: Moved to higher-tier plan
        DOWNGRADE: Moved to lower-tier plan
        RENEWAL: Subscription renewed for next period
        CANCEL: Subscription cancelled
        PRICE_CHANGE: Plan price changed on renewal
        REACTIVATE: Reactivated after cancellation
        SUSPEND: Temporarily suspended (payment issue)
        RESUME: Resumed after suspension
    """

    CREATE = "CREATE"
    UPGRADE = "UPGRADE"
    DOWNGRADE = "DOWNGRADE"
    RENEWAL = "RENEWAL"
    CANCEL = "CANCEL"
    PRICE_CHANGE = "PRICE_CHANGE"
    REACTIVATE = "REACTIVATE"
    SUSPEND = "SUSPEND"
    RESUME = "RESUME"


class SubscriptionHistory(BaseModel):
    """
    Audit record for every subscription change.

    Immutable historical record of subscription lifecycle events.
    """

    __tablename__ = "subscription_history"

    # Link to current subscription
    school_subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("school_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to SchoolSubscription this history belongs to",
    )

    # Action
    action = Column(
        Enum(SubscriptionAction, name="subscription_action_enum"),
        nullable=False,
        index=True,
        comment="Type of subscription change",
    )

    # Plan versions
    old_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id"),
        nullable=True,
        comment="Previous plan (NULL for CREATE action)",
    )

    new_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id"),
        nullable=False,
        comment="Plan after change",
    )

    # Timestamps
    changed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="When change was recorded in system",
    )

    effective_date = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="When change becomes effective (may differ from changed_at)",
    )

    # Financial snapshot
    old_price = Column(
        Numeric(14, 2),
        nullable=True,
        comment="Price before change (NULL for CREATE)",
    )

    new_price = Column(
        Numeric(14, 2),
        nullable=False,
        comment="Price after change",
    )

    old_billing_cycle = Column(
        String(20),
        nullable=True,
        comment="Previous billing cycle (MONTHLY, QUARTERLY, ANNUAL)",
    )

    new_billing_cycle = Column(
        String(20),
        nullable=False,
        comment="New billing cycle",
    )

    # Reason tracking
    reason = Column(
        String(500),
        nullable=True,
        comment="Why change occurred (user request, auto renewal, system action, etc)",
    )

    changed_by = Column(
        String(255),
        nullable=False,
        comment="Who initiated change (admin username or 'system' for automated)",
    )

    notes = Column(
        String(500),
        nullable=True,
        comment="Additional notes about the change",
    )

    # Relationships
    subscription = relationship(
        "SchoolSubscription",
        back_populates="history",
    )

    old_plan = relationship(
        "SubscriptionPlan",
        foreign_keys=[old_plan_id],
    )

    new_plan = relationship(
        "SubscriptionPlan",
        foreign_keys=[new_plan_id],
    )

    def __repr__(self) -> str:
        """
        String representation of SubscriptionHistory.

        Returns:
            String in format: <SubscriptionHistory action=UPGRADE school_id=uuid>
        """
        return (
            f"<SubscriptionHistory "
            f"action={self.action} "
            f"changed_at={self.changed_at}>"
        )
