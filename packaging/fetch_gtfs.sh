#!/usr/bin/env bash
# Stáhne GTFS z IDOL/SPOJENKA a přestaví jizdnirady.db.
# user.db (oblíbené a historie) zůstává nedotčená.
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
URL="${GTFS_URL:-https://www.spojenka.cz/jrdata/jizdnirady-gtfs.zip}"

cd "$DIR"
echo "==> Stahuji $URL"
curl -fL --retry 3 -o gtfs.zip.part "$URL"
mv gtfs.zip.part gtfs.zip
ls -lh gtfs.zip

echo "==> Stavím databázi"
python3 build_db.py
echo "==> Hotovo"
