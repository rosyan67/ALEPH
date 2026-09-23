#!/usr/bin/env bash
# Zeigt den Stand des VNP46A3-Hintergrund-Laufs: fertige Monate,
# Restzeit-Schätzung, letzter Fehler.

set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python -m aleph.layers.vnp46a3_status
