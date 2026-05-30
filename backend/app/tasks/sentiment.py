"""
情感分析 Celery 定时任务

对近期新闻批量提取 LLM 情感特征。
"""

from __future__ import annotations

import asyncio
import logging

from . import celery_app

logger = logging.getLogger(__name__)


async def _extract_single_news(news_id: int) -> bool:
    """对单条新闻提取 LLM 情感特征，返回是否成功。"""
    from app.api.deps import async_session
    from app.models import News, SentimentFeature
    from app.services.llm_router import extract_sentiment
    from app.core.config import settings
    from sqlalchemy import select

    async with async_session() as session:
        news = (await session.execute(
            select(News).where(News.id == news_id)
        )).scalar_one_or_none()

        if news is None:
            logger.warning("新闻 ID %d 不存在", news_id)
            return False

        # 检查是否已有情感特征
        existing = (await session.execute(
            select(SentimentFeature).where(SentimentFeature.news_id == news_id)
        )).scalar_one_or_none()

        if existing:
            return False  # 已处理，跳过

        # 获取股票名称
        from app.models import Stock
        stock = (await session.execute(
            select(Stock).where(Stock.id == news.stock_id)
        )).scalar_one_or_none()
        stock_name = stock.name if stock else ""

        result = await extract_sentiment(
            title=news.title,
            content=news.content or "",
            stock_name=stock_name,
        )

        if result is None:
            logger.warning("新闻 ID %d 情感提取失败（LLM 返回空）", news_id)
            return False

        sf = SentimentFeature(
            news_id=news.id,
            event_type=result.event_type,
            sentiment_score=result.sentiment_score,
            intensity=result.intensity,
            relevance=result.relevance,
            raw_llm_response=result.model_dump(),
            model_version=settings.LLM_MODEL_NAME,
        )
        session.add(sf)
        await session.commit()
        return True


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def extract_sentiment(self, news_id: int):
    """对单条新闻执行 LLM 情感特征提取。"""
    logger.info("提取新闻 ID %d 的情感特征…", news_id)
    try:
        success = asyncio.run(_extract_single_news(news_id))
        return {"status": "ok", "news_id": news_id, "extracted": success}
    except Exception as exc:
        logger.error("新闻 ID %d 情感提取失败: %s", news_id, exc)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise


async def _batch_extract_for_stock(stock_code: str, days: int = 7) -> dict:
    """批量处理某只股票近期的新闻。"""
    from datetime import date, timedelta
    from app.api.deps import async_session
    from app.models import Stock, News, SentimentFeature
    from sqlalchemy import select

    async with async_session() as session:
        stock = (await session.execute(
            select(Stock).where(Stock.code == stock_code)
        )).scalar_one_or_none()

        if stock is None:
            return {"status": "error", "message": f"股票 {stock_code} 不存在"}

        cutoff = date.today() - timedelta(days=days)
        news_list = (await session.execute(
            select(News)
            .where(News.stock_id == stock.id, News.publish_time >= cutoff)
            .order_by(News.publish_time.desc())
        )).scalars().all()

        processed = 0
        for news in news_list:
            success = await _extract_single_news(news.id)
            if success:
                processed += 1

    return {"status": "ok", "stock_code": stock_code, "processed": processed,
            "total_news": len(news_list)}


@celery_app.task(bind=True, max_retries=2)
def batch_extract_sentiment(self, stock_code: str, days: int = 7):
    """批量处理某只股票的近期新闻。"""
    logger.info("批量提取 %s 近 %d 天新闻情感…", stock_code, days)
    try:
        results = asyncio.run(_batch_extract_for_stock(stock_code, days))
        return results
    except Exception as exc:
        logger.error("批量情感提取失败 (%s): %s", stock_code, exc)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise
