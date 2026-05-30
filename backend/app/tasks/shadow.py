"""
影子模式 Celery 定时任务

每日收盘数据更新后，自动运行预测并回填历史结果。
"""

from __future__ import annotations

import asyncio
import logging

from . import celery_app

logger = logging.getLogger(__name__)


async def _run_shadow_pipeline() -> dict:
    """异步执行影子预测 + 回填。"""
    from app.api.deps import async_session
    from app.services.shadow import run_shadow_predictions, backfill_actual_prices

    async with async_session() as session:
        # 1. 先回填历史预测的实际结果
        logger.info("回填历史影子预测结果…")
        backfill_results = await backfill_actual_prices(session)
        logger.info("回填完成 — 检查 %d 条，更新 %d 条",
                    backfill_results["checked"], backfill_results["updated"])

        # 2. 运行当日预测
        logger.info("开始运行当日影子预测…")
        predict_results = await run_shadow_predictions(session)
        logger.info("预测完成 — 成功 %d / 跳过 %d / 失败 %d",
                    predict_results["success"],
                    predict_results["skipped"],
                    predict_results["failed"])

    return {"backfill": backfill_results, "predict": predict_results}


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def run_daily_shadow(self):
    """每日影子模式：回填历史 + 运行预测 → 写入 daily_shadow 表。"""
    logger.info("Celery 定时任务 run_daily_shadow 开始执行…")
    try:
        results = asyncio.run(_run_shadow_pipeline())
        return {"status": "ok", **results}
    except Exception as exc:
        logger.error("run_daily_shadow 执行失败: %s", exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise


@celery_app.task(bind=True, max_retries=1)
def backfill_actual_prices(self):
    """次日收盘后回填实际股价，计算 is_correct。"""
    logger.info("Celery 任务 backfill_actual_prices 开始执行…")
    try:
        from app.api.deps import async_session
        from app.services.shadow import backfill_actual_prices as _backfill

        results = asyncio.run(_async_backfill())
        return {"status": "ok", **results}
    except Exception as exc:
        logger.error("backfill_actual_prices 执行失败: %s", exc, exc_info=True)
        raise


async def _async_backfill() -> dict:
    from app.api.deps import async_session
    from app.services.shadow import backfill_actual_prices

    async with async_session() as session:
        return await backfill_actual_prices(session)
