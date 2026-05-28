from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import get_db
from ...models import Stock, DailyPrice
from ...schemas.prediction import PredictionResponse, FactorItem
from ...services.predictor import ml_predict

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
async def predict(request: "PredictRequest", db: AsyncSession = Depends(get_db)):
    stock_result = await db.execute(select(Stock).where(Stock.code == request.stock_code))
    stock = stock_result.scalar_one_or_none()
    if stock is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"股票 {request.stock_code} 不存在")

    today = date.today()
    cutoff = today - timedelta(days=180)
    result = await db.execute(
        select(DailyPrice)
        .where(DailyPrice.stock_id == stock.id, DailyPrice.trade_date >= cutoff)
        .order_by(DailyPrice.trade_date.asc())
    )
    prices = result.scalars().all()

    if len(prices) < 40:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"数据不足 ({len(prices)} 条K线, 需要至少40条)")

    closes = [p.close for p in prices]
    highs = [p.high for p in prices]
    lows = [p.low for p in prices]
    volumes = [float(p.volume) for p in prices]

    pred = ml_predict(request.stock_code, closes, highs, lows, volumes)
    if pred is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="模型未训练，请先运行 models/train_lightgbm.py")

    pred.predict_date = today.isoformat()
    pred.target_date = (today + timedelta(days=3)).isoformat()

    return PredictionResponse(
        stock_code=pred.stock_code,
        predict_date=pred.predict_date,
        target_date=pred.target_date,
        predicted_prob=pred.predicted_prob,
        predicted_label=pred.predicted_label,
        confidence=pred.confidence,
        top_factors=[FactorItem(factor=f["factor"], weight=f["weight"]) for f in pred.top_factors],
        model_version=pred.model_version,
    )


@router.get("/predict/history")
async def get_prediction_history(
    stock_code: str,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    stock = (await db.execute(select(Stock).where(Stock.code == stock_code))).scalar_one_or_none()
    if stock is None:
        return {"stock_code": stock_code, "records": []}

    from datetime import date
    from ...models import DailyShadow

    cutoff = date.today() - timedelta(days=days)
    records = (await db.execute(
        select(DailyShadow).where(
            DailyShadow.stock_id == stock.id,
            DailyShadow.predict_date >= cutoff,
        ).order_by(DailyShadow.predict_date.desc())
    )).scalars().all()

    return {
        "stock_code": stock_code,
        "records": [
            {
                "predict_date": r.predict_date.isoformat(),
                "target_date": r.target_date.isoformat(),
                "predicted_prob": r.predicted_prob,
                "predicted_label": r.predicted_label,
                "actual_close": r.actual_close,
                "is_correct": r.is_correct,
                "confidence": r.confidence,
            }
            for r in records
        ],
    }


class PredictRequest(BaseModel):
    stock_code: str = Field(..., description="股票代码，如 600519.SH")
