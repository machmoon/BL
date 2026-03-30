# Bentley Library

A student-first library platform for Bentley School with fast catalog search, copy-level circulation, grounded AI recommendations, and real-book metadata.

## Stack

- Python
- Django
- PostgreSQL or SQLite
- Optional Gemini-powered intent extraction
- Optional Go reranking service for low-latency recommendation scoring

## What Makes It Different

- Course-aware discovery instead of generic OPAC-style search
- ISBN lookup with real cover and metadata enrichment
- Student-facing recommendation flow grounded in the actual catalog
- Custom Bentley-style homepage with availability, demand, and research-oriented entry points
- Copy-level holds and circulation, not just title-level inventory

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

Run the Go reranker:

```bash
cd services/go-ranker
go run .
```

Import a real catalog:

```bash
python manage.py import_real_books --per-topic 15
```

## Notes

- Django migrations are the source of truth for the schema.
- PostgreSQL is the recommended production target.
- `.env` is required and should never be committed.
- The AI concierge uses a grounded flow: LLM query interpretation -> catalog retrieval -> Go/Python reranking.
- Set `GEMINI_API_KEY` locally if you want the Gemini-enhanced path; otherwise the app falls back to the built-in local guide.
