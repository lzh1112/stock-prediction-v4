from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.deps import engine
from .api.v1 import admin, ai, market, news, predict, stocks
from .core.config import settings
from .core.exceptions import AppException
from .models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：创建表 + 确保数据目录存在
    os.makedirs(os.path.dirname(settings.DATABASE_PATH) or ".", exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 关闭时
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="4.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_DEBUG else ["http://localhost:3000", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_timing_and_log(request: Request, call_next):
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


app.include_router(market.router, prefix="/api/v1", tags=["market"])
app.include_router(stocks.router, prefix="/api/v1", tags=["stocks"])
app.include_router(news.router, prefix="/api/v1", tags=["news"])
app.include_router(predict.router, prefix="/api/v1", tags=["predict"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
app.include_router(ai.router, prefix="/api/v1", tags=["ai"])


@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok", "version": "4.0.0"}
