"""Prüft den Login-Code mit Attrappen. Kein Netz, keine echten Zugangsdaten."""

from types import SimpleNamespace

import pytest

from aleph.core import auth

GEHEIM = "SEHR-GEHEIMES-PASSWORT-123"


@pytest.fixture(autouse=True)
def keine_echte_env(monkeypatch):
    # Die echte .env darf in diesen Tests nie geladen werden.
    monkeypatch.setattr(auth, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("EARTHDATA_USERNAME", "test-nutzer")
    monkeypatch.setenv("EARTHDATA_PASSWORD", GEHEIM)


def test_erfolg_meldet_nur_login_geklappt(monkeypatch, capsys):
    monkeypatch.setattr(auth.earthaccess, "login", lambda **k: SimpleNamespace(authenticated=True))
    assert auth.main() == 0
    aus = capsys.readouterr()
    assert aus.out == "Login geklappt\n"
    assert aus.err == ""


def test_fehler_meldet_nur_login_fehlgeschlagen_ohne_geheimnis(monkeypatch, capsys):
    def kaputt(**k):
        # Eine Fehlermeldung, die das Passwort enthält, darf nie sichtbar werden.
        raise RuntimeError(f"Anmeldung mit Passwort {GEHEIM} abgelehnt")

    monkeypatch.setattr(auth.earthaccess, "login", kaputt)
    assert auth.main() == 1
    aus = capsys.readouterr()
    assert aus.out == "Login fehlgeschlagen\n"
    assert GEHEIM not in aus.out + aus.err


def test_nicht_authentifiziert_zaehlt_als_fehlgeschlagen(monkeypatch, capsys):
    monkeypatch.setattr(auth.earthaccess, "login", lambda **k: SimpleNamespace(authenticated=False))
    assert auth.main() == 1
    assert capsys.readouterr().out == "Login fehlgeschlagen\n"


def test_eigene_ausgaben_von_earthaccess_werden_verworfen(monkeypatch, capsys):
    def geschwaetzig(**k):
        print(f"Eingeloggt als test-nutzer mit {GEHEIM}")
        return SimpleNamespace(authenticated=True)

    monkeypatch.setattr(auth.earthaccess, "login", geschwaetzig)
    auth.main()
    aus = capsys.readouterr()
    assert GEHEIM not in aus.out + aus.err
    assert aus.out == "Login geklappt\n"


# --- Einordnung und Wiederholung (seit 2026-09-27) ---------------------------
#
# Hintergrund: Am 26.09. 22:01 UTC beendete ein einziger fehlgeschlagener
# Login den ganzen Download. Jetzt wird wiederholt; abgelehnte Zugangsdaten
# enden nach der Reihe, ein nicht erreichbarer Dienst wird länger abgewartet.

import requests
from earthaccess.exceptions import LoginAttemptFailure, LoginStrategyUnavailable


def _http_fehler(status):
    return requests.HTTPError(f"{status} für https://urs.earthdata.nasa.gov/profile", response=SimpleNamespace(status_code=status))


@pytest.mark.parametrize(
    "fehler, art",
    [
        (requests.ConnectionError("Verbindung weg"), auth.NICHT_ERREICHBAR),
        (requests.Timeout("zu langsam"), auth.NICHT_ERREICHBAR),
        (_http_fehler(503), auth.NICHT_ERREICHBAR),
        (_http_fehler(500), auth.NICHT_ERREICHBAR),
        (_http_fehler(401), auth.ABGELEHNT),
        (_http_fehler(403), auth.ABGELEHNT),
        (LoginAttemptFailure(f"Authentication failed: {GEHEIM}"), auth.ABGELEHNT),
        (LoginStrategyUnavailable("Variablen fehlen"), auth.ZUGANGSDATEN_FEHLEN),
        (ValueError("Programmfehler"), auth.ABGELEHNT),
    ],
)
def test_login_fehler_werden_eingeordnet_ohne_meldungstext(monkeypatch, fehler, art):
    def kaputt(**k):
        raise fehler

    monkeypatch.setattr(auth.earthaccess, "login", kaputt)
    ergebnis = auth.earthdata_login()
    assert not ergebnis
    assert ergebnis.art == art
    assert GEHEIM not in ergebnis.beschreibung
    assert "urs.earthdata" not in ergebnis.beschreibung  # nur Art des Fehlers, nie der Meldungstext


def _folge(*arten):
    """Login-Attrappe: liefert nacheinander die angegebenen Arten, danach die letzte immer wieder."""
    zaehler = {"n": 0}

    def login():
        art = arten[min(zaehler["n"], len(arten) - 1)]
        zaehler["n"] += 1
        return auth.LoginErgebnis(art, "Attrappe")

    return login


def test_kurzer_ausfall_wird_ueberbrueckt():
    pausen, zeilen = [], []
    ergebnis = auth.login_mit_wiederholung(
        _folge(auth.NICHT_ERREICHBAR, auth.NICHT_ERREICHBAR, auth.OK), melde=zeilen.append, schlafe=pausen.append
    )
    assert ergebnis and ergebnis.versuche == 3
    assert pausen == [60, 120]
    assert zeilen[0].startswith("wartet auf NASA-Login, Versuch 1 fehlgeschlagen (nicht erreichbar")
    assert zeilen[1].startswith("wartet auf NASA-Login, Versuch 2 ")
    assert zeilen[-1] == "NASA-Login wieder erfolgreich (Versuch 3, nach 3 Minuten Warten)."


def test_dauerhaft_abgelehnt_endet_nach_der_reihe_mit_klarer_meldung():
    pausen, zeilen = [], []
    ergebnis = auth.login_mit_wiederholung(_folge(auth.ABGELEHNT), melde=zeilen.append, schlafe=pausen.append)
    assert not ergebnis
    assert pausen == [60, 120, 300, 600, 900, 1800]  # 1, 2, 5, 10, 15, 30 Minuten = 63 Minuten
    assert ergebnis.versuche == 7 and len(zeilen) == 6
    meldung = auth.abbruch_meldung(ergebnis)
    assert "nach 7 Versuchen in 63 Minuten weiterhin abgelehnt" in meldung
    assert "EARTHDATA_USERNAME/EARTHDATA_PASSWORD in .env prüfen" in meldung


def test_nicht_erreichbar_wird_ueber_die_reihe_hinaus_bis_12_stunden_versucht():
    pausen = []
    ergebnis = auth.login_mit_wiederholung(_folge(auth.NICHT_ERREICHBAR), schlafe=pausen.append)
    assert not ergebnis
    assert pausen[:6] == [60, 120, 300, 600, 900, 1800]
    assert set(pausen[6:]) == {1800}
    assert 11 * 3600 < sum(pausen) <= 12 * 3600
    assert "weiterhin nicht erreichbar" in auth.abbruch_meldung(ergebnis)
    assert "nicht die Zugangsdaten" in auth.abbruch_meldung(ergebnis)


def test_fehlende_zugangsdaten_brechen_sofort_ab():
    pausen = []
    ergebnis = auth.login_mit_wiederholung(_folge(auth.ZUGANGSDATEN_FEHLEN), schlafe=pausen.append)
    assert not ergebnis and pausen == []
    assert "fehlen in .env" in auth.abbruch_meldung(ergebnis)


def test_wiederholung_mit_echtem_login_code_gibt_nie_zugangsdaten_aus(monkeypatch, capsys):
    aufrufe = {"n": 0}

    def login(**k):
        aufrufe["n"] += 1
        print(f"Eingeloggt als test-nutzer mit {GEHEIM}")
        if aufrufe["n"] == 1:
            raise requests.ConnectionError(f"https://test-nutzer:{GEHEIM}@urs.earthdata.nasa.gov abgebrochen")
        if aufrufe["n"] == 2:
            raise LoginAttemptFailure(f"Authentication with Earthdata Login failed with: {GEHEIM}")
        return SimpleNamespace(authenticated=True)

    monkeypatch.setattr(auth.earthaccess, "login", login)
    zeilen = []
    ergebnis = auth.login_mit_wiederholung(melde=zeilen.append, schlafe=lambda s: None)
    assert ergebnis
    alles = "\n".join(zeilen) + capsys.readouterr().out + capsys.readouterr().err
    assert GEHEIM not in alles and "test-nutzer" not in alles


def test_haengender_login_zaehlt_nach_zeitlimit_als_nicht_erreichbar(monkeypatch):
    import threading
    frei = threading.Event()

    def haengt(**k):
        frei.wait(5)  # simuliert eine /profile-Anfrage ohne Antwort
        return SimpleNamespace(authenticated=True)

    monkeypatch.setattr(auth.earthaccess, "login", haengt)
    ergebnis = auth.earthdata_login(zeitlimit_sekunden=0.1)
    frei.set()
    assert not ergebnis and ergebnis.art == auth.NICHT_ERREICHBAR
    assert "keine Antwort nach" in ergebnis.beschreibung
