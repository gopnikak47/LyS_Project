#!/bin/sh
set -eu
file=${1:?Usage: restore.sh /backups/lys-TIMESTAMP.dump}
case "$file" in /backups/lys-*.dump) ;; *) echo 'Invalid backup path' >&2; exit 1;; esac
[ "${RESTORE_CONFIRM:-}" = "${PGDATABASE:-}" ] && [ -n "${PGDATABASE:-}" ] || {
  echo 'Set RESTORE_CONFIRM to the target database name after stopping API/workers.' >&2; exit 1;
}
cd /backups
sha256sum -c "$(basename "$file").sha256"
pg_restore --exit-on-error --single-transaction --clean --if-exists --no-owner --dbname="$PGDATABASE" "$file"
echo 'Restore complete. Apply migrations and verify before restarting writers.'
