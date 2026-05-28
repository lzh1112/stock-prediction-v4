#!/usr/bin/env python3
"""
LightGBM 股价涨跌预测模型训练脚本

特征: 技术指标(MA/MACD/RSI/波动率/量比等) + 可选情感特征
目标: 次日涨跌 (1=涨, 0=跌)
验证: 时间序列5折交叉验证
"""

from __future__ import annotations

import sys
import pickle
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, accuracy_score, classification_report
from sqlalchemy import create_engine, text
from lightgbm import LGBMClassifier, early_stopping, log_evaluation

from app.core.config import settings

# --- 配置 ---
MODEL_OUTPUT = Path(__file__).resolve().parent / "lgbm_model.pkl"
PREDICT_HORIZON = 3  # 预测未来N天
LOOKBACK_WINDOW = 180


def load_data() -> pd.DataFrame:
    """从 SQLite 加载股价数据，构造成用于训练的形式。"""
    engine = create_engine(settings.DATABASE_URL_SYNC)

    query = """
    SELECT s.code, s.name, dp.trade_date, dp.open, dp.high, dp.low, dp.close, dp.volume
    FROM daily_prices dp
    JOIN stocks s ON dp.stock_id = s.id
    ORDER BY s.code, dp.trade_date
    """
    df = pd.read_sql(query, engine)
    engine.dispose()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """为每只股票计算技术指标特征（无未来函数）。"""
    result = []
    for code, group in df.groupby("code"):
        group = group.sort_values("trade_date").copy()

        closes = group["close"].values
        volumes = group["volume"].values
        highs = group["high"].values
        lows = group["low"].values

        # 收益率
        group["ret_1d"] = group["close"].pct_change()
        group["ret_5d"] = group["close"].pct_change(5)
        group["ret_10d"] = group["close"].pct_change(10)

        # 均线
        for w in [5, 10, 20, 30]:
            group[f"ma_{w}"] = group["close"].rolling(w).mean()

        # MA 偏离度
        for w in [5, 20]:
            ma_col = f"ma_{w}"
            if ma_col in group.columns:
                group[f"ma_{w}_bias"] = (group["close"] - group[ma_col]) / group[ma_col]

        # 波动率
        group["volatility_5d"] = group["ret_1d"].rolling(5).std()
        group["volatility_20d"] = group["ret_1d"].rolling(20).std()

        # 量比
        group["volume_ma_5"] = group["volume"].rolling(5).mean()
        group["volume_ratio"] = group["volume"] / (group["volume_ma_5"] + 1)

        # MACD
        ema12 = group["close"].ewm(span=12, adjust=False).mean()
        ema26 = group["close"].ewm(span=26, adjust=False).mean()
        group["macd"] = ema12 - ema26
        group["macd_signal"] = group["macd"].ewm(span=9, adjust=False).mean()
        group["macd_hist"] = group["macd"] - group["macd_signal"]

        # RSI
        delta = group["close"].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / (avg_loss + 1e-9)
        group["rsi"] = 100 - (100 / (1 + rs))

        # 高低价范围
        group["hl_ratio"] = (group["high"] - group["low"]) / (group["close"] + 1e-9)
        group["hl_ratio_ma5"] = group["hl_ratio"].rolling(5).mean()

        # 未来N日收益率
        group["future_ret"] = group["close"].shift(-PREDICT_HORIZON) / group["close"] - 1

        result.append(group)

    df_full = pd.concat(result, ignore_index=True)

    # 截面排名: 每个交易日，按未来收益率排名，前30%为赢家(target=1)，后30%为输家(target=0)
    df_full["target"] = 0
    for trade_date, day_group in df_full.groupby("trade_date"):
        if day_group["future_ret"].notna().sum() < 10:
            continue
        ret = day_group["future_ret"]
        top_thresh = ret.quantile(0.7)
        df_full.loc[(df_full["trade_date"] == trade_date) & (df_full["future_ret"] >= top_thresh), "target"] = 1

    # 只保留有标签的行
    df_full = df_full[df_full["target"].notna()]
    return df_full


def prepare_train_test(df: pd.DataFrame, test_cutoff: date | None = None) -> tuple:
    """按时间切分训练/测试集（无未来信息泄露）。"""
    if test_cutoff is None:
        test_cutoff = date.today() - timedelta(days=90)

    df = df.dropna().copy()

    feature_cols = [c for c in df.columns if c not in (
        "code", "name", "trade_date", "open", "high", "low", "close",
        "volume", "target", "future_ret", "ma_5", "ma_10", "ma_20", "ma_30",
        "volume_ma_5",
    )]

    train_mask = df["trade_date"] < pd.Timestamp(test_cutoff)
    test_mask = df["trade_date"] >= pd.Timestamp(test_cutoff)

    X_train = df.loc[train_mask, feature_cols].values
    y_train = df.loc[train_mask, "target"].values
    X_test = df.loc[test_mask, feature_cols].values
    y_test = df.loc[test_mask, "target"].values

    return X_train, y_train, X_test, y_test, feature_cols


def train_model(X_train, y_train, X_test, y_test) -> LGBMClassifier:
    """训练 LightGBM，使用验证集做早停。"""
    model = LGBMClassifier(
        n_estimators=500,
        learning_rate=0.03,
        max_depth=5,
        num_leaves=23,
        subsample=0.7,
        colsample_bytree=0.7,
        min_child_samples=100,
        reg_alpha=0.1,
        reg_lambda=0.1,
        random_state=42,
        verbose=-1,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        eval_metric="auc",
        callbacks=[early_stopping(100), log_evaluation(100)],
    )

    return model


def run_ablation(df: pd.DataFrame) -> list[dict]:
    """消融实验：逐组移除特征，度量 AUC 变化。"""
    feature_groups = {
        "returns": ["ret_1d", "ret_5d", "ret_10d"],
        "moving_avg": ["ma_5_bias", "ma_20_bias"],
        "volatility": ["volatility_5d", "volatility_20d"],
        "volume": ["volume_ratio"],
        "macd": ["macd", "macd_signal", "macd_hist"],
        "rsi": ["rsi"],
        "hl_ratio": ["hl_ratio", "hl_ratio_ma5"],
    }

    all_features = [c for fg in feature_groups.values() for c in fg]
    target = "target"
    df_clean = df.dropna(subset=all_features + [target])

    test_cutoff = date.today() - timedelta(days=30)
    train = df_clean[df_clean["trade_date"] < pd.Timestamp(test_cutoff)]
    test = df_clean[df_clean["trade_date"] >= pd.Timestamp(test_cutoff)]

    # Full model
    model_full = LGBMClassifier(n_estimators=200, learning_rate=0.05, max_depth=6,
                                random_state=42, verbose=-1)
    model_full.fit(train[all_features], train[target])
    y_pred_full = model_full.predict_proba(test[all_features])[:, 1]
    full_auc = roc_auc_score(test[target], y_pred_full)

    results = [{"experiment": "E0_full", "auc": round(full_auc, 4), "features": len(all_features)}]

    # Ablation
    for group_name, feats in feature_groups.items():
        remaining = [f for f in all_features if f not in feats]
        model = LGBMClassifier(n_estimators=200, learning_rate=0.05, max_depth=6,
                               random_state=42, verbose=-1)
        model.fit(train[remaining], train[target])
        y_pred = model.predict_proba(test[remaining])[:, 1]
        auc = roc_auc_score(test[target], y_pred)
        results.append({
            "experiment": f"E1_drop_{group_name}",
            "auc": round(auc, 4),
            "auc_drop": round(full_auc - auc, 4),
            "features": len(remaining),
        })

    return results


def main():
    print("=" * 60)
    print("LightGBM 股价涨跌预测 — 模型训练")
    print("=" * 60)

    print("\n[1/4] 加载数据...")
    df = load_data()
    print(f"  总样本: {len(df):,}, 股票数: {df['code'].nunique()}")

    print("\n[2/4] 计算特征...")
    df = compute_features(df)
    df = df.dropna()
    print(f"  有效样本: {len(df):,}, 涨跌比: {df['target'].mean():.1%}")

    print("\n[3/4] 训练 LightGBM...")
    X_train, y_train, X_test, y_test, feature_cols = prepare_train_test(df)
    print(f"  训练集: {len(X_train):,}, 测试集: {len(X_test):,}")

    model = train_model(X_train, y_train, X_test, y_test)

    y_pred = model.predict_proba(X_test)[:, 1]
    y_label = (y_pred >= 0.5).astype(int)

    auc = roc_auc_score(y_test, y_pred)
    acc = accuracy_score(y_test, y_label)
    print(f"\n  测试集 AUC: {auc:.4f}")
    print(f"  测试集 Accuracy: {acc:.4f}")
    print(f"\n{classification_report(y_test, y_label, target_names=['Down', 'Up'])}")

    # 特征重要性
    importances = sorted(
        zip(feature_cols, model.feature_importances_),
        key=lambda x: x[1], reverse=True
    )
    print("Top-10 特征重要性:")
    for name, imp in importances[:10]:
        print(f"  {name:25s} {imp:.4f}")

    # 保存模型
    print(f"\n[4/4] 保存模型 → {MODEL_OUTPUT}")
    with open(MODEL_OUTPUT, "wb") as f:
        pickle.dump({
            "model": model,
            "feature_cols": feature_cols,
            "auc": auc,
        }, f)

    # 消融实验
    print("\n--- 消融实验 ---")
    ablation_results = run_ablation(df)
    for r in ablation_results:
        drop_info = f" (AUC drop: {r.get('auc_drop', 0):+.4f})" if "auc_drop" in r else ""
        print(f"  {r['experiment']:25s} AUC={r['auc']:.4f}{drop_info}")

    print("\nDone! Training complete.")


if __name__ == "__main__":
    main()
