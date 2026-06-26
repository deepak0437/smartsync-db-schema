import time
import uuid
from sqlalchemy import BigInteger, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def current_epoch_time() -> int:
    return int(time.time())

class Base(DeclarativeBase):
    """
    Universal Base Model for all SmartSync microservices.
    """
    # 1 - Primary Key and basic timestamps
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[int] = mapped_column(BigInteger, default=current_epoch_time, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, default=current_epoch_time, onupdate=current_epoch_time, nullable=False)
    
    # 2 - Soft deletion flags
    deleted_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # 3 - Audit tracking
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)