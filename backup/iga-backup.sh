#!/bin/sh
# One backup of Iga's data, run by the "backup" service in docker-compose.yml (every day, see
# iga-backup-loop.sh) or by hand:   docker compose exec backup iga-backup
#
# - The database: pg_dump in PostgreSQL's compressed "custom" format, checked with pg_restore --list, to
#   /backups/db/iga-YYYYMMDD-HHMMSS.dump.
# - Uploaded files (textbooks, past papers, resources): a gzipped tar of the media volume, to
#   /backups/media/media-YYYYMMDD-HHMMSS.tar.gz.
# Each file is written under a temporary name and renamed once complete, so a half-written backup never looks
# like a good one. Backups older than BACKUP_KEEP_DAYS days are then deleted (the newest one always stays).
#
# The dumps hold personal data: keep the volume private and copy it off the server encrypted (docs/DEPLOYMENT.md).
# Fields Iga encrypts (2FA secrets, phone numbers, payment details) stay encrypted in the dump: keep
# FIELD_ENCRYPTION_KEYS safe apart from the backups, or those values can't be read after a restore.
set -eu

: "${PGHOST:?PGHOST}" "${PGUSER:?PGUSER}" "${PGDATABASE:?PGDATABASE}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
MEDIA_DIR="${MEDIA_DIR:-/media}"

case "$KEEP_DAYS" in
  '' | *[!0-9]*) echo "BACKUP_KEEP_DAYS must be a whole number of days" >&2; exit 2 ;;
esac
[ "$KEEP_DAYS" -ge 1 ] || { echo "BACKUP_KEEP_DAYS must be at least 1" >&2; exit 2; }

stamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR/db" "$BACKUP_DIR/media"
umask 077

dump="$BACKUP_DIR/db/iga-$stamp.dump"
pg_dump --format=custom --compress=9 --file="$dump.partial" "$PGDATABASE"
pg_restore --list "$dump.partial" > /dev/null  # a readable archive, or this run fails
mv "$dump.partial" "$dump"
echo "$(date -Iseconds) database backup: $dump ($(du -h "$dump" | cut -f1))"

if [ -d "$MEDIA_DIR" ]; then
  archive="$BACKUP_DIR/media/media-$stamp.tar.gz"
  tar -czf "$archive.partial" -C "$MEDIA_DIR" .
  mv "$archive.partial" "$archive"
  echo "$(date -Iseconds) files backup: $archive ($(du -h "$archive" | cut -f1))"
fi

# Older than KEEP_DAYS days (find counts whole days: +N is "N+1 days or more").
find "$BACKUP_DIR/db" -name 'iga-*.dump' -type f -mtime +"$((KEEP_DAYS - 1))" ! -name "iga-$stamp.dump" -print -delete
find "$BACKUP_DIR/media" -name 'media-*.tar.gz' -type f -mtime +"$((KEEP_DAYS - 1))" ! -name "media-$stamp.tar.gz" -print -delete
find "$BACKUP_DIR" -name '*.partial' -type f -mmin +60 -delete
