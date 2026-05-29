"""
Media Service Models — File uploads, media library, CDN references.
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


class MediaFile(BaseModel):
    """
    Master file registry for all uploaded files across all services.
    All other services reference media_file_id to avoid duplicate storage.
    """
    __tablename__ = "media_files"
    __table_args__ = {"schema": "media"}
    uploader_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    original_filename = Column(String(500), nullable=False)
    stored_filename = Column(String(500), nullable=False, comment="UUID-based storage filename")
    file_path = Column(Text, nullable=False, comment="Storage path (S3 key / GCS path)")
    cdn_url = Column(Text, nullable=False, comment="Public CDN URL")
    file_type = Column(String(100), nullable=True, comment="MIME type: image/jpeg | application/pdf | ...")
    file_size_bytes = Column(Integer, nullable=True)
    file_extension = Column(String(20), nullable=True)
    media_category = Column(String(30), nullable=False, comment="IMAGE | DOCUMENT | VIDEO | AUDIO | SPREADSHEET | OTHER")
    storage_bucket = Column(String(100), nullable=True, comment="S3 bucket or GCS bucket name")
    storage_provider = Column(String(20), default="S3", comment="S3 | GCS | AZURE | LOCAL")
    # Image metadata
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    # Video metadata
    video_duration_seconds = Column(Integer, nullable=True)
    video_resolution = Column(String(20), nullable=True)
    # Access control
    access_level = Column(String(20), default="PRIVATE", comment="PUBLIC | PRIVATE | TENANT | SIGNED_URL")
    signed_url_expires_at = Column(DateTime(timezone=True), nullable=True)
    # Virus scan
    is_virus_scanned = Column(Boolean, default=False)
    virus_scan_status = Column(String(20), nullable=True, comment="CLEAN | INFECTED | PENDING | FAILED")
    virus_scan_at = Column(DateTime(timezone=True), nullable=True)
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    # Originating service
    source_service = Column(String(50), nullable=True, comment="academic | hr | admission | lms | ...")
    source_entity_type = Column(String(100), nullable=True, comment="HOMEWORK | ACHIEVEMENT | DOCUMENT | ...")
    source_entity_id = Column(UUID(as_uuid=True), nullable=True)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class MediaFolder(BaseModel):
    """Virtual folder organization for media files."""
    __tablename__ = "media_folders"
    __table_args__ = {"schema": "media"}
    folder_name = Column(String(255), nullable=False)
    folder_path = Column(Text, nullable=False, comment="Full virtual path e.g. /academics/homework/2024")
    parent_folder_id = Column(UUID(as_uuid=True), ForeignKey("media.media_folders.id", ondelete="SET NULL"), nullable=True)
    owner_user_id = Column(UUID(as_uuid=True), nullable=True)
    is_system_folder = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSONB, default={})


class MediaUsageLog(BaseModel):
    """Tracks file access for CDN cost analysis and audit."""
    __tablename__ = "media_usage_logs"
    __table_args__ = {"schema": "media"}
    media_file_id = Column(UUID(as_uuid=True), ForeignKey("media.media_files.id", ondelete="CASCADE"), nullable=False, index=True)
    accessed_by_user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    access_type = Column(String(20), nullable=False, comment="VIEW | DOWNLOAD | STREAM | THUMBNAIL")
    accessed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    bytes_transferred = Column(Integer, nullable=True)
    extra_metadata = Column(JSONB, default={})


class StorageQuota(BaseModel):
    """Storage quota tracking per tenant."""
    __tablename__ = "storage_quotas"
    __table_args__ = {"schema": "media"}
    quota_limit_gb = Column(Integer, nullable=False)
    used_bytes = Column(Integer, default=0)
    file_count = Column(Integer, default=0)
    last_computed_at = Column(DateTime(timezone=True), nullable=True)
    alert_threshold_percentage = Column(Integer, default=80)
    is_over_quota = Column(Boolean, default=False)
    extra_metadata = Column(JSONB, default={})
