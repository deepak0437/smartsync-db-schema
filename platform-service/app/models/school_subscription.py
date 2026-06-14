"""
School Subscription Models — Platform Service.

Two tables work together to represent a school's purchased subscription:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Table 1: SchoolSubscription
  The master purchase record.
  "School X bought Plan A2 with 2500 users for 12 months starting Jan 1."
  Contains: which plan, which user count chosen, tenure chosen,
            start/end dates, status, module selections.
"""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel
from .plan_constants import TenureMonths, TrialStatus


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS FOR SUBSCRIPTION STATE
# ═══════════════════════════════════════════════════════════════════════════════

class SubscriptionStatus(str, enum.Enum):
    """
    Lifecycle status of a school's subscription.

    State machine:
        FREE_TRIAL ──► ACTIVE (on payment)
        ACTIVE     ──► GRACE  (on end_date if auto_renewal fails)
        ACTIVE     ──► EXPIRED (on manual cancellation at period end)
        GRACE      ──► ACTIVE  (payment received within grace period)
        GRACE      ──► SUSPENDED (grace period elapsed, no payment)
        SUSPENDED  ──► ACTIVE  (payment received after suspension)
        ACTIVE     ──► CANCELLED (school requests cancellation)
        CANCELLED  ──► ARCHIVED (after data retention period)
    """
    FREE_TRIAL = "FREE_TRIAL"   # Trial period active
    ACTIVE     = "ACTIVE"       # Paid, within validity dates
    GRACE      = "GRACE"        # end_date passed, within grace period (15 days)
    EXPIRED    = "EXPIRED"      # Past end_date + grace, not renewed
    SUSPENDED  = "SUSPENDED"    # Manually blocked (non-payment or ops action)
    CANCELLED  = "CANCELLED"    # School cancelled, access until end_date
    ARCHIVED   = "ARCHIVED"     # No access, data retained per policy


class SubscriptionChangeType(str, enum.Enum):
    """
    Type of change event in subscription_history.
    Every status or plan change creates one immutable history row.
    """
    TRIAL_STARTED   = "TRIAL_STARTED"    # Free trial began
    TRIAL_CONVERTED = "TRIAL_CONVERTED"  # Trial → paid plan
    TRIAL_EXPIRED   = "TRIAL_EXPIRED"    # Trial ended without conversion
    ACTIVATED       = "ACTIVATED"        # First paid activation
    RENEWED         = "RENEWED"          # Subscription renewed (same plan)
    UPGRADED        = "UPGRADED"         # Moved to higher plan or more users
    DOWNGRADED      = "DOWNGRADED"       # Moved to lower plan or fewer users
    TENURE_CHANGED  = "TENURE_CHANGED"   # Same plan, different duration
    SUSPENDED       = "SUSPENDED"        # Access blocked
    REACTIVATED     = "REACTIVATED"      # Reinstated after suspension
    CANCELLED       = "CANCELLED"        # School cancelled
    EXPIRED         = "EXPIRED"          # Lapsed without renewal
    EXTENDED        = "EXTENDED"         # End date extended (goodwill)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHOOL SUBSCRIPTION  (the purchase record)
# ═══════════════════════════════════════════════════════════════════════════════

class SchoolSubscription(BaseModel):
    """
    A school's active or historical subscription to a plan.

    One row per subscription period.
    On renewal: new row created, old row status → EXPIRED.
    On upgrade: new row created, old row status → EXPIRED (prorated if needed).

    Invariant enforced by partial unique index:
        A school can have at most ONE subscription with
        status IN (FREE_TRIAL, ACTIVE, GRACE, SUSPENDED) at a time.
    """

    __tablename__ = "school_subscriptions"
    __table_args__ = (
        # For SCALABLE plans: selected_max_users must be provided.
        # For ENTRY plans: selected_max_users must be NULL (use plan's fixed count).
        CheckConstraint(
            "selected_max_users IS NOT NULL OR selected_max_users IS NULL",
            name="chk_subscription_user_count",
            # Note: actual enforcement done in application layer with enum validation
        ),
        {
            "schema": "platform",
            "comment": (
                "One row per school per subscription period. "
                "Captures what was purchased, at what user count, for how long. "
                "Pricing details are in school_subscription_pricing (1-to-1)."
            ),
        },
    )

    # ── Core References ───────────────────────────────────────────────────────

    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment=(
            "Soft FK → platform.tenants.id. "
            "Denormalized here for efficient billing queries. "
            "Hard FK avoided to allow cross-service flexibility."
        ),
    )

    school_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment=(
            "Soft FK → platform.schools.id. "
            "Billing is at school level, not tenant level."
        ),
    )

    # ── Status ────────────────────────────────────────────────────────────────

    status = Column(
        Enum(SubscriptionStatus, name="subscription_status_enum", schema="platform"),
        nullable=False,
        default=SubscriptionStatus.FREE_TRIAL,
        index=True,
        comment="Current lifecycle status. See SubscriptionStatus docstring for state machine.",
    )

    # ── User Count Selection ──────────────────────────────────────────────────

    selected_max_users = Column(
        Integer,
        nullable=True,
        comment=(
            "The user count option selected by platform team at subscription time. "
            "SCALABLE plans (A2, B2): must be a value from plan.allowed_user_counts. "
            "  A2 options: 1500 | 2500 | 3500 | 4500 | 5500 "
            "  B2 options: 2000 | 3000 | 4000 | 5000 "
            "ENTRY plans (A1, B1): NULL — plan.fixed_max_users is used instead. "
            "API Gateway and quota enforcement use the EFFECTIVE user count = "
            "  selected_max_users (if set) OR plan.fixed_max_users."
        ),
    )

    effective_max_users = Column(
        Integer,
        nullable=False,
        comment=(
            "Computed and stored at subscription creation time. "
            "= selected_max_users (for SCALABLE plans) "
            "OR plan.fixed_max_users (for ENTRY plans). "
            "This is the value used by all quota enforcement. "
            "Stored to avoid joining to plan on every request."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────


    def __repr__(self) -> str:
        return (
            f"<SchoolSubscription "
            f"school_id={self.school_id} "
            f"users={self.effective_max_users} "
            f"status={self.status}>"
        )
