@echo off
echo ====================================
echo Starting Employee Monitoring Backend
echo ====================================
echo.

REM Check if virtual environment exists
if not exist .venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first.
    pause
    exit /b 1
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo.
echo Starting Django development server...
echo Server will be available at: http://localhost:8000
echo Admin panel: http://localhost:8000/admin
echo.
echo Press Ctrl+C to stop the server
echo.

python manage.py runserver
