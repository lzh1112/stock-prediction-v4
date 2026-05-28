from __future__ import annotations

from datetime import date, datetime

import json

from sqlalchemy import String, Date, DateTime, Float, ForeignKey, Boolean, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class DailyShadow(Base):
    __tablename__ = "daily_shadow"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False, index=True)
    predict_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    predicted_prob: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_label: Mapped[str] = mapped_column(String(4), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    _top_factors: Mapped[str | None] = mapped_column("top_factors", Text, nullable=True)

    @property
    def top_factors(self) -> dict | None:
        if self._top_factors is None:
            return None
        return json.loads(self._top_factors)

    @top_factors.setter
    def top_factors(self, value: dict | None) -> None:
        self._top_factors = json.dumps(value, ensure_ascii=False) if value is not None else None
    actual_close: Mapped[float | None] = mapped_column(Float)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    stock: Mapped["Stock"] = relationship(back_populates="predictions")
