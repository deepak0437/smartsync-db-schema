"""Re-export PlatformBase and BaseModel for model file imports."""

from app.db.base import BaseModel, PlatformBase

__all__ = ["PlatformBase", "BaseModel"]
