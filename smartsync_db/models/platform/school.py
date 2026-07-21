"""School model — the operational and billing unit.

Each school belongs to exactly one tenant. A tenant (school group)
owns one or more schools. Subscriptions, addons, and capacity counters
are all scoped to a school. Unique subdomain per school (RFC-1035 validated).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smartsync_db.base import Base, SoftDeleteMixin, AuditMixin
from .enums import SchoolStatus, BoardType

if TYPE_CHECKING:
    from .school_subscription import SchoolSubscription
    from .tenant import Tenant


class School(SoftDeleteMixin, AuditMixin, Base):
    """Operational and billing unit within a tenant.

    Each school has a unique subdomain and at most one active subscription
    at any point in time.
    """

    __tablename__ = "schools"
    __table_args__ = (
        Index(
            "uq_schools_subdomain_active",
            "subdomain",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_schools_code_active",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_schools_tenant_id_active",
            "tenant_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_schools_state_city",
            "state",
            "city",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"schema": "platform"},
    )

    # ── Columns ──────────────────────────────────────────────────────────
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("platform.tenants.id"),
        nullable=False,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Unique school code for multi-tenant support"
    )

    board: Mapped[BoardType] = mapped_column(
        SAEnum(
            BoardType,
            name="board_type",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
        server_default=BoardType.CBSE.value,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    subdomain: Mapped[str] = mapped_column(
        String(63),
        nullable=False,
    )

    status: Mapped[SchoolStatus] = mapped_column(
        SAEnum(
            SchoolStatus,
            name="school_status",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
        server_default=SchoolStatus.PENDING.value,
    )

    state: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Indian state name or code, e.g. 'Karnataka' or 'KA'",
    )

    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    pincode: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Indian PIN code. String to preserve leading zeros.",
    )

    address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Full street address / landmark line",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    phone_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # ── Onboarding approval audit ────────────────────────────────────────
    # Set by the Pending School Approval workflow (Platform Admin
    # approve/reject actions). A school stays PENDING (see `status` above)
    # until approved — only one of the approved_*/rejected_* pairs is ever
    # populated for a given school, matching whichever action was taken.
    approved_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    approved_at: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    rejected_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    rejected_at: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    approval_remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Free-text remarks from the Platform Admin, required on reject.",
    )

    # ── Relationships ────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="schools",
        lazy="joined",
    )
    subscriptions: Mapped[List["SchoolSubscription"]] = relationship(
        "SchoolSubscription",
        back_populates="school",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<School id={self.id!s} subdomain={self.subdomain!r} "
            f"status={self.status.value}>"
        )

