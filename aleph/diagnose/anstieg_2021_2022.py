"""Untersuchung: Woher kommt der Anstieg des Nachtlichts 2021 (+10 %) und 2022 (+16 %)?

Auftrag 2026-10-05. Bericht: berichte/2026-10-05_anstieg-2021-2022.md. NUR LESEN: Der Würfel wird über
`aleph.layers.vnp46a3.lies_monate_mit_region` gelesen (dieselbe Ladelogik wie alle Auswertungen), nichts
wird am Würfel, am Download, an Kachellisten oder an `vnp46a3*.py` geändert. Zwischenergebnisse liegen auf der
SSD unter `auswertungen/anstieg_2021_2022/`.

Zeitraum: nur 2013-01 bis 2022-12. Monate ab 2023 werden verweigert (CLAUDE.md, Validierungs-/Endtestzeitraum),
auch nicht zum Vergleich.

ALLE REGELN UNTEN SIND VOR DER ERSTEN RECHNUNG FESTGELEGT (Commit vor dem ersten Lauf) und werden danach nicht
geändert. Was nachträglich dazukommt, steht im Bericht ausdrücklich als „nachträglich“.

Gemeinsame Grundlage (Teil 1, 3, 4)
- Fläche: nur die Region Afrika-Europa-Asien (188 Kacheln). Nur dort sind alle Monate 2013–2022 geladen
  (2013–2017 und 2021–2022 Zustand 4, 2018–2020 Zustand 1). „Gleiche Abdeckung“ heißt hier: immer dieselbe Fläche.
- Feld: `allangle_mittel_beobachtet` (wie Länderreihen und Earth-Engine-Vergleich); `near_nadir_*` nur als
  Gegenprobe (Blickwinkel).
- Monate: 2013-01 … 2022-12 ohne 2022-07 (nicht geladen, Suomi NPP Safe Mode 26.07.–20.08.2022). 2022-08 ist ein
  Teilmonat; im Bruchpunkt-Test wird er weggelassen (`TEILMONATE`), in Grafiken markiert.
- Gültiger Zellmonat: Wert endlich, Anteil beobachteter Pixel ≥ 0,5 (aufgefüllte zählen nie, wie
  `aleph/detect/anomalie.py`), kein Schnee-Verdacht (`aleph/detect/schnee.py`, unveränderte Regel).
- Basislinie je Zelle und Kalendermonat: Median der gültigen Werte 2013–2019 desselben Kalendermonats, nur bei
  mindestens `MIN_BASISJAHRE` = 4 von 7 Jahren. 2013–2019 ist der Kalibrierungszeitraum (ARCHITECTURE 9a).
- Helligkeit einer Zelle (fest über 2013–2019): Median aller gültigen Monatswerte 2013–2019, nur bei mindestens
  `MIN_MONATE_NIVEAU` = 42 von 84 gültigen Monaten. Klassen dunkel < 0,5, mittel 0,5 bis < 5, hell ≥ 5
  nW·cm⁻²·sr⁻¹ (gleiche Grenzen wie im Earth-Engine-Vergleich; 0,5 = Rauschschwelle von VNP46A3).
- Maß einer Gruppe in einem Monat: I = Σ a·x / Σ a·B über alle Zellen der Gruppe, die in diesem Monat gültig sind
  und B ≥ 0,5 haben (a = Zellfläche, x = Monatswert, B = Basislinie desselben Kalendermonats). I = 1 heißt „wie
  im Mittel 2013–2019“. Damit ist die Jahreszeit herausgerechnet, und jede Zelle wird nur mit sich selbst verglichen.
  Zusätzlich der Median von x/B (ungewichtet, robust). Dunkle Zellen (B < 0,5) gehen hier nicht ein; sie haben
  ein eigenes Maß in Teil 3.
- Jahreswert: gepoolt, Σ über die Monate des Jahres von Σ a·x geteilt durch Σ a·B.
- Unsicherheit: räumlicher Block-Bootstrap über 10°-Kacheln (wie im Earth-Engine-Vergleich), `BOOTSTRAP_N`
  Wiederholungen, 95-%-Intervall (2,5- und 97,5-%-Quantil). Er erfasst die räumliche Streuung, nicht
  systematische Fehler.

Teil 1 – Gruppen
- Breitenbänder (Zellmitte): südlich 20° S, 20° S–0°, 0–20° N, 20–40° N, 40–55° N, nördlich 55° N.
- Kontinente: UN-M49-Region mit dem größten Landanteil der Zelle (Zell-Einheiten-Zuordnung), nur Zellen mit
  mindestens 50 % Landanteil dieser Region.
- Helligkeitsklassen mittel und hell (siehe oben).
- Bruchpunkt (Das Statistik-Gerüst enthält KEINEN Bruchpunkt-Test; `trend.py` sagt ausdrücklich, dass ein Bruch
  als Trend erscheint. Deshalb hier ein einfaches, benanntes Verfahren): Reihe y_t = ln I_t (Gesamtgruppe),
  Monate ohne 2022-07 und 2022-08. Modelle, je per kleinsten Quadraten:
    M0 Gerade (a + b·t);
    M_stufe(k) Gerade plus eine Stufe ab Monat k (k gesucht, mindestens 12 Monate auf jeder Seite);
    M_knick(k) Gerade, deren Steigung ab k wechselt (schleichend, stetig), k gesucht;
    M_jan Gerade plus je eine Stufe im Januar 2021 und im Januar 2022 (fest, ohne Suche) – Hypothese
          „Kalibrierung wechselt mit dem Kalenderjahr“;
    M_l1b Gerade plus d·f_t, f_t = Anteil der L1B-Dateien (VNP02DNB) des Monats mit der PGE-Version
          `L1B_NEUE_VERSION` (aus dem NASA-Katalog, Teil 2) – Hypothese „Wechsel der Kalibrier-Software“.
  Vergleich mit BIC (gesuchtes k zählt als zusätzlicher Parameter). Unsicherheit der Lage von k: Bootstrap mit
  Blöcken von 12 Monaten aus den Resten des besten Stufenmodells, `BRUCH_BOOTSTRAP_N` Wiederholungen,
  90-%-Bereich. Grenzen: BIC und Bootstrap setzen voraus, dass die Reste nach Abzug der Jahreszeit nur mäßig
  abhängig sind; p-Werte werden nicht angegeben.
- Gleiche Kalendermonate: je Kalendermonat ein fester Zellkreis (gültig und B ≥ 0,5 in allen Jahren mit Daten
  dieses Kalendermonats), I je Jahr.
- Pandemie: I je Monat 2020 und 2021 gegen 2019, getrennt ausgewiesen.

Teil 3 – Orte, die sich nicht ändern sollten (Regeln vor dem Rechnen)
- R1 Dunkle Referenz: Zelle in der Region, Landanteil ≥ 0,99, Breite 15–35° N oder 15–35° S (Wüstengürtel,
  kaum Schnee, wenig Wolken), mindestens 60 gültige Monate 2013–2019, und JEDER gültige Monatswert 2013–2019
  < 0,1. Maß je Jahr: flächengewichtetes Mittel der gültigen Werte und Anteil der Zellmonate mit Wert > 0.
  Vorab bekannte Grenze: VNP46A3 setzt Pixelwerte unter 0,5 auf 0. Ein Versatz unter etwa 0,5 nW je Pixel ist
  hier deshalb kaum sichtbar; ein unveränderter Grundwert schließt einen kleinen Versatz NICHT aus.
- R2 Helle, stabile Orte: Klasse hell, |Breite| < 50°, mindestens 70 gültige Monate 2013–2019, in jedem Jahr
  2013–2019 mindestens 6 gültige Monate, und jedes Jahresmittel von x/B 2013–2019 liegt innerhalb ±5 % von 1
  (max |ln| ≤ ln 1,05). Ergibt das weniger als 30 Zellen, gelten stattdessen die 10 % der Zellen, die alle
  übrigen Bedingungen erfüllen, mit der kleinsten größten Jahresabweichung (Ersatzregel, vorab festgelegt).
- Erwartungen (vorab): Verstärkungsfaktor → stabile helle Zellen steigen im selben Verhältnis wie alle
  beleuchteten Zellen (Bootstrap-Intervalle überlappen); echtes Wachstum → stabile helle Zellen steigen deutlich
  weniger (weniger als die Hälfte des Anstiegs aller beleuchteten Zellen); Versatz → Grundwert der dunklen
  Referenz steigt und die Klasse mittel steigt verhältnismäßig deutlich stärker als hell.

Teil 4 – Gegenprobe Kandidat B (EOG VCMCFG über Earth Engine)
- Zellen: Region, südlich 60° N, Landanteil ≥ 0,5 (Boote), Klasse mittel oder hell (Feuer liegen vor allem in
  dunklen Zellen), B-Anteil Pixel mit Daten ≥ 0,5, Würfel gültig. Je Kalendermonat ein fester Zellkreis, der in
  allen Jahren 2019–2022 (Juli: 2019–2021) in BEIDEN Quellen gültig ist. Verhältnis je Quelle: Σ a·x_Jahr /
  Σ a·x_2019, gepoolt über die Kalendermonate, Bootstrap über Kacheln.
- Urteil (vorab): „B zeigt denselben Anstieg“, wenn B 2021/2019 und 2022/2019 jeweils mindestens 2/3 des
  Anstiegs des Würfels zeigt; „B zeigt keinen nennenswerten Anstieg“, wenn jeweils weniger als 1/3; sonst
  „teilweise“. Nur bewertet, wenn der Würfel in diesem Zellkreis selbst um mindestens 5 % steigt.
- Grenzen von B (Katalog): keine Mond-/BRDF-Korrektur, keine Trennung nach Schnee, Boote und Feuer nicht
  herausgefiltert, nördlich ~65° N im Herbst keine Daten. Eigene Kalibrierkette (nicht die NASA-L1B) ist zu
  belegen, nicht vorausgesetzt.

Aufruf:  .venv/bin/python -m aleph.diagnose.anstieg_2021_2022 [lesen|rechnen|grafiken]
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

VERSION = "0.1.0"
GESPERRT_AB = (2023, 1)
REGION = "afrika_europa_asien"
FELDER = ("allangle", "near_nadir")
HAUPTFELD = "allangle"
PIXEL_JE_ZELLE = 3600
ZELLEN_JE_KACHEL = 40

MONATE = [(j, m) for j in range(2013, 2023) for m in range(1, 13) if (j, m) != (2022, 7)]
TEILMONATE = [(2022, 8)]  # Safe Mode bis 20.08.2022; im Bruchpunkt-Test weggelassen
BASISJAHRE = tuple(range(2013, 2020))

MIN_BEOBACHTET = 0.5
MIN_BASISJAHRE = 4
MIN_MONATE_NIVEAU = 42
DUNKEL_BIS = 0.5
MITTEL_BIS = 5.0
MIN_BASIS_WERT = 0.5
BREITENBAENDER = (("südlich 20° S", -90.0, -20.0), ("20° S–0°", -20.0, 0.0), ("0–20° N", 0.0, 20.0),
                  ("20–40° N", 20.0, 40.0), ("40–55° N", 40.0, 55.0), ("nördlich 55° N", 55.0, 90.0))
MIN_LANDANTEIL_KONTINENT = 0.5
BOOTSTRAP_N = 500
BRUCH_BOOTSTRAP_N = 500
BRUCH_RAND_MONATE = 12
BRUCH_BLOCK_MONATE = 12
SEED = 20261005

# Teil 2 / Modell M_l1b: wird aus dem Tagesscan des NASA-Katalogs gesetzt (Datei unten), nicht aus Würfelwerten.
L1B_NEUE_VERSION = "3.0.30"

# Teil 3
R1_LANDANTEIL = 0.99
R1_BREITE = (15.0, 35.0)
R1_MIN_MONATE = 60
R1_MAX_WERT = 0.1
R2_MAX_BREITE = 50.0
R2_MIN_MONATE = 70
R2_MIN_MONATE_JE_JAHR = 6
R2_MAX_JAHRESABWEICHUNG = np.log(1.05)
R2_MIN_ZELLEN = 30
R2_ERSATZ_ANTEIL = 0.10

# Teil 4
B_MAX_BREITE = 60.0
B_LANDANTEIL = 0.5
B_MIN_ANTEIL = 0.5
B_JAHRE = (2019, 2020, 2021, 2022)
B_GLEICH_AB = 2 / 3
B_KEIN_UNTER = 1 / 3
B_MIN_ANSTIEG_WUERFEL = 0.05

AUSGABE_ORDNER = ("auswertungen", "anstieg_2021_2022")


class ZeitraumGesperrt(ValueError):
    """Monate ab 2023 sind Validierungs-/Endtestzeitraum (CLAUDE.md)."""


def pruefe_monat(monat: tuple[int, int]) -> None:
    if tuple(monat) >= GESPERRT_AB:
        raise ZeitraumGesperrt(f"{monat[0]:04d}-{monat[1]:02d} liegt im gesperrten Zeitraum 2023–2025.")


def ausgabe_ordner() -> Path:
    from aleph.core import io

    p = io.aleph_data_dir().joinpath(*AUSGABE_ORDNER)
    p.mkdir(parents=True, exist_ok=True)
    return p


# --- Lesen -------------------------------------------------------------------------------------------------


def region_zellen() -> tuple[np.ndarray, np.ndarray]:
    """Zeilen und Spalten aller Zellen der Region (aus der Kachelliste, wie die Lesefunktion)."""
    from aleph.layers import vnp46a3_regionen

    maske = vnp46a3_regionen.zellmaske(vnp46a3_regionen.lies_region(REGION), 720, 1440)
    return np.nonzero(maske)


def lies_stapel(monate=MONATE) -> dict:
    """Liest alle Monate (nur Region) über die gemeinsame Lesefunktion. Rückgabe: Felder (Monat × Zelle)."""
    from aleph.layers import vnp46a3

    zeilen, spalten = region_zellen()
    variablen = []
    for f in FELDER:
        variablen += [f"{f}_mittel_beobachtet", f"{f}_gueltige_pixel", f"{f}_aufgefuellt_pixel"]
    variablen.append("allangle_num")
    aus = {v: np.full((len(monate), len(zeilen)), np.nan, dtype="float32") for v in variablen}
    zustand = []
    for i, monat in enumerate(monate):
        pruefe_monat(monat)
        zustand.append(vnp46a3.monatsstatus(*monat))
        ds = vnp46a3.lies_monate_mit_region([monat], variablen, REGION)
        ng = ds["nicht_geladen"].values[0][zeilen, spalten]
        if ng.any():
            raise RuntimeError(f"{monat}: {int(ng.sum())} Zellen der Region nicht geladen – Abbruch.")
        for v in variablen:
            aus[v][i] = ds[v].values[0][zeilen, spalten]
        ds.close()
        print(f"  gelesen {monat[0]}-{monat[1]:02d} (Zustand {zustand[-1]})", flush=True)
    breite, laenge = vnp46a3._gitter_koordinaten()
    aus.update({"zeilen": zeilen, "spalten": spalten, "breite": breite[zeilen], "laenge": laenge[spalten],
                "monate": np.array(monate), "zustand": np.array(zustand)})
    return aus


def stapel_pfad() -> Path:
    return ausgabe_ordner() / "stapel.npz"


def lade_stapel() -> dict:
    with np.load(stapel_pfad()) as d:
        s = {k: d[k] for k in d.files}
    if any(tuple(m) >= GESPERRT_AB for m in s["monate"]):
        raise ZeitraumGesperrt("Stapel enthält Monate ab 2023.")
    return s


# --- Bausteine (rein rechnerisch, mit künstlichen Daten getestet) -------------------------------------------


def beobachtet_anteil(gueltig: np.ndarray, aufgefuellt: np.ndarray) -> np.ndarray:
    from aleph.detect.anomalie import _beobachtet_anteil

    return _beobachtet_anteil(np.nan_to_num(gueltig), np.nan_to_num(aufgefuellt), PIXEL_JE_ZELLE)


def gueltig_maske(x: np.ndarray, anteil: np.ndarray, breite: np.ndarray, monate) -> np.ndarray:
    """Monat × Zelle: Wert endlich, ≥ 50 % beobachtet, kein Schnee-Verdacht."""
    g = np.isfinite(x) & (anteil >= MIN_BEOBACHTET)
    for i, (_, m) in enumerate(monate):
        g[i] &= ~_schnee_1d(breite, m, anteil[i])
    return g


def _schnee_1d(breite: np.ndarray, monat: int, anteil: np.ndarray) -> np.ndarray:
    """Schnee-Verdacht für eine Zellliste: unveränderte Regel `schnee_verdacht`, je Zelle als eigene Zeile."""
    from aleph.detect.schnee import schnee_verdacht

    return schnee_verdacht(breite, monat, anteil[:, None])[:, 0]


def basislinie(x: np.ndarray, g: np.ndarray, monate) -> np.ndarray:
    """12 × Zelle: Median je Kalendermonat über die Basisjahre, NaN bei weniger als MIN_BASISJAHRE."""
    monate = [tuple(m) for m in monate]
    b = np.full((12, x.shape[1]), np.nan)
    for m in range(1, 13):
        idx = [i for i, (j, mm) in enumerate(monate) if mm == m and j in BASISJAHRE]
        w = np.where(g[idx], x[idx], np.nan)
        n = np.isfinite(w).sum(axis=0)
        with np.errstate(all="ignore"):
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                med = np.nanmedian(w, axis=0)
        b[m - 1] = np.where(n >= MIN_BASISJAHRE, med, np.nan)
    return b


def niveau(x: np.ndarray, g: np.ndarray, monate) -> np.ndarray:
    """Helligkeit je Zelle: Median der gültigen Werte 2013–2019, NaN bei weniger als MIN_MONATE_NIVEAU."""
    import warnings

    idx = [i for i, (j, _) in enumerate(monate) if j in BASISJAHRE]
    w = np.where(g[idx], x[idx], np.nan)
    n = np.isfinite(w).sum(axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(w, axis=0)
    return np.where(n >= MIN_MONATE_NIVEAU, med, np.nan)


def klassen(niv: np.ndarray) -> np.ndarray:
    k = np.full(niv.shape, "", dtype=object)
    k[niv < DUNKEL_BIS] = "dunkel"
    k[(niv >= DUNKEL_BIS) & (niv < MITTEL_BIS)] = "mittel"
    k[niv >= MITTEL_BIS] = "hell"
    return k


def basis_je_monat(b: np.ndarray, monate) -> np.ndarray:
    """Monat × Zelle: die Basislinie des jeweiligen Kalendermonats."""
    return b[[m - 1 for _, m in monate]]


def summen(x, g, bm, a, maske):
    """Je Monat Σ a·x und Σ a·B über gültige Zellen der Gruppe mit B ≥ MIN_BASIS_WERT; dazu Zellzahl."""
    ok = g & maske[None, :] & (bm >= MIN_BASIS_WERT) & np.isfinite(bm)
    sx = np.where(ok, a[None, :] * x, 0.0).sum(axis=1)
    sb = np.where(ok, a[None, :] * bm, 0.0).sum(axis=1)
    return sx, sb, ok.sum(axis=1)


def monatsindex(x, g, bm, a, maske) -> dict:
    sx, sb, n = summen(x, g, bm, a, maske)
    import warnings

    ok = g & maske[None, :] & (bm >= MIN_BASIS_WERT) & np.isfinite(bm)
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(np.where(ok, x / bm, np.nan), axis=1)
        idx = np.where(sb > 0, sx / sb, np.nan)
    return {"index": idx, "median_verhaeltnis": med, "zellen": n}


def kachel_von(zeilen, spalten) -> np.ndarray:
    return (zeilen // ZELLEN_JE_KACHEL) * 100 + spalten // ZELLEN_JE_KACHEL


def jahresindex_bootstrap(x, g, bm, a, maske, monate, kacheln, jahre, n_boot=BOOTSTRAP_N, seed=SEED) -> dict:
    """Gepoolter Jahreswert je Jahr mit 95-%-Intervall aus räumlichem Block-Bootstrap über Kacheln."""
    monate = [tuple(m) for m in monate]
    ok = g & maske[None, :] & (bm >= MIN_BASIS_WERT) & np.isfinite(bm)
    ax = np.where(ok, a[None, :] * x, 0.0)
    ab = np.where(ok, a[None, :] * bm, 0.0)
    ids, inv = np.unique(kacheln, return_inverse=True)
    sx = np.zeros((len(jahre), len(ids)))
    sb = np.zeros_like(sx)
    for k, j in enumerate(jahre):
        rows = [i for i, (jj, _) in enumerate(monate) if jj == j]
        sx[k] = np.bincount(inv, weights=ax[rows].sum(axis=0), minlength=len(ids))
        sb[k] = np.bincount(inv, weights=ab[rows].sum(axis=0), minlength=len(ids))
    rng = np.random.default_rng(seed)
    gew = rng.multinomial(len(ids), np.full(len(ids), 1 / len(ids)), size=n_boot).astype(float)
    with np.errstate(all="ignore"):
        punkt = sx.sum(axis=1) / sb.sum(axis=1)
        boot = (gew @ sx.T) / (gew @ sb.T)  # n_boot × Jahre
    return {"jahre": list(jahre), "wert": punkt, "boot": boot,
            "unten": np.nanquantile(boot, 0.025, axis=0), "oben": np.nanquantile(boot, 0.975, axis=0)}


def verhaeltnis_mit_intervall(boot: np.ndarray, jahre, zaehler: int, nenner: int, punkt) -> dict:
    i, k = list(jahre).index(zaehler), list(jahre).index(nenner)
    r = boot[:, i] / boot[:, k]
    return {"wert": float(punkt[i] / punkt[k]), "unten": float(np.nanquantile(r, 0.025)),
            "oben": float(np.nanquantile(r, 0.975))}


# --- Bruchpunkt ----------------------------------------------------------------------------------------------


def _ols(X: np.ndarray, y: np.ndarray):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    rest = y - X @ beta
    return beta, rest, float(rest @ rest)


def _bic(rss: float, n: int, p: int) -> float:
    return n * np.log(rss / n) + p * np.log(n)


def bruch_modelle(t: np.ndarray, y: np.ndarray, extra: dict[str, np.ndarray] | None = None,
                  rand: int = BRUCH_RAND_MONATE) -> dict:
    """Passt M0, M_stufe(k), M_knick(k) und feste Zusatzmodelle an; t in Monaten (ganzzahlig, Lücken erlaubt)."""
    n = len(y)
    eins = np.ones(n)
    X0 = np.column_stack([eins, t])
    _, _, rss0 = _ols(X0, y)
    aus = {"M0": {"bic": _bic(rss0, n, 2), "rss": rss0}}
    kand = [k for k in np.unique(t) if (t < k).sum() >= rand and (t >= k).sum() >= rand]
    beste_s, beste_k = None, None
    for k in kand:
        s = (t >= k).astype(float)
        b, _, rss = _ols(np.column_stack([X0, s]), y)
        if beste_s is None or rss < beste_s["rss"]:
            beste_s = {"k": int(k), "rss": rss, "stufe": float(b[2]), "steigung": float(b[1])}
        h = np.maximum(t - k, 0.0)
        b2, _, rss2 = _ols(np.column_stack([X0, h]), y)
        if beste_k is None or rss2 < beste_k["rss"]:
            beste_k = {"k": int(k), "rss": rss2, "steigungswechsel": float(b2[2]), "steigung": float(b2[1])}
    beste_s["bic"] = _bic(beste_s["rss"], n, 4)
    beste_k["bic"] = _bic(beste_k["rss"], n, 4)
    aus["M_stufe"], aus["M_knick"] = beste_s, beste_k
    for name, regressoren in (extra or {}).items():
        R = regressoren if regressoren.ndim == 2 else regressoren[:, None]
        b, _, rss = _ols(np.column_stack([X0, R]), y)
        aus[name] = {"bic": _bic(rss, n, 2 + R.shape[1]), "rss": rss, "koeffizienten": [float(v) for v in b[2:]],
                     "steigung": float(b[1])}
    return aus


def bruch_bootstrap(t, y, n_boot=BRUCH_BOOTSTRAP_N, block=BRUCH_BLOCK_MONATE, seed=SEED, rand=BRUCH_RAND_MONATE):
    """Lage der Stufe: Block-Bootstrap der Reste des besten Stufenmodells; Rückgabe aller k̂."""
    m = bruch_modelle(t, y, rand=rand)["M_stufe"]
    s = (t >= m["k"]).astype(float)
    X = np.column_stack([np.ones(len(t)), t, s])
    beta, rest, _ = _ols(X, y)
    passung = X @ beta
    rng = np.random.default_rng(seed)
    n = len(y)
    ks = []
    for _ in range(n_boot):
        starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
        r = np.concatenate([rest[s0:s0 + block] for s0 in starts])[:n]
        ks.append(bruch_modelle(t, passung + r, rand=rand)["M_stufe"]["k"])
    return np.array(ks)


def monat_aus_index(k: int) -> str:
    return f"{2013 + k // 12:04d}-{k % 12 + 1:02d}"


def t_von(monate) -> np.ndarray:
    return np.array([(j - 2013) * 12 + (m - 1) for j, m in monate], dtype=float)


# --- Teil 3: Auswahlregeln -------------------------------------------------------------------------------------


def regel_r1(x, g, monate, breite, landanteil) -> np.ndarray:
    idx = [i for i, (j, _) in enumerate(monate) if j in BASISJAHRE]
    w = np.where(g[idx], x[idx], np.nan)
    n = np.isfinite(w).sum(axis=0)
    with np.errstate(all="ignore"):
        mx = np.where(n > 0, np.nanmax(np.where(np.isfinite(w), w, -np.inf), axis=0), np.inf)
    b = np.abs(breite)
    return (landanteil >= R1_LANDANTEIL) & (b >= R1_BREITE[0]) & (b <= R1_BREITE[1]) & (n >= R1_MIN_MONATE) & (mx < R1_MAX_WERT)


def regel_r2(x, g, bm, monate, breite, klasse) -> tuple[np.ndarray, str, np.ndarray]:
    """Rückgabe (Maske, angewandte Regel, größte Jahresabweichung je Zelle)."""
    import warnings

    monate = [tuple(mm) for mm in monate]
    ok = g & (bm >= MIN_BASIS_WERT) & np.isfinite(bm)
    r = np.where(ok, x / np.where(ok, bm, 1.0), np.nan)
    idx = [i for i, (j, _) in enumerate(monate) if j in BASISJAHRE]
    n = ok[idx].sum(axis=0)
    abw = np.zeros(x.shape[1])
    jahr_ok = np.ones(x.shape[1], dtype=bool)
    for j in BASISJAHRE:
        rows = [i for i, (jj, _) in enumerate(monate) if jj == j]
        nj = ok[rows].sum(axis=0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            mj = np.nanmean(r[rows], axis=0)
        jahr_ok &= nj >= R2_MIN_MONATE_JE_JAHR
        abw = np.maximum(abw, np.abs(np.log(np.where(mj > 0, mj, np.nan))))
    abw = np.where(np.isfinite(abw), abw, np.inf)
    grund = (klasse == "hell") & (np.abs(breite) < R2_MAX_BREITE) & (n >= R2_MIN_MONATE) & jahr_ok
    haupt = grund & (abw <= R2_MAX_JAHRESABWEICHUNG)
    if haupt.sum() >= R2_MIN_ZELLEN:
        return haupt, "Hauptregel (alle Jahre 2013–2019 innerhalb ±5 %)", abw
    kand = np.nonzero(grund)[0]
    anzahl = max(1, int(np.ceil(R2_ERSATZ_ANTEIL * len(kand))))
    wahl = kand[np.argsort(abw[kand])[:anzahl]]
    m = np.zeros(x.shape[1], dtype=bool)
    m[wahl] = True
    return m, "Ersatzregel (10 % stabilste)", abw


@dataclass
class Gruppe:
    name: str
    maske: np.ndarray


# --- Zusatzdaten: Landanteil, Kontinent, L1B-Versionen --------------------------------------------------------


def land_und_kontinent(zeilen, spalten) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Je Zelle: Landanteil gesamt, Kontinent (M49-Region mit größtem Anteil), Anteil dieses Kontinents."""
    from aleph.layers import un_m49, zell_einheiten

    einheiten, zuordnung, _, _ = zell_einheiten.lade()
    m49, _ = un_m49.lade()
    region = dict(zip(m49["m49"], m49["region"]))
    z = zuordnung.merge(einheiten[["einheit_id", "un_m49"]], on="einheit_id", how="left")
    z["region"] = z["un_m49"].map(region).fillna("")
    schluessel = z["zeile"].to_numpy() * 1440 + z["spalte"].to_numpy()
    ziel = np.asarray(zeilen) * 1440 + np.asarray(spalten)
    pos = {k: i for i, k in enumerate(ziel)}
    land = np.zeros(len(ziel))
    je = {}
    for k, r, a in zip(schluessel, z["region"], z["anteil"]):
        i = pos.get(int(k))
        if i is None:
            continue
        land[i] += a
        if r:
            je[(i, r)] = je.get((i, r), 0.0) + a
    kont = np.full(len(ziel), "", dtype=object)
    kanteil = np.zeros(len(ziel))
    for (i, r), a in je.items():
        if a > kanteil[i]:
            kont[i], kanteil[i] = r, a
    return np.minimum(land, 1.0), kont, kanteil


def l1b_anteil_neu(monate) -> tuple[np.ndarray, dict]:
    """Je Monat Anteil der VNP02DNB-Dateien mit L1B_NEUE_VERSION (aus dem Tagesscan des NASA-Katalogs)."""
    daten = json.loads((ausgabe_ordner() / "l1b_versionen.json").read_text(encoding="utf-8"))
    je_monat = {}
    for tag, zaehler in daten["tage"].items():
        mon = tag[:7]
        neu = sum(n for k, n in zaehler.items() if k.split()[0] == L1B_NEUE_VERSION)
        alle = sum(zaehler.values())
        a, b = je_monat.get(mon, (0, 0))
        je_monat[mon] = (a + neu, b + alle)
    f = np.array([je_monat[f"{j:04d}-{m:02d}"][0] / je_monat[f"{j:04d}-{m:02d}"][1] for j, m in monate])
    return f, {k: v[0] / v[1] for k, v in sorted(je_monat.items())}


# --- Rechnen ------------------------------------------------------------------------------------------------------


def _grundlage(s: dict, feld: str = HAUPTFELD) -> dict:
    monate = [tuple(m) for m in s["monate"]]
    x = s[f"{feld}_mittel_beobachtet"].astype("float64")
    anteil = beobachtet_anteil(s[f"{feld}_gueltige_pixel"], s[f"{feld}_aufgefuellt_pixel"])
    g = gueltig_maske(x, anteil, s["breite"], monate)
    b = basislinie(x, g, monate)
    from aleph.detect.statistik import zellflaeche_km2

    return {"monate": monate, "x": x, "g": g, "b": b, "bm": basis_je_monat(b, monate), "anteil": anteil,
            "niveau": niveau(x, g, monate), "a": zellflaeche_km2(s["breite"]),
            "kachel": kachel_von(s["zeilen"], s["spalten"])}


def _gruppen(s, gl, kont, kanteil) -> list[Gruppe]:
    kl = klassen(gl["niveau"])
    br = s["breite"]
    alle = np.ones(len(br), dtype=bool)
    gr = [Gruppe("alle beleuchteten Zellen", alle), Gruppe("Klasse mittel", kl == "mittel"),
          Gruppe("Klasse hell", kl == "hell")]
    gr += [Gruppe(f"Breite {n}", (br >= u) & (br < o)) for n, u, o in BREITENBAENDER]
    for r, name in (("Africa", "Afrika"), ("Europe", "Europa"), ("Asia", "Asien"), ("Oceania", "Ozeanien")):
        gr.append(Gruppe(f"Kontinent {name}", (kont == r) & (kanteil >= MIN_LANDANTEIL_KONTINENT)))
    return gr


def _rund(v, n=3):
    return None if v is None or not np.isfinite(v) else round(float(v), n)


def rechne() -> dict:
    s = lade_stapel()
    gl = _grundlage(s)
    monate = gl["monate"]
    land, kont, kanteil = land_und_kontinent(s["zeilen"], s["spalten"])
    jahre = list(range(2013, 2023))
    erg = {"version": VERSION, "monate": [f"{j:04d}-{m:02d}" for j, m in monate],
           "zustand": [int(z) for z in s["zustand"]], "gruppen": {}}

    # Teil 1.1 Monatsreihen und Jahreswerte je Gruppe
    for gr in _gruppen(s, gl, kont, kanteil):
        mi = monatsindex(gl["x"], gl["g"], gl["bm"], gl["a"], gr.maske)
        jb = jahresindex_bootstrap(gl["x"], gl["g"], gl["bm"], gl["a"], gr.maske, monate, gl["kachel"], jahre)
        erg["gruppen"][gr.name] = {
            "zellen_gesamt": int(gr.maske.sum()),
            "monat_index": [_rund(v) for v in mi["index"]],
            "monat_median": [_rund(v) for v in mi["median_verhaeltnis"]],
            "monat_zellen": [int(v) for v in mi["zellen"]],
            "jahr": {str(j): {"wert": _rund(jb["wert"][k]), "unten": _rund(jb["unten"][k]), "oben": _rund(jb["oben"][k])}
                     for k, j in enumerate(jahre)},
            "verhaeltnis": {f"{a}/{b}": {k: _rund(v) for k, v in verhaeltnis_mit_intervall(jb["boot"], jahre, a, b, jb["wert"]).items()}
                            for a, b in ((2020, 2019), (2021, 2019), (2022, 2019), (2021, 2020), (2022, 2021))},
        }
        print(f"  Gruppe {gr.name}: {int(gr.maske.sum())} Zellen", flush=True)

    # Gegenprobe Blickwinkel: near_nadir mit eigener Basislinie
    gn = _grundlage(s, "near_nadir")
    alle = np.ones(len(s["breite"]), dtype=bool)
    jb = jahresindex_bootstrap(gn["x"], gn["g"], gn["bm"], gn["a"], alle, monate, gn["kachel"], jahre)
    erg["near_nadir"] = {"monat_index": [_rund(v) for v in monatsindex(gn["x"], gn["g"], gn["bm"], gn["a"], alle)["index"]],
                         "jahr": {str(j): _rund(jb["wert"][k]) for k, j in enumerate(jahre)}}
    # Zahl der Beobachtungen (Num) in beleuchteten gültigen Zellen
    ok = gl["g"] & (gl["bm"] >= MIN_BASIS_WERT)
    num = np.where(ok, s["allangle_num"], np.nan)
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        erg["num_median_je_monat"] = [_rund(v, 2) for v in np.nanmedian(num, axis=1)]
        erg["anteil_beobachtet_median_je_monat"] = [_rund(v, 3) for v in np.nanmedian(np.where(gl["bm"] >= MIN_BASIS_WERT, gl["anteil"], np.nan), axis=1)]

    # Teil 1.2 Bruchpunkt
    idx = np.array(erg["gruppen"]["alle beleuchteten Zellen"]["monat_index"], dtype=float)
    nimm = np.array([m not in TEILMONATE for m in monate])
    t = t_von(monate)[nimm]
    y = np.log(idx[nimm])
    f_l1b, f_je_monat = l1b_anteil_neu(monate)
    jan = np.column_stack([(t >= (2021 - 2013) * 12).astype(float), (t >= (2022 - 2013) * 12).astype(float)])
    mod = bruch_modelle(t, y, {"M_jan": jan, "M_l1b": f_l1b[nimm]})
    ks = bruch_bootstrap(t, y)
    erg["bruch"] = {
        "modelle": {k: {kk: (monat_aus_index(vv) if kk == "k" else _rund(vv, 4) if isinstance(vv, float) else vv)
                        for kk, vv in v.items()} for k, v in mod.items()},
        "k_bootstrap_5_95": [monat_aus_index(int(np.quantile(ks, 0.05))), monat_aus_index(int(np.quantile(ks, 0.95)))],
        "k_bootstrap_haeufigste": {monat_aus_index(int(k)): int(n) for k, n in zip(*np.unique(ks, return_counts=True)) if n >= 10},
        "l1b_anteil_neu_je_monat": {k: _rund(v) for k, v in f_je_monat.items() if k < "2023"},
        "groesste_monatsspruenge": sorted(
            [{"monat": monat_aus_index(int(t[i])), "aenderung_ln": _rund(y[i] - y[i - 1], 4)} for i in range(1, len(y))
             if t[i] - t[i - 1] == 1], key=lambda d: -abs(d["aenderung_ln"]))[:6],
    }
    erg["bruch_je_gruppe"] = {}
    for name, gdat in erg["gruppen"].items():
        yi = np.array(gdat["monat_index"], dtype=float)[nimm]
        if np.isfinite(yi).all() and (yi > 0).all():
            m = bruch_modelle(t, np.log(yi), {"M_l1b": f_l1b[nimm]})
            erg["bruch_je_gruppe"][name] = {"stufe_bei": monat_aus_index(m["M_stufe"]["k"]),
                                            "stufe_ln": _rund(m["M_stufe"]["stufe"], 4),
                                            "bic_stufe": _rund(m["M_stufe"]["bic"], 1), "bic_knick": _rund(m["M_knick"]["bic"], 1),
                                            "bic_l1b": _rund(m["M_l1b"]["bic"], 1), "bic_m0": _rund(m["M0"]["bic"], 1),
                                            "l1b_koeffizient_ln": _rund(m["M_l1b"]["koeffizienten"][0], 4)}

    # Teil 1.3 gleiche Kalendermonate, fester Zellkreis je Kalendermonat
    erg["kalendermonate"] = {}
    for m in range(1, 13):
        rows = [i for i, (_, mm) in enumerate(monate) if mm == m]
        ok = gl["g"][rows] & (gl["bm"][rows] >= MIN_BASIS_WERT)
        fest = ok.all(axis=0)
        werte = {}
        for i in rows:
            sx, sb, _ = summen(gl["x"][[i]], gl["g"][[i]], gl["bm"][[i]], gl["a"], fest)
            werte[str(monate[i][0])] = _rund(sx[0] / sb[0])
        erg["kalendermonate"][f"{m:02d}"] = {"zellen": int(fest.sum()), "index": werte}

    # Teil 3
    r1 = regel_r1(gl["x"], gl["g"], monate, s["breite"], land)
    dunkel = {}
    for j in jahre:
        rows = [i for i, (jj, _) in enumerate(monate) if jj == j]
        ok = gl["g"][rows] & r1[None, :]
        w = gl["a"][None, :] * np.where(ok, gl["x"][rows], 0.0)
        dunkel[str(j)] = {"mittel": _rund(w.sum() / (gl["a"][None, :] * ok).sum(), 4),
                          "anteil_ueber_0": _rund((ok & (gl["x"][rows] > 0)).sum() / ok.sum(), 4),
                          "zellmonate": int(ok.sum())}
    dunkel_monat = []
    for i in range(len(monate)):
        ok = gl["g"][i] & r1
        dunkel_monat.append(_rund((gl["a"] * np.where(ok, gl["x"][i], 0)).sum() / (gl["a"] * ok).sum(), 4) if ok.any() else None)
    kl = klassen(gl["niveau"])
    r2, r2_regel, _ = regel_r2(gl["x"], gl["g"], gl["bm"], monate, s["breite"], kl)
    jb2 = jahresindex_bootstrap(gl["x"], gl["g"], gl["bm"], gl["a"], r2, monate, gl["kachel"], jahre)
    erg["teil3"] = {
        "r1_zellen": int(r1.sum()), "r1_je_jahr": dunkel, "r1_je_monat": dunkel_monat,
        "r2_zellen": int(r2.sum()), "r2_regel": r2_regel,
        "r2_jahr": {str(j): {"wert": _rund(jb2["wert"][k]), "unten": _rund(jb2["unten"][k]), "oben": _rund(jb2["oben"][k])}
                    for k, j in enumerate(jahre)},
        "r2_verhaeltnis": {f"{a}/{b}": {k: _rund(v) for k, v in verhaeltnis_mit_intervall(jb2["boot"], jahre, a, b, jb2["wert"]).items()}
                           for a, b in ((2021, 2019), (2022, 2019), (2021, 2020), (2022, 2021))},
        "r2_monat_index": [_rund(v) for v in monatsindex(gl["x"], gl["g"], gl["bm"], gl["a"], r2)["index"]],
        "r2_breiten": {n: int((r2 & (s["breite"] >= u) & (s["breite"] < o)).sum()) for n, u, o in BREITENBAENDER},
        "r2_kontinente": {k: int((r2 & (kont == k)).sum()) for k in ("Africa", "Europe", "Asia", "Oceania")},
    }
    np.savez_compressed(ausgabe_ordner() / "auswahl_teil3.npz", r1=r1, r2=r2, zeilen=s["zeilen"], spalten=s["spalten"])
    ziel = ausgabe_ordner() / "ergebnis.json"
    ziel.write_text(json.dumps(erg, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"geschrieben: {ziel}")
    return erg


def rechne_b() -> dict:
    """Teil 4: relative Veränderung Würfel gegen EOG VCMCFG (Kandidat B), 2019–2022."""
    from aleph.quellenvergleich import ee_nachtlicht as ee

    s = lade_stapel()
    gl = _grundlage(s)
    monate = gl["monate"]
    land, _, _ = land_und_kontinent(s["zeilen"], s["spalten"])
    kl = klassen(gl["niveau"])
    basis = (s["breite"] < B_MAX_BREITE) & (land >= B_LANDANTEIL) & np.isin(kl, ["mittel", "hell"])
    pos = {m: i for i, m in enumerate(monate)}
    ids, inv = np.unique(gl["kachel"], return_inverse=True)
    je_kalendermonat = {}
    fehlend = []
    for m in range(1, 13):
        jahre_m = [j for j in B_JAHRE if (j, m) in pos]
        werte_b, ok_b = {}, {}
        for j in jahre_m:
            pruefe_monat((j, m))
            try:
                w, a, _ = ee.lies_ergebnis(j, m, "B")
            except FileNotFoundError:
                fehlend.append(f"{j}-{m:02d}")
                continue
            wb, ab = w[s["zeilen"], s["spalten"]], a[s["zeilen"], s["spalten"]]
            werte_b[j], ok_b[j] = wb, np.isfinite(wb) & (ab >= B_MIN_ANTEIL)
        if len(werte_b) != len(jahre_m):
            continue
        fest = basis.copy()
        for j in jahre_m:
            fest &= gl["g"][pos[(j, m)]] & ok_b[j]
        eintrag = {"zellen": int(fest.sum())}
        for q in ("wuerfel", "b"):
            sums = {}
            for j in jahre_m:
                x = gl["x"][pos[(j, m)]] if q == "wuerfel" else np.maximum(werte_b[j], 0.0)
                beitrag = np.where(fest, gl["a"] * x, 0.0)
                sums[j] = beitrag.sum()
            eintrag[q] = {str(j): _rund(sums[j] / sums[2019]) for j in jahre_m}
        je_kalendermonat[f"{m:02d}"] = eintrag
    # gepoolt über die Kalendermonate, die in allen vier Jahren vorliegen (Juli fehlt 2022 → ohne Juli)
    tile_p = {q: {j: np.zeros(len(ids)) for j in B_JAHRE} for q in ("wuerfel", "b")}
    for m in [mm for mm in range(1, 13) if mm != 7 and f"{mm:02d}" in je_kalendermonat]:
        fest = basis.copy()
        wbs = {}
        for j in B_JAHRE:
            w, a, _ = ee.lies_ergebnis(j, m, "B")
            wb, ab = w[s["zeilen"], s["spalten"]], a[s["zeilen"], s["spalten"]]
            wbs[j] = wb
            fest &= gl["g"][pos[(j, m)]] & np.isfinite(wb) & (ab >= B_MIN_ANTEIL)
        for j in B_JAHRE:
            tile_p["wuerfel"][j] += np.bincount(inv, weights=np.where(fest, gl["a"] * gl["x"][pos[(j, m)]], 0.0), minlength=len(ids))
            tile_p["b"][j] += np.bincount(inv, weights=np.where(fest, gl["a"] * np.maximum(wbs[j], 0.0), 0.0), minlength=len(ids))
    rng = np.random.default_rng(SEED)
    gew = rng.multinomial(len(ids), np.full(len(ids), 1 / len(ids)), size=BOOTSTRAP_N).astype(float)
    pool = {}
    for q in ("wuerfel", "b"):
        pool[q] = {}
        for j in (2020, 2021, 2022):
            punkt = tile_p[q][j].sum() / tile_p[q][2019].sum()
            boot = (gew @ tile_p[q][j]) / (gew @ tile_p[q][2019])
            pool[q][f"{j}/2019"] = {"wert": _rund(punkt), "unten": _rund(np.quantile(boot, 0.025)), "oben": _rund(np.quantile(boot, 0.975))}
    # Differenz des Anstiegs (Würfel − B) mit Bootstrap
    diff = {}
    for j in (2020, 2021, 2022):
        dw = (gew @ tile_p["wuerfel"][j]) / (gew @ tile_p["wuerfel"][2019])
        db = (gew @ tile_p["b"][j]) / (gew @ tile_p["b"][2019])
        diff[f"{j}/2019"] = {"unten": _rund(np.quantile(dw - db, 0.025)), "oben": _rund(np.quantile(dw - db, 0.975))}
    urteil = {}
    for j in (2021, 2022):
        aw = pool["wuerfel"][f"{j}/2019"]["wert"] - 1
        ab_ = pool["b"][f"{j}/2019"]["wert"] - 1
        if aw < B_MIN_ANSTIEG_WUERFEL:
            urteil[str(j)] = "nicht bewertet (Würfel steigt im Zellkreis um weniger als 5 %)"
        elif ab_ >= B_GLEICH_AB * aw:
            urteil[str(j)] = "B zeigt denselben Anstieg"
        elif ab_ < B_KEIN_UNTER * aw:
            urteil[str(j)] = "B zeigt keinen nennenswerten Anstieg"
        else:
            urteil[str(j)] = "teilweise"
    erg = {"je_kalendermonat": je_kalendermonat, "gepoolt_ohne_juli": pool, "differenz_wuerfel_minus_b": diff,
           "urteil": urteil, "fehlende_b_monate": fehlend, "zellen_grundmenge": int(basis.sum())}
    (ausgabe_ordner() / "ergebnis_b.json").write_text(json.dumps(erg, ensure_ascii=False, indent=1), encoding="utf-8")
    return erg


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    aktion = argv[0] if argv else "rechnen"
    if aktion == "lesen":
        s = lies_stapel()
        np.savez_compressed(stapel_pfad(), **s)
        print(f"geschrieben: {stapel_pfad()}")
    elif aktion == "rechnen":
        rechne()
    elif aktion == "b":
        print(json.dumps(rechne_b(), ensure_ascii=False, indent=1))
    else:
        raise SystemExit(f"Unbekannte Aktion {aktion!r} (lesen | rechnen | b)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
