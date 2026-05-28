from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


# --- Stock ---

class StockBrief(BaseModel):
    code: str
    name: str
    industry: str | None = None


class DailyPriceOut(BaseModel):
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class StockDetail(StockBrief):
    prices: list[DailyPriceOut] = []

    class Config:
        from_attributes = True


# --- News ---

class SentimentOut(BaseModel):
    event_type: str | None
    sentiment_score: float | None
    intensity: float | None
    relevance: float | None

    class Config:
        from_attributes = True


class NewsItem(BaseModel):
    id: int
    title: str
    source: str | None
    publish_time: datetime
    sentiment: SentimentOut | None = None

    class Config:
        from_attributes = True


class NewsDetail(NewsItem):
    content: str | None
    url: str | None
