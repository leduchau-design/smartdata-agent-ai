@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===================================================
echo   Khoi dong SmartData Agent (Backend + Frontend)
echo ===================================================

echo [1/2] Dang khoi dong Backend FastAPI (Port 8000)...
start "SmartData Agent - Backend" cmd /k "call venv\Scripts\activate.bat && python -m src.main"

timeout /t 3 /nobreak >nul

echo [2/2] Dang khoi dong Frontend Streamlit (Port 8501)...
start "SmartData Agent - Frontend" cmd /k "call venv\Scripts\activate.bat && python -m streamlit run frontend/app.py --server.address=0.0.0.0"

echo ===================================================
echo   He thong da khoi dong xong! Trinh duyet web se tu mo.
echo ===================================================
