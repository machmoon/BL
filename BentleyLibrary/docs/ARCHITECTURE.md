# BentleyLibrary Architecture

## Overview

BentleyLibrary is a Django-based library management system designed to track book inventory, manage checkouts/checkins, and provide search functionality.

## System Architecture

### Technology Stack
- **Backend**: Django 4.2.1
- **Database**: MySQL (production), SQLite (testing)
- **Python**: 3.13+
- **Dependencies**: python-decouple, mysqlclient

### Project Structure

```
BentleyLibrary/
├── BentleyLibrary/          # Main project settings
│   ├── settings.py          # Configuration
│   ├── urls.py              # URL routing
│   └── test_settings.py     # Test configuration
├── core/                     # Main application
│   ├── models.py            # Data models
│   ├── views.py             # View logic
│   ├── admin.py             # Admin interface
│   ├── tests.py             # Unit tests
│   └── templates/           # HTML templates
├── media/                    # User-uploaded files
│   ├── photos/              # Screenshots/photos
│   └── videos/              # Demo videos
└── docs/                     # Documentation
```

## Database Models

### Bookinventory
- Stores book information (title, author, ISBN, etc.)
- Tracks quantity and available quantity
- `managed = False` (uses existing database table)

### Log
- Tracks all checkout/checkin transactions
- Links to Bookinventory via ForeignKey
- Records borrower information and dates
- `managed = False` (uses existing database table)

## View Architecture

### Checkout Flow
1. User submits checkout form with ISBN
2. System validates input (email, required fields)
3. Uses `select_for_update()` to prevent race conditions
4. Creates Log entry
5. Decrements available_quantity
6. Returns success message

### Checkin Flow
1. User submits ISBN
2. System finds most recent unreturned Log entry
3. Updates Log with return date/time
4. Increments available_quantity
5. Returns success message

### Search Functionality
- Basic search: Searches across title, author, publisher, description, ISBN
- Advanced search: Complex queries with logical operators
- Date range filtering
- Available quantity filtering

## Security Features

1. **Environment Variables**: All secrets stored in `.env`
2. **CSRF Protection**: Enabled via Django middleware
3. **Input Validation**: Email validation, required field checks
4. **Race Condition Protection**: Database transactions with `select_for_update()`
5. **Error Handling**: Comprehensive try/except blocks

## Testing Strategy

- **Unit Tests**: 31 tests covering all view logic
- **Mocking**: Database operations mocked for isolated testing
- **Test Settings**: Separate SQLite database for fast testing
- **Coverage**: Views, validation, error handling, URL routing

## Deployment Considerations

1. Set `DEBUG = False` in production
2. Configure `ALLOWED_HOSTS` with domain name(s)
3. Use strong `SECRET_KEY` from environment
4. Set up proper database credentials
5. Configure static file serving
6. Set up logging for production

