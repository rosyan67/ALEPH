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
