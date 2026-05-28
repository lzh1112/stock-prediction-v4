#!/usr/bin/env python3
"""
无未来函数校验脚本

检测新闻发布时间是否晚于其关联的股价交易日（未来信息泄露）。
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.models import News, DailyPrice, Stock
from app.core.config import settings


async def check_alignment(db: AsyncSession, stock_code: str | None = None) -> list[dict]:
    """扫描新闻-股价时间对齐，返回违规记录列表。"""
    violations = []

    query = select(Stock)
    if stock_code:
        query = query.where(Stock.code == stock_code)
    stocks = (await db.execute(query)).scalars().all()

    for stock in stocks:
        news_list = (await db.execute(
            select(News).where(News.stock_id == stock.id)
        )).scalars().all()

        for news in news_list:
            prices_on_day = (await db.execute(
                select(DailyPrice).where(
                    DailyPrice.stock_id == stock.id,
                    DailyPrice.trade_date == news.publish_time.date(),
                )
            )).scalar_one_or_none()

            if prices_on_day is None:
                continue

            if news.publish_time.time() < datetime.strptime("15:00", "%H:%M").time():
                violations.append({
                    "stock_code": stock.code,
                    "news_id": news.id,
                    "news_title": news.title[:60],
                    "publish_time": news.publish_time.isoformat(),
                    "trade_date": str(prices_on_day.trade_date),
                    "issue": "新闻发布于收盘前，可能包含当日未来信息",
                })

    return violations


async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db:
        violations = await check_alignment(db)
        if violations:
            print(f"发现 {len(violations)} 条潜在未来信息泄露:")
            for v in violations[:10]:
                print(f"  [{v['stock_code']}] {v['news_title']}")
                print(f"    发布时间: {v['publish_time']} | 交易日: {v['trade_date']}")
        else:
            print("未发现未来信息泄露")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
