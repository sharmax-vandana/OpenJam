@echo off
echo.
echo =====================================================
echo   Open Jam — Real-time Music Listening Platform
echo =====================================================
echo.

echo [1/2] Installing dependencies...
pip install -r requirements.txt --quiet

echo [2/2] Starting server...
echo.
echo   App running at: http://localhost:8000
echo   Press Ctrl+C to stop
echo.
python run.py
