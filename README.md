# Bentley Library

Bentley Library is a student-first library platform built for Bentley School. It combines fast catalog search, copy-level circulation, grounded AI recommendations, and a modern web experience that feels more like a great campus product than a traditional OPAC.

## 🌟 Highlights

- Fast PostgreSQL-backed catalog search with GIN-indexed full-text retrieval
- Copy-level circulation, holds, and account workflows for a 400+ student school community
- Grounded AI recommendations for reading and research, tied to books actually in the catalog
- Real-book metadata flows including ISBN lookup, cover enrichment, and availability-aware discovery
- Django backend with a Go reranking service for low-latency recommendation scoring

## ℹ️ Overview

Bentley Library is a web app for students who want to find the right book quickly, understand whether it is available, and take action without fighting an admin-heavy interface. The product supports catalog search, holds, checkout workflows, account dashboards, staff circulation tools, and an AI-assisted recommendation flow grounded in the actual library database.

This project was built by Patrick Liu as a more thoughtful alternative to generic open source library software. The focus is simple: make discovery faster, borrowing clearer, and the overall experience feel like software students would actually want to use.

### Who it is for

- Students looking for class books, research sources, or something good to read next
- Librarians and staff managing circulation and inventory
- Engineers interested in search, retrieval, and AI-grounded product design

### What makes it different

- Student-first UX instead of a librarian-first dashboard
- Search and recommendations grounded in the live catalog
- Support for reading mode and research mode
- School-specific workflows like holds, copy-level availability, and account-driven discovery

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

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

Things to try:

- Search by title, author, topic, or ISBN
- Switch between reading mode and research mode
- Place a hold from a book page
- Use the ISBN lookup flow
- Open the AI library concierge and ask for a recommendation

## ⬇️ Installation

Minimum requirements:

- Python 3.11+
- SQLite for the default local setup, or PostgreSQL for the full search stack
- Optional Go install if you want to run the reranker locally

Minimal local configuration:

```env
SECRET_KEY=replace-with-a-long-random-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,testserver
DB_ENGINE=sqlite
```

For PostgreSQL, use either:

- `DATABASE_URL=postgresql://...`
- or `DB_ENGINE=postgresql` plus `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`

## 🤖 AI + Search

Bentley Library uses a grounded recommendation flow rather than freeform chat:

1. interpret a student prompt
2. retrieve matching books from the catalog
3. rerank results for relevance and availability
4. explain why the recommendation fits

The app supports:

- a local open-weight model through an OpenAI-compatible endpoint
- Gemini via `GEMINI_API_KEY`
- a Go reranker for low-latency scoring

Example local model configuration:

```env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_API_KEY=local-dev-key
LLM_MODEL=gpt-oss-20b
```

Run the optional Go reranker:

```bash
cd BentleyLibrary/services/go-ranker
go run .
```

## 🔐 Authentication

Bentley Library uses Django authentication by default and supports Auth0 as a server-side OIDC login flow. After Auth0 sign-in, Django sessions remain the source of truth for the web app.

Enable Auth0 with:

```env
AUTH0_ENABLED=True
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
```

In Auth0, register:

```text
Application Login URI:
http://127.0.0.1:8000/accounts/login/

Allowed Callback URLs:
http://127.0.0.1:8000/accounts/auth0/callback/

Allowed Logout URLs:
http://127.0.0.1:8000/

Allowed Web Origins:
http://127.0.0.1:8000
```

Notes:

- `next` redirects are sanitized before login and after callback.
- Auth0 login creates or updates the local Django user and library profile on first sign-in.
- Use a Regular Web Application in Auth0 for this Django setup.

## 🧪 Useful Commands

Run tests:

```bash
cd BentleyLibrary
python manage.py test core.tests --settings=BentleyLibrary.test_settings
```

Seed demo data:

```bash
cd BentleyLibrary
python manage.py seed_demo_library --books 1000 --users 40 --loans 300 --holds 120 --wipe-existing
```

Import real books:

```bash
cd BentleyLibrary
python manage.py import_real_books --per-topic 15
```

Benchmark search:

```bash
cd BentleyLibrary
python manage.py benchmark_postgres_search --query python --query history --runs 10
python manage.py evaluate_search
```

## 📁 Repo Layout

- [`BentleyLibrary/`](/Users/patliu/Desktop/Coding/BL/BentleyLibrary): Django app, templates, services, search, and docs
- [`BentleyLibrary/services/go-ranker/`](/Users/patliu/Desktop/Coding/BL/BentleyLibrary/services/go-ranker): Go reranking service
- [`BentleyLibrary/docs/`](/Users/patliu/Desktop/Coding/BL/BentleyLibrary/docs): deployment and supporting notes

## 💬 Feedback and Contributions

If you spot a broken flow, a search relevance issue, or a UX problem, open an issue or start a discussion. Good feedback for this project usually looks like:

- a query that should have returned something better
- a confusing student workflow
- a staff workflow that is too slow or awkward
- an idea for making the library feel more useful for Bentley students

## 👤 Author

Built by Patrick Liu.
