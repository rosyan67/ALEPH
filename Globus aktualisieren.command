#!/bin/bash
# Holt den neuesten Stand aus dem Nachtlicht-Würfel und der Einheitentabelle
# (SSD muss angeschlossen sein) und öffnet danach den Globus.
# Liest nur; der laufende Download wird nicht angefasst.
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1
echo "ALEPH: Daten für den Globus werden aus Würfel und Einheitentabelle gelesen …"
"$HOME/ALEPH/.venv/bin/python" -m aleph.export.globus
STATUS=$?
if [ $STATUS -ne 0 ]; then
  echo
  echo "Das hat nicht geklappt (siehe Meldung oben). Der Globus zeigt den letzten Stand."
fi
open -a "Google Chrome" "$DIR/web/globus.html" || open "$DIR/web/globus.html"
echo
read -n 1 -s -r -p "Fertig. Taste drücken, um dieses Fenster zu schließen."
