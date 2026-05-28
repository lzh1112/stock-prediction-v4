"""
多模态新闻驱动型股价预测系统 — Streamlit 原型看板

阶段 4 完整实现。当前为骨架版本。
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="股价预测系统 V4.0",
    page_icon="📈",
    layout="wide",
)

# --- 侧边栏 ---
st.sidebar.title("📊 导航")
page = st.sidebar.radio("选择页面", ["股票搜索", "预测看板", "历史回测", "系统状态"])

# --- 主内容 ---
if page == "股票搜索":
    st.title("🔍 股票搜索")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.text_input("输入股票代码或名称", placeholder="例如：600519 或 贵州茅台")
    with col2:
        st.button("搜索", type="primary")

    st.info("📡 输入股票代码后，K线图与新闻列表将在此展示。", icon="ℹ️")

elif page == "预测看板":
    st.title("🎯 每日预测看板")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric(label="今日预测胜率", value="--", delta="--")
    with col_b:
        st.metric(label="累计胜率 (30日)", value="--", delta="--")
    with col_c:
        st.metric(label="模型版本", value="v4.0-dev")

    st.divider()
    st.info("📡 影子模式运行后，每日预测结果将在此展示。", icon="ℹ️")

elif page == "历史回测":
    st.title("📈 历史回测")
    st.info("📡 回测结果将在模型训练完成后展示。", icon="ℹ️")

elif page == "系统状态":
    st.title("⚙️ 系统状态")
    st.json(
        {
            "backend": "http://localhost:8000",
            "docs": "http://localhost:8000/docs",
            "celery_flower": "http://localhost:5555",
            "database": "postgresql://localhost:5432/stock_pred",
        }
    )
