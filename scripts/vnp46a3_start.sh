#!/usr/bin/env bash
# Startet den Hintergrund-Download für den Layer Nachtlicht (VNP46A3),
# Zeitraum 2013-01 bis 2025-12 (Entscheidung E3).
#
# Zahl gleichzeitiger Kachel-Downloads einstellbar über das erste Argument
# (Vorschlag 2-4, Standard 3). Bei erneuten Hängern eine kleinere Zahl
# probieren statt zu raten, z. B.:
#   scripts/vnp46a3_start.sh 2
#
# Läuft weiter, auch wenn dieses Terminal-Fenster geschlossen wird
# (nohup) und hält den Mac wach, bis er fertig ist (caffeinate).
# Details laufen ins Protokoll auf der SSD; Status prüfen mit
# scripts/vnp46a3_status.sh.

set -euo pipefail
cd "$(dirname "$0")/.."

GLEICHZEITIG="${1:-3}"

mkdir -p logs
nohup caffeinate -ims .venv/bin/python -m aleph.layers.vnp46a3_lauf \
  --start 2013-01 --ende 2025-12 --gleichzeitig "$GLEICHZEITIG" \
  > logs/vnp46a3_absturz.log 2>&1 &
disown

echo "Gestartet (Prozess-Nummer $!), gleichzeitige Downloads: $GLEICHZEITIG."
echo "Status prüfen mit: scripts/vnp46a3_status.sh"
