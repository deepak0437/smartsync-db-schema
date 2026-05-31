"""
SmartSync Platform Service
Base Model

All platform models inherit from this. Provides:
- UUID primary key
- Soft delete fields
- Full audit trail (created_by, updated_by, deleted_by)
- Timezone-aware timestamps

Usage:
    class MyModel(BaseModel):
        __tablename__ = "my_table"
        ...
"""

from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.x DeclarativeBase.
    All models in this service use this single Base so Alembic
    can discover every table in one metadata object.
    """
    pass


class BaseModel(Base):
    """
    Abstract base model inherited by every table in the platform service.

    Fields
    ------
    id          : UUID primary key — generated client-side so the value is
                  known before the INSERT hits the database. Safe for event
                  payloads and cross-service references.

    is_deleted  : Soft-delete flag. Queries must always filter
                  WHERE is_deleted = FALSE unless explicitly doing a recovery.

    deleted_at  : Timestamp when soft-delete was triggered. NULL means active.

    deleted_by  : user_id (from Auth Service) who performed the delete.
                  Cross-service reference — NOT a foreign key constraint.

    created_at  : Server-side default so the DB clock is the source of truth.

    updated_at  : Auto-updates on every row change via onupdate hook.

    created_by  : user_id who created this row.

    updated_by  : user_id who last modified this row.
    """

    __abstract__ = True

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
        comment="UUID primary key — generated application-side before INSERT",
    )

    # ── Soft Delete ───────────────────────────────────────────────────────
    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Soft delete flag — never hard-delete rows",
    )
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when this record was soft-deleted",
    )
    deleted_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="user_id (Auth Service) who performed the soft delete",
    )

    # ── Audit Trail ───────────────────────────────────────────────────────
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Row creation timestamp — set by database server clock",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last modification timestamp — auto-updated on every write",
    )
    created_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="user_id (Auth Service) who created this record",
    )
    updated_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="user_id (Auth Service) who last updated this record",
    )

    def soft_delete(self, deleted_by_user_id) -> None:
        """
        Mark this record as deleted without removing it from the database.
        Call this instead of session.delete(instance).

        Example
        -------
            tenant.soft_delete(deleted_by_user_id=current_user.id)
            session.commit()
        """
        self.is_deleted = True
        self.deleted_at = func.now()
        self.deleted_by = deleted_by_user_id

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id} is_deleted={self.is_deleted}>"
        