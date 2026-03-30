import os

REQUIRED_ENV_VARS = ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME")
missing_vars = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]

if missing_vars:
    raise RuntimeError(
        "Missing required database environment variables: "
        + ", ".join(sorted(missing_vars))
    )

db_config = {
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"],
    "host": os.environ["DB_HOST"],
    "database": os.environ["DB_NAME"],
}

if os.getenv("DB_AUTH_PLUGIN"):
    db_config["auth_plugin"] = os.environ["DB_AUTH_PLUGIN"]
