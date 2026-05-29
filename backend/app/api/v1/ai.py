from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import get_db
from ...services.ai_analyst import analyze_stock, chat_with_agent

router = APIRouter()


class AnalyzeRequest(BaseModel):
    stock_code: str
    question: str = ""


class ChatRequest(BaseModel):
    stock_code: str | None = None
    message: str
    history: list[dict] | None = None


@router.post("/ai/analyze")
async def ai_analyze(req: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    """AI 综合分析 — 汇集行情、技术面、新闻情感，由大模型生成投资建议。"""
    result = await analyze_stock(db, code=req.stock_code, question=req.question or "")
    return result


@router.post("/ai/chat")
async def ai_chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """AI 对话智能体 — 无需预设股票，自动识别问题中的股票名称/代码。"""
    result = await chat_with_agent(
        db, message=req.message, code=req.stock_code, history=req.history
    )
    return result
