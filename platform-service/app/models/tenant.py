"""Tenant model — top-level organizational container.

A tenant owns one or more schools and has no billing of its own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy import Enum as SAEnum, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PlatformBase
from app.db.mixins import PrimaryKeyMixin, SoftDeleteMixin
from app.models.enums import TenantStatus

if TYPE_CHECKING:
    from app.models.school import School


class Tenant(PrimaryKeyMixin, SoftDeleteMixin, PlatformBase):
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
    )

    # ── Columns ──────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
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
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    # ── Relationships ────────────────────────────────────────────────────
    schools: Mapped[List["School"]] = relationship(
        "School",
        back_populates="tenant",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id!s} slug={self.slug!r} status={self.status.value}>"
