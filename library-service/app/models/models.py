"""
Library Service Models — Book catalog, issues, returns, fines.
"""
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Numeric, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from uuid import uuid4
from sqlalchemy import func


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)


class BookCategory(BaseModel):
    __tablename__ = "book_categories"
    __table_args__ = (UniqueConstraint("tenant_id", "category_code", name="uq_lib_book_category"), {"schema": "library"})
    category_code = Column(String(50), nullable=False)
    category_name = Column(String(255), nullable=False)
    parent_category_id = Column(UUID(as_uuid=True), ForeignKey("library.book_categories.id", ondelete="SET NULL"), nullable=True)
    dewey_decimal = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class Book(BaseModel):
    """Book catalog entry."""
    __tablename__ = "books"
    __table_args__ = (UniqueConstraint("tenant_id", "isbn", name="uq_lib_book_isbn"), {"schema": "library"})
    isbn = Column(String(20), nullable=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    authors = Column(JSONB, default=[], comment="Array of author names")
    publisher = Column(String(255), nullable=True)
    publication_year = Column(Integer, nullable=True)
    edition = Column(String(50), nullable=True)
    language = Column(String(30), default="English")
    category_id = Column(UUID(as_uuid=True), ForeignKey("library.book_categories.id", ondelete="SET NULL"), nullable=True)
    subject_tags = Column(JSONB, default=[], comment="Subject/topic tags")
    description = Column(Text, nullable=True)
    cover_image_url = Column(Text, nullable=True)
    total_copies = Column(Integer, default=1)
    available_copies = Column(Integer, default=1)
    location_rack = Column(String(50), nullable=True)
    location_shelf = Column(String(50), nullable=True)
    price = Column(Numeric(8, 2), nullable=True)
    is_reference_only = Column(Boolean, default=False, comment="Cannot be issued, only used in library")
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    copies = relationship("BookCopy", back_populates="book")


class BookCopy(BaseModel):
    """Individual physical copy of a book."""
    __tablename__ = "book_copies"
    __table_args__ = (UniqueConstraint("tenant_id", "accession_number", name="uq_lib_accession"), {"schema": "library"})
    book_id = Column(UUID(as_uuid=True), ForeignKey("library.books.id", ondelete="CASCADE"), nullable=False, index=True)
    accession_number = Column(String(50), nullable=False)
    barcode = Column(String(100), nullable=True)
    condition = Column(String(20), default="GOOD", comment="NEW | GOOD | FAIR | POOR | DAMAGED | LOST")
    acquisition_date = Column(Date, nullable=True)
    acquisition_cost = Column(Numeric(8, 2), nullable=True)
    status = Column(String(20), default="AVAILABLE", comment="AVAILABLE | ISSUED | RESERVED | LOST | DISCARDED")
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    book = relationship("Book", back_populates="copies")
    issues = relationship("BookIssue", back_populates="book_copy")


class LibraryMembership(BaseModel):
    """Library member registration."""
    __tablename__ = "library_memberships"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", "academic_year_id", name="uq_lib_membership"), {"schema": "library"})
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_type = Column(String(20), nullable=False, comment="STUDENT | TEACHER | STAFF")
    academic_year_id = Column(UUID(as_uuid=True), nullable=False)
    member_number = Column(String(50), nullable=False)
    max_books_allowed = Column(Integer, default=3)
    max_loan_days = Column(Integer, default=14)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class BookIssue(BaseModel):
    """Book issue/loan record."""
    __tablename__ = "book_issues"
    __table_args__ = {"schema": "library"}
    book_copy_id = Column(UUID(as_uuid=True), ForeignKey("library.book_copies.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id = Column(UUID(as_uuid=True), ForeignKey("library.library_memberships.id", ondelete="CASCADE"), nullable=False, index=True)
    issued_date = Column(Date, nullable=False, index=True)
    due_date = Column(Date, nullable=False, index=True)
    returned_date = Column(Date, nullable=True)
    status = Column(String(20), default="ISSUED", comment="ISSUED | RETURNED | OVERDUE | LOST")
    issued_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    returned_to_user_id = Column(UUID(as_uuid=True), nullable=True)
    condition_at_return = Column(String(20), nullable=True)
    remarks = Column(Text, nullable=True)
    extra_metadata = Column(JSONB, default={})
    book_copy = relationship("BookCopy", back_populates="issues")
    fines = relationship("LibraryFine", back_populates="issue")


class LibraryFine(BaseModel):
    """Library fines for overdue/damaged/lost books."""
    __tablename__ = "library_fines"
    __table_args__ = {"schema": "library"}
    issue_id = Column(UUID(as_uuid=True), ForeignKey("library.book_issues.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id = Column(UUID(as_uuid=True), ForeignKey("library.library_memberships.id"), nullable=False, index=True)
    fine_type = Column(String(20), nullable=False, comment="OVERDUE | DAMAGE | LOST")
    overdue_days = Column(Integer, default=0)
    fine_amount = Column(Numeric(8, 2), nullable=False)
    amount_paid = Column(Numeric(8, 2), default=0)
    payment_status = Column(String(20), default="PENDING", comment="PENDING | PARTIAL | PAID | WAIVED")
    waived_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    waiver_reason = Column(Text, nullable=True)
    extra_metadata = Column(JSONB, default={})
    issue = relationship("BookIssue", back_populates="fines")
