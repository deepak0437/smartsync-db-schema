"""
Base SQLAlchemy 2.x models with common fields for all auth-service tables.
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """SQLAlchemy 2.x declarative base."""
    pass


class BaseModel(Base):
    """
    Abstract base model with common fields for all tables.

    Provides:
    - UUID primary key
    - Soft delete support (is_deleted, deleted_at, deleted_by)
    - Audit fields (created_at, updated_at, created_by, updated_by)
    - Multi-tenancy support (tenant_id in subclasses)
    """
    __abstract__ = True

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
        comment="UUID primary key",
    )

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False, index=True, comment="Soft delete flag")
    deleted_at = Column(DateTime(timezone=True), nullable=True, comment="Timestamp of soft deletion")
    deleted_by = Column(UUID(as_uuid=True), nullable=True, comment="User who soft-deleted this record")

    # Audit fields
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp",
    )
    created_by = Column(UUID(as_uuid=True), nullable=True, comment="User who created this record")
    updated_by = Column(UUID(as_uuid=True), nullable=True, comment="User who last updated this record")

    def soft_delete(self, deleted_by_user_id=None):
        """Soft delete the record."""
        self.is_deleted = True
        self.deleted_at = utcnow()
        if deleted_by_user_id:
            self.deleted_by = deleted_by_user_id

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"


class TenantBaseModel(Base):
    """
    Base model for the tenant table itself (no tenant_id field — it IS the tenant).
    """
    __abstract__ = True

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
        comment="UUID primary key",
    )

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False, comment="Soft delete flag")
    deleted_at = Column(DateTime(timezone=True), nullable=True, comment="Timestamp of soft deletion")
    deleted_by = Column(UUID(as_uuid=True), nullable=True, comment="User who soft-deleted this record")

    # Audit fields
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp",
    )
    created_by = Column(UUID(as_uuid=True), nullable=True, comment="User who created this record")
    updated_by = Column(UUID(as_uuid=True), nullable=True, comment="User who last updated this record")

    def soft_delete(self, deleted_by_user_id=None):
        """Soft delete the record."""
        self.is_deleted = True
        self.deleted_at = utcnow()
        if deleted_by_user_id:
            self.deleted_by = deleted_by_user_id
