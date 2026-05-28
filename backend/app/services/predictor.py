"""
LightGBM 预测服务

加载训练好的 LightGBM 模型进行截面相对排名预测。
目标: 股票未来3日收益率进入截面前30%的概率。
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np

MODEL_PATH = Path(__file__).resolve().parent.parent.parent.parent / "models" / "lgbm_model.pkl"

_model_cache: dict | None = None


@dataclass
class PredictResult:
    stock_code: str
    predict_date: str
    target_date: str
    predicted_prob: float
    predicted_label: str
    confidence: float
    top_factors: list[dict]
    model_version: str


def _load_model() -> dict | None:
    global _model_cache
    if _model_cache is not None:
        return _model_cache
    try:
        with open(MODEL_PATH, "rb") as f:
            _model_cache = pickle.load(f)
        return _model_cache
    except FileNotFoundError:
        return None


def _compute_features(closes: list[float], highs: list[float] | None,
                      lows: list[float] | None, volumes: list[float] | None) -> dict | None:
    """计算与训练时一致的特征。需要至少40个交易日数据。"""
    n = len(closes)
    if n < 40:
        return None

    c = np.array(closes, dtype=np.float64)
    h = np.array(highs, dtype=np.float64) if highs else c
    l = np.array(lows, dtype=np.float64) if lows else c
    v = np.array(volumes, dtype=np.float64) if volumes else np.ones_like(c)

    # 收益率
    ret_1d = (c[-1] / c[-2] - 1) if n >= 2 else 0.0
    ret_5d = (c[-1] / c[-6] - 1) if n >= 6 else 0.0
    ret_10d = (c[-1] / c[-11] - 1) if n >= 11 else 0.0

    # 均线偏离
    ma5 = c[-5:].mean()
    ma20 = c[-20:].mean()
    ma5_bias = (c[-1] - ma5) / ma5
    ma20_bias = (c[-1] - ma20) / ma20

    # 波动率
    rets = np.diff(c[-21:]) / c[-21:-1]
    volatility_5d = rets[-5:].std() if len(rets) >= 5 else 0.0
    volatility_20d = rets.std() if len(rets) > 0 else 0.0

    # 量比
    vol_ma5 = v[-6:-1].mean()
    volume_ratio = v[-1] / vol_ma5 if vol_ma5 > 0 else 1.0

    # MACD
    ema12 = c[-12]
    ema26 = c[-26]
    for p in c[-11:]:
        ema12 = p * (2/13) + ema12 * (1 - 2/13)
    for p in c[-25:]:
        ema26 = p * (2/27) + ema26 * (1 - 2/27)
    macd_val = ema12 - ema26
    signal_val = macd_val * (2/10)
    macd_hist = macd_val - signal_val

    # RSI
    delta = np.diff(c[-15:])
    gain = np.maximum(delta, 0).mean()
    loss = np.maximum(-delta, 0).mean()
    rs = gain / (loss + 1e-9)
    rsi = 100.0 - (100.0 / (1.0 + rs))

    # 高低价比率
    hl_ratio = (h[-1] - l[-1]) / (c[-1] + 1e-9)
    hl_ratio_ma5_v = np.array([(h[i] - l[i]) / (c[i] + 1e-9) for i in range(-5, 0)]).mean()

    features = {
        "ret_1d": ret_1d,
        "ret_5d": ret_5d,
        "ret_10d": ret_10d,
        "ma_5_bias": ma5_bias,
        "ma_20_bias": ma20_bias,
        "volatility_5d": volatility_5d,
        "volatility_20d": volatility_20d,
        "volume_ratio": volume_ratio,
        "macd": macd_val,
        "macd_signal": signal_val,
        "macd_hist": macd_hist,
        "rsi": rsi,
        "hl_ratio": hl_ratio,
        "hl_ratio_ma5": hl_ratio_ma5_v,
    }
    return features


def ml_predict(stock_code: str, closes: list[float], highs: list[float] | None = None,
               lows: list[float] | None = None, volumes: list[float] | None = None) -> PredictResult | None:
    """使用 LightGBM 模型预测。返回 None 表示模型不可用。"""
    model_data = _load_model()
    if model_data is None:
        return None

    feats = _compute_features(closes, highs, lows, volumes)
    if feats is None:
        return None

    model = model_data["model"]
    feature_cols = model_data["feature_cols"]

    X = np.array([[feats.get(c, 0.0) for c in feature_cols]], dtype=np.float64)
    prob = float(model.predict_proba(X)[0, 1])

    importances = dict(zip(feature_cols, model.feature_importances_))
    top = sorted(
        [{"factor": k, "weight": float(importances.get(k, 0))} for k in feats],
        key=lambda x: abs(x["weight"]), reverse=True,
    )[:5]

    label = "up" if prob >= 0.5 else "down"
    confidence = abs(prob - 0.5) * 2

    return PredictResult(
        stock_code=stock_code,
        predict_date="",
        target_date="",
        predicted_prob=round(prob, 4),
        predicted_label=label,
        confidence=round(confidence, 4),
        top_factors=top,
        model_version=f"lgbm-auc{model_data['auc']:.3f}",
    )
