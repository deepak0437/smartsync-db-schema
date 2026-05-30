"""
Analytics Service — Import all models so Alembic autogenerate can detect them.
This file must be imported in alembic/env.py target_metadata.
"""
# Import Base first
from app.models.base import Base  # noqa: F401

# Import all models to register them with Base.metadata
# Add your model imports here when they are created
