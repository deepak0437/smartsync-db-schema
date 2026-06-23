"""PostgreSQL enum types for the platform schema.

Each Python enum maps 1:1 to a ``CREATE TYPE platform.<name> AS ENUM (...)``
statement.  The enum types are created explicitly in Alembic migrations
(``create_type=False`` on the SQLAlchemy column) so that schema evolution
remains controlled.
"""

import enum


class TenantStatus(str, enum.Enum):
    """Operational lifecycle states for a tenant."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class SchoolStatus(str, enum.Enum):
    """Operational lifecycle states for a school.

    Billing states (e.g. PAYMENT_DUE, SUSPENDED) are deliberately excluded.
    Billing state is derived from ``subscriptions.status`` at query time.
    """

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class PlanType(str, enum.Enum):
    """Base plan tier."""

    CORE = "CORE"
    GROWTH = "GROWTH"


class PlanVariant(str, enum.Enum):
    """Plan pricing variant."""

    ENTRY = "ENTRY"
    SCALABLE = "SCALABLE"


class SubscriptionStatus(str, enum.Enum):
    """Subscription lifecycle states."""

    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    UPGRADED = "UPGRADED"


class AddonStatus(str, enum.Enum):
    """Expansion addon lifecycle states."""

    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class HistoryEventType(str, enum.Enum):
    """All possible subscription history event types.

    This enum is append-only — new event types may be added but existing
    values must never be removed or renamed.
    """

    SUBSCRIPTION_CREATED = "SUBSCRIPTION_CREATED"
    SUBSCRIPTION_RENEWED = "SUBSCRIPTION_RENEWED"
    SUBSCRIPTION_UPGRADED = "SUBSCRIPTION_UPGRADED"
    SUBSCRIPTION_CANCELLED = "SUBSCRIPTION_CANCELLED"
    SUBSCRIPTION_EXPIRED = "SUBSCRIPTION_EXPIRED"
    ADDON_PURCHASED = "ADDON_PURCHASED"
    ADDON_CANCELLED = "ADDON_CANCELLED"
    ADDON_EXPIRED = "ADDON_EXPIRED"
    USER_COUNT_ADJUSTED = "USER_COUNT_ADJUSTED"
