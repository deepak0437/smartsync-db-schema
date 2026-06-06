"""
School Subscription History — Platform Service.

Immutable audit log. One row per change event.
Never updated or deleted after insert.

Every time a school's subscription status or plan changes,
one row is written here. This table answers every historical question:

  "What plan was this school on in August 2024?"
  "When exactly did they upgrade from A1 to A2?"
  "How many times have they renewed?"
  "What was the price at each renewal?"
  "Who made the change and why?"
  "Did they ever get suspended? When was it lifted?"

Design:
  - Append-only (no UPDATE, no DELETE ever)
  - Each row is self-contained: stores both old and new values
    so you can reconstruct any point-in-time state without
    joining to other tables
  - Links back to the subscription row via subscription_id
  - Also links the previous subscription via previous_subscription_id
    for multi-hop chain traversal

Query patterns:

  Full history for a school:
    SELECT * FROM school_subscription_history
    WHERE school_id = X
    ORDER BY changed_at ASC

  State at a specific date:
    SELECT * FROM school_subscription_history
    WHERE school_id = X AND changed_at <= '2024-08-01'
    ORDER BY changed_at DESC LIMIT 1

  All upgrades across platform:
    SELECT * FROM school_subscription_history
    WHERE change_type = 'UPGRADED'
    AND changed_at BETWEEN '2024-01-01' AND '2024-12-31'

  Monthly MRR from history:
    GROUP BY date_trunc('month', changed_at), new_final_amount_paise
"""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import BaseModel
from .school_subscription import SubscriptionChangeType


class SchoolSubscriptionHistory(BaseModel):
    """
    Immutable event log of every subscription change.

    One row is inserted for EVERY state transition:
      - Trial starts
      - School activates (pays)
      - Plan is upgraded or downgraded
      - Subscription is suspended or reactivated
      - Subscription is cancelled or expires
      - End date is extended

    Rows are NEVER modified after insert.
    The is_deleted, deleted_by fields from BaseModel are inherited
    but should never be used on this table.
    """

    __tablename__ = "school_subscription_history"
    __table_args__ = (
        {
            "schema": "platform",
            "comment": (
                "Immutable event log of every subscription change per school. "
                "Append-only. Never update or delete rows."
            ),
        },
    )

    # ── Core References ───────────────────────────────────────────────────────

    school_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Soft FK → platform.schools.id. Indexed for per-school history queries.",
    )

    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Soft FK → platform.tenants.id. Denormalized for tenant-level reporting.",
    )

    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform.school_subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment=(
            "FK → the NEW school_subscriptions row resulting from this change. "
            "NULL if the change was a suspension/cancellation that didn't create a new row."
        ),
    )

    previous_subscription_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment=(
            "FK → the OLD school_subscriptions row before this change. "
            "NULL for the very first event (TRIAL_STARTED)."
        ),
    )

    # ── Change Classification ─────────────────────────────────────────────────

    change_type = Column(
        Enum(SubscriptionChangeType, name="subscription_change_type_enum", schema="platform"),
        nullable=False,
        index=True,
        comment="Type of change. See SubscriptionChangeType enum for all values.",
    )

    # ── Before State Snapshot ─────────────────────────────────────────────────
    # Store old values explicitly so this row is self-contained.

    previous_plan_code = Column(
        String(20),
        nullable=True,
        comment=(
            "Plan code BEFORE this change. "
            "NULL for TRIAL_STARTED (no previous plan). "
            "E.g. 'A1' before an upgrade to 'A2'."
        ),
    )

    previous_plan_name = Column(
        String(100),
        nullable=True,
        comment="Plan name BEFORE this change. Stored for readability without joins.",
    )

    previous_status = Column(
        String(30),
        nullable=True,
        comment="Subscription status BEFORE this change. E.g. 'ACTIVE' before 'SUSPENDED'.",
    )

    previous_max_users = Column(
        Integer,
        nullable=True,
        comment="Effective user count BEFORE this change.",
    )

    previous_tenure_months = Column(
        Integer,
        nullable=True,
        comment="Tenure in months BEFORE this change.",
    )

    previous_end_date = Column(
        Date,
        nullable=True,
        comment="Subscription end date BEFORE this change.",
    )

    previous_final_amount_paise = Column(
        Numeric(14, 0),
        nullable=True,
        comment="Final invoice amount BEFORE this change, in paise.",
    )

    # ── After State Snapshot ──────────────────────────────────────────────────

    new_plan_code = Column(
        String(20),
        nullable=True,
        comment="Plan code AFTER this change.",
    )

    new_plan_name = Column(
        String(100),
        nullable=True,
        comment="Plan name AFTER this change.",
    )

    new_status = Column(
        String(30),
        nullable=False,
        comment="Subscription status AFTER this change.",
    )

    new_max_users = Column(
        Integer,
        nullable=True,
        comment="Effective user count AFTER this change.",
    )

    new_tenure_months = Column(
        Integer,
        nullable=True,
        comment="Tenure in months AFTER this change.",
    )

    new_start_date = Column(
        Date,
        nullable=True,
        comment="New subscription start date AFTER this change.",
    )

    new_end_date = Column(
        Date,
        nullable=True,
        comment="New subscription end date AFTER this change.",
    )

    new_final_amount_paise = Column(
        Numeric(14, 0),
        nullable=True,
        comment="Final invoice amount AFTER this change, in paise. NULL for suspensions.",
    )

    # ── Who and Why ───────────────────────────────────────────────────────────

    changed_by_user_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment=(
            "Internal SmartSync user_id who performed this change. "
            "NULL for system-automated changes (auto-expiry, auto-suspension)."
        ),
    )

    changed_by_type = Column(
        String(30),
        nullable=False,
        default="PLATFORM_ADMIN",
        comment=(
            "Who initiated this change. "
            "PLATFORM_ADMIN = SmartSync ops team manually. "
            "SYSTEM = Automated job (expiry cron, payment webhook). "
            "SCHOOL_ADMIN = School requested cancellation."
        ),
    )

    change_reason = Column(
        String(500),
        nullable=True,
        comment=(
            "Human-readable reason for this change. "
            "Examples: "
            "'School requested upgrade to accommodate 2500 students', "
            "'Payment failed after 3 retries — auto-suspended', "
            "'NGO verification approved — 10% additional discount applied', "
            "'Contract renewed for 24 months at negotiated rate'."
        ),
    )

    # ── Precise Change Timestamp ──────────────────────────────────────────────

    changed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment=(
            "Exact UTC timestamp when this change occurred. "
            "Not the same as created_at (BaseModel) — kept separate for clarity. "
            "Indexed for time-range queries and MRR calculations."
        ),
    )

    # ── Financial Snapshot at Change Time ─────────────────────────────────────
    # Separate from new_final_amount for clarity on pricing components.

    base_price_at_change_paise = Column(
        Numeric(14, 0),
        nullable=True,
        comment="Base price (before discounts) at the time of this change.",
    )

    discount_percent_at_change = Column(
        Numeric(5, 2),
        nullable=True,
        comment="Total discount percent applied at the time of this change.",
    )

    tax_percent_at_change = Column(
        Numeric(5, 2),
        nullable=True,
        comment="Tax percent applied at the time of this change.",
    )

    # ── Payment Reference ─────────────────────────────────────────────────────

    payment_reference = Column(
        String(255),
        nullable=True,
        comment="Payment gateway reference associated with this change (if applicable).",
    )

    # ── Internal Notes ────────────────────────────────────────────────────────

    internal_notes = Column(
        Text,
        nullable=True,
        comment="Additional internal notes from ops team. Not visible to school.",
    )

    # ── Relationship ──────────────────────────────────────────────────────────

    subscription = relationship(
        "SchoolSubscription",
        back_populates="history_events",
        foreign_keys=[subscription_id],
    )

    def __repr__(self) -> str:
        return (
            f"<SchoolSubscriptionHistory "
            f"school_id={self.school_id} "
            f"type={self.change_type} "
            f"{self.previous_plan_code}→{self.new_plan_code} "
            f"at={self.changed_at}>"
        )
        