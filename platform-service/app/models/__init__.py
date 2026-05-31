"""
Platform Service — Models Package

Exposes all SQLAlchemy model classes for use across the service.
Import from here, not from individual files.

Usage:
    from app.models import Tenant, TenantSubscription, SubscriptionPlan
    from app.models import TenantOnboarding, BillingInvoice
    from app.models import SubscriptionUsageSnapshot, TenantFeatureFlag
    from app.models import Base  # for Alembic metadata

File → Model mapping:
    base.py                → Base, BaseModel
    tenant.py              → Tenant, TenantStatus, TenantType
    tenant_onboarding.py   → TenantOnboarding, OnboardingStage, OnboardingChannel
    subscription_plan.py   → SubscriptionPlan, PlanTier, BillingCycle, PricingModel
    tenant_subscription.py → TenantSubscription, SubscriptionStatus, SubscriptionSource
    billing_and_flags.py   → BillingInvoice, InvoiceStatus
                          → SubscriptionUsageSnapshot
                          → TenantFeatureFlag
"""

# ── Base (must be imported first — all models depend on it) ─────────────────
from .base import Base, BaseModel

# ── Tenant ───────────────────────────────────────────────────────────────────
from .tenant import Tenant, TenantStatus, TenantType

# ── Onboarding ───────────────────────────────────────────────────────────────
from .tenant_onboarding import TenantOnboarding, OnboardingStage, OnboardingChannel

# ── Subscription Plan (product catalog) ─────────────────────────────────────
from .subscription_plan import (
    SubscriptionPlan,
    PlanTier,
    BillingCycle,
    PricingModel,
)

# ── Tenant Subscription (purchased plan per tenant) ──────────────────────────
from .tenant_subscription import (
    TenantSubscription,
    SubscriptionStatus,
    SubscriptionSource,
)

# ── Billing & Feature Flags ───────────────────────────────────────────────────
from .billing_and_flags import (
    BillingInvoice,
    InvoiceStatus,
    SubscriptionUsageSnapshot,
    TenantFeatureFlag,
)

__all__ = [
    # Base
    "Base",
    "BaseModel",
    # Tenant
    "Tenant",
    "TenantStatus",
    "TenantType",
    # Onboarding
    "TenantOnboarding",
    "OnboardingStage",
    "OnboardingChannel",
    # Plans
    "SubscriptionPlan",
    "PlanTier",
    "BillingCycle",
    "PricingModel",
    # Subscriptions
    "TenantSubscription",
    "SubscriptionStatus",
    "SubscriptionSource",
    # Billing & Flags
    "BillingInvoice",
    "InvoiceStatus",
    "SubscriptionUsageSnapshot",
    "TenantFeatureFlag",
]