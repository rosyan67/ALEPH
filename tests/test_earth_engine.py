"""Tests für aleph/core/earth_engine.py (Anmeldung, ohne echten Server)."""

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
