from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.v1 import admin, news, predict, stocks
from .core.config import settings
from .core.exceptions import AppException


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：初始化数据库连接池、加载模型
    yield
    # 关闭时：清理资源


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="4.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

# --- 中间件 ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_DEBUG else ["http://localhost:3000", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_timing_and_log(request: Request, call_next):
    """请求计时 + 全局异常捕获。"""
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except AppException as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "detail": exc.detail},
        )
    elapsed = time.perf_counter() - start
    response.headers["X-Response-Time-ms"] = f"{elapsed * 1000:.1f}"
    return response


# --- 路由注册 ---

app.include_router(stocks.router, prefix="/api/v1", tags=["stocks"])
app.include_router(news.router, prefix="/api/v1", tags=["news"])
app.include_router(predict.router, prefix="/api/v1", tags=["predict"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])


@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok", "version": "4.0.0"}
