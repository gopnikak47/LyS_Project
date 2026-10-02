#!/bin/sh
set -eu
umask 077
case "${BACKUP_KEEP:-14}" in ''|*[!0-9]*|0) echo 'Invalid BACKUP_KEEP' >&2; exit 1;; esac
mkdir -p /backups
stamp=$(date -u +%Y%m%dT%H%M%SZ)
target="/backups/lys-${stamp}.dump"
trap 'rm -f "$target.partial"' EXIT
pg_dump --format=custom --no-owner --file="$target.partial"
pg_restore --list "$target.partial" >/dev/null
mv "$target.partial" "$target"
cd /backups
sha256sum "lys-${stamp}.dump" >"lys-${stamp}.dump.sha256"
# Only files created by this script are eligible for retention.
ls -1t lys-*.dump | awk -v keep="${BACKUP_KEEP:-14}" 'NR > keep' | while IFS= read -r old; do
  rm -f "$old" "$old.sha256"
done
echo "Backup complete: $target"
