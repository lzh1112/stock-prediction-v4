"""
市场总览 API — 返回全部股票的行情快照，支持按行业/交易所分类筛选
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import get_db
from ...models import Stock, DailyPrice, SentimentFeature, News

router = APIRouter()


@router.get("/market/overview")
async def market_overview(
    industry: str | None = Query(None, description="按行业筛选"),
    exchange: str | None = Query(None, description="按交易所筛选: SZ 或 SH"),
    sort_by: str = Query("change_pct", description="排序: change_pct, volume, code"),
    db: AsyncSession = Depends(get_db),
):
    """获取全部股票的行情快照（最新价、涨跌幅、成交量、情感倾向等）。"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    day_before = today - timedelta(days=2)

    # 获取所有股票
    stmt = select(Stock)
    if industry:
        stmt = stmt.where(Stock.industry == industry)
    if exchange:
        stmt = stmt.where(Stock.code.like(f"%.{exchange}"))
    stocks = (await db.execute(stmt.order_by(Stock.code))).scalars().all()

    items = []
    for stock in stocks:
        # 最新价 (昨天, 因为今天可能还没收盘)
        latest = (await db.execute(
            select(DailyPrice)
            .where(DailyPrice.stock_id == stock.id)
            .order_by(DailyPrice.trade_date.desc())
            .limit(2)
        )).scalars().all()

        if len(latest) < 2:
            continue

        today_price = latest[0]
        prev_price = latest[1]

        change_pct = round((today_price.close - prev_price.close) / prev_price.close * 100, 2)

        # 情感数据
        sentiment_avg = None
        sent_result = (await db.execute(
            select(SentimentFeature.sentiment_score)
            .join(News, SentimentFeature.news_id == News.id)
            .where(News.stock_id == stock.id)
            .order_by(SentimentFeature.created_at.desc())
            .limit(5)
        )).scalars().all()
        if sent_result:
            sentiment_avg = round(sum(s for s in sent_result if s is not None) / len([s for s in sent_result if s is not None]), 2) if any(s is not None for s in sent_result) else None

        items.append({
            "code": stock.code,
            "name": stock.name,
            "industry": stock.industry or "其他",
            "exchange": stock.code.split(".")[1],
            "close": today_price.close,
            "change_pct": change_pct,
            "volume": today_price.volume,
            "sentiment": sentiment_avg,
            "trade_date": str(today_price.trade_date),
        })

    # 排序
    if sort_by == "change_pct":
        items.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
    elif sort_by == "volume":
        items.sort(key=lambda x: x["volume"], reverse=True)
    else:
        items.sort(key=lambda x: x["code"])

    # 按行业分组
    industries: dict[str, list[dict]] = {}
    for item in items:
        ind = item["industry"]
        industries.setdefault(ind, []).append(item)

    # 统计
    up_count = sum(1 for i in items if i["change_pct"] > 0)
    down_count = sum(1 for i in items if i["change_pct"] < 0)

    return {
        "items": items,
        "by_industry": {k: v for k, v in sorted(industries.items())},
        "summary": {
            "total": len(items),
            "up": up_count,
            "down": down_count,
            "up_ratio": round(up_count / len(items), 2) if items else 0,
        },
        "industries": sorted(set(i["industry"] for i in items)),
    }
