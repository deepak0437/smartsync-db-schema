"""
School Domain Model - Domain Mapping for Schools.

Module Purpose:
  Manages custom and subdomain mappings for schools.
  Supports SSL/TLS configuration and domain verification.

Architecture:
  - SchoolDomain (child) -> School (parent, 1-to-1)
  - Each school has exactly one domain (primary entry point)
  - Supports custom domain mapping

Key Features:
  - Custom domain support (e.g., erp.greenvalleyschool.com)
  - SSL/TLS provisioning (auto-managed by provider)
  - Domain verification with tokens
  - Status tracking (PENDING_VERIFICATION, VERIFIED, FAILED, DISABLED)

Usage:
  Supports both SmartSync subdomains and custom domains.
  SSL certificates managed automatically.
"""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class DomainStatus(str, enum.Enum):
    """
    Domain verification and operational status.

    States:
        PENDING_VERIFICATION: Awaiting DNS/SSL verification
        VERIFIED: Ready for use, SSL active
        FAILED: Verification failed, needs correction
        DISABLED: Manually disabled or expired
    """

    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


class SchoolDomain(BaseModel):
    """
    Domain mapping for a school.

    Examples:

    greenvalley.smartsync.ai
    erp.greenvalleyschool.com
    portal.greenvalleyschool.com
    """

    __tablename__ = "school_domains"

    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    domain = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    is_custom_domain = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    status = Column(
        Enum(
            DomainStatus,
            name="domain_status_enum",
        ),
        nullable=False,
        default=DomainStatus.PENDING_VERIFICATION,
        index=True,
    )

    verified_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    verified_by = Column(
        String(255),
        nullable=False,
    )

    school = relationship(
        "School",
        back_populates="domain",
    )

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            name="uq_school_domain_1to1",
        ),
    )

    def __repr__(self) -> str:
        """
        String representation of SchoolDomain.

        Returns:
            String in format: <SchoolDomain(domain=example.com, school_id=uuid)>
        """
        return (
            f"<SchoolDomain("
            f"domain={self.domain}, "
            f"school_id={self.school_id})>"
        )
    