#!/usr/bin/env bash
# Startet den Hintergrund-Download für den Layer Nachtlicht (VNP46A3),
# Zeitraum 2013-01 bis 2025-12 (Entscheidung E3).
#
# Reihenfolge (Entscheidung 2026-09-23): zuerst 2018-01 bis 2025-12, danach
# 2013-01 bis 2017-12. Bricht der Lauf ab oder greift die NASA-Frist
# (1.11.2026) früher, liegen so bereits acht vollständige Jahre vor. Ein
# neuer Aufruf setzt bei den noch offenen Monaten in derselben Reihenfolge fort.
#
# Vorrang (Auftrag 2026-09-25): Davor kommen 2018-01 bis 2019-12 und 2024-01
# (in dieser Reihenfolge). Diese Monate waren mit abgeschnittener Kachelabfrage
# geladen und werden vollständig neu geladen; nach 2018 liegt so zuerst ein
# vollständiges Jahr für die erste Auswertung vor.
#
# Region zuerst (Auftrag 2026-09-26): Weil die Hochrechnung den 1.11.2026 nicht
# sicher einhält, wird zweistufig geladen: erst für ALLE offenen Monate nur die
# 188 Kacheln mit Land in Afrika, Europa oder Asien (Zustand 4 im Würfel), danach
# die übrigen Kacheln (Zustand 1). Es wird nichts weggelassen.
# Kachelliste: aleph/layers/vnp46a3_kacheln_afrika_europa_asien.txt
#
# Zahl gleichzeitiger Kachel-Downloads einstellbar über das erste Argument
# (Standard 5 seit 2026-09-26: gemessen 1 = 1,69 MB/s, 3 = 2,06 MB/s,
# 5 = 2,31 MB/s, je 5 Minuten ohne Fehler; die Leitung bremst, mehr als 5 bringt
# kaum etwas). Bei erneuten Hängern eine kleinere Zahl probieren, z. B.:
#   scripts/vnp46a3_start.sh 3
#
# Läuft weiter, auch wenn dieses Terminal-Fenster geschlossen wird
# (nohup) und hält den Mac wach, bis er fertig ist (caffeinate).
# Details laufen ins Protokoll auf der SSD; Status prüfen mit
# scripts/vnp46a3_status.sh.

set -euo pipefail
cd "$(dirname "$0")/.."

GLEICHZEITIG="${1:-5}"

# Doppelstart-Sperre: zwei Läufe würden dieselben Monate laden und sich beim
# Löschen der Rohdaten in die Quere kommen.
LAUFENDE="$(pgrep -f '^[^ ]*python[^ ]* -m aleph[.]layers[.]vnp46a3_lauf' || true)"
if [ -n "$LAUFENDE" ]; then
  echo "ABGEBROCHEN: Es läuft bereits ein Lauf (Prozess-Nummer: $(echo $LAUFENDE | tr '\n' ' '))."
  echo "Status prüfen mit: scripts/vnp46a3_status.sh"
  exit 1
fi

mkdir -p logs
nohup caffeinate -ims .venv/bin/python -m aleph.layers.vnp46a3_lauf \
  --start 2013-01 --ende 2025-12 --zuerst-ab 2018-01 --vorrang 2018-01..2019-12,2024-01 \
  --gleichzeitig "$GLEICHZEITIG" --region-zuerst afrika_europa_asien \
  > logs/vnp46a3_absturz.log 2>&1 &
disown

echo "Gestartet (Prozess-Nummer $!), gleichzeitige Downloads: $GLEICHZEITIG."
echo "Status prüfen mit: scripts/vnp46a3_status.sh"
