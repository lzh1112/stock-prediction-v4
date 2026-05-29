"""
AI 投资分析师 — 基于 LLM 的综合股票分析
收集行情、技术面、新闻情感等多维度数据，交由 DeepSeek 生成投资建议。
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta

from openai import AsyncOpenAI
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..models import Stock, DailyPrice, News, SentimentFeature

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_API_BASE,
            timeout=60,
        )
    return _client


ANALYST_PROMPT = """你是一位资深A股量化分析师。请根据提供的股票数据，进行专业的投资分析，并用中文回复。

按以下格式输出分析：

## 📊 技术面分析
- 根据近期价格走势、均线、成交量，判断当前处于什么阶段（上涨/下跌/盘整）
- 说明支撑位和压力位的大致区间

## 📰 新闻情绪分析
- 综合近期新闻的情感倾向，判断市场情绪
- 如有重大事件请特别指出

## ⚖️ 综合研判
- 多空因素汇总
- 给出偏向判断（看多/看空/中性观望）

## 💡 操作建议
- 给出1-2条具体可操作的建议
- 风险提示

注意：
- 使用具体数据支撑论点
- 提示投资有风险，分析仅供参考
- 简洁有力，每个部分控制在3-5句话
- 避免套话，给出有信息量的分析
"""


async def _gather_stock_data(session: AsyncSession, code: str) -> dict:
    """收集股票的多维度数据用于 AI 分析。"""
    result = await session.execute(select(Stock).where(Stock.code == code))
    stock = result.scalar_one_or_none()
    if not stock:
        return {}

    # 近60个交易日的价格
    cutoff = date.today() - timedelta(days=90)
    prices = (await session.execute(
        select(DailyPrice)
        .where(DailyPrice.stock_id == stock.id, DailyPrice.trade_date >= cutoff)
        .order_by(DailyPrice.trade_date.asc())
    )).scalars().all()

    # 最近30条新闻
    news_list = (await session.execute(
        select(News, SentimentFeature)
        .join(SentimentFeature, SentimentFeature.news_id == News.id, isouter=True)
        .where(News.stock_id == stock.id)
        .order_by(News.publish_time.desc())
        .limit(30)
    )).all()

    # 计算技术指标
    closes = [p.close for p in prices]
    volumes = [p.volume for p in prices]

    ma5 = sum(closes[-5:]) / min(len(closes), 5) if closes else 0
    ma10 = sum(closes[-10:]) / min(len(closes), 10) if closes else 0
    ma20 = sum(closes[-20:]) / min(len(closes), 20) if closes else 0

    change_5d = (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) >= 6 else 0
    change_20d = (closes[-1] - closes[-21]) / closes[-21] * 100 if len(closes) >= 21 else 0

    high_60d = max(p.high for p in prices) if prices else 0
    low_60d = min(p.low for p in prices) if prices else 0

    avg_vol_5d = sum(volumes[-5:]) / min(len(volumes), 5) if volumes else 0
    avg_vol_20d = sum(volumes[-20:]) / min(len(volumes), 20) if volumes else 0

    # 构建价格摘要
    price_summary = {
        "name": stock.name,
        "code": stock.code,
        "industry": stock.industry or "未知",
        "latest": {"date": str(prices[-1].trade_date) if prices else "N/A",
                    "open": prices[-1].open if prices else 0,
                    "high": prices[-1].high if prices else 0,
                    "low": prices[-1].low if prices else 0,
                    "close": prices[-1].close if prices else 0,
                    "volume": prices[-1].volume if prices else 0},
        "ma5": round(ma5, 2),
        "ma10": round(ma10, 2),
        "ma20": round(ma20, 2),
        "change_5d_pct": round(change_5d, 2),
        "change_20d_pct": round(change_20d, 2),
        "high_60d": round(high_60d, 2),
        "low_60d": round(low_60d, 2),
        "volume_ratio": round(avg_vol_5d / avg_vol_20d, 2) if avg_vol_20d > 0 else 0,
        "data_points": len(prices),
    }

    # 新闻摘要
    news_summary = []
    for news, sent in news_list:
        item = {
            "title": news.title[:100],
            "time": str(news.publish_time)[:10] if news.publish_time else "N/A",
        }
        if sent:
            item["sentiment"] = round(sent.sentiment_score, 2)
            item["event_type"] = sent.event_type
            if sent.raw_llm_response and isinstance(sent.raw_llm_response, dict):
                item["reason"] = sent.raw_llm_response.get("reason", "")
        news_summary.append(item)

    # 计算情感统计
    sent_scores = [s.sentiment_score for _, s in news_list if s and s.sentiment_score is not None]
    sentiment_stats = {}
    if sent_scores:
        sentiment_stats = {
            "avg_sentiment": round(sum(sent_scores) / len(sent_scores), 2),
            "positive_count": sum(1 for s in sent_scores if s > 0.1),
            "negative_count": sum(1 for s in sent_scores if s < -0.1),
            "neutral_count": sum(1 for s in sent_scores if -0.1 <= s <= 0.1),
        }

    return {
        "price_summary": price_summary,
        "news_summary": news_summary,
        "sentiment_stats": sentiment_stats,
    }


CHAT_SYSTEM_PROMPT = """你是一位资深A股量化分析助手，名字叫"小析"。你可以：

1. 回答关于A股市场、具体股票的任何问题
2. 解释技术指标（均线、成交量、K线形态、MACD、RSI、BOLL等）
3. 分析新闻事件对股价的影响
4. 给出操作建议，但始终提醒风险
5. 进行多轮深度讨论，记住用户之前提到的内容
6. 如果用户没有指定股票，可以先回答通用问题，然后引导用户说出具体的股票名称或代码
7. 遇到"你好""在吗"等寒暄，友好回应并介绍自己

聊天规则：
- 用中文回复，简洁有力，避免废话
- 用数据说话，引用具体数字
- 风格专业但不生硬，像一位有经验的交易员朋友
- 如果用户问的问题超出数据范围，坦诚说明局限
- 始终强调：分析仅供参考，不构成投资建议
- 使用适度的emoji让对话更生动（📈📉📊⚠️💡🔥等）
- 如果提供了股票实时数据，务必基于数据进行精准分析"""

GENERAL_SYSTEM_PROMPT = """你是一位资深A股量化分析助手，名字叫"小析"。

当前用户还没有指定具体股票。你可以：
1. 回答关于A股市场、交易规则、技术指标等通用问题
2. 引导用户说出想分析的股票名称或代码（如"茅台"、"600519"等）
3. 提供投资学习建议和市场观点

回复要求：简洁友好，用中文，适度使用emoji。始终提醒投资有风险。"""


async def _search_stocks(session: AsyncSession, keyword: str) -> list[dict]:
    """根据关键词搜索股票（按代码或名称模糊匹配）。"""
    import re

    results: list[dict] = []
    seen: set[str] = set()

    def add(stock):
        if stock.code not in seen:
            seen.add(stock.code)
            results.append({"code": stock.code, "name": stock.name, "industry": stock.industry or ""})

    # 1) 按6位数字代码搜索
    code_matches = re.findall(r"\b(\d{6})\b", keyword)
    for code in code_matches:
        for suffix in [".SH", ".SZ"]:
            stock = (await session.execute(
                select(Stock).where(Stock.code == f"{code}{suffix}")
            )).scalar_one_or_none()
            if stock:
                add(stock)
    if results:
        return results

    # 2) 按名称搜索 — 滑动窗口提取2-4字中文候选词
    # 先提取连续中文片段
    segments: list[str] = []
    buf: list[str] = []
    for ch in keyword:
        if "一" <= ch <= "鿿":
            buf.append(ch)
        else:
            if buf:
                segments.append("".join(buf))
                buf = []
    if buf:
        segments.append("".join(buf))

    # 在每个中文片段上用2/3/4字滑动窗口搜索
    checked: set[str] = set()
    for seg in segments:
        for win in (2, 3, 4):
            for i in range(len(seg) - win + 1):
                cand = seg[i:i + win]
                if cand in checked:
                    continue
                checked.add(cand)
                matched = (await session.execute(
                    select(Stock).where(Stock.name.contains(cand)).limit(3)
                )).scalars().all()
                for s in matched:
                    add(s)
                if len(results) >= 5:
                    return results[:5]

    return results[:5]


async def _build_stock_context(session: AsyncSession, code: str) -> str:
    """构建股票数据上下文，注入到对话中。"""
    data = await _gather_stock_data(session, code)
    if not data:
        return ""

    ps = data["price_summary"]
    ctx = f"""## 当前分析标的: {ps['name']} ({ps['code']}) | 行业: {ps['industry']}

实时数据:
- 最新收盘: {ps['latest']['close']:.2f} (日期: {ps['latest']['date']})
- 今日区间: {ps['latest']['low']:.2f} - {ps['latest']['high']:.2f}
- 成交量: {ps['latest']['volume']:,}
- MA5: {ps['ma5']} | MA10: {ps['ma10']} | MA20: {ps['ma20']}
- 均线排列: {"多头" if ps['ma5'] > ps['ma10'] > ps['ma20'] else ("空头" if ps['ma5'] < ps['ma10'] < ps['ma20'] else "交叉震荡")}
- 5日涨跌: {ps['change_5d_pct']:+.2f}% | 20日涨跌: {ps['change_20d_pct']:+.2f}%
- 60日最高: {ps['high_60d']} | 60日最低: {ps['low_60d']}
- 量比(5日/20日均量): {ps['volume_ratio']}

新闻情绪: 共{len(data['news_summary'])}条, 平均情感{data['sentiment_stats'].get('avg_sentiment', 'N/A')}, 正面{data['sentiment_stats'].get('positive_count', 0)}条/负面{data['sentiment_stats'].get('negative_count', 0)}条/中性{data['sentiment_stats'].get('neutral_count', 0)}条
"""

    if data["news_summary"]:
        ctx += "近期要闻:\n"
        for n in data["news_summary"][:8]:
            sent_str = f" [{n.get('sentiment', '?')}]" if "sentiment" in n else ""
            ctx += f"  - {n['time']} | {n['title'][:80]}{sent_str}\n"

    return ctx


async def analyze_stock(session: AsyncSession, code: str, question: str = "") -> dict:
    """对指定股票进行全面 AI 分析。"""
    if not settings.LLM_API_KEY:
        return {"error": "未配置 LLM API Key，请检查 .env 文件"}

    data = await _gather_stock_data(session, code)
    if not data:
        return {"error": f"未找到股票 {code} 的数据"}

    ctx = await _build_stock_context(session, code)
    user_query = question if question else "请对该股票进行全面分析并给出操作建议。"
    user_message = f"{ctx}\n\n---\n用户: {user_query}"

    client = _get_client()
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": ANALYST_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=1200,
        )
        analysis = response.choices[0].message.content or ""
    except Exception as e:
        return {"error": f"AI 分析请求失败: {str(e)}"}

    return {
        "stock": {"code": ps["code"], "name": ps["name"], "industry": ps["industry"]},
        "analysis": analysis,
        "data_snapshot": {
            "price": f"{ps['latest']['close']:.2f}",
            "change_5d": f"{ps['change_5d_pct']:+.2f}%",
            "ma_signal": "多头排列" if ps['ma5'] > ps['ma10'] > ps['ma20'] else (
                "空头排列" if ps['ma5'] < ps['ma10'] < ps['ma20'] else "交叉震荡"
            ),
            "sentiment_avg": data["sentiment_stats"].get("avg_sentiment", 0),
        },
    }


async def chat_with_agent(
    session: AsyncSession,
    message: str,
    code: str | None = None,
    history: list[dict] | None = None,
) -> dict:
    """多轮对话智能体 — 支持自动识别股票、无需预设代码。"""
    if not settings.LLM_API_KEY:
        return {"reply": "未配置 LLM API Key，请检查 .env 文件中的 LLM_API_KEY。"}

    stock = None
    ctx = ""
    matched_stocks = []
    active_code = code

    if not active_code:
        # 自动检测用户消息中的股票关键词
        matched_stocks = await _search_stocks(session, message)
        if len(matched_stocks) == 1:
            active_code = matched_stocks[0]["code"]
        # 也检查历史中是否有已绑定的股票
        if not active_code and history:
            for h in reversed(history):
                if h.get("role") == "system" and "当前分析标的" in h.get("content", ""):
                    # 从历史上下文提取之前绑定的code
                    import re
                    m = re.search(r"\((\d{6}\.(?:SH|SZ))\)", h.get("content", ""))
                    if m:
                        active_code = m.group(1)
                    break

    # 构建股票上下文（如果有确定标的）
    if active_code:
        stock = (await session.execute(select(Stock).where(Stock.code == active_code))).scalar_one_or_none()
        if stock:
            ctx = await _build_stock_context(session, active_code)

    # 构建系统消息
    messages = []
    if ctx and stock:
        messages = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {"role": "system", "content": f"以下是用户关注的股票实时数据，请基于这些数据回答：\n\n{ctx}"},
        ]
    elif matched_stocks and len(matched_stocks) > 1:
        stock_list = "\n".join(f"- {s['code']} {s['name']} ({s['industry']})" for s in matched_stocks)
        msg_content = f"用户提到了多只股票：\n{stock_list}\n\n请让用户确认要分析哪一只，并列出这些股票供选择。"
        messages = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {"role": "system", "content": msg_content},
        ]
    else:
        messages = [
            {"role": "system", "content": GENERAL_SYSTEM_PROMPT},
        ]

    # 注入历史消息
    if history:
        for h in history[-20:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": message})

    client = _get_client()
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=messages,
            temperature=0.5,
            max_tokens=1000,
        )
        reply = response.choices[0].message.content or ""
    except Exception as e:
        return {"reply": f"AI 请求失败: {str(e)}"}

    result: dict = {"reply": reply}
    if stock:
        result["stock"] = {"code": stock.code, "name": stock.name}
    if matched_stocks:
        result["matched_stocks"] = matched_stocks
    return result
