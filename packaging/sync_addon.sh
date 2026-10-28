#!/usr/bin/env bash
# Home Assistant staví add-on z adresáře addon/ — ten musí mít vlastní kopii zdrojáků.
# Tenhle skript je znovu vygeneruje z kořene repa (jediný zdroj pravdy).
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$DIR/addon/src"

rm -rf "$SRC"
mkdir -p "$SRC"

cp "$DIR/app.py" "$DIR/transfers.py" "$DIR/build_db.py" "$DIR/report.py" "$DIR/requirements.txt" "$DIR/commute.json" "$SRC/"
cp -r "$DIR/templates" "$DIR/static" "$SRC/"

echo "addon/src synchronizováno:"
ls -1 "$SRC"
