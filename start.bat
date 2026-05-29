@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   股价预测系统 V4.0 — 一键启动
echo ============================================
echo.

echo [1/2] 启动后端服务 (FastAPI :8000)...
start "后端 API" cmd /c "cd /d %~dp0backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload && pause"

echo [2/2] 启动前端看板 (Streamlit :8501)...
start "前端看板" cmd /c "cd /d %~dp0frontend\streamlit_app && streamlit run main.py --server.port 8501 --server.headless true && pause"

echo.
echo ============================================
echo   启动完毕！
echo   后端: http://localhost:8000/docs
echo   前端: http://localhost:8501
echo ============================================
echo.
echo 按任意键打开前端页面...
pause >nul
start http://localhost:8501
