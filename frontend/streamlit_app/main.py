"""
多模态新闻驱动型股价预测系统 V4.0 — Streamlit 原型看板
"""

from __future__ import annotations

import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

API_BASE = "http://localhost:8000/api/v1"

st.set_page_config(
    page_title="股价预测系统 V4.0",
    page_icon="📈",
    layout="wide",
)

# --- 缓存 API 调用 ---


@st.cache_data(ttl=300)
def search_stocks(keyword: str) -> list[dict]:
    try:
        r = requests.get(f"{API_BASE}/stocks", params={"keyword": keyword, "page_size": 50}, timeout=10)
        return r.json().get("items", [])
    except Exception:
        return []


@st.cache_data(ttl=30)
def get_shadow_stats() -> dict:
    try:
        r = requests.get(f"{API_BASE}/admin/shadow-stats", timeout=5)
        return r.json()
    except Exception:
        return {"total_predictions": 0, "correct": 0, "win_rate": 0}

@st.cache_data(ttl=60)
def get_stock_detail(code: str) -> dict:
    try:
        r = requests.get(f"{API_BASE}/stocks/{code}", timeout=15)
        return r.json()
    except Exception:
        return {"code": code, "name": "", "prices": []}


@st.cache_data(ttl=120)
def get_news(stock_code: str, page_size: int = 20) -> list[dict]:
    try:
        r = requests.get(f"{API_BASE}/news", params={"stock_code": stock_code, "page_size": page_size}, timeout=10)
        return r.json().get("items", [])
    except Exception:
        return []


def call_predict(stock_code: str) -> dict | None:
    try:
        r = requests.post(f"{API_BASE}/predict", json={"stock_code": stock_code}, timeout=10)
        return r.json()
    except Exception:
        return None


# --- 侧边栏 ---

st.sidebar.title("📊 股价预测系统 V4.0")
st.sidebar.caption("原型机 · 技术指标规则基预测")

search_kw = st.sidebar.text_input("🔍 搜索股票", placeholder="代码或名称，如 600519 或 茅台")

stocks = search_stocks(search_kw) if search_kw else []

if stocks:
    code = st.sidebar.selectbox(
        "匹配结果",
        options=[s["code"] for s in stocks],
        format_func=lambda c: f"{c} — {next((s['name'] for s in stocks if s['code'] == c), '')}",
    )
else:
    code = None

# --- 主区域 ---

tab1, tab2, tab3 = st.tabs(["📈 K线 & 预测", "📰 新闻分析", "📋 系统信息"])

with tab1:
    if code:
        detail = get_stock_detail(code)
        prices = detail.get("prices", [])

        st.header(f"{code} — {detail.get('name', '')}")

        if prices:
            # --- K线图 ---
            dates = [p["date"] for p in prices]
            opens = [p["open"] for p in prices]
            highs = [p["high"] for p in prices]
            lows = [p["low"] for p in prices]
            closes = [p["close"] for p in prices]
            volumes = [p["volume"] for p in prices]

            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.7, 0.3],
            )

            fig.add_trace(
                go.Candlestick(
                    x=dates, open=opens, high=highs, low=lows, close=closes,
                    name="K线",
                    increasing=dict(line=dict(color="#ef4444"), fillcolor="#ef4444"),
                    decreasing=dict(line=dict(color="#22c55e"), fillcolor="#22c55e"),
                ),
                row=1, col=1,
            )

            # 均线
            if len(closes) >= 5:
                ma5 = [sum(closes[max(0, i - 4): i + 1]) / min(i + 1, 5) for i in range(len(closes))]
                fig.add_trace(go.Scatter(x=dates, y=ma5, mode="lines", name="MA5",
                                         line=dict(color="#f59e0b", width=1)), row=1, col=1)
            if len(closes) >= 20:
                ma20 = [sum(closes[max(0, i - 19): i + 1]) / min(i + 1, 20) for i in range(len(closes))]
                fig.add_trace(go.Scatter(x=dates, y=ma20, mode="lines", name="MA20",
                                         line=dict(color="#3b82f6", width=1)), row=1, col=1)

            # 成交量
            colors = ["#ef4444" if closes[i] >= opens[i] else "#22c55e" for i in range(len(closes))]
            fig.add_trace(go.Bar(x=dates, y=volumes, name="成交量", marker=dict(color=colors),
                                 opacity=0.3), row=2, col=1)

            fig.update_layout(
                height=600,
                xaxis=dict(rangeslider=dict(visible=False)),
                margin=dict(l=0, r=0, t=0, b=0),
                legend=dict(orientation="h", y=1.12),
                template="plotly_dark",
            )
            fig.update_xaxes(title_text="", row=2, col=1)
            fig.update_yaxes(title_text="价格", row=1, col=1)
            fig.update_yaxes(title_text="成交量", row=2, col=1)

            st.plotly_chart(fig, use_container_width=True)

            # --- 预测区域 ---
            st.divider()
            st.subheader("🎯 技术指标预测")

            if st.button("生成预测", type="primary"):
                with st.spinner("计算中..."):
                    result = call_predict(code)

                if result:
                    prob = result["predicted_prob"]
                    label = "📈 上涨" if result["predicted_label"] == "up" else "📉 下跌"
                    color = "#ef4444" if result["predicted_label"] == "up" else "#22c55e"

                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("预测方向", label, delta=f"{prob:.1%}")
                    with col_b:
                        st.metric("置信度", f"{result['confidence']:.1%}")
                    with col_c:
                        st.metric("模型版本", result["model_version"])

                    st.caption(f"预测日期: {result['predict_date']} → 目标日期: {result['target_date']}")

                    if result["top_factors"]:
                        st.write("**关键因子**")
                        for f in result["top_factors"]:
                            sign = "+" if f["weight"] > 0 else ""
                            st.text(f"  {sign}{f['weight']:.0%}  {f['factor']}")
                else:
                    st.error("预测服务不可用，请启动后端: `uvicorn app.main:app --port 8000`")
        else:
            st.info("暂无K线数据，点击「管理 → 初始化数据」获取数据", icon="ℹ️")
    else:
        st.info("👈 在左侧搜索股票代码或名称", icon="ℹ️")

with tab2:
    if code:
        st.header(f"📰 {code} 新闻分析")
        news_list = get_news(code)
        if news_list:
            for n in news_list:
                sent = n.get("sentiment")
                emoji = ""
                if sent and sent.get("sentiment_score"):
                    emoji = "🟢" if sent["sentiment_score"] > 0 else "🔴" if sent["sentiment_score"] < 0 else "⚪"

                with st.expander(f"{emoji} {n['title'][:80]}", expanded=False):
                    st.caption(f"来源: {n.get('source', '')} | {n.get('publish_time', '')}")
                    if sent:
                        st.json(sent)
        else:
            st.info("暂无新闻数据，LLM 情感分析将在阶段 2 实现", icon="ℹ️")
    else:
        st.info("👈 请先选择一只股票", icon="ℹ️")

with tab3:
    st.header("⚙️ 系统信息")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("服务端点")
        st.code(f"""后端 API:    {API_BASE}
Swagger 文档: http://localhost:8000/docs
健康检查:     http://localhost:8000/health""")

    with col2:
        st.subheader("数据统计")
        try:
            r = requests.get(f"{API_BASE}/stocks", params={"page_size": 1}, timeout=5)
            total = r.json().get("total", 0)
            st.metric("已录入股票数", total)
        except Exception:
            st.metric("已录入股票数", "N/A")

        shadow = get_shadow_stats()
        st.metric("影子胜率 (30日)", f"{shadow.get('win_rate', 0):.1%}")
        st.metric("总预测次数", shadow.get("total_predictions", 0))

    st.divider()

    st.subheader("🔧 管理操作")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 初始化数据 (50只沪深300)"):
            with st.spinner("正在从 akshare 抓取数据，预计2-3分钟..."):
                try:
                    r = requests.post(f"{API_BASE}/admin/seed-data", timeout=600)
                    data = r.json()
                    st.success(f"完成! 写入 {data['total_records']} 条K线记录")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"失败: {e}")

    with col_b:
        if st.button("🧹 清除缓存"):
            st.cache_data.clear()
            st.success("缓存已清除")
