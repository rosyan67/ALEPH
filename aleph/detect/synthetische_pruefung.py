"""Prüfung des statistischen Grundgerüsts am künstlichen Würfel (Entwicklungswerkzeug, nicht Teil der Pipeline).

Aufruf: .venv/bin/python -m aleph.detect.synthetische_pruefung [--wiederholungen 20] [--json pfad]

Szenarien (alle mit aleph/detect/synthetisch.py, 150 Monate, feste Startwerte, also wiederholbar):
1. Kein Trend, unabhängiges Rauschen: Anteil „signifikanter“ Zellen nach BH (αFDR = 0,10) und Anteil der
   Würfel mit mindestens einer Meldung (5 × so viele Wiederholungen wie sonst). Erwartung bei unabhängigen Zellen: höchstens etwa αFDR der Würfel
   mit einer Meldung (Wilks 2016, Abb. 4 des Manuskripts: bei fast unabhängigen Zellen liegt das globale
   Niveau nahe αFDR).
2. Kein Trend, Autokorrelation AR(1) 0,5 und 0,8: ohne Korrektur zu viele Meldungen, mit Korrektur weniger.
3. Eingepflanzte Trends bekannter Stärke (1, 3, 5 % je Jahr) in Blöcken: gefunden / falsch gemeldet.
4. Eingepflanzte Ausreißer bekannter Stärke (Anomalieerkennung): gefunden / falsch gemeldet; dazu ein
   Ausreißer in der BASISLINIE, um die Uneinigkeit klassisch/robust zu zeigen.
5. Rechenzeit: gemessen an einem Teilgitter, linear hochgerechnet auf 1440 × 720 Zellen und 150 Monate.
Zellen liegen in den Tropen (Breite 10° bis 0°), damit der Schnee-Verdacht die Statistik nicht verändert;
die Schnee-Regel hat eigene Tests.
"""

import argparse
import json
import time
import warnings

import numpy as np

from aleph.detect import anomalie, trend
from aleph.detect.statistik import alpha_fdr
from aleph.detect.synthetisch import Ereignis, kuenstlicher_wuerfel

MONATE = 150
JAHRE = (2010, 2022)  # 156 Monate, davon die ersten 150; alles vor 2023


def _reihe(ds):
    monate = [(int(str(z)[:4]), int(str(z)[5:7])) for z in ds["zeit"].values][:MONATE]
    w = ds["allangle_mittel_beobachtet"].values[:MONATE].astype("float32")
    g = ds["allangle_gueltige_pixel"].values[:MONATE].astype("float64")
    a = ds["allangle_aufgefuellt_pixel"].values[:MONATE].astype("float64")
    return w, (g - a) / 3600.0, monate


def _trend_lauf(seed, ny, nx, ar1=0.0, bloecke=()):
    ds = kuenstlicher_wuerfel(ny=ny, nx=nx, jahre=JAHRE, seed=seed, ar1=ar1, anteil_dunkel=0.0, breite_start=10.0)
    w, beob, monate = _reihe(ds)
    wahr = np.zeros((ny, nx), dtype=bool)
    for (z0, z1, s0, s1, prozent) in bloecke:
        faktor = (1 + prozent / 100.0) ** (np.arange(MONATE) / 12.0)
        w[:, z0:z1, s0:s1] *= faktor[:, None, None].astype("float32")
        wahr[z0:z1, s0:s1] = True
    ergebnis = trend.trend_je_zelle(w, monate, ds["breite"].values, ds["laenge"].values, beob)
    return ergebnis, wahr


def szenario_ohne_trend(wiederholungen=20, ny=40, nx=50, ar1=0.0):
    felder = ("signifikant_unkorrigiert", "signifikant_hamed_rao", "signifikant_yue", "trend_beide", "trend_gemeldet")
    anteil = {f: [] for f in felder}
    mit_meldung = {f: 0 for f in felder}
    moran = []
    for r in range(wiederholungen):
        erg, _ = _trend_lauf(1000 + r, ny, nx, ar1)
        for f in felder:
            n = int(erg.zellen[f].values.sum())
            anteil[f].append(erg.zusammenfassung[f + "_flaechenanteil"])
            mit_meldung[f] += n > 0
        moran.append(erg.zusammenfassung["moran"]["reste_i_median"])
    return {
        "ar1": ar1, "wiederholungen": wiederholungen, "zellen_je_wuerfel": ny * nx,
        "flaechenanteil_mittel": {f: float(np.mean(anteil[f])) for f in felder},
        "anteil_wuerfel_mit_meldung": {f: mit_meldung[f] / wiederholungen for f in felder},
        "moran_reste_median": float(np.median(moran)),
    }


def szenario_trends(ar1=0.0, seed=77, ny=40, nx=60):
    # Drei Blöcke je 10 × 10 Zellen mit 1, 3 und 5 % je Jahr, einer mit -3 % je Jahr; Rest ohne Trend.
    bloecke = [(5, 15, 5, 15, 1.0), (5, 15, 25, 35, 3.0), (5, 15, 45, 55, 5.0), (25, 35, 25, 35, -3.0)]
    erg, wahr = _trend_lauf(seed, ny, nx, ar1, bloecke)
    zeilen = []
    for (z0, z1, s0, s1, prozent) in bloecke:
        teil = (slice(z0, z1), slice(s0, s1))
        eintrag = {"staerke_prozent_je_jahr": prozent}
        for f in ("signifikant_unkorrigiert", "signifikant_hamed_rao", "signifikant_yue", "trend_beide", "trend_gemeldet"):
            eintrag[f] = float(erg.zellen[f].values[teil].mean())
        eintrag["sen_relativ_median"] = float(np.nanmedian(erg.zellen["sen_relativ_prozent"].values[teil]))
        zeilen.append(eintrag)
    falsch = {f: int((erg.zellen[f].values & ~wahr).sum()) for f in
              ("signifikant_unkorrigiert", "signifikant_hamed_rao", "signifikant_yue", "trend_beide", "trend_gemeldet")}
    gemeldet = {f: int(erg.zellen[f].values.sum()) for f in falsch}
    anteil_falsch = {f: (falsch[f] / gemeldet[f] if gemeldet[f] else 0.0) for f in falsch}
    return {"ar1": ar1, "bloecke": zeilen, "falsch_gemeldet_ausserhalb": falsch, "gemeldet_gesamt": gemeldet,
            "anteil_falsch_unter_meldungen": anteil_falsch, "zellen_ohne_trend": int((~wahr).sum())}


def szenario_ausreisser(seed=5, ny=40, nx=60):
    ziel = (2021, 6)
    ereignisse = (
        Ereignis(monat=ziel, zeilen=(5, 8), spalten=(5, 8), faktor=1.5),
        Ereignis(monat=ziel, zeilen=(5, 8), spalten=(20, 23), faktor=2.0),
        Ereignis(monat=ziel, zeilen=(5, 8), spalten=(35, 38), faktor=3.0),
        Ereignis(monat=ziel, zeilen=(20, 23), spalten=(20, 23), faktor=0.3),
        Ereignis(monat=(2017, 6), zeilen=(30, 33), spalten=(45, 48), faktor=6.0),  # Ausreißer in der Basislinie ...
        Ereignis(monat=ziel, zeilen=(30, 33), spalten=(45, 48), faktor=2.0),  # ... und im selben Block ein echter Anstieg
    )
    ds = kuenstlicher_wuerfel(ny=ny, nx=nx, jahre=JAHRE, seed=seed, anteil_dunkel=0.0, breite_start=10.0, ereignisse=ereignisse)
    erk = anomalie.erkenne_monat(ds, ziel, "allangle")
    z = erk.zellen
    zeilen = []
    for e in ereignisse[:4]:
        teil = (slice(*e.zeilen), slice(*e.spalten))
        zeilen.append({
            "faktor": e.faktor, "zellen": int(np.prod([e.zeilen[1] - e.zeilen[0], e.spalten[1] - e.spalten[0]])),
            "gemeldet": int(z["gemeldet"].values[teil].sum()),
            "z_robust_median": float(np.nanmedian(z["z"].values[teil])),
            "z_klassisch_median": float(np.nanmedian(z["z_klassisch"].values[teil])),
        })
    wahr = np.zeros((ny, nx), dtype=bool)
    for e in ereignisse:
        if e.monat == ziel:
            wahr[slice(*e.zeilen), slice(*e.spalten)] = True
    basis_teil = (slice(30, 33), slice(45, 48))
    return {
        "bloecke": zeilen,
        "falsch_gemeldet_zellen": int((z["gemeldet"].values & ~wahr).sum()),
        "ereignisse_gesamt": int(len(erk.ereignisse)),
        "basislinie_ausreisser": {
            "z_robust_median": float(np.nanmedian(z["z"].values[basis_teil])),
            "z_klassisch_median": float(np.nanmedian(z["z_klassisch"].values[basis_teil])),
            "gemeldet": int(z["gemeldet"].values[basis_teil].sum()),
            "z_uneinig_zellen_block": int(z["z_uneinig"].values[basis_teil].sum()),
            "z_uneinig_zellen_gesamt": int(z["z_uneinig"].values.sum()),
        },
    }


def rechenzeit(ny=100, nx=200):
    ds = kuenstlicher_wuerfel(ny=ny, nx=nx, jahre=JAHRE, seed=9, anteil_dunkel=0.3, breite_start=10.0)
    w, beob, monate = _reihe(ds)
    t0 = time.perf_counter()
    trend.trend_je_zelle(w, monate, ds["breite"].values, ds["laenge"].values, beob)
    t_trend = time.perf_counter() - t0
    t0 = time.perf_counter()
    anomalie.erkenne_monat(ds, (2021, 6), "allangle")
    t_anom = time.perf_counter() - t0
    faktor = (1440 * 720) / (ny * nx)
    return {"zellen_gemessen": ny * nx, "monate": MONATE, "trend_sekunden": t_trend, "anomalie_monat_sekunden": t_anom,
            "hochrechnung_faktor": faktor, "trend_volles_raster_minuten": t_trend * faktor / 60.0,
            "anomalie_volles_raster_je_monat_sekunden": t_anom * faktor}


def alles(wiederholungen=20) -> dict:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return {
            "alpha_fdr": alpha_fdr(),
            "ohne_trend_unabhaengig": szenario_ohne_trend(5 * wiederholungen, ar1=0.0),
            "ohne_trend_ar05": szenario_ohne_trend(wiederholungen, ar1=0.5),
            "ohne_trend_ar08": szenario_ohne_trend(wiederholungen, ar1=0.8),
            "trends_unabhaengig": szenario_trends(ar1=0.0),
            "trends_ar05": szenario_trends(ar1=0.5),
            "ausreisser": szenario_ausreisser(),
            "rechenzeit": rechenzeit(),
        }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--wiederholungen", type=int, default=20)
    p.add_argument("--json")
    a = p.parse_args()
    ergebnis = alles(a.wiederholungen)
    text = json.dumps(ergebnis, indent=1, ensure_ascii=False)
    print(text)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
