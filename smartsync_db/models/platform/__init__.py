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
    EmailRecipientStatus,
    HistoryEventType,
    PlanType,
    PlanVariant,
    SchoolStatus,
    StorageLimit,
    SubscriptionStatus,
    TenantStatus,
    TenantType,
    UserCount,
    CapacityExpansionPack,
)
from .email_send import EmailSend, EmailSendRecipient
from .email_template import EmailTemplate
from .expansion_addon import ExpansionAddon
from .plan import Plan
from .school import School
from .school_subscription import SchoolSubscription
from .tenant import Tenant

__all__ = [
    # Enums
    "TenantStatus",
    "TenantType",
    "SchoolStatus",
    "PlanType",
    "PlanVariant",
    "SubscriptionStatus",
    "AddonStatus",
    "HistoryEventType",
    "BoardType",
    "StorageLimit",
    "EmailRecipientStatus",
    "Tenant",
    "School",
    "Plan",
    "SchoolSubscription",
    "ExpansionAddon",
    "UserCount",
    "CapacityExpansionPack",
    "EmailTemplate",
    "EmailSend",
    "EmailSendRecipient",
]
