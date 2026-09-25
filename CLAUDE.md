# CLAUDE.md – Verbindliche Regeln für ALEPH

Ziel: Ein überzeugender, funktionierender Prototyp für die NASA Space Apps Challenge (14.–15.11.2026, Berlin). Bewertet wird nach Impact, Creativity, Validity, Relevance und Presentation. Erfolg entsteht durch nachprüfbare Qualität: Keine Aussage wird für die Präsentation übertrieben. Bei Zielkonflikten gilt: lieber weniger, dafür belastbar.

- Vor jeder Änderung ARCHITECTURE.md lesen.
- Keine Annahmen über den Code. Vor jeder Änderung den tatsächlichen Code lesen.
- Bei größeren Änderungen die komplette Datei liefern statt vieler kleiner Patches.
- Nach jeder Änderung einen konkreten Test ausführen und das Ergebnis zeigen.
- Alle Datenquellen nutzen dieselbe Ladelogik.
- Keine scheinpräzisen Scores. Unsicherheit immer ausweisen.
- Jede Aussage trägt eine Evidenzstufe: beobachtet, statistische Assoziation, Modellprojektion oder hypothetisches Szenario.
- Fachliche Angaben aus dem Chat (auch Zahlen, Autoren, DOIs) gelten als unbestätigt, bis sie gegen die Originalquelle geprüft sind. Im Zweifel citation_verified: false.
- Jede Quelle im Theorie-Register trägt `verifiziert_umfang: metadaten | originaltext`. `metadaten` heißt: Autoren, Jahr, Titel, Fundstelle in einem Verzeichnis gesehen; `originaltext` heißt: die inhaltliche Aussage wurde im Volltext gelesen. Aussagen, die in einer Präsentation oder Veröffentlichung verwendet werden, brauchen `verifiziert_umfang: originaltext` (und `citation_verified: true`). Fehlt das, wird die Aussage vorher am Volltext geprüft oder nicht verwendet. Ein Abstract oder eine Zusammenfassung durch ein Hilfsmodell zählt nicht als Volltext.
- Kein unnötiges Deep Learning, keine unnötig komplexe Infrastruktur.
- Fehler explizit erklären statt Workarounds.
- Zugangsdaten nur in .env, niemals im Code.
- Den Inhalt von .env niemals lesen, anzeigen oder ausgeben. Code darf die Werte nur zur Laufzeit laden.
- Nach jeder Arbeitssitzung einen Eintrag in LOG.md.
- Der Nutzer programmiert nicht selbst. Jede Änderung in einfachen Worten erklären.

## Agenten

Die Agenten liegen unter `.claude/agents/`.

- Nach jeder Änderung an Analyse-Code wird `statistik-pruefer` eingesetzt.
- Vor jedem neuen Layer wird `datenquellen-scout` eingesetzt.
- Für jede neue Theorie wird `theorie-kurator` eingesetzt.
- Vor jedem Ergebnis, das ich zu sehen bekomme, wird `plausibilitaets-pruefer` eingesetzt.
- Neue Layer werden mit `layer-bauer` gebaut.
