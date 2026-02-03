# Deployment Guide

## Prerequisites

- Python 3.13+
- MySQL 5.7+ or 8.0+
- pip
- Virtual environment (recommended)

## Installation Steps

### 1. Clone Repository
```bash
git clone https://github.com/machmoon/BL.git
cd BL/BentleyLibrary
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the `BentleyLibrary` directory:

```env
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

DB_NAME=BentleyLibrary
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306
```

**Important**: Never commit the `.env` file to version control!

### 5. Database Setup

#### Create MySQL Database
```sql
CREATE DATABASE BentleyLibrary CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### Run Migrations
```bash
python manage.py migrate
```

### 6. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 7. Collect Static Files (Production)
```bash
python manage.py collectstatic
```

## Production Deployment

### Using Gunicorn

1. Install Gunicorn:
```bash
pip install gunicorn
```

2. Run with Gunicorn:
```bash
gunicorn BentleyLibrary.wsgi:application --bind 0.0.0.0:8000
```

### Using Nginx (Recommended)

1. Install Nginx
2. Configure Nginx to proxy to Gunicorn
3. Set up SSL certificates (Let's Encrypt recommended)

### Environment Variables for Production

```env
SECRET_KEY=<generate-strong-secret-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

### Security Checklist

- [ ] Set `DEBUG = False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use strong `SECRET_KEY`
- [ ] Set up HTTPS/SSL
- [ ] Configure database with strong password
- [ ] Set up firewall rules
- [ ] Enable database backups
- [ ] Configure logging
- [ ] Set up monitoring

## Testing

Run tests before deployment:
```bash
python manage.py test core.tests --settings=BentleyLibrary.test_settings
```

## Troubleshooting

### Database Connection Issues
- Verify MySQL is running
- Check database credentials in `.env`
- Ensure database exists
- Check firewall rules

### Static Files Not Loading
- Run `collectstatic`
- Check `STATIC_URL` and `STATIC_ROOT` in settings
- Verify Nginx/Apache static file configuration

### Template Errors
- Verify `TEMPLATES` setting in `settings.py`
- Check template paths are correct
- Ensure templates exist in `core/templates/core/`

## Backup Strategy

1. **Database Backups**: Set up automated MySQL backups
2. **Code Backups**: Use git for version control
3. **Media Backups**: Backup `media/` directory regularly

## Monitoring

- Set up error logging
- Monitor database performance
- Track checkout/checkin activity
- Monitor server resources

