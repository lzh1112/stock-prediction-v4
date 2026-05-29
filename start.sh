#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "============================================"
echo "  股价预测系统 V4.0 — 一键启动"
echo "============================================"
echo ""

# 检测 Python
PYTHON=""
for p in python3 python; do
    if command -v $p &>/dev/null; then
        PYTHON=$p
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌ 未找到 Python，请先安装 Python 3.11+"
    exit 1
fi

echo "[1/2] 启动后端 (FastAPI :8000)..."
(cd backend && $PYTHON -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload) &
BACKEND_PID=$!

echo "[2/2] 启动前端 (Streamlit :8501)..."
(cd frontend/streamlit_app && $PYTHON -m streamlit run main.py --server.port 8501 --server.headless true) &
FRONTEND_PID=$!

echo ""
echo "============================================"
echo "  启动完毕！"
echo "  后端 API: http://localhost:8000/docs"
echo "  前端看板: http://localhost:8501"
echo "  PID: 后端=$BACKEND_PID  前端=$FRONTEND_PID"
echo "============================================"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 打开浏览器
if command -v open &>/dev/null; then
    open http://localhost:8501
elif command -v start &>/dev/null; then
    start http://localhost:8501
fi

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
