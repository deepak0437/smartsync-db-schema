"""Tenant model — top-level organizational container.

A tenant represents an education group, trust, or management body
that owns one or more schools.  The tenant itself has no billing —
all subscriptions are scoped to individual schools.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy import Enum as SAEnum, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.models.enums import TenantStatus

if TYPE_CHECKING:
    from app.models.school import School


class Tenant(BaseModel):
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
        comment=(
            "Extensible tenant attributes. "
            "Expected keys: region (str), board (str), group_code (str), "
            "notes (str). Governed by application-layer Pydantic validation."
        ),
    )

    # ── Relationships ────────────────────────────────────────────────────
    schools: Mapped[List["School"]] = relationship(
        "School",
        back_populates="tenant",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id!s} slug={self.slug!r} status={self.status.value}>"
