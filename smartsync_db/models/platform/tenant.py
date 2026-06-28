"""Tenant model — top-level organizational container.

A tenant represents an education group, trust, or management body
that owns one or more schools.  The tenant itself has no billing —
all subscriptions are scoped to individual schools.
"""

from __future__ import annotations
from typing import Optional
from typing import TYPE_CHECKING, List

from sqlalchemy import Enum as SAEnum, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smartsync_db.base import Base, SoftDeleteMixin, AuditMixin
from .enums import TenantStatus, TenantType

if TYPE_CHECKING:
    from .school import School


class Tenant(SoftDeleteMixin, AuditMixin, Base):
    """Top-level organizational container.

    Owns one or more :class:`School` instances. Carries no billing
    of its own — subscriptions are scoped to schools.
    """

    __tablename__ = "tenants"
    __table_args__ = (
        Index(
            "uq_tenants_slug_active",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_tenants_code_active",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"schema": "platform"},
    )

    # ── Columns ──────────────────────────────────────────────────────────
    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Unique tenant code for multi-tenant support"
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    
    status: Mapped[TenantStatus] = mapped_column(
        SAEnum(
            TenantStatus,
            name="tenant_status",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
        server_default=TenantStatus.ACTIVE.value,
    )

    type: Mapped[TenantType] = mapped_column(
        SAEnum(
            TenantType,
            name="tenant_type_enum",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
        server_default=TenantType.SINGLE_SCHOOL.value,
    )

    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # ── Relationships ────────────────────────────────────────────────────
    schools: Mapped[List["School"]] = relationship(
        "School",
        back_populates="tenant",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id!s} slug={self.slug!r} status={self.status.value}>"

