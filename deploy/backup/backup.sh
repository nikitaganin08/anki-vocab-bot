#!/bin/sh
# Daily SQLite backup: consistent online copy, integrity check, gzip, keep KEEP_DAYS days.
# Installed on the VPS by the deploy workflow (/opt/anki-vocab-bot/backup/) and run from cron.
set -eu

DB="${DB:-/opt/anki-vocab-bot/backend/data/app.db}"
DIR="${BACKUP_DIR:-$HOME/backups/wordloop}"
KEEP_DAYS="${KEEP_DAYS:-14}"

mkdir -p "$DIR"
out="$DIR/app-$(date +%Y%m%d-%H%M%S).db"

sqlite3 "$DB" ".backup '$out'"
if [ "$(sqlite3 "$out" 'pragma integrity_check')" != "ok" ]; then
  rm -f "$out"
  echo "backup failed: integrity_check" >&2
  exit 1
fi
gzip -f "$out"

find "$DIR" -maxdepth 1 -name 'app-*.db.gz' -mtime +"$KEEP_DAYS" -delete
echo "backup ok: $out.gz ($(du -h "$out.gz" | cut -f1)), kept: $(find "$DIR" -maxdepth 1 -name 'app-*.db.gz' | wc -l)"
