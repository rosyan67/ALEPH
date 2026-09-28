"""Unpaywall: Die E-Mail-Adresse darf nie in Ausgabe, Fehlermeldung oder Protokoll landen.

Kein Netz, keine echte .env: Die Adresse ist eine Attrappe.
"""

import logging
import traceback
from types import SimpleNamespace

import pytest
import requests

from aleph.core import unpaywall

ATTRAPPE = "attrappe.test-person@beispiel.invalid"


@pytest.fixture(autouse=True)
def keine_echte_env(monkeypatch):
    monkeypatch.setattr(unpaywall, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("UNPAYWALL_EMAIL", ATTRAPPE)


@pytest.fixture(autouse=True)
def pausen(monkeypatch):
    """Keine echten Pausen im Test; die verlangten Pausen werden mitgeschrieben."""
    gewartet = []
    monkeypatch.setattr(unpaywall.time, "sleep", gewartet.append)
    return gewartet


def _antwort(status=200, daten=None):
    return SimpleNamespace(status_code=status, json=lambda: daten or {})


def _alles(fehler, capsys, caplog):
    aus = capsys.readouterr()
    tb = "".join(traceback.format_exception(fehler)) if fehler else ""
    return aus.out + aus.err + caplog.text + tb


def test_adresse_geht_nur_als_parameter_raus_und_nie_in_die_ausgabe(monkeypatch, capsys, caplog):
    gesehen = {}

    def get(url, params, timeout):
        gesehen.update(url=url, params=params)
        return _antwort(200, {"doi": "10.1/x", "is_oa": True,
                              "oa_locations": [{"url_for_pdf": "https://e.org/a.pdf"}]})

    monkeypatch.setattr(unpaywall.requests, "get", get)
    caplog.set_level(logging.DEBUG)
    assert unpaywall.main(["10.1/x"]) == 0
    assert gesehen["params"] == {"email": ATTRAPPE}
    assert ATTRAPPE not in gesehen["url"]
    assert ATTRAPPE not in _alles(None, capsys, caplog)


def test_verbindungsfehler_mit_adresse_in_der_meldung_wird_bereinigt(monkeypatch, capsys, caplog):
    def get(url, params, timeout):
        # So sehen echte requests-Meldungen aus: die ganze Adresse mit ?email=…
        raise requests.ConnectionError(f"Max retries exceeded with url: /v2/10.1/x?email={ATTRAPPE}")

    monkeypatch.setattr(unpaywall.requests, "get", get)
    caplog.set_level(logging.DEBUG)
    with pytest.raises(unpaywall.UnpaywallFehler) as info:
        unpaywall.open_access("10.1/x")
    assert ATTRAPPE not in _alles(info.value, capsys, caplog)
    assert info.value.__cause__ is None and info.value.__context__ is None


def test_http_fehler_ohne_adresse(monkeypatch, capsys, caplog):
    monkeypatch.setattr(unpaywall.requests, "get", lambda url, params, timeout: _antwort(422))
    assert unpaywall.main(["kaputt"]) == 1
    assert ATTRAPPE not in _alles(None, capsys, caplog)


def test_urllib3_protokollzeile_mit_adresse_wird_verworfen(caplog):
    caplog.set_level(logging.DEBUG)
    logging.getLogger("urllib3.connectionpool").debug(
        '%s://%s:%s "%s %s %s" %s', "https", "api.unpaywall.org", 443, "GET",
        f"/v2/10.1/x?email={ATTRAPPE}", "HTTP/1.1", 200)
    logging.getLogger("urllib3.connectionpool").debug("harmlose Zeile")
    assert ATTRAPPE not in caplog.text
    assert "harmlose Zeile" in caplog.text


def test_fehlende_variable_klare_meldung(monkeypatch):
    monkeypatch.delenv("UNPAYWALL_EMAIL")
    with pytest.raises(unpaywall.UnpaywallFehler, match="UNPAYWALL_EMAIL ist nicht gesetzt"):
        unpaywall.open_access("10.1/x")


def test_adresse_steht_nirgends_im_code():
    # Der Quelltext enthält keine E-Mail-Adresse, nur den Variablennamen.
    import re
    from pathlib import Path

    text = Path(unpaywall.__file__).read_text(encoding="utf-8")
    assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}", text)


def test_unter_logger_von_urllib3_filtern_ebenfalls(caplog):
    caplog.set_level(logging.DEBUG)
    unpaywall.open_access.__globals__["_filter_anbringen"]()
    logging.getLogger("urllib3.util.retry").debug("Incremented Retry for (url='/v2/x?email=%s')", ATTRAPPE)
    assert ATTRAPPE not in caplog.text


def test_verbindungsfehler_haengt_auch_nicht_als_context_an(monkeypatch):
    def get(url, params, timeout):
        raise requests.ConnectionError(f"url: /v2/x?email={ATTRAPPE}")

    monkeypatch.setattr(unpaywall.requests, "get", get)
    with pytest.raises(unpaywall.UnpaywallFehler) as info:
        unpaywall.open_access("10.1/x")
    assert info.value.__context__ is None and info.value.__cause__ is None


def test_url_kodierte_adresse_wird_ebenfalls_ersetzt():
    from urllib.parse import quote
    assert ATTRAPPE not in unpaywall._ohne(f"https://x/?email={quote(ATTRAPPE, safe='')}", ATTRAPPE)
    assert quote(ATTRAPPE, safe="") not in unpaywall._ohne(f"https://x/?email={quote(ATTRAPPE, safe='')}", ATTRAPPE)


# --- Netzwerkregel: Zeitlimit und Wiederholung mit wachsenden Pausen -------------------


def test_serverfehler_wird_wiederholt_und_gemeldet_ohne_adresse(monkeypatch, capsys, caplog, pausen):
    antworten = iter([_antwort(503), _antwort(429), _antwort(200, {"doi": "10.1/x", "is_oa": False})])
    zeitlimits = []

    def get(url, params, timeout):
        zeitlimits.append(timeout)
        return next(antworten)

    monkeypatch.setattr(unpaywall.requests, "get", get)
    caplog.set_level(logging.DEBUG)
    ergebnis = unpaywall.open_access("10.1/x")
    assert ergebnis["is_oa"] is False
    assert pausen == list(unpaywall.PAUSEN_SEKUNDEN)
    assert zeitlimits == [unpaywall.ZEITLIMIT_SEKUNDEN] * 3
    alles = _alles(None, capsys, caplog)
    assert "Versuch 1/3" in alles and "HTTP 503" in alles and "Versuch 2/3" in alles
    assert ATTRAPPE not in alles


def test_verbindungsfehler_nach_allen_versuchen_klarer_abbruch(monkeypatch, capsys, caplog, pausen):
    aufrufe = []

    def get(url, params, timeout):
        aufrufe.append(url)
        raise requests.Timeout(f"Read timed out: /v2/10.1/x?email={ATTRAPPE}")

    monkeypatch.setattr(unpaywall.requests, "get", get)
    with pytest.raises(unpaywall.UnpaywallFehler, match="Timeout") as info:
        unpaywall.open_access("10.1/x")
    assert len(aufrufe) == unpaywall.MAX_VERSUCHE
    assert pausen == [5, 15]
    assert ATTRAPPE not in _alles(info.value, capsys, caplog)


def test_http_404_wird_nicht_wiederholt(monkeypatch, pausen):
    aufrufe = []
    monkeypatch.setattr(unpaywall.requests, "get", lambda url, params, timeout: aufrufe.append(url) or _antwort(404))
    with pytest.raises(unpaywall.UnpaywallFehler, match="HTTP 404"):
        unpaywall.open_access("10.1/x")
    assert len(aufrufe) == 1 and pausen == []
