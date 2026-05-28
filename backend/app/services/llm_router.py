"""
LLM 情感特征提取服务

通过 OpenAI 兼容 API 提取新闻的:
- event_type: 事件类型 (earnings/merger/policy/market/other)
- sentiment_score: 情感得分 [-1, 1]
- intensity: 事件强度 [0, 1]
- relevance: 与目标股票的相关度 [0, 1]
"""

from __future__ import annotations

import json
import re
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from ..core.config import settings

# 仅在 API Key 存在时初始化
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_API_BASE,
            timeout=settings.LLM_TIMEOUT,
        )
    return _client


class SentimentOutput(BaseModel):
    event_type: str = Field(description="earnings, merger, policy, market, product, or other")
    sentiment_score: float = Field(ge=-1.0, le=1.0, description="-1极度负面, 1极度正面")
    intensity: float = Field(ge=0.0, le=1.0, description="事件影响力强度")
    relevance: float = Field(ge=0.0, le=1.0, description="与目标公司的相关程度")
    reason: str = Field(max_length=120, description="简短理由")


SYSTEM_PROMPT = """你是金融新闻分析专家。对输入的新闻，提取以下信息，以 JSON 格式输出:

{
  "event_type": "earnings(财报)/merger(并购)/policy(政策)/market(行情)/product(产品)/other(其他)",
  "sentiment_score": 情感得分, -1(极度负面) 到 1(极度正面),
  "intensity": 事件强度, 0(弱) 到 1(强),
  "relevance": 与目标公司的相关度, 0 到 1,
  "reason": "简短理由(20字以内)"
}

只输出JSON，不要其他内容。"""


def _extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON，处理 markdown 代码块包裹。"""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
async def extract_sentiment(title: str, content: str, stock_name: str) -> SentimentOutput | None:
    """提取单条新闻的情感特征。失败重试最多3次。"""

    if not settings.LLM_API_KEY:
        return None

    user_text = f"目标公司: {stock_name}\n新闻标题: {title}\n新闻内容: {content[:800] or title}"

    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        temperature=0.1,
        max_tokens=300,
    )

    raw = response.choices[0].message.content or "{}"
    try:
        data = _extract_json(raw)
        return SentimentOutput(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        return None


async def batch_extract_sentiment(
    news_list: list[dict],
    stock_name: str = "",
) -> list[dict]:
    """批量提取多条新闻的情感。"""
    results = []
    for news in news_list:
        result = await extract_sentiment(
            title=news.get("title", ""),
            content=news.get("content", ""),
            stock_name=stock_name,
        )
        results.append({
            "news_id": news.get("id"),
            "sentiment": result.model_dump() if result else None,
        })
    return results
