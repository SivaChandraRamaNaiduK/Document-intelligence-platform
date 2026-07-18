"""
Declarative base. Every SQLAlchemy model inherits from Base.

Model imports for Alembic's autogenerate live in alembic/env.py, not here —
importing them here creates a circular import the moment any other module
imports app.models.* before app.db.base has finished loading.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass