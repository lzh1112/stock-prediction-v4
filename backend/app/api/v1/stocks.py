from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/stocks")
async def list_stocks(
    keyword: str = Query("", description="股票代码或名称关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """搜索股票列表"""
    return {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
    }


@router.get("/stocks/{code}")
async def get_stock_detail(code: str):
    """获取股票详情与历史K线"""
    return {
        "code": code,
        "name": "",
        "industry": "",
        "prices": [],
    }
