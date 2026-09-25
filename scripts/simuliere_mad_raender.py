"""Simulation zur Begründung der gemeinsamen Mindest-Streuung (aleph/detect/anomalie.py).

Untersucht bei reinem Rauschen (keine Anomalie), wie oft die robuste Abweichung
T = (x - Median) / (max(1,4826 * MAD, Mindest-Streuung) * sqrt(1 + pi/(2n))) eine Schwelle überschreitet,
verglichen mit der Normalverteilung. Zwei Fälle: alle Zellen gleich stark verrauscht, und Zellen mit
lognormal verteilter Streuung (Sigma 0,5 bzw. 1,0). Mindest-Streuung = Perzentil der MAD-Streuung aller
Zellen derselben Simulation (wie im Verfahren, nur aus der Basislinie geschätzt).

Nur numpy. Aufruf:  .venv/bin/python scripts/simuliere_mad_raender.py [Zellen je Lauf] [Läufe]
Die Ergebnisse stehen im LOG.md (Eintrag 2026-09-24, Etappe 3) und im Modulkopf von anomalie.py.
Dies ist Entwicklungswerkzeug, nicht Teil der Pipeline. Der Zufallszahlen-Startwert ist fest (7).
"""

import sys
from math import erfc, sqrt

import numpy as np

FAKTOR_MEDIAN = np.pi / 2.0  # wie in anomalie.py: sqrt(1 + pi/(2n))


def normal_zweiseitig(t: float) -> float:
    return erfc(t / sqrt(2))


def lauf(n: int, heterogen: float, perzentil: float | None, zellen: int, laeufe: int, rng) -> dict:
    zaehler = {4: 0, 5: 0, 6: 0, 8: 0, 12: 0}
    gesamt = 0
    for _ in range(laeufe):
        sigma = np.exp(heterogen * rng.standard_normal(zellen))[:, None]
        basis = sigma * rng.standard_normal((zellen, n))
        neu = sigma[:, 0] * rng.standard_normal(zellen)
        med = np.median(basis, axis=1)
        streu = 1.4826 * np.median(np.abs(basis - med[:, None]), axis=1)
        if perzentil is not None:
            streu = np.maximum(streu, np.percentile(streu, perzentil))
        t = np.abs(neu - med) / (streu * np.sqrt(1 + FAKTOR_MEDIAN / n))
        gesamt += zellen
        for schwelle in zaehler:
            zaehler[schwelle] += int((t >= schwelle).sum())
    return {schwelle: anzahl / gesamt for schwelle, anzahl in zaehler.items()}


def main() -> None:
    zellen = int(sys.argv[1]) if len(sys.argv) > 1 else 3_000_000
    laeufe = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    rng = np.random.default_rng(7)
    print("Normalverteilung (perfekt): " + "  ".join(f"T>={t}: {normal_zweiseitig(t):.1e}" for t in (4, 5, 6, 8, 12)))
    for heterogen in (0.0, 0.5, 1.0):
        for n in (5, 6, 8, 12):
            for perzentil in (None, 75.0):
                r = lauf(n, heterogen, perzentil, zellen, laeufe, rng)
                name = "nur MAD" if perzentil is None else f"Mindest-Streuung {int(perzentil)}. Perzentil"
                print(f"Streuung der Zellen lognormal Sigma={heterogen} n={n:2d} {name:34s} " + "  ".join(f"T>={t}: {r[t]:.1e}" for t in r))


if __name__ == "__main__":
    main()
