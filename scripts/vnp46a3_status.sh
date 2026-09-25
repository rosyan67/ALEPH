#!/usr/bin/env bash
# Zeigt den Stand des VNP46A3-Hintergrund-Laufs: läuft er, fertige Monate,
# aktueller Monat, Restzeit-Schätzung, letzter Fehler und eine Ampel (OK/ACHTUNG/HÄNGT).

set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python -m aleph.layers.vnp46a3_status
