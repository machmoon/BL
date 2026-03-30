# Bentley Library

A student-first library platform for Bentley School with fast catalog search, copy-level circulation, grounded AI recommendations, and real book metadata.

## 🌟 Highlights

- Student-friendly discovery instead of a generic, admin-heavy catalog
- PostgreSQL-backed search with indexed retrieval and full-text search benchmarking
- Copy-level circulation, holds, and account workflows
- ISBN lookup with live metadata and cover enrichment
- Grounded AI recommendations tied to books actually in the catalog
- Reading mode and research mode for different student goals

## ℹ️ Overview

Bentley Library is a web app designed to feel more like a great student product than a dusty library system. Students can search by title, author, ISBN, and topic, place holds, check availability, manage their account, and get grounded recommendations that only surface books the library actually has.

This project was built by Patrick Liu as a modern, school-specific alternative to one-size-fits-all open source library software. The focus is on student usability: faster discovery, clearer borrowing flows, and a cleaner interface for research and independent reading.

### Who it is for

- Students who need to find a class book quickly
- Librarians and staff managing circulation
- Anyone who wants a more modern library UX than a traditional OPAC

### What makes it different

- Course-aware search and discovery
- Real metadata instead of obviously fake seed data
- AI features grounded in the catalog rather than freeform chat
- Separate student and staff experiences

## 🚀 Usage

Run the app locally:

```bash
cd BentleyLibrary
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

Useful things to try:

- Search for a title, author, or ISBN
- Switch between reading mode and research mode
- Use the ISBN lookup panel on the homepage
- Open a title page and place a hold
- Log in and view the account dashboard

## ⬇️ Installation Notes

Minimum setup for local development:

```env
SECRET_KEY=replace-with-a-long-random-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,testserver
DB_ENGINE=sqlite
```

You can also use PostgreSQL with either:

- `DATABASE_URL=postgresql://...`
- or `DB_ENGINE=postgresql` plus `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`

## 🤖 AI Features

The AI concierge uses a grounded flow:

1. interpret student intent
2. retrieve matching books from the catalog
3. rerank results for relevance and availability
4. explain why the recommendation fits

You can use either:

- a local open-weight model through an OpenAI-compatible endpoint
- Gemini via `GEMINI_API_KEY`

Example local open-model config:

```env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_API_KEY=local-dev-key
LLM_MODEL=gpt-oss-20b
```

Optional Go reranker:

```bash
cd services/go-ranker
go run .
```

## 🧱 Architecture

The app is organized around a few core layers:

- `core/presenters/` for book and UI-facing presentation logic
- `core/services/` for homepage assembly and product event logging
- `core/discovery/` for search orchestration
- `core/search.py` for lexical/full-text retrieval primitives

This keeps the Django views thinner and makes search, homepage curation, and analytics easier to evolve independently.

## 🧪 Useful Commands

Run tests:

```bash
python manage.py test core.tests --settings=BentleyLibrary.test_settings
```

Seed demo data:

```bash
python manage.py seed_demo_library --books 1000 --users 40 --loans 300 --holds 120 --wipe-existing
```

Import real books:

```bash
python manage.py import_real_books --per-topic 15
```

Benchmark search:

```bash
python manage.py benchmark_search --query python --query history --query science
python manage.py benchmark_postgres_search --query python --query history --runs 10
python manage.py evaluate_search
```

## 📦 Deployment

This repo is set up for:

- Fly.io for the Django app
- Neon for PostgreSQL

Example deploy flow:

```bash
fly secrets set \
  SECRET_KEY=replace-me \
  DATABASE_URL=postgresql://... \
  ALLOWED_HOSTS=bentley-library.fly.dev \
  CSRF_TRUSTED_ORIGINS=https://bentley-library.fly.dev

fly launch --no-deploy
fly deploy
```

## 👤 Author

Built by Patrick Liu.

## 💬 Feedback

If you want to improve the product, open an issue or start a discussion with:

- broken workflows
- search relevance problems
- UI/UX suggestions
- ideas for better student or librarian features
