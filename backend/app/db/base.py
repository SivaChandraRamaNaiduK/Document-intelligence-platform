"""
Declarative base. Every SQLAlchemy model inherits from Base.

IMPORTANT: import all models here so Alembic's autogenerate can see them.
When you add a new model file (documents, chunks, ...), add its import below.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Model imports (needed for Alembic autogenerate) — noqa keeps linters quiet
from app.models.user import User  # noqa: E402, F401