from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/admin/health")
async def service_health():
    """系统组件健康检查（DB, Redis, Celery）"""
    return {
        "status": "ok",
        "components": {
            "database": "unknown",
            "redis": "unknown",
            "celery": "unknown",
        },
    }


@router.post("/admin/reload-model")
async def reload_model():
    """热加载预测模型（无需重启服务）"""
    return {"status": "not_implemented", "message": "模型热加载将在阶段 3 实现"}
