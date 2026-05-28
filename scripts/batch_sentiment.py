#!/usr/bin/env python3
"""批量LLM情感提取 — 全部50只股票的所有未处理新闻"""

from __future__ import annotations

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.api.deps import async_session
from app.models import Stock, News, SentimentFeature
from app.services.llm_router import extract_sentiment


async def process_all():
    processed = 0
    failed = 0
    skipped = 0

    async with async_session() as db:
        stocks = (await db.execute(select(Stock))).scalars().all()
        total_news = 0

        for stock in stocks:
            news_list = (await db.execute(
                select(News).where(News.stock_id == stock.id).order_by(News.publish_time.desc())
            )).scalars().all()
            total_news += len(news_list)

            for news in news_list:
                existing = (await db.execute(
                    select(SentimentFeature).where(SentimentFeature.news_id == news.id)
                )).scalar_one_or_none()
                if existing:
                    skipped += 1
                    continue

                result = await extract_sentiment(
                    title=news.title,
                    content=news.content or "",
                    stock_name=stock.name,
                )
                if result is None:
                    failed += 1
                    continue

                sf = SentimentFeature(
                    news_id=news.id,
                    event_type=result.event_type,
                    sentiment_score=result.sentiment_score,
                    intensity=result.intensity,
                    relevance=result.relevance,
                    raw_llm_response=result.model_dump(),
                    model_version=settings.LLM_MODEL_NAME,
                )
                db.add(sf)
                processed += 1

                if processed % 10 == 0:
                    await db.commit()
                    print(f"  Progress: {processed} processed, {failed} failed, {skipped} skipped")

        await db.commit()

    print(f"\nDone! {processed} processed, {failed} failed, {skipped} already had sentiment")
    print(f"Total news in DB: {total_news}")


if __name__ == "__main__":
    print(f"Starting sentiment extraction with {settings.LLM_MODEL_NAME}...")
    print(f"API: {settings.LLM_API_BASE}")
    asyncio.run(process_all())
