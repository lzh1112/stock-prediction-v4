"""
影子模式服务

每个交易日收盘后:
1. 对所有股票运行预测，写入 daily_shadow
2. 次日收盘后回填实际股价，计算预测正确性
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Stock, DailyPrice, DailyShadow
from .predictor import ml_predict


async def run_shadow_predictions(db: AsyncSession) -> dict:
    """对全部50只股票运行预测，写入 daily_shadow。"""
    stocks = (await db.execute(select(Stock))).scalars().all()

    today = date.today()
    results = {"success": 0, "skipped": 0, "failed": 0}

    for stock in stocks:
        # 检查是否今天已有预测
        existing = await db.execute(
            select(DailyShadow).where(
                DailyShadow.stock_id == stock.id,
                DailyShadow.predict_date == today,
            )
        )
        if existing.scalar_one_or_none():
            results["skipped"] += 1
            continue

        # 获取K线
        cutoff = today - timedelta(days=180)
        prices = (await db.execute(
            select(DailyPrice)
            .where(DailyPrice.stock_id == stock.id, DailyPrice.trade_date >= cutoff)
            .order_by(DailyPrice.trade_date.asc())
        )).scalars().all()

        if len(prices) < 40:
            results["failed"] += 1
            continue

        closes = [p.close for p in prices]
        highs = [p.high for p in prices]
        lows = [p.low for p in prices]
        volumes = [float(p.volume) for p in prices]

        pred = ml_predict(stock.code, closes, highs, lows, volumes)
        if pred is None:
            results["failed"] += 1
            continue

        shadow = DailyShadow(
            stock_id=stock.id,
            predict_date=today,
            target_date=today + timedelta(days=3),
            predicted_prob=pred.predicted_prob,
            predicted_label=pred.predicted_label,
            confidence=pred.confidence,
            top_factors=pred.top_factors,
            model_version=pred.model_version,
        )
        db.add(shadow)
        results["success"] += 1

    await db.commit()
    return results


async def backfill_actual_prices(db: AsyncSession) -> dict:
    """回填已达目标日期的预测的实际结果。"""
    today = date.today()
    records = (await db.execute(
        select(DailyShadow).where(
            DailyShadow.actual_close.is_(None),
            DailyShadow.target_date <= today,
        )
    )).scalars().all()

    results = {"checked": len(records), "updated": 0}

    for record in records:
        price = (await db.execute(
            select(DailyPrice).where(
                DailyPrice.stock_id == record.stock_id,
                DailyPrice.trade_date == record.target_date,
            )
        )).scalar_one_or_none()

        if price is None:
            continue

        # 获取预测日的收盘价
        pred_day_price = (await db.execute(
            select(DailyPrice).where(
                DailyPrice.stock_id == record.stock_id,
                DailyPrice.trade_date == record.predict_date,
            )
        )).scalar_one_or_none()

        if pred_day_price is None:
            continue

        record.actual_close = price.close
        record.is_correct = (
            (record.predicted_label == "up" and price.close > pred_day_price.close) or
            (record.predicted_label == "down" and price.close <= pred_day_price.close)
        )
        results["updated"] += 1

    await db.commit()
    return results


async def get_shadow_stats(db: AsyncSession, days: int = 30) -> dict:
    """获取影子模式统计：胜率、累计表现等。"""
    today = date.today()
    cutoff = today - timedelta(days=days)

    records = (await db.execute(
        select(DailyShadow).where(
            DailyShadow.predict_date >= cutoff,
            DailyShadow.is_correct.isnot(None),
        )
    )).scalars().all()

    total = len(records)
    correct = sum(1 for r in records if r.is_correct)

    return {
        "total_predictions": total,
        "correct": correct,
        "win_rate": round(correct / total, 4) if total > 0 else 0,
        "days": days,
    }
