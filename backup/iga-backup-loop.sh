#!/bin/sh
# The "backup" service's loop: a backup when the volume has none yet, then one every day at BACKUP_TIME (HH:MM,
# the container's time zone, TZ). A failed backup is reported and retried at the next time; the service's
# healthcheck turns unhealthy when the newest backup is more than a day old (docs/DEPLOYMENT.md, "Monitoring").
set -u

BACKUP_TIME="${BACKUP_TIME:-02:30}"
case "$BACKUP_TIME" in
  [0-2][0-9]:[0-5][0-9]) ;;
  *) echo "BACKUP_TIME must be HH:MM, for example 02:30" >&2; exit 2 ;;
esac

if ! ls "${BACKUP_DIR:-/backups}"/db/iga-*.dump > /dev/null 2>&1; then
  # Wait for the database, then take the first backup straight away.
  until pg_isready -q; do sleep 5; done
  iga-backup || echo "$(date -Iseconds) backup FAILED" >&2
fi

while true; do
  now="$(date +%s)"
  next="$(date -d "$(date +%Y-%m-%d) $BACKUP_TIME" +%s)"
  [ "$next" -gt "$now" ] || next=$((next + 86400))
  echo "$(date -Iseconds) next backup at $(date -d "@$next" -Iseconds)"
  sleep $((next - now))
  iga-backup || echo "$(date -Iseconds) backup FAILED" >&2
done
