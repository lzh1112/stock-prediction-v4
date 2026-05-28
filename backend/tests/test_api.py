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
async def test_predict_no_data(client: AsyncClient):
    """无数据时返回 404（股票不存在）或 400（数据不足）。"""
    response = await client.post("/api/v1/predict", json={"stock_code": "000001.SZ"})
    assert response.status_code in (404, 400)


@pytest.mark.asyncio
async def test_admin_health(client: AsyncClient):
    response = await client.get("/api/v1/admin/health")
    assert response.status_code == 200
