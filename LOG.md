# LOG

## 2026-09-21

- Projekt neu aufgesetzt.
- Architektur hinzugefügt.
- Entscheidungen E1–E9 in ARCHITECTURE.md als bestätigt eingetragen, Status auf „bestätigt“ gesetzt. Zeitplan auf 7 Wochen gekürzt (Woche 7 und 8 zusammengefasst).
- Woche 7 in ARCHITECTURE.md ausführlicher formuliert (Globus, Suchleiste, alle Filter, Fokusgebiet-Ansicht, Theorie-Status; Challenge-Bezug; stabilisieren, Präsentation vorbereiten).
- Ordner .claude/ ins Repo aufgenommen (Plugin-Einstellungen: feature-dev, frontend-design, context7). Drei Agenten angelegt: statistik-pruefer, datenquellen-scout, theorie-kurator. Abschnitt „Agenten“ in CLAUDE.md ergänzt. .claude/settings.local.json in .gitignore.
- docs/sources/ in die Ordnerstruktur (ARCHITECTURE.md, Abschnitt 11) aufgenommen. NASA-Zugang vorbereitet: Vorlage .env.example (nur Variablennamen EARTHDATA_USERNAME, EARTHDATA_PASSWORD), leere .env lokal angelegt und als ausgeschlossen geprüft. Neue Regel in CLAUDE.md: Inhalt von .env nie lesen, anzeigen oder ausgeben.
- Woche 1, Etappe 1:
  - Umgebung: Python 3.12.14 über uv (per pip installiert) in `.venv/`, Paketliste `requirements.txt` mit festen Versionen. `pyproj` auf 3.7.0 festgelegt, weil es für macOS 12 nur bis dahin fertige Pakete gibt (neuere Versionen wollten sich selbst bauen und scheiterten).
  - Login: `aleph/core/auth.py` (gibt nur „Login geklappt“ oder „Login fehlgeschlagen“ aus). Echter NASA-Login getestet: geklappt. 4 Attrappen-Tests belegen, dass nie ein Wert ausgegeben wird.
  - Speicherwächter: `aleph/core/io.py`, Stopp unter 20 GB frei (Platte hat aktuell 130 GB frei). 5 Tests. Alle 9 Tests bestehen.
  - VNP46A3 ausgemessen (Katalog, exakt): 156 Monate 2013–2025, 84 135 Dateien, 4 108 GB (4,01 TB), pro Monat rund 540 Kacheln, pro Kachel im Mittel etwa 40 MB. Eine Probekachel geladen (26,2 MB, stimmt mit dem Katalog überein) und wieder gelöscht. Eine Kachel = 2400 × 2400 Pixel, 60 × 60 Pixel = eine 0,25°-Zelle, also 40 × 40 Zellen je Kachel.
  - Wichtig: Fehlwerte stehen als −999,9 in der Datei (nicht als NaN) und müssen vor jedem Mittelwert entfernt werden. Ein erster Test ohne Maskierung lieferte deshalb Unsinn und wurde wiederholt.
  - Steckbrief `docs/sources/vnp46a3.md` (Agent datenquellen-scout war in dieser Sitzung nicht geladen, ein allgemeiner Agent hat dessen Anweisungen aus der Datei befolgt). Der Agent hat außerdem einmal Bash benutzt und PDF-Text über den Fremddienst r.jina.ai gelesen; im Projekt hat er nur den Steckbrief geschrieben.
  - Befund, offen: In der Probekachel hat kein gültiger Pixel Quality 0, obwohl `_Num` bis 15 reicht. Die Deutung von Quality als „mehr als 3 Nächte“ passt deshalb nicht zur Messung. Im Steckbrief korrigiert. Vorerst `_Num` und Zahl gültiger Pixel als Datenlage verwenden.
  - NASA-Mitteilung (direkt gelesen): Auslieferung von Suomi-NPP-Produkten endet am 1. November 2026, 13:00 UTC, Datum änderbar. Ob das Archiv bleibt, steht nicht in der Mitteilung. Vorsichtshalber alle benötigten Kacheln vor dem 1. November laden.
  - Noch offen: Ladeplan (Vorschlag steht im Chat, wartet auf Freigabe), Feldwahl NearNadir gegen AllAngle, Auswertung der Fehlwerte nach Land/Wasser.

## 2026-09-22

- Oberflächen-Gerüst (Woche 2, ARCHITECTURE.md Abschnitt 10) in `web/` gebaut, auf eigenem Branch `ui-geruest` in einem eigenen Git-Worktree, getrennt von der parallel laufenden Sitzung auf `main` (SSD, Download-Skript). Plugin `frontend-design` für die Gestaltung genutzt.
- Globus: MapLibre GL JS 5.19.0 über CDN (unpkg, kein Konto/Schlüssel), Globus-Projektion (`projection: {type: 'globe'}`). Als Basiskarte die freien, schlüssellosen Kacheln von EOX Maps genutzt – bewusst die NASA-Black-Marble-Nachtlichtkarte (`blackmarble_3857`) plus Grenzen/Label-Überlagerung (`overlay_3857`), weil Nachtlicht der erste echte ALEPH-Layer ist. Erreichbarkeit beider Kachel-URLs und der MapLibre-CDN-Dateien mit `curl` geprüft (alle 200).
- Suchleiste über Orte (mitgeliefertes Verzeichnis `web/beispieldaten/orte.js`, 59 Einträge, keine externe API), Beispiel-Anomalien und Beispiel-Theorien; Klick fliegt zum Ort bzw. öffnet die Untersuchungsansicht bzw. ein Theorie-Kärtchen.
- Filter: Region, Anomalie-Typ, Zeitraum (Doppel-Schieberegler, monatlich 2013-01 bis 2027-12), Evidenzstufe (Mehrfachauswahl), Mindeststärke (auffällig/stark/extrem), nur Fokusgebiete. Anzeige „N von 18 sichtbar".
- Untersuchungsansicht (rechte Seitenleiste, helles „Dossier" vor dem dunklen Globus): Name, Evidenzstufe, Typ-Sicherheit, Datenlage, Stärke/Richtung, Layer, Fokusgebiet, Platzhalter für Zeitreihe und Nachrichten/ACLED, Verweis auf verknüpfte Theorie.
- 18 Beispiel-Anomalien als GeoJSON (`web/beispieldaten/beispiel_anomalien.js`, Polygone statt Punkte, entspricht „gebiet (Umriss)" aus Abschnitt 7), 5 Beispiel-Theorien aus Abschnitt 8. Alle Felder aus Abschnitt 7 befüllt. Jede Anomalie trägt `beispiel: true`; Badge „Beispieldaten" oben auf der Seite und in jeder Untersuchungsansicht, dauerhaft sichtbar, nicht nur beim Start.
- Kein Server nötig: alle Beispieldaten liegen als `window.ALEPH_...`-Objekte in `.js`-Dateien (kein `fetch()`), `index.html` lässt sich direkt per Doppelklick öffnen. MapLibre und die Kartenkacheln brauchen weiterhin Internet, aber kein Konto.
- Getestet:
  - Syntaxprüfung aller vier `.js`-Dateien und Ausführung der drei Datendateien über `osascript -l JavaScript` (kein `node` auf diesem Rechner installiert): 18 Anomalien, 5 Theorien, 59 Orte geladen, keine Datenfehler (Pflichtfelder vollständig, gültige Werte für Stärke/Evidenzstufe/Typ-Sicherheit/Datenlage, Polygone geschlossen und auf der Erde, Theorie-Verweise lösen auf).
  - Filterlogik aus `app.js` nachgebaut und gegen von Hand gezählte Erwartungswerte geprüft: 9 von 9 Tests bestehen (u. a. Mindeststärke, Region, Evidenzstufe, Zeitraum, Kombination mehrerer Filter).
  - Dabei einen echten Fehler gefunden und behoben: Die Beispiel-Anomalie mit Evidenzstufe „hypothetisches Szenario" liegt 2026 (bewusst in der Zukunft, siehe Abschnitt 2 „Was-wäre-wenn"), der Zeitschieber reichte aber nur bis 2025-12 – sie war dadurch beim Start unsichtbar. Schieberegler-Bereich auf 2013-01 bis 2027-12 erweitert.
  - Lokalen Server gestartet und alle sechs Dateien (`index.html`, `style.css`, `app.js`, drei Datendateien) per `curl` auf Statuscode 200 geprüft.
  - Nicht getestet: echtes Rendern im Browser (kein Browser-Werkzeug in dieser Sitzung verfügbar) – Alexander sollte die Seite einmal selbst öffnen und auf den ersten Blick prüfen, ob der Globus wie erwartet aussieht.
- Branch `ui-geruest` gepusht, `main` nicht angefasst.
