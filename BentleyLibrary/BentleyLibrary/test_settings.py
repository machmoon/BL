"""
Test settings for BentleyLibrary project.
Uses SQLite for faster testing.
"""
from .settings import *
import os

# Use SQLite for testing (faster than MySQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations for managed=False models during tests
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Speed up tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable logging during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

