#!/bin/bash
# Öffnet den ALEPH-Globus in Chrome. Kein Server nötig, keine Zugangsdaten.
DIR="$(cd "$(dirname "$0")" && pwd)"
open -a "Google Chrome" "$DIR/web/globus.html" || open "$DIR/web/globus.html"
