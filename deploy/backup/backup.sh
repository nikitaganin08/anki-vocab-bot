#!/bin/sh
# Daily SQLite backup: consistent online copy, integrity check, gzip, keep KEEP_DAYS days.
# When ~/.backup-s3.env exists (S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET, optional
# S3_ENDPOINT / S3_REGION) the copy is also uploaded to that S3-compatible bucket (Yandex Object
# Storage by default); an upload failure is reported with a non-zero exit after the local copy.
# Installed on the VPS by the deploy workflow (/opt/anki-vocab-bot/backup/) and run from cron.
set -eu

DB="${DB:-/opt/anki-vocab-bot/backend/data/app.db}"
DIR="${BACKUP_DIR:-$HOME/backups/wordloop}"
KEEP_DAYS="${KEEP_DAYS:-14}"
S3_ENV="${S3_ENV:-$HOME/.backup-s3.env}"

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

if [ -f "$S3_ENV" ]; then
  . "$S3_ENV"
  endpoint="${S3_ENDPOINT:-https://storage.yandexcloud.net}"
  name="$(basename "$out").gz"
  sha="$(sha256sum "$out.gz" | cut -d' ' -f1)"
  # The credentials go through curl's stdin config, not the command line (visible in ps).
  if printf 'user = "%s:%s"\n' "$S3_ACCESS_KEY_ID" "$S3_SECRET_ACCESS_KEY" |
    curl -sS --fail --config - --aws-sigv4 "aws:amz:${S3_REGION:-ru-central1}:s3" \
      -H "x-amz-content-sha256: $sha" -T "$out.gz" "$endpoint/$S3_BUCKET/$name"; then
    echo "off-site copy ok: $S3_BUCKET/$name"
  else
    echo "off-site copy FAILED: $S3_BUCKET/$name" >&2
    exit 1
  fi
else
  echo "off-site copy not configured ($S3_ENV missing)"
fi
