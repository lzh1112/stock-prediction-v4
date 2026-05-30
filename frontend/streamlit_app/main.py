"""
多模态新闻驱动型股价预测系统 V4.0 — Streamlit 看板
Design: "Precision Terminal" — refined dark financial dashboard
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

API_BASE = "http://localhost:8000/api/v1"

# ── Page Config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="StockScope V4.0",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design System CSS ────────────────────────────────────────────
st.markdown("""
<!-- Google Fonts -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">

<style>
/* ================================================================
   PRECISION TERMINAL — Design System
   ================================================================ */

:root {
    --bg-root: #06070c;
    --bg-surface: #0c0e16;
    --bg-card: #11131e;
    --bg-elevated: #161925;
    --bg-input: #0d0f18;
    --border-subtle: #1a1d2b;
    --border-default: #232636;
    --border-active: #2f3345;
    --text-primary: #e4e6ef;
    --text-secondary: #9296ab;
    --text-muted: #5e6278;
    --amber: #f0a500;
    --amber-glow: rgba(240, 165, 0, 0.18);
    --amber-dim: rgba(240, 165, 0, 0.08);
    --blue: #5284ff;
    --blue-glow: rgba(82, 132, 255, 0.18);
    --cyan: #00c2d1;
    --red: #ff5252;
    --red-dim: rgba(255, 82, 82, 0.12);
    --green: #00c897;
    --green-dim: rgba(0, 200, 151, 0.12);
    --purple: #b388ff;
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --font-heading: 'Outfit', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    --font-body: 'Plus Jakarta Sans', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    --font-mono: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace;
}

/* ── Global Reset ─────────────────────────────────── */

.stApp {
    background: var(--bg-root);
}

.stApp > header {
    background: transparent !important;
}

.main > div:first-child {
    padding-top: 0;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(175deg, #080912 0%, #0c0f1d 40%, #0f1324 100%);
    border-right: 1px solid var(--border-subtle);
}

section[data-testid="stSidebar"] > div:first-child {
    background: transparent !important;
    padding-top: 6px;
}

/* Hide Streamlit chrome */
header[data-testid="stHeader"] { display: none !important; }
footer { display: none !important; }
#MainMenu { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }

/* ── Typography ──────────────────────────────────── */

body, .stApp, .stMarkdown, p, span, div {
    font-family: var(--font-body);
    color: var(--text-primary);
}

h1, h2, h3, h4, h5, h6, .stTitle, .stHeading {
    font-family: var(--font-heading) !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em;
    color: var(--text-primary);
}

h1 { font-size: 1.5rem !important; }
h2 { font-size: 1.2rem !important; }
h3 { font-size: 1.05rem !important; }

code, .stCode, pre {
    font-family: var(--font-mono) !important;
}

/* ── Sidebar ─────────────────────────────────────── */

[data-testid="stSidebar"] .stMarkdown {
    font-family: var(--font-body);
}

[data-testid="stSidebar"] h1 {
    font-family: var(--font-heading) !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--amber) !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] > div {
    gap: 2px;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
    padding: 8px 14px !important;
    border-radius: var(--radius-sm) !important;
    font-family: var(--font-body) !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    color: var(--text-secondary) !important;
    transition: all 0.18s ease !important;
    border: 1px solid transparent !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(255,255,255,0.03) !important;
    color: var(--text-primary) !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label[data-selected="true"] {
    background: var(--amber-dim) !important;
    color: var(--amber) !important;
    border-color: rgba(240,165,0,0.25) !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label[data-selected="true"]::before {
    content: '';
    display: inline-block;
    width: 4px;
    height: 4px;
    background: var(--amber);
    border-radius: 50%;
    margin-right: 8px;
    box-shadow: 0 0 6px var(--amber-glow);
}

/* Sidebar divider */
[data-testid="stSidebar"] hr {
    border-color: var(--border-subtle) !important;
    margin: 12px 0 !important;
}

/* ── Buttons ─────────────────────────────────────── */

.stButton > button {
    font-family: var(--font-body) !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border-default) !important;
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    padding: 6px 16px !important;
    transition: all 0.18s ease !important;
    letter-spacing: 0.01em;
}

.stButton > button:hover {
    border-color: var(--border-active) !important;
    background: var(--bg-elevated) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(0,0,0,0.3);
}

.stButton > button[kind="primary"] {
    background: var(--amber) !important;
    border-color: var(--amber) !important;
    color: #0a0b10 !important;
    font-weight: 600 !important;
    box-shadow: 0 0 20px var(--amber-glow);
}

.stButton > button[kind="primary"]:hover {
    background: #f5b020 !important;
    box-shadow: 0 0 30px rgba(240,165,0,0.28);
    transform: translateY(-1px);
}

/* ── Inputs ──────────────────────────────────────── */

.stTextInput > div > div > input,
.stSelectbox > div > div,
.stNumberInput > div > div > input {
    font-family: var(--font-body) !important;
    background: var(--bg-input) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
    transition: border-color 0.18s ease;
}

.stTextInput > div > div > input:focus,
.stSelectbox > div > div:focus-within {
    border-color: var(--amber) !important;
    box-shadow: 0 0 0 2px var(--amber-dim) !important;
}

.stSelectbox [data-baseweb="select"] {
    font-family: var(--font-body) !important;
}

/* ── DataFrames ──────────────────────────────────── */

[data-testid="stDataFrame"] {
    font-family: var(--font-mono) !important;
    font-size: 13px !important;
    border-radius: var(--radius-md) !important;
    overflow: hidden;
    border: 1px solid var(--border-subtle) !important;
}

[data-testid="stDataFrame"] th {
    font-family: var(--font-heading) !important;
    font-weight: 500 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    color: var(--text-muted) !important;
    background: var(--bg-surface) !important;
    border-bottom: 1px solid var(--border-default) !important;
    padding: 10px 14px !important;
}

[data-testid="stDataFrame"] td {
    padding: 8px 14px !important;
    border-bottom: 1px solid rgba(255,255,255,0.02) !important;
}

[data-testid="stDataFrame"] tr:hover td {
    background: rgba(255,255,255,0.015) !important;
}

/* ── Metrics ─────────────────────────────────────── */

[data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    padding: 16px 20px !important;
    transition: all 0.2s ease;
}

[data-testid="stMetric"]:hover {
    border-color: var(--border-default) !important;
    background: var(--bg-elevated) !important;
}

[data-testid="stMetric"] label {
    font-family: var(--font-heading) !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: var(--text-muted) !important;
}

[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-family: var(--font-mono) !important;
    font-size: 1.6rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
}

[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    font-family: var(--font-mono) !important;
    font-size: 0.85rem !important;
}

/* ── Expanders ───────────────────────────────────── */

[data-testid="stExpander"] {
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-sm) !important;
    background: var(--bg-card) !important;
    margin-bottom: 6px !important;
    transition: all 0.15s ease;
}

[data-testid="stExpander"]:hover {
    border-color: var(--border-default) !important;
}

[data-testid="stExpander"] summary {
    font-family: var(--font-body) !important;
    font-size: 0.85rem !important;
    color: var(--text-secondary) !important;
}

/* ── Chat Messages ───────────────────────────────── */

.stChatMessage {
    border-radius: var(--radius-md) !important;
    padding: 12px 16px !important;
}

.stChatMessage[data-testid="stChatMessage"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
}

.stChatInput textarea {
    font-family: var(--font-body) !important;
    background: var(--bg-input) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
}

/* ── Toast / Spinner ─────────────────────────────── */

.stSpinner > div {
    border-top-color: var(--amber) !important;
}

[data-testid="stNotification"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-md) !important;
}

/* ── Tabs ────────────────────────────────────────── */

.stTabs [data-baseweb="tab-list"] {
    gap: 0 !important;
    border-bottom: 1px solid var(--border-subtle) !important;
}

.stTabs button {
    font-family: var(--font-body) !important;
    color: var(--text-muted) !important;
    border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
}

.stTabs button[aria-selected="true"] {
    color: var(--amber) !important;
    border-bottom: 2px solid var(--amber) !important;
}

/* ── Scrollbar ───────────────────────────────────── */

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: var(--border-default);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: var(--border-active); }

/* ── Dividers ────────────────────────────────────── */

hr, .stDivider {
    border-color: var(--border-subtle) !important;
}

/* ── Animations ──────────────────────────────────── */

@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

@keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 8px var(--amber-glow); }
    50%      { box-shadow: 0 0 20px rgba(240,165,0,0.28); }
}

@keyframes scanline {
    0%   { background-position: 0 0; }
    100% { background-position: 0 100px; }
}

/* Subtle background texture */
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 9999;
    opacity: 0.015;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(255,255,255,0.015) 2px,
        rgba(255,255,255,0.015) 4px
    );
    animation: scanline 8s linear infinite;
}

/* ── Custom card utility ─────────────────────────── */

.glass-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 20px 24px;
    transition: all 0.22s ease;
}

.glass-card:hover {
    border-color: var(--border-default);
    background: var(--bg-elevated);
}

/* ── Data highlight ──────────────────────────────── */

.data-up   { color: var(--red) !important; font-weight: 600; }
.data-down { color: var(--green) !important; font-weight: 600; }
.data-mono { font-family: var(--font-mono) !important; }

/* ── Progress bars ───────────────────────────────── */

.stProgress > div > div {
    background: var(--amber) !important;
}
</style>
""", unsafe_allow_html=True)


# ── API Helpers ──────────────────────────────────────────────────

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

@st.cache_data(ttl=30)
def get_news_with_sentiment(stock_code: str, page_size: int = 30) -> list[dict]:
    try:
        r = requests.get(
            f"{API_BASE}/news",
            params={"stock_code": stock_code, "page_size": page_size, "with_sentiment": "true"},
            timeout=10,
        )
        return r.json().get("items", [])
    except Exception:
        return []

def call_predict(stock_code: str) -> dict | None:
    try:
        r = requests.post(f"{API_BASE}/predict", json={"stock_code": stock_code}, timeout=10)
        return r.json()
    except Exception:
        return None


# ── Shared Chart Theme ───────────────────────────────────────────

PLOTLY_THEME = {
    "plotly_dark": {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Plus Jakarta Sans, PingFang SC, sans-serif", "color": "#9296ab"},
        "title": {"font": {"family": "Outfit, PingFang SC, sans-serif", "color": "#e4e6ef"}},
        "xaxis": {"gridcolor": "#1a1d2b", "linecolor": "#232636", "zerolinecolor": "#1a1d2b"},
        "yaxis": {"gridcolor": "#1a1d2b", "linecolor": "#232636", "zerolinecolor": "#1a1d2b"},
        "legend": {"font": {"color": "#9296ab"}},
        "colorway": ["#f0a500", "#5284ff", "#ff5252", "#00c897", "#b388ff", "#00c2d1"],
        "margin": {"l": 0, "r": 0, "t": 0, "b": 0},
    }
}


# ==================================================================
#  SIDEBAR
# ==================================================================

with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;padding:4px 0 16px 0;">
        <div style="width:32px;height:32px;border-radius:6px;background:linear-gradient(135deg,#f0a500,#f5c842);
                    display:flex;align-items:center;justify-content:center;font-weight:800;font-size:16px;
                    color:#0a0b10;font-family:'JetBrains Mono',monospace;">◆</div>
        <div>
            <div style="font-family:'Outfit',sans-serif;font-weight:700;font-size:0.95rem;color:#e4e6ef;
                        letter-spacing:0.03em;">StockScope</div>
            <div style="font-family:'Plus Jakarta Sans',sans-serif;font-size:0.65rem;color:#5e6278;
                        letter-spacing:0.06em;text-transform:uppercase;">Prediction Engine v4.0</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "",
        ["🏠 市场总览", "🔍 个股详情", "📊 回测曲线", "📰 新闻分析", "🤖 AI助手", "⚙️ 系统"],
        label_visibility="collapsed",
    )

    st.markdown("</br>", unsafe_allow_html=True)

    # Live status indicator
    try:
        r = requests.get(f"{API_BASE}/admin/health", timeout=3)
        if r.status_code == 200:
            st.markdown("""
            <div style="display:flex;align-items:center;gap:6px;padding:6px 0;">
                <div style="width:6px;height:6px;border-radius:50%;background:#00c897;box-shadow:0 0 6px rgba(0,200,151,0.5);"></div>
                <span style="font-size:0.7rem;color:#5e6278;font-family:'Plus Jakarta Sans',sans-serif;">系统在线</span>
            </div>
            """, unsafe_allow_html=True)
    except Exception:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:6px;padding:6px 0;">
            <div style="width:6px;height:6px;border-radius:50%;background:#ff5252;box-shadow:0 0 6px rgba(255,82,82,0.5);"></div>
            <span style="font-size:0.7rem;color:#ff5252;font-family:'Plus Jakarta Sans',sans-serif;">后端离线</span>
        </div>
        """, unsafe_allow_html=True)


# ==================================================================
#  PAGE: Market Overview
# ==================================================================

if page == "🏠 市场总览":

    data = get_market_overview()
    items = data.get("items", [])
    industries = data.get("industries", [])
    summary = data.get("summary", {})

    if not items:
        st.warning("暂无行情数据 — 请先运行 系统 → 刷新股价 抓取数据")
        st.stop()

    # ── Hero metrics row ──
    shadow = get_shadow_stats()
    c1, c2, c3, c4, c5 = st.columns(5)

    metric_style = """
    <div style="background:%s;border:1px solid %s;border-radius:10px;padding:16px 18px;
                transition:all 0.2s ease;">
        <div style="font-family:'Outfit','PingFang SC',sans-serif;font-size:0.68rem;font-weight:500;
                    text-transform:uppercase;letter-spacing:0.08em;color:#5e6278;margin-bottom:8px;">
            %s</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:1.5rem;font-weight:600;
                    color:%s;">%s</div>
        %s
    </div>
    """

    def delta_html(delta_str, is_up):
        color = "#ff5252" if is_up else "#00c897"
        arrow = "▲" if is_up else "▼"
        return f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.78rem;color:{color};margin-top:4px;">{arrow} {delta_str}</div>'

    with c1:
        st.markdown(metric_style % (
            "#11131e", "#1a1d2b", "股票总数",
            "#e4e6ef", f"{summary.get('total', 0):,}",
            ""
        ), unsafe_allow_html=True)

    with c2:
        up_pct = f"{summary.get('up_ratio', 0):.0%}"
        st.markdown(metric_style % (
            "rgba(255,82,82,0.05)", "rgba(255,82,82,0.12)", "上涨家数",
            "#ff5252", str(summary.get("up", 0)),
            delta_html(up_pct, True)
        ), unsafe_allow_html=True)

    with c3:
        st.markdown(metric_style % (
            "rgba(0,200,151,0.05)", "rgba(0,200,151,0.12)", "下跌家数",
            "#00c897", str(summary.get("down", 0)),
            ""
        ), unsafe_allow_html=True)

    with c4:
        wr = shadow.get('win_rate', 0)
        wr_label = f"{wr:.1%}"
        st.markdown(metric_style % (
            "rgba(240,165,0,0.05)", "rgba(240,165,0,0.15)", "回测胜率",
            "#f0a500", wr_label,
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.7rem;color:#5e6278;margin-top:4px;">{shadow.get("total_predictions", 0)} 次预测</div>'
        ), unsafe_allow_html=True)

    with c5:
        # net breadth
        up_n = summary.get("up", 0)
        down_n = summary.get("down", 0)
        net = up_n - down_n
        net_sym = "+" if net >= 0 else ""
        net_color = "#ff5252" if net >= 0 else "#00c897"
        st.markdown(metric_style % (
            "#11131e", "#1a1d2b", "净涨跌",
            net_color, f"{net_sym}{net}",
            '<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.7rem;color:#5e6278;margin-top:4px;">上涨 - 下跌</div>'
        ), unsafe_allow_html=True)

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── Filters ──
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        selected_industry = st.selectbox("行业", ["全部"] + industries, key="ind")
    with col_f2:
        exchange_filter = st.selectbox("交易所", ["全部", "SH (上海)", "SZ (深圳)"], key="exch")
    with col_f3:
        screener = st.selectbox(
            "快速筛选",
            ["全部", "🔥 涨幅>2%", "❄️ 跌幅>2%", "📉 RSI<30超卖", "💡 积极情感", "🏦 仅银行"],
            key="screen",
        )

    # Apply filters
    industry_arg = None if selected_industry == "全部" else selected_industry
    exchange_arg = None
    if exchange_filter == "SH (上海)":
        exchange_arg = "SH"
    elif exchange_filter == "SZ (深圳)":
        exchange_arg = "SZ"
    if industry_arg or exchange_arg:
        data = get_market_overview(industry=industry_arg, exchange=exchange_arg)
        items = data.get("items", [])

    if screener == "🔥 涨幅>2%":
        items = [i for i in items if i["change_pct"] > 2]
    elif screener == "❄️ 跌幅>2%":
        items = [i for i in items if i["change_pct"] < -2]
    elif screener == "🏦 仅银行":
        items = [i for i in items if i["industry"] == "银行"]
    elif screener == "💡 积极情感":
        items = [i for i in items if i.get("sentiment") and i["sentiment"] > 0.05]
    elif screener == "📉 RSI<30超卖":
        items = [i for i in items if i.get("change_pct", 0) < -3]

    st.markdown(
        f'<div style="font-size:0.75rem;color:#5e6278;margin-bottom:8px;">'
        f'显示 <b style="color:#e4e6ef;">{len(items)}</b> 只股票'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Table ──
    if items:
        df = pd.DataFrame(items)

        # Build styled display with HTML in cells
        def make_change_cell(val):
            if val > 0:
                return f'<span style="color:#ff5252;font-weight:600;font-family:JetBrains Mono,monospace;">+{val:.2f}%</span>'
            elif val < 0:
                return f'<span style="color:#00c897;font-weight:600;font-family:JetBrains Mono,monospace;">{val:.2f}%</span>'
            else:
                return f'<span style="color:#5e6278;font-family:JetBrains Mono,monospace;">0.00%</span>'

        def make_sent_icon(val):
            if val and val > 0.05:
                return '🟢'
            elif val and val < -0.05:
                return '🔴'
            return '⚪'

        display_df = df[["code", "name", "industry", "close", "change_pct", "volume", "sentiment"]].copy()
        display_df["sentiment"] = display_df["sentiment"].apply(make_sent_icon)
        display_df["change_pct"] = display_df["change_pct"].apply(make_change_cell)
        display_df["volume"] = (display_df["volume"] / 10000).apply(lambda x: f"{x:.0f}万")
        display_df["close"] = display_df["close"].apply(
            lambda x: f'<span style="font-family:JetBrains Mono,monospace;font-weight:500;">{x:.2f}</span>'
        )
        display_df.columns = ["代码", "名称", "行业", "最新价", "涨跌幅", "成交量(万)", "情感"]

        st.dataframe(
            display_df,
            use_container_width=True,
            height=580,
            hide_index=True,
            column_config={
                "代码": st.column_config.TextColumn(width="small"),
                "涨跌幅": st.column_config.TextColumn(width="small"),
                "情感": st.column_config.TextColumn(width="small"),
            },
        )
    else:
        st.info("无匹配结果")

    # ── Industry Distribution ──
    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'Outfit','PingFang SC',sans-serif;font-size:0.95rem;font-weight:600;color:#e4e6ef;">
    📊 行业涨跌分布</div>
    """, unsafe_allow_html=True)

    by_ind = data.get("by_industry", {})
    if by_ind:
        chart_data = []
        for ind, stocks in by_ind.items():
            up = sum(1 for s in stocks if s["change_pct"] > 0)
            down = sum(1 for s in stocks if s["change_pct"] < 0)
            flat = len(stocks) - up - down
            chart_data.append({
                "行业": ind,
                "上涨": up,
                "下跌": down,
                "持平": flat,
                "涨比": round(up / len(stocks) * 100, 1) if stocks else 0,
            })

        chart_df = pd.DataFrame(chart_data).sort_values("涨比", ascending=False)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="上涨", y=chart_df["行业"], x=chart_df["上涨"],
            orientation="h", marker=dict(color="#ff5252", cornerradius=2),
        ))
        fig.add_trace(go.Bar(
            name="下跌", y=chart_df["行业"], x=chart_df["下跌"],
            orientation="h", marker=dict(color="#00c897", cornerradius=2),
        ))
        fig.add_trace(go.Bar(
            name="持平", y=chart_df["行业"], x=chart_df["持平"],
            orientation="h", marker=dict(color="#2f3345", cornerradius=2),
        ))
        fig.update_layout(
            barmode="stack",
            height=max(280, len(chart_data) * 28),
            margin=dict(l=0, r=0, t=0, b=0),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans, sans-serif", color="#9296ab", size=12),
            xaxis=dict(title="股票数", gridcolor="#1a1d2b"),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"),
            legend=dict(orientation="h", y=1.04, x=0, font=dict(color="#9296ab")),
            bargap=0.3,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("行业分布数据不足")


# ==================================================================
#  PAGE: Stock Detail
# ==================================================================

elif page == "🔍 个股详情":

    st.markdown("""
    <div style="font-family:'Outfit','PingFang SC',sans-serif;font-size:1.2rem;font-weight:600;color:#e4e6ef;
                margin-bottom:8px;">🔍 个股深度分析</div>
    """, unsafe_allow_html=True)

    search_kw = st.text_input(
        "搜索股票",
        placeholder="输入代码或名称，如 600519 或 茅台...",
        label_visibility="collapsed",
    )
    stocks = search_stocks(search_kw) if search_kw else []

    if stocks:
        code = st.selectbox(
            "选择股票",
            options=[s["code"] for s in stocks],
            format_func=lambda c: f"{c}  —  {next((s['name'] for s in stocks if s['code'] == c), '')}",
            label_visibility="collapsed",
        )
    else:
        code = st.selectbox(
            "选择股票",
            options=["600519.SH", "000001.SZ", "300750.SZ", "601318.SH"],
            format_func=lambda c: f"{c}  —  热门",
            label_visibility="collapsed",
        )

    if not code:
        st.stop()

    detail = get_stock_detail(code)
    prices = detail.get("prices", [])

    # ── Stock header ──
    st.markdown(f"""
    <div style="display:flex;align-items:baseline;gap:12px;margin:12px 0 8px 0;">
        <span style="font-family:'JetBrains Mono',monospace;font-size:1.3rem;font-weight:600;color:#e4e6ef;">
            {code}</span>
        <span style="font-family:'Outfit','PingFang SC',sans-serif;font-size:1.1rem;font-weight:500;color:#9296ab;">
            {detail.get('name', '')}</span>
        <span style="font-size:0.75rem;padding:3px 10px;border-radius:20px;background:rgba(240,165,0,0.1);
                     color:#f0a500;font-weight:500;font-family:'Plus Jakarta Sans',sans-serif;">
            {detail.get('industry', 'N/A')}</span>
    </div>
    """, unsafe_allow_html=True)

    if not prices:
        st.info("暂无K线数据 — 请先在系统页面刷新股价")
        st.stop()

    # ── Data prep ──
    dates = [p["date"] for p in prices]
    opens = [p["open"] for p in prices]
    highs = [p["high"] for p in prices]
    lows = [p["low"] for p in prices]
    closes = [p["close"] for p in prices]
    volumes = [p["volume"] for p in prices]
    n = len(closes)

    # ── Technical Indicators ──
    def sma(data, w):
        return [sum(data[max(0, i-w+1):i+1]) / min(i+1, w) for i in range(len(data))]

    ma5 = sma(closes, 5) if n >= 5 else closes
    ma20 = sma(closes, 20) if n >= 20 else closes

    # BOLL (20,2)
    boll_mid = ma20
    boll_upper, boll_lower = [], []
    for i in range(n):
        w = closes[max(0, i-19):i+1]
        std = (sum((x - sum(w)/len(w))**2 for x in w) / len(w)) ** 0.5 if len(w) > 1 else 0
        boll_upper.append(boll_mid[i] + 2 * std)
        boll_lower.append(boll_mid[i] - 2 * std)

    # MACD (12,26,9)
    ema12 = closes[0]
    ema26 = closes[0]
    macd_vals, signal_vals, hist_vals = [], [], []
    for i, p in enumerate(closes):
        ema12 = p * 2/13 + ema12 * 11/13
        ema26 = p * 2/27 + ema26 * 25/27
        d = ema12 - ema26
        macd_vals.append(d)
        sig = macd_vals[0] if i == 0 else d * 2/10 + signal_vals[-1] * 8/10
        signal_vals.append(sig)
        hist_vals.append(d - sig)

    # RSI (14)
    rsi_vals = [50.0] * 14
    for i in range(14, n):
        gains, losses = [], []
        for j in range(i-13, i+1):
            diff = closes[j] - closes[j-1]
            gains.append(diff if diff > 0 else 0)
            losses.append(-diff if diff < 0 else 0)
        avg_g = sum(gains) / 14
        avg_l = sum(losses) / 14
        rs = avg_g / (avg_l + 1e-9)
        rsi_vals.append(100 - 100/(1+rs))

    # ── K-line Chart (4 panels) ──
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.025,
        row_heights=[0.44, 0.2, 0.18, 0.18],
    )

    # Candle
    fig.add_trace(go.Candlestick(
        x=dates, open=opens, high=highs, low=lows, close=closes, name="K线",
        increasing=dict(line=dict(color="#ff5252", width=1), fillcolor="#ff5252"),
        decreasing=dict(line=dict(color="#00c897", width=1), fillcolor="#00c897"),
        whiskerwidth=0.5,
    ), row=1, col=1)

    # MAs
    fig.add_trace(go.Scatter(
        x=dates, y=ma5, mode="lines", name="MA5",
        line=dict(color="#f0a500", width=1.2),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=dates, y=ma20, mode="lines", name="MA20",
        line=dict(color="#5284ff", width=1.2),
    ), row=1, col=1)

    # Bollinger bands
    fig.add_trace(go.Scatter(
        x=dates, y=boll_upper, mode="lines", name="BOLL上轨",
        line=dict(color="#b388ff", width=0.6, dash="dot"), showlegend=False,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=dates, y=boll_lower, mode="lines", name="BOLL下轨",
        line=dict(color="#b388ff", width=0.6, dash="dot"),
        fill="tonexty", fillcolor="rgba(179,136,255,0.04)", showlegend=False,
    ), row=1, col=1)

    # Volume bars
    vol_colors = ["#ff5252" if closes[i] >= opens[i] else "#00c897" for i in range(n)]
    fig.add_trace(go.Bar(
        x=dates, y=volumes, name="成交量",
        marker=dict(color=vol_colors, opacity=0.3), showlegend=False,
    ), row=2, col=1)

    # MACD
    macd_bar_colors = ["#ff5252" if h >= 0 else "#00c897" for h in hist_vals]
    fig.add_trace(go.Bar(
        x=dates, y=hist_vals, name="MACD柱",
        marker=dict(color=macd_bar_colors, opacity=0.65), showlegend=False,
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=dates, y=macd_vals, mode="lines", name="DIF",
        line=dict(color="#f0a500", width=1),
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=dates, y=signal_vals, mode="lines", name="DEA",
        line=dict(color="#5284ff", width=1),
    ), row=3, col=1)

    # RSI
    fig.add_trace(go.Scatter(
        x=dates, y=rsi_vals, mode="lines", name="RSI(14)",
        line=dict(color="#b388ff", width=1.5),
    ), row=4, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(255,82,82,0.25)", row=4, col=1,
                  annotation_text="超买 70", annotation_font_color="#ff5252", annotation_font_size=9)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(0,200,151,0.25)", row=4, col=1,
                  annotation_text="超卖 30", annotation_font_color="#00c897", annotation_font_size=9)

    # Layout
    fig.update_layout(
        height=720,
        xaxis=dict(rangeslider=dict(visible=False)),
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="h", y=1.06, x=0, font=dict(size=11, color="#9296ab")),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#9296ab"),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#161925",
            font=dict(family="JetBrains Mono, monospace", size=12, color="#e4e6ef"),
            bordercolor="#2f3345",
        ),
    )
    fig.update_yaxes(title_text="价格 ¥", row=1, col=1, gridcolor="#1a1d2b", title_font=dict(color="#9296ab"))
    fig.update_yaxes(title_text="成交量", row=2, col=1, gridcolor="#1a1d2b", title_font=dict(color="#9296ab"))
    fig.update_yaxes(title_text="MACD", row=3, col=1, gridcolor="#1a1d2b", title_font=dict(color="#9296ab"))
    fig.update_yaxes(title_text="RSI", row=4, col=1, gridcolor="#1a1d2b", title_font=dict(color="#9296ab"))

    st.plotly_chart(fig, use_container_width=True)

    # ── Prediction + Latest Price ──
    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    col_pred, col_info = st.columns([1, 2])

    with col_pred:
        st.markdown("""
        <div style="font-family:'Outfit','PingFang SC',sans-serif;font-size:0.9rem;font-weight:600;
                    color:#e4e6ef;margin-bottom:10px;">🎯 模型预测</div>
        """, unsafe_allow_html=True)

        if st.button("⚡ 生成预测", type="primary", use_container_width=True):
            with st.spinner("模型推理中..."):
                result = call_predict(code)
            if result:
                label_text = "📈 看涨" if result["predicted_label"] == "up" else "📉 看跌"
                label_color = "#ff5252" if result["predicted_label"] == "up" else "#00c897"
                prob = result["predicted_prob"]
                conf = result["confidence"]

                st.markdown(f"""
                <div style="background:{'rgba(255,82,82,0.06)' if result['predicted_label'] == 'up' else 'rgba(0,200,151,0.06)'};
                            border:1px solid {'rgba(255,82,82,0.2)' if result['predicted_label'] == 'up' else 'rgba(0,200,151,0.2)'};
                            border-radius:10px;padding:20px 24px;text-align:center;">
                    <div style="font-size:1.1rem;font-weight:700;color:{label_color};margin-bottom:12px;">
                        {label_text}</div>
                    <div style="display:flex;justify-content:center;gap:32px;">
                        <div>
                            <div style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.08em;color:#5e6278;">
                                概率</div>
                            <div style="font-family:'JetBrains Mono',monospace;font-size:1.4rem;font-weight:700;color:#e4e6ef;">
                                {prob:.1%}</div>
                        </div>
                        <div>
                            <div style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.08em;color:#5e6278;">
                                置信度</div>
                            <div style="font-family:'JetBrains Mono',monospace;font-size:1.4rem;font-weight:700;color:#e4e6ef;">
                                {conf:.1%}</div>
                        </div>
                    </div>
                    <div style="margin-top:12px;font-size:0.7rem;color:#5e6278;">
                        模型: {result['model_version']} · 目标日: {result['target_date']}</div>
                </div>
                """, unsafe_allow_html=True)

    with col_info:
        if prices:
            st.markdown("""
            <div style="font-family:'Outfit','PingFang SC',sans-serif;font-size:0.9rem;font-weight:600;
                        color:#e4e6ef;margin-bottom:10px;">📋 最新行情</div>
            """, unsafe_allow_html=True)

            latest = prices[-1]
            prev = prices[-2] if len(prices) > 1 else latest
            chg = (latest["close"] - prev["close"]) / prev["close"] * 100

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.metric("收盘价", f"{latest['close']:.2f}", delta=f"{chg:+.2f}%")
            with c2:
                st.metric("开盘", f"{latest['open']:.2f}")
            with c3:
                st.metric("最高", f"{latest['high']:.2f}")
            with c4:
                st.metric("最低", f"{latest['low']:.2f}")
            with c5:
                vol_display = f"{latest['volume']/10000:.0f}万" if latest['volume'] > 10000 else f"{latest['volume']}"
                st.metric("成交量", vol_display)


# ==================================================================
#  PAGE: Backtest
# ==================================================================

elif page == "📊 回测曲线":

    st.markdown("""
    <div style="font-family:'Outfit','PingFang SC',sans-serif;font-size:1.2rem;font-weight:600;color:#e4e6ef;
                margin-bottom:8px;">📊 影子模式回测</div>
    """, unsafe_allow_html=True)

    bt = get_backtest_daily()
    daily_data = bt.get("daily", [])

    if daily_data:
        overall_wr = bt.get("overall_win_rate", 0)
        shadow = get_shadow_stats()

        # ── Summary cards ──
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            delta_str = f"{overall_wr - 0.5:+.1%}"
            st.metric("累计胜率", f"{overall_wr:.1%}", delta=f"{delta_str} vs 随机")

        with c2:
            st.metric("回测天数", str(len(daily_data)))

        with c3:
            st.metric("最新日胜率", f"{shadow.get('win_rate', 0):.1%}")

        with c4:
            total_preds = sum(d.get("total", 0) for d in daily_data)
            st.metric("总预测数", str(total_preds))

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        # ── Chart ──
        dates = [d["date"] for d in daily_data]
        daily_wr = [d["win_rate"] for d in daily_data]
        cum_wr = [d["cumulative_win_rate"] for d in daily_data]

        fig = go.Figure()

        # Daily bars
        bar_colors = ["#ff5252" if w >= 0.5 else "#00c897" for w in daily_wr]
        fig.add_trace(go.Bar(
            x=dates, y=daily_wr, name="日胜率",
            marker=dict(color=bar_colors, opacity=0.55),
            hovertemplate="%{x}<br>日胜率: %{y:.1%}<extra></extra>",
        ))

        # Cumulative line
        fig.add_trace(go.Scatter(
            x=dates, y=cum_wr, name="累计胜率",
            line=dict(color="#f0a500", width=2.2),
            hovertemplate="%{x}<br>累计: %{y:.1%}<extra></extra>",
        ))

        # 50% baseline
        fig.add_hline(
            y=0.5, line_dash="dash", line_color="rgba(255,255,255,0.15)",
            annotation=dict(text="随机基线 50%", font=dict(color="#5e6278", size=10)),
        )

        fig.update_layout(
            height=420,
            margin=dict(l=0, r=0, t=0, b=0),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans, sans-serif", color="#9296ab"),
            yaxis=dict(tickformat=".0%", gridcolor="#1a1d2b", title="胜率"),
            xaxis=dict(gridcolor="rgba(0,0,0,0)"),
            legend=dict(orientation="h", y=1.04, x=0),
            bargap=0.4,
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"""
        <div style="text-align:center;font-size:0.78rem;color:#5e6278;margin-top:8px;">
            LightGBM 截面排名模型 · 累计胜率 <b style="color:{'#f0a500' if overall_wr >= 0.5 else '#ff5252'};">{overall_wr:.1%}</b> · {len(daily_data)} 个交易日
        </div>
        """, unsafe_allow_html=True)

    else:
        st.info("暂无回测数据。运行影子模式预测后自动生成回测曲线。")


# ==================================================================
#  PAGE: News Analysis
# ==================================================================

elif page == "📰 新闻分析":

    st.markdown("""
    <div style="font-family:'Outfit','PingFang SC',sans-serif;font-size:1.2rem;font-weight:600;color:#e4e6ef;
                margin-bottom:8px;">📰 新闻情感分析</div>
    """, unsafe_allow_html=True)

    search_code = st.selectbox(
        "选择股票",
        options=["600519.SH", "000001.SZ", "300750.SZ", "601318.SH", "000858.SZ"],
        format_func=lambda c: c,
        label_visibility="collapsed",
    )

    if search_code:
        news_list = get_news_with_sentiment(search_code, page_size=30)
        if news_list:
            # ── Sentiment summary ──
            sentiments = [
                n.get("sentiment", {}).get("sentiment_score", 0) or 0
                for n in news_list if n.get("sentiment")
            ]
            if sentiments:
                pos = sum(1 for s in sentiments if s > 0.1)
                neg = sum(1 for s in sentiments if s < -0.1)
                neu = len(sentiments) - pos - neg

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("积极 🟢", str(pos))
                with c2:
                    st.metric("中性 ⚪", str(neu))
                with c3:
                    st.metric("消极 🔴", str(neg))
                with c4:
                    avg_sent = sum(sentiments) / len(sentiments)
                    st.metric("平均情感", f"{avg_sent:+.2f}")

            st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

            # ── News list ──
            for n in news_list:
                sent = n.get("sentiment")
                if sent and sent.get("sentiment_score") is not None:
                    score = sent["sentiment_score"]
                    if score > 0.1:
                        emoji, tag_color = "🟢", "rgba(0,200,151,0.12)"
                    elif score < -0.1:
                        emoji, tag_color = "🔴", "rgba(255,82,82,0.12)"
                    else:
                        emoji, tag_color = "⚪", "rgba(255,255,255,0.04)"
                    event = sent.get("event_type", "N/A")
                    label = f"{emoji} [{event}] {n['title'][:70]}"
                else:
                    label = f"⚫ {n['title'][:70]}"

                with st.expander(label, expanded=False):
                    st.caption(f"来源: {n.get('source', '—')}  |  {n.get('publish_time', '—')}")
                    if sent:
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            st.metric("情感得分", f"{sent['sentiment_score']:+.2f}")
                        with c2:
                            st.metric("强度", f"{sent['intensity']:.2f}")
                        with c3:
                            st.metric("相关度", f"{sent['relevance']:.2f}")
                        with c4:
                            st.metric("事件类型", sent.get("event_type", "N/A"))
        else:
            st.info("暂无新闻数据。请先在系统页面抓取新闻。")


# ==================================================================
#  PAGE: AI Chat
# ==================================================================

elif page == "🤖 AI助手":

    st.markdown("""
    <div style="font-family:'Outfit','PingFang SC',sans-serif;font-size:1.2rem;font-weight:600;color:#e4e6ef;
                margin-bottom:2px;">🤖 AI 投资助手<span style="font-size:0.8rem;color:#5e6278;font-weight:400;
                margin-left:8px;">· 小析</span></div>
    <div style="font-size:0.78rem;color:#5e6278;margin-bottom:12px;">
        直接描述问题，AI 自动识别股票并分析 — 试试"茅台最近表现怎么样？"
    </div>
    """, unsafe_allow_html=True)

    # Init session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_stock_code" not in st.session_state:
        st.session_state.chat_stock_code = ""

    # ── Chat area ──
    chat_container = st.container(height=440, border=False)

    with chat_container:
        if not st.session_state.chat_history:
            st.markdown("""
            <div style="text-align:center;padding:40px 20px;">
                <div style="font-size:56px;margin-bottom:16px;">◆</div>
                <div style="font-family:'Outfit','PingFang SC',sans-serif;font-size:1rem;font-weight:600;
                            color:#e4e6ef;margin-bottom:6px;">
                    你好，我是小析</div>
                <div style="font-size:0.82rem;color:#9296ab;line-height:2;">
                    直接输入问题，我会自动识别你想了解的股票<br>
                    试试说：<br>
                    <code style="background:#1a1d2b;padding:2px 8px;border-radius:4px;color:#f0a500;">
                        茅台最近表现怎么样？</code><br>
                    <code style="background:#1a1d2b;padding:2px 8px;border-radius:4px;color:#f0a500;">
                        比亚迪现在适合买入吗？</code><br>
                    <code style="background:#1a1d2b;padding:2px 8px;border-radius:4px;color:#f0a500;">
                        上证50有哪些成分股值得关注？</code>
                </div>
            </div>
            """, unsafe_allow_html=True)

        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("assistant", avatar="💎"):
                    st.markdown(msg["content"])
                    if msg.get("stocks"):
                        stock_tags = ", ".join(
                            f"<code style='background:#1a1d2b;padding:2px 8px;border-radius:4px;"
                            f"color:#f0a500;font-size:0.78rem;'>{s['code']}</code> {s['name']}"
                            for s in msg["stocks"]
                        )
                        st.markdown(f"📌 已匹配: {stock_tags}", unsafe_allow_html=True)

    # ── Input ──
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
    input_col, btn_col = st.columns([6, 1])
    with input_col:
        user_input = st.chat_input(
            "输入问题... 如\"分析一下茅台\"、\"平安银行最近怎么样\"",
            key="ai_chat_input",
        )
    with btn_col:
        if st.button("🔄 清空", use_container_width=True, key="clear_chat"):
            st.session_state.chat_history = []
            st.session_state.chat_stock_code = ""
            st.rerun()

    if user_input:
        msg = user_input.strip()
        if not msg:
            st.stop()

        st.session_state.chat_history.append({"role": "user", "content": msg})

        with st.spinner("小析思考中..."):
            try:
                payload = {
                    "message": msg,
                    "history": [
                        {"role": h["role"], "content": h["content"]}
                        for h in st.session_state.chat_history[:-1]
                    ],
                }
                if st.session_state.chat_stock_code:
                    payload["stock_code"] = st.session_state.chat_stock_code

                r = requests.post(f"{API_BASE}/ai/chat", json=payload, timeout=60)
                result = r.json()
                reply = result.get("reply", "抱歉，分析出错。")

                matched = result.get("matched_stocks", [])
                active_stock = result.get("stock")
            except Exception as e:
                reply = f"请求失败: {e}"
                matched = []
                active_stock = None

        assistant_msg = {"role": "assistant", "content": reply}

        if active_stock:
            st.session_state.chat_stock_code = active_stock["code"]
            assistant_msg["stocks"] = [active_stock]
        elif matched:
            assistant_msg["stocks"] = matched

        st.session_state.chat_history.append(assistant_msg)
        st.rerun()

    # Disclaimer
    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align:center;font-size:0.7rem;color:#5e6278;padding:8px 0;
                border-top:1px solid #1a1d2b;">
        ⚠️ AI 分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。
    </div>
    """, unsafe_allow_html=True)


# ==================================================================
#  PAGE: System
# ==================================================================

elif page == "⚙️ 系统":

    st.markdown("""
    <div style="font-family:'Outfit','PingFang SC',sans-serif;font-size:1.2rem;font-weight:600;color:#e4e6ef;
                margin-bottom:8px;">⚙️ 系统管理</div>
    """, unsafe_allow_html=True)

    # ── Status cards ──
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("""
        <div style="font-family:'Outfit','PingFang SC',sans-serif;font-size:0.85rem;font-weight:600;
                    color:#e4e6ef;margin-bottom:8px;">🔗 服务端点</div>
        """, unsafe_allow_html=True)
        st.code(f"""API 后端   {API_BASE}
Swagger   http://localhost:8000/docs
健康检查  http://localhost:8000/health
ReDoc     http://localhost:8000/redoc""", language=None)

    with c2:
        st.markdown("""
        <div style="font-family:'Outfit','PingFang SC',sans-serif;font-size:0.85rem;font-weight:600;
                    color:#e4e6ef;margin-bottom:8px;">📈 数据统计</div>
        """, unsafe_allow_html=True)

        c2a, c2b = st.columns(2)
        with c2a:
            try:
                r = requests.get(f"{API_BASE}/stocks", params={"page_size": 1}, timeout=5)
                total = r.json().get("total", 0)
                st.metric("股票总数", str(total))
            except Exception:
                st.metric("股票总数", "N/A")
        with c2b:
            shadow = get_shadow_stats()
            st.metric("回测胜率", f"{shadow.get('win_rate', 0):.1%}")

    st.divider()

    # ── Actions ──
    st.markdown("""
    <div style="font-family:'Outfit','PingFang SC',sans-serif;font-size:0.85rem;font-weight:600;
                color:#e4e6ef;margin-bottom:10px;">🔧 管理操作</div>
    """, unsafe_allow_html=True)

    c_a, c_b, c_c = st.columns(3)

    with c_a:
        if st.button("🔄 刷新股价数据", use_container_width=True):
            with st.spinner("正在从 AkShare 抓取全 A 股数据..."):
                try:
                    r = requests.post(f"{API_BASE}/admin/seed-data", timeout=300)
                    result = r.json()
                    st.success(f"✅ 完成 — {result.get('total_records', 0):,} 条K线数据，"
                               f"{result.get('stocks_processed', 0)} 只股票")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"失败: {e}")

    with c_b:
        if st.button("🔮 运行影子预测", use_container_width=True):
            with st.spinner("正在对全部股票运行预测..."):
                try:
                    r = requests.post(f"{API_BASE}/admin/shadow-run", timeout=60)
                    result = r.json()
                    st.success(f"✅ 完成 — {result.get('success', 0)} 只预测成功, "
                               f"{result.get('skipped', 0)} 跳过")
                except Exception as e:
                    st.error(f"失败: {e}")

    with c_c:
        if st.button("🧹 清除缓存", use_container_width=True):
            st.cache_data.clear()
            st.success("缓存已清除")

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    c_d, c_e, c_f = st.columns(3)

    with c_d:
        if st.button("📰 抓取新闻", use_container_width=True):
            with st.spinner("正在抓取财经新闻..."):
                try:
                    r = requests.post(f"{API_BASE}/admin/seed-news", timeout=120)
                    result = r.json()
                    st.success(f"✅ 完成 — {result.get('total_news', 0)} 条新闻")
                except Exception as e:
                    st.error(f"失败: {e}")

    with c_e:
        if st.button("🧠 提取情感特征", use_container_width=True):
            with st.spinner("LLM 情感分析中..."):
                try:
                    r = requests.post(f"{API_BASE}/admin/extract-sentiment", timeout=120)
                    result = r.json()
                    st.success(f"✅ 处理 {result.get('processed', 0)} 条")
                except Exception as e:
                    st.error(f"失败: {e}")

    with c_f:
        if st.button("📋 回填实际价格", use_container_width=True):
            with st.spinner("回填影子预测结果..."):
                try:
                    r = requests.post(f"{API_BASE}/admin/shadow-backfill", timeout=60)
                    result = r.json()
                    st.success(f"✅ 回填 {result.get('updated', 0)} 条")
                except Exception as e:
                    st.error(f"失败: {e}")
