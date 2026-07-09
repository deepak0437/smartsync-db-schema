import time
import uuid
from sqlalchemy import BigInteger, Boolean, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def current_epoch_time() -> int:
    return int(time.time())


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    created_at: Mapped[int] = mapped_column(
        BigInteger,
        default=current_epoch_time,
        server_default=text("EXTRACT(EPOCH FROM NOW())::BIGINT"),
        nullable=False,
    )

    updated_at: Mapped[int] = mapped_column(
        BigInteger,
        default=current_epoch_time,
        server_default=text("EXTRACT(EPOCH FROM NOW())::BIGINT"),
        onupdate=current_epoch_time,
        nullable=False,
    )


class SoftDeleteMixin:
    deleted_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )

    deleted_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class AuditMixin:
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

