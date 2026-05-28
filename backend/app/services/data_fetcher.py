"""
股价与新闻数据获取服务 (原型版 — akshare + SQLite)

数据源: akshare (免费，无需 API Key)
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta

import akshare as ak
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Stock, DailyPrice, News


# --- 华东 300 成分股 (前 50 只用于原型) ---
CSI300_SAMPLE = [
    ("000001.SZ", "平安银行"),
    ("000002.SZ", "万科A"),
    ("000063.SZ", "中兴通讯"),
    ("000100.SZ", "TCL科技"),
    ("000333.SZ", "美的集团"),
    ("000338.SZ", "潍柴动力"),
    ("000425.SZ", "徐工机械"),
    ("000568.SZ", "泸州老窖"),
    ("000625.SZ", "长安汽车"),
    ("000651.SZ", "格力电器"),
    ("000725.SZ", "京东方A"),
    ("000776.SZ", "广发证券"),
    ("000858.SZ", "五粮液"),
    ("002142.SZ", "宁波银行"),
    ("002230.SZ", "科大讯飞"),
    ("002352.SZ", "顺丰控股"),
    ("002415.SZ", "海康威视"),
    ("002459.SZ", "晶澳科技"),
    ("002594.SZ", "比亚迪"),
    ("002714.SZ", "牧原股份"),
    ("300059.SZ", "东方财富"),
    ("300274.SZ", "阳光电源"),
    ("300308.SZ", "中际旭创"),
    ("300498.SZ", "温氏股份"),
    ("300750.SZ", "宁德时代"),
    ("600000.SH", "浦发银行"),
    ("600009.SH", "上海机场"),
    ("600016.SH", "民生银行"),
    ("600028.SH", "中国石化"),
    ("600030.SH", "中信证券"),
    ("600036.SH", "招商银行"),
    ("600048.SH", "保利发展"),
    ("600050.SH", "中国联通"),
    ("600085.SH", "同仁堂"),
    ("600104.SH", "上汽集团"),
    ("600276.SH", "恒瑞医药"),
    ("600309.SH", "万华化学"),
    ("600406.SH", "国电南瑞"),
    ("600436.SH", "片仔癀"),
    ("600438.SH", "通威股份"),
    ("600519.SH", "贵州茅台"),
    ("600585.SH", "海螺水泥"),
    ("600809.SH", "山西汾酒"),
    ("600887.SH", "伊利股份"),
    ("600900.SH", "长江电力"),
    ("601012.SH", "隆基绿能"),
    ("601088.SH", "中国神华"),
    ("601166.SH", "兴业银行"),
    ("601318.SH", "中国平安"),
    ("601398.SH", "工商银行"),
]


async def ensure_stocks(session: AsyncSession) -> list[Stock]:
    """确保样本股票在数据库中，返回 Stock 对象列表。"""
    stocks = []
    for code, name in CSI300_SAMPLE:
        result = await session.execute(select(Stock).where(Stock.code == code))
        stock = result.scalar_one_or_none()
        if stock is None:
            stock = Stock(code=code, name=name)
            session.add(stock)
        stocks.append(stock)
    await session.commit()
    return stocks


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


async def fetch_all_stocks_prices(session: AsyncSession) -> dict[str, int]:
    """批量获取所有样本股票的股价数据。"""
    stocks = await ensure_stocks(session)
    results = {}
    for stock in stocks:
        n = await fetch_and_store_prices(session, stock)
        results[stock.code] = n
    return results


async def fetch_news_for_stock(
    session: AsyncSession,
    stock: Stock,
    max_news: int = 50,
) -> int:
    """
    从 akshare 获取单个股票的近期新闻并去重写入 DB。
    返回新写入的记录数。
    """
    symbol = stock.code.split(".")[0]

    try:
        df = ak.stock_news_em(symbol=symbol)
    except Exception:
        return 0

    if df.empty:
        return 0

    count = 0
    for _, row in df.head(max_news).iterrows():
        title = str(row.get("title", row.get("标题", "")))
        content = str(row.get("content", row.get("内容", "")))
        url = str(row.get("url", row.get("链接", "")))
        source = str(row.get("source", row.get("来源", "")))
        pub_time_str = str(row.get("publish_time", row.get("发布时间", "")))

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
            title=title,
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
