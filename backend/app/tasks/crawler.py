from __future__ import annotations

from . import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_daily_data(self):
    """每个交易日收盘后抓取股价和新闻数据。阶段 1B 实现。"""
    pass
