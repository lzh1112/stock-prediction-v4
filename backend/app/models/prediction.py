from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import String, Date, DateTime, Float, ForeignKey, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB
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
    top_factors: Mapped[dict | None] = mapped_column(JSONB)
    actual_close: Mapped[float | None] = mapped_column(Float)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    stock: Mapped["Stock"] = relationship(back_populates="predictions")
