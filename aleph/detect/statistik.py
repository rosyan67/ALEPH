"""Kleine statistische Bausteine für die Anomalieerkennung, nur mit numpy und math.

Warum nicht scipy: Es ist nicht Teil der festgelegten Umgebung (requirements.txt),
und ein Nachinstallieren würde die Python-Umgebung des laufenden Nachtlicht-Laufs
verändern. Gebraucht werden nur die zweiseitige Normalverteilungs-Wahrscheinlichkeit und
das Benjamini-Hochberg-Verfahren; beides ist kurz und wird in
tests/test_detect_statistik.py an bekannten Werten geprüft.
"""

import math

import numpy as np

_ERFC = np.frompyfunc(math.erfc, 1, 1)


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
