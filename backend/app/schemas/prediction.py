from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    stock_code: str = Field(..., description="股票代码，如 600519.SH")


class FactorItem(BaseModel):
    factor: str
    weight: float


class PredictionResponse(BaseModel):
    stock_code: str
    predict_date: str
    target_date: str
    predicted_prob: float = Field(..., ge=0, le=1)
    predicted_label: str = Field(..., description="up 或 down")
    confidence: float = Field(..., ge=0, le=1)
    top_factors: list[FactorItem]
    model_version: str


class ShadowRecord(BaseModel):
    predict_date: date
    target_date: date
    predicted_prob: float
    predicted_label: str
    actual_close: float | None
    is_correct: bool | None
    confidence: float

    class Config:
        from_attributes = True
