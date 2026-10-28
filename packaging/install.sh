#!/usr/bin/env bash
# Instalace jako uživatelská systemd služba (Linux, systemd --user).
# Použití:  ./packaging/install.sh [port]
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${1:-8099}"
UNIT_DIR="$HOME/.config/systemd/user"

echo "==> Python závislosti"
python3 -m pip install --user -r "$DIR/requirements.txt"

echo "==> Databáze"
if [ ! -f "$DIR/jizdnirady.db" ]; then
  echo "    jizdnirady.db chybí — stahuji GTFS a stavím databázi"
  "$DIR/packaging/fetch_gtfs.sh"
else
  echo "    jizdnirady.db už existuje, přeskakuji"
fi

echo "==> Systemd unit"
mkdir -p "$UNIT_DIR"
sed "s/Environment=PORT=.*/Environment=PORT=$PORT/" \
  "$DIR/packaging/jizdnirady.service" > "$UNIT_DIR/jizdnirady.service"

systemctl --user daemon-reload
systemctl --user enable --now jizdnirady.service
sleep 1
systemctl --user --no-pager status jizdnirady.service | head -5

echo
echo "Hotovo: http://$(hostname -I | awk '{print $1}'):$PORT/"
echo "Displej:  http://$(hostname -I | awk '{print $1}'):$PORT/display"
