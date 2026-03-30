# Bentley Library App

This folder contains the Django application, templates, services, management commands, and deployment config for Bentley Library.

For the main project overview, setup guide, and feature summary, see the repo root README:

- [Project README](/Users/patliu/Desktop/Coding/BL/README.md)

Quick local start:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Useful commands:

```bash
python manage.py test core.tests --settings=BentleyLibrary.test_settings
python manage.py seed_demo_library --books 1000 --users 40 --loans 300 --holds 120 --wipe-existing
python manage.py benchmark_postgres_search --query python --query history --runs 10
python manage.py evaluate_search
```
