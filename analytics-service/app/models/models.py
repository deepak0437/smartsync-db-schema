"""
Analytics Service Models — Report configs, dashboards, cached metrics, report runs.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase
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


class ReportDefinition(BaseModel):
    """Pre-defined report configurations."""
    __tablename__ = "report_definitions"
    __table_args__ = {"schema": "analytics"}
    report_code = Column(String(50), nullable=False, index=True)
    report_name = Column(String(255), nullable=False)
    report_category = Column(String(50), nullable=False, comment="ACADEMIC | FINANCE | ATTENDANCE | BEHAVIOR | HR | TRANSPORT")
    description = Column(Text, nullable=True)
    query_config = Column(JSONB, nullable=False, comment="Report query parameters and filters")
    output_format = Column(String(20), default="TABLE", comment="TABLE | CHART | BOTH | PDF | EXCEL")
    required_permissions = Column(JSONB, default=[], comment="Required permission codes to access this report")
    available_filters = Column(JSONB, default=[])
    is_schedulable = Column(Boolean, default=False)
    cache_ttl_minutes = Column(Integer, default=60)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class ReportRun(BaseModel):
    """Individual report execution record."""
    __tablename__ = "report_runs"
    __table_args__ = {"schema": "analytics"}
    report_id = Column(UUID(as_uuid=True), ForeignKey("analytics.report_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    filters_applied = Column(JSONB, default={}, comment="Filters used for this run")
    status = Column(String(20), default="QUEUED", comment="QUEUED | RUNNING | COMPLETED | FAILED | CANCELLED")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    result_row_count = Column(Integer, nullable=True)
    output_file_url = Column(Text, nullable=True, comment="CDN URL for generated report file")
    output_format = Column(String(20), nullable=True)
    error_message = Column(Text, nullable=True)
    cache_hit = Column(Boolean, default=False)
    extra_metadata = Column(JSONB, default={})


class Dashboard(BaseModel):
    """Configurable dashboards per user role."""
    __tablename__ = "dashboards"
    __table_args__ = {"schema": "analytics"}
    dashboard_code = Column(String(50), nullable=False)
    dashboard_name = Column(String(255), nullable=False)
    target_role = Column(String(50), nullable=False, comment="STUDENT | PARENT | TEACHER | HOD | PRINCIPAL | ADMIN")
    layout = Column(JSONB, default=[], comment="Widget layout configuration")
    is_default = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False, comment="System dashboards cannot be deleted")
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class DashboardWidget(BaseModel):
    """Individual widgets on a dashboard."""
    __tablename__ = "dashboard_widgets"
    __table_args__ = {"schema": "analytics"}
    dashboard_id = Column(UUID(as_uuid=True), ForeignKey("analytics.dashboards.id", ondelete="CASCADE"), nullable=False, index=True)
    widget_type = Column(String(50), nullable=False, comment="ATTENDANCE_CHART | FEE_SUMMARY | HOMEWORK_STATUS | BEHAVIOR_TREND | ...")
    title = Column(String(255), nullable=False)
    config = Column(JSONB, default={}, comment="Widget-specific configuration")
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    width = Column(Integer, default=4)
    height = Column(Integer, default=3)
    data_source = Column(String(100), nullable=True, comment="Service endpoint or report_definition_id")
    refresh_interval_minutes = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class MetricSnapshot(BaseModel):
    """Pre-computed metric snapshots for fast dashboard loading."""
    __tablename__ = "metric_snapshots"
    __table_args__ = {"schema": "analytics"}
    metric_type = Column(String(100), nullable=False, index=True, comment="DAILY_ATTENDANCE | MONTHLY_FEE_COLLECTION | HOMEWORK_COMPLETION | ...")
    academic_year_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    class_id = Column(UUID(as_uuid=True), nullable=True)
    section_id = Column(UUID(as_uuid=True), nullable=True)
    reference_date = Column(DateTime(timezone=True), nullable=False, index=True)
    metric_data = Column(JSONB, nullable=False, comment="Computed metric values")
    computed_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    extra_metadata = Column(JSONB, default={})


class ScheduledReport(BaseModel):
    """Recurring report schedules."""
    __tablename__ = "scheduled_reports"
    __table_args__ = {"schema": "analytics"}
    report_id = Column(UUID(as_uuid=True), ForeignKey("analytics.report_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    schedule_name = Column(String(255), nullable=False)
    cron_expression = Column(String(100), nullable=False, comment="Cron expression for schedule")
    recipient_user_ids = Column(JSONB, default=[], comment="Users who receive the report")
    filters = Column(JSONB, default={})
    output_format = Column(String(20), default="PDF")
    delivery_channel = Column(String(20), default="EMAIL", comment="EMAIL | IN_APP | DOWNLOAD")
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    extra_metadata = Column(JSONB, default={})
