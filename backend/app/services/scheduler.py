"""
内置轻量调度器 — 桌面模式自动定时更新

当 Redis 不可用时（即 Celery beat 无法工作），自动启用 asyncio 后台定时器，
在每个交易日收盘后执行数据抓取和影子预测。
"""

from __future__ import annotations

import asyncio
import logging
import socket
import time
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

# 默认执行时间（北京时间）
DEFAULT_FETCH_HOUR = 15
DEFAULT_FETCH_MINUTE = 45
DEFAULT_SHADOW_HOUR = 16
DEFAULT_SHADOW_MINUTE = 15

# 检查间隔（秒）
CHECK_INTERVAL = 60


def _is_redis_available(redis_url: str) -> bool:
    """检测 Redis 是否可达。"""
    try:
        # redis://localhost:6379/1 → host=localhost, port=6379
        parts = redis_url.replace("redis://", "").split(":")
        host = parts[0] if parts else "localhost"
        port_str = parts[1].split("/")[0] if len(parts) > 1 else "6379"
        port = int(port_str)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _is_weekday(d: date | None = None) -> bool:
    """判断是否为交易日（周一至周五）。"""
    d = d or date.today()
    return d.weekday() < 5  # 0=Mon, 4=Fri


def _beijing_now() -> datetime:
    """获取北京时间当前时刻。"""
    return datetime.now()  # 系统已配置为 Asia/Shanghai 时区


class BuiltinScheduler:
    """轻量级 asyncio 定时调度器。"""

    def __init__(
        self,
        redis_url: str = "",
        fetch_hour: int = DEFAULT_FETCH_HOUR,
        fetch_minute: int = DEFAULT_FETCH_MINUTE,
        shadow_hour: int = DEFAULT_SHADOW_HOUR,
        shadow_minute: int = DEFAULT_SHADOW_MINUTE,
    ):
        self._redis_url = redis_url
        self._fetch_hour = fetch_hour
        self._fetch_minute = fetch_minute
        self._shadow_hour = shadow_hour
        self._shadow_minute = shadow_minute
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        # 记录今天已执行的任务，防止重复
        self._last_fetch_date: date | None = None
        self._last_shadow_date: date | None = None

    @property
    def enabled(self) -> bool:
        """Redis 不可用时自动启用。"""
        if not self._redis_url:
            return True
        return not _is_redis_available(self._redis_url)

    async def start(self):
        """启动后台调度循环。"""
        if not self.enabled:
            logger.info("内置调度器: Redis 可用，跳过（由 Celery beat 接管）")
            return

        logger.info(
            "内置调度器: Redis 不可用，启动 asyncio 定时调度（数据抓取 %02d:%02d，影子预测 %02d:%02d 北京时间）",
            self._fetch_hour, self._fetch_minute,
            self._shadow_hour, self._shadow_minute,
        )
        self._stop_event.clear()
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        """停止调度循环。"""
        if self._task is None:
            return
        logger.info("内置调度器: 正在停止…")
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("内置调度器: 已停止")

    async def _loop(self):
        """主循环：每分钟检查一次是否到执行时间。"""
        while not self._stop_event.is_set():
            try:
                await self._tick()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("内置调度器 tick 异常")
            # 等待下一次检查
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=CHECK_INTERVAL)
            except asyncio.TimeoutError:
                pass  # 正常超时，继续循环

    async def _tick(self):
        """单次检查：到点且是交易日则执行。"""
        now = _beijing_now()
        today = now.date()

        if not _is_weekday(today):
            return

        current_minutes = now.hour * 60 + now.minute

        # 15:45 数据抓取
        fetch_minutes = self._fetch_hour * 60 + self._fetch_minute
        if current_minutes >= fetch_minutes and self._last_fetch_date != today:
            self._last_fetch_date = today
            logger.info("内置调度器: 触发数据抓取 (%s)", now.strftime("%H:%M"))
            await self._run_fetch()

        # 16:15 影子预测
        shadow_minutes = self._shadow_hour * 60 + self._shadow_minute
        if current_minutes >= shadow_minutes and self._last_shadow_date != today:
            self._last_shadow_date = today
            logger.info("内置调度器: 触发影子预测 (%s)", now.strftime("%H:%M"))
            await self._run_shadow()

    async def _run_fetch(self):
        """执行数据抓取。"""
        try:
            from app.tasks.crawler import _fetch_prices_and_news
            t0 = time.monotonic()
            results = await _fetch_prices_and_news()
            elapsed = time.monotonic() - t0
            logger.info(
                "内置调度器: 数据抓取完成 — 股价 %d 条 / 新闻 %d 条，耗时 %.1f 秒",
                sum(results["prices"].values()),
                sum(results["news"].values()),
                elapsed,
            )
        except Exception:
            logger.exception("内置调度器: 数据抓取失败")

    async def _run_shadow(self):
        """执行影子预测。"""
        try:
            from app.tasks.shadow import _run_shadow_pipeline
            t0 = time.monotonic()
            results = await _run_shadow_pipeline()
            elapsed = time.monotonic() - t0
            pred = results.get("predict", {})
            logger.info(
                "内置调度器: 影子预测完成 — 成功 %d / 跳过 %d / 失败 %d，耗时 %.1f 秒",
                pred.get("success", 0),
                pred.get("skipped", 0),
                pred.get("failed", 0),
                elapsed,
            )
        except Exception:
            logger.exception("内置调度器: 影子预测失败")


# 模块级单例
_scheduler: BuiltinScheduler | None = None


def get_scheduler() -> BuiltinScheduler:
    """获取或创建内置调度器单例。"""
    global _scheduler
    if _scheduler is None:
        from app.core.config import settings
        _scheduler = BuiltinScheduler(redis_url=settings.CELERY_BROKER_URL)
    return _scheduler


async def start_scheduler():
    """启动内置调度器（由 FastAPI lifespan 调用）。"""
    await get_scheduler().start()


async def stop_scheduler():
    """停止内置调度器（由 FastAPI lifespan 调用）。"""
    await get_scheduler().stop()
