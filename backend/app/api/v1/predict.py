from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    stock_code: str = Field(..., description="股票代码，如 600519.SH")


class FactorItem(BaseModel):
    factor: str
    weight: float


class PredictResponse(BaseModel):
    stock_code: str
    predict_date: str
    target_date: str
    predicted_prob: float = Field(..., ge=0, le=1, description="上涨概率")
    predicted_label: str = Field(..., description="up 或 down")
    confidence: float = Field(..., ge=0, le=1)
    top_factors: list[FactorItem]
    model_version: str


router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """预测单只股票次日涨跌概率。LLM 特征需已预计算。"""
    # 阶段 3 实现：加载 ONNX 模型 → 查特征 → 推理
    raise HTTPException(status_code=501, detail="预测服务尚未部署")


@router.get("/predict/history")
async def get_prediction_history(
    stock_code: str,
    days: int = 30,
):
    """获取历史预测记录（用于前端绘制胜率曲线）"""
    return {"stock_code": stock_code, "records": []}
