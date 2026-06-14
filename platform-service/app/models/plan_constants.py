"""
Plan Constants — SmartSync Platform Service.

This module defines ALL selectable option sets for the subscription system.
Think of these as the "dropdown options" available to the platform team
when configuring or assigning a plan to a school.

Structure:
───────────────────────────────────────────────────────────────────────
Two plan FAMILIES:

  Family A — "Core Plans" (for smaller schools)
  ├── A1 — Fixed entry plan        → 500 users (no choice, it's fixed)
  └── A2 — Scalable core plan      → choose from: 1500, 2500, 3500, 4500, 5500

  Family B — "Growth Plans" (for larger/growing schools)
  ├── B1 — Fixed growth entry plan → 1000 users (no choice, it's fixed)
  └── B2 — Scalable growth plan    → choose from: 2000, 3000, 4000, 5000

TENURE options (selectable dropdown when assigning plan to school):
  1 month, 3 months, 6 months, 12 months, 24 months, 36 months

Why this design?
  - A1 and B1 are "entry" tiers — no configuration needed.
    Platform team just picks A1 or B1. User limit is baked in.
  - A2 and B2 are "scalable" tiers — platform team picks the variant
    AND chooses a user count from the predefined list.
  - No arbitrary numbers at PURCHASE time. Controlled vocabulary prevents pricing mistakes.
  - MID-TERM UPGRADES: Schools can increase user count to ANY number (not just tier multiples)
    via SchoolSubscriptionUpgrade table. Upgrades are prorated for remaining days.
    Example: Buy 1000 users, upgrade to 1300 users after 1 month (not limited to tiers).
───────────────────────────────────────────────────────────────────────
"""

import enum


# ═══════════════════════════════════════════════════════════════════════════════
# PLAN FAMILY  (the top-level grouping)
# ═══════════════════════════════════════════════════════════════════════════════

class PlanFamily(str, enum.Enum):
    """
    Top-level plan family.

    A = Core family  → designed for schools up to ~5500 users
    B = Growth family → designed for larger schools up to ~5000 (in 1000 steps)

    Why separate families instead of one list?
    Because A and B have different pricing baselines and different
    step sizes. Core (A) grows in 1000-user steps. Growth (B)
    grows in 1000-user steps but at a higher price per user.
    They are marketed differently and have different module bundles.
    """
    CORE   = "CORE"    # Family A
    GROWTH = "GROWTH"  # Family B


# ═══════════════════════════════════════════════════════════════════════════════
# PLAN VARIANT  (the tier within a family)
# ═══════════════════════════════════════════════════════════════════════════════

class PlanVariant(str, enum.Enum):
    """
    Variant within a plan family.

    ENTRY    = Fixed user count, no choice required. (A1 or B1)
    SCALABLE = Platform team selects a user count from a fixed list. (A2 or B2)

    Combining PlanFamily + PlanVariant gives the full plan identity:
        CORE   + ENTRY    = A1  (500 users, fixed)
        CORE   + SCALABLE = A2  (choose: 1500 / 2500 / 3500 / 4500 / 5500)
        GROWTH + ENTRY    = B1  (1000 users, fixed)
        GROWTH + SCALABLE = B2  (choose: 2000 / 3000 / 4000 / 5000)
    """
    ENTRY    = "ENTRY"
    SCALABLE = "SCALABLE"
    

# ═══════════════════════════════════════════════════════════════════════════════
# CAPACITY EXPANSION TYPE 
# ═══════════════════════════════════════════════════════════════════════════════

class ExpansionType(str, enum.Enum):
    """
    Identifies the specific classification of an upgrade applied to an active subscription.
    
    In a multi-tenant SaaS environment, tracking the *intent* of an upgrade is 
    critical for analytics, revenue reporting, and webhook event routing. 
    This enum distinguishes a pure user-seat increase from a fundamental 
    plan migration (e.g., moving from an Entry plan to a Scalable plan).
    
    Usage:
        - Stored in the database to categorize upgrade history.
        - Used by the financial reporting service to isolate revenue generated 
          specifically from capacity boosters versus base plan sales.
    """
    USER_CAPACITY_EXPANSION = "EXPANSION"


# ═══════════════════════════════════════════════════════════════════════════════
# USER COUNT OPTIONS  (the selectable dropdown values)
# ═══════════════════════════════════════════════════════════════════════════════

class CoreScalableUserCount(int, enum.Enum):
    """
    Selectable user count options for the A2 (Core Scalable) plan.

    Platform team picks ONE of these when assigning an A2 plan to a school.
    Multiples of 1000, starting from 1500.

    Options:
        USERS_1500 →  1,500 users
        USERS_2500 →  2,500 users
        USERS_3500 →  3,500 users
        USERS_4500 →  4,500 users
        USERS_5500 →  5,500 users
    """
    USERS_1500 = 1500
    USERS_2500 = 2500
    USERS_3500 = 3500
    USERS_4500 = 4500
    USERS_5500 = 5500


class GrowthScalableUserCount(int, enum.Enum):
    """
    Selectable user count options for the B2 (Growth Scalable) plan.

    Platform team picks ONE of these when assigning a B2 plan to a school.
    Multiples of 1000, starting from 2000.

    Options:
        USERS_2000 →  2,000 users
        USERS_3000 →  3,000 users
        USERS_4000 →  4,000 users
        USERS_5000 →  5,000 users
    """
    USERS_2000 = 2000
    USERS_3000 = 3000
    USERS_4000 = 4000
    USERS_5000 = 5000


# Fixed user counts for entry plans (not selectable — hardcoded)
CORE_ENTRY_USER_COUNT   = 500   # A1 — always 500, no choice
GROWTH_ENTRY_USER_COUNT = 1000  # B1 — always 1000, no choice


# ═══════════════════════════════════════════════════════════════════════════════
# EXPANSION COUNT (The selectable dropdown values)
# ═══════════════════════════════════════════════════════════════════════════════

class CapacityExpansionPack(int, enum.Enum):
    """
    Standardized mid-term capacity expansion values.
    
    These are the exact, strictly enforced values that populate the "Add Users" 
    dropdown in the platform administration UI. 
    
    Business Logic:
        - Any school on an active CORE or GROWTH base plan can purchase these fixed blocks.
        - By enforcing strict +500 or +1000 increments, the platform prevents 
          fragmented, arbitrary user count requests (e.g., +312 users). 
        - This standardizes prorated billing calculations, ensures clean 
          financial forecasting, and prevents the need to manage complex, 
          custom pricing edge cases for individual tenants.
          
    Options:
        PLUS_500  → Adds exactly 500 users to the current subscription limit.
        PLUS_1000 → Adds exactly 1000 users to the current subscription limit.
    """
    PLUS_500 = 500
    PLUS_1000 = 1000


# ═══════════════════════════════════════════════════════════════════════════════
# TENURE OPTIONS  (subscription duration — selectable dropdown)
# ═══════════════════════════════════════════════════════════════════════════════

class TenureMonths(int, enum.Enum):
    """
    Selectable tenure (duration) options for a school subscription.

    Platform team picks ONE of these when assigning any plan to a school.
    The subscription end_date is calculated as: start_date + tenure months.

    Options:
        ONE_MONTH      →   1 month
        THREE_MONTHS   →   3 months  (quarter)
        SIX_MONTHS     →   6 months  (half-year)
        TWELVE_MONTHS  →  12 months  (1 year — most common)
        TWENTY_FOUR    →  24 months  (2 years — discounted)
        THIRTY_SIX     →  36 months  (3 years — maximum discount)

    Longer tenure = higher discount (configured in SubscriptionPlan.tenure_discounts).
    """
    ONE_MONTH     = 1
    THREE_MONTHS  = 3
    SIX_MONTHS    = 6
    TWELVE_MONTHS = 12
    TWENTY_FOUR   = 24
    THIRTY_SIX    = 36


# ═══════════════════════════════════════════════════════════════════════════════
# PRICING MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class PricingModel(str, enum.Enum):
    """
    How the base price is calculated.

    FLAT        → Single fixed price for the selected user count.
                  Price does not change based on actual usage within the limit.
                  E.g. A1 = ₹X/month flat for up to 500 users.

    PER_USER    → Price = per_user_price_paise × selected_max_users.
                  Useful for large schools where the per-user rate is negotiated.

    HYBRID      → base_price_paise (flat component) +
                  (per_user_price_paise × selected_max_users).
                  Rare — used for custom/enterprise negotiations.
    """
    FLAT     = "FLAT"
    PER_USER = "PER_USER"
    HYBRID   = "HYBRID"


# ═══════════════════════════════════════════════════════════════════════════════
# CURRENCY
# ═══════════════════════════════════════════════════════════════════════════════

class Currency(str, enum.Enum):
    """
    Supported billing currencies.

    INR → Indian Rupee (primary)
    USD → US Dollar (international schools)
    """
    INR = "INR"
    USD = "USD"


# ═══════════════════════════════════════════════════════════════════════════════
# FREE TRIAL CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class TrialStatus(str, enum.Enum):
    """
    Status of a school's free trial.

    NOT_STARTED  → Trial granted but school hasn't logged in yet
    ACTIVE       → Trial currently running
    EXPIRED      → Trial period ended, school not yet converted
    CONVERTED    → Trial ended, school purchased a paid plan
    CANCELLED    → Trial cancelled by school or platform team
    """
    NOT_STARTED = "NOT_STARTED"
    ACTIVE      = "ACTIVE"
    EXPIRED     = "EXPIRED"
    CONVERTED   = "CONVERTED"
    CANCELLED   = "CANCELLED"
    