from __future__ import annotations

from celery import Celery

from ..core.config import settings

celery_app = Celery(
    "stock_pred",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.crawler",
        "app.tasks.sentiment",
        "app.tasks.shadow",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_prefetch_multiplier=1,
)

# 定时任务调度 (UTC 时间)
celery_app.conf.beat_schedule = {
    "daily-data-fetch": {
        "task": "app.tasks.crawler.fetch_daily_data",
        "schedule": 0,  # 占位，阶段 1B 配置为 crontab(30, 7) = 北京时间 15:30
    },
}
