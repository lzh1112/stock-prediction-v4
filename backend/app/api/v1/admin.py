from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import get_db
from ...services.data_fetcher import fetch_all_stocks_prices

router = APIRouter()


@router.get("/admin/health")
async def service_health(db: AsyncSession = Depends(get_db)):
    components = {}
    try:
        await db.execute(text("SELECT 1"))
        components["database"] = "ok"
    except Exception as e:
        components["database"] = f"error: {e}"

    components["redis"] = "disabled (prototype)"
    components["celery"] = "disabled (prototype)"

    all_ok = all(v == "ok" or v.startswith("disabled") for v in components.values())
    return {"status": "ok" if all_ok else "degraded", "components": components}


@router.post("/admin/seed-data")
async def seed_data(db: AsyncSession = Depends(get_db)):
    """抓取 50 只沪深 300 成分股的近一年股价数据。可能需要几分钟。"""
    results = await fetch_all_stocks_prices(db)
    total = sum(results.values())
    return {
        "status": "ok",
        "total_records": total,
        "stocks_processed": len(results),
        "details": results,
    }


@router.post("/admin/reload-model")
async def reload_model():
    return {"status": "not_implemented", "message": "模型热加载将在阶段 3 实现"}
