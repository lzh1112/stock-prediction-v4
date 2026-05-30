"""
股价与新闻数据获取服务 (原型版 — akshare + SQLite)

数据源: akshare (免费，无需 API Key)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import date, datetime, timedelta

import akshare as ak
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Stock, DailyPrice, News

logger = logging.getLogger(__name__)


def _get_all_a_stocks() -> list[tuple[str, str]]:
    """从 akshare 获取全部 A 股股票代码和名称。"""
    try:
        df = ak.stock_info_a_code_name()
    except Exception:
        return []
    if df.empty:
        return []

    stocks = []
    for _, row in df.iterrows():
        code = str(row["code"]).zfill(6)
        name = str(row["name"])
        # 判断交易所：6/9 开头为上海，0/2/3 开头为深圳
        if code.startswith(("6", "9")):
            full_code = f"{code}.SH"
        else:
            full_code = f"{code}.SZ"
        stocks.append((full_code, name))
    return stocks


async def ensure_stocks(session: AsyncSession) -> list[Stock]:
    """获取全部 A 股股票列表并确保在数据库中，返回 Stock 对象列表。"""
    all_stocks = _get_all_a_stocks()
    if not all_stocks:
        return []

    # 批量查询已有股票
    new_codes = [code for code, _ in all_stocks]
    existing = (await session.execute(
        select(Stock).where(Stock.code.in_(new_codes))
    )).scalars().all()
    existing_map = {s.code: s for s in existing}

    # 新增不存在的股票
    new_stocks = []
    for code, name in all_stocks:
        if code in existing_map:
            continue
        s = Stock(code=code, name=name)
        session.add(s)
        new_stocks.append(s)

    await session.commit()

    # 返回全部股票（已有 + 新增）
    for s in new_stocks:
        existing_map[s.code] = s
    return list(existing_map.values())


def _code_to_ak_symbol(code: str) -> str:
    """000001.SZ → sz000001, 600519.SH → sh600519"""
    parts = code.split(".")
    return f"{parts[1].lower()}{parts[0]}"


async def fetch_and_store_prices(
    session: AsyncSession,
    stock: Stock,
    lookback_days: int = 504,  # 约2年交易日
) -> int:
    """
    从 akshare 获取单只股票的日线数据并写入 DB。
    使用 stock_zh_a_daily (腾讯源), 仅保留最近 N 个交易日的数据。
    """
    symbol = _code_to_ak_symbol(stock.code)

    try:
        df = ak.stock_zh_a_daily(symbol=symbol, adjust="qfq")
    except Exception:
        return 0

    if df.empty:
        return 0

    # 只保留最近的数据
    df = df.tail(lookback_days)
    cutoff = date.today() - timedelta(days=lookback_days * 2)

    count = 0
    for _, row in df.iterrows():
        trade_date = row["date"]
        if isinstance(trade_date, pd.Timestamp):
            trade_date = trade_date.date()
        if trade_date < cutoff:
            continue

        existing = await session.execute(
            select(DailyPrice).where(
                DailyPrice.stock_id == stock.id,
                DailyPrice.trade_date == trade_date,
            )
        )
        if existing.scalar_one_or_none():
            continue

        price = DailyPrice(
            stock_id=stock.id,
            trade_date=trade_date,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"]),
        )
        session.add(price)
        count += 1

    await session.commit()
    return count


async def fetch_all_stocks_prices(
    session: AsyncSession, max_stocks: int | None = None, concurrency: int = 10
) -> dict[str, int]:
    """批量获取股票的股价数据。max_stocks 限制处理数量，None 表示全部。

    使用 asyncio.Semaphore 控制并发数，避免同时发起过多网络请求。
    每个并发任务使用独立的 DB session，保证线程安全。
    """
    stocks = await ensure_stocks(session)
    if max_stocks:
        stocks = stocks[:max_stocks]

    if not stocks:
        return {}

    logger.info("开始并发抓取 %d 只股票的价格数据（并发数=%d）…", len(stocks), concurrency)
    semaphore = asyncio.Semaphore(concurrency)

    async def fetch_one(stock: Stock) -> tuple[str, int]:
        async with semaphore:
            try:
                # 每个并发任务创建独立的 DB session
                from app.api.deps import async_session
                async with async_session() as sess:
                    n = await fetch_and_store_prices(sess, stock)
                    return (stock.code, n)
            except Exception as exc:
                logger.warning("抓取 %s 价格异常: %s", stock.code, exc)
                return (stock.code, 0)

    tasks = [fetch_one(s) for s in stocks]
    results_list = await asyncio.gather(*tasks)

    results = dict(results_list)
    total = sum(results.values())
    succeeded = sum(1 for v in results.values() if v > 0)
    logger.info("价格抓取完成: %d/%d 只有新数据，总计 %d 条记录", succeeded, len(results), total)
    return results


async def fetch_news_for_stock(
    session: AsyncSession,
    stock: Stock,
    max_news: int = 30,
) -> int:
    """
    从 akshare 获取单个股票的近期新闻并去重写入 DB。
    仅获取最近新闻，返回新写入的记录数。
    """
    symbol = stock.code.split(".")[0]

    try:
        df = ak.stock_news_em(symbol=symbol)
    except Exception:
        return 0

    if df.empty:
        return 0

    cols = list(df.columns)
    count = 0
    for _, row in df.head(max_news).iterrows():
        title = str(row.iloc[1]) if len(cols) > 1 else ""
        content = str(row.iloc[2]) if len(cols) > 2 else ""
        pub_time_str = str(row.iloc[3]) if len(cols) > 3 else ""
        source = str(row.iloc[4]) if len(cols) > 4 else ""
        url = str(row.iloc[5]) if len(cols) > 5 else ""

        title_hash = hashlib.sha256((title + stock.code).encode()).hexdigest()

        existing = await session.execute(
            select(News).where(News.title_hash == title_hash)
        )
        if existing.scalar_one_or_none():
            continue

        try:
            publish_time = pd.Timestamp(pub_time_str).to_pydatetime()
        except Exception:
            publish_time = datetime.now()

        news = News(
            stock_id=stock.id,
            title=title[:500],
            content=content or None,
            source=source or None,
            url=url or None,
            publish_time=publish_time,
            title_hash=title_hash,
        )
        session.add(news)
        count += 1

    await session.commit()
    return count


async def fetch_all_stocks_news(
    session: AsyncSession, concurrency: int = 10
) -> dict[str, int]:
    """批量获取所有样本股票的新闻。

    使用 asyncio.Semaphore 控制并发数，每个并发任务使用独立的 DB session。
    """
    stocks = await ensure_stocks(session)
    if not stocks:
        return {}

    logger.info("开始并发抓取 %d 只股票的新闻数据（并发数=%d）…", len(stocks), concurrency)
    semaphore = asyncio.Semaphore(concurrency)

    async def fetch_one(stock: Stock) -> tuple[str, int]:
        async with semaphore:
            try:
                from app.api.deps import async_session
                async with async_session() as sess:
                    n = await fetch_news_for_stock(sess, stock)
                    return (stock.code, n)
            except Exception as exc:
                logger.warning("抓取 %s 新闻异常: %s", stock.code, exc)
                return (stock.code, 0)

    tasks = [fetch_one(s) for s in stocks]
    results_list = await asyncio.gather(*tasks)

    results = dict(results_list)
    total = sum(results.values())
    logger.info("新闻抓取完成: %d 条新记录", total)
    return results


async def get_kline_data(session: AsyncSession, code: str, days: int = 365) -> list[dict]:
    """获取某只股票的 K 线数据（最近 N 天），用于前端展示。"""
    result = await session.execute(
        select(Stock).where(Stock.code == code)
    )
    stock = result.scalar_one_or_none()
    if stock is None:
        return []

    cutoff = date.today() - timedelta(days=days)
    result = await session.execute(
        select(DailyPrice)
        .where(DailyPrice.stock_id == stock.id, DailyPrice.trade_date >= cutoff)
        .order_by(DailyPrice.trade_date.asc())
    )
    prices = result.scalars().all()

    return [
        {
            "date": p.trade_date.isoformat(),
            "open": p.open,
            "high": p.high,
            "low": p.low,
            "close": p.close,
            "volume": p.volume,
        }
        for p in prices
    ]
