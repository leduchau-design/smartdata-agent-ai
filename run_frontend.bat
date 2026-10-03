@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===================================================
echo   Khoi dong SmartData Agent - Frontend (Streamlit)
echo ===================================================
call venv\Scripts\activate.bat
python -m streamlit run frontend/app.py --server.address=0.0.0.0
pause
