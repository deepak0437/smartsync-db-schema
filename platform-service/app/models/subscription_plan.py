"""
Subscription Plan Model — Platform Service.

This is the PRODUCT CATALOG. It defines what SmartSync sells.
Platform team creates and manages these. Schools never touch this table.

Design:
───────────────────────────────────────────────────────────────────────
Four concrete plan definitions live here as rows:

  Row 1: A1 — Core Entry
    family=CORE, variant=ENTRY, fixed_max_users=500
    Platform team cannot pick a user count — it's baked in at 500.

  Row 2: A2 — Core Scalable
    family=CORE, variant=SCALABLE, fixed_max_users=NULL
    Platform team picks user count from CoreScalableUserCount enum
    when creating a SchoolSubscription. The plan itself doesn't
    store the user count — that goes on the subscription.

  Row 3: B1 — Growth Entry
    family=GROWTH, variant=ENTRY, fixed_max_users=1000

  Row 4: B2 — Growth Scalable
    family=GROWTH, variant=SCALABLE, fixed_max_users=NULL
    User count picked from GrowthScalableUserCount.

Plus optionally:
  Row 5: FREE_TRIAL — special plan, no payment, time-limited

Each plan stores:
  - Its base price at the minimum user tier
  - Per-user incremental price (for scalable plans, to compute
    the price at the chosen user count tier)
  - Tenure discounts (JSONB — how much % off for each tenure)
  - Included modules, feature flags, storage limits
  - Tax configuration

Pricing computation (done at SchoolSubscription creation):
  base_price_for_selected_users
      = plan.base_price_paise
        + (selected_users - min_users) / step * plan.per_user_increment_paise

  After getting base, SchoolSubscriptionPricing records the full
  breakdown: base → discount → subtotal → tax → final.
───────────────────────────────────────────────────────────────────────
"""

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import BaseModel
from .plan_constants import (
    PlanFamily,
    PlanVariant,
    PricingModel,
    Currency,
)


class SubscriptionPlan(BaseModel):
    """
    Master product catalog entry.

    One row per plan definition. Platform team creates 4-5 rows total.
    Never modified after creation (except is_active to deprecate).
    Existing SchoolSubscriptions snapshot their pricing at purchase time,
    so changing a plan does NOT affect active subscribers.
    """

    __tablename__ = "subscription_plans"
    __table_args__ = (
        # A family+variant combo is unique — only one A1, one A2, one B1, one B2
        UniqueConstraint(
            "family",
            "variant",
            name="uq_plan_family_variant",
        ),
        # Entry plans must have fixed_max_users set.
        # Scalable plans must NOT (user count lives on the subscription).
        CheckConstraint(
            "(variant = 'ENTRY' AND fixed_max_users IS NOT NULL) OR "
            "(variant = 'SCALABLE' AND fixed_max_users IS NULL)",
            name="chk_plan_user_count_consistency",
        ),
        {
            "schema": "platform",
            "comment": (
                "SmartSync product catalog. "
                "4 core rows: A1, A2, B1, B2 plus FREE_TRIAL. "
                "Platform team managed only."
            ),
        },
    )

    # ── Plan Identity ─────────────────────────────────────────────────────────

    name = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment=(
            "Human-readable plan name shown in the platform admin UI. "
            "Examples: 'Core Entry', 'Core Scalable', 'Growth Entry', 'Growth Scalable'"
        ),
    )

    code = Column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
        comment=(
            "Machine-readable unique identifier. Used in feature checks and API responses. "
            "Values: A1 | A2 | B1 | B2 | FREE_TRIAL"
        ),
    )

    family = Column(
        Enum(PlanFamily, name="plan_family_enum", schema="platform"),
        nullable=False,
        index=True,
        comment=(
            "Plan family grouping. "
            "CORE = A-series (smaller schools, 500-5500 users). "
            "GROWTH = B-series (larger schools, 1000-5000 users)."
        ),
    )

    variant = Column(
        Enum(PlanVariant, name="plan_variant_enum", schema="platform"),
        nullable=False,
        index=True,
        comment=(
            "Plan variant within family. "
            "ENTRY    = fixed user count, no selection needed (A1=500, B1=1000). "
            "SCALABLE = platform team picks user count from allowed list (A2, B2)."
        ),
    )

    description = Column(
        Text,
        nullable=True,
        comment="Internal description for platform team. Not visible to schools.",
    )

    is_publicly_listed = Column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "Whether this plan appears on the public pricing page. "
            "False = hidden (legacy plans, government-special deals)."
        ),
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment=(
            "False = deprecated plan. Cannot be assigned to new schools. "
            "Existing subscribers on this plan are unaffected."
        ),
    )

    display_order = Column(
        Integer,
        nullable=False,
        default=0,
        comment=(
            "Sort order for display on pricing page and admin dropdowns. "
            "Convention: A1=1, A2=2, B1=3, B2=4"
        ),
    )

    highlight_text = Column(
        String(100),
        nullable=True,
        comment=(
            "Optional badge text on pricing card. "
            "Examples: 'Most Popular', 'Best Value', 'New'"
        ),
    )

    # ── User Count Configuration ──────────────────────────────────────────────

    fixed_max_users = Column(
        Integer,
        nullable=True,
        comment=(
            "ENTRY plans only (A1, B1). "
            "The fixed maximum total user count. No selection needed. "
            "A1 = 500, B1 = 1000. "
            "NULL for SCALABLE plans (A2, B2) — count chosen at subscription time."
        ),
    )

    min_users_for_scalable = Column(
        Integer,
        nullable=True,
        comment=(
            "SCALABLE plans only (A2, B2). "
            "The minimum/first option in the user count dropdown. "
            "A2 = 1500, B2 = 2000. NULL for ENTRY plans."
        ),
    )

    max_users_for_scalable = Column(
        Integer,
        nullable=True,
        comment=(
            "SCALABLE plans only. "
            "The maximum/last option in the user count dropdown. "
            "A2 = 5500, B2 = 5000. NULL for ENTRY plans."
        ),
    )

    allowed_user_counts = Column(
        JSONB,
        nullable=True,
        comment=(
            "SCALABLE plans only. "
            "The exact ordered list of selectable user counts shown in the dropdown. "
            "A2: [1500, 2500, 3500, 4500, 5500] "
            "B2: [2000, 3000, 4000, 5000] "
            "NULL for ENTRY plans."
        ),
    )

    user_count_step = Column(
        Integer,
        nullable=True,
        comment=(
            "SCALABLE plans only. Step size between user count options. "
            "A2 = 1000 (1500 → 2500 → 3500 ...). "
            "B2 = 1000 (2000 → 3000 → 4000 ...). "
            "Used to validate selected_max_users on the subscription."
        ),
    )

    # ── Pricing ───────────────────────────────────────────────────────────────

    pricing_model = Column(
        Enum(PricingModel, name="pricing_model_enum", schema="platform"),
        nullable=False,
        default=PricingModel.FLAT,
        comment=(
            "How the monthly base price is computed. "
            "FLAT    = one fixed price per user tier (most common). "
            "PER_USER = price × selected_max_users. "
            "HYBRID  = flat_base + (per_user_rate × selected_max_users)."
        ),
    )

    base_price_paise = Column(
        Numeric(14, 0),
        nullable=False,
        default=0,
        comment=(
            "Monthly base price in paise (1 INR = 100 paise). "
            "For ENTRY plans: this is the full price (e.g. A1 = ₹5,000/month = 500000). "
            "For SCALABLE plans: this is the price at the minimum user count. "
            "E.g. A2 at 1500 users = this amount."
        ),
    )

    per_user_increment_paise = Column(
        Numeric(14, 0),
        nullable=False,
        default=0,
        comment=(
            "SCALABLE plans only. "
            "Additional price per user_count_step users above the minimum. "
            "E.g. A2: min=1500, step=1000, increment=50000 (₹500/month per 1000 extra users). "
            "Price at 2500 = base + 1 × increment. "
            "Price at 3500 = base + 2 × increment. "
            "0 for ENTRY plans."
        ),
    )

    currency = Column(
        Enum(Currency, name="currency_enum", schema="platform"),
        nullable=False,
        default=Currency.INR,
        comment="Billing currency. INR for India, USD for international schools.",
    )

    # ── Tenure Discount Table ─────────────────────────────────────────────────

    tenure_discounts = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Discount percent offered for each tenure length. "
            "Keys are tenure in months (as strings for JSON compatibility). "
            "Values are discount percentages. "
            "Example: { "
            "  '1':  0.00,   "
            "  '3':  5.00,   "
            "  '6':  10.00,  "
            "  '12': 15.00,  "
            "  '24': 20.00,  "
            "  '36': 25.00   "
            "} "
            "When platform team assigns plan with tenure_months=12, "
            "SchoolSubscriptionPricing uses tenure_discounts['12'] = 15.00."
        ),
    )

    # ── Tax Configuration ─────────────────────────────────────────────────────

    tax_percent = Column(
        Numeric(5, 2),
        nullable=False,
        default=18.00,
        comment=(
            "Tax rate applied to the discounted subtotal. "
            "18.00 = 18% GST (India default). "
            "0.00  = tax-exempt (NGO/charitable schools with valid certificate)."
        ),
    )

    tax_label = Column(
        String(50),
        nullable=False,
        default="GST",
        comment="Tax label printed on invoice. E.g. 'GST', 'VAT', 'Service Tax'",
    )

    hsn_sac_code = Column(
        String(20),
        nullable=True,
        default="9984",
        comment=(
            "HSN/SAC code for tax classification. "
            "9984 = Online Information and Database Retrieval Services (India)."
        ),
    )

    # ── Storage Limits ────────────────────────────────────────────────────────

    max_storage_gb = Column(
        Integer,
        nullable=True,
        comment=(
            "Maximum file/media storage included in this plan, in GB. "
            "NULL = unlimited storage (Enterprise/custom plans only)."
        ),
    )

    # ── Module Access ─────────────────────────────────────────────────────────

    included_modules = Column(
        JSONB,
        nullable=False,
        default=list,
        comment=(
            "List of module codes included in this plan. "
            "API Gateway enforces module access using this list per request. "
            "Example for Professional plan: "
            "['ACADEMICS', 'FINANCE', 'HR', 'COMMUNICATION', "
            " 'LMS', 'LIBRARY', 'ADMIN']"
        ),
    )

    module_add_ons = Column(
        JSONB,
        nullable=False,
        default=list,
        comment=(
            "Modules available as optional paid additions to this plan. "
            "Each entry: {module: 'HOSTEL', monthly_price_paise: 200000} "
            "Selected add-ons are stored on SchoolSubscription.active_add_ons."
        ),
    )

    features = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Fine-grained feature flags included in this plan. "
            "Example: { "
            "  'api_access': false, "
            "  'custom_reports': false, "
            "  'white_label': false, "
            "  'sso_google': false, "
            "  'sso_microsoft': false, "
            "  'priority_support': false, "
            "  'dedicated_csm': false, "
            "  'data_export_csv': true, "
            "  'bulk_import': true, "
            "  'advanced_analytics': false "
            "}"
        ),
    )

    # ── Free Trial Configuration ──────────────────────────────────────────────

    trial_days = Column(
        Integer,
        nullable=False,
        default=0,
        comment=(
            "Free trial days before any payment is required. "
            "0 = no trial period for this plan. "
            "Only the FREE_TRIAL plan row should have this > 0."
        ),
    )

    trial_max_users = Column(
        Integer,
        nullable=True,
        default=None,
        comment=(
            "User cap enforced during the trial period. "
            "NULL = same as the plan's fixed_max_users or selected count. "
            "Set to a lower value to restrict trial access (e.g. 50 users max)."
        ),
    )

    trial_included_modules = Column(
        JSONB,
        nullable=True,
        default=None,
        comment=(
            "Modules available during trial. "
            "NULL = use included_modules (full access). "
            "Typical trial restriction: ['ACADEMICS', 'COMMUNICATION'] only."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    school_subscriptions = relationship(
        "SchoolSubscription",
        back_populates="plan",
        foreign_keys="SchoolSubscription.plan_id",
    )

    def __repr__(self) -> str:
        return (
            f"<SubscriptionPlan "
            f"code={self.code!r} "
            f"family={self.family} "
            f"variant={self.variant}>"
        )
        