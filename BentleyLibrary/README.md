# BentleyLibrary

A Django-based library management system for tracking book inventory and checkouts.

**Repository**: [https://github.com/machmoon/BL](https://github.com/machmoon/BL)

## Overview

BentleyLibrary is a comprehensive library management system built with Django that allows users to:
- Search and browse book inventory
- Check out and check in books
- Track borrowing history
- Manage book inventory through admin interface

## Quick Start

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the `BentleyLibrary` directory (same level as `manage.py`) with the following variables:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Settings
DB_NAME=BentleyLibrary
DB_USER=root
DB_PASSWORD=your-database-password
DB_HOST=localhost
DB_PORT=3306
```

**Important:** 
- Never commit the `.env` file to version control
- Use a strong, unique `SECRET_KEY` in production
- Set `DEBUG=False` in production
- Update `ALLOWED_HOSTS` with your domain name(s) in production

### 3. Database Setup

Make sure MySQL is running and the database exists:

```sql
CREATE DATABASE BentleyLibrary CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. Run Migrations

```bash
python manage.py migrate
```

### 5. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 6. Run Development Server

```bash
python manage.py runserver
```

## Features

- Book inventory management
- Checkout/checkin system
- Advanced search functionality
- Admin interface with CSV export
- Borrowing history tracking

## Security Notes

- All sensitive credentials are now stored in environment variables
- The `.env` file is excluded from version control via `.gitignore`
- Race conditions in checkout/checkin are prevented using database transactions
- Input validation has been added to prevent invalid data

## Recent Improvements

- ✅ Fixed security vulnerabilities (hardcoded credentials)
- ✅ Added race condition protection for checkout/checkin
- ✅ Fixed checkin logic bugs
- ✅ Added input validation and error handling
- ✅ Improved code quality (removed commented code, fixed imports)
- ✅ Added logging for important operations
- ✅ Fixed template path issues

## Documentation

- [Architecture Documentation](docs/ARCHITECTURE.md)
- [API Documentation](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Test Results](TEST_RESULTS.md)

## Project Structure

```
BentleyLibrary/
├── BentleyLibrary/      # Project settings
├── core/                # Main application
├── media/               # Media files (photos, videos)
├── docs/                # Documentation
└── requirements.txt     # Dependencies
```

## Testing

Run the test suite:
```bash
python manage.py test core.tests --settings=BentleyLibrary.test_settings
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is for educational purposes.

## Notes

- The `Credentials.py` file is deprecated. Use `.env` instead.
- Models are set to `managed = False` - Django won't create/modify these tables automatically
- Make sure to run migrations if you change model definitions

