"""
School Model - Physical School/Campus Entity.

Module Purpose:
  Represents individual school locations within a tenant organization.
  Each school has independent subscriptions and can have multiple domains.

Architecture:
  - School (child) -> Tenant (parent, many-to-one)
  - School -> SchoolSubscriptions (1-to-many, billing per school)
  - School -> SchoolDomain (1-to-1, one domain per school)
  - Billing boundary is at school level

Key Features:
  - Subdomain-based isolation
  - Board type support (CBSE, ICSE, STATE, IB, IGCSE)
  - Address and contact information
  - Timezone and academic year configuration
  - Status tracking (ACTIVE, INACTIVE, ARCHIVED)

Usage:
  Every school must belong to exactly one tenant.
  Multiple schools can belong to same tenant (school groups).
"""

import enum

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class SchoolStatus(str, enum.Enum):
    """
    School operational status.

    States:
        ACTIVE: Currently operational
        INACTIVE: Temporarily closed/paused
        ARCHIVED: Historical record, no access
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class BoardType(str, enum.Enum):
    """
    Educational board/curriculum type.

    Boards:
        CBSE: Central Board of Secondary Education (India)
        ICSE: Indian Certificate of Secondary Education
        STATE: State board curriculum
        IB: International Baccalaureate
        IGCSE: International General Certificate of Secondary Education
        OTHER: Custom or other curriculum
    """

    CBSE = "CBSE"
    ICSE = "ICSE"
    STATE = "STATE"
    IB = "IB"
    IGCSE = "IGCSE"
    OTHER = "OTHER"


class School(BaseModel):
    """
    Represents a physical school/campus.

    Examples:
        Green Valley Bangalore
        Green Valley Hyderabad
        ABC Public School
    """

    __tablename__ = "schools"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(
        String(255),
        nullable=False,
        index=True,
    )

    code = Column(
        String(50),
        nullable=False,
        index=True,
    )

    subdomain = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    board = Column(
        Enum(BoardType, name="board_type_enum"),
        nullable=True,
    )

    email = Column(
        String(255),
        nullable=True,
    )

    phone_number = Column(
        String(20),
        nullable=True,
    )

    address = Column(
        String(255),
        nullable=True,
    )

    city = Column(
        String(100),
        nullable=True,
    )

    state = Column(
        String(100),
        nullable=True,
    )

    country = Column(
        String(100),
        nullable=True,
    )

    pincode = Column(
        String(20),
        nullable=True,
    )

    timezone = Column(
        String(100),
        nullable=False,
        default="Asia/Kolkata",
    )

    status = Column(
        Enum(SchoolStatus, name="school_status_enum"),
        nullable=False,
        default=SchoolStatus.ACTIVE,
        index=True,
    )

    academic_year_start_month = Column(
        Integer,
        nullable=True,
        comment="Month (1-12) when academic year starts. Example: 4 for April (India), 1 for January (US/UK)",
    )

    tenant = relationship(
        "Tenant",
        back_populates="schools",
    )

    subscriptions = relationship(
        "SchoolSubscription",
        back_populates="school",
    )

    domain = relationship(
        "SchoolDomain",
        back_populates="school",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code",
            name="uq_school_tenant_code"
        ),
    )

    def __repr__(self) -> str:
        """
        String representation of School.

        Returns:
            String in format: <School(id=uuid, school_name=Green Valley)>
        """
        return (
            f"<School(id={self.id}, "
            f"school_name={self.name})>"
        )
