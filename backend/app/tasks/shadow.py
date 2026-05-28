from __future__ import annotations

from . import celery_app


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def run_daily_shadow(self):
    """每日影子模式：拉取数据 → LLM 特征 → 模型预测 → 写入 daily_shadow 表。阶段 4 实现。"""
    pass


@celery_app.task(bind=True, max_retries=1)
def backfill_actual_prices(self):
    """次日收盘后回填实际股价，计算 is_correct。阶段 4 实现。"""
    pass
