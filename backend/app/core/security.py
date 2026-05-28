from __future__ import annotations

from fastapi import Header, HTTPException
from .config import settings


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """简单的 API Key 鉴权。生产环境应替换为 JWT 或 OAuth2。"""
    if settings.APP_ENV == "development":
        return "dev-user"

    if not x_api_key or x_api_key != settings.SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key
