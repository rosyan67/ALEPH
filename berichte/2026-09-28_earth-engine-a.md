# Earth Engine A: Agenten-Kopfzeilen, Zeitlimit-Regel, engere Anmeldung, Kandidat A

Stand: 2026-09-28 · in Arbeit

## Kurzfassung

(folgt am Ende)

## Urteil

(folgt)

## Belege

### Teil 1a/1b – Agenten (Zwischenstand)

- **Ursache:** Nicht nur `plausibilitaets-pruefer.md`, auch `layer-bauer.md` begann ohne die öffnende Zeile `---`. Die Claude-Code-Doku sagt dazu wörtlich: „An opening `---` that isn't the file's first line: Claude Code reads the file as having no frontmatter and treats it as documentation.“ (https://code.claude.com/docs/en/sub-agents.md, Abschnitt „Subagent files Claude Code skips“, abgerufen 2026-09-28 als Text mit `curl`, selbst gelesen). Beide Agenten fehlten deshalb in der Agentenliste.
- **Modell-Feld laut Doku** (gleiche Seite, „Frontmatter reference“ und „Choose a model“): Feld `model`, gültige Werte `sonnet`, `opus`, `haiku`, `fable`, eine volle Modellkennung oder `inherit`. Wichtig: Ein beim Aufruf mitgegebenes `model` hat Vorrang vor der Datei; deshalb gebe ich beim Aufruf kein Modell mit. Läuft die Hauptsitzung selbst auf Opus, nimmt `opus` genau dieses Modell.
- **Änderung:** je Datei nur die Kopfzeile. Bei zwei Dateien eine Zeile `---` am Anfang, bei allen fünf eine Zeile `model: …`. Der Vergleich mit der Sicherungskopie (`diff`) zeigt keine weitere Änderung; die Rollenbeschreibungen sind unverändert.

| Agent | Modell (`model:`) | vorher erkannt | jetzt erkannt |
|---|---|---|---|
| statistik-pruefer | opus | ja | ja |
| plausibilitaets-pruefer | opus | **nein** | ja |
| datenquellen-scout | sonnet | ja | ja |
| layer-bauer | sonnet | **nein** | ja |
| theorie-kurator | sonnet | ja | ja |

- **Test:**
  - `claude plugin validate .claude/agents` (Claude Code 2.1.283) → „✔ Validation passed“.
  - Eine frische, kurze Claude-Code-Sitzung im Projekt (`claude -p`, ohne Werkzeuge) nennt als verfügbare eigene Agenten genau: datenquellen-scout, layer-bauer, plausibilitaets-pruefer, statistik-pruefer, theorie-kurator.
  - Nicht direkt gemessen: welches Modell ein Agent beim Lauf tatsächlich benutzt. Belegt sind nur Datei und Doku.

### Teil 2 – Netzwerkregel (Zwischenstand)

- **CLAUDE.md:** Regel „Netzwerk“ wörtlich eingetragen (vor „Zeiträume“).
- **Bestandsaufnahme** aller Serverzugriffe im Code, durch Lesen des Codes und des Bibliothekscodes in `.venv` (nicht durch künstliche Hänger an echten Servern):

| Zugriff | Datei | Zeitlimit vorher | Wiederholung vorher | gemeldet vorher | jetzt |
|---|---|---|---|---|---|
| Weltbank-API | `aleph/layers/weltbank.py` | 60 s | 4 Versuche, Pausen 5/10/20 s | nein | Meldung je Wiederholung, Begründung an den Konstanten |
| Natural Earth | `aleph/layers/natural_earth.py` | 120 s | 4 Versuche, 5/10/20 s | nein | wie Weltbank, 1 neuer Test |
| UN M49 | `aleph/layers/un_m49.py` | 120 s | 4 Versuche, 5/10/20 s | nein | wie Weltbank |
| Unpaywall | `aleph/core/unpaywall.py` | 30 s | **keine** | – | 3 Versuche, Pausen 5/15 s, nur bei Netzfehler, HTTP 429 oder 5xx; Meldung ohne Adresse; 3 neue Tests |
| Earth Engine, Start (`ee.Initialize`) | `aleph/core/earth_engine.py` | **keins** | **keine** | – | 120 s je Versuch, 4 Versuche mit 10/30/60 s bei Netzfehler/Zeitüberschreitung, sofortiger Abbruch bei Ablehnung; 4 neue Tests |
| Earth Engine, Anfragen danach (`getInfo` u. a.) | `aleph/core/earth_engine.py` | **keins** (Bibliothek: `deadline_ms = 0` heißt „kein Limit“, `ee/_state.py`) | Bibliothek selbst: 5 bei HTTP 429/5xx | Bibliothek | Standard 300 s, Wiederholungen ausdrücklich 5 |
| Earth Engine, Blöcke (`computePixels`) | `aleph/quellenvergleich/ee_nachtlicht.py` | 600 s (seit 27.09.) | 4 Versuche, 5/10/20 s, als nackte Zahlen | nur gezählt | Konstanten `BLOCK_VERSUCHE`, `BLOCK_PAUSE_BASIS_SEKUNDEN` mit Begründung, Meldung je Wiederholung; 1 neuer Test |
| NASA-Anmeldung | `aleph/core/auth.py` | 120 s | 1–30 min wachsend, dann bis 12 h | ja | erfüllt; **nicht angefasst** (vom Download benutzt) |
| NASA-Kacheln | `aleph/layers/vnp46a3.py` | 10 min+ je Kachel, Stillstand 30 min, Notbremse 12 h | ja | ja | erfüllt; gesperrt |
| **NASA-Katalogabfrage** (`_katalog_abfrage`: `hits()` und Seiten) | `aleph/layers/vnp46a3.py` → earthaccess 0.19.0 `search.py` Z. 458, `utils/_search.py` Z. 37 | **keins** (`session.get` ohne `timeout=`) | keine eigene | – | **nur Empfehlung** (gesperrte Datei). Der Stillstands-Wächter greift erst beim Laden der Kacheln, nicht bei der Katalogabfrage (nach Codelesen, nicht mit einem Hänger getestet). |
| **GPM IMERG** (`search_data`, `download`) | `aleph/layers/gpm_imerg.py` | **keins**; `future.result(timeout=120)` steht hinter `as_completed` und wirkt deshalb nie | keine | nein, Fehler werden still verschluckt (`except …: pass`) | **nur Empfehlung**: Das Modul hat weitere offensichtliche Fehler (z. B. wird der 12. statt des Monatsendes als Enddatum gebaut). Kein kleiner, sicherer Eingriff; neu bauen mit `layer-bauer`. |

- Sonstige: `earthengine authenticate` ist ein Befehl, den der Nutzer von Hand ausführt (kein Code im Repo). Weitere Netzzugriffe im Code gibt es nicht (Suche nach `requests`, `urllib`, `earthaccess`, `ee.` in `aleph/` und `scripts/`; in `scripts/` keiner).
- **Tests nach Teil 2:** `tests/test_unpaywall.py`, `test_natural_earth.py`, `test_weltbank.py`, `test_un_m49.py`, `test_earth_engine.py`, `test_quellenvergleich_ee.py` → alle grün (37 + 8 + 19 sowie Weltbank/M49; Zahlen siehe Gesamtlauf am Ende).

### Teil 3 – Earth-Engine-Anmeldung mit engeren Rechten (Zwischenstand 09:30 UTC)

- **Welche Rechte nötig sind, belegt an der offiziellen REST-Referenz** (developers.google.com/earth-engine/reference/rest/v1/…, abgerufen 2026-09-28 als HTML, Text selbst gelesen, Seitenstand „Last updated 2025-03-06“). Jede der drei Methoden, die ALEPH benutzt, „Requires one of the following OAuth scopes: …/auth/earthengine, …/auth/earthengine.readonly, …/auth/cloud-platform, …/auth/cloud-platform.read-only“:
  - `projects.algorithms/list` (braucht `ee.Initialize` zum Start),
  - `projects.value/compute` (`getInfo`),
  - `projects.image/computePixels` (Herunterladen der Zellwerte; das Ergebnis kommt direkt in der Antwort, ohne Umweg über Drive oder Cloud Storage).
  - Das kleinste Recht ist damit **`https://www.googleapis.com/auth/earthengine.readonly`**. Es erlaubt kein Schreiben (keine eigenen Assets, kein Export nach Drive/Cloud Storage); das braucht ALEPH nicht.
- **Leitfaden** (developers.google.com/earth-engine/guides/auth, „Last updated 2025-01-09“): Standard sind die Rechte „earthengine, cloud-platform, and drive“ „or the scopes in the scopes argument“. Die Bibliothek (`ee/oauth.py`, `earthengine-api` 1.7.45) nimmt standardmäßig zusätzlich `devstorage.full_control`; sie speichert die gewählten Rechte in der Anmeldedatei und prüft beim Start keine weiteren (im Bibliothekscode gelesen).
- **Alte Anmeldedaten entfernt:**
  - Die alte Datei hatte vier Rechte: `earthengine`, `cloud-platform`, `drive`, `devstorage.full_control` (nur die Liste der Rechte angesehen, nicht das Token).
  - Das alte Token wurde bei Google **widerrufen** (`https://oauth2.googleapis.com/revoke`, Antwort HTTP 200), denn nur die Datei zu löschen hätte es bei Google gültig gelassen. Danach Datei gelöscht.
  - Andere Google-Anmeldedaten gibt es auf dem Rechner nicht (`~/.config/gcloud/` existiert nicht, `gcloud` ist nicht installiert).
- **Neue Anmeldung:** `earthengine authenticate --auth_mode=localhost --scopes=https://www.googleapis.com/auth/earthengine.readonly --force`, im Browser vom Nutzer bestätigt (09:26 UTC).
  - Zwei Anläufe davor scheiterten nur an der Zeit: Der erste lief 15 min ohne Bestätigung ab. Beim zweiten lagen gut vier Stunden zwischen Start und Klick; der Prozess hatte nach 30 min aufgegeben, daher „localhost hat die Verbindung abgelehnt“.
  - Neue Datei `~/.config/earthengine/credentials` (Rechte `-rw-------`), gespeicherte Rechte: nur `earthengine.readonly`.
- **Tests:**
  - Google selbst bestätigt die erteilten Rechte (`oauth2.googleapis.com/tokeninfo`, das Token wurde nicht ausgegeben): „https://www.googleapis.com/auth/earthengine.readonly“, sonst nichts. Kein Zugriff auf Google Drive.
  - Mini-Test `.venv/bin/python -m aleph.core.earth_engine` → „Earth Engine verbunden. Test 1+1 = 2; VCMCFG-Bilder für 2018-10: 1“.
  - Herunterladen: ein Block von B (10–20° O, 50–60° N, 40 × 40 Zellen) über `computePixels` → 12 912 Bytes, 6,3 s, 0 Wiederholungen, 1 600 Zellen mit Daten.
