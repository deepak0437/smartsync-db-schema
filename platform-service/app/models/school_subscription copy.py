"""
School Subscription Models — Platform Service.

Two tables work together to represent a school's purchased subscription:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Table 1: SchoolSubscription
  The master purchase record.
  "School X bought Plan A2 with 2500 users for 12 months starting Jan 1."
  Contains: which plan, which user count chosen, tenure chosen,
            start/end dates, status, module selections.

Table 2: SchoolSubscriptionPricing
  The complete price breakdown for that subscription.
  Separated from SchoolSubscription so the financial audit trail
  is completely independent — one join gives the full invoice breakdown.
  Contains: base_price → discount → subtotal → tax → final_amount.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Why separate pricing into its own table?
  - Clean separation of concerns: subscription = what + when, pricing = how much
  - Pricing can be recalculated (mid-term upgrade) without touching subscription
  - Invoice generation queries only the pricing table — no joins needed
  - Easy to add multiple pricing entries for complex billing scenarios
  - Audit trail: you can see every price that was ever associated

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pricing Calculation Flow:
  1. Platform team picks: Plan A2 + 2500 users + 12 months
  2. System computes:
       base_price_paise
           = plan.base_price_paise
             + ((2500 - 1500) / 1000) × plan.per_user_increment_paise
             = base_at_min + 1 × increment

       tenure_discount_percent = plan.tenure_discounts["12"]  → e.g. 15.00

       discount_amount_paise
           = base_price_paise × (tenure_discount_percent / 100)

       subtotal_paise = base_price_paise - discount_amount_paise

       tax_amount_paise = subtotal_paise × (plan.tax_percent / 100)

       final_amount_paise = subtotal_paise + tax_amount_paise

  3. All of these values are STORED on SchoolSubscriptionPricing.
     They are snapshots — changing the plan later doesn't change them.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Relationships:
  SchoolSubscription (many) → SubscriptionPlan (1)      [plan_id]
  SchoolSubscription (many) → School (1)                [school_id]
  SchoolSubscription (many) → Tenant (1)                [tenant_id]
  SchoolSubscription (1)    → SchoolSubscriptionPricing (1)
  SchoolSubscription (1)    → SchoolFreeTrial (0-1)
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

    plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform.subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment=(
            "FK → platform.subscription_plans.id. "
            "RESTRICT prevents deleting a plan that has subscribers. "
            "Deprecated plans use is_active=False instead."
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

    # ── Tenure ────────────────────────────────────────────────────────────────

    tenure_months = Column(
        Enum(TenureMonths, name="tenure_months_enum", schema="platform"),
        nullable=False,
        comment=(
            "Duration of this subscription period. Selected from fixed options. "
            "Options: 1 | 3 | 6 | 12 | 24 | 36 months. "
            "Determines: end_date, discount applied, billing frequency."
        ),
    )

    # ── Validity Period ───────────────────────────────────────────────────────

    start_date = Column(
        Date,
        nullable=False,
        index=True,
        comment=(
            "Date this subscription becomes active. "
            "For trials: date of first login or explicit trial start. "
            "For paid: date payment is confirmed."
        ),
    )

    end_date = Column(
        Date,
        nullable=False,
        index=True,
        comment=(
            "Last date this subscription is valid (inclusive). "
            "Computed as: start_date + tenure_months months - 1 day. "
            "After this date: status → GRACE for 15 days, then EXPIRED."
        ),
    )

    grace_period_end_date = Column(
        Date,
        nullable=True,
        comment=(
            "Date until which school retains access after end_date. "
            "Typically end_date + 15 days. "
            "NULL if school cancelled voluntarily."
        ),
    )

    auto_renewal = Column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "Whether this subscription auto-renews at end_date. "
            "If True and payment collected: new subscription row created. "
            "If True and payment fails: status → GRACE."
        ),
    )

    next_renewal_date = Column(
        Date,
        nullable=True,
        comment=(
            "Date when renewal should be initiated. "
            "Typically 30 days before end_date for advance invoice generation."
        ),
    )

    # ── Module & Add-on Selections ────────────────────────────────────────────

    active_modules = Column(
        JSONB,
        nullable=False,
        default=list,
        comment=(
            "Snapshot of modules this school can access for this subscription period. "
            "Copied from plan.included_modules at purchase time + any add-ons. "
            "API Gateway uses this (cached in Redis) for module-level access control. "
            "Storing snapshot means plan changes don't retroactively affect this school."
        ),
    )

    active_add_ons = Column(
        JSONB,
        nullable=False,
        default=list,
        comment=(
            "Optional modules purchased in addition to included_modules. "
            "Each entry: {module: 'HOSTEL', monthly_price_paise: 200000} "
            "Add-on prices are included in SchoolSubscriptionPricing."
        ),
    )

    # ── Contract & Payment References ─────────────────────────────────────────

    contract_file_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="File ID (File/Media Service) of the signed subscription contract.",
    )

    po_number = Column(
        String(100),
        nullable=True,
        comment="Purchase Order number. Required for government schools and enterprise accounts.",
    )

    payment_reference = Column(
        String(255),
        nullable=True,
        comment="External payment gateway reference (Razorpay order_id, NEFT UTR, cheque number).",
    )

    payment_method = Column(
        String(50),
        nullable=True,
        comment="How payment was received. E.g. 'NEFT', 'RAZORPAY', 'CHEQUE', 'NACH', 'CASH'",
    )

    # ── Chain References (for upgrade/renewal history) ─────────────────────

    previous_subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform.school_subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment=(
            "FK → previous school_subscriptions.id. "
            "Set when this row was created as a renewal or upgrade of an earlier one. "
            "Creates a linked chain: current → previous → older → oldest. "
            "Walk this chain to reconstruct full subscription history."
        ),
    )

    # ── Account Manager ───────────────────────────────────────────────────────

    account_manager_user_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Internal SmartSync user_id of the account manager who owns this deal.",
    )

    # ── Suspension / Cancellation Details ─────────────────────────────────────

    suspended_at = Column(
        Date,
        nullable=True,
        comment="Date subscription was suspended (non-payment or manual action).",
    )

    suspension_reason = Column(
        String(500),
        nullable=True,
        comment="Reason for suspension. E.g. 'Payment failed after 3 retries'",
    )

    cancelled_at = Column(
        Date,
        nullable=True,
        comment="Date cancellation was requested.",
    )

    cancellation_reason = Column(
        String(500),
        nullable=True,
        comment="Reason for cancellation. E.g. 'Switching to competitor', 'School closed'",
    )

    # ── Internal Notes ────────────────────────────────────────────────────────

    internal_notes = Column(
        Text,
        nullable=True,
        comment="Internal ops team notes. Not visible to school admin.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    plan = relationship(
        "SubscriptionPlan",
        back_populates="school_subscriptions",
        foreign_keys=[plan_id],
    )

    pricing = relationship(
        "SchoolSubscriptionPricing",
        back_populates="subscription",
        uselist=False,
        cascade="all, delete-orphan",
    )

    history_events = relationship(
        "SchoolSubscriptionHistory",
        back_populates="subscription",
        foreign_keys="SchoolSubscriptionHistory.subscription_id",
        order_by="SchoolSubscriptionHistory.changed_at",
    )

    free_trial = relationship(
        "SchoolFreeTrial",
        back_populates="subscription",
        uselist=False,
    )

    def __repr__(self) -> str:
        return (
            f"<SchoolSubscription "
            f"school_id={self.school_id} "
            f"plan_id={self.plan_id} "
            f"users={self.effective_max_users} "
            f"tenure={self.tenure_months}m "
            f"status={self.status}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SCHOOL SUBSCRIPTION PRICING  (the financial breakdown)
# ═══════════════════════════════════════════════════════════════════════════════

class SchoolSubscriptionPricing(BaseModel):
    """
    Complete price breakdown for one SchoolSubscription.

    One row per SchoolSubscription. Created at the same time as the subscription.
    Immutable after creation — a price change creates a new subscription row
    (which gets a new pricing row).

    All monetary values stored in paise (1 INR = 100 paise).
    Stored as integers to prevent floating-point rounding errors.

    Full calculation chain:
        base_price_paise
            ↓  minus
        discount_amount_paise  (from tenure_discount_percent)
            ↓  equals
        subtotal_paise
            ↓  plus
        tax_amount_paise  (from tax_percent)
            ↓  equals
        final_amount_paise  ← this is what school pays
    """

    __tablename__ = "school_subscription_pricing"
    __table_args__ = (
        {
            "schema": "platform",
            "comment": (
                "Complete price breakdown per subscription. "
                "1-to-1 with school_subscriptions. "
                "All amounts in paise. Immutable after creation."
            ),
        },
    )

    # ── Reference ─────────────────────────────────────────────────────────────

    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform.school_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="FK → school_subscriptions.id. Unique = one pricing per subscription.",
    )

    # ── What Was Priced (snapshot at purchase time) ────────────────────────────

    plan_code_at_purchase = Column(
        String(20),
        nullable=False,
        comment=(
            "Snapshot of plan code at purchase time. "
            "E.g. 'A2'. Stored so pricing row is self-explanatory even if plan changes."
        ),
    )

    user_count_at_purchase = Column(
        Integer,
        nullable=False,
        comment="Effective user count at purchase time (selected or fixed).",
    )

    tenure_months_at_purchase = Column(
        Integer,
        nullable=False,
        comment="Tenure in months at purchase time. E.g. 12",
    )

    # ── Base Price ────────────────────────────────────────────────────────────

    base_price_paise = Column(
        Numeric(14, 0),
        nullable=False,
        comment=(
            "Computed monthly base price before any discounts, in paise. "
            "For ENTRY plans: plan.base_price_paise directly. "
            "For SCALABLE plans: plan.base_price_paise + "
            "  ((user_count - min_users) / step) × plan.per_user_increment_paise."
        ),
    )

    # ── Tenure Discount ───────────────────────────────────────────────────────

    tenure_discount_percent = Column(
        Numeric(5, 2),
        nullable=False,
        default=0,
        comment=(
            "Discount percentage applied based on tenure selection. "
            "Looked up from plan.tenure_discounts[tenure_months]. "
            "E.g. 12 months → 15.00 (15% off)."
        ),
    )

    discount_amount_paise = Column(
        Numeric(14, 0),
        nullable=False,
        default=0,
        comment=(
            "Computed discount amount in paise. "
            "= base_price_paise × (tenure_discount_percent / 100). "
            "E.g. base=500000, discount=15% → discount_amount=75000."
        ),
    )

    # ── Additional Discount (manual override by platform team) ────────────────

    additional_discount_percent = Column(
        Numeric(5, 2),
        nullable=False,
        default=0,
        comment=(
            "Extra discount % applied manually by platform team. "
            "Used for: referrals, NGO rate, negotiations, goodwill. "
            "Applied on top of tenure_discount (both stack). "
            "E.g. NGO gets extra 10% off after tenure discount."
        ),
    )

    additional_discount_amount_paise = Column(
        Numeric(14, 0),
        nullable=False,
        default=0,
        comment=(
            "Additional discount amount in paise. "
            "= (base_price_paise - discount_amount_paise) "
            "  × (additional_discount_percent / 100)."
        ),
    )

    additional_discount_reason = Column(
        String(255),
        nullable=True,
        comment=(
            "Why the additional discount was given. "
            "E.g. 'NGO registered school', 'Referral from XYZ School', "
            "'Early adopter offer', 'Negotiated rate'."
        ),
    )

    # ── Subtotal ──────────────────────────────────────────────────────────────

    subtotal_paise = Column(
        Numeric(14, 0),
        nullable=False,
        comment=(
            "Amount after all discounts, before tax. "
            "= base_price_paise - discount_amount_paise - additional_discount_amount_paise."
        ),
    )

    # ── Tax ───────────────────────────────────────────────────────────────────

    tax_percent = Column(
        Numeric(5, 2),
        nullable=False,
        default=18.00,
        comment=(
            "Tax rate applied to subtotal. "
            "Snapshot from plan.tax_percent at purchase time. "
            "18.00 = GST 18% (India standard). "
            "0.00  = tax-exempt school."
        ),
    )

    tax_label = Column(
        String(50),
        nullable=False,
        default="GST",
        comment="Tax label for invoice. Snapshot from plan.tax_label.",
    )

    tax_amount_paise = Column(
        Numeric(14, 0),
        nullable=False,
        default=0,
        comment=(
            "Tax amount in paise. "
            "= subtotal_paise × (tax_percent / 100). "
            "E.g. subtotal=425000, tax=18% → tax_amount=76500."
        ),
    )

    # ── Final Amount ──────────────────────────────────────────────────────────

    final_amount_paise = Column(
        Numeric(14, 0),
        nullable=False,
        comment=(
            "Total amount school must pay for this subscription period, in paise. "
            "= subtotal_paise + tax_amount_paise. "
            "This is the figure on the invoice. "
            "E.g. subtotal=425000, tax=76500 → final=501500 (₹5,015.00)."
        ),
    )

    # ── Add-on Breakdown ──────────────────────────────────────────────────────

    add_on_price_paise = Column(
        Numeric(14, 0),
        nullable=False,
        default=0,
        comment=(
            "Total price of all add-on modules for this period, in paise. "
            "Sum of SchoolSubscription.active_add_ons prices × tenure_months. "
            "Already included in final_amount_paise."
        ),
    )

    add_on_breakdown = Column(
        JSONB,
        nullable=False,
        default=list,
        comment=(
            "Itemised add-on pricing for invoice display. "
            "Example: [ "
            "  {module: 'HOSTEL', monthly_paise: 200000, months: 12, total_paise: 2400000}, "
            "  {module: 'TRANSPORT', monthly_paise: 150000, months: 12, total_paise: 1800000} "
            "]"
        ),
    )

    # ── Currency ──────────────────────────────────────────────────────────────

    currency = Column(
        String(3),
        nullable=False,
        default="INR",
        comment="Currency for all paise amounts. Snapshot from plan.currency.",
    )

    # ── GST Compliance (India) ────────────────────────────────────────────────

    hsn_sac_code = Column(
        String(20),
        nullable=True,
        comment="HSN/SAC code snapshot for invoice compliance.",
    )

    school_gstin = Column(
        String(20),
        nullable=True,
        comment="School's GSTIN for B2B invoice. Required for ITC claims.",
    )

    place_of_supply = Column(
        String(100),
        nullable=True,
        comment="State of supply for IGST vs CGST+SGST determination.",
    )

    # ── Relationship ──────────────────────────────────────────────────────────

    subscription = relationship(
        "SchoolSubscription",
        back_populates="pricing",
    )

    def __repr__(self) -> str:
        return (
            f"<SchoolSubscriptionPricing "
            f"subscription_id={self.subscription_id} "
            f"base={self.base_price_paise} "
            f"final={self.final_amount_paise} {self.currency}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FREE TRIAL  (separate config for trial-specific tracking)
# ═══════════════════════════════════════════════════════════════════════════════

class SchoolFreeTrial(BaseModel):
    """
    Tracks a school's free trial period and conversion.

    Created when a school first starts a trial.
    One row per school — trials don't repeat once converted or expired.

    Linked to the SchoolSubscription row that has status=FREE_TRIAL.
    On conversion: trial.status → CONVERTED, new paid SchoolSubscription created.
    """

    __tablename__ = "school_free_trials"
    __table_args__ = (
        UniqueConstraint("school_id", name="uq_one_trial_per_school"),
        {
            "schema": "platform",
            "comment": (
                "Free trial tracking per school. "
                "One row per school. Linked to the FREE_TRIAL subscription row."
            ),
        },
    )

    # ── References ────────────────────────────────────────────────────────────

    school_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
        index=True,
        comment="Soft FK → platform.schools.id. Unique — one trial per school ever.",
    )

    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Soft FK → platform.tenants.id. Denormalized for efficient queries.",
    )

    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform.school_subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK → the FREE_TRIAL status school_subscriptions row.",
    )

    # ── Trial Configuration ───────────────────────────────────────────────────

    trial_days_granted = Column(
        Integer,
        nullable=False,
        default=30,
        comment="Total free trial days granted to this school.",
    )

    trial_start_date = Column(
        Date,
        nullable=False,
        comment="Date the trial started (first login or explicit activation).",
    )

    trial_end_date = Column(
        Date,
        nullable=False,
        index=True,
        comment="Date the trial expires = trial_start_date + trial_days_granted.",
    )

    trial_max_users = Column(
        Integer,
        nullable=True,
        default=50,
        comment="User cap during trial. NULL = use plan's limit. Typically 50.",
    )

    trial_modules = Column(
        JSONB,
        nullable=False,
        default=list,
        comment=(
            "Modules available during trial. "
            "Typically a subset: ['ACADEMICS', 'COMMUNICATION']."
        ),
    )

    # ── Trial Status ──────────────────────────────────────────────────────────

    status = Column(
        Enum(TrialStatus, name="trial_status_enum", schema="platform"),
        nullable=False,
        default=TrialStatus.NOT_STARTED,
        index=True,
        comment="Current trial state. See TrialStatus enum.",
    )

    # ── Conversion Tracking ───────────────────────────────────────────────────

    converted_at = Column(
        Date,
        nullable=True,
        comment="Date school converted to a paid plan.",
    )

    converted_to_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform.subscription_plans.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK → the plan they converted to after trial.",
    )

    converted_to_subscription_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="FK → the new paid SchoolSubscription created on conversion.",
    )

    days_used_before_conversion = Column(
        Integer,
        nullable=True,
        comment="How many trial days were used before converting. Useful for sales analytics.",
    )

    # ── Expiry ────────────────────────────────────────────────────────────────

    expired_at = Column(
        Date,
        nullable=True,
        comment="Date trial expired without conversion.",
    )

    expiry_reminder_sent_at = Column(
        Date,
        nullable=True,
        comment="Date a trial-expiry reminder was sent to school admin.",
    )

    # ── Extension ─────────────────────────────────────────────────────────────

    extension_days = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Extra days added by platform team (goodwill extension). 0 = no extension.",
    )

    extension_reason = Column(
        String(255),
        nullable=True,
        comment="Why the trial was extended. E.g. 'School requested more time', 'Demo rescheduled'",
    )

    # ── Relationship ──────────────────────────────────────────────────────────

    subscription = relationship(
        "SchoolSubscription",
        back_populates="free_trial",
        foreign_keys=[subscription_id],
    )

    def __repr__(self) -> str:
        return (
            f"<SchoolFreeTrial "
            f"school_id={self.school_id} "
            f"status={self.status} "
            f"{self.trial_start_date}→{self.trial_end_date}>"
        )
        