# 🐳 Docker Quick Start Guide

Get your Employee Monitoring Backend running with Docker in **5 minutes**!

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose

## 🚀 Quick Start

### 1. Navigate to Backend Directory

```bash
cd employee-monitoring-backend
```

### 2. Start Everything with One Command

```bash
docker-compose up -d --build
```

That's it! The backend is now running with PostgreSQL.

## ✅ Verify It's Working

### Check Services Status

```bash
docker-compose ps
```

You should see 3 services running:
- `employee_monitoring_web` (Django)
- `employee_monitoring_db` (PostgreSQL)
- `employee_monitoring_pgadmin` (PgAdmin)

### Test the API

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "ok",
  "database": "connected"
}
```

## 📍 Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **Django API** | http://localhost:8000 | N/A |
| **Admin Panel** | http://localhost:8000/admin | admin / admin123 |
| **PgAdmin** | http://localhost:5050 | See `.env` file |

## 🔑 Default Credentials

**Django Admin:**
- Username: `admin`
- Password: `admin123`

**PgAdmin:**
- Email: `admin@example.com`
- Password: `admin123`

**PostgreSQL:**
- Database: `employee_monitoring`
- User: `monitoring_user`
- Password: `SecurePassword123!`

⚠️ **Change these in production!** Edit `.env` file.

## 🛠️ Common Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Django only
docker-compose logs -f web

# Database only
docker-compose logs -f db
```

### Stop Services

```bash
docker-compose down
```

### Restart Services

```bash
docker-compose restart
```

### Rebuild and Restart

```bash
docker-compose up -d --build
```

### Run Django Commands

```bash
# Create superuser
docker-compose exec web python manage.py createsuperuser

# Run migrations
docker-compose exec web python manage.py migrate

# Access Django shell
docker-compose exec web python manage.py shell
```

### Access Database

```bash
# PostgreSQL shell
docker-compose exec db psql -U monitoring_user -d employee_monitoring

# Via PgAdmin
# Open http://localhost:5050 and add server:
# Host: db
# Port: 5432
# Database: employee_monitoring
# Username: monitoring_user
# Password: SecurePassword123!
```

## 📊 What's Included?

### Django Web Service

- **Gunicorn** WSGI server (3 workers)
- Automatic database migrations
- Auto-created admin user
- Static files collection
- Health check endpoint

### PostgreSQL Database

- **PostgreSQL 16 Alpine**
- Persistent data volume
- Health checks enabled
- Automatic initialization

### PgAdmin

- **Web-based** database management
- Pre-configured for easy access
- Visual query builder
- Database monitoring

## 🔧 Configuration

### Edit Environment Variables

```bash
# Edit .env file
nano .env

# Or on Windows
notepad .env
```

**Important variables:**

```ini
# Change for production!
SECRET_KEY=your-secret-key-here
DB_PASSWORD=your-secure-password
DEBUG=False
ALLOWED_HOSTS=your-domain.com
```

### Apply Configuration Changes

```bash
# Restart services to apply changes
docker-compose down
docker-compose up -d
```

## 📦 Data Persistence

Data is stored in Docker volumes:

```bash
# List volumes
docker volume ls

# Volumes created:
# - employee_monitoring_postgres_data (Database)
# - employee_monitoring_static (Static files)
# - employee_monitoring_media (Uploaded files)
# - employee_monitoring_pgadmin (PgAdmin data)
```

### Backup Database

```bash
docker-compose exec db pg_dump -U monitoring_user employee_monitoring > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
docker-compose exec -T db psql -U monitoring_user employee_monitoring < backup.sql
```

## 🐛 Troubleshooting

### Port Already in Use

**Error:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Fix:**
```bash
# Find and kill process using port 8000
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### Database Connection Failed

**Fix:**
```bash
# Wait for database to be ready
docker-compose logs db

# Restart services
docker-compose restart
```

### Migrations Not Applied

**Fix:**
```bash
# Manually run migrations
docker-compose exec web python manage.py migrate

# Or rebuild
docker-compose down -v  # ⚠️ Deletes data!
docker-compose up -d --build
```

### Permission Denied

**Fix:**
```bash
# Make entrypoint executable
chmod +x entrypoint.sh

# Rebuild
docker-compose up -d --build
```

## 🧹 Clean Up

### Stop and Remove Everything

```bash
# Stop services
docker-compose down

# Remove volumes too (⚠️ deletes all data!)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

### Start Fresh

```bash
docker-compose down -v
docker-compose up -d --build
```

## 🚀 Next Steps

### 1. Test with C++ Client

Update C++ tracker to point to:
```cpp
authManager->setServerUrl("http://localhost:8000");
tracker->setServerUrl("http://localhost:8000/api/upload/");
```

### 2. Create Users

```bash
# Create additional users via Django shell
docker-compose exec web python manage.py shell
```

```python
from django.contrib.auth.models import User
User.objects.create_user('john', 'john@example.com', 'password123')
```

### 3. View Data

- **Admin Panel:** http://localhost:8000/admin
- **PgAdmin:** http://localhost:5050
- **API:** http://localhost:8000/api/

### 4. Deploy to Production

See `README.md` for production deployment guide.

## 📚 Additional Resources

- **Full Documentation:** `README.md`
- **Docker Compose Reference:** https://docs.docker.com/compose/
- **Django Documentation:** https://docs.djangoproject.com/
- **PostgreSQL Documentation:** https://www.postgresql.org/docs/

---

**You're all set!** 🎉

Your Employee Monitoring Backend is now running in Docker with PostgreSQL.
