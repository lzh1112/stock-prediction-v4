from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...api.deps import get_db
from ...models import Stock, News, SentimentFeature

router = APIRouter()


@router.get("/news")
async def list_news(
    stock_code: str = Query(..., description="股票代码"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stock_result = await db.execute(select(Stock).where(Stock.code == stock_code))
    stock = stock_result.scalar_one_or_none()
    if stock is None:
        return {"stock_code": stock_code, "items": [], "total": 0, "page": page, "page_size": page_size}

    result = await db.execute(
        select(News)
        .options(selectinload(News.sentiment))
        .where(News.stock_id == stock.id)
        .order_by(News.publish_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    news_list = result.scalars().all()

    count_result = await db.execute(
        select(News).where(News.stock_id == stock.id)
    )
    total = len(count_result.scalars().all())

    items = []
    for n in news_list:
        sent = None
        if n.sentiment:
            sent = {
                "event_type": n.sentiment.event_type,
                "sentiment_score": n.sentiment.sentiment_score,
                "intensity": n.sentiment.intensity,
                "relevance": n.sentiment.relevance,
            }
        items.append({
            "id": n.id,
            "title": n.title,
            "source": n.source,
            "publish_time": n.publish_time.isoformat(),
            "sentiment": sent,
        })

    return {
        "stock_code": stock_code,
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/news/{news_id}")
async def get_news_detail(news_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(News).options(selectinload(News.sentiment)).where(News.id == news_id)
    )
    news = result.scalar_one_or_none()
    if news is None:
        return {"error": "Not found"}

    sent = None
    if news.sentiment:
        sent = {
            "event_type": news.sentiment.event_type,
            "sentiment_score": news.sentiment.sentiment_score,
            "intensity": news.sentiment.intensity,
            "relevance": news.sentiment.relevance,
        }

    return {
        "news_id": news.id,
        "title": news.title,
        "content": news.content,
        "url": news.url,
        "source": news.source,
        "publish_time": news.publish_time.isoformat(),
        "sentiment": sent,
    }
