from __future__ import annotations

from sqlalchemy import String, Numeric, BigInteger, Date, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass
