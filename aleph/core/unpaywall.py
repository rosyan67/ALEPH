"""Unpaywall-Abfrage: frei zugängliche Volltexte zu einer DOI finden.

Unpaywall (https://unpaywall.org/products/api) verlangt bei jeder Abfrage
eine E-Mail-Adresse als Parameter `email`. Diese Adresse ist eine persönliche
Angabe und wird deshalb wie ein Zugangsdatum behandelt:

- Sie steht nur in `.env` unter UNPAYWALL_EMAIL (Vorlage ohne Wert in
  `.env.example`) und wird zur Laufzeit geladen, genau wie die anderen
  Zugangsdaten (`load_dotenv(ENV_DATEI)`, siehe `aleph/core/io.py`).
- Sie wird nie in Code, Befehle, Protokolle, Berichte oder Ausgaben
  geschrieben. Fehlermeldungen von `requests` enthalten die ganze Adresse der
  Abfrage (samt `?email=…`); sie werden deshalb nie weitergereicht, sondern
  durch eine eigene Meldung ohne Adresse ersetzt (`raise … from None`, damit
  auch der Traceback die ursprüngliche Meldung nicht zeigt).
- `urllib3` schreibt auf Stufe DEBUG jede abgerufene Adresse ins Protokoll.
  Ein Filter auf diesem Logger entfernt jede Zeile, die `email=` enthält.

Vorfall, der zu diesem Modul geführt hat: LOG.md, Eintrag 2026-09-26/27, und
berichte/2026-09-27_robustheit.md (die Adresse stand damals direkt in einem
Befehl).
"""

import logging
import os
import sys
import time
from urllib.parse import quote

import requests
from dotenv import load_dotenv

from aleph.core.io import ENV_DATEI

ENV_VARIABLE = "UNPAYWALL_EMAIL"
API = "https://api.unpaywall.org/v2/"
# Netzwerkregel (CLAUDE.md): Zeitlimit je Anfrage und Wiederholung mit wachsenden Pausen.
# Unpaywall antwortet normalerweise in unter 2 s; 30 s trennen „langsam" von „hängt".
# 3 Versuche mit 5 und 15 s Pause überbrücken kurze Störungen oder eine Drosselung (HTTP 429);
# dauert die Störung länger, bricht die Abfrage mit klarer Meldung ab. Jede
# Wiederholung wird gemeldet (nur DOI und Fehlerart, nie die Adresse).
ZEITLIMIT_SEKUNDEN = 30
MAX_VERSUCHE = 3
PAUSEN_SEKUNDEN = (5, 15)


class UnpaywallFehler(RuntimeError):
    """Abfrage gescheitert. Die Meldung enthält nie die E-Mail-Adresse."""


class _OhneEmailParameter(logging.Filter):
    """Verwirft Protokollzeilen, die einen `email=`-Parameter enthalten."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            text = record.getMessage()
        except Exception:
            text = str(record.msg)
        return "email=" not in text


_FILTER = _OhneEmailParameter()
# Filter auf Logger-Ebene gelten nicht für Unter-Logger (z. B. urllib3.util.retry,
# das bei Wiederholungen die URL schreibt). Deshalb vor jeder Abfrage an JEDEN
# vorhandenen Logger von urllib3/requests hängen.
_BEKANNT = ("urllib3", "urllib3.connectionpool", "urllib3.util.retry", "urllib3.poolmanager", "requests")


def _filter_anbringen() -> None:
    namen = set(_BEKANNT) | {
        n for n in logging.Logger.manager.loggerDict if n.startswith(("urllib3", "requests"))
    }
    for name in namen:
        logger = logging.getLogger(name)
        if _FILTER not in logger.filters:
            logger.addFilter(_FILTER)


_filter_anbringen()


def _adresse() -> str:
    load_dotenv(ENV_DATEI)
    wert = (os.environ.get(ENV_VARIABLE) or "").strip()
    if not wert:
        raise UnpaywallFehler(
            f"{ENV_VARIABLE} ist nicht gesetzt. In .env eine E-Mail-Adresse "
            "eintragen, mit der Unpaywall abgefragt werden darf."
        )
    return wert


def _ohne(text: str, adresse: str) -> str:
    for form in (adresse, quote(adresse, safe=""), quote(adresse)):
        text = text.replace(form, "[E-Mail-Adresse]")
    return text


def open_access(doi: str) -> dict:
    """Fragt Unpaywall zu einer DOI ab.

    Rückgabe: {"doi", "is_oa", "pdf_links" (Liste), "landing_links" (Liste)}.
    Bei jedem Fehler `UnpaywallFehler` mit Meldung ohne E-Mail-Adresse.
    """
    adresse = _adresse()
    _filter_anbringen()
    for versuch in range(1, MAX_VERSUCHE + 1):
        fehlerart = None
        antwort = None
        try:
            antwort = requests.get(
                API + doi.strip(), params={"email": adresse}, timeout=ZEITLIMIT_SEKUNDEN
            )
        except requests.RequestException as fehler:
            fehlerart = type(fehler).__name__
        voruebergehend = fehlerart is not None or antwort.status_code == 429 or antwort.status_code >= 500
        if not voruebergehend or versuch == MAX_VERSUCHE:
            break
        pause = PAUSEN_SEKUNDEN[versuch - 1]
        grund = fehlerart or f"HTTP {antwort.status_code}"
        print(
            f"Unpaywall: Versuch {versuch}/{MAX_VERSUCHE} für DOI {doi} gescheitert ({grund}), "
            f"neuer Versuch in {pause} s",
            file=sys.stderr,
            flush=True,
        )
        time.sleep(pause)
    if fehlerart is not None:
        # Außerhalb des except-Blocks ausgelöst: So hängt die Originalmeldung (mit
        # ?email=…) auch nicht als __context__ an der neuen Ausnahme.
        raise UnpaywallFehler(f"Unpaywall nicht erreichbar für DOI {doi} ({fehlerart}).")
    if antwort.status_code != 200:
        raise UnpaywallFehler(
            f"Unpaywall antwortet mit HTTP {antwort.status_code} für DOI {doi}."
        )
    try:
        daten = antwort.json()
    except ValueError:
        daten = None
    if not isinstance(daten, dict):
        raise UnpaywallFehler(f"Unpaywall lieferte keine lesbare Antwort für DOI {doi}.")
    orte = [o for o in (daten.get("oa_locations") or []) if isinstance(o, dict)]
    return {
        "doi": _ohne(str(daten.get("doi", doi)), adresse),
        "is_oa": bool(daten.get("is_oa")),
        "pdf_links": [_ohne(o["url_for_pdf"], adresse) for o in orte if o.get("url_for_pdf")],
        "landing_links": [
            _ohne(o["url_for_landing_page"], adresse) for o in orte if o.get("url_for_landing_page")
        ],
    }


def main(argv=None) -> int:
    import sys

    dois = (argv if argv is not None else sys.argv[1:])
    if not dois:
        print("Aufruf: .venv/bin/python -m aleph.core.unpaywall <DOI> [<DOI> …]")
        return 2
    code = 0
    for doi in dois:
        try:
            e = open_access(doi)
            print(f"{e['doi']}: frei zugänglich={e['is_oa']}; PDF: {', '.join(e['pdf_links']) or 'keins'}")
        except UnpaywallFehler as fehler:
            print(str(fehler))
            code = 1
    return code


if __name__ == "__main__":
    raise SystemExit(main())
