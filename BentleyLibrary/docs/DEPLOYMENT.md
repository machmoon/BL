# Deployment

## Recommended Setup

- Django app server
- PostgreSQL database
- `DATABASE_URL` or `DB_ENGINE=postgresql` config
- `DEBUG=False`
- real `SECRET_KEY`
- correct `ALLOWED_HOSTS`

## Minimal Steps

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic
python manage.py test core.tests --settings=BentleyLibrary.test_settings
```

Run with Gunicorn:

```bash
gunicorn BentleyLibrary.wsgi:application --bind 0.0.0.0:8000
```

## Example Environment

```env
SECRET_KEY=replace-me
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require
```

## Checklist

- set `DEBUG=False`
- set `ALLOWED_HOSTS`
- use PostgreSQL in production
- rotate any previously exposed credentials
- enable HTTPS
- back up the database
- add logging and monitoring
