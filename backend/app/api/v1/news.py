from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/news")
async def list_news(
    stock_code: str = Query(..., description="股票代码"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取某股票的新闻列表（含情感特征）"""
    return {
        "stock_code": stock_code,
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
    }


@router.get("/news/{news_id}")
async def get_news_detail(news_id: int):
    """获取单条新闻详情"""
    return {"news_id": news_id, "title": "", "content": "", "sentiment": {}}
