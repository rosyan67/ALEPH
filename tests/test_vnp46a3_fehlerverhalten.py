"""Prüft das Fehlerverhalten des Nachtlicht-Downloads (Auftrag 2026-09-24).

Auslöser: Am 2026-09-24 05:25 UTC endete der große Lauf, weil zwei Kacheln von
2019-02 nach je 4 Versuchen mit HTTP 502 (Serverfehler bei der NASA)
scheiterten. Das gewünschte Verhalten:
- Serverfehler (5xx) und Zeitüberschreitungen hartnäckig wiederholen (wachsende
  Wartezeit, insgesamt bis etwa 30 Minuten je Kachel); 4xx sofort aufgeben,
- ein danach unvollständiger Monat wird zurückgestellt (nicht fertig, Rohdaten
  bleiben), der Lauf macht weiter und versucht ihn am Ende noch einmal,
- der Lauf endet nur bei echten Blockern (Speicher, SSD, Anmeldung),
- der Status zeigt fertige, offene und nachzuholende Monate.

Kein Netzzugriff, keine echten Wartezeiten: earthaccess und time.sleep sind
durch Attrappen ersetzt.
"""

import errno
import sys
import time
from pathlib import Path

import h5py
import numpy as np
import pytest
import xarray as xr
from earthaccess.exceptions import DownloadFailure, EulaNotAccepted

from aleph.core import io
from aleph.layers import vnp46a3, vnp46a3_lauf, vnp46a3_status

# Die Meldung, wie sie im Absturzprotokoll vom 2026-09-24 steht.
MELDUNG_502 = (
    "Download failed for https://data.laadsdaac.earthdatacloud.nasa.gov/prod-lads/VNP46A3/"
    "VNP46A3.A2019032.h18v08.002.2025133154653.h5. Status code: 502"
)


@pytest.fixture
def fake_ssd(tmp_path, monkeypatch):
    monkeypatch.setenv("ALEPH_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def zugangszaehler_zuruecksetzen():
    """Der 403-Zähler gilt für den ganzen Prozess; jeder Test beginnt mit 0."""
    vnp46a3.ZUGANG.zuruecksetzen()
    yield
    vnp46a3.ZUGANG.zuruecksetzen()


def _fehler(status: int) -> DownloadFailure:
    return DownloadFailure(MELDUNG_502.replace("502", str(status)))


def _schlaf_rekorder(monkeypatch) -> list[float]:
    wartezeiten: list[float] = []
    monkeypatch.setattr(vnp46a3.time, "sleep", lambda s: wartezeiten.append(s))
    return wartezeiten


# --- Eine Kachel: 5xx hartnäckig, 4xx sofort ---------------------------------


def test_statuscode_wird_aus_der_echten_meldung_gelesen():
    assert vnp46a3._statuscode(DownloadFailure(MELDUNG_502)) == 502
    assert vnp46a3._statuscode(RuntimeError("irgendein anderer Text")) is None


def test_502_mit_spaeterem_erfolg(monkeypatch, tmp_path):
    """Sechs Serverfehler hintereinander (mehr als die früheren 4 Versuche), dann klappt es."""
    aufrufe = {"n": 0}

    def fake_download(granules, local_path):
        aufrufe["n"] += 1
        if aufrufe["n"] <= 6:
            raise _fehler(502)
        return [str(Path(local_path) / "kachel.h5")]

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    wartezeiten = _schlaf_rekorder(monkeypatch)

    pfad = vnp46a3._lade_kachel("granule-1", tmp_path, datei_timeout_sekunden=1)

    assert pfad == tmp_path / "kachel.h5"
    assert aufrufe["n"] == 7
    # Wartezeit wächst (20, 40, 80, 160 s) und bleibt dann bei höchstens 300 s je Pause.
    assert wartezeiten == [20, 40, 80, 160, 300, 300]


def test_502_dauerhaft_gibt_erst_nach_dem_30_minuten_budget_auf(monkeypatch, tmp_path):
    aufrufe = {"n": 0}

    def fake_download(granules, local_path):
        aufrufe["n"] += 1
        raise _fehler(502)

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    wartezeiten = _schlaf_rekorder(monkeypatch)

    with pytest.raises(vnp46a3.KachelNichtGeladen) as info:
        vnp46a3._lade_kachel("granule-1", tmp_path, datei_timeout_sekunden=1)

    assert info.value.dauerhaft is False  # vorübergehend: der Monat wird später erneut versucht
    assert info.value.status == 502
    assert "502" in str(info.value)
    assert sum(wartezeiten) <= 30 * 60  # nie mehr als das Budget
    # aber nicht früh aufgegeben: 20+40+80+160 s, dann 300-s-Pausen bis das Budget nicht mehr reicht (25 Minuten)
    assert sum(wartezeiten) >= 20 * 60
    assert aufrufe["n"] == len(wartezeiten) + 1
    assert aufrufe["n"] >= 9  # deutlich hartnäckiger als die früheren 4 Versuche
    assert max(wartezeiten) <= 300


def test_404_wird_sofort_aufgegeben(monkeypatch, tmp_path):
    aufrufe = {"n": 0}

    def fake_download(granules, local_path):
        aufrufe["n"] += 1
        raise _fehler(404)

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    wartezeiten = _schlaf_rekorder(monkeypatch)

    with pytest.raises(vnp46a3.KachelNichtGeladen) as info:
        vnp46a3._lade_kachel("granule-1", tmp_path, datei_timeout_sekunden=1)

    assert aufrufe["n"] == 1
    assert wartezeiten == []
    assert info.value.dauerhaft is True
    assert info.value.status == 404


@pytest.mark.parametrize("status", [400, 403, 410])
def test_andere_4xx_werden_sofort_aufgegeben(monkeypatch, tmp_path, status):
    aufrufe = {"n": 0}

    def fake_download(granules, local_path):
        aufrufe["n"] += 1
        raise _fehler(status)

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    wartezeiten = _schlaf_rekorder(monkeypatch)
    with pytest.raises(vnp46a3.KachelNichtGeladen) as info:
        vnp46a3._lade_kachel("granule-1", tmp_path, datei_timeout_sekunden=1)
    assert (aufrufe["n"], wartezeiten, info.value.dauerhaft) == (1, [], True)


@pytest.mark.parametrize("status", [408, 429, 500, 503, 504])
def test_408_429_und_5xx_werden_wiederholt(monkeypatch, tmp_path, status):
    aufrufe = {"n": 0}

    def fake_download(granules, local_path):
        aufrufe["n"] += 1
        if aufrufe["n"] == 1:
            raise _fehler(status)
        return [str(Path(local_path) / "kachel.h5")]

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    _schlaf_rekorder(monkeypatch)
    assert vnp46a3._lade_kachel("granule-1", tmp_path, datei_timeout_sekunden=1) == tmp_path / "kachel.h5"
    assert aufrufe["n"] == 2


def test_fehler_ohne_lesbaren_statuscode_gilt_als_vorlaeufig(monkeypatch, tmp_path):
    """Ändert earthaccess den Meldungstext, wird lieber gewartet als fälschlich aufgegeben."""
    aufrufe = {"n": 0}

    def fake_download(granules, local_path):
        aufrufe["n"] += 1
        if aufrufe["n"] == 1:
            raise DownloadFailure("Download failed: neuer Text ohne Statuszahl")
        return [str(Path(local_path) / "kachel.h5")]

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    _schlaf_rekorder(monkeypatch)
    vnp46a3._lade_kachel("granule-1", tmp_path, datei_timeout_sekunden=1)
    assert aufrufe["n"] == 2


def test_zeitueberschreitung_zaehlt_zum_budget_und_wird_dann_aufgegeben(monkeypatch, tmp_path):
    aufrufe = {"n": 0}

    def fake_download(granules, local_path):
        aufrufe["n"] += 1
        time.sleep(0.3)  # reagiert nicht innerhalb des Zeitlimits (0,05 s)

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    with pytest.raises(vnp46a3.KachelNichtGeladen, match="reagiert seit") as info:
        vnp46a3._lade_kachel(
            "granule-1",
            tmp_path,
            datei_timeout_sekunden=0.05,
            retry_budget_sekunden=0.3,
            wartezeit_basis_sekunden=0.01,
            wartezeit_max_sekunden=0.05,
        )
    assert info.value.dauerhaft is False
    assert aufrufe["n"] >= 3  # mehrfach wiederholt, nicht nach dem ersten Hänger aufgegeben


def test_unbekannter_fehler_wird_nicht_dreissig_minuten_wiederholt(monkeypatch, tmp_path):
    """Ein Programmfehler hilft kein Warten: sofort melden."""
    aufrufe = {"n": 0}

    def fake_download(granules, local_path):
        aufrufe["n"] += 1
        raise ValueError("Programmfehler")

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    wartezeiten = _schlaf_rekorder(monkeypatch)
    with pytest.raises(vnp46a3.KachelNichtGeladen, match="Programmfehler") as info:
        vnp46a3._lade_kachel("granule-1", tmp_path, datei_timeout_sekunden=1)
    assert (aufrufe["n"], wartezeiten, info.value.dauerhaft) == (1, [], True)


# --- Eine Kachel: echte Blocker werden nicht als Kachelproblem behandelt -----


def test_anmeldung_401_ist_ein_blocker_und_wird_nicht_wiederholt(monkeypatch, tmp_path):
    aufrufe = {"n": 0}

    def fake_download(granules, local_path):
        aufrufe["n"] += 1
        raise _fehler(401)

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    wartezeiten = _schlaf_rekorder(monkeypatch)
    with pytest.raises(vnp46a3.AnmeldungFehlgeschlagen):
        vnp46a3._lade_kachel("granule-1", tmp_path, datei_timeout_sekunden=1)
    assert (aufrufe["n"], wartezeiten) == (1, [])


def test_nicht_akzeptierte_eula_ist_ein_blocker(monkeypatch, tmp_path):
    def fake_download(granules, local_path):
        raise EulaNotAccepted("Eula Acceptance Failure for https://x")

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    _schlaf_rekorder(monkeypatch)
    with pytest.raises(vnp46a3.AnmeldungFehlgeschlagen, match="EULA"):
        vnp46a3._lade_kachel("granule-1", tmp_path, datei_timeout_sekunden=1)


def test_platte_voll_beim_schreiben_ist_ein_blocker(monkeypatch, tmp_path, fake_ssd):
    def fake_download(granules, local_path):
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    wartezeiten = _schlaf_rekorder(monkeypatch)
    with pytest.raises(io.SpeicherZuKnapp):
        vnp46a3._lade_kachel("granule-1", tmp_path, datei_timeout_sekunden=1)
    assert wartezeiten == []


def test_ssd_abgezogen_ist_ein_blocker(monkeypatch, tmp_path):
    monkeypatch.setenv("ALEPH_DATA_DIR", str(tmp_path / "nicht_da"))

    def fake_download(granules, local_path):
        raise OSError(errno.EIO, "Input/output error")

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    _schlaf_rekorder(monkeypatch)
    with pytest.raises(io.SSDNichtGefunden):
        vnp46a3._lade_kachel("granule-1", tmp_path, datei_timeout_sekunden=1)


def test_verbindungsfehler_bei_vorhandener_ssd_wird_wiederholt(monkeypatch, tmp_path, fake_ssd):
    aufrufe = {"n": 0}

    def fake_download(granules, local_path):
        aufrufe["n"] += 1
        if aufrufe["n"] < 3:
            raise ConnectionError("Verbindung getrennt")
        return [str(Path(local_path) / "kachel.h5")]

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    _schlaf_rekorder(monkeypatch)
    vnp46a3._lade_kachel("granule-1", tmp_path, datei_timeout_sekunden=1)
    assert aufrufe["n"] == 3


# --- Ein Monat: dauerhaft fehlende Kachel, Wiederaufnahme, Serverausfall ------


class _Granule:
    def __init__(self, nr: int):
        # Nur echte Gitterpositionen (h 0-35): die Referenzprüfung in
        # lade_monat lehnt erfundene Positionen wie h36 ab.
        self.h = nr % 36
        v = 3 + nr // 36
        self._link = f"https://example.org/VNP46A3.A2024001.h{self.h:02d}v{v:02d}.002.20240101000000.h5"

    def data_links(self):
        return [self._link]

    @property
    def dateiname(self) -> str:
        return self._link.rsplit("/", 1)[-1]


def _schreibe_gueltige_kachel(ordner: Path, granule: _Granule) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    pfad = ordner / granule.dateiname
    with h5py.File(pfad, "w"):
        pass
    return pfad


@pytest.fixture
def monat_mit_5_kacheln(monkeypatch):
    granules = [_Granule(h) for h in range(5)]
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    monkeypatch.setattr(vnp46a3.earthaccess, "search_data", lambda **kwargs: granules)
    return granules


def test_dauerhaft_fehlende_kachel_macht_den_monat_unvollstaendig_und_loescht_nichts(
    monkeypatch, tmp_path, monat_mit_5_kacheln
):
    granules = monat_mit_5_kacheln

    def fake_lade_kachel(granule, ziel_ordner, **kwargs):
        if granule is granules[2]:
            raise vnp46a3.KachelNichtGeladen(f"{MELDUNG_502.replace('502', '404')}", dauerhaft=True, status=404)
        return _schreibe_gueltige_kachel(ziel_ordner, granule)

    monkeypatch.setattr(vnp46a3, "_lade_kachel", fake_lade_kachel)
    with pytest.raises(vnp46a3.KachelnFehlen) as info:
        vnp46a3.lade_monat(2024, 1, tmp_path, gleichzeitige_downloads=2)

    assert "1 von 5" in str(info.value)
    assert (info.value.dauerhaft, info.value.vorlaeufig) == (1, 0)
    # Rohdaten bleiben: die vier geladenen Kacheln liegen noch da.
    assert sorted(p.name for p in tmp_path.glob("*.h5")) == sorted(
        g.dateiname for i, g in enumerate(granules) if i != 2
    )


def test_wiederaufnahme_laedt_vorhandene_kacheln_nicht_neu(monkeypatch, tmp_path, monat_mit_5_kacheln):
    granules = monat_mit_5_kacheln
    angefragt: list[str] = []
    ausfall = {"aktiv": True}

    def fake_lade_kachel(granule, ziel_ordner, **kwargs):
        angefragt.append(granule.dateiname)
        if granule is granules[3] and ausfall["aktiv"]:
            raise vnp46a3.KachelNichtGeladen("Serverfehler 502", dauerhaft=False, status=502)
        return _schreibe_gueltige_kachel(ziel_ordner, granule)

    monkeypatch.setattr(vnp46a3, "_lade_kachel", fake_lade_kachel)
    with pytest.raises(vnp46a3.KachelnFehlen):
        vnp46a3.lade_monat(2024, 1, tmp_path, gleichzeitige_downloads=1)
    assert len(angefragt) == 5

    # Server wieder gesund: nur die eine fehlende Kachel wird angefragt.
    angefragt.clear()
    ausfall["aktiv"] = False
    meldungen: list[str] = []
    dateien = vnp46a3.lade_monat(2024, 1, tmp_path, gleichzeitige_downloads=1, melde=meldungen.append).dateien

    assert angefragt == [granules[3].dateiname]
    assert sorted(p.name for p in dateien) == sorted(g.dateiname for g in granules)
    assert any("4 Kacheln aus einem früheren Versuch schon vorhanden" in m for m in meldungen)


def test_wiederaufnahme_ersetzt_kaputte_kachel_und_raeumt_reste_auf(monkeypatch, tmp_path, monat_mit_5_kacheln):
    granules = monat_mit_5_kacheln
    for g in granules[1:]:
        _schreibe_gueltige_kachel(tmp_path, g)
    (tmp_path / granules[0].dateiname).write_bytes(b"das ist keine HDF5-Datei")  # z. B. Absturz beim Schreiben
    (tmp_path / "partial_abc123").write_bytes(b"halber Download")

    angefragt: list[str] = []

    def fake_lade_kachel(granule, ziel_ordner, **kwargs):
        angefragt.append(granule.dateiname)
        return _schreibe_gueltige_kachel(ziel_ordner, granule)

    monkeypatch.setattr(vnp46a3, "_lade_kachel", fake_lade_kachel)
    dateien = vnp46a3.lade_monat(2024, 1, tmp_path, gleichzeitige_downloads=1).dateien

    assert angefragt == [granules[0].dateiname]  # nur die kaputte wird neu geladen
    assert len(dateien) == 5
    assert not (tmp_path / "partial_abc123").exists()


def test_serverausfall_bricht_den_monat_nach_zehn_gescheiterten_kacheln_ab(monkeypatch, tmp_path):
    """Sonst kostete ein Ausfall 30 Minuten je Kachel, hunderte Kacheln lang."""
    granules = [_Granule(h) for h in range(40)]
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    monkeypatch.setattr(vnp46a3.earthaccess, "search_data", lambda **kwargs: granules)
    monkeypatch.setattr(vnp46a3, "MAX_GESCHEITERTE_KACHELN_JE_MONAT", 3)
    angefragt: list[str] = []

    def fake_lade_kachel(granule, ziel_ordner, **kwargs):
        angefragt.append(granule.dateiname)
        time.sleep(0.05)  # in Wirklichkeit dauert ein Fehlschlag Minuten; so kann der Lauf rechtzeitig reagieren
        raise vnp46a3.KachelNichtGeladen("Serverfehler 502", dauerhaft=False, status=502)

    monkeypatch.setattr(vnp46a3, "_lade_kachel", fake_lade_kachel)
    with pytest.raises(vnp46a3.KachelnFehlen, match="abgebrochen"):
        vnp46a3.lade_monat(2024, 1, tmp_path, gleichzeitige_downloads=1)
    assert len(angefragt) <= 5  # 3 gescheiterte plus höchstens eine schon laufende; nicht alle 40


def test_blocker_in_einer_kachel_beendet_lade_monat_mit_dem_blocker(monkeypatch, tmp_path, monat_mit_5_kacheln):
    granules = monat_mit_5_kacheln

    def fake_lade_kachel(granule, ziel_ordner, **kwargs):
        if granule is granules[1]:
            raise vnp46a3.AnmeldungFehlgeschlagen("Login abgelaufen")
        return _schreibe_gueltige_kachel(ziel_ordner, granule)

    monkeypatch.setattr(vnp46a3, "_lade_kachel", fake_lade_kachel)
    with pytest.raises(vnp46a3.AnmeldungFehlgeschlagen):
        vnp46a3.lade_monat(2024, 1, tmp_path, gleichzeitige_downloads=1)


def test_login_fehlschlag_ist_ein_blocker(monkeypatch, tmp_path):
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: False)
    with pytest.raises(vnp46a3.AnmeldungFehlgeschlagen):
        vnp46a3.lade_monat(2024, 1, tmp_path)


# --- Der Lauf: zurückstellen, weitermachen, nachholen, nur bei Blockern enden --
#
# Hier ersetzen Attrappen den NASA-Download (`lade_monat`) und das Verkleinern
# (`verkleinere_monat`, sonst 100 MB je Testkachel); Würfel schreiben und als
# fertig markieren, Manifest, Löschen der Rohdaten und Protokoll laufen echt.


def _leerer_monat(jahr: int, monat: int) -> xr.Dataset:
    breite, laenge = vnp46a3._gitter_koordinaten()
    variablen = {}
    for name, dtyp in vnp46a3._wuerfel_variablen().items():
        leer = np.full((1, len(breite), len(laenge)), np.nan if dtyp == "float32" else 0, dtype=dtyp)
        variablen[name] = (("zeit", "breite", "laenge"), leer)
    return xr.Dataset(
        variablen,
        coords={"zeit": [np.datetime64(f"{jahr:04d}-{monat:02d}-01")], "breite": breite, "laenge": laenge},
    )


class LaufAttrappe:
    """Steuert je Monat und Aufruf, was `lade_monat` tut: 'ok', 'fehlt' (dauerhaft), '502' oder eine Ausnahme."""

    def __init__(self, monkeypatch, fake_ssd, plan=None):
        self.plan = plan or {}
        self.aufrufe: list[tuple[int, int]] = []
        self.vorgefunden: dict[tuple[int, int], list[str]] = {}
        monkeypatch.setattr(vnp46a3, "lade_monat", self._lade_monat)
        monkeypatch.setattr(vnp46a3, "verkleinere_monat", lambda dateien, erwarteter_monat=None: _leerer_monat(*erwarteter_monat))
        monkeypatch.setattr(io, "pruefe_speicher", lambda *a, **k: None)
        self.fake_ssd = fake_ssd

    def _lade_monat(self, jahr, monat, ziel_ordner, gleichzeitige_downloads=3, melde=None):
        m = (jahr, monat)
        self.aufrufe.append(m)
        # Was liegt beim Aufruf schon im Rohordner? (Beweis, dass nichts vorab gelöscht wird.)
        self.vorgefunden[m] = sorted(p.name for p in ziel_ordner.glob("*")) if ziel_ordner.exists() else []
        aufruf_nr = self.aufrufe.count(m)
        verhalten = self.plan.get(m, "ok")
        if isinstance(verhalten, list):
            verhalten = verhalten[min(aufruf_nr, len(verhalten)) - 1]
        ziel_ordner.mkdir(parents=True, exist_ok=True)
        (ziel_ordner / f"kachel_a_{aufruf_nr}.h5").touch()  # ein Teil ist da
        if verhalten == "ok":
            return vnp46a3.MonatsLadung(dateien=[ziel_ordner / f"kachel_a_{aufruf_nr}.h5"], zustaende={})
        if verhalten == "fehlt":
            raise vnp46a3.KachelnFehlen(f"{jahr:04d}-{monat:02d}: 1 von 2 Kacheln fehlen (HTTP 404).", dauerhaft=1, vorlaeufig=0)
        if verhalten == "502":
            raise vnp46a3.KachelnFehlen(f"{jahr:04d}-{monat:02d}: 1 von 2 Kacheln fehlen (HTTP 502).", dauerhaft=0, vorlaeufig=1)
        raise verhalten  # eine Ausnahme


def _starte_lauf(monkeypatch, fake_ssd, start, ende, **argumente) -> int:
    argv = ["lauf", "--start", start, "--ende", ende, "--gleichzeitig", "1"]
    monkeypatch.setattr(sys, "argv", argv)
    return vnp46a3_lauf.main()


def _protokoll(fake_ssd) -> str:
    return (fake_ssd / "protokoll" / "vnp46a3.log").read_text(encoding="utf-8")


def test_lauf_stellt_monat_mit_fehlender_kachel_zurueck_und_macht_weiter(monkeypatch, fake_ssd):
    lauf = LaufAttrappe(monkeypatch, fake_ssd, plan={(2018, 2): "fehlt"})
    rueckgabe = _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-03")

    assert rueckgabe == 2  # nicht 1 (Blocker), nicht 0 (alles fertig)
    # 2018-03 wurde trotz des Problems mit 2018-02 bearbeitet, 2018-02 danach noch einmal versucht.
    assert lauf.aufrufe == [(2018, 1), (2018, 2), (2018, 3), (2018, 2)]
    # Nur die zwei gesunden Monate stehen im Würfel; der zurückgestellte gilt NICHT als fertig.
    assert vnp46a3.vorhandene_monate() == {(2018, 1), (2018, 3)}
    # Rohdaten des zurückgestellten Monats sind nicht gelöscht, die der fertigen schon.
    assert sorted(p.name for p in (fake_ssd / "raw" / "vnp46a3" / "2018-02").glob("*"))
    assert not (fake_ssd / "raw" / "vnp46a3" / "2018-01").exists()

    text = _protokoll(fake_ssd)
    assert "2018-02: ZURÜCKGESTELLT (später erneut versuchen)" in text
    assert text.index("2018-02: ZURÜCKGESTELLT") < text.index("2018-03: fertig")
    assert "Nachhol-Durchgang 1 von höchstens 3: 1 zurückgestellte Monate" in text
    assert "kein Monat dazugekommen" in text  # ohne Fortschritt kein zweiter Durchgang und keine Pause
    assert "Lauf beendet mit offenen Monaten" in text and "2018-02" in text.split("Lauf beendet mit offenen Monaten")[1]
    assert "Lauf fertig" not in text
    assert "ABBRUCH" not in text and "FEHLER" not in text


def test_lauf_holt_502_monat_im_nachhol_durchgang_nach(monkeypatch, fake_ssd):
    lauf = LaufAttrappe(monkeypatch, fake_ssd, plan={(2018, 2): ["502", "ok"]})
    rueckgabe = _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-03")

    assert rueckgabe == 0
    assert vnp46a3.vorhandene_monate() == {(2018, 1), (2018, 2), (2018, 3)}
    text = _protokoll(fake_ssd)
    assert text.index("2018-03: fertig") < text.index("2018-02: fertig")  # 2018-02 kam erst am Ende
    assert "Lauf fertig: alle angefragten Monate stehen im Würfel." in text
    assert "Lauf beendet mit offenen Monaten" not in text
    # Der Rohordner des nachgeholten Monats wird erst nach dem Erfolg aufgeräumt.
    assert not (fake_ssd / "raw" / "vnp46a3" / "2018-02").exists()
    # Beim zweiten Versuch lagen die Reste des ersten noch da (nichts vorab gelöscht).
    assert lauf.vorgefunden[(2018, 2)] == ["kachel_a_1.h5"]


def test_lauf_wiederaufnahme_laedt_fertige_monate_nicht_neu(monkeypatch, fake_ssd):
    # Erster Lauf: 2018-01 und 2018-02 werden fertig.
    erster = LaufAttrappe(monkeypatch, fake_ssd)
    assert _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-02") == 0
    assert erster.aufrufe == [(2018, 1), (2018, 2)]

    # "Neustart" über einen längeren Zeitraum: nur der neue Monat wird geladen.
    zweiter = LaufAttrappe(monkeypatch, fake_ssd)
    assert _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-03") == 0
    assert zweiter.aufrufe == [(2018, 3)]
    assert "2 von 3 Monaten bereits fertig, 1 offen" in _protokoll(fake_ssd)


def test_neustart_verwendet_rohdaten_des_zurueckgestellten_monats_wieder(monkeypatch, fake_ssd):
    LaufAttrappe(monkeypatch, fake_ssd, plan={(2018, 2): "502"})
    assert _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-02") == 2

    # Neustart mit gesundem Server: 2018-01 ist fertig, 2018-02 wird fortgesetzt, nicht neu begonnen.
    neu = LaufAttrappe(monkeypatch, fake_ssd)
    assert _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-02") == 0
    assert neu.aufrufe == [(2018, 2)]
    assert neu.vorgefunden[(2018, 2)] != []  # die Kacheln vom ersten Versuch lagen noch da
    assert "Rohdaten aus früheren Versuchen vorhanden für: 2018-02" in _protokoll(fake_ssd)
    assert vnp46a3.vorhandene_monate() == {(2018, 1), (2018, 2)}


def test_lauf_endet_bei_anmeldefehler(monkeypatch, fake_ssd):
    lauf = LaufAttrappe(
        monkeypatch, fake_ssd, plan={(2018, 2): vnp46a3.AnmeldungFehlgeschlagen("Login fehlgeschlagen")}
    )
    assert _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-03") == 1
    assert lauf.aufrufe == [(2018, 1), (2018, 2)]  # 2018-03 nicht mehr begonnen
    assert vnp46a3.vorhandene_monate() == {(2018, 1)}
    assert "ABBRUCH bei 2018-02" in _protokoll(fake_ssd)


def test_lauf_endet_bei_zu_wenig_speicher(monkeypatch, fake_ssd):
    lauf = LaufAttrappe(monkeypatch, fake_ssd)
    zaehler = {"n": 0}

    def knapp(*a, **k):
        zaehler["n"] += 1
        if zaehler["n"] == 2:
            raise io.SpeicherZuKnapp("Nur noch 10 GB frei")

    monkeypatch.setattr(io, "pruefe_speicher", knapp)
    assert _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-03") == 1
    assert lauf.aufrufe == [(2018, 1)]
    assert vnp46a3.vorhandene_monate() == {(2018, 1)}  # fertiger Monat bleibt erhalten
    assert "ABBRUCH bei 2018-02: Nur noch 10 GB frei" in _protokoll(fake_ssd)


def test_lauf_endet_wenn_die_ssd_weg_ist(monkeypatch, fake_ssd):
    lauf = LaufAttrappe(monkeypatch, fake_ssd)

    def weg(*a, **k):
        raise io.SSDNichtGefunden("SSD nicht gefunden")

    monkeypatch.setattr(io, "pruefe_speicher", weg)
    assert _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-02") == 1
    assert lauf.aufrufe == []


def test_platte_voll_mitten_in_der_verarbeitung_beendet_den_lauf(monkeypatch, fake_ssd):
    lauf = LaufAttrappe(
        monkeypatch, fake_ssd, plan={(2018, 1): OSError(errno.ENOSPC, "No space left on device")}
    )
    assert _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-03") == 1
    assert lauf.aufrufe == [(2018, 1)]
    assert "ABBRUCH bei 2018-01" in _protokoll(fake_ssd)


def test_einzelner_verarbeitungsfehler_wird_zurueckgestellt_eine_serie_beendet_den_lauf(monkeypatch, fake_ssd):
    # Einzelfall: zurückstellen, weitermachen (Nachhol-Durchgang scheitert wieder -> Rückgabe 2).
    lauf = LaufAttrappe(monkeypatch, fake_ssd, plan={(2018, 2): ValueError("unlesbare Kachel")})
    assert _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-03") == 2
    assert (2018, 3) in lauf.aufrufe
    assert "Verarbeitungsfehler" in _protokoll(fake_ssd) and "unlesbare Kachel" in _protokoll(fake_ssd)


def test_serie_von_verarbeitungsfehlern_beendet_den_lauf(monkeypatch, fake_ssd):
    plan = {(2018, m): ValueError("immer derselbe Fehler") for m in (1, 2, 3, 4)}
    lauf = LaufAttrappe(monkeypatch, fake_ssd, plan=plan)
    assert _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-05") == 1
    assert lauf.aufrufe == [(2018, 1), (2018, 2), (2018, 3)]  # der vierte Monat wird nicht mehr geladen
    assert "Programm- oder Datenträgerfehler" in _protokoll(fake_ssd)


# --- Status: fertige, offene und nachzuholende Monate -------------------------


def test_status_liest_zurueckgestellte_monate_und_streicht_fertige():
    zeilen = [
        "2026-09-24 04:05:54 UTC  Lauf gestartet: Test.",
        "2026-09-24 04:05:55 UTC  2019-02: Start 2026-09-24 04:05:55 UTC.",
        "2026-09-24 05:25:56 UTC  2019-02: ZURÜCKGESTELLT (später erneut versuchen), nicht als fertig markiert, "
        "Rohdaten bleiben erhalten. 2019-02: 2 von 460 Kacheln fehlen (2 nach Wiederholung vorübergehend nicht ladbar).",
        "Traceback-Folgezeile ohne Zeitstempel",
        "2026-09-24 05:26:00 UTC  2019-03: Start 2026-09-24 05:26:00 UTC.",
    ]
    p = vnp46a3_status.lies_protokoll(zeilen)
    assert list(p["zurueckgestellt"]) == [(2019, 2)]
    assert "2 von 460 Kacheln fehlen" in p["zurueckgestellt"][(2019, 2)]
    assert p["aktuell"]["monat"] == (2019, 3)
    assert p["fehler"] == []  # ein zurückgestellter Monat ist kein Fehler

    zeilen += [
        "2026-09-24 09:00:00 UTC  2019-02: fertig, 460 Kacheln, Start x, Ende y, Dauer gesamt 70.0 Minuten "
        "(Download 65.0, Verkleinern und Schreiben 5.0), Manifest 2019-02.txt.",
    ]
    assert vnp46a3_status.lies_protokoll(zeilen)["zurueckgestellt"] == {}


def test_status_behaelt_zurueckgestellte_monate_ueber_einen_neustart_hinweg():
    zeilen = [
        "2026-09-24 05:25:56 UTC  2019-02: ZURÜCKGESTELLT (später erneut versuchen). Grund.",
        "2026-09-25 08:00:00 UTC  Lauf gestartet: neuer Start.",
    ]
    assert list(vnp46a3_status.lies_protokoll(zeilen)["zurueckgestellt"]) == [(2019, 2)]


def test_status_zeigt_fertig_offen_und_nachzuholen(monkeypatch, fake_ssd, capsys):
    protokoll = fake_ssd / "protokoll"
    protokoll.mkdir(parents=True)
    (protokoll / "vnp46a3.log").write_text(
        "2026-09-24 04:05:54 UTC  Lauf gestartet: Test.\n"
        "2026-09-24 05:25:56 UTC  2019-02: ZURÜCKGESTELLT (später erneut versuchen), nicht als fertig markiert, "
        "Rohdaten bleiben erhalten. 2 von 460 Kacheln fehlen.\n"
        "2026-09-24 05:26:00 UTC  Lauf beendet mit offenen Monaten: 1 Monate sind weiterhin nicht fertig.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(vnp46a3, "vorhandene_monate", lambda: {(2018, 1), (2018, 2)})
    monkeypatch.setattr(vnp46a3_status, "_prozess_nummern", lambda: [])

    assert vnp46a3_status.main() == 0
    ausgabe = capsys.readouterr().out
    assert "Fertige Monate: 2 von 156" in ausgabe
    assert "Offene Monate: 154 von 156" in ausgabe
    assert "Nachzuholen (zurückgestellt, später erneut versuchen): 1 Monat(e)" in ausgabe
    assert "2019-02: 2 von 460 Kacheln fehlen." in ausgabe
    assert "AMPEL: FERTIG MIT LÜCKEN" in ausgabe


def test_status_ohne_zurueckgestellte_monate(monkeypatch, fake_ssd, capsys):
    protokoll = fake_ssd / "protokoll"
    protokoll.mkdir(parents=True)
    (protokoll / "vnp46a3.log").write_text("2026-09-24 04:05:54 UTC  Lauf gestartet: Test.\n", encoding="utf-8")
    monkeypatch.setattr(vnp46a3, "vorhandene_monate", lambda: {(2018, 1)})
    monkeypatch.setattr(vnp46a3_status, "_prozess_nummern", lambda: [])
    vnp46a3_status.main()
    assert "Nachzuholen (zurückgestellt): keine" in capsys.readouterr().out


# --- 403: einzeln ein Kachelfehler, gehäuft ein Zugangsproblem (2026-09-24) --
#
# NASA antwortet bei abgelaufenem oder ungültigem Zugang oft mit 403 statt 401.
# Ohne diese Regel liefe der Lauf tagelang weiter, ohne etwas zu laden.


def _lade_mit_status(monkeypatch, tmp_path, ergebnisse: list):
    """Ruft `_lade_kachel` je Eintrag einmal auf: Zahl = HTTP-Fehler mit diesem Status, 'ok' = Erfolg.

    Gibt die Ausgänge zurück: 'KachelNichtGeladen', 'AnmeldungFehlgeschlagen' oder 'ok'.
    """
    reihe = iter(ergebnisse)

    def fake_download(granules, local_path):
        nächster = next(reihe)
        if nächster == "ok":
            return [str(Path(local_path) / "kachel.h5")]
        raise _fehler(nächster)

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    _schlaf_rekorder(monkeypatch)
    ausgaenge = []
    for _ in ergebnisse:
        try:
            vnp46a3._lade_kachel("granule-1", tmp_path, datei_timeout_sekunden=1)
            ausgaenge.append("ok")
        except vnp46a3.KachelNichtGeladen:
            ausgaenge.append("KachelNichtGeladen")
        except vnp46a3.AnmeldungFehlgeschlagen:
            ausgaenge.append("AnmeldungFehlgeschlagen")
    return ausgaenge


def test_einzelne_403_bleibt_ein_kachelfehler(monkeypatch, tmp_path):
    assert _lade_mit_status(monkeypatch, tmp_path, [403]) == ["KachelNichtGeladen"]


def test_fuenf_403_hintereinander_sind_noch_kachelfehler_die_sechste_ist_ein_blocker(monkeypatch, tmp_path):
    ausgaenge = _lade_mit_status(monkeypatch, tmp_path, [403] * 6)
    assert ausgaenge == ["KachelNichtGeladen"] * 5 + ["AnmeldungFehlgeschlagen"]


def test_erfolgreiche_kachel_setzt_den_403_zaehler_zurueck(monkeypatch, tmp_path):
    ausgaenge = _lade_mit_status(monkeypatch, tmp_path, [403] * 5 + ["ok"] + [403] * 5)
    assert "AnmeldungFehlgeschlagen" not in ausgaenge
    assert ausgaenge[5] == "ok"


def test_404_dazwischen_unterbricht_die_403_folge_nicht(monkeypatch, tmp_path):
    ausgaenge = _lade_mit_status(monkeypatch, tmp_path, [403, 403, 403, 404, 403, 403, 403])
    assert ausgaenge[-1] == "AnmeldungFehlgeschlagen"


def test_403_blocker_meldung_sagt_klar_was_zu_tun_ist(monkeypatch, tmp_path):
    def fake_download(granules, local_path):
        raise _fehler(403)

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    _schlaf_rekorder(monkeypatch)
    for _ in range(5):
        with pytest.raises(vnp46a3.KachelNichtGeladen):
            vnp46a3._lade_kachel("granule-1", tmp_path, datei_timeout_sekunden=1)
    with pytest.raises(vnp46a3.AnmeldungFehlgeschlagen, match="Anmeldung prüfen.*403.*\\.env"):
        vnp46a3._lade_kachel("granule-1", tmp_path, datei_timeout_sekunden=1)


def test_lade_monat_mit_dauerhaft_403_beendet_sich_als_blocker_und_laedt_nicht_alles_durch(monkeypatch, tmp_path):
    granules = [_Granule(h) for h in range(40)]
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    monkeypatch.setattr(vnp46a3.earthaccess, "search_data", lambda **kwargs: granules)
    aufrufe = {"n": 0}

    def fake_download(granules_, local_path):
        aufrufe["n"] += 1
        time.sleep(0.02)
        raise _fehler(403)

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    with pytest.raises(vnp46a3.AnmeldungFehlgeschlagen, match="Anmeldung prüfen"):
        vnp46a3.lade_monat(2024, 1, tmp_path, gleichzeitige_downloads=1)
    assert aufrufe["n"] <= 10  # nach der sechsten 403 Schluss, nicht alle 40 Kacheln


def test_alle_kacheln_eines_kleinen_monats_mit_403_sind_ein_blocker(monkeypatch, tmp_path, monat_mit_5_kacheln):
    def fake_lade_kachel(granule, ziel_ordner, **kwargs):
        raise vnp46a3.KachelNichtGeladen("403", dauerhaft=True, status=403)

    monkeypatch.setattr(vnp46a3, "_lade_kachel", fake_lade_kachel)
    with pytest.raises(vnp46a3.AnmeldungFehlgeschlagen, match="alle 5 Kacheln"):
        vnp46a3.lade_monat(2024, 1, tmp_path, gleichzeitige_downloads=1)


def test_eine_403_kachel_in_einem_monat_bleibt_ein_kachelfehler(monkeypatch, tmp_path, monat_mit_5_kacheln):
    granules = monat_mit_5_kacheln

    def fake_lade_kachel(granule, ziel_ordner, **kwargs):
        if granule is granules[2]:
            raise vnp46a3.KachelNichtGeladen("403", dauerhaft=True, status=403)
        return _schreibe_gueltige_kachel(ziel_ordner, granule)

    monkeypatch.setattr(vnp46a3, "_lade_kachel", fake_lade_kachel)
    with pytest.raises(vnp46a3.KachelnFehlen):
        vnp46a3.lade_monat(2024, 1, tmp_path, gleichzeitige_downloads=1)


def test_fortsetzung_mit_zwei_fehlenden_403_kacheln_ist_kein_alle_kacheln_fall(
    monkeypatch, tmp_path, monat_mit_5_kacheln
):
    """Sind 3 von 5 Kacheln schon da und die restlichen 2 bekommen 403, sind es nicht 'alle Kacheln des Monats'."""
    granules = monat_mit_5_kacheln
    for g in granules[:3]:
        _schreibe_gueltige_kachel(tmp_path, g)

    def fake_lade_kachel(granule, ziel_ordner, **kwargs):
        raise vnp46a3.KachelNichtGeladen("403", dauerhaft=True, status=403)

    monkeypatch.setattr(vnp46a3, "_lade_kachel", fake_lade_kachel)
    with pytest.raises(vnp46a3.KachelnFehlen):
        vnp46a3.lade_monat(2024, 1, tmp_path, gleichzeitige_downloads=1)


def test_lauf_endet_bei_gehaeuften_403_mit_klarer_meldung(monkeypatch, fake_ssd):
    lauf = LaufAttrappe(
        monkeypatch,
        fake_ssd,
        plan={(2018, 2): vnp46a3.AnmeldungFehlgeschlagen(vnp46a3._zugang_pruefen_meldung("alle 460 Kacheln von 2018-02 mit"))},
    )
    assert _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-03") == 1
    assert lauf.aufrufe == [(2018, 1), (2018, 2)]
    text = _protokoll(fake_ssd)
    assert "ABBRUCH bei 2018-02: Anmeldung prüfen" in text and "403" in text


# --- Nachhol-Durchgang: wiederholen, solange etwas dazukommt (2026-09-24) -----


def _schlaf_rekorder_lauf(monkeypatch) -> list[float]:
    pausen: list[float] = []
    monkeypatch.setattr(vnp46a3_lauf.time, "sleep", lambda s: pausen.append(s))
    return pausen


def test_nachhol_durchgang_wiederholt_sich_solange_ein_monat_dazukommt(monkeypatch, fake_ssd):
    pausen = _schlaf_rekorder_lauf(monkeypatch)
    # A klappt im 1. Nachhol-Durchgang, B erst im 2.
    lauf = LaufAttrappe(monkeypatch, fake_ssd, plan={(2018, 1): ["502", "ok"], (2018, 2): ["502", "502", "ok"]})
    assert _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-02") == 0

    assert vnp46a3.vorhandene_monate() == {(2018, 1), (2018, 2)}
    assert pausen == [30 * 60]  # genau eine Pause von 30 Minuten zwischen Durchgang 1 und 2
    assert lauf.aufrufe == [(2018, 1), (2018, 2), (2018, 1), (2018, 2), (2018, 2)]
    text = _protokoll(fake_ssd)
    assert "Nachhol-Durchgang 1 von höchstens 3" in text and "Nachhol-Durchgang 2 von höchstens 3" in text
    assert "Pause 30 Minuten, dann Durchgang 2" in text
    assert "Lauf fertig" in text


def test_nachhol_durchgang_hoert_ohne_fortschritt_auf_und_pausiert_nicht(monkeypatch, fake_ssd):
    pausen = _schlaf_rekorder_lauf(monkeypatch)
    lauf = LaufAttrappe(monkeypatch, fake_ssd, plan={(2018, 2): "502"})
    assert _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-02") == 2
    assert pausen == []
    assert lauf.aufrufe.count((2018, 2)) == 2  # Hauptdurchgang + ein Nachhol-Durchgang
    assert "kein Monat dazugekommen" in _protokoll(fake_ssd)


def test_nachhol_durchgaenge_sind_auf_drei_begrenzt(monkeypatch, fake_ssd):
    pausen = _schlaf_rekorder_lauf(monkeypatch)
    # Je Durchgang kommt ein Monat dazu, aber D klappt nie: nach dem 3. Durchgang ist Schluss.
    plan = {
        (2018, 1): ["502", "ok"],
        (2018, 2): ["502", "502", "ok"],
        (2018, 3): ["502", "502", "502", "ok"],
        (2018, 4): "502",
    }
    lauf = LaufAttrappe(monkeypatch, fake_ssd, plan=plan)
    assert _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-04") == 2

    assert vnp46a3.vorhandene_monate() == {(2018, 1), (2018, 2), (2018, 3)}
    assert pausen == [30 * 60, 30 * 60]  # zwei Pausen zwischen drei Durchgängen
    assert lauf.aufrufe.count((2018, 4)) == 4  # Hauptdurchgang + 3 Nachhol-Durchgänge, kein vierter
    text = _protokoll(fake_ssd)
    assert "Nachhol-Durchgang 4" not in text
    assert "Höchstzahl an Durchgängen erreicht" in text
    assert "Lauf beendet mit offenen Monaten" in text and "2018-04" in text.split("Lauf beendet mit offenen Monaten")[1]


def test_blocker_im_nachhol_durchgang_beendet_den_lauf_ebenfalls(monkeypatch, fake_ssd):
    _schlaf_rekorder_lauf(monkeypatch)
    LaufAttrappe(monkeypatch, fake_ssd, plan={(2018, 1): ["502", vnp46a3.AnmeldungFehlgeschlagen("Login weg")]})
    assert _starte_lauf(monkeypatch, fake_ssd, "2018-01", "2018-02") == 1
    assert "ABBRUCH bei 2018-01: Login weg" in _protokoll(fake_ssd)


# --- Status: Sonderfall fortgesetzter Monat, Nachhol-Anzeige ------------------


def _fertig_zeile(monat: str, minuten: float, download: float) -> str:
    return (
        f"2026-09-24 12:00:00 UTC  {monat}: fertig, 460 Kacheln, Start x, Ende y, Dauer gesamt {minuten} Minuten "
        f"(Download {download}, Verkleinern und Schreiben 5.0), Manifest {monat}.txt."
    )


def test_status_erkennt_fortgesetzte_monate():
    zeilen = [
        "2026-09-24 10:25:55 UTC  Lauf gestartet: Test.",
        "2026-09-24 10:26:00 UTC  2019-02: 458 Kacheln aus einem früheren Versuch schon vorhanden und gültig, 2 werden noch geladen.",
    ]
    assert vnp46a3_status.lies_protokoll(zeilen)["wiederaufgenommen"] == {(2019, 2)}


def test_status_rechnet_fortgesetzten_monat_aus_der_restzeit_heraus(monkeypatch, fake_ssd, capsys):
    protokoll = fake_ssd / "protokoll"
    protokoll.mkdir(parents=True)
    (protokoll / "vnp46a3.log").write_text(
        "2026-09-24 00:00:00 UTC  Lauf gestartet: Test.\n"
        + _fertig_zeile("2018-12", 70.0, 65.0) + "\n"
        + "2026-09-24 10:26:00 UTC  2019-02: 458 Kacheln aus einem früheren Versuch schon vorhanden und gültig, 2 werden noch geladen.\n"
        + _fertig_zeile("2019-02", 7.5, 0.4) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(vnp46a3, "vorhandene_monate", lambda: {(2018, 12), (2019, 2)})
    monkeypatch.setattr(vnp46a3_status, "_prozess_nummern", lambda: [])
    vnp46a3_status.main()
    ausgabe = capsys.readouterr().out
    assert "Gemessen an 1 vollständig geladenen Monat(en)" in ausgabe
    assert "Nicht eingerechnet (Sonderfall" in ausgabe and "2019-02" in ausgabe
    assert "Ø 70.0 Minuten/Monat" in ausgabe  # nicht (70,0 + 7,5) / 2 = 38,8
    # 154 offene Monate * 539 Kacheln * (70 min / 460 Kacheln) ergibt Tage in der Größenordnung von 9,
    # nicht die zu optimistischen rund 5 mit dem 7,5-Minuten-Monat
    assert "etwa 9 bis 9 Tage" in ausgabe


def test_status_zeigt_den_nachhol_durchgang_waehrend_der_pause(monkeypatch, fake_ssd, capsys):
    protokoll = fake_ssd / "protokoll"
    protokoll.mkdir(parents=True)
    (protokoll / "vnp46a3.log").write_text(
        "2026-09-24 12:00:00 UTC  Lauf gestartet: Test.\n"
        "2026-09-24 12:01:00 UTC  2018-02: ZURÜCKGESTELLT (später erneut versuchen). Rohdaten bleiben erhalten. x\n"
        "2026-09-24 12:02:00 UTC  Nachhol-Durchgang 1: 1 Monat(e) dazugekommen, 1 weiterhin offen. Pause 30 Minuten, dann Durchgang 2.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(vnp46a3, "vorhandene_monate", lambda: set())
    monkeypatch.setattr(vnp46a3_status, "_prozess_nummern", lambda: ["123"])
    vnp46a3_status.main()
    assert "Nachholen: Nachhol-Durchgang 1: 1 Monat(e) dazugekommen" in capsys.readouterr().out
