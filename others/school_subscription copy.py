"""
School Subscription Model - Subscription Instance for Schools.

Module Purpose:
  Represents active subscriptions purchased by individual schools.
  Tracks purchased limits for subscription enforcement.
  Billing boundary is per-school within multi-school tenants.

Architecture:
  - SchoolSubscription (many-to-many bridge)
    - School (one school -> multiple subscriptions, different plans over time)
    - Tenant (organizational link for reporting)
    - SubscriptionPlan (product reference)
  - Stores LIMITS only (what was purchased)
  - Usage metrics fetched from respective services:
    * User counts -> Auth Service (school_role_stats)
    * Storage usage -> Media Service

Key Features:
  - Trial period support (trial_ends_at date)
  - Auto-renewal capability
  - Usage limits enforcement (student count, user count, storage)
  - Flexible billing (base price, per-student, hybrid)
  - NO runtime usage counters (fetched from Auth Service when needed)

Usage:
  Each school subscription links to exactly one subscription plan.
  Multiple subscriptions can exist per school (for upgrades/downgrades).
  Used for billing, feature access control, and quota enforcement.

Design Decision:
  We do NOT store active_student_count, active_user_count here.
  Rationale:
    - Auth Service owns user data -> Auth Service tracks counts
    - Prevents data duplication and sync issues
    - Platform Service only stores purchased LIMITS
    - Usage fetched via Auth Service API when displaying subscription status
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

    Stores:
        - Subscription plan details
        - Purchased limits (max total users, max storage)
        - Billing information (amounts, dates, currency)
        - Subscription status and dates

    Does NOT store:
        - Active user counts (→ Auth Service: school_role_stats)
        - Storage usage (→ Media Service: school_storage_stats)

    Example:
        Green Valley Bangalore
            → Enterprise Plan (₹999/month)
            → Purchased: 520 total users (all roles), 1TB storage
            → Current usage: 450 users (students + teachers + parents + staff)
            → Usage fetched from Auth Service when needed

        Green Valley Hyderabad
            → Professional Plan (₹499/month)
            → Purchased: 500 total users, 500GB storage
            → Current usage: 480 users
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

    # Purchased Limits (What the school paid for)
    # These are the MAXIMUM allowed values enforced by the platform
    purchased_user_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment=(
            "Maximum total users allowed across ALL roles (students, teachers, parents, staff, etc.). "
            "Example: Plan ₹499/month = 500 users total, Plan ₹999/month = 520 users total."
        ),
    )

    purchased_storage_gb = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Maximum storage in GB allowed (for media, documents, etc.)",
    )

    # NOTE: Active usage counts are NOT stored here.
    # They are maintained in:
    #   - Auth Service: auth.school_role_stats (user counts per role)
    #     To get total usage: SUM(active_users) across all roles for the school
    #   - Media Service: media.school_storage_stats (storage usage)
    # Fetch via API when displaying subscription dashboard.

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
        comment=(
            "When subscription was last updated (plan changes, renewals, etc.). "
            "NOTE: This does NOT track usage changes. "
            "Usage is tracked in Auth Service (school_role_stats.updated_at)."
        ),
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