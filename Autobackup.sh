#!/usr/bin/env bash

set -euo pipefail

: "${DB_NAME:=BentleyLibrary}"
: "${DB_HOST:=localhost}"
: "${DB_USER:?Set DB_USER in your environment before running this script.}"
: "${DB_PASSWORD:?Set DB_PASSWORD in your environment before running this script.}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$SCRIPT_DIR}"

# Get the current date in YYYY-MM-DD format
DATE=$(date +"%Y-%m-%d")

# Set the backup file name
BACKUP_FILE="${BACKUP_DIR}/BentleyLibraryBackup_${DATE}.sql"

# Perform the backup
mysqldump \
  --host="$DB_HOST" \
  --user="$DB_USER" \
  --password="$DB_PASSWORD" \
  "$DB_NAME" > "$BACKUP_FILE"
