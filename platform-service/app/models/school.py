"""School model — the operational and billing unit.

Each school belongs to exactly one tenant. Subscriptions are scoped here.
Unique subdomain per school (RFC-1035 validated).
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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PlatformBase
from app.db.mixins import PrimaryKeyMixin, SoftDeleteMixin
from app.models.enums import SchoolStatus

if TYPE_CHECKING:
    from app.models.subscription import Subscription
    from app.models.tenant import Tenant


class School(PrimaryKeyMixin, SoftDeleteMixin, PlatformBase):
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
    )

    # ── Columns ──────────────────────────────────────────────────────────
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"),
        nullable=False,
    )
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
    address: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )
    contact_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    contact_phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    # ── Relationships ────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="schools",
        lazy="joined",
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription",
        back_populates="school",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<School id={self.id!s} subdomain={self.subdomain!r} "
            f"status={self.status.value}>"
        )
