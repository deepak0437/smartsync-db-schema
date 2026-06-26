"""SmartSync Platform models — public API.

All models and enums are re-exported here for clean imports
and Alembic metadata discovery.

Usage::

    from app.models import Tenant, School, Plan, SchoolSubscription
    from app.models import TenantStatus, SchoolStatus
"""

from .enums import (
    AddonStatus,
    BoardType,
    HistoryEventType,
    PlanType,
    PlanVariant,
    SchoolStatus,
    StorageLimit,
    SubscriptionStatus,
    TenantStatus,
    UserCount,
)
from .expansion_addon import ExpansionAddon
from .plan import Plan
from .school import School
from .school_subscription import SchoolSubscription
from .tenant import Tenant

__all__ = [
    # Enums
    "TenantStatus",
    "SchoolStatus",
    "PlanType",
    "PlanVariant",
    "SubscriptionStatus",
    "AddonStatus",
    "HistoryEventType",
    "BoardType",
    "StorageLimit",
    "Tenant",
    "School",
    "Plan",
    "SchoolSubscription",
    "ExpansionAddon",
    "UserCount"
]
