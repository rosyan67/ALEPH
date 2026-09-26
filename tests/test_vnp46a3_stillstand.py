"""Tests zum Umbau vom 2026-09-26: Stillstands-Erkennung statt fester 4-Stunden-Frist,
Download-Statistik im Protokoll, Reihenfolge nach Neustart, Durchsatz und Hochrechnung im Status.

Die Zeiten sind in den Tests auf Bruchteile von Sekunden verkleinert
(`stillstand_sekunden`, `notbremse_sekunden`); die Logik ist dieselbe wie mit
30 Minuten bzw. 12 Stunden.
"""

import concurrent.futures
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from aleph.core import io
from aleph.layers import vnp46a3, vnp46a3_lauf, vnp46a3_status


def _starte(aufgaben, gleichzeitig=1):
    """Startet Aufgaben (Funktionen ohne Argument) in einem Pool; Rückgabe (pool, future->position)."""
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=gleichzeitig)
    return pool, {pool.submit(f): f"h{i:02d}v00" for i, f in enumerate(aufgaben)}


def _kachel(dauer, ergebnis="datei"):
    def f():
        time.sleep(dauer)
        return Path(ergebnis)
    return f


def _scheitert(dauer):
    def f():
        time.sleep(dauer)
        raise vnp46a3.KachelNichtGeladen("simuliert", dauerhaft=False)
    return f


# ---------------------------------------------------------------- Stillstand


def test_langsamer_aber_stetiger_fortschritt_bricht_nicht_ab():
    # 10 Kacheln, je 0,12 s, eine nach der anderen: insgesamt 1,2 s, also weit
    # über der Stillstandsgrenze von 0,5 s - aber nie 0,5 s ohne neue Kachel.
    pool, fz = _starte([_kachel(0.12) for _ in range(10)])
    geladen, fehl = {}, []
    abgebrochen = vnp46a3._sammle_kacheln(fz, geladen, fehl, "2018-01", 10, stillstand_sekunden=0.5, notbremse_sekunden=30)
    pool.shutdown()
    assert abgebrochen is False
    assert len(geladen) == 10 and fehl == []


def test_stillstand_wird_erkannt():
    pool, fz = _starte([_kachel(0.05), _kachel(3.0)])
    geladen = {}
    t0 = time.monotonic()
    with pytest.raises(vnp46a3.DownloadHaengt) as info:
        vnp46a3._sammle_kacheln(fz, geladen, [], "2018-01", 2, stillstand_sekunden=0.4, notbremse_sekunden=30)
    dauer = time.monotonic() - t0
    pool.shutdown(wait=False, cancel_futures=True)
    assert not isinstance(info.value, vnp46a3.DownloadZuLangsam)
    text = str(info.value)
    assert "Stillstand" in text and "keine neue, geprüfte Kachel" in text and "1 von 2 Kacheln fertig" in text
    assert "reagiert seit über" not in text  # die alte, irreführende Meldung ist weg
    # erkannt rund 0,4 s nach der letzten fertigen Kachel, nicht erst nach der hängenden
    assert 0.4 <= dauer < 1.5


def test_gescheiterte_kacheln_zaehlen_nicht_als_fortschritt():
    # Alle 0,1 s scheitert eine Kachel, aber keine wird fertig: das ist Stillstand.
    pool, fz = _starte([_scheitert(0.1) for _ in range(6)] + [_kachel(5.0)])
    fehl = []
    with pytest.raises(vnp46a3.DownloadHaengt):
        vnp46a3._sammle_kacheln(fz, {}, fehl, "2018-01", 7, stillstand_sekunden=0.35, notbremse_sekunden=30)
    pool.shutdown(wait=False, cancel_futures=True)
    assert len(fehl) >= 3


def test_notbremse_greift_trotz_fortschritt():
    pool, fz = _starte([_kachel(0.1) for _ in range(40)])
    t0 = time.monotonic()
    with pytest.raises(vnp46a3.DownloadZuLangsam) as info:
        vnp46a3._sammle_kacheln(fz, {}, [], "2018-01", 40, stillstand_sekunden=0.5, notbremse_sekunden=0.6)
    pool.shutdown(wait=False, cancel_futures=True)
    assert time.monotonic() - t0 < 1.5
    assert "Notbremse" in str(info.value) and "obwohl noch Kacheln ankommen" in str(info.value)
    # Notbremse ist ein Unterfall des Hängers: vnp46a3_lauf stellt den Monat zurück
    assert isinstance(info.value, vnp46a3.DownloadHaengt)


def test_zu_viele_gescheiterte_kacheln_brechen_den_monat_ab(monkeypatch):
    monkeypatch.setattr(vnp46a3, "MAX_GESCHEITERTE_KACHELN_JE_MONAT", 3)
    pool, fz = _starte([_scheitert(0.01) for _ in range(5)])
    fehl = []
    assert vnp46a3._sammle_kacheln(fz, {}, fehl, "2018-01", 5, stillstand_sekunden=5, notbremse_sekunden=30) is True
    pool.shutdown(wait=False, cancel_futures=True)
    assert len(fehl) == 3


def test_blocker_wird_sofort_weitergereicht():
    def blocker():
        raise io.SpeicherZuKnapp("voll")
    pool, fz = _starte([blocker])
    with pytest.raises(io.SpeicherZuKnapp):
        vnp46a3._sammle_kacheln(fz, {}, [], "2018-01", 1, stillstand_sekunden=5, notbremse_sekunden=30)
    pool.shutdown()


def test_standardwerte_und_alte_frist_entfernt():
    assert vnp46a3.STILLSTAND_SEKUNDEN == 30 * 60
    assert vnp46a3.MONAT_NOTBREMSE_SEKUNDEN == 12 * 60 * 60
    assert vnp46a3.STILLSTAND_SEKUNDEN > vnp46a3.DATEI_TIMEOUT_SEKUNDEN  # ein Kachel-Hänger bricht den Monat nicht ab
    assert not hasattr(vnp46a3, "DOWNLOAD_TIMEOUT_SEKUNDEN")


# ---------------------------------------------------------------- Statistik


def test_statistik_zaehlt_verworfene_und_neue_kacheln(tmp_path, monkeypatch):
    datei = tmp_path / "VNP46A3.A2018001.h00v00.002.x.h5"
    aufrufe = {"n": 0}

    def lade(granule, ziel, stopp=None, statistik=None, **zeitlimits):
        aufrufe["n"] += 1
        datei.write_bytes(b"x" * (100 if aufrufe["n"] == 1 else 250))
        return datei

    monkeypatch.setattr(vnp46a3, "_lade_kachel", lade)
    monkeypatch.setattr(vnp46a3, "_pruefe_gegen_katalog", lambda p, soll: "MD5 falsch" if aufrufe["n"] == 1 else None)
    st = vnp46a3.LadeStatistik()
    vnp46a3._lade_und_pruefe_kachel(object(), object(), tmp_path, statistik=st)
    assert (st.verworfen, st.verworfen_endgueltig, st.neu_anzahl, st.neu_bytes) == (1, 0, 1, 250)
    assert st.abdruecke[datei] == vnp46a3._abdruck(datei)  # Fingerabdruck der geprüften Datei


def test_endgueltig_verworfene_kachel_wird_gezaehlt(tmp_path, monkeypatch):
    datei = tmp_path / "k.h5"

    def lade(granule, ziel, stopp=None, statistik=None, **zeitlimits):
        datei.write_bytes(b"x")
        return datei

    monkeypatch.setattr(vnp46a3, "_lade_kachel", lade)
    monkeypatch.setattr(vnp46a3, "_pruefe_gegen_katalog", lambda p, soll: "MD5 falsch")
    st = vnp46a3.LadeStatistik()
    class Soll:
        datei, groesse = "k.h5", None

    with pytest.raises(vnp46a3.KachelNichtGeladen):
        vnp46a3._lade_und_pruefe_kachel(object(), Soll(), tmp_path, statistik=st, versuche=2)
    assert (st.verworfen, st.verworfen_endgueltig, st.neu_anzahl) == (2, 1, 0)


def test_zeitlimit_je_kachel_waechst_mit_der_groesse(monkeypatch):
    assert vnp46a3.kachel_zeitlimit(None) == vnp46a3.DATEI_TIMEOUT_SEKUNDEN
    assert vnp46a3.kachel_zeitlimit(10_000_000) == vnp46a3.DATEI_TIMEOUT_SEKUNDEN
    # größte beobachtete Kachel: 158,5 MB bei 0,1 MB/s = 26,4 Minuten
    assert vnp46a3.kachel_zeitlimit(158_524_351) == pytest.approx(1585.24351)
    gesehen = {}

    def lade(granule, ziel, stopp=None, statistik=None, datei_timeout_sekunden=None, retry_budget_sekunden=None):
        gesehen.update(timeout=datei_timeout_sekunden, budget=retry_budget_sekunden)
        raise vnp46a3.KachelNichtGeladen("egal", dauerhaft=True)

    class Soll:
        groesse = 158_524_351

    monkeypatch.setattr(vnp46a3, "_lade_kachel", lade)
    with pytest.raises(vnp46a3.KachelNichtGeladen):
        vnp46a3._lade_und_pruefe_kachel(object(), Soll(), Path("."))
    assert gesehen["timeout"] == pytest.approx(1585.24351)
    assert gesehen["budget"] == pytest.approx(3 * 1585.24351)  # Platz für mehr als einen Versuch


def test_ersetzte_datei_wird_erkannt_und_neu_geprueft(tmp_path, monkeypatch):
    a, b, c = tmp_path / "a.h5", tmp_path / "b.h5", tmp_path / "c.h5"
    for f in (a, b, c):
        f.write_bytes(b"geprueft")
    abdruecke = {f: vnp46a3._abdruck(f) for f in (a, b, c)}
    # b: von einem späten Download-Faden durch anderen Inhalt ersetzt; c: verschwunden
    neu = tmp_path / "tmp"
    neu.write_bytes(b"ANDERER INHALT")
    os.replace(neu, b)
    c.unlink()
    monkeypatch.setattr(vnp46a3, "_pruefe_gegen_katalog", lambda p, soll: None if p.read_bytes() == b"geprueft" else "MD5 passt nicht")
    schlecht = vnp46a3.pruefe_unveraendert({"a": a, "b": b, "c": c}, {"a": 1, "b": 2, "c": 3}, abdruecke)
    assert set(schlecht) == {"b", "c"}
    assert "nach der Prüfung verändert" in schlecht["b"] and "verschwunden" in schlecht["c"]


def test_ersetzte_datei_mit_gleichem_inhalt_bleibt_gueltig(tmp_path, monkeypatch):
    a = tmp_path / "a.h5"
    a.write_bytes(b"geprueft")
    abdruecke = {a: vnp46a3._abdruck(a)}
    neu = tmp_path / "tmp"
    neu.write_bytes(b"geprueft")
    os.replace(neu, a)
    monkeypatch.setattr(vnp46a3, "_pruefe_gegen_katalog", lambda p, soll: None)
    assert vnp46a3.pruefe_unveraendert({"a": a}, {"a": 1}, abdruecke) == {}


def test_abbruchrunde_traegt_erst_alle_fertigen_kacheln_ein(monkeypatch):
    """Auflage A3: Kacheln, die in derselben Runde fertig wurden, gehen nicht verloren."""
    monkeypatch.setattr(vnp46a3, "MAX_GESCHEITERTE_KACHELN_JE_MONAT", 1)
    ok = concurrent.futures.Future()
    ok.set_result(Path("gut.h5"))
    schlecht = concurrent.futures.Future()
    schlecht.set_exception(vnp46a3.KachelNichtGeladen("x", dauerhaft=True))
    geladen, fehl = {}, []
    assert vnp46a3._sammle_kacheln({schlecht: "h01v01", ok: "h02v02"}, geladen, fehl, "2018-01", 2,
                                   stillstand_sekunden=5, notbremse_sekunden=30) is True
    assert geladen == {"h02v02": Path("gut.h5")} and len(fehl) == 1


def test_statistik_zaehlt_wiederholungen(tmp_path, monkeypatch):
    aufrufe = {"n": 0}

    def download(granules, ziel):
        aufrufe["n"] += 1
        if aufrufe["n"] < 3:
            raise vnp46a3.DownloadHaengt("simulierte Zeitüberschreitung")
        return [str(tmp_path / "k.h5")]

    monkeypatch.setattr(vnp46a3.earthaccess, "download", download)
    st = vnp46a3.LadeStatistik()
    vnp46a3._lade_kachel(object(), tmp_path, wartezeit_basis_sekunden=0.01, wartezeit_max_sekunden=0.01, statistik=st)
    assert st.wiederholungen == 2


def test_statistikzeile_wird_vom_status_gelesen():
    st = vnp46a3.LadeStatistik()
    st.neu(1_500_000_000)
    st.neu(500_000_000)
    st.verwerfe()
    st.wiederhole()
    zeile = "2026-09-26 12:00:00 UTC  2018-01: " + st.text(1000.0, "vollständig geladen")
    assert "2.00 MB/s geprüfte Nutzdaten einschließlich Wartezeit" in zeile  # 2 GB in 1000 s
    assert "ohne interne Versuche von earthaccess" in zeile
    p = vnp46a3_status.lies_protokoll([zeile])
    assert p["statistik"] == [{
        "monat": (2018, 1), "zustand": "vollständig geladen", "kacheln": 2, "gb": 2.0, "minuten": 16.7,
        "mb_s": 2.0, "verworfen": 1, "verworfen_endgueltig": 0, "wiederholungen": 1,
    }]
    # darf nicht als "Download fertig" gelesen werden
    assert p["aktuell"] is None


# ---------------------------------------------------------------- Reihenfolge nach Neustart


def test_zurueckgestellte_monate_2018_kommen_nach_neustart_zuerst():
    """Die Liste der Zurückgestellten lebt nur im laufenden Prozess. Nach einem
    Neustart bildet der Lauf die Reihenfolge neu aus dem Würfel: nicht fertige
    Monate, mit `--vorrang 2018-01..2019-12,2024-01` vorne, 2018-01 zuerst."""
    alle = vnp46a3_lauf._monatsliste("2013-01", "2025-12")
    fertig = {(2019, 1)}  # angenommen fertig: fällt heraus
    vorrang = vnp46a3_lauf._vorrang_argument("2018-01..2019-12,2024-01")
    folge = vnp46a3_lauf._reihenfolge([m for m in alle if m not in fertig], "2018-01", vorrang)
    assert folge[:5] == [(2018, 1), (2018, 2), (2018, 3), (2018, 4), (2018, 5)]
    assert (2019, 1) not in folge
    assert len(folge) == 155 and len(set(folge)) == 155


# ---------------------------------------------------------------- Status: Durchsatz, Hochrechnung


def test_hochrechnung_nach_datenmenge():
    h = vnp46a3_status.hochrechnung(offene_monate=100, roh_bytes=100 * 10**9, mb_s_min=1.5, mb_s_max=2.0)
    assert h["tb"][0] == pytest.approx(2.7) and h["tb"][1] == pytest.approx(3.21)
    # kürzeste: 2,7 TB bei 2 MB/s; längste: 3,21 TB bei 1,5 MB/s; je + 100 × 6,5 min
    assert h["tage"][0] == pytest.approx(2.7e12 / 2e6 / 86400 + 100 * 6.5 / 1440)
    assert h["tage"][1] == pytest.approx(3.21e12 / 1.5e6 / 86400 + 100 * 6.5 / 1440)


def test_durchsatz_zaehlt_nur_fertige_kacheln_im_fenster(tmp_path):
    jetzt = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
    t = jetzt.timestamp()
    for name, groesse, alter_min in [("a.h5", 900_000_000, 5), ("b.h5", 900_000_000, 20),
                                     ("alt.h5", 900_000_000, 45), ("partial_c.h5", 900_000_000, 1)]:
        p = tmp_path / name
        p.write_bytes(b"")
        os.truncate(p, groesse)
        os.utime(p, (t - alter_min * 60, t - alter_min * 60))
    assert vnp46a3_status.durchsatz_im_ordner(tmp_path, jetzt, 30) == pytest.approx(1800 / 1800)
    assert vnp46a3_status.durchsatz_im_ordner(tmp_path / "fehlt", jetzt) is None


def test_status_zeigt_statistik_durchsatz_und_hochrechnung(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("ALEPH_DATA_DIR", str(tmp_path))
    (tmp_path / "protokoll").mkdir()
    (tmp_path / "protokoll" / "vnp46a3.log").write_text(
        "2026-09-26 08:00:00 UTC  Lauf gestartet: Test.\n"
        "2026-09-26 08:00:01 UTC  2018-01: Start 2026-09-26 08:00:01 UTC.\n"
        "2026-09-26 09:00:00 UTC  2018-01: Download-Statistik (vollständig geladen): 500 Kacheln neu geladen (26.3 GB) "
        "in 220.0 Minuten, 1.99 MB/s geprüfte Nutzdaten einschließlich Wartezeit; 2 nach Größen-/MD5-Prüfung verworfen "
        "(davon 0 nicht mehr neu geladen); 5 Wiederholungen nach Netzfehler oder Zeitüberschreitung (ohne interne "
        "Versuche von earthaccess).\n"
        "2026-09-26 10:00:00 UTC  2018-02: Download-Statistik (abgebrochen): 10 Kacheln neu geladen (0.5 GB) "
        "in 40.0 Minuten, 0.21 MB/s geprüfte Nutzdaten einschließlich Wartezeit; 0 nach Größen-/MD5-Prüfung verworfen "
        "(davon 0 nicht mehr neu geladen); 0 Wiederholungen nach Netzfehler oder Zeitüberschreitung (ohne interne "
        "Versuche von earthaccess).\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(vnp46a3, "vorhandene_monate", lambda: set())
    monkeypatch.setattr(vnp46a3_status, "_prozess_nummern", lambda: [])
    vnp46a3_status.main()
    aus = capsys.readouterr().out
    assert "Letzte Download-Statistik (2018-02, abgebrochen): 10 Kacheln" in aus
    # die abgebrochene Zeile (0,21 MB/s mit Stillstand) geht NICHT in den Durchsatz ein
    assert "Durchsatz: 2.0 MB/s (1 zuletzt vollständig geladene Monate)." in aus
    assert "Hochrechnung bis ganz fertig (alle Stufen): noch etwa 4.4 bis 5.2 TB (156 offene Monate × 28-33 GB, davon 0 mit Zustand 4" in aus
    assert "Hochrechnung Stufe 1 (nur Afrika-Europa-Asien, 156 Monate" in aus
    assert "Vollständig für Afrika-Europa-Asien (Zustand 4 oder fertig): 0 von 156" in aus
    assert "Annahme: der Durchsatz bleibt in dieser Spanne" in aus


def test_durchsatz_zaehlt_erst_ab_download_beginn(tmp_path):
    """Am Monatsanfang prüft der Lauf erst die vorhandenen Kacheln; diese Zeit darf den Durchsatz nicht drücken."""
    jetzt = datetime(2026, 9, 26, 12, 28, tzinfo=timezone.utc)
    beginn = datetime(2026, 9, 26, 12, 18, tzinfo=timezone.utc)  # 10 Minuten geladen
    p = tmp_path / "neu.h5"
    p.write_bytes(b"")
    os.truncate(p, 1_200_000_000)
    os.utime(p, (jetzt.timestamp() - 60, jetzt.timestamp() - 60))
    assert vnp46a3_status.durchsatz_im_ordner(tmp_path, jetzt, 30) == pytest.approx(1200 / 1800)
    assert vnp46a3_status.durchsatz_im_ordner(tmp_path, jetzt, 30, download_seit=beginn) == pytest.approx(1200 / 600)
    # zu kurzes Fenster: kein Wert statt eines Zufallswerts
    assert vnp46a3_status.durchsatz_im_ordner(tmp_path, jetzt, 30, download_seit=jetzt) is None


def test_protokoll_merkt_download_beginn_und_teilstufe():
    zeilen = [
        "2026-09-26 12:13:05 UTC  2018-01: Start 2026-09-26 12:13:05 UTC (Stufe 1: nur Afrika-Europa-Asien).",
        "2026-09-26 12:13:16 UTC  2018-01: 188 Kacheln bei NASA gemeldet für 188 ausgewählte Positionen (Katalog gesamt 540) (Katalog: 540 Treffer, alle geholt; Referenzliste 188 Positionen), Download beginnt.",
        "2026-09-26 12:18:47 UTC  2018-01: 167 Kacheln aus einem früheren Versuch schon vorhanden und gültig (Größe und MD5 geprüft), 0 verworfen, weil sie nicht zum Katalog passten, 21 werden noch geladen.",
    ]
    a = vnp46a3_status.lies_protokoll(zeilen)["aktuell"]
    assert a["gemeldet"] == 188 and a["teil"] is True
    assert a["download_seit"] == datetime(2026, 9, 26, 12, 18, 47, tzinfo=timezone.utc)


def test_alte_dateien_im_rohordner_melden_keinen_haenger(monkeypatch, tmp_path, capsys):
    """Ein Monat mit Kacheln vom Vortag im Rohordner, eben gestartet: Ampel darf nicht HÄNGT zeigen."""
    monkeypatch.setenv("ALEPH_DATA_DIR", str(tmp_path))
    jetzt = datetime.now(timezone.utc)
    ordner = tmp_path / "raw" / "vnp46a3" / "2018-02"
    ordner.mkdir(parents=True)
    alt = ordner / "VNP46A3.A2018032.h19v03.002.x.h5"
    alt.write_bytes(b"x")
    os.utime(alt, (jetzt.timestamp() - 86400, jetzt.timestamp() - 86400))  # von gestern
    (tmp_path / "protokoll").mkdir()
    start = jetzt.strftime("%Y-%m-%d %H:%M:%S")
    (tmp_path / "protokoll" / "vnp46a3.log").write_text(
        f"{start} UTC  Lauf gestartet: Test.\n{start} UTC  2018-02: Start {start} UTC (Stufe 1: nur Afrika-Europa-Asien).\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(vnp46a3, "vorhandene_monate", lambda: set())
    monkeypatch.setattr(vnp46a3_status, "_prozess_nummern", lambda: ["123"])
    vnp46a3_status.main()
    aus = capsys.readouterr().out
    assert "AMPEL: OK" in aus
