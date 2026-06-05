"""
Subscription Plan Model - Product Catalog.

Module Purpose:
  Defines available subscription tiers and their capabilities.
  Master product catalog for the SmartSync platform.
  Immutable product definitions referenced by school subscriptions.

Architecture:
  - SubscriptionPlan (master entity)
    - Referenced by SchoolSubscriptions (1-to-many)
    - Defines pricing, billing cycles, and feature sets
    - Independent of tenant/school hierarchy

Key Features:
  - Multiple pricing models: FLAT, PER_STUDENT, PER_USER, HYBRID
  - Flexible billing cycles: MONTHLY, QUARTERLY, ANNUAL
  - Plan tiers: FREE_TRIAL, STARTER, PROFESSIONAL, ENTERPRISE, GOVERNMENT, CUSTOM
  - Feature flags as JSON (dynamic, pluggable)
  - Module add-ons for optional features
  - Usage limits (students, teachers, storage, roles, schools)
  - Trial period configuration
  - Display customization (order, highlight text)

Usage:
  Created and managed by admins.
  Referenced during school subscription creation.
  Used to enforce feature access and usage limits.
"""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import BaseModel


class BillingCycle(str, enum.Enum):
    """
    Subscription billing frequency.

    Cycles:
        MONTHLY: Monthly billing
        QUARTERLY: Quarterly (3-month) billing
        ANNUAL: Yearly billing
    """

    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"


class PlanTier(str, enum.Enum):
    """
    Subscription plan tier/level.

    Tiers:
        FREE_TRIAL: Trial access, limited features
        STARTER: Entry-level plan
        PROFESSIONAL: Mid-tier plan with standard features
        ENTERPRISE: High-tier plan with advanced features
        GOVERNMENT: Special government pricing tier
        CUSTOM: Custom plan for special agreements
    """

    FREE_TRIAL = "FREE_TRIAL"
    STARTER = "STARTER"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"
    GOVERNMENT = "GOVERNMENT"
    CUSTOM = "CUSTOM"


class PricingModel(str, enum.Enum):
    """
    Subscription pricing calculation method.

    Models:
        FLAT: Fixed price regardless of usage
        PER_STUDENT: Per active student count
        PER_USER: Per active user (teachers, staff)
        HYBRID: Combination of flat + per-student/user
    """

    FLAT = "FLAT"
    PER_STUDENT = "PER_STUDENT"
    PER_USER = "PER_USER"
    HYBRID = "HYBRID"


class SubscriptionPlan(BaseModel):
    """
    Platform Product Catalog

    Examples:
        Starter
        Professional
        Enterprise
    """

    __tablename__ = "subscription_plans"

    # Identity
    name = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    code = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    tier = Column(
        Enum(PlanTier, name="plan_tier_enum"),
        nullable=False,
        index=True,
    )

    description = Column(
        Text,
        nullable=True,
    )

    is_publicly_listed = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Billing
    billing_cycle = Column(
        Enum(BillingCycle, name="billing_cycle_enum"),
        nullable=False,
        default=BillingCycle.ANNUAL,
    )

    pricing_model = Column(
        Enum(PricingModel, name="pricing_model_enum"),
        nullable=False,
        default=PricingModel.FLAT,
    )

    # Pricing
    base_price_paise = Column(
        Numeric(14, 0),
        nullable=False,
        default=0,
    )

    per_student_price_paise = Column(
        Numeric(14, 0),
        nullable=False,
        default=0,
    )

    per_user_price_paise = Column(
        Numeric(14, 0),
        nullable=False,
        default=0,
    )

    currency = Column(
        String(3),
        nullable=False,
        default="INR",
    )

    # Limits
    max_total_users = Column(
        Integer,
        nullable=True,
        comment=(
            "Maximum total users allowed across ALL roles (students, teachers, parents, staff, etc.). "
            "Null = unlimited."
        ),
    )

    max_storage_gb = Column(
        Integer,
        nullable=True,
        comment="Maximum storage in GB. Null = unlimited.",
    )

    # Modules
    included_modules = Column(
        JSONB,
        nullable=False,
        default=list,
    )

    module_add_ons = Column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Features
    features = Column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Trial
    trial_days = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # Display
    display_order = Column(
        Integer,
        nullable=False,
        default=0,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    highlight_text = Column(
        String(100),
        nullable=True,
    )

    subscriptions = relationship(
        "SchoolSubscription",
        back_populates="plan",
    )

    def __repr__(self) -> str:
        """
        String representation of SubscriptionPlan.

        Returns:
            String in format: <SubscriptionPlan code='PROF' tier=PROFESSIONAL>
        """
        return (
            f"<SubscriptionPlan "
            f"code={self.code!r} "
            f"tier={self.tier}>"
        )
