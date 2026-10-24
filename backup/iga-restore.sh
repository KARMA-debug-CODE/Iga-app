#!/bin/sh
# Restore Iga's database (and, optionally, the uploaded files) from a backup made by iga-backup.sh.
# Run it from the backup service while the app is stopped (docs/DEPLOYMENT.md, "Restore"):
#
#   docker compose stop backend scheduler web
#   docker compose run --rm backup iga-restore /backups/db/iga-20261017-023000.dump
#   docker compose run --rm backup iga-restore --media /backups/media/media-20261017-023000.tar.gz   # optional
#   docker compose up -d      # the migrate service re-applies the database roles and any newer migrations
#
# The database is replaced: it is dropped (closing any connection left), created again empty and filled from
# the dump. Objects are restored without their original owners and grants (--no-owner --no-privileges); the
# migrate service's db_roles then gives them to iga_owner and grants iga_app its rights, as on every start.
set -eu

usage() {
  echo "Usage: iga-restore FILE.dump        replace the database with this backup" >&2
  echo "       iga-restore --media FILE.tar.gz   put these uploaded files back into the media volume" >&2
  exit 2
}

[ $# -ge 1 ] || usage
if [ "$1" = "--media" ]; then
  [ $# -eq 2 ] && [ -f "$2" ] || usage
  MEDIA_DIR="${MEDIA_DIR:-/media}"
  tar -tzf "$2" > /dev/null  # a readable archive, before anything is touched
  find "$MEDIA_DIR" -mindepth 1 -delete
  tar -xzf "$2" -C "$MEDIA_DIR"
  echo "Uploaded files restored from $2."
  exit 0
fi

[ $# -eq 1 ] && [ -f "$1" ] || usage
: "${PGHOST:?PGHOST}" "${PGUSER:?PGUSER}" "${PGDATABASE:?PGDATABASE}"
pg_restore --list "$1" > /dev/null  # a readable archive, before the database is dropped

echo "Replacing database $PGDATABASE on $PGHOST with $1 ..."
dropdb --if-exists --force --maintenance-db=postgres "$PGDATABASE"
createdb --maintenance-db=postgres "$PGDATABASE"
pg_restore --no-owner --no-privileges --exit-on-error --single-transaction --dbname="$PGDATABASE" "$1"
echo "Database restored. Start Iga again with: docker compose up -d"
