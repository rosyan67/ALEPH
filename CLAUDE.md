# CLAUDE.md – Verbindliche Regeln für ALEPH

- Vor jeder Änderung ARCHITECTURE.md lesen.
- Keine Annahmen über den Code. Vor jeder Änderung den tatsächlichen Code lesen.
- Bei größeren Änderungen die komplette Datei liefern statt vieler kleiner Patches.
- Nach jeder Änderung einen konkreten Test ausführen und das Ergebnis zeigen.
- Alle Datenquellen nutzen dieselbe Ladelogik.
- Keine scheinpräzisen Scores. Unsicherheit immer ausweisen.
- Jede Aussage trägt eine Evidenzstufe: beobachtet, statistische Assoziation, Modellprojektion oder hypothetisches Szenario.
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
