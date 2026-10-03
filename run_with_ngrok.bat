@echo off
chcp 65001 >nul
cd /d "%~dp0"

set NGROK="C:\Users\admin\AppData\Local\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"

echo ===================================================
echo   SmartData Agent + NGROK Public Link
echo ===================================================

echo [1/3] Dang khoi dong Backend FastAPI (Port 8000)...
start "SmartData - Backend" cmd /k "call venv\Scripts\activate.bat && python -m src.main"

timeout /t 3 /nobreak >nul

echo [2/3] Dang khoi dong Frontend Streamlit (Port 8501)...
start "SmartData - Frontend" cmd /k "call venv\Scripts\activate.bat && python -m streamlit run frontend/app.py"

timeout /t 5 /nobreak >nul

echo [3/3] Dang tao link public voi ngrok...
echo.
echo >>> Nhin vao cua so NGROK de lay link HTTPS <<<
echo >>> Copy dong "Forwarding https://..." roi gui cho ban be <<<
echo.
start "NGROK - Public Link" cmd /k "%NGROK% http 8501"

echo ===================================================
echo   Xong! Tim link trong cua so co ten "NGROK - Public Link"
echo ===================================================
pause
