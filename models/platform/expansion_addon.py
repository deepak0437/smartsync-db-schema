"""ExpansionAddon model — mid-term capacity booster.

Tied to the active base subscription's remaining tenure.  The addon's
``expires_at`` must be ≤ the parent subscription's ``expires_at`` — this
invariant is enforced at the service layer since cross-table CHECK
constraints are not supported in PostgreSQL.

Once purchased, addons cannot be cancelled — they run until expiry.
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SAEnum,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from base import Base, SoftDeleteMixin, AuditMixin
from .enums import ExpansionType, CapacityExpansionPack, TenureMonths, StorageLimit



class ExpansionAddon(SoftDeleteMixin, AuditMixin, Base):
    """Mid-term capacity booster attached to an active subscription.

    Adds ``user_count`` users to the subscription's
    ``effective_max_users`` for the remaining tenure.
    """

    __tablename__ = "expansion_addons"
    __table_args__ = (
        CheckConstraint(
            "price > 0",
            name="positive_addon_price",
        ),
        # ── Indexes ──────────────────────────────────────────────────────
        Index(
            "uq_addons_code_active",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    # ── Columns ──────────────────────────────────────────────────────────
    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Unique addon code for multi-tenant support"
    )

    expansion_type: Mapped[ExpansionType] = mapped_column(
        SAEnum(
            ExpansionType,
            name="expansion_type",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
    )

    user_count: Mapped[CapacityExpansionPack] = mapped_column(
        SAEnum(
            CapacityExpansionPack,
            name="expansion_user_count",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
    )

    tenure: Mapped[TenureMonths] = mapped_column(
        SAEnum(
            TenureMonths,
            name="addon_tenure",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    discount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    discount_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    
    storage: Mapped[StorageLimit] = mapped_column(
        SAEnum(
            StorageLimit,
            name="storage_limit",
            schema="platform",
            create_type=False,
        ),
        nullable=False,
        comment="Storage limit in GB"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<ExpansionAddon id={self.id!s} code={self.code!r} status={self.status.value}>"
        )

