@echo off
REM Quick start script for Windows

echo ================================
echo ANTIGRAVITY QUICK START
echo ================================
echo.

echo Installing dependencies...
echo.

cd services\runtime
pip install -r requirements.txt
cd ..\..

cd services\agent
pip install -r requirements.txt
cd ..\..

cd services\orchestrator
pip install -r requirements.txt
cd ..\..

echo.
echo Dependencies installed!
echo.
echo Starting services...
echo.
echo Open 3 separate terminals and run:
echo.
echo Terminal 1: cd services\agent ^&^& python main.py
echo Terminal 2: cd services\orchestrator ^&^& python main.py  
echo Terminal 3: cd services\runtime ^&^& python main.py
echo.
echo Or use Docker:
echo cd docker ^&^& docker-compose up --build
echo.
pause
