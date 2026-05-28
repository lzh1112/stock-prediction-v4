"""
简单预测服务 (原型版 — 技术指标 + 规则基预测)

阶段 2-3 将被 ML 模型替代。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PredictResult:
    stock_code: str
    predict_date: str
    target_date: str
    predicted_prob: float
    predicted_label: str  # "up" or "down"
    confidence: float
    top_factors: list[dict]
    model_version: str = "prototype-v0"


def compute_sma(prices: list[float], window: int) -> list[float]:
    """简单移动平均"""
    if len(prices) < window:
        return [prices[-1]] * len(prices) if prices else []
    result = []
    for i in range(len(prices)):
        if i < window - 1:
            result.append(sum(prices[: i + 1]) / (i + 1))
        else:
            result.append(sum(prices[i - window + 1 : i + 1]) / window)
    return result


def compute_rsi(prices: list[float], window: int = 14) -> float:
    """计算 RSI 指标 (最近值)"""
    if len(prices) < window + 1:
        return 50.0

    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gains.append(diff if diff > 0 else 0)
        losses.append(-diff if diff < 0 else 0)

    avg_gain = sum(gains[-window:]) / window
    avg_loss = sum(losses[-window:]) / window
    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_macd(prices: list[float]) -> dict:
    """计算 MACD 指标"""
    if len(prices) < 26:
        return {"macd": 0, "signal": 0, "histogram": 0}

    ema12 = prices[0]
    ema26 = prices[0]
    k12 = 2 / (12 + 1)
    k26 = 2 / (26 + 1)
    k9 = 2 / (9 + 1)

    macd_values = []
    for p in prices[1:]:
        ema12 = p * k12 + ema12 * (1 - k12)
        ema26 = p * k26 + ema26 * (1 - k26)
        macd_values.append(ema12 - ema26)

    signal = macd_values[0]
    signal_values = [signal]
    for m in macd_values[1:]:
        signal = m * k9 + signal * (1 - k9)
        signal_values.append(signal)

    return {
        "macd": round(macd_values[-1], 4),
        "signal": round(signal_values[-1], 4),
        "histogram": round(macd_values[-1] - signal_values[-1], 4),
    }


def rule_based_predict(closes: list[float]) -> PredictResult:
    """
    基于技术指标的简单规则预测:
    - SMA 金叉/死叉
    - MACD 方向
    - RSI 超买/超卖
    - 近期动量
    """
    if len(closes) < 30:
        return PredictResult(
            stock_code="",
            predict_date="",
            target_date="",
            predicted_prob=0.5,
            predicted_label="up",
            confidence=0.0,
            top_factors=[],
        )

    sma5 = compute_sma(closes, 5)
    sma20 = compute_sma(closes, 20)
    rsi = compute_rsi(closes)
    macd = compute_macd(closes)

    momentum_5d = (closes[-1] / closes[-6]) - 1 if len(closes) >= 6 else 0
    momentum_10d = (closes[-1] / closes[-11]) - 1 if len(closes) >= 11 else 0

    score = 0.0
    factors = []

    # SMA 交叉
    sma_bullish = sma5[-1] > sma20[-1]
    sma_bearish = sma5[-1] < sma20[-1]
    if sma_bullish:
        score += 0.15
        factors.append({"factor": "SMA金叉 (MA5>MA20)", "weight": 0.15})
    if sma_bearish:
        score -= 0.15
        factors.append({"factor": "SMA死叉 (MA5<MA20)", "weight": -0.15})

    # MACD
    if macd["histogram"] > 0:
        score += 0.12
        factors.append({"factor": "MACD柱>0", "weight": 0.12})
    else:
        score -= 0.12
        factors.append({"factor": "MACD柱<0", "weight": -0.12})

    # RSI
    if rsi < 30:
        score += 0.10
        factors.append({"factor": f"RSI超卖 ({rsi:.1f})", "weight": 0.10})
    elif rsi > 70:
        score -= 0.10
        factors.append({"factor": f"RSI超买 ({rsi:.1f})", "weight": -0.10})

    # 动量
    if momentum_5d > 0.02:
        score += 0.10
        factors.append({"factor": f"5日动量 {momentum_5d:.2%}", "weight": 0.10})
    elif momentum_5d < -0.02:
        score -= 0.10
        factors.append({"factor": f"5日动量 {momentum_5d:.2%}", "weight": -0.10})

    prob = 0.5 + score
    prob = max(0.01, min(0.99, prob))
    label = "up" if prob >= 0.5 else "down"
    confidence = abs(prob - 0.5) * 2  # [0, 1]

    return PredictResult(
        stock_code="",
        predict_date="",
        target_date="",
        predicted_prob=round(prob, 4),
        predicted_label=label,
        confidence=round(confidence, 4),
        top_factors=sorted(factors, key=lambda x: abs(x["weight"]), reverse=True),
    )
