from pathlib import Path
from urllib.parse import parse_qs, urlparse

from django.core.exceptions import ImproperlyConfigured
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="")
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY environment variable is required.")

DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = [
    host.strip()
    for host in config("ALLOWED_HOSTS", default="localhost,127.0.0.1,testserver").split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in config("CSRF_TRUSTED_ORIGINS", default="").split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core.apps.CoreConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "BentleyLibrary.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "core" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.library_shell",
            ],
        },
    },
]

WSGI_APPLICATION = "BentleyLibrary.wsgi.application"

# Database engine can be sqlite, postgresql, or mysql.
DB_ENGINE = config("DB_ENGINE", default="sqlite").strip().lower()
DATABASE_URL = config("DATABASE_URL", default="").strip()


def database_config_from_url(database_url):
    parsed = urlparse(database_url)
    engine_map = {
        "postgres": "django.db.backends.postgresql",
        "postgresql": "django.db.backends.postgresql",
        "pgsql": "django.db.backends.postgresql",
        "mysql": "django.db.backends.mysql",
    }
    engine = engine_map.get(parsed.scheme)
    if not engine:
        raise ImproperlyConfigured(
            f"Unsupported DATABASE_URL scheme '{parsed.scheme}'."
        )

    query = parse_qs(parsed.query)
    options = {}
    if "sslmode" in query:
        options["sslmode"] = query["sslmode"][-1]
    if "channel_binding" in query:
        options["channel_binding"] = query["channel_binding"][-1]

    database = {
        "ENGINE": engine,
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
    }
    if options:
        database["OPTIONS"] = options
    return {"default": database}

if DATABASE_URL:
    if DATABASE_URL.startswith(("postgres://", "postgresql://")):
        INSTALLED_APPS.append("django.contrib.postgres")
    DATABASES = database_config_from_url(DATABASE_URL)
elif DB_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
elif DB_ENGINE == "postgresql":
    INSTALLED_APPS.append("django.contrib.postgres")
    DB_NAME = config("DB_NAME", default="bentleylibrary")
    DB_USER = config("DB_USER", default="postgres")
    DB_PASSWORD = config("DB_PASSWORD", default="")
    DB_HOST = config("DB_HOST", default="localhost")
    DB_PORT = config("DB_PORT", default="5432")

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
        }
    }
else:
    DB_NAME = config("DB_NAME")
    DB_USER = config("DB_USER")
    DB_PASSWORD = config("DB_PASSWORD")
    DB_HOST = config("DB_HOST", default="localhost")
    DB_PORT = config("DB_PORT", default="3306")

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_REDIRECT_URL = "account_overview"
LOGOUT_REDIRECT_URL = "index"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

if not DEBUG:
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

GEMINI_API_KEY = config("GEMINI_API_KEY", default="").strip()
GEMINI_MODEL = config("GEMINI_MODEL", default="gemini-2.5-flash").strip()
LLM_PROVIDER = config("LLM_PROVIDER", default="off").strip().lower()
LLM_BASE_URL = config("LLM_BASE_URL", default="http://127.0.0.1:11434/v1").strip()
LLM_API_KEY = config("LLM_API_KEY", default="local-dev-key").strip()
LLM_MODEL = config("LLM_MODEL", default="gpt-oss-20b").strip()
GO_RERANKER_URL = config("GO_RERANKER_URL", default="http://127.0.0.1:8088/rank").strip()

AUTH0_ENABLED = config("AUTH0_ENABLED", default=False, cast=bool)
AUTH0_DOMAIN = config("AUTH0_DOMAIN", default="").strip()
AUTH0_CLIENT_ID = config("AUTH0_CLIENT_ID", default="").strip()
AUTH0_CLIENT_SECRET = config("AUTH0_CLIENT_SECRET", default="").strip()
AUTH0_AUDIENCE = config("AUTH0_AUDIENCE", default="").strip()
AUTH0_SCOPES = config("AUTH0_SCOPES", default="openid profile email").strip()
AUTH0_LOGOUT_REDIRECT_URL = config("AUTH0_LOGOUT_REDIRECT_URL", default="").strip()

if AUTH0_ENABLED:
    if not AUTH0_DOMAIN or not AUTH0_CLIENT_ID:
        raise ImproperlyConfigured(
            "AUTH0_DOMAIN and AUTH0_CLIENT_ID are required when AUTH0_ENABLED is True."
        )
    if not AUTH0_DOMAIN.startswith(("http://", "https://")):
        AUTH0_DOMAIN = f"https://{AUTH0_DOMAIN}"
