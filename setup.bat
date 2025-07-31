@echo off
echo CommandPad Companion Setup
echo =========================

echo Installing Python dependencies...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo Installation failed. Make sure you have Python and pip installed.
    echo Try running as administrator if you get permission errors.
    pause
    exit /b 1
)

echo.
echo Installation complete!
echo.
echo To run the companion app:
echo   python companion_app.py
echo.
echo Or specify a specific COM port:
echo   python companion_app.py COM3
echo.
pause
