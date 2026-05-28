"""
多模态新闻驱动型股价预测系统 V4.0 — Streamlit 看板
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

API_BASE = "http://localhost:8000/api/v1"

st.set_page_config(page_title="股价预测系统 V4.0", page_icon="📈", layout="wide")

# --- 缓存 ---

@st.cache_data(ttl=60)
def get_market_overview(industry: str | None = None, exchange: str | None = None):
    params = {}
    if industry:
        params["industry"] = industry
    if exchange:
        params["exchange"] = exchange
    try:
        r = requests.get(f"{API_BASE}/market/overview", params=params, timeout=15)
        return r.json()
    except Exception:
        return {"items": [], "by_industry": {}, "summary": {}, "industries": []}

@st.cache_data(ttl=300)
def search_stocks(keyword: str) -> list[dict]:
    try:
        r = requests.get(f"{API_BASE}/stocks", params={"keyword": keyword, "page_size": 50}, timeout=10)
        return r.json().get("items", [])
    except Exception:
        return []

@st.cache_data(ttl=30)
def get_shadow_stats():
    try:
        r = requests.get(f"{API_BASE}/admin/shadow-stats?days=90", timeout=5)
        return r.json()
    except Exception:
        return {"win_rate": 0, "total_predictions": 0}

@st.cache_data(ttl=30)
def get_backtest_daily():
    try:
        r = requests.get(f"{API_BASE}/admin/shadow-daily?days=120", timeout=10)
        return r.json()
    except Exception:
        return {"daily": [], "overall_win_rate": 0}

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


# ===================== 侧边栏 =====================

st.sidebar.title("📊 股价预测 V4.0")
page = st.sidebar.radio("导航", ["🏠 市场总览", "🔍 个股详情", "📊 回测曲线", "📰 新闻分析", "⚙️ 系统"])


# ===================== 市场总览 =====================

if page == "🏠 市场总览":
    st.title("🏠 市场总览")

    data = get_market_overview()
    items = data.get("items", [])
    industries = data.get("industries", [])
    summary = data.get("summary", {})

    if not items:
        st.warning("暂无行情数据")
        st.stop()

    # 顶部概览
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("股票数", summary.get("total", 0))
    with c2:
        st.metric("上涨", summary.get("up", 0), delta=f"{summary.get('up_ratio', 0):.0%}")
    with c3:
        st.metric("下跌", summary.get("down", 0))
    with c4:
        shadow = get_shadow_stats()
        st.metric("回测胜率", f"{shadow.get('win_rate', 0):.1%}")

    # 筛选器
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_industry = st.selectbox("按行业筛选", ["全部"] + industries, key="industry_filter")
    with col_f2:
        exchange_filter = st.selectbox("按交易所", ["全部", "SH (上海)", "SZ (深圳)"], key="exchange_filter")

    # 应用筛选
    industry_arg = None if selected_industry == "全部" else selected_industry
    exchange_arg = None
    if exchange_filter == "SH (上海)":
        exchange_arg = "SH"
    elif exchange_filter == "SZ (深圳)":
        exchange_arg = "SZ"

    if industry_arg or exchange_arg:
        data = get_market_overview(industry=industry_arg, exchange=exchange_arg)
        items = data.get("items", [])

    # 表格
    df = pd.DataFrame(items)
    if not df.empty:
        # 涨跌颜色
        def color_change(val):
            if val > 0:
                return f'color: #ef4444; font-weight: bold'
            elif val < 0:
                return f'color: #22c55e; font-weight: bold'
            return 'color: #9ca3af'

        def color_sentiment(val):
            if val and val > 0.05:
                return '🟢'
            elif val and val < -0.05:
                return '🔴'
            return '⚪'

        display_df = df[["code", "name", "industry", "close", "change_pct", "volume", "sentiment"]].copy()
        display_df["sentiment"] = display_df["sentiment"].apply(color_sentiment)
        display_df["change_pct"] = display_df["change_pct"].apply(lambda x: f"{x:+.2f}%")
        display_df["volume"] = (display_df["volume"] / 10000).apply(lambda x: f"{x:.0f}万")
        display_df.columns = ["代码", "名称", "行业", "最新价", "涨跌幅", "成交量(万)", "情感"]

        # 行业色彩标记
        st.dataframe(
            display_df,
            use_container_width=True,
            height=600,
            hide_index=True,
            column_config={
                "涨跌幅": st.column_config.TextColumn(),
                "最新价": st.column_config.NumberColumn(format="%.2f"),
            },
        )

        # 统计每个行业的涨跌比
        st.divider()
        st.subheader("📊 行业涨跌分布")
        by_ind = data.get("by_industry", {})
        chart_data = []
        for ind, stocks in by_ind.items():
            up = sum(1 for s in stocks if s["change_pct"] > 0)
            down = sum(1 for s in stocks if s["change_pct"] < 0)
            chart_data.append({"行业": ind, "上涨": up, "下跌": down, "上涨比": round(up / len(stocks) * 100, 1) if stocks else 0})

        chart_df = pd.DataFrame(chart_data).sort_values("上涨比", ascending=False)

        fig = go.Figure()
        fig.add_trace(go.Bar(name="上涨", y=chart_df["行业"], x=chart_df["上涨"],
                             orientation="h", marker_color="#ef4444"))
        fig.add_trace(go.Bar(name="下跌", y=chart_df["行业"], x=chart_df["下跌"],
                             orientation="h", marker_color="#22c55e"))
        fig.update_layout(barmode="group", height=500, margin=dict(l=0, r=0, t=0, b=0),
                          template="plotly_dark", xaxis_title="股票数")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("无匹配结果")


# ===================== 个股详情 =====================

elif page == "🔍 个股详情":
    st.title("🔍 个股详情")

    search_kw = st.text_input("搜索股票", placeholder="代码或名称，如 600519 或 茅台")
    stocks = search_stocks(search_kw) if search_kw else []

    if stocks:
        code = st.selectbox(
            "选择股票",
            options=[s["code"] for s in stocks],
            format_func=lambda c: f"{c} — {next((s['name'] for s in stocks if s['code'] == c), '')}",
        )
    else:
        code = st.selectbox("选择股票", options=["600519.SH", "000001.SZ", "300750.SZ", "601318.SH"],
                            format_func=lambda c: f"{c} — 热门")

    if code:
        detail = get_stock_detail(code)
        prices = detail.get("prices", [])
        st.header(f"{code} — {detail.get('name', '')}")

        if prices:
            dates = [p["date"] for p in prices]
            opens = [p["open"] for p in prices]
            highs = [p["high"] for p in prices]
            lows = [p["low"] for p in prices]
            closes = [p["close"] for p in prices]
            volumes = [p["volume"] for p in prices]

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])

            fig.add_trace(go.Candlestick(
                x=dates, open=opens, high=highs, low=lows, close=closes, name="K线",
                increasing=dict(line=dict(color="#ef4444"), fillcolor="#ef4444"),
                decreasing=dict(line=dict(color="#22c55e"), fillcolor="#22c55e"),
            ), row=1, col=1)

            if len(closes) >= 5:
                ma5 = [sum(closes[max(0, i - 4): i + 1]) / min(i + 1, 5) for i in range(len(closes))]
                fig.add_trace(go.Scatter(x=dates, y=ma5, mode="lines", name="MA5",
                                         line=dict(color="#f59e0b", width=1)), row=1, col=1)
            if len(closes) >= 20:
                ma20 = [sum(closes[max(0, i - 19): i + 1]) / min(i + 1, 20) for i in range(len(closes))]
                fig.add_trace(go.Scatter(x=dates, y=ma20, mode="lines", name="MA20",
                                         line=dict(color="#3b82f6", width=1)), row=1, col=1)

            colors = ["#ef4444" if closes[i] >= opens[i] else "#22c55e" for i in range(len(closes))]
            fig.add_trace(go.Bar(x=dates, y=volumes, name="成交量", marker=dict(color=colors), opacity=0.3), row=2, col=1)

            fig.update_layout(height=500, xaxis=dict(rangeslider=dict(visible=False)),
                              margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", y=1.12),
                              template="plotly_dark")
            fig.update_yaxes(title_text="价格", row=1, col=1)
            fig.update_yaxes(title_text="成交量", row=2, col=1)

            st.plotly_chart(fig, use_container_width=True)

            # 预测
            st.divider()
            col_pred, col_info = st.columns([1, 2])
            with col_pred:
                st.subheader("🎯 模型预测")
                if st.button("生成预测", type="primary"):
                    with st.spinner("计算中..."):
                        result = call_predict(code)
                    if result:
                        label = "📈 上涨" if result["predicted_label"] == "up" else "📉 下跌"
                        st.metric("方向", label)
                        st.metric("概率", f"{result['predicted_prob']:.1%}")
                        st.metric("置信度", f"{result['confidence']:.1%}")
                        st.caption(f"模型: {result['model_version']}")
                        st.caption(f"目标日: {result['target_date']}")
            with col_info:
                if prices:
                    st.subheader("📋 最新行情")
                    latest = prices[-1]
                    prev = prices[-2] if len(prices) > 1 else latest
                    chg = (latest["close"] - prev["close"]) / prev["close"] * 100
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("收盘", f"{latest['close']:.2f}", delta=f"{chg:+.2f}%")
                    with c2:
                        st.metric("最高", f"{latest['high']:.2f}")
                    with c3:
                        st.metric("最低", f"{latest['low']:.2f}")
                    with c4:
                        st.metric("成交量", f"{latest['volume']:,}")
        else:
            st.info("暂无K线数据")


# ===================== 回测曲线 =====================

elif page == "📊 回测曲线":
    st.title("📊 回测曲线")

    bt = get_backtest_daily()
    daily_data = bt.get("daily", [])

    if daily_data:
        overall_wr = bt.get("overall_win_rate", 0)
        shadow = get_shadow_stats()
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("回测胜率", f"{overall_wr:.1%}", delta=f"{overall_wr - 0.5:+.1%} vs 随机")
        with c2:
            st.metric("回测天数", len(daily_data))
        with c3:
            st.metric("最新胜率", f"{shadow.get('win_rate', 0):.1%}")

        dates = [d["date"] for d in daily_data]
        daily_wr = [d["win_rate"] for d in daily_data]
        cum_wr = [d["cumulative_win_rate"] for d in daily_data]

        fig = go.Figure()
        fig.add_trace(go.Bar(x=dates, y=daily_wr, name="日胜率", marker=dict(opacity=0.4)))
        fig.add_trace(go.Scatter(x=dates, y=cum_wr, name="累计胜率", line=dict(color="#f59e0b", width=2)))
        fig.add_hline(y=0.5, line_dash="dash", line_color="gray", annotation_text="随机基线")
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0),
                          template="plotly_dark", yaxis=dict(tickformat=".0%"))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"LightGBM 截面排名模型 | 累计胜率 {overall_wr:.1%} | {len(daily_data)} 个交易日")
    else:
        st.info("暂无回测数据。运行: python models/run_backtest.py")


# ===================== 新闻分析 =====================

elif page == "📰 新闻分析":
    st.title("📰 新闻情感分析")

    search_code = st.selectbox("选择股票", options=["600519.SH", "000001.SZ", "300750.SZ", "601318.SH", "000858.SZ"],
                                format_func=lambda c: c)
    if search_code:
        news_list = get_news(search_code, page_size=30)
        if news_list:
            sentiments = [n.get("sentiment", {}).get("sentiment_score", 0) or 0 for n in news_list if n.get("sentiment")]
            if sentiments:
                pos = sum(1 for s in sentiments if s > 0.1)
                neg = sum(1 for s in sentiments if s < -0.1)
                neu = len(sentiments) - pos - neg
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("积极 🟢", pos)
                with c2: st.metric("中性 ⚪", neu)
                with c3: st.metric("消极 🔴", neg)
                st.divider()

            for n in news_list:
                sent = n.get("sentiment")
                if sent and sent.get("sentiment_score") is not None:
                    score = sent["sentiment_score"]
                    emoji = "🟢" if score > 0.1 else ("🔴" if score < -0.1 else "⚪")
                    label = f"{emoji} [{sent.get('event_type', 'N/A')}] {n['title'][:60]}"
                else:
                    label = f"⚫ {n['title'][:60]}"

                with st.expander(label, expanded=False):
                    st.caption(f"来源: {n.get('source', '?')} | {n.get('publish_time', '?')}")
                    if sent:
                        c1, c2, c3, c4 = st.columns(4)
                        with c1: st.metric("情感", f"{sent['sentiment_score']:+.2f}")
                        with c2: st.metric("强度", f"{sent['intensity']:.2f}")
                        with c3: st.metric("相关度", f"{sent['relevance']:.2f}")
                        with c4: st.metric("类型", sent.get("event_type", "N/A"))
        else:
            st.info("暂无新闻数据")


# ===================== 系统信息 =====================

elif page == "⚙️ 系统":
    st.title("⚙️ 系统信息")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("服务端点")
        st.code(f"""后端:  {API_BASE}
文档:  http://localhost:8000/docs
健康:  http://localhost:8000/health""")

    with c2:
        st.subheader("数据统计")
        try:
            r = requests.get(f"{API_BASE}/stocks", params={"page_size": 1}, timeout=5)
            total = r.json().get("total", 0)
            st.metric("股票数", total)
        except Exception:
            st.metric("股票数", "N/A")
        shadow = get_shadow_stats()
        st.metric("回测胜率", f"{shadow.get('win_rate', 0):.1%}")

    st.divider()
    st.subheader("🔧 管理")
    c_a, c_b, c_c = st.columns(3)
    with c_a:
        if st.button("🔄 刷新股价", use_container_width=True):
            with st.spinner("更新中..."):
                r = requests.post(f"{API_BASE}/admin/seed-data", timeout=300)
                st.success(f"完成: {r.json().get('total_records', 0)} 条")
                st.cache_data.clear()
    with c_b:
        if st.button("🔮 今日预测", use_container_width=True):
            with st.spinner("预测中..."):
                r = requests.post(f"{API_BASE}/admin/shadow-run", timeout=60)
                st.success(f"完成: {r.json().get('success', 0)} 只")
    with c_c:
        if st.button("🧹 清除缓存", use_container_width=True):
            st.cache_data.clear()
            st.success("已清除")
