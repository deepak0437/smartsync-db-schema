"""
Transport Service Models — Routes, vehicles, stops, allocations, tracking.
"""
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Numeric, String, Text, ForeignKey, UniqueConstraint, Time
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


class Vehicle(BaseModel):
    """School vehicle (bus, van, etc.)."""
    __tablename__ = "vehicles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "registration_number", name="uq_transport_vehicle"),
        {"schema": "transport"},
    )
    registration_number = Column(String(20), nullable=False)
    vehicle_type = Column(String(20), nullable=False, comment="BUS | VAN | AUTO | CAR")
    vehicle_model = Column(String(100), nullable=True)
    vehicle_color = Column(String(50), nullable=True)
    seating_capacity = Column(Integer, nullable=False)
    fuel_type = Column(String(20), default="DIESEL", comment="DIESEL | PETROL | CNG | ELECTRIC")
    driver_user_id = Column(UUID(as_uuid=True), nullable=True, comment="Driver user_id from auth-service")
    co_driver_user_id = Column(UUID(as_uuid=True), nullable=True)
    fitness_certificate_number = Column(String(100), nullable=True)
    fitness_valid_until = Column(Date, nullable=True)
    insurance_number = Column(String(100), nullable=True)
    insurance_valid_until = Column(Date, nullable=True)
    permit_number = Column(String(100), nullable=True)
    permit_valid_until = Column(Date, nullable=True)
    gps_device_id = Column(String(100), nullable=True)
    gps_sim_number = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    routes = relationship("TransportRoute", back_populates="vehicle")


class TransportRoute(BaseModel):
    """Transport route definition."""
    __tablename__ = "transport_routes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "route_code", name="uq_transport_route"),
        {"schema": "transport"},
    )
    route_code = Column(String(20), nullable=False)
    route_name = Column(String(255), nullable=False)
    route_type = Column(String(10), nullable=False, comment="MORNING | AFTERNOON | BOTH")
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("transport.vehicles.id", ondelete="SET NULL"), nullable=True)
    start_location = Column(String(255), nullable=True)
    end_location = Column(String(255), nullable=False, comment="School")
    total_distance_km = Column(Numeric(8, 2), nullable=True)
    departure_time = Column(Time, nullable=True)
    arrival_time = Column(Time, nullable=True)
    monthly_fee = Column(Numeric(10, 2), default=0)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    vehicle = relationship("Vehicle", back_populates="routes")
    stops = relationship("RouteStop", back_populates="route")
    allocations = relationship("TransportAllocation", back_populates="route")


class RouteStop(BaseModel):
    """Individual stops on a transport route."""
    __tablename__ = "route_stops"
    __table_args__ = (
        UniqueConstraint("tenant_id", "route_id", "stop_order", name="uq_transport_stop_order"),
        {"schema": "transport"},
    )
    route_id = Column(UUID(as_uuid=True), ForeignKey("transport.transport_routes.id", ondelete="CASCADE"), nullable=False, index=True)
    stop_name = Column(String(255), nullable=False)
    stop_order = Column(Integer, nullable=False)
    landmark = Column(String(255), nullable=True)
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    morning_pickup_time = Column(Time, nullable=True)
    afternoon_drop_time = Column(Time, nullable=True)
    stop_fee = Column(Numeric(10, 2), default=0)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})
    route = relationship("TransportRoute", back_populates="stops")


class TransportAllocation(BaseModel):
    """Student/staff transport allocation."""
    __tablename__ = "transport_allocations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "academic_year_id", name="uq_transport_allocation"),
        {"schema": "transport"},
    )
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_type = Column(String(20), nullable=False, comment="STUDENT | STAFF")
    route_id = Column(UUID(as_uuid=True), ForeignKey("transport.transport_routes.id", ondelete="CASCADE"), nullable=False)
    stop_id = Column(UUID(as_uuid=True), ForeignKey("transport.route_stops.id", ondelete="SET NULL"), nullable=True)
    academic_year_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    allocation_date = Column(Date, nullable=False)
    pickup_stop_id = Column(UUID(as_uuid=True), nullable=True)
    drop_stop_id = Column(UUID(as_uuid=True), nullable=True)
    rfid_card_number = Column(String(50), nullable=True, comment="RFID card for tracking")
    status = Column(String(20), default="ACTIVE", comment="ACTIVE | INACTIVE | SUSPENDED")
    extra_metadata = Column(JSONB, default={})
    route = relationship("TransportRoute", back_populates="allocations")


class VehicleTracking(BaseModel):
    """Real-time vehicle GPS tracking logs."""
    __tablename__ = "vehicle_tracking"
    __table_args__ = {"schema": "transport"}
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("transport.vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    route_id = Column(UUID(as_uuid=True), nullable=True)
    latitude = Column(String(20), nullable=False)
    longitude = Column(String(20), nullable=False)
    speed_kmh = Column(Numeric(5, 2), nullable=True)
    heading = Column(Numeric(6, 2), nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)
    trip_status = Column(String(20), nullable=True, comment="STARTED | IN_PROGRESS | COMPLETED | PARKED")
    extra_metadata = Column(JSONB, default={})
