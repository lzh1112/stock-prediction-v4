from __future__ import annotations

from datetime import datetime

import json

from sqlalchemy import String, Text, DateTime, func, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str | None] = mapped_column(Text)
    publish_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    title_hash: Mapped[str] = mapped_column(String(64), unique=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    stock: Mapped["Stock"] = relationship(back_populates="news")
    sentiment: Mapped["SentimentFeature | None"] = relationship(back_populates="news", uselist=False)


class SentimentFeature(Base):
    __tablename__ = "sentiment_features"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(ForeignKey("news.id"), unique=True, nullable=False)
    event_type: Mapped[str | None] = mapped_column(String(50))
    sentiment_score: Mapped[float | None] = mapped_column(Float)
    intensity: Mapped[float | None] = mapped_column(Float)
    relevance: Mapped[float | None] = mapped_column(Float)
    _raw_llm_response: Mapped[str | None] = mapped_column("raw_llm_response", Text, nullable=True)

    @property
    def raw_llm_response(self) -> dict | None:
        if self._raw_llm_response is None:
            return None
        return json.loads(self._raw_llm_response)

    @raw_llm_response.setter
    def raw_llm_response(self, value: dict | None) -> None:
        self._raw_llm_response = json.dumps(value, ensure_ascii=False) if value is not None else None
    model_version: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    news: Mapped["News"] = relationship(back_populates="sentiment")
