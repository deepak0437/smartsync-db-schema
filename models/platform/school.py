"""School model — the operational and billing unit.

Each school belongs to exactly one tenant. A tenant (school group)
owns one or more schools. Subscriptions, addons, and capacity counters
are all scoped to a school. Unique subdomain per school (RFC-1035 validated).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from base import Base
from enums import SchoolStatus

if TYPE_CHECKING:
    from school_subscription import SchoolSubscription
    from tenant import Tenant


class School(Base):
    """Operational and billing unit within a tenant.

    Each school has a unique subdomain and at most one active subscription
    at any point in time.
    """

    __tablename__ = "schools"
    __table_args__ = (
        CheckConstraint(
            r"subdomain ~ '^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?$'",
            name="valid_subdomain",
        ),
        Index(
            "uq_schools_subdomain_active",
            "subdomain",
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
    )

    # ── Columns ──────────────────────────────────────────────────────────
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"),
        nullable=False,
    )
    #code for school also 
    # create a board column - and map it to enum BoardType 
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
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
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True, #false
    )
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True, #false
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment=(
            "Extensible school attributes. "
            "Expected keys: board (str, e.g. 'CBSE'), medium (str, e.g. 'English'), "
            "affiliation_number (str), udise_code (str). "
            "Governed by application-layer Pydantic validation."
        ),
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