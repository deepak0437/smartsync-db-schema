"""
Tenant Model - Multi-Tenant Organization Entity.

Module Purpose:
  Represents customer organizations in the SmartSync platform.
  Each tenant can have multiple schools, and each school can have separate subscriptions.

Architecture:
  - Tenant (parent) -> Schools (children, 1-to-many)
  - Tenant -> SchoolSubscriptions (1-to-many, for billing tracking)
  - Supports different organizational types: SINGLE_SCHOOL, SCHOOL_GROUP, GOVERNMENT_BLOCK

Usage:
  Used in platform-service as the primary multi-tenancy boundary.
  All schools are linked to exactly one tenant.
"""

import enum

from sqlalchemy import Column, Enum, String
from sqlalchemy.orm import relationship

from .base import BaseModel


class TenantStatus(str, enum.Enum):
    """
    Tenant organizational lifecycle status.

    States:
        ACTIVE: Organization is operational
        INACTIVE: Organization temporarily paused
        ARCHIVED: Historical record, no longer in use
    
    Note: Billing/subscription status is managed at School level.
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class TenantType(str, enum.Enum):
    """
    Organizational structure type.

    Types:
        SINGLE_SCHOOL: Independent school
        SCHOOL_GROUP: Education company with multiple schools
        GOVERNMENT_BLOCK: Government education department/block
        UNIVERSITY: Higher education institution
    """

    SINGLE_SCHOOL = "SINGLE_SCHOOL"
    SCHOOL_GROUP = "SCHOOL_GROUP"
    GOVERNMENT_BLOCK = "GOVERNMENT_BLOCK"


class Tenant(BaseModel):
    """
    Represents a customer organization.

    Examples:
        - ABC Public School
        - Green Valley Education Group
        - Narayana Educational Society
    """

    __tablename__ = "tenants"

    name = Column(
        String(255),
        nullable=False,
        index=True,
    )

    code = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    type = Column(
        Enum(TenantType, name="tenant_type_enum"),
        nullable=False,
        default=TenantType.SINGLE_SCHOOL,
    )

    slug = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    website = Column(
        String(255),
        nullable=True,
    )

    status = Column(
        Enum(TenantStatus, name="tenant_status_enum"),
        nullable=False,
        default=TenantStatus.ACTIVE,
        index=True,
    )

    schools = relationship(
        "School",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    subscriptions = relationship(
        "SchoolSubscription",
        back_populates="tenant",
    )

    def __repr__(self) -> str:
        """
        String representation of Tenant.

        Returns:
            String in format: <Tenant(id=uuid, organization_name=ABC Public School)>
        """
        return (
            f"<Tenant(id={self.id}, "
            f"organization_name={self.name})>"
        )
        