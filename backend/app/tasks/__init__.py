from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

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
    task_time_limit=3600,       # 数据抓取可能较慢，放宽到 1 小时
    task_soft_time_limit=3300,  # 软限制 55 分钟
    worker_prefetch_multiplier=1,
)

# 定时任务调度 (enable_utc=True 时 crontab 按 UTC 解释)
# 北京时间 = UTC + 8:
#   15:45 北京时间 → 07:45 UTC → crontab(hour=7, minute=45)
#   16:15 北京时间 → 08:15 UTC → crontab(hour=8, minute=15)
celery_app.conf.beat_schedule = {
    "daily-data-fetch": {
        "task": "app.tasks.crawler.fetch_daily_data",
        "schedule": crontab(hour=7, minute=45, day_of_week="1-5"),
        "options": {"queue": "default"},
    },
    "daily-shadow-run": {
        "task": "app.tasks.shadow.run_daily_shadow",
        "schedule": crontab(hour=8, minute=15, day_of_week="1-5"),
        "options": {"queue": "default"},
    },
}
