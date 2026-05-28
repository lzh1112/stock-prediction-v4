from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import get_db
from ...models import Stock
from ...services.data_fetcher import get_kline_data

router = APIRouter()


@router.get("/stocks")
async def list_stocks(
    keyword: str = Query("", description="股票代码或名称关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Stock)
        .where(
            (Stock.code.contains(keyword)) | (Stock.name.contains(keyword))
        )
        .order_by(Stock.code)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    stocks = result.scalars().all()

    count_result = await db.execute(
        select(Stock).where(
            (Stock.code.contains(keyword)) | (Stock.name.contains(keyword))
        )
    )
    total = len(count_result.scalars().all())

    return {
        "items": [{"code": s.code, "name": s.name, "industry": s.industry} for s in stocks],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/stocks/{code}")
async def get_stock_detail(code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Stock).where(Stock.code == code))
    stock = result.scalar_one_or_none()
    if stock is None:
        return {"code": code, "name": "", "industry": "", "prices": []}

    prices = await get_kline_data(db, code)
    return {
        "code": stock.code,
        "name": stock.name,
        "industry": stock.industry,
        "prices": prices,
    }
