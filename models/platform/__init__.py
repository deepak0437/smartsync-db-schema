"""SmartSync Platform models — public API.

All models and enums are re-exported here for clean imports
and Alembic metadata discovery.

Usage::

    from app.models import Tenant, School, Plan, SchoolSubscription
    from app.models import TenantStatus, SchoolStatus
"""

from app.models.enums import (
    AddonStatus,
    HistoryEventType,
    PlanType,
    PlanVariant,
    SchoolStatus,
    SubscriptionStatus,
    TenantStatus,
)
from app.models.expansion_addon import ExpansionAddon
from app.models.plan import Plan
from app.models.school import School
from app.models.school_subscription import SchoolSubscription
from app.models.subscription_history import SubscriptionHistory
from app.models.tenant import Tenant

__all__ = [
    # Enums
    "TenantStatus",
    "SchoolStatus",
    "PlanType",
    "PlanVariant",
    "SubscriptionStatus",
    "AddonStatus",
    "HistoryEventType",
    # Models
    "Tenant",
    "School",
    "Plan",
    "SchoolSubscription",
    "ExpansionAddon",
    "SubscriptionHistory",
]
