@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===================================================
echo   Khoi dong SmartData Agent - Backend (FastAPI)
echo ===================================================
call venv\Scripts\activate.bat
python -m src.main
pause
