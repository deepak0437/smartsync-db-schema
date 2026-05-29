"""
Academic Service — Import all models for Alembic autogenerate.
"""
from app.models.base import Base  # noqa: F401
from app.models import *  # noqa: F401,F403 — registers all models with Base.metadata

metadata = Base.metadata

__all__ = ["Base", "metadata"]
