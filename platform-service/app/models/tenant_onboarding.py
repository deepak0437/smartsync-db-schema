"""
Tenant Onboarding Model — Platform Service

Tracks the complete onboarding journey from first contact to go-live.
This is a separate table (not merged into tenants) because:
  - It has its own lifecycle and status transitions
  - It is written frequently during setup, rarely after go-live
  - It allows querying onboarding funnel health independently

Onboarding Stages:
    LEAD_CAPTURED       → Inquiry received, sales process started
    DEMO_SCHEDULED      → Demo meeting booked
    DEMO_COMPLETED      → Demo done, proposal shared
    PROPOSAL_SENT       → Formal pricing proposal shared
    CONTRACT_SIGNED     → Legal agreement executed
    SETUP_IN_PROGRESS   → Technical setup ongoing (user import, config)
    TRAINING_SCHEDULED  → Training sessions booked
    TRAINING_COMPLETED  → All training done
    GO_LIVE             → Tenant is live on production
    CHURNED             → Tenant cancelled before or after go-live

Each stage transition is timestamped independently for funnel analysis.
"""

import enum

from sqlalchemy import Column, Date, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class OnboardingStage(str, enum.Enum):
    LEAD_CAPTURED = "LEAD_CAPTURED"
    DEMO_SCHEDULED = "DEMO_SCHEDULED"
    DEMO_COMPLETED = "DEMO_COMPLETED"
    PROPOSAL_SENT = "PROPOSAL_SENT"
    CONTRACT_SIGNED = "CONTRACT_SIGNED"
    SETUP_IN_PROGRESS = "SETUP_IN_PROGRESS"
    TRAINING_SCHEDULED = "TRAINING_SCHEDULED"
    TRAINING_COMPLETED = "TRAINING_COMPLETED"
    GO_LIVE = "GO_LIVE"
    CHURNED = "CHURNED"


class OnboardingChannel(str, enum.Enum):
    INBOUND_WEB = "INBOUND_WEB"         # School found us online
    OUTBOUND_SALES = "OUTBOUND_SALES"   # Sales team reached out
    REFERRAL = "REFERRAL"               # Referred by another school
    RESELLER = "RESELLER"               # Through a reseller partner
    GOVERNMENT = "GOVERNMENT"           # Government scheme/tender
    EVENT = "EVENT"                     # Education expo / conference


class TenantOnboarding(BaseModel):
    """
    Tracks every milestone in a tenant's onboarding journey.

    One row per tenant. Updated in place as stages progress.
    Stage timestamps are stored separately so funnel conversion
    can be measured precisely.
    """

    __tablename__ = "tenant_onboardings"

    # ── Tenant Link ───────────────────────────────────────────────────────────
    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
        index=True,
        comment="FK → tenants.id. One onboarding record per tenant.",
    )

    # ── Current Stage ─────────────────────────────────────────────────────────
    current_stage = Column(
        Enum(OnboardingStage, name="onboarding_stage_enum"),
        nullable=False,
        default=OnboardingStage.LEAD_CAPTURED,
        index=True,
        comment="Current stage in the onboarding funnel",
    )

    # ── Stage Timestamps (populated as each stage is reached) ─────────────────
    lead_captured_at = Column(
        Date,
        nullable=True,
        comment="Date when this tenant was first captured as a lead",
    )
    demo_scheduled_at = Column(
        Date,
        nullable=True,
        comment="Date when product demo was scheduled",
    )
    demo_completed_at = Column(
        Date,
        nullable=True,
        comment="Date when product demo was conducted",
    )
    proposal_sent_at = Column(
        Date,
        nullable=True,
        comment="Date when pricing proposal was formally sent",
    )
    contract_signed_at = Column(
        Date,
        nullable=True,
        comment="Date when the contract / agreement was signed",
    )
    setup_started_at = Column(
        Date,
        nullable=True,
        comment="Date when technical setup (data import, config) began",
    )
    setup_completed_at = Column(
        Date,
        nullable=True,
        comment="Date when setup was marked complete by the implementation team",
    )
    training_scheduled_at = Column(
        Date,
        nullable=True,
        comment="Date when training sessions were scheduled",
    )
    training_completed_at = Column(
        Date,
        nullable=True,
        comment="Date when all training sessions were completed",
    )
    go_live_date = Column(
        Date,
        nullable=True,
        index=True,
        comment="Date when the tenant went live on production. Critical metric.",
    )
    churned_at = Column(
        Date,
        nullable=True,
        comment="Date when tenant churned (if applicable)",
    )
    churn_reason = Column(
        String(500),
        nullable=True,
        comment="Reason for churn. E.g. 'Cost', 'Missing feature', 'Switched competitor'",
    )

    # ── Acquisition ───────────────────────────────────────────────────────────
    acquisition_channel = Column(
        Enum(OnboardingChannel, name="onboarding_channel_enum"),
        nullable=True,
        comment="How this tenant was acquired",
    )
    referred_by_tenant_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="tenant_id that referred this school (if acquisition_channel = REFERRAL)",
    )
    reseller_partner_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Partner/reseller account ID (if acquisition_channel = RESELLER)",
    )
    utm_source = Column(
        String(255),
        nullable=True,
        comment="UTM source from the lead capture URL",
    )
    utm_medium = Column(
        String(255),
        nullable=True,
        comment="UTM medium from the lead capture URL",
    )
    utm_campaign = Column(
        String(255),
        nullable=True,
        comment="UTM campaign from the lead capture URL",
    )

    # ── Account Management ────────────────────────────────────────────────────
    account_manager_user_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Internal SmartSync user_id of the assigned account manager",
    )
    implementation_engineer_user_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Internal SmartSync user_id of the assigned implementation engineer",
    )

    # ── Setup Checklist (JSON, flexible) ──────────────────────────────────────
    setup_checklist = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Tracks completion of each setup step. "
            "E.g. {"
            "  'admin_users_imported': true, "
            "  'students_imported': false, "
            "  'classes_configured': true, "
            "  'fee_structure_set': false, "
            "  'email_templates_configured': false"
            "}"
        ),
    )

    # ── Training Details ──────────────────────────────────────────────────────
    training_sessions_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of training sessions conducted so far",
    )
    training_notes = Column(
        Text,
        nullable=True,
        comment="Internal notes from implementation team about training",
    )

    # ── Expected Users (for capacity planning) ────────────────────────────────
    expected_students = Column(
        Integer,
        nullable=True,
        comment="Approximate number of students expected. Used for infrastructure sizing.",
    )
    expected_teachers = Column(
        Integer,
        nullable=True,
        comment="Approximate number of teachers expected",
    )
    expected_admin_users = Column(
        Integer,
        nullable=True,
        comment="Approximate number of admin users expected",
    )

    # ── Internal Notes ────────────────────────────────────────────────────────
    sales_notes = Column(
        Text,
        nullable=True,
        comment="Free-text notes from sales team about the deal",
    )
    implementation_notes = Column(
        Text,
        nullable=True,
        comment="Technical notes from implementation team",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    tenant = relationship(
        "Tenant",
        back_populates="onboarding",
        foreign_keys=[tenant_id],
    )

    def __repr__(self) -> str:
        return (
            f"<TenantOnboarding tenant_id={self.tenant_id} "
            f"stage={self.current_stage} go_live={self.go_live_date}>"
        )
        