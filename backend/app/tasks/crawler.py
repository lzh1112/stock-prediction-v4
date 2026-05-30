"""
数据抓取 Celery 定时任务

每个交易日收盘后自动抓取股价和新闻数据。
"""

from __future__ import annotations

import asyncio
import logging
import time

from . import celery_app

logger = logging.getLogger(__name__)


async def _fetch_prices_and_news() -> dict:
    """异步抓取全部 A 股股价和新闻数据。"""
    from app.api.deps import async_session
    from app.services.data_fetcher import fetch_all_stocks_prices, fetch_all_stocks_news

    results = {"prices": {}, "news": {}}

    async with async_session() as session:
        # 1. 抓取股价数据
        logger.info("开始抓取全部 A 股股价数据…")
        t0 = time.monotonic()
        results["prices"] = await fetch_all_stocks_prices(session)
        elapsed = time.monotonic() - t0
        total_prices = sum(results["prices"].values())
        logger.info(
            "股价数据抓取完成 — %d 条新增记录 / %d 只股票，耗时 %.1f 秒",
            total_prices,
            len(results["prices"]),
            elapsed,
        )

        # 2. 抓取新闻数据
        logger.info("开始抓取股票新闻数据…")
        t0 = time.monotonic()
        results["news"] = await fetch_all_stocks_news(session)
        elapsed = time.monotonic() - t0
        total_news = sum(results["news"].values())
        logger.info(
            "新闻数据抓取完成 — %d 条新增 / %d 只股票，耗时 %.1f 秒",
            total_news,
            len(results["news"]),
            elapsed,
        )

    return results


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_daily_data(self):
    """每个交易日收盘后抓取股价和新闻数据。"""
    logger.info("Celery 定时任务 fetch_daily_data 开始执行…")
    try:
        results = asyncio.run(_fetch_prices_and_news())
        return {
            "status": "ok",
            "total_price_records": sum(results["prices"].values()),
            "stocks_with_prices": len(results["prices"]),
            "total_news": sum(results["news"].values()),
        }
    except Exception as exc:
        logger.error("fetch_daily_data 执行失败: %s", exc, exc_info=True)
        # 网络临时故障 → 自动重试
        if self.request.retries < self.max_retries:
            logger.info("将在 %d 秒后重试 (%d/%d)", self.default_retry_delay,
                        self.request.retries + 1, self.max_retries)
            raise self.retry(exc=exc)
        raise
