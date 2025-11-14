@echo off
echo ====================================
echo Employee Monitoring Backend Setup
echo ====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/5] Creating virtual environment...
if exist .venv (
    echo Virtual environment already exists. Skipping creation.
) else (
    python -m venv .venv
    echo Virtual environment created successfully!
)

echo.
echo [2/5] Activating virtual environment...
call .venv\Scripts\activate.bat

echo.
echo [3/5] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [4/5] Running database migrations...
python manage.py makemigrations
python manage.py migrate

echo.
echo [5/5] Creating superuser...
echo.
echo Default credentials will be: admin / admin123
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123', employee_id='EMP001', full_name='Administrator', role='ADMIN')"

echo.
echo ====================================
echo Setup completed successfully!
echo ====================================
echo.
echo To start the server, run: run_server.bat
echo Or manually: .venv\Scripts\activate.bat then python manage.py runserver
echo.
pause
