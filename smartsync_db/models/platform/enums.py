"""PostgreSQL enum types for the platform schema.

Each Python enum maps 1:1 to a ``CREATE TYPE platform.<name> AS ENUM (...)``
statement.  The enum types are created explicitly in Alembic migrations
(``create_type=False`` on the SQLAlchemy column) so that schema evolution
remains controlled.
"""

import enum


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT STATUS  (the top-level business information)
# ═══════════════════════════════════════════════════════════════════════════════
class TenantStatus(str, enum.Enum):
    """Operational lifecycle states for a tenant."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT TYPE
# ═══════════════════════════════════════════════════════════════════════════════
class TenantType(str, enum.Enum):
    """
    Organizational structure type.

    Types:
        SINGLE_SCHOOL: Independent school
        SCHOOL_GROUP: Education company with multiple schools
        GOVERNMENT_BLOCK: Government education department/block
        UNIVERSITY: Higher education institution
    """

    SINGLE_SCHOOL = "SINGLE_SCHOOL"
    SCHOOL_GROUP = "SCHOOL_GROUP"
    GOVERNMENT_BLOCK = "GOVERNMENT_BLOCK"


# ═══════════════════════════════════════════════════════════════════════════════
# SCHOOL STATUS  (inside tenant level group)
# ═══════════════════════════════════════════════════════════════════════════════
class SchoolStatus(str, enum.Enum):
    """Operational lifecycle states for a school.

    Billing states (e.g. PAYMENT_DUE, SUSPENDED) are deliberately excluded.
    Billing state is derived from ``subscriptions.status`` at query time.
    """

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"
    REJECTED = "REJECTED"


# ═══════════════════════════════════════════════════════════════════════════════
# PLAN TYPE  (the top-level grouping)
# ═══════════════════════════════════════════════════════════════════════════════
class PlanType(str, enum.Enum):
    """
    Top-level plan plan type.

    A = Core plan type  → designed for schools up to ~5500 users
    B = Growth plan type → designed for larger schools up to ~5000 (in 1000 steps)

    Why separate families instead of one list?
    Because A and B have different pricing baselines and different
    step sizes. Core (A) grows in 1000-user steps. Growth (B)
    grows in 1000-user steps but at a higher price per user.
    They are marketed differently and have different module bundles.
    """

    CORE = "CORE"
    GROWTH = "GROWTH"
    TRIAL = "TRIAL"


# ═══════════════════════════════════════════════════════════════════════════════
# PLAN VARIANT  (the tier within a plan type)
# ═══════════════════════════════════════════════════════════════════════════════
class PlanVariant(str, enum.Enum):
    """
    Variant within a plan plan type.

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

class UserCount(int, enum.Enum):
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
    USERS_500 = 500
    USERS_1000=  1000
    USERS_1500 = 1500
    USERS_2500 = 2500
    USERS_3500 = 3500
    USERS_4500 = 4500
    USERS_5500 = 5500
    USERS_2000 = 2000
    USERS_3000 = 3000
    USERS_4000 = 4000
    USERS_5000 = 5000


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


class SubscriptionStatus(str, enum.Enum):
    """
    Subscription lifecycle states.

    CANCELLED is intentionally omitted — subscriptions cannot be explicitly
    cancelled midway.  They either expire naturally or are superseded by
    an upgrade.  For early termination, set status to EXPIRED.
    """

    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    NO_PLAN = "NO_PLAN"


class AddonStatus(str, enum.Enum):
    """Expansion addon lifecycle states.

    CANCELLED is intentionally omitted — once purchased, addons run
    until expiry.  They cannot be cancelled midway.
    """

    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    NO_PLAN = "NO_PLAN"


class HistoryEventType(str, enum.Enum):
    """All possible subscription history event types.

    This enum is append-only — new event types may be added but existing
    values must never be removed or renamed.
    """

    SUBSCRIPTION_CREATED = "SUBSCRIPTION_CREATED"
    SUBSCRIPTION_RENEWED = "SUBSCRIPTION_RENEWED"
    SUBSCRIPTION_UPGRADED = "SUBSCRIPTION_UPGRADED"
    SUBSCRIPTION_EXPIRED = "SUBSCRIPTION_EXPIRED"
    ADDON_PURCHASED = "ADDON_PURCHASED"
    ADDON_EXPIRED = "ADDON_EXPIRED"
    USER_COUNT_ADJUSTED = "USER_COUNT_ADJUSTED"


class BoardType(str, enum.Enum):
    """Educational board affiliation."""

    CBSE = "CBSE"
    ICSE = "ICSE"
    STATE = "STATE"
    IB = "IB"
    IGCSE = "IGCSE"


class StorageLimit(int, enum.Enum):
    """Storage package labels are in GB; values are stored/calculated in MB."""

    GB_20 = 20480
    GB_30 = 30720
    GB_50 = 51200
    GB_100 = 102400
    GB_150 = 153600
    GB_200 = 204800
    GB_250 = 256000
    GB_300 = 307200
    GB_350 = 358400
    GB_400 = 409600
    GB_450 = 460800
    GB_500 = 512000


class EmailRecipientStatus(str, enum.Enum):
    """Per-recipient delivery status for an EmailSendRecipient row.

    QUEUED is the initial state set when notification-api accepts the
    publish request; the other three are populated later by polling
    notification-service's own notification_log via its internal status
    endpoint. UNKNOWN means that poll never found a matching log row (e.g.
    still in flight, or the queue-to-log write hasn't landed yet).
    """

    QUEUED = "QUEUED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    SKIPPED = "SKIPPED"
    UNKNOWN = "UNKNOWN"
