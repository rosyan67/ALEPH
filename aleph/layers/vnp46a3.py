"""Layer Nachtlicht: NASA VNP46A3 (Black Marble, monatlich).

Steckbrief: docs/sources/vnp46a3.md. Nutzt dieselbe Ladelogik wie alle
anderen Layer (aleph/core/io.py, aleph/core/auth.py).

Zwei Datenfelder werden mitgeführt (Entscheidung 2026-09-24: AllAngle als
Standardfeld, NearNadir als Gegenprobe):
- AllAngle_Composite_Snow_Free    (Standardfeld: mehr Beobachtungen, weniger
  aufgefüllte Pixel)
- NearNadir_Composite_Snow_Free   (Gegenprobe: gleichbleibende Blickgeometrie)

Pro Feld und Gitterzelle (0,25°, 60 x 60 Rohpixel) wird gespeichert:
- `<feld>_mittel`: Mittelwert aller gültigen Pixel (beobachtet und aufgefüllt
  gemeinsam) (nW·cm⁻²·sr⁻¹)
- `<feld>_mittel_beobachtet`: Mittelwert nur über beobachtete Pixel
  (Quality != 2)
- `<feld>_gueltige_pixel`: Zahl der Pixel ohne Fehlwert (Datenlage, 0-3600)
- `<feld>_beobachtete_pixel`: Zahl der beobachteten Pixel (gültig und
  Quality != 2)
- `<feld>_aufgefuellt_pixel`: Zahl der Pixel mit Quality=2 ("gap filled NTL
  based on historical data", Steckbrief Abschnitt 8) unter den gültigen
  Pixeln. Diese Pixel sind keine direkte Messung des Monats, sondern aus
  historischen Daten ergänzt. Sie fließen weiterhin in `_mittel` ein (wie im
  Rohprodukt), werden aber separat gezählt, damit spätere Auswertungen
  zwischen „beobachtet" und „aus historischen Daten ergänzt" unterscheiden
  können (ARCHITECTURE.md Abschnitt 4, Evidenzstufen).

Fehlwerte: Komposit −999,9 (kein NaN in der Rohdatei), `_Num` 65535.
`_Quality` wird NICHT als vollständiges Feld mitgeführt (der Steckbrief,
Abschnitt 8, zeigt an zwei Probekacheln, dass die Zahlen-Schwelle in einer
Kachel exakt passte, in einer anderen nicht erklärbar abwich); `_Num` und
die Zahl gültiger Pixel bleiben das Datenlage-Maß, ergänzt um die separate
Zählung aufgefüllter Pixel oben.

Sicherheitsnetz vor dem großen Lauf (nach Prüfung durch statistik-pruefer,
2026-09-22):
- `pruefe_vollstaendigkeit` prüft, ob ein Monat vollständig geladen wurde.
  BERICHTIGT 2026-09-25: Die frühere Fassung verglich nur mit der Länge der
  Kachelliste, und diese Liste war durch `count=1000` abgeschnitten (die
  „460 Kacheln" von Januar 2024 waren ein Artefakt davon, echt sind 540). Seitdem:
  Katalogabfrage über alle Seiten mit Abgleich der Trefferzahl
  (`_katalog_abfrage`), Vollständigkeit gegen den Katalog UND gegen die
  Referenzliste der 540 Positionen (`vnp46a3_kachelpositionen.txt`), Zustand
  je Position im Manifest.
- Jede Kachel wird nach dem Laden gegen Name, Größe und MD5 aus dem Katalog
  geprüft (`_lade_und_pruefe_kachel`), auch wiederverwendete Rohdateien.
- `_pruefe_ausrichtung` liest `lat`/`lon` aus jeder Kachel und prüft die
  Annahme "Zeile 0 = Nordrand, Spalte 0 = Westrand" gegen die tatsächlichen
  Koordinaten, statt sie nur aus dem Dateinamen (h/v) anzunehmen.
- `schreibe_manifest` hält je Position Zustand, Dateiname (inkl.
  Erzeugungszeitstempel), Größe und MD5 fest, bevor die Rohdaten gelöscht werden.

Aufbau des Würfels (geändert 2026-09-23, damit die Monate in beliebiger
Reihenfolge geladen werden können, z. B. erst 2018-2025, dann 2013-2017):
Der Würfel wird beim ersten Schreiben mit der FESTEN Zeitachse
2013-01 bis 2025-12 (Entscheidung E3, 156 Monate) angelegt, alle Zellen leer
(Wert NaN, Zähler 0). Jeder Monat wird an seine Position auf der Zeitachse
geschrieben, nie hinten angehängt; die Zeitachse ist damit immer sortiert,
egal in welcher Reihenfolge geladen wird. Die Variable `monat_fertig`
(je Monat 0 leer, 1 fertig, 2 unvollständig, 3 wird geschrieben; siehe
`MONAT_LEER` usw.) wird erst auf 1 gesetzt, nachdem die Werte zurückgelesen und mit
den geschriebenen verglichen wurden. Nur so markierte Monate gelten als
vorhanden (`vorhandene_monate`); ein leerer Monat der Zeitachse ist damit von
einem Monat mit Daten unterscheidbar, und ein Absturz mitten im Schreiben
hinterlässt keinen Monat, der fälschlich als fertig gilt.

Download-Zuverlässigkeit (nach den Hängern vom 2026-09-22, behoben
2026-09-23):
`earthaccess.download()` lädt intern mit `requests` und OHNE jedes
Zeitlimit (`session.get(url, stream=True, ...)`, kein `timeout=`). Bleibt
eine Verbindung stecken (beobachtet: CLOSE_WAIT-Sockets zu einem
CloudFront-Server), wartet Python unbegrenzt, egal wie viele parallele
Threads earthaccess intern nutzt. Vermutete Ursache der Hänger: zu viele
gleichzeitige Verbindungen zum selben NASA/CloudFront-Server (übliche,
stille Drosselung ohne Fehlermeldung). Deshalb:
- Kacheln werden einzeln geladen (`_lade_kachel`), jede in einem eigenen,
  mit `concurrent.futures` überwachten Aufruf von `earthaccess.download`
  (weiterhin dieselbe NASA-Bibliothek, ARCHITECTURE.md Abschnitt 5 - hier
  wird nur die Nebenläufigkeit und das Zeitlimit von außen gesteuert,
  keine eigene HTTP-Logik geschrieben).
- `DATEI_TIMEOUT_SEKUNDEN` (10 Minuten) ist das Zeitlimit je Kachel,
  großzügig über der beobachteten Normaldauer einer einzelnen Kachel.
- Für den ganzen Monat gibt es seit 2026-09-26 keine feste Gesamtfrist mehr,
  sondern eine Stillstands-Erkennung (`STILLSTAND_SEKUNDEN`, 30 Minuten ohne
  neue geprüfte Kachel) und eine großzügige Notbremse
  (`MONAT_NOTBREMSE_SEKUNDEN`, 12 Stunden). Die frühere Frist von 4 Stunden
  stellte auch Monate zurück, deren Kacheln stetig ankamen, nur langsamer
  (Diagnose berichte/2026-09-26_diagnose-download.md).
- `GLEICHZEITIGE_DOWNLOADS_STANDARD` begrenzt, wie viele Kacheln gleichzeitig
  angefragt werden (Vorschlag 2-4, siehe LOG.md 2026-09-23). Einstellbar je
  Aufruf (`lade_monat`, `download`) und über `--gleichzeitig` beim
  Hintergrund-Lauf (`vnp46a3_lauf.py`).

Fehlerverhalten (geändert 2026-09-24, nachdem am 2026-09-24 05:25 UTC zwei
Kacheln von 2019-02 nach je 4 Versuchen mit HTTP 502 - Serverfehler bei der
NASA - den ganzen Lauf beendet und 6,5 Stunden gekostet hatten):
- Vorübergehende Fehler (HTTP 5xx, Zeitüberschreitung, Verbindungsfehler,
  ebenso 408 und 429, bei denen Warten hilft) werden hartnäckig wiederholt:
  Wartezeit 20 s, verdoppelt sich, höchstens `KACHEL_WARTEZEIT_MAX_SEKUNDEN`
  je Pause; insgesamt höchstens `KACHEL_RETRY_BUDGET_SEKUNDEN` (30 Minuten,
  gezählt einschließlich der Versuche selbst) je Kachel.
- Dauerhafte Fehler (HTTP 4xx wie 404 „nicht gefunden") führen sofort zum
  Aufgeben dieser Kachel, ohne Wartezeit.
- HTTP 403 ist ein Sonderfall (Änderung 2026-09-24): NASA antwortet bei einem
  abgelaufenen oder ungültigen Zugang oft mit 403 statt 401. Eine einzelne 403
  bleibt ein Kachelfehler. Mehr als `ZUGANG_403_HINTEREINANDER_MAX` (5)
  403-Antworten hintereinander (eine erfolgreich geladene Kachel setzt den
  Zähler zurück) oder 403 bei ALLEN Kacheln eines Monats gelten als Blocker
  „Anmeldung prüfen" (`AnmeldungFehlgeschlagen`) und beenden den Lauf, statt
  tagelang ohne Ergebnis weiterzulaufen.
- Echte Blocker beenden den Lauf, alles andere nicht: Anmeldung fehlgeschlagen
  (`AnmeldungFehlgeschlagen`, auch bei HTTP 401 oder nicht akzeptierter EULA),
  Speicherplatz voll (`io.SpeicherZuKnapp`, auch bei ENOSPC) und SSD nicht
  erreichbar (`io.SSDNichtGefunden`) werden aus jeder Kachel-Wiederholung
  durchgereicht.
- Fehlen nach allen Versuchen einzelne Kacheln, meldet `lade_monat`
  `KachelnFehlen`. Der Monat wird dann NICHT geschrieben und NICHT als fertig
  markiert; die schon geladenen Kacheln bleiben im Rohordner. Beim nächsten
  Versuch (Nachhol-Durchgang am Ende des Laufs oder Neustart) werden gültige
  Kacheln wiederverwendet und nur die fehlenden geladen.
- Scheitern in einem Monat `MAX_GESCHEITERTE_KACHELN_JE_MONAT` Kacheln, gilt der
  Server als gestört: der Rest des Monats wird nicht mehr versucht (sonst
  kostete ein Ausfall 30 Minuten je Kachel, hunderte Kacheln lang).
"""

import concurrent.futures
import errno
import hashlib
import os
import re
import shutil
import threading
import time
import warnings
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import h5py
import numpy as np
import xarray as xr

import earthaccess
from earthaccess.exceptions import DownloadFailure, EulaNotAccepted, ServiceOutage

from aleph.core import io
from aleph.core.auth import earthdata_login

META = {
    "name": "VNP46A3",
    "bereich": "Umwelt / menschliche Aktivität",
    "quelle": "NASA VIIRS Black Marble, LAADS DAAC, DOI 10.5067/VIIRS/VNP46A3.002",
    "lizenz": "CC0 / ohne Einschränkung laut LAADS, Quellenangabe erbeten (nicht Pflicht)",
    "native_aufloesung": "15 Bogensekunden (~500 m), Kacheln 10° x 10°",
    "ziel_aufloesung": "0,25° (60 x 60 Rohpixel je Zelle), monatlich",
    "einheit": "nW·cm⁻²·sr⁻¹",
    "zeitraum": "2013-01 bis 2025-12 (Untersuchungszeitraum ALEPH, Entscheidung E3)",
    "bekannte_schwaechen": (
        "Starke Winkelabhängigkeit; Schnee verfälscht Nachtlicht; wenig "
        "gültige Nächte im Sommer in hohen Breiten; Suomi-NPP-Auslieferung "
        "endet 2026-11-01 (danach ggf. VJ146A3/NOAA-20 prüfen)."
    ),
    "details": "docs/sources/vnp46a3.md",
}

FELD_TRIPEL = {
    "near_nadir": (
        "NearNadir_Composite_Snow_Free",
        "NearNadir_Composite_Snow_Free_Num",
        "NearNadir_Composite_Snow_Free_Quality",
    ),
    "allangle": (
        "AllAngle_Composite_Snow_Free",
        "AllAngle_Composite_Snow_Free_Num",
        "AllAngle_Composite_Snow_Free_Quality",
    ),
}
HDF_GRUPPE = "HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields"
FEHLWERT_KOMPOSIT = -999.9
FEHLWERT_NUM = 65535
QUALITAET_AUFGEFUELLT = 2

PIXEL_PRO_KACHEL = 2400
ZELLEN_PRO_KACHEL = 40
PIXEL_PRO_ZELLE = 60
GITTER_BREITE = 720  # Zeilen, 0,25°, Zeile 0 = 90°N
GITTER_LAENGE = 1440  # Spalten, 0,25°, Spalte 0 = 180°W
ZELLGROESSE = 0.25

# Feste Zeitachse des Würfels (Entscheidung E3: 2013-2025).
ZEITACHSE_START = (2013, 1)
ZEITACHSE_ENDE = (2025, 12)
FERTIG_VARIABLE = "monat_fertig"
WUERFEL_DIMS = ("zeit", "breite", "laenge")
WUERFEL_CHUNKS = (1, 180, 720)  # ein Monat je Chunk-Schicht

# Stillstands-Erkennung für den Download eines Monats (Umbau 2026-09-26; ersetzt
# die frühere feste Gesamtfrist von 4 Stunden, die am 25./26.09. vier Monate
# zurückstellte, obwohl bis zuletzt 88-142 Kacheln je Stunde ankamen).
# Ein Monat gilt nur als hängend, wenn so lange KEINE neue, gegen Größe und MD5
# geprüfte Kachel fertig wird. Warum 30 Minuten:
# - Eine einzelne hängende Verbindung löst schon das Zeitlimit je Kachel
#   (DATEI_TIMEOUT_SEKUNDEN, 10 Minuten) mit neuem Versuch; das soll den Monat
#   nicht abbrechen. 30 Minuten sind drei solche Zeitlimits.
# - Bei mehreren gleichzeitigen Downloads wird normalerweise alle 0,5-2 Minuten
#   eine Kachel fertig (gemessen 2026-09-25/26). Eine sehr große Kachel
#   (bis 158,5 MB, Manifest 2024-01) bekommt je Versuch ein größenabhängiges
#   Zeitlimit (KACHEL_MINDESTRATE_BYTES_JE_S, siehe dort); die 30 Minuten gelten
#   für den ganzen Monat, in dem parallel weitere Kacheln fertig werden.
# - Eine kurze Serverstörung (5xx) wird je Kachel bis zu 30 Minuten wiederholt
#   (KACHEL_RETRY_BUDGET_SEKUNDEN); dauert sie länger, ist Zurückstellen richtig.
STILLSTAND_SEKUNDEN = 30 * 60

# Notbremse: So lange darf der Download EINES Monats insgesamt dauern, auch
# wenn noch Kacheln ankommen. Nur gegen einen praktisch endlosen Monat bei
# extrem langsamer Leitung. Ein vollständiger Monat hat etwa 28-33 GB
# (Manifest 2024-01: 33,1 GB); 12 Stunden greifen also erst unter etwa
# 0,75 MB/s. Greift sie, wird der Monat mit eigener Meldung zurückgestellt.
MONAT_NOTBREMSE_SEKUNDEN = 12 * 60 * 60

# Zeitlimit je einzelner Kachel. earthaccess.download() setzt selbst kein
# Zeitlimit für die HTTP-Anfrage (session.get ohne timeout=), eine
# hängengebliebene Verbindung würde sonst unbegrenzt warten. 10 Minuten sind
# großzügig über der beobachteten Normaldauer einer Kachel (~11 Sekunden im
# Schnitt bei vollem Durchsatz), aber kurz genug, um einen echten Hänger
# rasch zu erkennen und neu zu versuchen.
DATEI_TIMEOUT_SEKUNDEN = 10 * 60  # 10 Minuten

# Das Zeitlimit je Versuch misst die GESAMTzeit eines Downloads, nicht Stillstand
# (earthaccess meldet keinen Fortschritt nach außen). Damit eine große Kachel auch
# bei langsamer Leitung in EINEM Versuch fertig werden kann, wächst das Limit mit
# der Dateigröße: max(DATEI_TIMEOUT_SEKUNDEN, Größe / diese Mindestrate).
# 0,1 MB/s je Verbindung: gemessen wurden am 26.09. 0,6-1,6 MB/s je Verbindung;
# die größte Kachel (158,5 MB) bekommt so 26 Minuten. (Auflage statistik-pruefer
# 2026-09-26: vorher konnte eine 158-MB-Kachel unter 0,26 MB/s nie fertig werden,
# und jeder Neuversuch startete einen zusätzlichen Datenstrom.) Unter 0,1 MB/s je
# Verbindung bleibt das möglich - dann greift ohnehin bald die Notbremse.
KACHEL_MINDESTRATE_BYTES_JE_S = 100_000


def kachel_zeitlimit(groesse_bytes: int | None) -> float:
    """Zeitlimit für EINEN Ladeversuch einer Kachel dieser Größe (Sekunden)."""
    if not groesse_bytes:
        return DATEI_TIMEOUT_SEKUNDEN
    return max(DATEI_TIMEOUT_SEKUNDEN, groesse_bytes / KACHEL_MINDESTRATE_BYTES_JE_S)

# Zeit, die eine Kachel bei vorübergehenden Fehlern (5xx, Zeitüberschreitung)
# insgesamt bekommt, Versuche und Pausen zusammengezählt. Danach wird der
# Monat zurückgestellt (nicht der Lauf beendet). Ausgangslage: 4 Versuche in
# rund 2 Minuten reichten am 2026-09-24 nicht für einen Serverfehler (502).
KACHEL_RETRY_BUDGET_SEKUNDEN = 30 * 60

# Wartezeit vor dem ersten erneuten Versuch; verdoppelt sich je Versuch
# (20 s, 40 s, 80 s, ...), damit eine kurzzeitige Drosselung Zeit hat,
# nachzulassen, aber höchstens KACHEL_WARTEZEIT_MAX_SEKUNDEN je Pause.
KACHEL_WARTEZEIT_BASIS_SEKUNDEN = 20
KACHEL_WARTEZEIT_MAX_SEKUNDEN = 5 * 60

# Scheitern in einem Monat so viele Kacheln endgültig (Budget verbraucht oder
# dauerhaft fehlend), wird der Rest des Monats nicht mehr versucht. Sonst
# kostete ein Serverausfall 30 Minuten je Kachel (460 Kacheln, 3 gleichzeitig:
# über 70 Stunden für einen einzigen Monat).
MAX_GESCHEITERTE_KACHELN_JE_MONAT = 10

# HTTP-Statuscodes aus der 4xx-Familie, bei denen Warten trotzdem hilft
# (Zeitüberschreitung des Servers, Anfragebegrenzung).
_HTTP_4XX_MIT_WARTEN = {408, 429}
# Anmeldung fehlt oder abgelaufen: Blocker, kein Kachel-Problem.
_HTTP_ANMELDUNG = {401}

# HTTP 403: einzeln ein Kachelfehler, gehäuft ein Zugangsproblem. Mehr als so
# viele 403 hintereinander (ohne dazwischen erfolgreich geladene Kachel) beenden
# den Lauf als „Anmeldung prüfen".
ZUGANG_403_HINTEREINANDER_MAX = 5
_STATUS_IM_TEXT = re.compile(r"Status code:\s*(\d{3})")

# Zahl gleichzeitiger Kachel-Downloads. Vermutete Ursache der Hänger vom
# 2026-09-22: zu viele gleichzeitige Verbindungen zum selben NASA/CloudFront-
# Server (stille Drosselung ohne Fehlermeldung). Vorschlag 2-4 (LOG.md
# 2026-09-23); bei erneuten Hängern hier eine kleinere Zahl eintragen statt
# zu raten.
GLEICHZEITIGE_DOWNLOADS_STANDARD = 3

# Referenzliste aller Kachelpositionen, die VNP46A3 liefert (540 Stück).
# Eine Annahme über den Anbieter, keine Naturkonstante: Herkunft und
# Erhebungsdatum stehen im Kopf der Datei. Meldet der Katalog eine Position,
# die hier fehlt, bricht der Monat mit `ReferenzlisteVeraltet` ab, statt sie
# stillschweigend zu übergehen (Auftrag 2026-09-25).
REFERENZ_KACHELN_DATEI = Path(__file__).with_name("vnp46a3_kachelpositionen.txt")

# Grenzen für „beim Anbieter nicht vorhanden" (Auflage statistik-pruefer
# 2026-09-25): Sonst würde jede Lücke in der KATALOGANTWORT selbst (Störung,
# falsches Zeitfenster) still diesen Namen bekommen und der Monat als fertig
# gelten. Gemessen am 2026-09-25 in 22 Monaten: nur 1 bis 6 Positionen, alle
# bei 60-80° N (Zeilen v01-v02), nur in Mai bis Juli. Die Grenzen sind etwas
# weiter gezogen (v00-v03 = nördlich 50° N, April bis August, höchstens 10),
# aber eng genug, dass eine abgeschnittene Katalogantwort (80 bis 441 fehlende
# Positionen, über alle Breiten) abbricht. Eine ANNAHME: Bricht ein Monat
# daran ab, erst am Katalog prüfen, dann die Grenze begründet anpassen.
NICHT_BEIM_ANBIETER_MAX = 10
NICHT_BEIM_ANBIETER_ZEILEN = range(0, 4)  # v00-v03
NICHT_BEIM_ANBIETER_MONATE = range(4, 9)  # April bis August

# So oft wird eine Kachel geladen, wenn Größe oder MD5-Prüfsumme nicht zum
# NASA-Katalog passen (Anlass: die Datei „h12v09" von 2019-05 enthielt
# byteidentisch h13v04, LOG.md 2026-09-25). Danach gilt sie als nicht geladen.
PRUEFSUMMEN_VERSUCHE = 3

# Zustand jeder Kachelposition im Manifest (genau einer je Position).
ZUSTAND_GELADEN = "geladen"
ZUSTAND_NICHT_BEIM_ANBIETER = "beim Anbieter nicht vorhanden"
ZUSTAND_NICHT_GELADEN = "nicht geladen"

# Werte von `monat_fertig` (FERTIG_VARIABLE) je Monat:
# 0 = leer (nie geladen), 1 = fertig und vollständig, 2 = Daten vorhanden, aber
# unvollständig (vor 2026-09-25 mit abgeschnittener Kachelabfrage geladen, wird
# neu geladen), 3 = wird gerade geschrieben (ein Absturz dabei hinterlässt
# keinen Monat, der als fertig oder als „alte Daten" gilt). Nur 1 zählt als
# vorhanden (`vorhandene_monate`, aleph/detect/wuerfel.py).
MONAT_LEER = 0
MONAT_FERTIG = 1
MONAT_UNVOLLSTAENDIG = 2
MONAT_WIRD_GESCHRIEBEN = 3
# 4 = vollständig NUR für die Region Afrika-Europa-Asien (Vorrang beim Laden,
# seit 2026-09-26; Kachelliste aleph/layers/vnp46a3_kacheln_afrika_europa_asien.txt).
# Zellen außerhalb der Region-Kacheln sind in einem solchen Monat NICHT GELADEN
# (Wert NaN, Zähler 0 - im Würfel gleich kodiert wie „keine Daten“; nur der
# Zustand 4 zusammen mit der Kachelliste trennt beides). Zählt NICHT als
# vorhanden (`vorhandene_monate`, aleph/detect/wuerfel.py liefern nur 1); lesen
# nur ausdrücklich über aleph/detect/wuerfel.py `lies_monate_mit_region`.
MONAT_REGION_VOLLSTAENDIG = 4

_KACHEL_HV = re.compile(r"\.h(\d{2})v(\d{2})\.")
_KACHEL_DATUM = re.compile(r"\.A(\d{4})(\d{3})\.")


class KachelName(RuntimeError):
    """Der Dateiname passt nicht zum erwarteten VNP46A3-Muster."""


class KachelAusrichtung(RuntimeError):
    """Die lat/lon-Werte einer Kachel passen nicht zur angenommenen Ausrichtung."""


class MonatUnvollstaendig(RuntimeError):
    """Der Monat ist nicht vollständig (Kacheln fehlen, Katalog oder Referenzliste passen nicht).

    `zustaende`: Zustand je Kachelposition (siehe `kachel_zustaende`), wenn
    bekannt; wird ins Manifest geschrieben.
    """

    def __init__(self, meldung: str, zustaende: "dict[str, KachelEintrag] | None" = None):
        super().__init__(meldung)
        self.zustaende = zustaende


class KatalogUnvollstaendig(MonatUnvollstaendig):
    """Die Katalogabfrage lieferte nicht so viele Einträge, wie der Katalog selbst meldet (CMR-Hits)."""


class ReferenzlisteVeraltet(MonatUnvollstaendig):
    """Der Katalog meldet Kachelpositionen, die in der Referenzliste fehlen."""


class DownloadHaengt(RuntimeError):
    """Der Download ist stehen geblieben: je Kachel über dem Zeitlimit, oder im
    Monat seit `STILLSTAND_SEKUNDEN` keine neue geprüfte Kachel."""


class DownloadZuLangsam(DownloadHaengt):
    """Notbremse: Der Download eines Monats dauert länger als
    `MONAT_NOTBREMSE_SEKUNDEN`, obwohl noch Kacheln ankommen. Wird wie ein
    Hänger behandelt (Monat zurückgestellt), aber mit eigener Meldung."""


def _abdruck(pfad: Path) -> tuple[int, int, int] | None:
    """Fingerabdruck einer Datei (Inode, Größe, Änderungszeit in ns); None, wenn sie fehlt.

    Ändert sich der Abdruck nach der MD5-Prüfung, wurde die Datei ersetzt (z. B.
    von einem aufgegebenen Download-Faden, der später doch noch fertig wurde).
    """
    try:
        st = pfad.stat()
    except FileNotFoundError:
        return None
    return (st.st_ino, st.st_size, st.st_mtime_ns)


class LadeStatistik:
    """Zählt je Monat, was beim Laden passiert (für das Protokoll; thread-sicher).

    - `neu_anzahl`, `neu_bytes`: in diesem Versuch neu geladene und geprüfte Kacheln
    - `verworfen`: Kacheln, deren Größe oder MD5 nicht zum Katalog passte und die
      deshalb gelöscht und neu geladen wurden
    - `wiederholungen`: erneute Versuche nach Netzfehler oder Zeitüberschreitung
    """

    def __init__(self):
        self._sperre = threading.Lock()
        self.neu_anzahl = 0
        self.neu_bytes = 0
        self.verworfen = 0
        self.verworfen_endgueltig = 0
        self.wiederholungen = 0
        self.abdruecke: dict[Path, tuple] = {}

    def merke(self, pfad: Path) -> None:
        """Fingerabdruck einer eben gegen Größe und MD5 geprüften Datei festhalten."""
        with self._sperre:
            self.abdruecke[pfad] = _abdruck(pfad)

    def neu(self, groesse: int) -> None:
        with self._sperre:
            self.neu_anzahl += 1
            self.neu_bytes += groesse

    def verwerfe(self) -> None:
        with self._sperre:
            self.verworfen += 1

    def wiederhole(self) -> None:
        with self._sperre:
            self.wiederholungen += 1

    def verwerfe_endgueltig(self) -> None:
        with self._sperre:
            self.verworfen_endgueltig += 1

    def text(self, dauer_sekunden: float, zustand: str) -> str:
        """Protokollzeile. `zustand`: „vollständig geladen" oder „abgebrochen".

        MB/s = geprüfte Nutzdaten (neu geladene Kacheln, die Größe und MD5 bestanden)
        geteilt durch die ganze Dauer einschließlich Wartezeiten; verworfene und
        doppelt übertragene Bytes zählen nicht. Wiederholungen: nur die eigenen
        erneuten Versuche, ohne die bis zu 3 internen Versuche von earthaccess.
        """
        mbs = self.neu_bytes / 1e6 / dauer_sekunden if dauer_sekunden > 0 else 0.0
        return (
            f"Download-Statistik ({zustand}): {self.neu_anzahl} Kacheln neu geladen ({self.neu_bytes / 1e9:.1f} GB) "
            f"in {dauer_sekunden / 60:.1f} Minuten, {mbs:.2f} MB/s geprüfte Nutzdaten einschließlich Wartezeit; "
            f"{self.verworfen} nach Größen-/MD5-Prüfung verworfen (davon {self.verworfen_endgueltig} nicht mehr neu "
            f"geladen); {self.wiederholungen} Wiederholungen nach Netzfehler oder Zeitüberschreitung "
            "(ohne interne Versuche von earthaccess)."
        )


class AnmeldungFehlgeschlagen(RuntimeError):
    """Login bei NASA Earthdata fehlgeschlagen oder abgelaufen (echter Blocker: Lauf endet)."""


class KachelNichtGeladen(RuntimeError):
    """Eine Kachel konnte nicht geladen werden.

    `dauerhaft`: True bei HTTP 4xx (Warten hilft nicht), False, wenn das
    Wiederholungs-Budget bei vorübergehenden Fehlern (5xx, Zeitüberschreitung)
    verbraucht wurde oder der Monat abgebrochen wurde. `status`: HTTP-Status,
    wenn bekannt.
    """

    def __init__(self, meldung: str, dauerhaft: bool, status: int | None = None):
        super().__init__(meldung)
        self.dauerhaft = dauerhaft
        self.status = status


class KachelnFehlen(MonatUnvollstaendig):
    """Ein Monat ist unvollständig, weil einzelne Kacheln nicht geladen werden konnten.

    Kein Blocker: Der Lauf stellt den Monat zurück und macht weiter.
    `dauerhaft`/`vorlaeufig`: Zahl der Kacheln je Art des Scheiterns.
    """

    def __init__(
        self,
        meldung: str,
        dauerhaft: int,
        vorlaeufig: int,
        zustaende: "dict[str, KachelEintrag] | None" = None,
    ):
        super().__init__(meldung, zustaende)
        self.dauerhaft = dauerhaft
        self.vorlaeufig = vorlaeufig


class WuerfelFormat(RuntimeError):
    """Der Würfel auf der SSD hat nicht den erwarteten Aufbau (feste Zeitachse)."""


class MonatAusserhalbZeitachse(ValueError):
    """Der Monat liegt nicht auf der Zeitachse des Würfels (2013-01 bis 2025-12)."""


class MonatSchonVorhanden(RuntimeError):
    """Der Monat ist im Würfel schon als fertig markiert und wird nicht überschrieben."""


class WuerfelSchreibFehler(RuntimeError):
    """Die Rückprüfung nach dem Schreiben fand Werte, die nicht den geschriebenen entsprechen."""


@dataclass(frozen=True)
class KachelSoll:
    """Was der NASA-Katalog über eine Kachel sagt: Dateiname, Größe, MD5-Prüfsumme."""

    datei: str
    groesse: int
    md5: str


@dataclass(frozen=True)
class KachelEintrag:
    """Eine Zeile im Manifest: Zustand einer Kachelposition in einem Monat."""

    zustand: str
    soll: KachelSoll | None = None  # None bei ZUSTAND_NICHT_BEIM_ANBIETER
    grund: str = ""


@dataclass
class MonatsLadung:
    """Ergebnis von `lade_monat`: die geladenen Dateien und der Zustand jeder Position.

    Seit 2026-09-26 zusätzlich: `katalog_positionen` (alle Positionen, die der
    Katalog für den GANZEN Monat meldete, auch außerhalb einer Stufe) und
    `abdruecke` (Fingerabdruck jeder geprüften Datei, für `pruefe_ladung_unveraendert`).
    """

    dateien: list[Path]
    zustaende: dict[str, KachelEintrag]
    katalog_positionen: set[str] = field(default_factory=set)
    abdruecke: dict = field(default_factory=dict)


def pruefe_ladung_unveraendert(ladung: MonatsLadung) -> None:
    """Direkt vor dem Verkleinern: sind alle geprüften Dateien noch dieselben? Sonst Abbruch.

    Schließt die Lücke zwischen der Prüfung in `lade_monat` und dem Lesen
    (Rest-Befund zu Auflage A1, statistik-pruefer 2026-09-26). Ohne Fingerabdrücke
    (ältere Aufrufer, Test-Attrappen) wird nichts geprüft.
    """
    if not ladung.abdruecke:
        return
    geladen = {p: e for p, e in ladung.zustaende.items() if e.zustand == ZUSTAND_GELADEN}
    pfade = {_position(d.name): d for d in ladung.dateien}
    schlecht = pruefe_unveraendert(
        {p: pfade[p] for p in geladen if p in pfade}, {p: e.soll for p, e in geladen.items()}, ladung.abdruecke
    )
    if schlecht:
        raise MonatUnvollstaendig(
            f"{len(schlecht)} Kachel(n) wurden nach der Prüfung verändert und passen nicht mehr "
            f"(z. B. {next(iter(schlecht.values()))[:200]}). Nichts geschrieben; Monat wird erneut versucht."
        )


class _ZugangsWaechter:
    """Zählt HTTP-403-Antworten hintereinander, über Kacheln, Monate und Threads hinweg.

    Eine erfolgreich geladene Kachel beweist, dass der Zugang funktioniert, und
    setzt den Zähler zurück. Andere Fehler (404, 5xx) ändern ihn nicht.
    """

    def __init__(self) -> None:
        self._sperre = threading.Lock()
        self._folge = 0

    def erfolg(self) -> None:
        with self._sperre:
            self._folge = 0

    def melde_403(self) -> int:
        with self._sperre:
            self._folge += 1
            return self._folge

    def zuruecksetzen(self) -> None:
        self.erfolg()


ZUGANG = _ZugangsWaechter()


def _zugang_pruefen_meldung(befund: str) -> str:
    return (
        f"Anmeldung prüfen: {befund} HTTP 403 (Zugriff verweigert). Das deutet auf einen "
        "abgelaufenen oder ungültigen Zugang hin, nicht auf einzelne fehlende Kacheln. "
        "Zugangsdaten in .env und das Earthdata-Konto prüfen (auch die Nutzungsbedingungen "
        "für LAADS DAAC). Lauf beendet; fertige Monate und geladene Rohdaten bleiben "
        "erhalten, ein Neustart setzt fort."
    )


def _kachel_position(pfad: Path) -> tuple[int, int, int, int]:
    """Globale Zeilen-/Spalten-Startposition (0,25°-Gitter) einer Kachel, plus h, v.

    h/v aus dem Dateinamen, z. B. h19v03. Kachel h=0 beginnt bei 180°W,
    v=0 bei 90°N (geprüft an der Probekachel h19v03 = 10-20°O, 50-60°N,
    docs/sources/vnp46a3.md Abschnitt 14, und zusätzlich zur Laufzeit gegen
    lat/lon jeder Kachel geprüft, siehe `_pruefe_ausrichtung`).
    """
    treffer = _KACHEL_HV.search(pfad.name)
    if not treffer:
        raise KachelName(f"Kann h/v nicht aus Dateinamen lesen: {pfad.name}")
    h, v = int(treffer.group(1)), int(treffer.group(2))
    return v * ZELLEN_PRO_KACHEL, h * ZELLEN_PRO_KACHEL, h, v


def _kachel_jahr_monat(pfad: Path) -> tuple[int, int]:
    """Jahr und Monat einer Kachel aus dem Dateinamen (A{Jahr}{Tag-im-Jahr})."""
    treffer = _KACHEL_DATUM.search(pfad.name)
    if not treffer:
        raise KachelName(f"Kann Datum nicht aus Dateinamen lesen: {pfad.name}")
    jahr, tag = int(treffer.group(1)), int(treffer.group(2))
    datum = date(jahr, 1, 1) + timedelta(days=tag - 1)
    return datum.year, datum.month


def _pruefe_ausrichtung(gruppe, pfad: Path, h: int, v: int) -> None:
    """Prüft Zeile-0-ist-Nordrand / Spalte-0-ist-Westrand an den echten lat/lon-Werten.

    Nicht nur eine Annahme aus dem Dateinamen: `lat`/`lon` sind 1D-Felder je
    Kachel (gemessen, 2400 Werte). lat[0] muss der Nordrand sein und fallend
    verlaufen, lon[0] der Westrand und steigend, jeweils zur h/v-Position
    passend (Toleranz 0,01°, deutlich unter der Pixelgröße von 15 Bogensek.).
    """
    lat = gruppe["lat"][:]
    lon = gruppe["lon"][:]
    erwartet_lat0 = 90 - v * 10
    erwartet_lon0 = -180 + h * 10
    fehler = []
    if abs(float(lat[0]) - erwartet_lat0) > 0.01:
        fehler.append(f"lat[0]={lat[0]}, erwartet {erwartet_lat0}")
    if lat[0] <= lat[-1]:
        fehler.append("lat ist nicht fallend (Zeile 0 wäre dann nicht der Nordrand)")
    if abs(float(lon[0]) - erwartet_lon0) > 0.01:
        fehler.append(f"lon[0]={lon[0]}, erwartet {erwartet_lon0}")
    if lon[0] >= lon[-1]:
        fehler.append("lon ist nicht steigend (Spalte 0 wäre dann nicht der Westrand)")
    if fehler:
        raise KachelAusrichtung(f"{pfad.name}: unerwartete Ausrichtung: {'; '.join(fehler)}")


def _lies_kachel(pfad: Path) -> dict[str, np.ndarray]:
    """Liest eine Kachel und verkleinert sie auf 40 x 40 Gitterzellen.

    Fehlwerte werden vor jedem Mittelwert maskiert (−999,9 beim Komposit,
    65535 bei `_Num`). Rückgabe je Feldpaar: `<name>_mittel` (Mittelwert
    aller gültigen Pixel, beobachtet und aufgefüllt gemeinsam),
    `<name>_mittel_beobachtet` (Mittelwert nur über beobachtete Pixel,
    Quality != 2), `<name>_gueltige_pixel`, `<name>_beobachtete_pixel`,
    `<name>_aufgefuellt_pixel`, `<name>_num`, je 40 x 40.
    """
    ergebnis: dict[str, np.ndarray] = {}
    block_form = (ZELLEN_PRO_KACHEL, PIXEL_PRO_ZELLE, ZELLEN_PRO_KACHEL, PIXEL_PRO_ZELLE)
    with h5py.File(pfad, "r") as datei:
        gruppe = datei[HDF_GRUPPE]
        for name, (komposit_feld, num_feld, qualitaet_feld) in FELD_TRIPEL.items():
            komposit = gruppe[komposit_feld][:].astype("float32")
            num = gruppe[num_feld][:].astype("float32")
            qualitaet = gruppe[qualitaet_feld][:]
            if komposit.shape != (PIXEL_PRO_KACHEL, PIXEL_PRO_KACHEL):
                raise ValueError(
                    f"{pfad.name}: unerwartete Form {komposit.shape} bei {komposit_feld}"
                )
            # Vergleich mit dem exakten float32-Fehlwert der Datei (nicht mit
            # dem float64-Literal), damit Rundung beim Hoch-/Herunterrechnen
            # keine Fehlwert-Pixel übersehen lässt.
            fehlwert_f32 = np.float32(FEHLWERT_KOMPOSIT)
            gueltig = (komposit != fehlwert_f32) & (num != FEHLWERT_NUM)
            komposit_masked = np.where(gueltig, komposit, np.nan).reshape(block_form)
            num_masked = np.where(gueltig, num, np.nan).reshape(block_form)
            gueltig_bloecke = gueltig.reshape(block_form)
            aufgefuellt_bloecke = (
                (qualitaet == QUALITAET_AUFGEFUELLT) & gueltig
            ).reshape(block_form)
            beobachtet_bloecke = gueltig_bloecke & (~aufgefuellt_bloecke)

            with np.errstate(invalid="ignore"), warnings.catch_warnings():
                # Zellen ohne einen einzigen gültigen Pixel sind erwartbar
                # (z. B. am Kachelrand); "Mean of empty slice" ist dann kein Fehler.
                warnings.filterwarnings("ignore", message="Mean of empty slice")
                mittel = np.nanmean(komposit_masked, axis=(1, 3))
                mittel_beobachtet = np.nanmean(
                    np.where(beobachtet_bloecke, komposit_masked, np.nan), axis=(1, 3)
                )
                num_mittel = np.nanmean(num_masked, axis=(1, 3))
            gueltige_pixel = gueltig_bloecke.sum(axis=(1, 3)).astype("int16")
            beobachtete_pixel = beobachtet_bloecke.sum(axis=(1, 3)).astype("int16")
            aufgefuellte_pixel = aufgefuellt_bloecke.sum(axis=(1, 3)).astype("int16")

            ergebnis[f"{name}_mittel"] = mittel.astype("float32")
            ergebnis[f"{name}_mittel_beobachtet"] = mittel_beobachtet.astype("float32")
            ergebnis[f"{name}_gueltige_pixel"] = gueltige_pixel
            ergebnis[f"{name}_beobachtete_pixel"] = beobachtete_pixel
            ergebnis[f"{name}_num"] = num_mittel.astype("float32")
            ergebnis[f"{name}_aufgefuellt_pixel"] = aufgefuellte_pixel
    return ergebnis


def _monatsspanne(jahr: int, monat: int) -> tuple[str, str]:
    """Zeitspanne der Katalogsuche für einen Monat, so gewählt, dass nur dieser Monat kommt.

    Der Katalog (CMR) sucht nach Überlappung. Ein VNP46A3-Monatsgranulat reicht
    vom 1. um 00:00:00 bis zum 1. des Folgemonats um 00:00:00 (gemessen
    2026-09-25: Januar 2018 = 2017-12-01T00:00 bis 2018-01-01T00:00 beim
    Dezember-Granulat). Eine Suche ab 00:00:00 berührt deshalb den Vormonat:
    2018-02 lieferte so 1080 statt 540 Treffer, und zusammen mit der früheren
    Obergrenze von 1000 fielen 80 Kacheln des Monats weg (LOG.md 2026-09-25).
    Ab 00:00:01 bis 23:59:59 des letzten Tages kommen nur die 540 des Monats
    (gemessen; `exclude_boundary` hätte dasselbe ergeben, die Sekunde ist aber
    ohne Sonderoption im Aufruf sichtbar). Die Monatsprüfung am Dateinamen
    (`_passt_zum_monat`) bleibt trotzdem als Sicherung bestehen.
    """
    letzter_tag = monthrange(jahr, monat)[1]
    return (
        f"{jahr:04d}-{monat:02d}-01T00:00:01Z",
        f"{jahr:04d}-{monat:02d}-{letzter_tag:02d}T23:59:59Z",
    )


# Wie viele Einträge über die gemeldete Trefferzahl hinaus abgefragt werden.
# Kommt mehr zurück als gemeldet (Katalog hat sich zwischen den Anfragen
# geändert), fällt das so auf, statt an der Grenze abgeschnitten zu werden.
_KATALOG_UEBERHANG = 100


def _katalog_abfrage(jahr: int, monat: int) -> tuple[int, list]:
    """Fragt ALLE VNP46A3-Granulate des Monats beim NASA-Katalog ab.

    Rückgabe: (vom Katalog gemeldete Trefferzahl, alle Granulate). Früher
    stand hier `count=1000`, und nur die erste Seite wurde gelesen; das schnitt
    jeden Monat ab (Befund 2026-09-25). Jetzt: zuerst die Gesamtzahl
    (`hits`, Header CMR-Hits), dann alle Seiten (earthaccess blättert über
    CMR-Search-After, bis nichts mehr kommt oder die Grenze erreicht ist; die
    Grenze liegt absichtlich über der gemeldeten Zahl). Weicht die Zahl der
    geholten Einträge von der gemeldeten ab, bricht der Monat mit
    `KatalogUnvollstaendig` ab. Kein stilles Weiterlaufen.
    """
    start, ende = _monatsspanne(jahr, monat)
    auth = earthaccess.__auth__
    abfrage = earthaccess.DataGranules(auth if auth.authenticated else None).parameters(
        short_name="VNP46A3", version="2", temporal=(start, ende)
    )
    gemeldet = abfrage.hits()
    granules = abfrage.get(gemeldet + _KATALOG_UEBERHANG) if gemeldet > 0 else []
    if len(granules) != gemeldet:
        raise KatalogUnvollstaendig(
            f"{jahr:04d}-{monat:02d}: Der NASA-Katalog meldet {gemeldet} Treffer, geholt wurden "
            f"{len(granules)}. Die Kachelliste wäre unvollständig oder uneindeutig; nichts geladen, "
            "Monat wird später erneut versucht."
        )
    return gemeldet, granules


def _position(dateiname: str) -> str:
    """Kachelposition als Text, z. B. 'h21v05', aus einem Dateinamen."""
    treffer = _KACHEL_HV.search(dateiname)
    if not treffer:
        raise KachelName(f"Kann h/v nicht aus Dateinamen lesen: {dateiname}")
    return f"h{treffer.group(1)}v{treffer.group(2)}"


def lies_referenz_positionen(pfad: Path | None = None) -> set[str]:
    """Liest die Referenzliste der Kachelpositionen (Zeilen 'hXXvYY', '#' = Kommentar)."""
    pfad = pfad or REFERENZ_KACHELN_DATEI
    positionen = set()
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#"):
            continue
        if not re.fullmatch(r"h\d{2}v\d{2}", zeile):
            raise ValueError(f"{pfad.name}: unerwartete Zeile {zeile!r}")
        positionen.add(zeile)
    return positionen


def _katalog_soll(granule) -> KachelSoll:
    """Dateiname, Größe und MD5 einer Kachel laut Katalog (UMM-Feld ArchiveAndDistributionInformation).

    Fehlen Größe oder MD5, wird nicht geraten: `KachelNichtGeladen` (dauerhaft),
    die Kachel gilt dann als nicht geladen und der Monat bleibt offen.
    """
    dateien = [
        link.rsplit("/", 1)[-1] for link in granule.data_links() if link.endswith(".h5")
    ]
    if len(set(dateien)) != 1:
        raise KachelNichtGeladen(f"Katalogeintrag ohne eindeutigen .h5-Link: {dateien}", dauerhaft=True)
    angaben = granule["umm"].get("DataGranule", {}).get("ArchiveAndDistributionInformation", [])
    mit_md5 = [
        a for a in angaben
        if a.get("SizeInBytes") is not None and (a.get("Checksum") or {}).get("Algorithm") == "MD5"
    ]
    passend = [a for a in mit_md5 if a.get("Name") == dateien[0]] or mit_md5
    if len(passend) != 1:
        raise KachelNichtGeladen(
            f"{dateien[0]}: Katalog nennt {len(mit_md5)} Einträge mit Größe und MD5, erwartet genau einen. "
            "Ohne Soll-Werte kann die Datei nicht geprüft werden.",
            dauerhaft=True,
        )
    return KachelSoll(dateien[0], int(passend[0]["SizeInBytes"]), passend[0]["Checksum"]["Value"].lower())


def _md5(pfad: Path) -> str:
    pruefsumme = hashlib.md5()
    with open(pfad, "rb") as datei:
        for block in iter(lambda: datei.read(1024 * 1024), b""):
            pruefsumme.update(block)
    return pruefsumme.hexdigest()


def _pruefe_gegen_katalog(pfad: Path, soll: KachelSoll) -> str | None:
    """None, wenn Name, Größe und MD5 der Datei zum Katalog passen, sonst der Grund."""
    if pfad.name != soll.datei:
        return f"Dateiname {pfad.name} statt {soll.datei}"
    groesse = pfad.stat().st_size
    if groesse != soll.groesse:
        return f"{pfad.name}: Größe {groesse} Bytes statt {soll.groesse} laut Katalog"
    md5 = _md5(pfad)
    if md5 != soll.md5:
        return f"{pfad.name}: MD5 {md5} statt {soll.md5} laut Katalog"
    return None


def _statuscode(fehler: BaseException) -> int | None:
    """HTTP-Status aus der Fehlermeldung von earthaccess ("... Status code: 502").

    earthaccess (`DownloadFailure`) gibt den Status nur im Meldungstext an,
    nicht als eigenes Feld. Ändert sich der Text bei einem Update, liefert
    diese Funktion None; der Fehler gilt dann als vorübergehend (Warten kostet
    Zeit, verliert aber keine Daten). Ein Test hält das Format fest.
    """
    treffer = _STATUS_IM_TEXT.search(str(fehler))
    return int(treffer.group(1)) if treffer else None


def pruefe_blocker(fehler: BaseException, status: int | None) -> None:
    """Reicht echte Blocker weiter (Login, Speicher, SSD); kehrt bei Kachel-Problemen zurück.

    Nur diese Fälle dürfen den Lauf beenden (Auftrag 2026-09-24): kein
    Speicherplatz, SSD weg, Anmeldung fehlgeschlagen.
    """
    if isinstance(fehler, (io.SSDNichtGefunden, io.SpeicherZuKnapp, AnmeldungFehlgeschlagen)):
        raise fehler
    if isinstance(fehler, EulaNotAccepted) or status in _HTTP_ANMELDUNG:
        raise AnmeldungFehlgeschlagen(
            f"NASA lehnt die Anmeldung ab ({fehler}). Zugangsdaten in .env prüfen "
            "und bei NASA Earthdata die Nutzungsbedingungen (EULA) für LAADS DAAC akzeptieren."
        ) from fehler
    if isinstance(fehler, OSError):
        if fehler.errno == errno.ENOSPC:
            raise io.SpeicherZuKnapp(
                "Schreibfehler: kein Speicherplatz mehr auf der SSD (ENOSPC). Lauf gestoppt. "
                "Bereits fertig verarbeitete Monate bleiben erhalten."
            ) from fehler
        # Ein Schreib- oder Verbindungsfehler kann auch heißen, dass die SSD
        # abgezogen wurde. aleph_data_dir() bricht dann mit SSDNichtGefunden ab.
        io.aleph_data_dir()


def _ist_vorlaeufig(fehler: BaseException, status: int | None) -> bool:
    """True, wenn Warten und Wiederholen sinnvoll ist (5xx, Zeitüberschreitung, Verbindung).

    HTTP 4xx (z. B. 404 „nicht gefunden") ist dauerhaft: Warten hilft nicht.
    Ausnahmen sind 408 und 429 (Anfragebegrenzung). 403 zählt einzeln als
    dauerhaft (nicht geprüft, ob NASA/CloudFront damit auch fehlende Dateien
    meldet); gehäufte 403 sind ein Zugangsproblem und werden vorher in
    `_lade_kachel` als Blocker gemeldet (`ZUGANG`). Bei 401 gilt der Login als
    abgelaufen, siehe `pruefe_blocker`. Ein
    unbekannter Fehlertyp (z. B. Programmfehler) gilt als dauerhaft, damit er
    nicht 30 Minuten je Kachel verbrennt.
    """
    if isinstance(fehler, (DownloadHaengt, ServiceOutage, OSError)):
        return True
    if isinstance(fehler, DownloadFailure):
        return status is None or status >= 500 or status in _HTTP_4XX_MIT_WARTEN
    return False


def _warte(sekunden: float, stopp: threading.Event | None) -> bool:
    """Wartet; gibt True zurück, wenn stattdessen `stopp` gesetzt wurde."""
    if stopp is None:
        time.sleep(sekunden)
        return False
    return stopp.wait(sekunden)


def _lade_kachel(
    granule,
    ziel_ordner: Path,
    datei_timeout_sekunden: float = DATEI_TIMEOUT_SEKUNDEN,
    retry_budget_sekunden: float = KACHEL_RETRY_BUDGET_SEKUNDEN,
    wartezeit_basis_sekunden: float = KACHEL_WARTEZEIT_BASIS_SEKUNDEN,
    wartezeit_max_sekunden: float = KACHEL_WARTEZEIT_MAX_SEKUNDEN,
    stopp: threading.Event | None = None,
    statistik: LadeStatistik | None = None,
) -> Path:
    """Lädt eine einzelne Kachel über `earthaccess.download`, mit eigenem
    Zeitlimit und hartnäckiger Wiederholung bei vorübergehenden Fehlern.

    `earthaccess.download` selbst kennt kein Zeitlimit (siehe Moduldoku
    oben). Jeder Versuch läuft deshalb in einem eigenen Thread; reagiert er
    nicht innerhalb von `datei_timeout_sekunden`, wird dieser Thread
    aufgegeben (er kann nicht sauber beendet werden, sein Ergebnis wird nur
    ignoriert) und ein neuer Versuch gestartet.

    Fehlerverhalten (Auftrag 2026-09-24):
    - vorübergehend (5xx, Zeitüberschreitung, Verbindung): warten
      (`wartezeit_basis_sekunden`, verdoppelt sich, höchstens
      `wartezeit_max_sekunden`) und wiederholen, bis `retry_budget_sekunden`
      (Versuche und Pausen zusammen) verbraucht sind. Dann
      `KachelNichtGeladen(dauerhaft=False)`.
    - dauerhaft (4xx wie 404): sofort `KachelNichtGeladen(dauerhaft=True)`,
      ohne Wartezeit.
    - Blocker (Login, Speicher, SSD): sofort weitergereicht, nicht wiederholt.
    `stopp`: wird er gesetzt (Monat abgebrochen), endet die Wiederholung.
    """
    verbraucht = 0.0
    versuch = 0
    while True:
        versuch += 1
        beginn = time.monotonic()
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(earthaccess.download, [granule], str(ziel_ordner))
        try:
            ergebnis = future.result(timeout=datei_timeout_sekunden)
            pool.shutdown(wait=False)
            ZUGANG.erfolg()
            return Path(ergebnis[0])
        except concurrent.futures.TimeoutError:
            pool.shutdown(wait=False, cancel_futures=True)
            fehler: BaseException = DownloadHaengt(
                f"Kachel reagiert seit über {datei_timeout_sekunden / 60:.0f} "
                f"Minuten nicht mehr (Versuch {versuch})."
            )
        except Exception as gefangen:  # bewusst breit: unten wird nach Art des Fehlers entschieden
            pool.shutdown(wait=False)
            fehler = gefangen
        verbraucht += time.monotonic() - beginn

        status = _statuscode(fehler)
        pruefe_blocker(fehler, status)
        if status == 403 and ZUGANG.melde_403() > ZUGANG_403_HINTEREINANDER_MAX:
            raise AnmeldungFehlgeschlagen(
                _zugang_pruefen_meldung(f"mehr als {ZUGANG_403_HINTEREINANDER_MAX} Kacheln hintereinander mit")
            ) from fehler
        if not _ist_vorlaeufig(fehler, status):
            raise KachelNichtGeladen(
                f"{fehler} (dauerhafter Fehler, Warten hilft nicht, kein weiterer Versuch)",
                dauerhaft=True,
                status=status,
            ) from fehler

        wartezeit = min(wartezeit_basis_sekunden * (2 ** min(versuch - 1, 30)), wartezeit_max_sekunden)
        if verbraucht + wartezeit > retry_budget_sekunden:
            raise KachelNichtGeladen(
                f"{fehler} (vorübergehender Fehler, nach {versuch} Versuchen in "
                f"{verbraucht / 60:.0f} Minuten aufgegeben)",
                dauerhaft=False,
                status=status,
            ) from fehler
        if _warte(wartezeit, stopp):
            raise KachelNichtGeladen(
                f"{fehler} (Monat wurde abgebrochen, keine weiteren Versuche)",
                dauerhaft=False,
                status=status,
            ) from fehler
        verbraucht += wartezeit
        if statistik is not None:
            statistik.wiederhole()


def _lade_und_pruefe_kachel(
    granule,
    soll: KachelSoll,
    ziel_ordner: Path,
    stopp: threading.Event | None = None,
    versuche: int = PRUEFSUMMEN_VERSUCHE,
    statistik: LadeStatistik | None = None,
) -> Path:
    """Lädt eine Kachel (`_lade_kachel`) und prüft Name, Größe und MD5 gegen den Katalog.

    Passt etwas nicht, wird die Datei verworfen und neu geladen, insgesamt
    höchstens `versuche` Mal; danach `KachelNichtGeladen` (nicht dauerhaft:
    ein späterer Versuch kann gelingen). Grund: 2019-05 lag unter dem Namen
    h12v09 byteidentisch die Kachel h13v04 (LOG.md 2026-09-25); erst die
    Ausrichtungsprüfung beim Verkleinern hatte das bemerkt.
    """
    grund = ""
    versuch = 0
    while versuch < versuche:
        versuch += 1
        zeitlimit = kachel_zeitlimit(getattr(soll, "groesse", None))
        pfad = _lade_kachel(
            granule, ziel_ordner, stopp=stopp, statistik=statistik,
            datei_timeout_sekunden=zeitlimit,
            retry_budget_sekunden=max(KACHEL_RETRY_BUDGET_SEKUNDEN, 3 * zeitlimit),
        )
        grund = _pruefe_gegen_katalog(pfad, soll)
        if grund is None:
            if statistik is not None:
                statistik.merke(pfad)
                statistik.neu(pfad.stat().st_size)
            return pfad
        pfad.unlink(missing_ok=True)
        if statistik is not None:
            statistik.verwerfe()
            if versuch >= versuche:
                statistik.verwerfe_endgueltig()
        if stopp is not None and stopp.is_set():
            break
    raise KachelNichtGeladen(
        f"{soll.datei}: passt nach {versuch} Versuch(en) nicht zum Katalog ({grund}); Datei verworfen.",
        dauerhaft=False,
    )


def _granule_dateiname(granule, jahr: int, monat: int) -> str | None:
    """Dateiname der .h5-Kachel dieses Monats aus den Download-Links (None, wenn keiner passt)."""
    for link in granule.data_links():
        if link.endswith(".h5") and _passt_zum_monat(link, jahr, monat):
            return link.rsplit("/", 1)[-1]
    return None


def _ist_lesbare_h5(pfad: Path) -> bool:
    try:
        with h5py.File(pfad, "r"):
            return True
    except OSError:
        return False


def _sichte_rohordner(ziel_ordner: Path) -> dict[str, Path]:
    """Sichtet einen Rohordner aus einem früheren Versuch und gibt die brauchbaren Kacheln zurück.

    earthaccess schreibt jede Kachel zuerst unter `partial_*` und benennt sie
    erst nach dem vollständigen Download um; eine Datei mit Kachelnamen ist
    also normalerweise vollständig. Zur Sicherheit wird trotzdem geprüft, dass
    sie sich als HDF5 öffnen lässt. Nicht lesbare Dateien und übrig gebliebene
    `partial_*`-Reste werden gelöscht (wertlos, und earthaccess würde eine
    vorhandene Datei sonst überspringen); alles andere bleibt unberührt.
    """
    if not ziel_ordner.exists():
        return {}
    brauchbar: dict[str, Path] = {}
    for pfad in sorted(ziel_ordner.iterdir()):
        if not pfad.is_file() or pfad.name.startswith("."):
            continue
        if pfad.name.startswith("partial_") or (pfad.suffix == ".h5" and not _ist_lesbare_h5(pfad)):
            pfad.unlink()
        elif pfad.suffix == ".h5":
            brauchbar[pfad.name] = pfad
    return brauchbar


def pruefe_unveraendert(
    geladen: dict[str, Path], soll_je_position: dict, abdruecke: dict[Path, tuple]
) -> dict[str, str]:
    """Positionen, deren Datei sich seit der Prüfung verändert hat UND nicht mehr zum Katalog passt.

    Unveränderter Abdruck: in Ordnung. Veränderter Abdruck: Größe und MD5 erneut
    prüfen (Datei wurde ersetzt, vielleicht mit gleichem Inhalt). Rückgabe:
    Position -> Grund, nur für Dateien, die jetzt nicht mehr passen oder fehlen.
    """
    schlecht: dict[str, str] = {}
    for position, pfad in geladen.items():
        vorher = abdruecke.get(pfad)
        jetzt = _abdruck(pfad)
        if vorher is not None and jetzt == vorher:
            continue
        if jetzt is None:
            schlecht[position] = f"{pfad.name}: nach der Prüfung verschwunden"
            continue
        grund = _pruefe_gegen_katalog(pfad, soll_je_position[position])
        if grund is not None:
            schlecht[position] = f"nach der Prüfung verändert und passt nicht mehr: {grund}"
        else:
            abdruecke[pfad] = jetzt
    return schlecht


def _sammle_kacheln(
    future_zu_position: dict,
    geladen: dict[str, Path],
    fehlgeschlagen: list,
    name: str,
    gesamt: int,
    statistik: LadeStatistik | None = None,
    stillstand_sekunden: float | None = None,
    notbremse_sekunden: float | None = None,
) -> bool:
    """Wartet auf die Kachel-Downloads eines Monats, mit Stillstands-Erkennung.

    Trägt jede fertige, geprüfte Kachel in `geladen` ein und jede gescheiterte in
    `fehlgeschlagen`. Fortschritt heißt: eine neue Kachel ist fertig und hat die
    Prüfung gegen Größe und MD5 bestanden; eine gescheiterte Kachel ist KEIN
    Fortschritt.

    - Kommt `stillstand_sekunden` lang (Standard `STILLSTAND_SEKUNDEN`) keine
      neue geprüfte Kachel dazu: `DownloadHaengt`.
    - Dauert das Ganze länger als `notbremse_sekunden` (Standard
      `MONAT_NOTBREMSE_SEKUNDEN`), obwohl Kacheln kommen: `DownloadZuLangsam`.
    - Echte Blocker (SSD, Speicher, Anmeldung) werden sofort weitergereicht.

    Rückgabe: True, wenn nach `MAX_GESCHEITERTE_KACHELN_JE_MONAT` gescheiterten
    Kacheln abgebrochen wurde (Server scheint gestört), sonst False.
    Gemessen mit der monotonen Uhr (eine Uhrumstellung verfälscht nichts).
    """
    stillstand = STILLSTAND_SEKUNDEN if stillstand_sekunden is None else stillstand_sekunden
    notbremse = MONAT_NOTBREMSE_SEKUNDEN if notbremse_sekunden is None else notbremse_sekunden
    beginn = time.monotonic()
    letzter_fortschritt = beginn
    ausstehend = set(future_zu_position)

    def rate_text() -> str:
        if statistik is None:
            return ""
        dauer = time.monotonic() - beginn
        return f", {statistik.neu_bytes / 1e6 / dauer:.2f} MB/s im Schnitt seit Beginn dieses Versuchs" if dauer > 0 else ""

    while ausstehend:
        jetzt = time.monotonic()
        if jetzt - beginn >= notbremse:
            raise DownloadZuLangsam(
                f"{name}: Notbremse - der Download dieses Monats läuft seit über "
                f"{notbremse / 3600:.0f} Stunden, obwohl noch Kacheln ankommen "
                f"({len(geladen)} von {gesamt} Kacheln fertig{rate_text()}). Die Leitung ist "
                "vermutlich sehr langsam. Die geladenen Kacheln bleiben im Rohordner; der Monat "
                "wird später erneut versucht."
            )
        if jetzt - letzter_fortschritt >= stillstand:
            raise DownloadHaengt(
                f"{name}: Stillstand - seit {stillstand / 60:.0f} Minuten ist keine neue, geprüfte "
                f"Kachel mehr fertig geworden ({len(geladen)} von {gesamt} Kacheln fertig{rate_text()}). "
                "Die geladenen Kacheln bleiben im Rohordner; der Monat wird später erneut versucht."
            )
        warte = min(stillstand - (jetzt - letzter_fortschritt), notbremse - (jetzt - beginn))
        fertig, ausstehend = concurrent.futures.wait(
            ausstehend, timeout=max(warte, 0), return_when=concurrent.futures.FIRST_COMPLETED
        )
        for future in fertig:  # erst die ganze Runde eintragen (Auflage A3), dann entscheiden
            position = future_zu_position[future]
            try:
                geladen[position] = future.result()
                letzter_fortschritt = time.monotonic()
            except (io.SSDNichtGefunden, io.SpeicherZuKnapp, AnmeldungFehlgeschlagen):
                raise  # echter Blocker: der Lauf endet
            except Exception as fehler:
                fehlgeschlagen.append((position, fehler))
        if len(fehlgeschlagen) >= MAX_GESCHEITERTE_KACHELN_JE_MONAT:
            return True  # Server scheint gestört: Rest des Monats nicht mehr versuchen
    return False


def lade_monat(
    jahr: int,
    monat: int,
    ziel_ordner: Path,
    gleichzeitige_downloads: int = GLEICHZEITIGE_DOWNLOADS_STANDARD,
    melde=None,
    positionen: set[str] | None = None,
) -> MonatsLadung:
    """Lädt alle VNP46A3-Kacheln eines Monats global nach `ziel_ordner`.

    Meldet sich vorher bei NASA Earthdata an (dieselbe Ladelogik wie alle
    Layer, aleph/core/auth.py). Bricht mit `AnmeldungFehlgeschlagen` ab, wenn
    der Login fehlschlägt.

    Kachelliste (geändert 2026-09-25, Befund Kachel-Vollständigkeit): alle
    Granulate des Monats über alle Katalogseiten, abgeglichen mit der vom
    Katalog gemeldeten Trefferzahl (`_katalog_abfrage`). Vor jedem Download
    wird geprüft, dass jede gemeldete Position in der Referenzliste steht
    (`ReferenzlisteVeraltet` sonst) und keine Position doppelt vorkommt.

    Jede Kachel wird einzeln geladen, mit eigenem Zeitlimit und
    hartnäckiger Wiederholung bei vorübergehenden Fehlern (`_lade_kachel`),
    danach gegen Name, Größe und MD5 aus dem Katalog geprüft und bei
    Abweichung bis zu `PRUEFSUMMEN_VERSUCHE` Mal neu geladen
    (`_lade_und_pruefe_kachel`). Höchstens `gleichzeitige_downloads` Kacheln
    gleichzeitig (Vorschlag 2-4, siehe Moduldoku oben).

    Wiederaufnahme: Liegt im `ziel_ordner` schon etwas von einem früheren
    Versuch, werden die brauchbaren Kacheln (`_sichte_rohordner`) nach
    derselben Katalogprüfung wiederverwendet; passt eine nicht, wird sie
    gelöscht und neu geladen. Der Rohordner selbst wird hier nie gelöscht.

    Danach `pruefe_vollstaendigkeit`: gegen die Trefferzahl des Katalogs und
    gegen die Referenzliste der Positionen. Rückgabe: `MonatsLadung` mit den
    Dateien und dem Zustand jeder Position (fürs Manifest).

    `melde` (optional) bekommt Textbausteine fürs Protokoll des
    Hintergrund-Laufs.

    `positionen` (optional, seit 2026-09-26): nur diese Kachelpositionen laden
    und prüfen (Vorrang einer Region). Die Katalogabfrage bleibt vollständig
    (alle Seiten, Trefferzahl, unbekannte Positionen sind weiterhin ein Fehler);
    danach werden Katalog UND Referenzliste auf `positionen` beschnitten, und
    die Vollständigkeit wird für diese Teilmenge genauso streng geprüft wie
    sonst für den ganzen Monat. `positionen` muss Teilmenge der Referenzliste
    sein.

    Fehler:
    - `AnmeldungFehlgeschlagen`, `io.SpeicherZuKnapp`, `io.SSDNichtGefunden`:
      echte Blocker, sofort weitergereicht. Dazu zählt gehäuftes HTTP 403
      (mehr als 5 hintereinander oder alle Kacheln des Monats), einzelne 403
      bleiben Kachelfehler.
    - `KatalogUnvollstaendig`, `ReferenzlisteVeraltet`: Kachelliste nicht
      belastbar, nichts geladen.
    - `KachelnFehlen`: einzelne Kacheln fehlen auch nach allen Versuchen (oder
      der Monat wurde nach `MAX_GESCHEITERTE_KACHELN_JE_MONAT` Fehlschlägen
      abgebrochen). Der Zustand je Position hängt an der Ausnahme
      (`zustaende`); das Manifest schreibt der Aufrufer (vnp46a3_lauf.py).
      Kein Blocker; die geladenen Kacheln bleiben im Rohordner.
    - `DownloadHaengt`: seit `STILLSTAND_SEKUNDEN` (30 Minuten) ist keine
      neue, geprüfte Kachel mehr fertig geworden (Stillstand).
      `DownloadZuLangsam` (Unterfall): der Monat lädt länger als
      `MONAT_NOTBREMSE_SEKUNDEN` (12 Stunden), obwohl Kacheln ankommen.
      Beides kein Blocker; der Monat wird zurückgestellt.

    Am Ende des Downloads (auch bei Abbruch) meldet `melde` eine Zeile
    „Download-Statistik“: neu geladene Kacheln, GB, MB/s, nach Größen-/MD5-
    Prüfung verworfene Kacheln und Wiederholungen.
    """
    if not earthdata_login():
        raise AnmeldungFehlgeschlagen("NASA-Earthdata-Login fehlgeschlagen. Zugangsdaten in .env prüfen.")
    gemeldet, alle = _katalog_abfrage(jahr, monat)
    # Sicherung: Granulate anderer Monate aussortieren. Das geschieht auf der
    # VOLLSTÄNDIGEN Liste; eine Begrenzung gibt es nicht mehr.
    treffer = [g for g in alle if any(_passt_zum_monat(link, jahr, monat) for link in g.data_links())]
    aussortiert = len(alle) - len(treffer)
    if aussortiert or len(treffer) != gemeldet:
        # Mit der Zeitspanne ab 00:00:01 darf hier nichts aussortiert werden.
        # Kommt doch etwas, ist die Annahme über die Zeitfenster falsch (oder
        # ein Dateiname anders); stilles Aussortieren könnte eine Position
        # still zu „beim Anbieter nicht vorhanden" machen.
        fremd = sorted(
            link.rsplit("/", 1)[-1]
            for g in alle if g not in treffer
            for link in g.data_links() if link.endswith(".h5")
        )
        raise MonatUnvollstaendig(
            f"{jahr:04d}-{monat:02d}: Der Katalog meldet {gemeldet} Treffer, davon passen "
            f"{len(treffer)} nach dem Dateinamen zu diesem Monat (z. B. fremd: {', '.join(fremd[:3]) or '-'}). "
            "Zeitspanne der Abfrage prüfen; nichts geladen."
        )

    referenz = lies_referenz_positionen()
    soll_je_position: dict[str, KachelSoll] = {}
    granule_je_position: dict[str, object] = {}
    name_je_position: dict[str, str] = {}
    for granule in treffer:
        name = _granule_dateiname(granule, jahr, monat)
        if name is None:
            raise MonatUnvollstaendig(f"{jahr:04d}-{monat:02d}: Katalogeintrag ohne .h5-Link dieses Monats.")
        position = _position(name)
        if position in granule_je_position:
            raise MonatUnvollstaendig(
                f"{jahr:04d}-{monat:02d}: Position {position} kommt im Katalog doppelt vor "
                f"({name_je_position[position]} und {name}). "
                "Welche Version gilt, ist nicht entscheidbar; nichts geladen."
            )
        granule_je_position[position] = granule
        name_je_position[position] = name
    unbekannt = sorted(set(granule_je_position) - referenz)
    if unbekannt:
        raise ReferenzlisteVeraltet(
            f"{jahr:04d}-{monat:02d}: Der Katalog meldet {len(unbekannt)} Kachelposition(en), die nicht in "
            f"{REFERENZ_KACHELN_DATEI.name} stehen: {', '.join(unbekannt)}. Referenzliste prüfen und "
            "ergänzen (Annahme über den Anbieter); nichts geladen."
        )
    teil_text = ""
    katalog_positionen = set(granule_je_position)
    if positionen is not None:
        # Auflage B2 (statistik-pruefer 2026-09-26): Die Grenze für „beim Anbieter
        # nicht vorhanden“ gilt für den GANZEN Monat, auch wenn nur eine Stufe
        # geladen wird. Sonst könnten zwei Stufen zusammen doppelt so viele
        # fehlende Positionen durchlassen wie ein ganzer Monat.
        pruefe_fehlende_beim_anbieter(jahr, monat, referenz - katalog_positionen)
        fremd = sorted(set(positionen) - referenz)
        if fremd or not positionen:
            raise ReferenzlisteVeraltet(
                f"{jahr:04d}-{monat:02d}: Die verlangten Positionen sind leer oder stehen nicht in "
                f"{REFERENZ_KACHELN_DATEI.name}: {', '.join(fremd[:5])}. Nichts geladen."
            )
        katalog_gesamt = len(treffer)
        granule_je_position = {p: g for p, g in granule_je_position.items() if p in positionen}
        treffer = list(granule_je_position.values())
        referenz = referenz & set(positionen)
        teil_text = f" für {len(referenz)} ausgewählte Positionen (Katalog gesamt {katalog_gesamt})"

    fehlgruende: dict[str, str] = {}
    for position, granule in granule_je_position.items():
        try:
            soll_je_position[position] = _katalog_soll(granule)
        except KachelNichtGeladen as fehler:
            fehlgruende[position] = str(fehler)

    # Vor dem Download: passt die Katalogantwort überhaupt zur Referenzliste?
    # (Sonst stellt sich eine abgeschnittene Antwort erst nach Stunden heraus.)
    pruefe_fehlende_beim_anbieter(jahr, monat, set(referenz) - set(granule_je_position))

    ziel_ordner.mkdir(parents=True, exist_ok=True)
    if melde is not None:
        melde(
            f"{len(treffer)} Kacheln bei NASA gemeldet{teil_text} (Katalog: {gemeldet} Treffer, alle geholt; "
            f"Referenzliste {len(referenz)} Positionen), Download beginnt."
        )

    statistik = LadeStatistik()
    vorhanden = _sichte_rohordner(ziel_ordner)
    geladen: dict[str, Path] = {}
    offen: list[str] = []
    verworfen = 0
    for position, soll in soll_je_position.items():
        pfad = vorhanden.get(soll.datei)
        if pfad is not None:
            if _pruefe_gegen_katalog(pfad, soll) is None:
                geladen[position] = pfad
                statistik.merke(pfad)
                continue
            pfad.unlink()  # passt nicht zum Katalog: wertlos, neu laden
            verworfen += 1
        offen.append(position)
    if (geladen or verworfen) and melde is not None:
        melde(
            f"{len(geladen)} Kacheln aus einem früheren Versuch schon vorhanden und "
            f"gültig (Größe und MD5 geprüft), {verworfen} verworfen, weil sie nicht zum Katalog "
            f"passten, {len(offen)} werden noch geladen."
        )

    beginn = time.monotonic()
    stopp = threading.Event()
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, gleichzeitige_downloads))
    future_zu_position = {
        pool.submit(
            _lade_und_pruefe_kachel, granule_je_position[p], soll_je_position[p], ziel_ordner,
            stopp=stopp, statistik=statistik,
        ): p
        for p in offen
    }

    fehlgeschlagen: list[tuple[str, Exception]] = []
    sammeln_ok = False
    try:
        abgebrochen = _sammle_kacheln(
            future_zu_position, geladen, fehlgeschlagen, f"{jahr:04d}-{monat:02d}", len(treffer), statistik
        )
        sammeln_ok = True
    finally:
        # Läuft auch bei Stillstand oder Blocker: wartende Kacheln nicht mehr
        # starten, laufende Wiederholungen beenden (die gerade übertragenen
        # Kacheln laden im Hintergrund noch zu Ende und bleiben im Rohordner).
        stopp.set()
        pool.shutdown(wait=False, cancel_futures=True)
        dauer = time.monotonic() - beginn
        if not sammeln_ok and melde is not None and offen:
            melde(statistik.text(dauer, "abgebrochen"))

    if (
        fehlgeschlagen
        and len(fehlgeschlagen) == len(treffer)
        and all(isinstance(f, KachelNichtGeladen) and f.status == 403 for _, f in fehlgeschlagen)
    ):
        raise AnmeldungFehlgeschlagen(
            _zugang_pruefen_meldung(f"alle {len(treffer)} Kacheln von {jahr:04d}-{monat:02d} mit")
        )

    for position, fehler in fehlgeschlagen:
        fehlgruende[position] = str(fehler)[:300]

    # Auflage statistik-pruefer 2026-09-26 (A1): Eine geprüfte Datei kann danach
    # noch ersetzt worden sein (aufgegebener Download-Faden wird doch fertig und
    # benennt seine Datei um). Dann Größe und MD5 erneut prüfen; passt es nicht,
    # gilt die Kachel als nicht geladen.
    veraendert = pruefe_unveraendert(geladen, soll_je_position, statistik.abdruecke)
    for position, grund in veraendert.items():
        del geladen[position]
        fehlgruende[position] = grund
    if melde is not None and offen:
        vollstaendig = not abgebrochen and not fehlgeschlagen and not veraendert
        melde(statistik.text(dauer, "vollständig geladen" if vollstaendig else "abgebrochen"))
    for position in granule_je_position:
        if position not in geladen and position not in fehlgruende:
            fehlgruende[position] = "nicht mehr versucht (Monat nach zu vielen Fehlschlägen abgebrochen)"

    if fehlgruende:
        zustaende = kachel_zustaende(soll_je_position, geladen, referenz, fehlgruende, set(granule_je_position))
        dauerhaft = sum(1 for _, f in fehlgeschlagen if isinstance(f, KachelNichtGeladen) and f.dauerhaft)
        dauerhaft += len(set(fehlgruende) - {p for p, _ in fehlgeschlagen} - set(offen))  # ohne Katalog-Sollwerte
        vorlaeufig = len(fehlgruende) - dauerhaft
        abbruch = (
            f" Der Monat wurde nach {MAX_GESCHEITERTE_KACHELN_JE_MONAT} gescheiterten Kacheln "
            "abgebrochen, weil der Server gestört scheint (übrige Kacheln nicht mehr versucht)."
            if abgebrochen
            else ""
        )
        beispiel = next(iter(fehlgruende.values()))
        raise KachelnFehlen(
            f"{jahr:04d}-{monat:02d}: {len(fehlgruende)} von {len(treffer)} Kacheln fehlen "
            f"({vorlaeufig} vorübergehend nicht ladbar, {dauerhaft} dauerhaft "
            f"nicht ladbar).{abbruch} Beispiel: {beispiel[:300]}. "
            f"{len(geladen)} Kacheln bleiben im Rohordner. Zustand je Position im Manifest.",
            dauerhaft=dauerhaft,
            vorlaeufig=vorlaeufig,
            zustaende=zustaende,
        )

    zustaende = pruefe_vollstaendigkeit(jahr, monat, len(treffer), soll_je_position, geladen, referenz)
    return MonatsLadung(
        dateien=sorted(geladen.values()), zustaende=zustaende,
        katalog_positionen=katalog_positionen, abdruecke=dict(statistik.abdruecke),
    )


def _passt_zum_monat(link: str, jahr: int, monat: int) -> bool:
    treffer = _KACHEL_DATUM.search(link)
    if not treffer:
        return False
    datum = date(int(treffer.group(1)), 1, 1) + timedelta(days=int(treffer.group(2)) - 1)
    return datum.year == jahr and datum.month == monat


def kachel_zustaende(
    katalog: dict[str, KachelSoll],
    geladen: dict[str, Path],
    referenz: set[str],
    fehlgruende: dict[str, str] | None = None,
    katalog_positionen: set[str] | None = None,
) -> dict[str, KachelEintrag]:
    """Ordnet jeder Position (Referenzliste und Katalog) genau einen Zustand zu.

    - `geladen`: im Katalog, Datei da und ihr Name gleich dem Katalognamen
      (Größe und MD5 wurden beim Laden geprüft).
    - `beim Anbieter nicht vorhanden`: in der Referenzliste, aber nicht im Katalog.
    - `nicht geladen`: im Katalog, aber keine passende Datei (Grund angegeben).
    `katalog_positionen`: Positionen im Katalog, auch solche ohne Sollwerte
    (fehlt es, gelten die Schlüssel von `katalog`).
    """
    fehlgruende = fehlgruende or {}
    im_katalog = set(katalog) if katalog_positionen is None else set(katalog_positionen)
    zustaende: dict[str, KachelEintrag] = {}
    for position in sorted(referenz | im_katalog):
        soll = katalog.get(position)
        if position not in im_katalog:
            zustaende[position] = KachelEintrag(ZUSTAND_NICHT_BEIM_ANBIETER)
        elif position in fehlgruende:
            zustaende[position] = KachelEintrag(ZUSTAND_NICHT_GELADEN, soll, fehlgruende[position])
        elif position not in geladen:
            zustaende[position] = KachelEintrag(ZUSTAND_NICHT_GELADEN, soll, "keine Datei geladen")
        elif soll is not None and geladen[position].name != soll.datei:
            zustaende[position] = KachelEintrag(
                ZUSTAND_NICHT_GELADEN, soll, f"andere Datei geladen: {geladen[position].name}"
            )
        else:
            zustaende[position] = KachelEintrag(ZUSTAND_GELADEN, soll)
    return zustaende


def pruefe_vollstaendigkeit(
    jahr: int,
    monat: int,
    katalog_treffer: int,
    katalog: dict[str, KachelSoll],
    geladen: dict[str, Path],
    referenz: set[str],
) -> dict[str, KachelEintrag]:
    """Prüft einen Monat gegen den Katalog UND gegen die Referenzliste der Positionen.

    Berichtigt 2026-09-25: Bis dahin wurde nur gegen die Länge der schon
    abgeschnittenen Kachelliste geprüft (`count=1000`), also gegen sich
    selbst; so galten Monate mit 99 von 540 Kacheln als fertig. Jetzt:

    1. `katalog_treffer` (Zahl der Granulate dieses Monats laut Katalog, alle
       Seiten, abgeglichen mit CMR-Hits in `_katalog_abfrage`) muss gleich der
       Zahl verschiedener Positionen in `katalog` sein.
    2. Jede Position der Referenzliste und des Katalogs bekommt genau einen
       Zustand (`kachel_zustaende`). Positionen im Katalog, die in der
       Referenzliste fehlen, sind ein Fehler (`ReferenzlisteVeraltet`), kein
       stilles Übergehen.
    3. `beim Anbieter nicht vorhanden` ist nur in engen Grenzen erlaubt
       (`pruefe_fehlende_beim_anbieter`: nördlich 50° N, April bis August,
       höchstens 10 Positionen; gemessen: 1 bis 6 in Mai bis Juli). Mehr
       fehlende Positionen sprechen für eine lückenhafte Katalogantwort, nicht
       für den Anbieter: Abbruch.
    4. Der Monat ist nur vollständig, wenn keine Position `nicht geladen` ist.

    Rückgabe: Zustand je Position. Sonst `MonatUnvollstaendig` (mit
    `zustaende`, fürs Manifest).
    """
    name = f"{jahr:04d}-{monat:02d}"
    if len(katalog) != katalog_treffer:
        raise MonatUnvollstaendig(
            f"{name}: Der Katalog meldet {katalog_treffer} Kacheln, verschieden sind davon {len(katalog)} "
            "Positionen. Nichts wird als fertig markiert."
        )
    unbekannt = sorted(set(katalog) - referenz)
    if unbekannt:
        raise ReferenzlisteVeraltet(
            f"{name}: Katalogpositionen außerhalb der Referenzliste: {', '.join(unbekannt)}."
        )
    pruefe_fehlende_beim_anbieter(jahr, monat, set(referenz) - set(katalog))
    zustaende = kachel_zustaende(katalog, geladen, referenz)
    fehlend = sorted(p for p, e in zustaende.items() if e.zustand == ZUSTAND_NICHT_GELADEN)
    if fehlend:
        raise MonatUnvollstaendig(
            f"{name}: {len(fehlend)} von {katalog_treffer} Kacheln laut Katalog sind nicht geladen "
            f"(z. B. {', '.join(fehlend[:5])}). Nichts wird als fertig markiert.",
            zustaende,
        )
    return zustaende


def pruefe_fehlende_beim_anbieter(jahr: int, monat: int, fehlend: set[str]) -> None:
    """Bricht ab, wenn die im Katalog fehlenden Referenzpositionen nicht zum bekannten Muster passen.

    Erlaubt: höchstens `NICHT_BEIM_ANBIETER_MAX` Positionen, alle in den
    Zeilen `NICHT_BEIM_ANBIETER_ZEILEN` (nördlich 50° N), nur in den Monaten
    `NICHT_BEIM_ANBIETER_MONATE`. Alles andere: `MonatUnvollstaendig`.
    """
    if not fehlend:
        return
    name = f"{jahr:04d}-{monat:02d}"
    unerwartet = sorted(p for p in fehlend if int(p[4:6]) not in NICHT_BEIM_ANBIETER_ZEILEN)
    gruende = []
    if len(fehlend) > NICHT_BEIM_ANBIETER_MAX:
        gruende.append(f"{len(fehlend)} Positionen (erlaubt höchstens {NICHT_BEIM_ANBIETER_MAX})")
    if monat not in NICHT_BEIM_ANBIETER_MONATE:
        gruende.append("außerhalb April bis August")
    if unerwartet:
        gruende.append(f"südlich 50° N: {', '.join(unerwartet[:5])}")
    if gruende:
        raise MonatUnvollstaendig(
            f"{name}: Im Katalog fehlen {len(fehlend)} Positionen der Referenzliste "
            f"(z. B. {', '.join(sorted(fehlend)[:5])}); das passt nicht zu „beim Anbieter nicht "
            f"vorhanden\" ({'; '.join(gruende)}). Vermutlich ist die Katalogantwort lückenhaft. "
            "Nichts wird als fertig markiert; später erneut versuchen."
        )


def manifest_pfad(jahr: int, monat: int, zusatz: str = "") -> Path:
    """`zusatz` (z. B. „_afrika_europa_asien“, „_rest“) trennt die Manifeste der Stufen."""
    return io.aleph_data_dir() / "protokoll" / "manifeste" / "vnp46a3" / f"{jahr:04d}-{monat:02d}{zusatz}.tsv"


def schreibe_manifest(
    jahr: int, monat: int, zustaende: dict[str, KachelEintrag], hinweis: str = "", zusatz: str = ""
) -> Path:
    """Schreibt Zustand, Dateiname, Größe und MD5 je Kachelposition (Tabulator-getrennt).

    Geschrieben vom Hintergrund-Lauf, bevor die Rohdaten gelöscht werden, und
    auch für Monate, die unvollständig bleiben (dann mit `nicht geladen` und
    Grund). Größe und MD5
    stammen aus dem NASA-Katalog und wurden beim Laden an der Datei geprüft;
    so lässt sich später ohne Rohdaten nachweisen, was geladen wurde. Die
    Erzeugungszeitstempel von NASA stehen im Dateinamen (docs/sources/vnp46a3.md
    Abschnitt 10). Ältere Manifeste (vor 2026-09-25) sind `.txt` mit reinen
    Dateinamen und bleiben unverändert liegen. `hinweis` kommt als zweite
    Kopfzeile dazu (z. B. welchen Stand der Würfel beim Schreiben hatte).
    """
    ziel = manifest_pfad(jahr, monat, zusatz)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    zaehler = {z: sum(1 for e in zustaende.values() if e.zustand == z) for z in (
        ZUSTAND_GELADEN, ZUSTAND_NICHT_BEIM_ANBIETER, ZUSTAND_NICHT_GELADEN
    )}
    zeilen = [
        f"# VNP46A3 {jahr:04d}-{monat:02d}, Referenzliste {REFERENZ_KACHELN_DATEI.name}, "
        + ", ".join(f"{z}: {n}" for z, n in zaehler.items()),
    ]
    if hinweis:
        zeilen.append(f"# {hinweis}")
    zeilen.append("position\tzustand\tdatei\tgroesse_bytes\tmd5\tgrund")
    for position, eintrag in sorted(zustaende.items()):
        soll = eintrag.soll
        zeilen.append(
            "\t".join([
                position,
                eintrag.zustand,
                soll.datei if soll else "-",
                str(soll.groesse) if soll else "-",
                soll.md5 if soll else "-",
                eintrag.grund.replace("\t", " ").replace("\n", " ") or "-",
            ])
        )
    ziel.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return ziel


class MonatStimmtNicht(RuntimeError):
    """Die Kacheln gehören nicht zum angefragten Monat oder nicht alle zum selben Monat."""


def verkleinere_monat(kachel_dateien: list[Path], erwarteter_monat: tuple[int, int] | None = None) -> xr.Dataset:
    """Baut aus den Kacheln eines Monats ein globales 0,25°-Gitter (ein Zeitschritt).

    Prüft vorher, dass alle Kacheln im selben Monat liegen (bei
    `erwarteter_monat`: genau in diesem), und dass keine Kachelposition
    (h, v) doppelt vorkommt. Eine doppelte Kachel würde sonst stumm die
    zuerst gelesene überschreiben, und die Vollständigkeitsprüfung
    (Zahl gleich Zahl) würde es nicht bemerken.
    """
    if not kachel_dateien:
        raise ValueError("Keine Kacheln übergeben.")
    monate = {_kachel_jahr_monat(p) for p in kachel_dateien}
    if len(monate) != 1 or (erwarteter_monat is not None and monate != {erwarteter_monat}):
        raise MonatStimmtNicht(
            f"Kacheln aus den Monaten {sorted(monate)} statt aus "
            f"{erwarteter_monat if erwarteter_monat else 'einem einzigen Monat'}. Nichts geschrieben."
        )
    positionen = [_kachel_position(p)[2:] for p in kachel_dateien]
    if len(set(positionen)) != len(positionen):
        raise MonatStimmtNicht("Mindestens eine Kachelposition (h, v) kommt doppelt vor. Nichts geschrieben.")
    jahr, monat = next(iter(monate))

    variablen: dict[str, np.ndarray] = {}
    for name in FELD_TRIPEL:
        variablen[f"{name}_mittel"] = np.full((GITTER_BREITE, GITTER_LAENGE), np.nan, dtype="float32")
        variablen[f"{name}_mittel_beobachtet"] = np.full(
            (GITTER_BREITE, GITTER_LAENGE), np.nan, dtype="float32"
        )
        variablen[f"{name}_gueltige_pixel"] = np.zeros((GITTER_BREITE, GITTER_LAENGE), dtype="int16")
        variablen[f"{name}_beobachtete_pixel"] = np.zeros(
            (GITTER_BREITE, GITTER_LAENGE), dtype="int16"
        )
        variablen[f"{name}_num"] = np.full((GITTER_BREITE, GITTER_LAENGE), np.nan, dtype="float32")
        variablen[f"{name}_aufgefuellt_pixel"] = np.zeros((GITTER_BREITE, GITTER_LAENGE), dtype="int16")

    for pfad in kachel_dateien:
        zeile0, spalte0, h, v = _kachel_position(pfad)
        with h5py.File(pfad, "r") as datei:
            _pruefe_ausrichtung(datei[HDF_GRUPPE], pfad, h, v)
        bloecke = _lies_kachel(pfad)
        for schluessel, block in bloecke.items():
            variablen[schluessel][zeile0 : zeile0 + ZELLEN_PRO_KACHEL, spalte0 : spalte0 + ZELLEN_PRO_KACHEL] = block

    breite, laenge = _gitter_koordinaten()
    zeit = [np.datetime64(f"{jahr:04d}-{monat:02d}-01")]

    daten_vars = {
        schluessel: (("zeit", "breite", "laenge"), werte[np.newaxis, :, :])
        for schluessel, werte in variablen.items()
    }
    return xr.Dataset(
        data_vars=daten_vars,
        coords={"zeit": zeit, "breite": breite, "laenge": laenge},
        attrs={"quelle": META["quelle"], "einheit_mittel": META["einheit"]},
    )


def _wuerfel_pfad() -> Path:
    return io.wuerfel_pfad("vnp46a3.zarr")


def zeitachse() -> np.ndarray:
    """Die feste Zeitachse des Würfels: jeder Monat 2013-01 bis 2025-12, je der Monatserste."""
    start = np.datetime64(f"{ZEITACHSE_START[0]:04d}-{ZEITACHSE_START[1]:02d}", "M")
    ende = np.datetime64(f"{ZEITACHSE_ENDE[0]:04d}-{ZEITACHSE_ENDE[1]:02d}", "M")
    return np.arange(start, ende + 1).astype("datetime64[ns]")


def _gitter_koordinaten() -> tuple[np.ndarray, np.ndarray]:
    breite = 90 - ZELLGROESSE / 2 - np.arange(GITTER_BREITE) * ZELLGROESSE
    laenge = -180 + ZELLGROESSE / 2 + np.arange(GITTER_LAENGE) * ZELLGROESSE
    return breite, laenge


def _wuerfel_variablen() -> dict[str, str]:
    """Alle Datenvariablen des Würfels mit ihrem Datentyp."""
    variablen: dict[str, str] = {}
    for name in FELD_TRIPEL:
        variablen[f"{name}_mittel"] = "float32"
        variablen[f"{name}_mittel_beobachtet"] = "float32"
        variablen[f"{name}_gueltige_pixel"] = "int16"
        variablen[f"{name}_beobachtete_pixel"] = "int16"
        variablen[f"{name}_num"] = "float32"
        variablen[f"{name}_aufgefuellt_pixel"] = "int16"
    return variablen


def _monat_index(jahr: int, monat: int) -> int:
    """Position eines Monats auf der Zeitachse; bricht ab, wenn er nicht darauf liegt."""
    ziel = np.datetime64(f"{jahr:04d}-{monat:02d}-01", "ns")
    treffer = np.flatnonzero(zeitachse() == ziel)
    if len(treffer) != 1:
        raise MonatAusserhalbZeitachse(
            f"{jahr:04d}-{monat:02d} liegt nicht auf der Zeitachse des Würfels "
            f"({ZEITACHSE_START[0]:04d}-{ZEITACHSE_START[1]:02d} bis "
            f"{ZEITACHSE_ENDE[0]:04d}-{ZEITACHSE_ENDE[1]:02d})."
        )
    return int(treffer[0])


def _lege_wuerfel_an(pfad: Path) -> None:
    """Legt den leeren Würfel mit fester Zeitachse an (Werte NaN, Zähler 0, nichts fertig).

    Wird zuerst an einem Hilfspfad gebaut und erst am Ende umbenannt, damit
    ein Abbruch beim Anlegen keinen halbfertigen Würfel am echten Pfad
    hinterlässt. Nur Metadaten und leere Blöcke: dauert Sekunden, braucht
    keinen nennenswerten Arbeitsspeicher (`np.broadcast_to` belegt keinen
    eigenen Speicher, leere Blöcke schreibt Zarr nicht).
    """
    achse = zeitachse()
    breite, laenge = _gitter_koordinaten()
    hilfspfad = pfad.with_name(pfad.name + ".neu")
    if hilfspfad.exists():
        shutil.rmtree(hilfspfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)

    xr.Dataset(
        coords={"zeit": achse, "breite": breite, "laenge": laenge},
        attrs={"quelle": META["quelle"], "einheit_mittel": META["einheit"]},
    ).to_zarr(hilfspfad, mode="w")
    form = (len(achse), GITTER_BREITE, GITTER_LAENGE)
    for name, dtyp in _wuerfel_variablen().items():
        leerwert = np.float32(np.nan) if dtyp == "float32" else np.int16(0)
        xr.Dataset({name: (WUERFEL_DIMS, np.broadcast_to(leerwert, form))}).to_zarr(
            hilfspfad, mode="a", encoding={name: {"chunks": WUERFEL_CHUNKS}}
        )
    xr.Dataset({FERTIG_VARIABLE: (("zeit",), np.zeros(len(achse), dtype="int8"))}).to_zarr(
        hilfspfad, mode="a"
    )
    os.replace(hilfspfad, pfad)


def _pruefe_wuerfel_format(pfad: Path) -> None:
    """Bricht mit klarer Meldung ab, wenn der Würfel nicht den festen Aufbau hat.

    Fängt vor allem den alten Aufbau (Monate hinten angehängt, ohne
    `monat_fertig`) ab: Ein solcher Würfel darf nicht stillschweigend
    weiterbenutzt werden, sonst landen neue Monate an falscher Stelle.
    """
    with xr.open_zarr(pfad, chunks=None) as ds:
        fehlend = [v for v in [*_wuerfel_variablen(), FERTIG_VARIABLE] if v not in ds]
        achse_ok = ds.sizes.get("zeit") == len(zeitachse()) and np.array_equal(
            ds["zeit"].values, zeitachse()
        )
    if fehlend or not achse_ok:
        raise WuerfelFormat(
            f"Der Würfel {pfad} hat nicht den erwarteten Aufbau (feste Zeitachse "
            f"{ZEITACHSE_START[0]:04d}-{ZEITACHSE_START[1]:02d} bis "
            f"{ZEITACHSE_ENDE[0]:04d}-{ZEITACHSE_ENDE[1]:02d} mit `{FERTIG_VARIABLE}`"
            f"{'; fehlende Variablen: ' + ', '.join(fehlend) if fehlend else ''}"
            f"{'; Zeitachse stimmt nicht' if not achse_ok else ''}). "
            "Nichts wurde geschrieben. Ein Würfel im alten Aufbau muss zuerst "
            "übernommen oder verschoben werden."
        )


def vorhandene_monate() -> set[tuple[int, int]]:
    """Monate, die im Würfel auf der SSD als fertig markiert sind (für den Neustart).

    Zählt nur Monate mit `monat_fertig == MONAT_FERTIG` (1), nicht alle Plätze
    der Zeitachse und nicht die als unvollständig markierten (2) oder gerade
    geschriebenen (3).
    """
    pfad = _wuerfel_pfad()
    if not pfad.exists():
        return set()
    _pruefe_wuerfel_format(pfad)
    with xr.open_zarr(pfad, chunks=None) as ds:
        zeiten = ds["zeit"].values
        fertig = ds[FERTIG_VARIABLE].values
    monate = set()
    for z, f in zip(zeiten, fertig):
        if f == MONAT_FERTIG:
            datum = np.datetime64(z, "M").astype(object)
            monate.add((datum.year, datum.month))
    return monate


def schreibe_in_wuerfel(monatsdaten: xr.Dataset, zielzustand: int = MONAT_FERTIG) -> None:
    """Schreibt einen Monat an seine Position auf der Zeitachse des Würfels.

    Legt den Würfel beim ersten Mal an. Die Reihenfolge der Aufrufe spielt
    keine Rolle (2018 vor 2013 ist erlaubt). Schritte:
    1. Monat muss genau ein Zeitschritt sein und auf der Zeitachse liegen,
       Gitterkoordinaten müssen zu denen des Würfels passen.
    2. Ein schon als fertig markierter Monat wird nicht überschrieben. Ein als
       unvollständig markierter (2) darf ersetzt werden (Neuladen nach dem
       Befund vom 2026-09-25); seine alten Werte bleiben bis hierhin stehen.
    3. `monat_fertig` auf 3 („wird geschrieben") setzen, dann die Werte in die
       Position des Monats schreiben. Bricht es dazwischen ab, gilt der Monat
       weder als fertig noch als „alte Daten"; die neuen Rohdaten liegen dann
       noch im Rohordner (gelöscht wird erst nach Schritt 5), ein Neustart
       schreibt den Monat erneut.
    4. Zurücklesen und mit den geschriebenen Werten vergleichen.
    5. Erst danach `monat_fertig` für diesen Monat auf `zielzustand` setzen:
       1 (fertig) oder 4 (nur die Region vollständig, seit 2026-09-26). Ein
       Monat mit Zustand 4 darf nur mit Zielzustand 1 überschrieben werden
       (Stufe 2, nach `vereine_mit_region`), nie erneut mit 4.
    """
    if zielzustand not in (MONAT_FERTIG, MONAT_REGION_VOLLSTAENDIG):
        raise ValueError(f"Zielzustand {zielzustand} ist nicht erlaubt (nur 1 oder 4).")
    if monatsdaten.sizes.get("zeit") != 1:
        raise ValueError("Es muss genau ein Monat (ein Zeitschritt) übergeben werden.")
    datum = np.datetime64(monatsdaten["zeit"].values[0], "M").astype(object)
    index = _monat_index(datum.year, datum.month)

    pfad = _wuerfel_pfad()
    if not pfad.exists():
        _lege_wuerfel_an(pfad)
    _pruefe_wuerfel_format(pfad)

    breite, laenge = _gitter_koordinaten()
    if not (
        np.allclose(monatsdaten["breite"].values, breite)
        and np.allclose(monatsdaten["laenge"].values, laenge)
    ):
        raise WuerfelFormat("Die Gitterkoordinaten des Monats passen nicht zum Würfel. Nichts geschrieben.")

    with xr.open_zarr(pfad, chunks=None) as ds:
        bisher = int(ds[FERTIG_VARIABLE].values[index])
    if bisher == MONAT_FERTIG:
        raise MonatSchonVorhanden(
            f"{datum.year:04d}-{datum.month:02d} ist im Würfel schon fertig und wird nicht überschrieben."
        )
    if bisher == MONAT_REGION_VOLLSTAENDIG and zielzustand == MONAT_REGION_VOLLSTAENDIG:
        raise MonatSchonVorhanden(
            f"{datum.year:04d}-{datum.month:02d} ist für die Region schon vollständig; nur Stufe 2 darf ihn ergänzen."
        )

    variablen = list(_wuerfel_variablen())
    region = {"zeit": slice(index, index + 1)}
    _setze_monatsstatus(pfad, index, MONAT_WIRD_GESCHRIEBEN)
    monatsdaten[variablen].drop_vars(["zeit", "breite", "laenge"]).to_zarr(pfad, mode="r+", region=region)

    with xr.open_zarr(pfad, chunks=None) as ds:
        for name in variablen:
            gelesen = ds[name].isel(zeit=index).values
            geschrieben = monatsdaten[name].values[0]
            if not np.array_equal(gelesen, geschrieben, equal_nan=True):
                raise WuerfelSchreibFehler(
                    f"{datum.year:04d}-{datum.month:02d}: Variable {name} ist nach dem Schreiben "
                    "nicht identisch mit den geschriebenen Werten. Monat nicht als fertig markiert."
                )

    _setze_monatsstatus(pfad, index, zielzustand)


def vereine_mit_region(rest: xr.Dataset, region_positionen: set[str]) -> xr.Dataset:
    """Stufe 2: ergänzt die neu geladenen übrigen Kacheln um den Region-Teil aus dem Würfel.

    Voraussetzungen (sonst Abbruch, nichts geschrieben):
    - der Monat hat im Würfel Zustand 4 (Region vollständig),
    - `rest` enthält in den Zellen der Region-Kacheln keine Werte (NaN bzw. 0),
      d. h. es wurde wirklich nur der Rest geladen.
    Ergebnis: je Variable die Werte aus dem Würfel in den Region-Zellen, sonst
    die aus `rest`. Geschrieben wird es danach mit `schreibe_in_wuerfel` (Zielzustand 1).
    """
    from aleph.layers.vnp46a3_regionen import zellmaske

    datum = np.datetime64(rest["zeit"].values[0], "M").astype(object)
    index = _monat_index(datum.year, datum.month)
    name = f"{datum.year:04d}-{datum.month:02d}"
    maske = zellmaske(region_positionen, GITTER_BREITE, GITTER_LAENGE)
    pfad = _wuerfel_pfad()
    _pruefe_wuerfel_format(pfad)
    ergebnis = rest.copy(deep=True)
    with xr.open_zarr(pfad, chunks=None) as ds:
        if int(ds[FERTIG_VARIABLE].values[index]) != MONAT_REGION_VOLLSTAENDIG:
            raise MonatUnvollstaendig(
                f"{name}: Stufe 2 verlangt Zustand 4 (Region vollständig) im Würfel; nichts geschrieben."
            )
        for var in _wuerfel_variablen():
            neu = ergebnis[var].values[0]
            if np.issubdtype(neu.dtype, np.floating):
                belegt = np.isfinite(neu) & maske
            else:
                belegt = (neu != 0) & maske
            if belegt.any():
                raise MonatStimmtNicht(
                    f"{name}: Die nachgeladenen Kacheln haben Werte in {int(belegt.sum())} Zellen der Region "
                    f"({var}); Region und Rest überschneiden sich. Nichts geschrieben."
                )
            alt = ds[var].isel(zeit=index).values
            neu[maske] = alt[maske]
            ergebnis[var].values[0] = neu
    return ergebnis


def _setze_monatsstatus(pfad: Path, index: int, wert: int) -> None:
    region = {"zeit": slice(index, index + 1)}
    xr.Dataset({FERTIG_VARIABLE: (("zeit",), np.array([wert], dtype="int8"))}).to_zarr(
        pfad, mode="r+", region=region
    )


def monatsstatus(jahr: int, monat: int) -> int:
    """Wert von `monat_fertig` für einen Monat (0, wenn es noch keinen Würfel gibt)."""
    pfad = _wuerfel_pfad()
    if not pfad.exists():
        return MONAT_LEER
    _pruefe_wuerfel_format(pfad)
    with xr.open_zarr(pfad, chunks=None) as ds:
        return int(ds[FERTIG_VARIABLE].values[_monat_index(jahr, monat)])


MONATSSTATUS_TEXT = {
    MONAT_LEER: "leer",
    MONAT_FERTIG: "fertig",
    MONAT_UNVOLLSTAENDIG: "unvollständig (ältere Daten, werden ersetzt)",
    MONAT_WIRD_GESCHRIEBEN: "wurde zuletzt beim Schreiben unterbrochen",
    MONAT_REGION_VOLLSTAENDIG: "vollständig nur für Afrika-Europa-Asien (übrige Zellen nicht geladen)",
}


REGION_PRUEFSUMME_TEXT = "Region-Kacheln-Prüfsumme"


def pruefe_stufe1_nachweis(jahr: int, monat: int, region: str) -> tuple[bool, str, set[str]]:
    """Passt das Stufe-1-Manifest eines Monats zur aktuellen Kachelliste der Region? (Auflage B1)

    Verlangt: Manifest `<Monat>_<region>.tsv` vorhanden, Kopf mit
    `REGION_PRUEFSUMME_TEXT` gleich der Prüfsumme der aktuellen Liste, und jede
    Region-Position darin „geladen“ oder „beim Anbieter nicht vorhanden“.
    Rückgabe: (in Ordnung?, Grund, Positionen „beim Anbieter nicht vorhanden“).
    """
    from aleph.layers import vnp46a3_regionen

    positionen = vnp46a3_regionen.lies_region(region)
    pfad = manifest_pfad(jahr, monat, f"_{region}")
    if not pfad.exists():
        return False, f"Stufe-1-Manifest {pfad.name} fehlt", set()
    zeilen = pfad.read_text(encoding="utf-8").splitlines()
    erwartet = f"{REGION_PRUEFSUMME_TEXT}: {vnp46a3_regionen.pruefsumme(positionen)}"
    if not any(erwartet in z for z in zeilen if z.startswith("#")):
        return False, f"{pfad.name}: Kachelliste der Region hat sich seit Stufe 1 geändert (Prüfsumme)", set()
    zustand_je_pos = {}
    for z in zeilen:
        if z.startswith("#") or z.startswith("position\t") or not z.strip():
            continue
        teile = z.split("\t")
        zustand_je_pos[teile[0]] = teile[1]
    erlaubt = (ZUSTAND_GELADEN, ZUSTAND_NICHT_BEIM_ANBIETER)
    schlecht = sorted(p for p in positionen if zustand_je_pos.get(p) not in erlaubt)
    if schlecht:
        return False, f"{pfad.name}: Region-Positionen nicht geladen: {', '.join(schlecht[:5])}", set()
    nba = {p for p in positionen if zustand_je_pos.get(p) == ZUSTAND_NICHT_BEIM_ANBIETER}
    return True, "", nba


def lies_monate_mit_region(monate: list[tuple[int, int]], variablen: list[str], region: str):
    """Liest fertige Monate und Monate mit Zustand 4 dieser Region (siehe aleph/detect/wuerfel.py).

    Die Maske wird hier aus der Kachelliste gebildet, und für jeden Monat mit
    Zustand 4 muss sein Stufe-1-Nachweis zu genau dieser Liste passen (Auflage B1);
    sonst `MonatUnvollstaendig`. So kann keine zu große Maske nicht geladene
    Zellen als „geladen, 0 Pixel“ ausgeben.
    """
    from aleph.detect import wuerfel
    from aleph.layers import vnp46a3_regionen

    for jahr, monat in monate:
        if monatsstatus(jahr, monat) == MONAT_REGION_VOLLSTAENDIG:
            ok, grund, _ = pruefe_stufe1_nachweis(jahr, monat, region)
            if not ok:
                raise MonatUnvollstaendig(f"{jahr:04d}-{monat:02d}: {grund}; nichts geliefert.")
    maske = vnp46a3_regionen.zellmaske(vnp46a3_regionen.lies_region(region), GITTER_BREITE, GITTER_LAENGE)
    return wuerfel.lies_monate_mit_region(
        _wuerfel_pfad(), monate, variablen, maske, region_zustand=MONAT_REGION_VOLLSTAENDIG
    )


def monate_je_zustand() -> dict[int, set[tuple[int, int]]]:
    """Alle Monate der Zeitachse, gruppiert nach `monat_fertig` (für Lauf und Status)."""
    pfad = _wuerfel_pfad()
    if not pfad.exists():
        return {}
    _pruefe_wuerfel_format(pfad)
    with xr.open_zarr(pfad, chunks=None) as ds:
        zeiten = ds["zeit"].values
        werte = ds[FERTIG_VARIABLE].values
    ergebnis: dict[int, set[tuple[int, int]]] = {}
    for z, w in zip(zeiten, werte):
        datum = np.datetime64(z, "M").astype(object)
        ergebnis.setdefault(int(w), set()).add((datum.year, datum.month))
    return ergebnis


def markiere_unvollstaendig(monate: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Setzt fertige Monate auf `MONAT_UNVOLLSTAENDIG` (2), ohne Werte anzufassen.

    Für die Monate, die vor dem 2026-09-25 mit abgeschnittener Kachelabfrage
    geladen wurden: Ihre Werte bleiben im Würfel liegen, bis der Neuladeversuch
    erfolgreich war (`schreibe_in_wuerfel` ersetzt sie dann), gelten aber
    nicht mehr als vorhanden. Der Lauf lädt sie deshalb neu, und eine
    Auswertung, die nur fertige Monate liest, sieht sie nicht. Nur Monate mit
    Wert 1 werden umgestellt; zurückgegeben wird, welche das waren.
    """
    pfad = _wuerfel_pfad()
    _pruefe_wuerfel_format(pfad)
    geaendert = []
    for jahr, monat in monate:
        index = _monat_index(jahr, monat)
        with xr.open_zarr(pfad, chunks=None) as ds:
            wert = int(ds[FERTIG_VARIABLE].values[index])
        if wert == MONAT_FERTIG:
            _setze_monatsstatus(pfad, index, MONAT_UNVOLLSTAENDIG)
            geaendert.append((jahr, monat))
    return geaendert


# --- Architektur-Vertrag (ARCHITECTURE.md Abschnitt 5) ----------------------
# download() und to_cube() sind die vorgeschriebenen Einstiegspunkte für
# einzelne, kleinere Läufe. Der Hintergrund-Lauf (viele Monate, mit
# Speicherwächter, Vollständigkeitsprüfung, Fortsetzung, Manifest und
# Protokoll) nutzt die Bausteine oben direkt, siehe
# aleph/layers/vnp46a3_lauf.py.


def download(
    start: str,
    ende: str,
    gleichzeitige_downloads: int = GLEICHZEITIGE_DOWNLOADS_STANDARD,
) -> list[Path]:
    """Lädt Rohdaten für den Zeitraum [start, ende] (Format 'JJJJ-MM') nach der SSD."""
    dateien: list[Path] = []
    jahr, monat = (int(t) for t in start.split("-"))
    end_jahr, end_monat = (int(t) for t in ende.split("-"))
    while (jahr, monat) <= (end_jahr, end_monat):
        ziel = io.rohdaten_pfad("vnp46a3", f"{jahr:04d}-{monat:02d}")
        dateien += lade_monat(jahr, monat, ziel, gleichzeitige_downloads=gleichzeitige_downloads).dateien
        monat += 1
        if monat > 12:
            monat, jahr = 1, jahr + 1
    return dateien


def to_cube() -> xr.Dataset:
    """Baut den Würfel aus allen momentan unter raw/vnp46a3/ vorhandenen Monaten."""
    basis = io.rohdaten_pfad("vnp46a3")
    monats_ordner = sorted(p for p in basis.iterdir() if p.is_dir()) if basis.exists() else []
    monats_datasets = [verkleinere_monat(sorted(p.glob("*.h5"))) for p in monats_ordner]
    return xr.concat(monats_datasets, dim="zeit") if monats_datasets else xr.Dataset()
