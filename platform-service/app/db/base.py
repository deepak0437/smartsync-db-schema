from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

from app.db.mixins import PrimaryKeyMixin, SoftDeleteMixin

PLATFORM_SCHEMA = "platform"

convention = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class PlatformBase(DeclarativeBase):
    metadata = MetaData(schema=PLATFORM_SCHEMA, naming_convention=convention)


class BaseModel(PrimaryKeyMixin, SoftDeleteMixin, PlatformBase):
    """Abstract base for all standard platform models.

    Provides:
    - ``id`` UUID primary key (via PrimaryKeyMixin)
    - ``created_at``, ``updated_at`` timestamps (via TimestampMixin → SoftDeleteMixin)
    - ``deleted_at`` soft-delete marker (via SoftDeleteMixin)

    Exception: ``SubscriptionHistory`` uses ``AuditOnlyMixin`` instead and
    inherits directly from ``PrimaryKeyMixin + AuditOnlyMixin + PlatformBase``.
    """

    __abstract__ = True
