@echo off
echo ==========================================
echo     PPE Detection Setup Script
echo ==========================================
echo.
echo This script will install all required dependencies
echo for the PPE Detection Web Application.
echo.
echo Please ensure you have Python 3.8+ installed.
echo.
pause

echo Installing Python packages...
echo.

pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ==========================================
echo Installation complete!
echo ==========================================
echo.
echo To start the application, run:
echo   start_server.bat
echo.
echo Or manually run:
echo   python app.py
echo.
pause