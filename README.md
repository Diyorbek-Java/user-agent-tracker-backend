# Employee Monitoring Backend

Django REST API backend for the Employee Monitoring System. Tracks and stores employee activity data.

## ⚡ Quick Start

### Prerequisites
- Python 3.11 or higher
- pip (Python package manager)

### Setup (First Time)

1. **Run the setup script:**
   ```bash
   setup.bat
   ```
   This will:
   - Create virtual environment (.venv)
   - Install all dependencies
   - Run database migrations
   - Create admin user (admin/admin123)

2. **Start the server:**
   ```bash
   run_server.bat
   ```

3. **Access the application:**
   - API: http://localhost:8000
   - Admin Panel: http://localhost:8000/admin
   - Login: `admin` / `admin123`

### Daily Usage

Just run `run_server.bat` to start the development server!

## 🚀 Features

- **RESTful API** for activity data collection
- **SQLite Database** (default) or PostgreSQL support
- **Custom User Model** combining authentication and employee data
- **Admin Dashboard** via Django Admin
- **CORS Support** for cross-origin requests
- **Auto-reload** development server

## 📋 Project Structure

```
employee-monitoring-backend/
├── .venv/                    # Virtual environment (created by setup.bat)
├── monitoring_system/        # Django project settings
│   ├── settings.py          # Configuration
│   ├── urls.py              # URL routing
│   └── wsgi.py              # WSGI application
├── tracker_api/             # Main API application
│   ├── models.py            # Database models (User, Session, Activity)
│   ├── serializers.py       # API serializers
│   ├── views.py             # API views
│   ├── urls.py              # API routes
│   └── admin.py             # Admin configuration
├── .env                     # Environment variables
├── requirements.txt         # Python dependencies
├── manage.py                # Django management script
├── setup.bat                # Setup script
└── run_server.bat           # Run development server
```

## 🛠️ Manual Setup (Alternative)

If you prefer to set up manually without the script:

### 1. Create Virtual Environment

```bash
python -m venv .venv
```

### 2. Activate Virtual Environment

**Windows:**
```bash
.venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser

```bash
python manage.py createsuperuser
```

### 6. Start Development Server

```bash
python manage.py runserver
```

## 🌐 Access the Application

- **Django API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
  - Username: `admin`
  - Password: `admin123`

## 🛠️ Common Commands

### Database Management

```bash
# Make sure virtual environment is activated
.venv\Scripts\activate.bat

# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create a new superuser
python manage.py createsuperuser

# Access Django shell
python manage.py shell

# Access database shell (SQLite)
python manage.py dbshell
```

### Useful Django Commands

```bash
# Check for issues
python manage.py check

# Run tests
python manage.py test

# Collect static files
python manage.py collectstatic
```

## 💾 Database Configuration

By default, the project uses **SQLite** (no setup required). The database file `db.sqlite3` will be created automatically.

### Optional: Use PostgreSQL

If you want to use PostgreSQL instead:

1. Install PostgreSQL on your system
2. Create a database:
   ```sql
   CREATE DATABASE employee_monitoring;
   ```
3. Update `.env` file:
   ```ini
   DB_ENGINE=django.db.backends.postgresql
   DB_NAME=employee_monitoring
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432
   ```
4. Run migrations again:
   ```bash
   python manage.py migrate
   ```

## 📡 API Endpoints

### Authentication

**POST /api/auth/login/**
```json
{
  "username": "john",
  "password": "password123"
}
```

Response:
```json
{
  "success": true,
  "token": "auth-token-here",
  "user": {
    "id": 1,
    "username": "john",
    "email": "john@example.com"
  }
}
```

### Data Upload (C++ Client)

**POST /api/upload/**
```json
{
  "user_id": "john",
  "computer_name": "DESKTOP-ABC123",
  "session": {
    "start_time": 1699564800,
    "end_time": 1699568400
  },
  "activities": [
    {
      "type": 1,
      "process_name": "chrome.exe",
      "window_title": "GitHub - Chrome",
      "start_time": 1699564800,
      "end_time": 1699564900
    }
  ]
}
```

### User Management

- `GET /api/users/` - List all users
- `POST /api/users/` - Create new user
- `GET /api/users/{id}/` - Get user details
- `GET /api/users/{id}/sessions/` - Get user sessions
- `GET /api/users/{id}/stats/` - Get user statistics
- `GET /api/users/{id}/report/` - Get detailed activity report

### Session Management

- `GET /api/sessions/` - List all sessions
- `GET /api/sessions/{id}/` - Get session details (with activities)
- `GET /api/sessions/active/` - Get all active sessions

### Activity Management

- `GET /api/activities/` - List all activities
- `GET /api/activities/?session={id}` - Filter by session
- `GET /api/activities/?process={name}` - Filter by process name

### Dashboard

- `GET /api/dashboard/?days=7` - Get dashboard statistics

### Health Check

**GET /api/health**
```json
{
  "status": "ok",
  "database": "connected",
  "timestamp": "2025-11-11T10:30:00Z"
}
```

## 📊 Database Schema

### Models

**User** (Custom user model combining authentication and employee data)
- Authentication: `username`, `password`, `email`, `is_staff`, `is_superuser`
- Employee Info: `employee_id`, `full_name`, `role` (ADMIN/MANAGER/EMPLOYEE)
- Job Details: `department`, `position`, `computer_name`
- OTP System: `otp`, `otp_created_at`, `otp_expires_at`, `reset_otp`
- Timestamps: `date_joined`, `last_login`, `updated_at`

**Session**
- `id`: Primary key
- `user`: ForeignKey to User
- `start_time`: Session start
- `end_time`: Session end
- `is_active`: Boolean
- `total_duration`: Duration in seconds
- `created_at`: Record creation time

**Activity**
- `id`: Primary key
- `session`: ForeignKey to Session
- `activity_type`: Activity type (0-4)
- `process_name`: Application name
- `window_title`: Window title
- `details`: Additional information
- `start_time`: Activity start
- `end_time`: Activity end
- `duration`: Duration in seconds

**ApplicationUsageStats**
- `id`: Primary key
- `user`: ForeignKey to User
- `process_name`: Application name
- `date`: Date of usage
- `total_duration`: Total time in seconds
- `switch_count`: Number of switches

## 🔧 Configuration

### Environment Variables (.env file)

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Debug mode | `True` |
| `SECRET_KEY` | Django secret key | Auto-generated |
| `ALLOWED_HOSTS` | Allowed host names | `localhost,127.0.0.1` |
| `DB_ENGINE` | Database engine | `django.db.backends.sqlite3` |
| `DB_NAME` | Database name | `db.sqlite3` |

## 🔒 Security

### Production Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `DEBUG=False`
- [ ] Update `ALLOWED_HOSTS` with your domain
- [ ] Use strong database passwords
- [ ] Enable HTTPS
- [ ] Configure firewall rules
- [ ] Set up regular backups
- [ ] Review CORS settings
- [ ] Enable API authentication
- [ ] Set up logging and monitoring

### Generating Secret Key

```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

## 📦 Project Structure

```
employee-monitoring-backend/
├── .venv/                   # Virtual environment (created by setup.bat)
├── monitoring_system/       # Django project settings
│   ├── settings.py          # Configuration
│   ├── urls.py              # URL routing
│   └── wsgi.py              # WSGI application
├── tracker_api/             # Main API application
│   ├── models.py            # Database models
│   ├── serializers.py       # API serializers
│   ├── views.py             # API views
│   └── urls.py              # API routes
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
├── .env.example             # Environment template
├── setup.bat                # Setup script
├── run_server.bat           # Run development server
└── manage.py                # Django CLI
```

## 🧪 Testing

```bash
# Activate virtual environment first
.venv\Scripts\activate.bat

# Run all tests
python manage.py test

# Run specific test
python manage.py test tracker_api.tests.TestUploadAPI

# Check code coverage (install coverage first: pip install coverage)
coverage run --source='.' manage.py test
coverage report
```

## 🐛 Troubleshooting

### Virtual Environment Not Found

```bash
# Run setup script
setup.bat

# Or create manually
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

### Migrations Not Applied

```bash
# Activate virtual environment
.venv\Scripts\activate.bat

# Create and apply migrations
python manage.py makemigrations
python manage.py migrate
```

### Database Issues

```bash
# Reset SQLite database (⚠️ data loss)
# 1. Delete db.sqlite3 file
# 2. Run migrations again
python manage.py migrate

# Create new superuser
python manage.py createsuperuser
```

### Port Already in Use

```bash
# Find process using port 8000
# Windows
netstat -ano | findstr :8000

# Kill the process or change port
python manage.py runserver 8001
```

### Import Errors After Updates

```bash
# Reinstall dependencies
.venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
```

## 💾 Backup and Restore

### Backup SQLite Database

```bash
# Simply copy the database file
copy db.sqlite3 backup_db.sqlite3

# Or with timestamp
copy db.sqlite3 backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%.sqlite3
```

### Restore Database

```bash
# Restore from backup
copy backup_db.sqlite3 db.sqlite3
```

## 🚀 Deployment

### Prepare for Production

1. **Update .env file:**
   ```ini
   DEBUG=False
   SECRET_KEY=your-strong-secret-key-here
   ALLOWED_HOSTS=your-domain.com
   ```

2. **Consider using PostgreSQL** instead of SQLite for production

3. **Use a production server** like Gunicorn:
   ```bash
   pip install gunicorn
   gunicorn monitoring_system.wsgi:application --bind 0.0.0.0:8000
   ```

4. **Set up a reverse proxy** (Nginx/Apache)

5. **Enable HTTPS** with Let's Encrypt

### Deploy to Cloud

- **Heroku**: Add Procfile and use PostgreSQL add-on
- **PythonAnywhere**: Upload project and configure WSGI
- **AWS/Azure/GCP**: Use their Django hosting services
- Always use environment variables for sensitive configuration

## 📞 Support

For issues or questions:
- Review error messages in console
- Check `.env` configuration
- Verify virtual environment is activated
- Run `python manage.py check` to diagnose issues

---

**Happy coding!** 🎉

Start with: `setup.bat` then `run_server.bat`
