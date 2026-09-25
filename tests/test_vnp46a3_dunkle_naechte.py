"""Tests für das Kriterium „Kachel darf fehlen, weil es keine Nacht gibt" (aleph/layers/vnp46a3_dunkle_naechte.py).

Anlass: 2022-07 fehlen im NASA-Katalog 36 Kacheln (Reihe v01, 70-80° N),
LOG.md 2026-09-25. Kein Netzzugriff. Die Referenzwerte der Deklination sind
mit astropy 8.0.1 berechnet (scheinbare Deklination, wahrer Äquator zum Datum,
Rahmen TETE), am 2026-09-25; astropy ist keine Projektabhängigkeit.
"""

from datetime import datetime, timezone

import numpy as np
import pytest

from aleph.layers import vnp46a3_dunkle_naechte as dn

# Die 36 Positionen, die der NASA-Katalog für 2022-07 nicht meldet (Abfrage
# über vnp46a3._katalog_abfrage am 2026-09-25: 504 Treffer, Referenzliste 540).
FEHLEND_2022_07 = [f"h{h:02d}v01" for h in range(36)]


# --- Geometrie ----------------------------------------------------------------


@pytest.mark.parametrize(
    "v, sued, nord",
    [(0, 80, 90), (1, 70, 80), (2, 60, 70), (8, 0, 10), (9, -10, 0), (15, -70, -60), (17, -90, -80)],
)
def test_kachel_breiten_im_geo_gitter(v, sued, nord):
    assert dn.kachel_breiten(v) == (sued, nord)


@pytest.mark.parametrize("v", [-1, 18])
def test_kachel_breiten_lehnt_unbekannte_zeile_ab(v):
    with pytest.raises(ValueError):
        dn.kachel_breiten(v)


def test_zeile_aus_position():
    assert dn.zeile_aus_position("h21v05") == 5
    assert dn.zeile_aus_position("h00v01") == 1
    with pytest.raises(ValueError):
        dn.zeile_aus_position("VNP46A3.A2022182.h00v01.002.h5")


# --- Sonnenstand --------------------------------------------------------------


@pytest.mark.parametrize(
    "zeitpunkt, astropy_grad",
    [
        ("2013-01-01T00:00:00", -23.0025),
        ("2016-06-20T22:34:00", 23.4346),  # Sonnenwende
        ("2019-09-23T07:50:00", 0.0),  # Tagundnachtgleiche
        ("2022-07-31T12:00:00", 18.1945),
        ("2022-12-21T21:48:00", -23.4381),  # Sonnenwende
        ("2025-03-20T09:01:00", -0.0003),  # Tagundnachtgleiche
    ],
)
def test_deklination_stimmt_mit_astropy_ueberein(zeitpunkt, astropy_grad):
    """Gemessen über 2013-2025 alle 6 Stunden: höchstens 0,0055° Abweichung (LOG.md)."""
    wert = float(dn.sonnendeklination_grad(np.array([np.datetime64(zeitpunkt)]))[0])
    assert wert == pytest.approx(astropy_grad, abs=0.01)


def test_sicherheitsabstand_deutlich_groesser_als_formelfehler():
    assert dn.SICHERHEITSABSTAND_GRAD >= 10 * 0.0055


def test_monatsfenster_umfasst_beide_enden_plus_puffer():
    """Katalogfenster 1. 00:00 bis 1. des Folgemonats 00:00 UTC, dazu je ein Tag Puffer."""
    assert dn.ZEITFENSTER_PUFFER_TAGE == 1
    t = dn._monats_zeitpunkte(2022, 7)
    assert t[0] == np.datetime64("2022-06-30T00:00:00")
    assert t[-1] == np.datetime64("2022-08-02T00:00:00")
    assert len(t) == 33 * 24 + 1


# --- Der Fall 2022-07 -----------------------------------------------------------


@pytest.mark.parametrize("position", FEHLEND_2022_07)
def test_2022_07_alle_36_fehlenden_kacheln_erklaerbar(position):
    befund = dn.fehlen_erklaerbar(position, 2022, 7)
    assert befund.fehlen_erlaubt
    assert (befund.breite_sued, befund.breite_nord) == (70, 80)
    # Am Südrand, am Ende des Fensters (kleinste Deklination), Sonne gut 2° unter dem Horizont.
    assert befund.breite_am_dunkelsten == 70
    assert befund.zeitpunkt_am_dunkelsten == datetime(2022, 8, 2, tzinfo=timezone.utc)
    assert befund.groesster_zenitwinkel_grad == pytest.approx(92.18, abs=0.02)
    assert befund.abstand_zur_grenze_grad > 9


def test_2022_07_nachbarreihe_v02_nicht_erlaubt():
    """Ohne Puffer verfehlte v02 die Grenze um 0,07°; mit einem Tag Puffer wird sie erreicht."""
    befund = dn.zeilen_befund(2, 2022, 7)
    assert befund.abstand_zur_grenze_grad < 0
    assert not befund.fehlen_erlaubt


def test_knapper_fall_wird_im_zweifel_nicht_erlaubt():
    """v01 im August 2014: Grenze knapp verfehlt, aber um weniger als den Sicherheitsabstand."""
    befund = dn.zeilen_befund(1, 2014, 8)
    assert 0 < befund.abstand_zur_grenze_grad < dn.SICHERHEITSABSTAND_GRAD
    assert not befund.fehlen_erlaubt
    assert "im Zweifel Fehlen nicht erlaubt" in befund.begruendung


def test_begruendung_nennt_sonnentiefe_grenze_und_ergebnis():
    text = dn.fehlen_erklaerbar("h19v01", 2022, 7).begruendung
    assert "2,2° unter dem Horizont" in text
    assert "Sonnenzenit ≥ 102°" in text
    assert "keine Nacht im Sinne dieser Grenze" in text
    text = dn.zeilen_befund(3, 2022, 7).begruendung
    assert "es gibt Nächte" in text


# --- Plausibilität: beide Halbkugeln, Jahreszeiten ----------------------------


def test_juli_nur_hoher_norden():
    assert dn.erlaubte_zeilen(2022, 7) == [0, 1]


def test_dezember_nur_hoher_sueden():
    assert dn.erlaubte_zeilen(2022, 12) == [15, 16, 17]


def test_maerz_nichts():
    assert dn.erlaubte_zeilen(2022, 3) == []


def test_suedhalbkugel_am_nordrand_bei_groesster_deklination():
    befund = dn.zeilen_befund(15, 2022, 12)
    assert befund.breite_am_dunkelsten == -60
    assert befund.fehlen_erlaubt


def test_aequatorkachel_sonne_im_nadir_zur_tagundnachtgleiche():
    """Im März geht die Deklination durch 0°: am Äquator steht die Sonne um Mitternacht im Nadir."""
    befund = dn.zeilen_befund(8, 2022, 3)
    assert befund.groesster_zenitwinkel_grad == 180
    # Erster Zeitpunkt, an dem die Gegenbreite −δ in der Kachel liegt: 1. März, δ ≈ −7,7°.
    zeit = np.array([np.datetime64(befund.zeitpunkt_am_dunkelsten.replace(tzinfo=None))])
    assert 0 <= befund.breite_am_dunkelsten <= 10
    assert befund.breite_am_dunkelsten == pytest.approx(-dn.sonnendeklination_grad(zeit)[0])
    assert not befund.fehlen_erlaubt


def test_aequatorkachel_im_juli_nacht_aber_kein_nadir():
    """Kleinste Deklination im Fenster (2. August 00:00 UTC) ≈ 17,82°: Zenitwinkel 180° − 17,82°."""
    befund = dn.zeilen_befund(8, 2022, 7)
    assert befund.groesster_zenitwinkel_grad == pytest.approx(162.18, abs=0.02)
    assert not befund.fehlen_erlaubt


def test_zwischen_50_nord_und_50_sued_nie_erlaubt():
    """Schutz vor stillen Lücken: In den Reihen v03-v14 darf in keinem Monat 2013-2025 etwas fehlen."""
    for jahr in range(2013, 2026):
        for monat in range(1, 13):
            erlaubt = dn.erlaubte_zeilen(jahr, monat)
            assert set(erlaubt) <= {0, 1, 2, 15, 16, 17}, (jahr, monat, erlaubt)


# Alle Fälle 2013-2025, in denen Fehlen erlaubt ist: (Monat, Reihe v). Gilt in
# jedem Jahr gleich (Auflage statistik-pruefer 2026-09-25: Tabelle festschreiben).
ERLAUBT_2013_2025 = {
    (4, 0), (5, 0), (6, 0), (7, 0), (8, 0),
    (5, 1), (6, 1), (7, 1),
    (6, 2),
    (12, 15),
    (1, 16), (11, 16), (12, 16),
    (1, 17), (2, 17), (10, 17), (11, 17), (12, 17),
}


def _alle_befunde():
    return [dn.zeilen_befund(v, j, m) for j in range(2013, 2026) for m in range(1, 13) for v in range(18)]


def test_tabelle_aller_erlaubten_faelle_2013_2025():
    befunde = _alle_befunde()
    for jahr in range(2013, 2026):
        erlaubt = {(b.monat, b.v) for b in befunde if b.jahr == jahr and b.fehlen_erlaubt}
        assert erlaubt == ERLAUBT_2013_2025, jahr


def test_jeder_erlaubte_fall_hat_mindestens_3_grad_abstand():
    abstaende = [b.abstand_zur_grenze_grad for b in _alle_befunde() if b.fehlen_erlaubt]
    assert min(abstaende) > 3.0


def test_ergebnis_haengt_nicht_am_genauen_sicherheitsabstand(monkeypatch):
    """Jeder Abstand zwischen 0,5° und 3,5° ergibt dieselben erlaubten Fälle."""
    for abstand in (0.5, 1.0, 2.0, 3.5):
        monkeypatch.setattr(dn, "SICHERHEITSABSTAND_GRAD", abstand)
        erlaubt = {(b.jahr, b.monat, b.v) for b in _alle_befunde() if b.fehlen_erlaubt}
        assert {(m, v) for _, m, v in erlaubt} == ERLAUBT_2013_2025
        assert len(erlaubt) == 13 * len(ERLAUBT_2013_2025)


def test_ungueltiger_monat():
    with pytest.raises(ValueError):
        dn.zeilen_befund(1, 2022, 13)
