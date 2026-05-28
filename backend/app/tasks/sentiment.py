from __future__ import annotations

from . import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def extract_sentiment(self, news_id: int):
    """对单条新闻执行 LLM 情感特征提取。阶段 2 实现。"""
    pass


@celery_app.task(bind=True, max_retries=2)
def batch_extract_sentiment(self, stock_code: str, days: int = 7):
    """批量处理某只股票的近期新闻。阶段 2 实现。"""
    pass
