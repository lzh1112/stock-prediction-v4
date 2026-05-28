from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_list_stocks(client: AsyncClient):
    response = await client.get("/api/v1/stocks")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_predict_not_ready(client: AsyncClient):
    """预测接口阶段 3 前返回 501。"""
    response = await client.post("/api/v1/predict", json={"stock_code": "000001.SZ"})
    assert response.status_code == 501


@pytest.mark.asyncio
async def test_admin_health(client: AsyncClient):
    response = await client.get("/api/v1/admin/health")
    assert response.status_code == 200
