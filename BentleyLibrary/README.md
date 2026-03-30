# Bentley Library

A Django library platform for catalog search, copy-level circulation, holds, and role-aware accounts.

## Stack

- Python
- Django
- PostgreSQL or SQLite

## Quick Start

```bash
cd BentleyLibrary
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000`.

## Environment

Use SQLite locally:

```env
SECRET_KEY=replace-with-a-long-random-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,testserver
DB_ENGINE=sqlite
```

Use PostgreSQL with either:

- `DATABASE_URL=postgresql://...`
- or `DB_ENGINE=postgresql` plus `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

## Useful Commands

Run tests:

```bash
python manage.py test core.tests --settings=BentleyLibrary.test_settings
```

Seed demo data:

```bash
python manage.py seed_demo_library --books 1000 --users 40 --loans 300 --holds 120 --wipe-existing
```

Benchmark app-level search:

```bash
python manage.py benchmark_search --query python --query history --query science
```

Benchmark PostgreSQL full-text search:

```bash
python manage.py benchmark_postgres_search --query python --query history --runs 10
```

## Notes

- Django migrations are the source of truth for the schema.
- PostgreSQL is the recommended production target.
- `.env` is required and should never be committed.
