"""
School Subscription Model - Subscription Instance for Schools.

Module Purpose:
  Represents active subscriptions purchased by individual schools.
  Tracks both purchased limits and active usage metrics.
  Billing boundary is per-school within multi-school tenants.

Architecture:
  - SchoolSubscription (many-to-many bridge)
    - School (one school -> multiple subscriptions, different plans over time)
    - Tenant (organizational link for reporting)
    - SubscriptionPlan (product reference)
  - Tracks usage metrics in real-time
  - Billing data (amount, discount, tax, final amount)

Key Features:
  - Trial period support (trial_ends_at date)
  - Auto-renewal capability
  - Usage limits enforcement (student count, user count, storage)
  - Current usage tracking (active counts)
  - Flexible billing (base price, per-student, hybrid)

Usage:
  Each school subscription links to exactly one subscription plan.
  Multiple subscriptions can exist per school (for upgrades/downgrades).
  Used for billing, feature access control, and quota enforcement.
"""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class SubscriptionStatus(str, enum.Enum):
    """
    Subscription lifecycle status.

    States:
        TRIAL: Evaluation period, limited access
        ACTIVE: Paid subscription, full access
        EXPIRED: End date passed, no renewal
        SUSPENDED: Temporary block (e.g., payment issue)
        CANCELLED: Subscription terminated by user/admin
    """

    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"


class SchoolSubscription(BaseModel):
    """
    Subscription purchased by a School.

    Billing Boundary = School

    Example:

    Green Valley Bangalore
        -> Enterprise

    Green Valley Hyderabad
        -> Professional
    """

    __tablename__ = "school_subscriptions"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
    )

    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.id"),
        nullable=False,
        index=True,
    )

    subscription_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id"),
        nullable=False,
        index=True,
    )

    status = Column(
        Enum(
            SubscriptionStatus,
            name="subscription_status_enum",
        ),
        nullable=False,
        default=SubscriptionStatus.TRIAL,
        index=True,
    )

    start_date = Column(
        Date,
        nullable=False,
    )

    end_date = Column(
        Date,
        nullable=False,
    )

    trial_ends_at = Column(
        Date,
        nullable=True,
    )

    auto_renew = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Purchased Limits
    purchased_student_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    purchased_user_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    purchased_role_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    purchased_storage_gb = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # Runtime Counters
    active_student_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    active_user_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    active_role_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    used_storage_gb = Column(
        Integer,
        nullable=False,
        default=0,
    )

    amount_paid = Column(
        Numeric(14, 2),
        nullable=False,
        default=0,
    )

    plan_amount = Column(
        Numeric(14, 2),
        nullable=False,
        default=0,
    )

    discount_amount = Column(
        Numeric(14, 2),
        nullable=False,
        default=0,
    )

    tax_amount = Column(
        Numeric(14, 2),
        nullable=False,
        default=0,
    )

    final_amount = Column(
        Numeric(14, 2),
        nullable=False,
        default=0,
    )

    currency = Column(
        String(3),
        nullable=False,
        default="INR",
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="When subscription was created/purchased",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="When subscription was last updated",
    )

    # Relationships
    tenant = relationship(
        "Tenant",
        back_populates="subscriptions",
    )

    school = relationship(
        "School",
        back_populates="subscriptions",
    )

    plan = relationship(
        "SubscriptionPlan",
        back_populates="subscriptions",
    )

    history = relationship(
        "SubscriptionHistory",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """
        String representation of SchoolSubscription.

        Returns:
            String in format: <SchoolSubscription school_id=uuid status=ACTIVE>
        """
        return (
            f"<SchoolSubscription "
            f"school_id={self.school_id} "
            f"status={self.status}>"
        )