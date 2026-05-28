from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from datetime import date, timedelta
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import get_db
from ...core.config import settings
from ...services.data_fetcher import fetch_all_stocks_prices, fetch_all_stocks_news
from ...services.llm_router import extract_sentiment
from ...services.shadow import run_shadow_predictions, backfill_actual_prices, get_shadow_stats
from ...models import Stock, News, SentimentFeature

router = APIRouter()


@router.get("/admin/health")
async def service_health(db: AsyncSession = Depends(get_db)):
    components = {}
    try:
        await db.execute(text("SELECT 1"))
        components["database"] = "ok"
    except Exception as e:
        components["database"] = f"error: {e}"

    components["redis"] = "disabled (prototype)"
    components["celery"] = "disabled (prototype)"

    all_ok = all(v == "ok" or v.startswith("disabled") for v in components.values())
    return {"status": "ok" if all_ok else "degraded", "components": components}


@router.post("/admin/seed-data")
async def seed_data(db: AsyncSession = Depends(get_db)):
    """抓取 50 只沪深 300 成分股的近一年股价数据。可能需要几分钟。"""
    results = await fetch_all_stocks_prices(db)
    total = sum(results.values())
    return {
        "status": "ok",
        "total_records": total,
        "stocks_processed": len(results),
        "details": results,
    }


@router.post("/admin/seed-news")
async def seed_news(db: AsyncSession = Depends(get_db)):
    """抓取 50 只股票的近期财经新闻。每只约 10-30 条。"""
    results = await fetch_all_stocks_news(db)
    total = sum(results.values())
    return {
        "status": "ok",
        "total_news": total,
        "stocks_processed": len(results),
    }


@router.post("/admin/extract-sentiment")
async def extract_sentiment_batch(
    stock_code: str = "600519.SH",
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """对指定股票的最近 N 条新闻提取LLM情感特征。需要配置 LLM_API_KEY。"""
    stock = (await db.execute(select(Stock).where(Stock.code == stock_code))).scalar_one_or_none()
    if stock is None:
        return {"status": "error", "message": f"股票 {stock_code} 不存在"}

    news_list = (await db.execute(
        select(News)
        .where(News.stock_id == stock.id)
        .order_by(News.publish_time.desc())
        .limit(limit)
    )).scalars().all()

    if not news_list:
        return {"status": "ok", "processed": 0, "message": "无新闻数据"}

    count = 0
    for news in news_list:
        existing = (await db.execute(
            select(SentimentFeature).where(SentimentFeature.news_id == news.id)
        )).scalar_one_or_none()
        if existing:
            continue

        result = await extract_sentiment(
            title=news.title,
            content=news.content or "",
            stock_name=stock.name,
        )
        if result is None:
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
        count += 1

    await db.commit()
    return {"status": "ok", "processed": count, "total_news": len(news_list)}


@router.post("/admin/shadow-run")
async def shadow_run(db: AsyncSession = Depends(get_db)):
    """对全部50只股票运行当日影子预测。"""
    results = await run_shadow_predictions(db)
    return {"status": "ok", **results}


@router.post("/admin/shadow-backfill")
async def shadow_backfill(db: AsyncSession = Depends(get_db)):
    """回填已达目标日期的影子预测实际结果。"""
    results = await backfill_actual_prices(db)
    return {"status": "ok", **results}


@router.get("/admin/shadow-stats")
async def shadow_stats(days: int = 30, db: AsyncSession = Depends(get_db)):
    """获取影子模式累计胜率统计。"""
    return await get_shadow_stats(db, days=days)


@router.get("/admin/shadow-daily")
async def shadow_daily(days: int = 60, db: AsyncSession = Depends(get_db)):
    """获取每日胜率（用于回测曲线图）。"""
    from ...models import DailyShadow

    today = date.today()
    cutoff = today - timedelta(days=days)

    records = (await db.execute(
        select(DailyShadow).where(
            DailyShadow.predict_date >= cutoff,
            DailyShadow.is_correct.isnot(None),
        ).order_by(DailyShadow.predict_date.asc())
    )).scalars().all()

    daily = {}
    for r in records:
        d = r.predict_date.isoformat()
        daily.setdefault(d, {"total": 0, "correct": 0})
        daily[d]["total"] += 1
        daily[d]["correct"] += int(r.is_correct)

    result = []
    cumulative_correct = 0
    cumulative_total = 0
    for d in sorted(daily):
        cumulative_correct += daily[d]["correct"]
        cumulative_total += daily[d]["total"]
        wr = daily[d]["correct"] / daily[d]["total"] if daily[d]["total"] > 0 else 0
        cwr = cumulative_correct / cumulative_total if cumulative_total > 0 else 0
        result.append({
            "date": d,
            "win_rate": round(wr, 4),
            "cumulative_win_rate": round(cwr, 4),
            "total": daily[d]["total"],
            "correct": daily[d]["correct"],
        })

    return {"daily": result, "overall_win_rate": round(cumulative_correct / cumulative_total, 4) if cumulative_total > 0 else 0}


@router.post("/admin/reload-model")
async def reload_model():
    return {"status": "not_implemented", "message": "模型热加载将在阶段 3 实现"}
