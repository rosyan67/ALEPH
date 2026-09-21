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
