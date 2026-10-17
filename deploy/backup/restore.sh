#!/bin/sh
# Restore app.db from a backup made by backup.sh. Usage: restore.sh <app-....db.gz>
# Stops the app, keeps the current database as app.db.before-restore, starts the app again.
set -eu

BACKUP="${1:?usage: restore.sh <backup.db.gz>}"
APP_DIR="${APP_DIR:-/opt/anki-vocab-bot}"
DB="$APP_DIR/backend/data/app.db"
tmp="$DB.restore-tmp"

gunzip -c "$BACKUP" > "$tmp"
if [ "$(sqlite3 "$tmp" 'pragma integrity_check')" != "ok" ]; then
  rm -f "$tmp"
  echo "refusing to restore: integrity_check failed" >&2
  exit 1
fi

cd "$APP_DIR"
docker compose stop app
mv "$DB" "$DB.before-restore"
rm -f "$DB-wal" "$DB-shm"
mv "$tmp" "$DB"
docker compose start app
echo "restored $BACKUP; previous database kept as $DB.before-restore"
