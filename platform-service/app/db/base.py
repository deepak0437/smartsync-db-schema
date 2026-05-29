"""Import all models for Alembic autogenerate."""
from app.models.models import Base  # noqa: F401
metadata = Base.metadata
__all__ = ["Base", "metadata"]
