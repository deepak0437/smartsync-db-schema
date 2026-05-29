"""
Hostel Service Models — Hostels, blocks, rooms, allocations, attendance, mess.
"""
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Numeric, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
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


class Hostel(BaseModel):
    """Hostel/dormitory building."""
    __tablename__ = "hostels"
    __table_args__ = (
        UniqueConstraint("tenant_id", "hostel_code", name="uq_hostel_code"),
        {"schema": "hostel"},
    )
    hostel_code = Column(String(50), nullable=False)
    hostel_name = Column(String(255), nullable=False)
    hostel_type = Column(String(20), nullable=False, comment="BOYS | GIRLS | CO_ED | STAFF")
    warden_user_id = Column(UUID(as_uuid=True), nullable=True)
    address = Column(Text, nullable=True)
    total_capacity = Column(Integer, default=0)
    current_occupancy = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    blocks = relationship("HostelBlock", back_populates="hostel")


class HostelBlock(BaseModel):
    """Hostel block/wing."""
    __tablename__ = "hostel_blocks"
    __table_args__ = {"schema": "hostel"}
    hostel_id = Column(UUID(as_uuid=True), ForeignKey("hostel.hostels.id", ondelete="CASCADE"), nullable=False, index=True)
    block_name = Column(String(100), nullable=False)
    floor_count = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    hostel = relationship("Hostel", back_populates="blocks")
    rooms = relationship("HostelRoom", back_populates="block")


class HostelRoom(BaseModel):
    """Individual hostel room."""
    __tablename__ = "hostel_rooms"
    __table_args__ = (
        UniqueConstraint("tenant_id", "hostel_id", "room_number", name="uq_hostel_room"),
        {"schema": "hostel"},
    )
    hostel_id = Column(UUID(as_uuid=True), ForeignKey("hostel.hostels.id", ondelete="CASCADE"), nullable=False, index=True)
    block_id = Column(UUID(as_uuid=True), ForeignKey("hostel.hostel_blocks.id", ondelete="SET NULL"), nullable=True)
    room_number = Column(String(20), nullable=False)
    floor = Column(Integer, default=1)
    room_type = Column(String(20), default="SHARED", comment="SINGLE | DOUBLE | TRIPLE | SHARED | DORMITORY")
    capacity = Column(Integer, default=2)
    current_occupants = Column(Integer, default=0)
    monthly_fee = Column(Numeric(10, 2), default=0)
    amenities = Column(JSONB, default=[], comment="Array of amenities")
    is_available = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    block = relationship("HostelBlock", back_populates="rooms")
    allocations = relationship("RoomAllocation", back_populates="room")


class RoomAllocation(BaseModel):
    """Student room allocation record."""
    __tablename__ = "room_allocations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "student_id", "academic_year_id", name="uq_hostel_student_alloc"),
        {"schema": "hostel"},
    )
    hostel_id = Column(UUID(as_uuid=True), ForeignKey("hostel.hostels.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id = Column(UUID(as_uuid=True), ForeignKey("hostel.hostel_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="academic_profile.id")
    academic_year_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    allocation_date = Column(Date, nullable=False)
    vacating_date = Column(Date, nullable=True)
    bed_number = Column(String(10), nullable=True)
    monthly_fee = Column(Numeric(10, 2), default=0)
    deposit_amount = Column(Numeric(10, 2), default=0)
    status = Column(String(20), default="ACTIVE", comment="ACTIVE | VACATED | TRANSFERRED | SUSPENDED")
    extra_metadata = Column(JSONB, default={})
    room = relationship("HostelRoom", back_populates="allocations")


class HostelAttendance(BaseModel):
    """Daily hostel attendance (night roll call)."""
    __tablename__ = "hostel_attendance"
    __table_args__ = (
        UniqueConstraint("tenant_id", "student_id", "attendance_date", name="uq_hostel_attendance"),
        {"schema": "hostel"},
    )
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    room_id = Column(UUID(as_uuid=True), ForeignKey("hostel.hostel_rooms.id"), nullable=False)
    attendance_date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False, comment="PRESENT | ABSENT | ON_LEAVE | WEEKEND_OUT")
    marked_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    remarks = Column(Text, nullable=True)
    extra_metadata = Column(JSONB, default={})


class MessMenu(BaseModel):
    """Daily mess/cafeteria menu."""
    __tablename__ = "mess_menus"
    __table_args__ = {"schema": "hostel"}
    hostel_id = Column(UUID(as_uuid=True), ForeignKey("hostel.hostels.id", ondelete="CASCADE"), nullable=False)
    menu_date = Column(Date, nullable=False, index=True)
    meal_type = Column(String(20), nullable=False, comment="BREAKFAST | LUNCH | SNACKS | DINNER")
    menu_items = Column(JSONB, nullable=False, comment="Array of menu items")
    is_vegetarian = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class MessAttendance(BaseModel):
    """Student mess attendance (meal tracking)."""
    __tablename__ = "mess_attendance"
    __table_args__ = (
        UniqueConstraint("tenant_id", "student_id", "attendance_date", "meal_type", name="uq_mess_attendance"),
        {"schema": "hostel"},
    )
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    hostel_id = Column(UUID(as_uuid=True), ForeignKey("hostel.hostels.id"), nullable=False)
    attendance_date = Column(Date, nullable=False, index=True)
    meal_type = Column(String(20), nullable=False)
    status = Column(String(10), nullable=False, comment="PRESENT | ABSENT | OPT_OUT")
    extra_metadata = Column(JSONB, default={})
