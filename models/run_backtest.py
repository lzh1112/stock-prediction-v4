#!/usr/bin/env python3
"""
历史回测模拟

在历史数据上模拟影子模式:
- 对过去 N 天，每天预测 50 只股票的截面排名
- 3天后检查预测是否正确（预测为"赢家"的股票是否确实跑赢中位数）
- 计算滚动胜率并写入 DB 供前端展示
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import numpy as np
import pandas as pd
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session
from tqdm import tqdm

from app.core.config import settings
from app.models import Stock, DailyPrice, DailyShadow


def load_price_data() -> dict[str, pd.DataFrame]:
    """加载所有股票的K线数据，返回 {code: DataFrame}"""
    engine = create_engine(settings.DATABASE_URL_SYNC)
    query = """
    SELECT s.code, dp.trade_date, dp.open, dp.high, dp.low, dp.close, dp.volume
    FROM daily_prices dp JOIN stocks s ON dp.stock_id = s.id
    ORDER BY s.code, dp.trade_date
    """
    df = pd.read_sql(query, engine, parse_dates=["trade_date"])
    engine.dispose()

    data = {}
    for code, group in df.groupby("code"):
        group = group.sort_values("trade_date").set_index("trade_date")
        data[code] = group
    return data


def compute_features_at_date(prices_df: pd.DataFrame, target_date: date) -> dict | None:
    """计算截至 target_date 的特征（仅用该日期及之前的数据）。"""
    df = prices_df[prices_df.index <= pd.Timestamp(target_date)]
    if len(df) < 40:
        return None

    c = df["close"].values
    h = df["high"].values
    l = df["low"].values
    v = df["volume"].values.astype(float)
    n = len(c)

    ret_1d = (c[-1] / c[-2] - 1) if n >= 2 else 0.0
    ret_5d = (c[-1] / c[-6] - 1) if n >= 6 else 0.0
    ret_10d = (c[-1] / c[-11] - 1) if n >= 11 else 0.0

    ma5 = c[-5:].mean()
    ma20 = c[-20:].mean()
    ma5_bias = (c[-1] - ma5) / ma5
    ma20_bias = (c[-1] - ma20) / ma20

    rets = np.diff(c[-21:]) / c[-21:-1]
    vol_5d = float(rets[-5:].std()) if len(rets) >= 5 else 0.0
    vol_20d = float(rets.std()) if len(rets) > 0 else 0.0

    vol_ma5 = v[-6:-1].mean()
    vol_ratio = float(v[-1] / vol_ma5) if vol_ma5 > 0 else 1.0

    ema12 = c[-12]
    ema26 = c[-26]
    for p in c[-11:]:
        ema12 = p * (2/13) + ema12 * (1 - 2/13)
    for p in c[-25:]:
        ema26 = p * (2/27) + ema26 * (1 - 2/27)
    macd = ema12 - ema26
    signal = macd * (2/10)
    hist = macd - signal

    delta = np.diff(c[-15:])
    gain = np.maximum(delta, 0).mean()
    loss = np.maximum(-delta, 0).mean()
    rs = gain / (loss + 1e-9)
    rsi = float(100.0 - (100.0 / (1.0 + rs)))

    hl_ratio = float((h[-1] - l[-1]) / (c[-1] + 1e-9))
    hl_ratio_ma5 = float(np.array([(h[i] - l[i]) / (c[i] + 1e-9) for i in range(-5, 0)]).mean())

    return {
        "ret_1d": float(ret_1d),
        "ret_5d": float(ret_5d),
        "ret_10d": float(ret_10d),
        "ma_5_bias": float(ma5_bias),
        "ma_20_bias": float(ma20_bias),
        "volatility_5d": vol_5d,
        "volatility_20d": vol_20d,
        "volume_ratio": vol_ratio,
        "macd": float(macd),
        "macd_signal": float(signal),
        "macd_hist": float(hist),
        "rsi": rsi,
        "hl_ratio": hl_ratio,
        "hl_ratio_ma5": hl_ratio_ma5,
    }


def run_backtest(days: int = 90, horizon: int = 3) -> list[dict]:
    """
    对过去 N 个交易日进行回测。
    horizon: 预测未来几天（默认3天）
    """
    import pickle

    model_path = Path(__file__).resolve().parent / "lgbm_model.pkl"
    with open(model_path, "rb") as f:
        model_data = pickle.load(f)

    model = model_data["model"]
    feature_cols = model_data["feature_cols"]

    print(f"Loading price data...")
    price_data = load_price_data()
    print(f"Loaded {len(price_data)} stocks")

    # 生成回测日期列表
    all_dates = sorted(set().union(*[set(df.index) for df in price_data.values()]))
    end_date = all_dates[-1] - timedelta(days=horizon + 1)
    if isinstance(end_date, pd.Timestamp):
        end_date = end_date.date()
    start_date = end_date - timedelta(days=days)
    if isinstance(start_date, pd.Timestamp):
        start_date = start_date.date()

    backtest_dates = [d for d in all_dates if start_date <= (d.date() if hasattr(d, 'date') else d) <= end_date]
    print(f"Backtesting {len(backtest_dates)} trading days ({start_date} to {end_date})")

    engine = create_engine(settings.DATABASE_URL_SYNC)

    results = []
    for bt_date in tqdm(backtest_dates[-days:], desc="Backtesting"):
        if isinstance(bt_date, pd.Timestamp):
            bt_date = bt_date.date()

        # Compute features and predictions for all stocks
        batch = []
        for code, df in price_data.items():
            feats = compute_features_at_date(df, bt_date)
            if feats is None:
                continue
            X = np.array([[feats.get(c, 0.0) for c in feature_cols]], dtype=np.float64)
            prob = float(model.predict_proba(X)[0, 1])

            # Get actual return 3 days later
            target_date = bt_date + timedelta(days=horizon)
            df_target = df[df.index >= pd.Timestamp(target_date)]
            if len(df_target) == 0:
                continue

            future_price = df_target.iloc[0]["close"]
            current_price = df[df.index <= pd.Timestamp(bt_date)].iloc[-1]["close"]
            actual_ret = (future_price / current_price) - 1

            batch.append({
                "code": code,
                "predict_date": bt_date,
                "target_date": target_date,
                "prob": prob,
                "current_close": current_price,
                "future_close": future_price,
                "actual_ret": actual_ret,
            })

        if len(batch) < 10:
            continue

        # Cross-sectional ranking: top 30% by prob are predicted "up"
        probs = [b["prob"] for b in batch]
        threshold = np.quantile(probs, 0.7)
        actual_rets = [b["actual_ret"] for b in batch]
        median_ret = np.median(actual_rets)

        for b in batch:
            predicted_label = "up" if b["prob"] >= threshold else "down"
            is_correct = (predicted_label == "up" and b["actual_ret"] > median_ret) or \
                         (predicted_label == "down" and b["actual_ret"] <= median_ret)

            with Session(engine) as session:
                stock = session.execute(select(Stock).where(Stock.code == b["code"])).scalar_one_or_none()
                if stock is None:
                    continue

                # Check if record exists
                existing = session.execute(
                    select(DailyShadow).where(
                        DailyShadow.stock_id == stock.id,
                        DailyShadow.predict_date == b["predict_date"],
                    )
                ).scalar_one_or_none()

                if existing is None:
                    shadow = DailyShadow(
                        stock_id=stock.id,
                        predict_date=b["predict_date"],
                        target_date=b["target_date"],
                        predicted_prob=round(b["prob"], 4),
                        predicted_label=predicted_label,
                        confidence=round(abs(b["prob"] - 0.5) * 2, 4),
                        top_factors=[],
                        actual_close=round(b["future_close"], 2),
                        is_correct=is_correct,
                        model_version=f"lgbm-auc{model_data['auc']:.3f}",
                    )
                    session.add(shadow)
                else:
                    existing.actual_close = round(b["future_close"], 2)
                    existing.is_correct = is_correct
                    existing.predicted_label = predicted_label

                session.commit()

            results.append({
                "date": b["predict_date"],
                "code": b["code"],
                "prob": b["prob"],
                "predicted_label": predicted_label,
                "is_correct": is_correct,
                "actual_ret": round(b["actual_ret"], 4),
            })

    engine.dispose()

    # Summary
    total = len(results)
    correct = sum(1 for r in results if r["is_correct"])
    win_rate = correct / total if total > 0 else 0
    print(f"\nBacktest complete: {total} predictions, {correct} correct, win_rate={win_rate:.2%}")

    # Daily win rates
    daily = {}
    for r in results:
        d = r["date"]
        daily.setdefault(d, {"total": 0, "correct": 0})
        daily[d]["total"] += 1
        daily[d]["correct"] += int(r["is_correct"])

    for d in sorted(daily):
        wr = daily[d]["correct"] / daily[d]["total"] if daily[d]["total"] > 0 else 0
        print(f"  {d}: {daily[d]['correct']}/{daily[d]['total']} = {wr:.1%}")

    return results


if __name__ == "__main__":
    results = run_backtest(days=60)
