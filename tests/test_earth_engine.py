"""Tests für aleph/core/earth_engine.py (Anmeldung, ohne echten Server)."""

import threading

import ee
import pytest

from aleph.core import earth_engine


@pytest.fixture
def ohne_env_datei(monkeypatch, tmp_path):
    # Eine leere .env statt der echten, damit die Tests nichts aus .env lesen.
    leer = tmp_path / ".env"
    leer.write_text("")
    monkeypatch.setattr(earth_engine, "ENV_DATEI", leer)
    monkeypatch.delenv(earth_engine.PROJEKT_VARIABLE, raising=False)


@pytest.fixture(autouse=True)
def einstellungen(monkeypatch):
    """Zeitlimit und Wiederholungen der Bibliothek mitschreiben statt am echten Zustand setzen."""
    gesetzt = {}
    monkeypatch.setattr(ee.data, "setDeadline", lambda ms: gesetzt.update(deadline_ms=ms))
    monkeypatch.setattr(ee.data, "setMaxRetries", lambda n: gesetzt.update(max_retries=n))
    return gesetzt


def test_fehlendes_projekt_bricht_klar_ab(ohne_env_datei):
    with pytest.raises(earth_engine.EarthEngineNichtBereit, match="EE_PROJECT ist in .env nicht gesetzt"):
        earth_engine.projekt()


def test_projekt_wird_zur_laufzeit_geladen(ohne_env_datei, monkeypatch):
    monkeypatch.setenv(earth_engine.PROJEKT_VARIABLE, "  attrappe-projekt  ")
    assert earth_engine.projekt() == "attrappe-projekt"


def test_fehlermeldung_der_bibliothek_wird_nicht_weitergegeben(ohne_env_datei, monkeypatch, capsys):
    geheim = "attrappe-projekt-4711"
    monkeypatch.setenv(earth_engine.PROJEKT_VARIABLE, geheim)

    def scheitert(project=None, **_):
        raise ee.EEException(f"Project {project} not registered; token ya29.GEHEIM")

    monkeypatch.setattr(ee, "Initialize", scheitert)
    with pytest.raises(earth_engine.EarthEngineNichtBereit) as info:
        earth_engine.starte()
    text = str(info.value)
    assert "EEException" in text
    assert geheim not in text and "ya29" not in text
    assert info.value.__context__ is None and info.value.__cause__ is None
    ausgabe = capsys.readouterr()
    assert geheim not in ausgabe.out + ausgabe.err


def test_erfolg_uebergibt_projekt(ohne_env_datei, monkeypatch):
    monkeypatch.setenv(earth_engine.PROJEKT_VARIABLE, "attrappe-projekt")
    gesehen = {}
    monkeypatch.setattr(ee, "Initialize", lambda project=None, **_: gesehen.update(project=project))
    assert earth_engine.starte() is ee
    assert gesehen["project"] == "attrappe-projekt"



# --- Netzwerkregel: Zeitlimit und Wiederholung mit wachsenden Pausen -------------------


def test_erfolg_setzt_zeitlimit_und_wiederholungen(ohne_env_datei, monkeypatch, einstellungen):
    monkeypatch.setenv(earth_engine.PROJEKT_VARIABLE, "attrappe-projekt")
    monkeypatch.setattr(ee, "Initialize", lambda project=None, **_: None)
    earth_engine.starte()
    assert einstellungen == {
        "deadline_ms": earth_engine.ANFRAGE_ZEITLIMIT_STANDARD_SEKUNDEN * 1000,
        "max_retries": earth_engine.BIBLIOTHEK_WIEDERHOLUNGEN,
    }
    assert earth_engine.ANFRAGE_ZEITLIMIT_STANDARD_SEKUNDEN > 0  # 0 hieße in der Bibliothek: kein Limit


def test_haengender_start_wird_abgebrochen_und_mit_wachsenden_pausen_wiederholt(ohne_env_datei, monkeypatch, capsys):
    monkeypatch.setenv(earth_engine.PROJEKT_VARIABLE, "attrappe-projekt-4711")
    freigabe = threading.Event()
    aufrufe = []

    def haengt(project=None, **_):
        aufrufe.append(project)
        freigabe.wait(5)  # simuliert eine Anfrage ohne Antwort

    monkeypatch.setattr(ee, "Initialize", haengt)
    pausen = []
    try:
        with pytest.raises(earth_engine.EarthEngineNichtBereit, match="TimeoutError"):
            earth_engine.starte(zeitlimit_sekunden=0.05, schlafe=pausen.append)
    finally:
        freigabe.set()
    assert len(aufrufe) == len(earth_engine.START_PAUSEN_SEKUNDEN) + 1
    assert pausen == list(earth_engine.START_PAUSEN_SEKUNDEN)
    assert pausen == sorted(pausen)
    fehlerausgabe = capsys.readouterr().err
    assert "Startversuch 1/4" in fehlerausgabe and "Startversuch 3/4" in fehlerausgabe
    assert "attrappe-projekt-4711" not in fehlerausgabe


def test_netzfehler_dann_erfolg(ohne_env_datei, monkeypatch):
    monkeypatch.setenv(earth_engine.PROJEKT_VARIABLE, "attrappe-projekt")
    ergebnisse = iter([ConnectionError("weg"), None])

    def start(project=None, **_):
        fehler = next(ergebnisse)
        if fehler:
            raise fehler

    monkeypatch.setattr(ee, "Initialize", start)
    pausen = []
    assert earth_engine.starte(schlafe=pausen.append) is ee
    assert pausen == [earth_engine.START_PAUSEN_SEKUNDEN[0]]


def test_abgelehnter_start_wird_nicht_wiederholt(ohne_env_datei, monkeypatch):
    monkeypatch.setenv(earth_engine.PROJEKT_VARIABLE, "attrappe-projekt")
    aufrufe = []

    def abgelehnt(project=None, **_):
        aufrufe.append(project)
        raise ee.EEException("Permission denied")

    monkeypatch.setattr(ee, "Initialize", abgelehnt)
    pausen = []
    with pytest.raises(earth_engine.EarthEngineNichtBereit, match="EEException"):
        earth_engine.starte(schlafe=pausen.append)
    assert len(aufrufe) == 1 and pausen == []
