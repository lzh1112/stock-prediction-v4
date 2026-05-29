@echo off
title Stock Prediction V4.0
cd /d "%~dp0"

echo ============================================
echo   Stock Prediction System V4.0
echo ============================================
echo.

echo [1/2] Starting Backend API (port 8000)...
start "Backend-API" cmd /c "pushd "%~dp0backend" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload && pause"

echo [2/2] Starting Frontend (port 8501)...
start "Frontend" cmd /c "pushd "%~dp0frontend\streamlit_app" && streamlit run main.py --server.port 8501 --server.headless true && pause"

echo.
echo ============================================
echo   Backend API : http://localhost:8000/docs
echo   Frontend   : http://localhost:8501
echo ============================================
echo.
echo Starting browser...
start http://localhost:8501

echo All services started. Close this window or the two API/Frontend windows to stop.
echo.
pause
