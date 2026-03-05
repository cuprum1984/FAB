# core/models/base.py
"""
Базовый класс для всех моделей.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс для всех ORM моделей."""
    pass
