"""Statistische Bausteine für Anomalie- und Trendverfahren (nur numpy, math und scipy.sparse).

Seit 2026-09-26 (Statistisches Grundgerüst): Mann-Kendall, Sen-Steigung, zwei Korrekturen für
Autokorrelation (Hamed-Rao, Prewhitening nach Yue et al.), Flächengewichte, Moran's I mit dünn
besetzter Nachbarschaftsmatrix, Mindestlängen. Alle Funktionen rechnen VEKTORISIERT über viele
Zellen zugleich (Zeit auf Achse 0, Zellen auf Achse 1); Schleifen laufen nur über Zeitabstände
(höchstens 155), nie über Zellen.

Fehlende Werte sind NaN und bleiben NaN. Sie werden nie zu 0 und zählen nie als Beobachtung:
n ist immer die Zahl der GÜLTIGEN Werte je Zelle.

Quellen (Stand der Prüfung 2026-09-26; „Metadaten“ = Autoren, Jahr, Titel, Zeitschrift, Band,
Seiten bei Crossref gesehen; „Originaltext“ = die benutzte Aussage im Volltext gelesen):
- Benjamini, Y.; Hochberg, Y. (1995): Controlling the False Discovery Rate: A Practical and Powerful
  Approach to Multiple Testing. J. R. Stat. Soc. B 57(1), 289-300, DOI 10.1111/j.2517-6161.1995.tb02031.x.
  Geprüft: Metadaten. Das Verfahren (größter Rang i mit p_(i) <= q*i/m) ist Standard; Volltext nicht gelesen.
- Wilks, D. S. (2016): "The Stippling Shows Statistically Significant Grid Points": How Research Results
  are Routinely Overstated and Overinterpreted, and What to Do about It. BAMS 97(12), 2263-2273,
  DOI 10.1175/BAMS-D-15-00267.1. Geprüft: Metadaten (Crossref) und ORIGINALTEXT des Autorenmanuskripts
  (AMS 96th Annual Meeting 2016, Paper 9.3, ams.confex.com, gelesen 2026-09-26), NICHT die
  Zeitschriftenfassung (Verlagsseite gesperrt). Wörtlich: „for data grids exhibiting moderate to strong
  spatial correlation, approximately correct global test levels can be produced using the FDR procedure
  by choosing αFDR = 2αglobal.“ Die Regel betrifft das GLOBALE Testniveau (Wahrscheinlichkeit, dass
  überhaupt eine Zelle gemeldet wird, wenn nirgends etwas ist), nicht die Fehlerrate je Zelle; bei fast
  unabhängigen Zellen ist das globale Niveau nahe αFDR selbst (Abbildung 4 des Manuskripts), also
  doppelt so hoch wie αglobal.
- Mann, H. B. (1945): Nonparametric Tests Against Trend. Econometrica 13(3), 245-259, DOI 10.2307/1907187.
  Geprüft: Metadaten.
- Kendall, M. G.: Rank Correlation Methods (Buch, mehrere Auflagen). Nicht geprüft. Varianz von S mit
  Bindungskorrektur Var(S) = [n(n-1)(2n+5) - Σ t(t-1)(2t+5)] / 18 ist die Standardformel; gegen
  scipy.stats.kendalltau in tests/test_detect_statistik.py nachgerechnet (gleiches S und gleiches z).
- Sen, P. K. (1968): Estimates of the Regression Coefficient Based on Kendall's Tau. JASA 63(324),
  1379-1389, DOI 10.1080/01621459.1968.10480934. Geprüft: Metadaten. Steigung = Median aller paarweisen
  Steigungen; gegen scipy.stats.theilslopes nachgerechnet. Das Vertrauensband über die Ränge
  (N' - C)/2 und (N' + C)/2 mit C = z * sqrt(Var(S)) ist die übliche Form (nicht am Originaltext geprüft).
- Hamed, K. H.; Ramachandra Rao, A. (1998): A modified Mann-Kendall trend test for autocorrelated data.
  J. Hydrol. 204(1-4), 182-196, DOI 10.1016/S0022-1694(97)00125-X. Geprüft: Metadaten. Umgesetzt ist die
  verbreitete Form (Korrekturfaktor aus den signifikanten Autokorrelationen der Ränge der trendbereinigten
  Reihe); Einzelheiten (welche Lags, welches Niveau) NICHT am Originaltext geprüft.
- Yue, S.; Pilon, P.; Phinney, B.; Cavadias, G. (2002): The influence of autocorrelation on the ability to
  detect trend in hydrological series. Hydrol. Process. 16(9), 1807-1829, DOI 10.1002/hyp.1095. Geprüft:
  Metadaten. Umgesetzt ist das „trend-free pre-whitening“ in der üblichen Beschreibung (Sen-Trend abziehen,
  Lag-1-Autokorrelation entfernen, Trend wieder addieren); Einzelheiten NICHT am Originaltext geprüft.
- Moran, P. A. P. (1950): Notes on Continuous Stochastic Phenomena. Biometrika 37(1-2), 17-23,
  DOI 10.1093/biomet/37.1-2.17. Geprüft: Metadaten. Erwartungswert -1/(n-1) und Varianz unter Normalannahme
  in der Form von Cliff & Ord (Buch „Spatial Processes“, 1981, nicht geprüft); gegen eine direkte
  Rechnung mit voller Matrix nachgerechnet (Test).
- Rousseeuw, P. J.; Croux, C. (1993): Alternatives to the Median Absolute Deviation. JASA 88(424),
  1273-1283, DOI 10.1080/01621459.1993.10476408. Geprüft: Metadaten. Nur als Beleg, dass 1,4826·MAD bei
  Normalverteilung die Standardabweichung schätzt (Faktor 1/Φ⁻¹(3/4), nachgerechnet im Test).

Evidenzstufe aller Ergebnisse dieser Bausteine: „beobachtet“ (Beschreibung gemessener Reihen mit
statistischer Unsicherheit). Kein Baustein prüft einen Zusammenhang zwischen zwei Größen.
"""

import math
from dataclasses import dataclass

import numpy as np

STATISTIK_VERSION = "0.2.0"

_ERFC = np.frompyfunc(math.erfc, 1, 1)

# Wilks (2016, Autorenmanuskript, siehe oben): αFDR = 2·αglobal bei mäßiger bis starker räumlicher Korrelation.
ALPHA_GLOBAL = 0.05
FAKTOR_FDR = 2.0


def alpha_fdr(alpha_global: float = ALPHA_GLOBAL) -> float:
    """Niveau für Benjamini-Hochberg nach der Regel von Wilks (2016): 2 · αglobal (0,10 bei 0,05)."""
    if not 0 < alpha_global < 0.5:
        raise ValueError("alpha_global muss zwischen 0 und 0,5 liegen.")
    return FAKTOR_FDR * alpha_global


def normal_zweiseitig(z: np.ndarray) -> np.ndarray:
    """Zweiseitige Überschreitungswahrscheinlichkeit P(|Z| >= |z|) der Standardnormalverteilung.

    NaN bleibt NaN. Für große |z| ist das exakter als 1 - Verteilungsfunktion (erfc).
    """
    z = np.asarray(z, dtype="float64")
    p = np.full(z.shape, np.nan)
    gueltig = np.isfinite(z)
    p[gueltig] = _ERFC(np.abs(z[gueltig]) / math.sqrt(2.0)).astype("float64")
    p[np.isinf(z)] = 0.0
    return p


def benjamini_hochberg(p: np.ndarray, q: float) -> np.ndarray:
    """Benjamini-Hochberg-Verfahren.

    Kontrolliert den erwarteten Anteil falscher ZELLEN (nicht falscher Ereignisse) unter den
    Meldungen nur dann auf q, wenn die p-Werte exakt sind und die Tests unabhängig oder positiv
    abhängig; sonst gilt das nicht (siehe unten). Kein Anspruch auf mehr.

    `p`: beliebig geformte Reihe von p-Werten; NaN heißt „nicht getestet" und zählt weder
    zur Testzahl m noch wird es je gemeldet. Rückgabe: Boolesche Maske gleicher Form,
    True = auch nach der Korrektur auffällig. Die Grenze ist der größte Rang i mit
    p_(i) <= q * i / m; alle p-Werte bis dahin werden gemeldet.

    Grenze des Verfahrens: Die Garantie gilt für unabhängige oder positiv abhängige Tests
    und exakte p-Werte. Ob die Voraussetzung der positiven Abhängigkeit für benachbarte Zellen
    bei zweiseitigen Tests erfüllt ist, ist nicht gezeigt, und die p-Werte hier sind nominell
    (siehe aleph/detect/anomalie.py, Abschnitt „Was nicht garantiert ist").
    """
    p = np.asarray(p, dtype="float64")
    treffer = np.zeros(p.shape, dtype=bool)
    getestet = np.isfinite(p)
    m = int(getestet.sum())
    if m == 0:
        return treffer
    werte = p[getestet]
    sortiert = np.sort(werte)
    grenzen = q * np.arange(1, m + 1) / m
    unter = np.flatnonzero(sortiert <= grenzen)
    if unter.size == 0:
        return treffer
    treffer[getestet] = werte <= sortiert[unter[-1]]
    return treffer


# --- Mindestlängen --------------------------------------------------------------------


@dataclass(frozen=True)
class Mindestlaengen:
    """Mindestzahl GÜLTIGER Werte je Zelle und Verfahren; darunter heißt das Ergebnis „nicht bestimmbar“.

    Begründung (eigene Festlegung 2026-09-26, keine Quelle, außer wo genannt):
    - `mann_kendall` 24 Monatswerte: Die Normalnäherung von S wird üblicherweise ab etwa n = 10 benutzt
      (verbreitete Faustregel, nicht an einer Quelle geprüft). 24 verlangt zusätzlich zwei volle Jahre,
      damit ein Trend nicht nur eine halbe Jahreszeit ist.
    - `autokorrelation` 60 Monatswerte (5 Jahre) für Hamed-Rao und Yue: Beide schätzen Autokorrelationen;
      deren Standardfehler ist etwa 1/sqrt(n), bei n = 60 also 0,13. Bei kürzeren Reihen ist die
      Korrektur selbst so unsicher, dass sie mehr Rauschen als Nutzen bringt.
    - `je_kalendermonat` 3: Für das Abziehen der Jahreszeit braucht jeder Kalendermonat mindestens 3
      Werte (Median aus 3); sonst werden die Werte dieses Kalendermonats nicht verwendet.
    - `basisjahre_anomalie` 5: wie bisher in aleph/detect/anomalie.py (Schwellen.min_basisjahre).
    - `moran_zellen` 30: Moran's I aus weniger als 30 Zellen ist als Diagnose zu grob.
    """

    mann_kendall: int = 24
    autokorrelation: int = 60
    je_kalendermonat: int = 3
    basisjahre_anomalie: int = 5
    moran_zellen: int = 30

    def __post_init__(self):
        if self.mann_kendall < 10:
            raise ValueError("mann_kendall muss mindestens 10 sein (Normalnäherung).")
        if self.autokorrelation < self.mann_kendall:
            raise ValueError("autokorrelation darf nicht kleiner als mann_kendall sein.")
        if self.je_kalendermonat < 2 or self.basisjahre_anomalie < 2 or self.moran_zellen < 3:
            raise ValueError("Mindestlängen zu klein.")


# --- Mann-Kendall und Sen-Steigung ------------------------------------------------------


def _als_2d(y: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype="float64")
    if y.ndim == 1:
        y = y[:, None]
    if y.ndim != 2:
        raise ValueError("Erwartet (Zeit, Zellen).")
    return y


def bindungs_summe(y: np.ndarray) -> np.ndarray:
    """Σ t(t-1)(2t+5) über alle Gruppen gleicher Werte je Zelle (NaN zählt nicht). Vektorisiert mit bincount."""
    y = _als_2d(y)
    t_len, n_zellen = y.shape
    s = np.sort(y, axis=0)  # NaN ans Ende
    neu = np.ones(s.shape, dtype=bool)
    neu[1:] = s[1:] != s[:-1]  # NaN != NaN: jede NaN eigene Gruppe, wird unten ausgeblendet
    gid = np.cumsum(neu, axis=0) - 1
    ok = np.isfinite(s)
    schluessel = (gid + np.arange(n_zellen)[None, :] * t_len)[ok]
    anzahl = np.bincount(schluessel, minlength=n_zellen * t_len).astype("float64")
    beitrag = anzahl * (anzahl - 1) * (2 * anzahl + 5)
    spalte = np.arange(n_zellen * t_len) // t_len
    return np.bincount(spalte, weights=beitrag, minlength=n_zellen)


def mann_kendall(y: np.ndarray) -> dict:
    """Mann-Kendall je Spalte. y: (Zeit, Zellen), NaN = fehlend (Paare mit NaN zählen nicht).

    Rückgabe (je Zelle): `s`, `var_s` (mit Bindungskorrektur, n = gültige Werte), `z` (mit
    Stetigkeitskorrektur ±1), `n`. Wo var_s <= 0 (z. B. alle Werte gleich): z = 0, wenn s = 0, sonst NaN.
    """
    y = _als_2d(y)
    t_len = y.shape[0]
    s = np.zeros(y.shape[1])
    for k in range(1, t_len):
        s += np.nansum(np.sign(y[k:] - y[:-k]), axis=0)
    n = np.isfinite(y).sum(axis=0).astype("float64")
    var_s = (n * (n - 1) * (2 * n + 5) - bindungs_summe(y)) / 18.0
    z = np.full(s.shape, np.nan)
    pos = var_s > 0
    z[pos] = (s[pos] - np.sign(s[pos])) / np.sqrt(var_s[pos])
    z[(~pos) & (s == 0)] = 0.0
    return {"s": s, "var_s": var_s, "z": z, "n": n}


def sen_steigung(y: np.ndarray, var_s: np.ndarray | None = None, niveau: float = 0.95,
                 behalte_sortierung: bool = False) -> dict:
    """Sen-Steigung je Spalte (Median aller paarweisen Steigungen, Einheit: je Zeitschritt).

    Mit `var_s` zusätzlich das Vertrauensband über die Ränge der sortierten Steigungen
    (untere Grenze = Rang (N'-C)/2, obere = Rang (N'+C)/2 + 1, C = z_{(1+niveau)/2} * sqrt(var_s)).
    Mit `behalte_sortierung` liegen die sortierten Steigungen unter `_sortiert` bei, damit `sen_band`
    ein zweites Band (z. B. mit der Hamed-Rao-Varianz) ohne erneutes Sortieren rechnen kann.
    Speicher: (Paare × Zellen) als float32, also Zellen in Blöcken übergeben (bei 150 Zeitschritten
    etwa 45 kB je Zelle).
    """
    y = _als_2d(y).astype("float32")
    t_len, n_zellen = y.shape
    teile = [(y[k:] - y[:-k]) / np.float32(k) for k in range(1, t_len)]
    steig = np.concatenate(teile, axis=0) if teile else np.full((0, n_zellen), np.nan, "float32")
    steig.sort(axis=0)  # NaN ans Ende
    m = np.isfinite(steig).sum(axis=0)
    ergebnis = {"steigung": np.full(n_zellen, np.nan), "unten": np.full(n_zellen, np.nan),
                "oben": np.full(n_zellen, np.nan), "paare": m}
    ok = m > 0
    spalten = np.arange(n_zellen)
    lo = np.clip((m - 1) // 2, 0, None)
    hi = np.clip(m // 2, 0, None)
    median = 0.5 * (steig[np.minimum(lo, len(steig) - 1), spalten].astype("float64")
                    + steig[np.minimum(hi, len(steig) - 1), spalten].astype("float64")) if len(steig) else np.full(n_zellen, np.nan)
    ergebnis["steigung"][ok] = median[ok]
    if var_s is not None:
        ergebnis["unten"], ergebnis["oben"] = sen_band(steig, m, var_s, niveau)
    if behalte_sortierung:
        ergebnis["_sortiert"] = steig
    return ergebnis


def sen_band(steig_sortiert: np.ndarray, m: np.ndarray, var_s: np.ndarray, niveau: float = 0.95):
    """Vertrauensband der Sen-Steigung aus sortierten paarweisen Steigungen (siehe `sen_steigung`).
    NaN oder nicht positive Varianz ergibt NaN (kein Band)."""
    n_zellen = steig_sortiert.shape[1]
    unten = np.full(n_zellen, np.nan)
    oben = np.full(n_zellen, np.nan)
    if not len(steig_sortiert):
        return unten, oben
    var = np.asarray(var_s, dtype="float64")
    gueltig = np.isfinite(var) & (var > 0) & (m > 0)
    z_krit = _normal_quantil(0.5 + niveau / 2.0)
    c = z_krit * np.sqrt(np.where(gueltig, var, 0.0))
    r_unten = np.floor((m - c) / 2.0).astype("int64")  # 1-basiert gerundet, dann 0-basiert
    r_oben = np.ceil((m + c) / 2.0).astype("int64")
    band_ok = gueltig & (r_unten >= 1) & (r_oben <= m)
    spalten = np.arange(n_zellen)
    iu = np.clip(r_unten - 1, 0, len(steig_sortiert) - 1)
    io = np.minimum(np.clip(r_oben, 0, len(steig_sortiert) - 1), np.clip(m - 1, 0, None))
    unten[band_ok] = steig_sortiert[iu, spalten][band_ok]
    oben[band_ok] = steig_sortiert[io, spalten][band_ok]
    return unten, oben


def _normal_quantil(p: float) -> float:
    """Quantil der Standardnormalverteilung (Bisektion über erfc; genau auf 1e-12, nur für feste Niveaus)."""
    lo, hi = -40.0, 40.0
    for _ in range(200):
        mitte = 0.5 * (lo + hi)
        if 0.5 * math.erfc(-mitte / math.sqrt(2.0)) < p:
            lo = mitte
        else:
            hi = mitte
    return 0.5 * (lo + hi)


# --- Autokorrelation ------------------------------------------------------------------------


def _raenge(y: np.ndarray) -> np.ndarray:
    """Ränge je Spalte (1..n, Durchschnittsränge bei Bindungen nicht nötig: gleiche Werte -> gleicher Rang
    über die Mitte der Gruppe). NaN bleibt NaN."""
    y = _als_2d(y)
    ordnung = np.argsort(y, axis=0, kind="stable")
    sortiert = np.take_along_axis(y, ordnung, axis=0)
    t_len, n_zellen = y.shape
    pos = np.arange(1, t_len + 1, dtype="float64")[:, None] * np.ones((1, n_zellen))
    neu = np.ones(y.shape, dtype=bool)
    neu[1:] = sortiert[1:] != sortiert[:-1]
    gid = np.cumsum(neu, axis=0) - 1
    schluessel = (gid + np.arange(n_zellen)[None, :] * t_len).ravel()
    summe = np.bincount(schluessel, weights=pos.ravel(), minlength=n_zellen * t_len)
    anzahl = np.bincount(schluessel, minlength=n_zellen * t_len)
    mittel = np.where(anzahl > 0, summe / np.maximum(anzahl, 1), np.nan)
    rang_sortiert = mittel[schluessel].reshape(y.shape)
    raenge = np.empty_like(y)
    np.put_along_axis(raenge, ordnung, rang_sortiert, axis=0)
    raenge[~np.isfinite(y)] = np.nan
    return raenge


def autokorrelation(y: np.ndarray, max_lag: int | None = None) -> np.ndarray:
    """Autokorrelation je Spalte für Lags 1..max_lag (NaN-fähig: nur Paare mit zwei gültigen Werten,
    Mittelwert und Nenner aus allen gültigen Werten). Rückgabe (max_lag, Zellen)."""
    y = _als_2d(y)
    t_len = y.shape[0]
    max_lag = t_len - 1 if max_lag is None else min(max_lag, t_len - 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mittel = np.nanmean(y, axis=0)
        d = y - mittel
        nenner = np.nansum(d * d, axis=0)
        rho = np.full((max_lag, y.shape[1]), np.nan)
        for k in range(1, max_lag + 1):
            rho[k - 1] = np.nansum(d[k:] * d[:-k], axis=0) / nenner
    rho[:, ~(nenner > 0)] = np.nan
    return rho


HAMED_RAO_LAGS = 3  # Standard: nur die ersten 3 Lags (Begründung im Docstring von `hamed_rao`)


def hamed_rao(y: np.ndarray, steigung: np.ndarray, var_s: np.ndarray, niveau_lag: float = 0.05,
              max_lag: int | None = HAMED_RAO_LAGS, nur_vergroessern: bool = True) -> dict:
    """Korrekturfaktor n/n* nach Hamed und Rao (1998) und korrigierte Varianz von S.

    Trendbereinigung mit der Sen-Steigung (je Zeitschritt), Ränge der bereinigten Reihe, Autokorrelation
    der Ränge; nur Lags mit |rho| > z_{1-niveau_lag/2}/sqrt(n) gehen ein (verbreitete Form, siehe Modulkopf).
    Faktor = 1 + 2/(n(n-1)(n-2)) · Σ (n-k)(n-k-1)(n-k-2) rho_k. Faktor <= 0 (möglich bei stark negativer
    Autokorrelation) ergibt NaN („nicht bestimmbar“), nie eine erfundene Zahl.

    `max_lag` (Standard 3): Mit ALLEN Lags (bis n-1) war die Korrektur am künstlichen Würfel ohne Trend
    und ohne Autokorrelation zu freigiebig: 8,9 % statt 5 % „signifikant“ bei 5 000 Reihen der Länge 150
    (gemessen 2026-09-26), weil von ~150 Lags zufällig einige die Signifikanzgrenze überschreiten.
    GRENZE (Auflage statistik-pruefer 2026-09-26): Auch mit 3 Lags hält die Korrektur das Niveau bei
    Autokorrelation NICHT: Bei AR(1) 0,5 fallen Lags unter der Grenze 1,96/sqrt(n) weg (rho_3 ≈ 0,12 < 0,16),
    der Faktor wird zu klein (etwa 2,4 statt etwa 3). Gemessen: reine AR(1)-Reihen 0,5, 20 × 2 000, BH:
    0,18 % der Zellen falsch, 70 % der Würfel mit Meldung; im künstlichen Würfel (mit Jahreszeit)
    0,33 % der Fläche, 90 % der Würfel. Mehr Lags (10, alle) waren schlechter (0,8 % bzw. 3,3 %).
    Lücken schwächen die Schätzung zusätzlich (Zähler nur vorhandene Paare, Nenner alle Werte).
    Die Beschränkung auf die ersten 3 Lags nennt die Dokumentation von pymannkendall als ebenfalls
    von Hamed und Rao (1998) vorgeschlagen (Drittquelle, NICHT am Originaltext geprüft). `None` = alle Lags.

    `nur_vergroessern` (Standard True, eigene Festlegung, ABWEICHUNG von der Literaturform): Der Faktor wird
    auf mindestens 1 gesetzt, die Korrektur darf die Unsicherheit also nur vergrößern. Grund (gemessen
    2026-09-26, 200 Würfel à 2 000 Zellen reines Rauschen der Länge 150, BH mit q = 0,10, damals mit ALLEN
    Lags): ohne Untergrenze meldeten 43,5 % der Würfel mindestens eine „signifikante“ Zelle, mit Untergrenze
    6,0 % (ohne Korrektur 6,0 %). Mit 3 Lags und Untergrenze: 10 % von 40 Würfeln (Zufallsschwankung). Zufällig negative Autokorrelationen verkleinern sonst die Varianz genau in den äußersten
    Rändern, auf die es bei Hunderttausenden Zellen ankommt.
    """
    y = _als_2d(y)
    t = np.arange(y.shape[0], dtype="float64")[:, None]
    rest = y - np.asarray(steigung)[None, :] * t
    r = _raenge(rest)
    n = np.isfinite(y).sum(axis=0).astype("float64")
    rho = autokorrelation(r, max_lag=max_lag)
    grenze = _normal_quantil(1 - niveau_lag / 2.0) / np.sqrt(np.maximum(n, 1))
    k = np.arange(1, rho.shape[0] + 1, dtype="float64")[:, None]
    gewicht = (n - k) * (n - k - 1) * (n - k - 2)
    beitrag = np.where(np.isfinite(rho) & (np.abs(rho) > grenze) & (gewicht > 0), gewicht * rho, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        faktor = 1.0 + 2.0 / (n * (n - 1) * (n - 2)) * beitrag.sum(axis=0)
    faktor = np.where((n >= 3) & (faktor > 0), faktor, np.nan)
    if nur_vergroessern:
        faktor = np.where(np.isfinite(faktor), np.maximum(faktor, 1.0), np.nan)
    return {"faktor": faktor, "var_s": np.asarray(var_s) * faktor}


def yue_vorbleichung(y: np.ndarray, steigung: np.ndarray, niveau_lag: float = 0.05) -> dict:
    """„Trend-free pre-whitening“ nach Yue et al. (2002), übliche Beschreibung (siehe Modulkopf):

    1. Sen-Trend abziehen, 2. Lag-1-Autokorrelation r1 der Restreihe; ist sie nicht signifikant
    (|r1| <= z_{1-niveau_lag/2}/sqrt(n)), bleibt die Originalreihe, 3. sonst Rest_t - r1·Rest_{t-1},
    4. Trend wieder addieren. Rückgabe: vorbereitete Reihe (für Mann-Kendall) und r1.
    Hinweis: Eine Lücke (NaN) macht den Folgewert ebenfalls NaN (kein Auffüllen).
    """
    y = _als_2d(y)
    t = np.arange(y.shape[0], dtype="float64")[:, None]
    b = np.asarray(steigung)[None, :]
    rest = y - b * t
    r1 = autokorrelation(rest, max_lag=1)[0]
    n = np.isfinite(y).sum(axis=0).astype("float64")
    grenze = _normal_quantil(1 - niveau_lag / 2.0) / np.sqrt(np.maximum(n, 1))
    wirksam = np.isfinite(r1) & (np.abs(r1) > grenze)
    gebleicht = np.full(y.shape, np.nan)
    gebleicht[1:] = rest[1:] - np.nan_to_num(r1)[None, :] * rest[:-1] + b * t[1:]
    reihe = np.where(wirksam[None, :], gebleicht, y)
    return {"reihe": reihe, "r1": r1, "wirksam": wirksam}


# --- Fläche --------------------------------------------------------------------------------

ERDRADIUS_KM = 6371.0


def zellflaeche_km2(breite_mitte: np.ndarray, zellgroesse_grad: float = 0.25) -> np.ndarray:
    """Fläche von Gitterzellen (Kugel, Radius 6371 km) je Zellmittelpunkt-Breite.

    A = R² · Δλ · (sin φ_oben − sin φ_unten): bei 0° etwa 773 km², bei 60° die Hälfte, bei 80° ein Sechstel.
    Die Länge spielt keine Rolle; über die Datumsgrenze gibt es keine doppelten Zellen (Gitter −180..180).
    """
    halb = np.radians(zellgroesse_grad) / 2.0
    lat = np.radians(np.asarray(breite_mitte, dtype="float64"))
    oben = np.clip(lat + halb, -np.pi / 2, np.pi / 2)
    unten = np.clip(lat - halb, -np.pi / 2, np.pi / 2)
    return ERDRADIUS_KM**2 * np.radians(zellgroesse_grad) * (np.sin(oben) - np.sin(unten))


def flaechenanteil(maske: np.ndarray, bezug: np.ndarray, breite: np.ndarray, zellgroesse_grad: float = 0.25) -> float:
    """Flächengewichteter Anteil: Fläche(maske & bezug) / Fläche(bezug). maske, bezug: (Breite, Länge).

    Für jede Aussage „X % der Fläche“. `bezug` sind die Zellen, über die die Aussage geht (z. B. alle
    bewertbaren Zellen); fehlende Zellen gehören nicht dazu. NaN, wenn der Bezug leer ist.
    """
    gewicht = zellflaeche_km2(breite, zellgroesse_grad)[:, None] * np.ones((1, np.asarray(maske).shape[1]))
    nenner = float(gewicht[bezug].sum())
    if nenner <= 0:
        return float("nan")
    return float(gewicht[np.asarray(maske, bool) & np.asarray(bezug, bool)].sum() / nenner)


# --- Moran's I -------------------------------------------------------------------------------


def nachbarschaft(maske: np.ndarray, umbruch: bool = True):
    """Dünn besetzte, symmetrische 0/1-Nachbarschaftsmatrix (8er-Nachbarschaft) der True-Zellen von `maske`.

    Achse 0 = Breite (kein Umbruch), Achse 1 = Länge (mit `umbruch`: letzte Spalte grenzt an die erste,
    Datumsgrenze). Rückgabe: (scipy.sparse.csr_matrix n×n, Zeilenindizes, Spaltenindizes der Zellen).
    """
    from scipy import sparse

    maske = np.asarray(maske, dtype=bool)
    ny, nx = maske.shape
    ys, xs = np.nonzero(maske)
    index = np.full(maske.shape, -1, dtype="int64")
    index[ys, xs] = np.arange(ys.size)
    zeilen, spalten = [], []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            ny_ = ys + dy
            nx_ = xs + dx
            if umbruch:
                nx_ = nx_ % nx
                innen = (ny_ >= 0) & (ny_ < ny)
            else:
                innen = (ny_ >= 0) & (ny_ < ny) & (nx_ >= 0) & (nx_ < nx)
            ziel = np.full(ys.size, -1, dtype="int64")
            ziel[innen] = index[ny_[innen], nx_[innen]]
            ok = ziel >= 0
            zeilen.append(np.flatnonzero(ok))
            spalten.append(ziel[ok])
    z = np.concatenate(zeilen) if zeilen else np.zeros(0, "int64")
    s = np.concatenate(spalten) if spalten else np.zeros(0, "int64")
    w = sparse.csr_matrix((np.ones(z.size), (z, s)), shape=(ys.size, ys.size))
    w.data[:] = 1.0  # doppelte Einträge (sehr schmale Gitter mit Umbruch) auf 1 setzen
    return w, ys, xs


def morans_i(werte: np.ndarray, w) -> dict:
    """Moran's I je Spalte von `werte` (Zellen × k), W dünn besetzt und symmetrisch (0/1).

    I = (n / S0) · (zᵀ W z) / (zᵀ z), z = Werte minus Mittel. Erwartung −1/(n−1); Varianz unter
    Normalannahme: (n² S1 − n S2 + 3 S0²) / ((n² − 1) S0²) − E². Nur als DIAGNOSE (räumliche
    Restabhängigkeit), nicht als Test mit Garantie. Zellen ohne Nachbarn zählen zu n (Standardrechnung).
    """
    x = np.asarray(werte, dtype="float64")
    if x.ndim == 1:
        x = x[:, None]
    n = x.shape[0]
    z = x - x.mean(axis=0)
    s0 = float(w.sum())
    wz = w @ z
    with np.errstate(invalid="ignore", divide="ignore"):
        i = (n / s0) * (z * wz).sum(axis=0) / (z * z).sum(axis=0)
    wsym = w + w.T
    s1 = 0.5 * float(wsym.multiply(wsym).sum())
    zeilen_summe = np.asarray(w.sum(axis=1)).ravel()
    spalten_summe = np.asarray(w.sum(axis=0)).ravel()
    s2 = float(((zeilen_summe + spalten_summe) ** 2).sum())
    e = -1.0 / (n - 1)
    var = (n * n * s1 - n * s2 + 3 * s0 * s0) / ((n * n - 1) * s0 * s0) - e * e
    return {"i": i, "erwartung": e, "varianz": var, "z": (i - e) / math.sqrt(var) if var > 0 else np.full(i.shape, np.nan), "n": n}
