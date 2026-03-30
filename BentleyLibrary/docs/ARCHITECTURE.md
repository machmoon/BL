# BentleyLibrary Architecture

## Overview

BentleyLibrary is a small Django application centered on one catalog model and one borrowing log model. The codebase is intentionally simple: server-rendered templates, ORM-backed workflows, and no separate API layer.

## Technology Stack

- Backend: Django 4.2.1
- Database: SQLite by default, MySQL optional
- Python: 3.9+
- Dependencies: `python-decouple`, `mysqlclient`

## Application Structure

```text
BentleyLibrary/
├── BentleyLibrary/
│   ├── settings.py
│   ├── test_settings.py
│   └── urls.py
├── core/
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   ├── models.py
│   ├── tests.py
│   ├── views.py
│   └── templates/core/
└── docs/
```

## Data Model

### `Bookinventory`

- Stores catalog metadata and availability counts
- Includes a cover image URL and description
- Uses Django-managed migrations with the `bookinventory` table name

### `Log`

- Records each checkout/checkin event
- Links back to `Bookinventory`
- Tracks borrower identity plus borrow/return timestamps
- Uses Django-managed migrations with the `log` table name

## Request Flow

### Checkout

1. Validate the borrower fields.
2. Lock the selected book row inside a transaction.
3. Reject the request if no copies are available.
4. Create a `Log` row.
5. Decrement `available_quantity`.
6. Redirect to the home page with a success message.

### Checkin

1. Validate the ISBN.
2. Lock the selected book row inside a transaction.
3. Find the latest unreturned `Log` row for that book.
4. Stamp the return date and time.
5. Increment `available_quantity`.
6. Redirect to the home page with a success message.

### Search

- `/search/` acts as both search and browse.
- Free-text queries search across title, author, publisher, description, and ISBN.
- Advanced search uses an allow-list of searchable fields/operators to avoid invalid ORM lookups.

## Template Strategy

- All rendered templates live under `core/templates/core/`.
- Views render templates by their fully-qualified names such as `core/checkout.html`.
- Shared flash messages are rendered from the base template.

## Database Strategy

- Django migrations are the source of truth for schema changes.
- `core/migrations/0004_reconcile_schema.py` reconciles older local states into the current schema.
- SQLite is the default local database for a frictionless setup.
- MySQL remains available when `USE_SQLITE=False`.

## Testing Strategy

- `core/tests.py` uses Django `TestCase` with the real ORM and templates.
- The suite currently contains 25 passing tests.
- Coverage focuses on checkout, checkin, search, advanced search, routing, and graceful error handling.
