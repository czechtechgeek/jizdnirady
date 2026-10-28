#!/bin/sh
set -e

cd /app

log() { echo "[jizdnirady] $*"; }

if [ ! -f /data/commute.json ]; then
  log "Kopíruji výchozí commute.json do /data"
  cp /app/commute.json /data/commute.json
fi

if [ ! -f "$JIZDNIRADY_DB" ]; then
  log "Databáze chybí — stahuji GTFS (může to trvat několik minut)"
  curl -fL --retry 3 -o /tmp/gtfs.zip "$GTFS_URL"
  log "Stavím databázi..."
  python3 build_db.py /tmp/gtfs.zip "$JIZDNIRADY_DB"
  rm -f /tmp/gtfs.zip
  log "Hotovo"
else
  log "Používám existující databázi $JIZDNIRADY_DB"
fi

log "Spouštím Jablonecké spojení na portu ${PORT}"
exec python3 -u app.py
