"""Künstliche Datenwürfel zum Entwickeln und Testen der Anomalieerkennung.

Der Aufbau folgt dem echten Nachtlicht-Würfel (aleph/layers/vnp46a3.py): Zeitachse,
Variablen `<feld>_mittel`, `<feld>_gueltige_pixel`, `<feld>_num`, `<feld>_aufgefuellt_pixel`
und `monat_fertig`; nicht geladene Monate sind leer (Wert NaN, Zähler 0, nicht fertig), genau
wie im echten Würfel. Die Größe des Gitters ist frei (Standard klein, damit Tests schnell laufen).

Was erzeugt wird: je Zelle ein Grundwert (lognormal, ein Teil der Zellen dunkel), eine
jahreszeitliche Schwankung (Stärke und Phase je Zelle), multiplikatives Rauschen (optional je
Zelle unterschiedlich stark; optional mit Autokorrelation AR(1) über die Monate, `ar1`) und ein zufälliger Anteil aufgefüllter Pixel (unabhängig von den Werten: die Kopplung an die Historie, die bei
echten Daten die Änderung dämpft, ist NICHT nachgebildet). Optional Trend, schwere Ränder (t3). Eingebaute
Ereignisse (`Ereignis`) verändern einen Block von Zellen in einem oder mehreren Monaten.

Nur für Entwicklung und Tests; nichts hiervon geht in Auswertungen echter Daten ein.
"""

from dataclasses import dataclass

import numpy as np
import xarray as xr

FELDER = ("mittel", "mittel_beobachtet", "gueltige_pixel", "beobachtete_pixel", "num", "aufgefuellt_pixel")


@dataclass(frozen=True)
class Ereignis:
    """Ein künstliches Ereignis: Block von Zellen, ein oder mehrere aufeinanderfolgende Monate.

    `faktor`: multiplikative Änderung des Wertes (0,3 = Rückgang auf 30 %); `zusatz`: additive
    Änderung in nW (für Zellen, die vorher dunkel waren). `aufgefuellt_anteil`: wenn gesetzt,
    Anteil aufgefüllter Pixel im Block (für Datenlage-Tests).
    """

    monat: tuple[int, int]
    zeilen: tuple[int, int]  # von, bis (bis ausgeschlossen)
    spalten: tuple[int, int]
    faktor: float = 1.0
    zusatz: float = 0.0
    dauer_monate: int = 1
    aufgefuellt_anteil: float | None = None
    gueltige_pixel: int | None = None  # gesetzt: Zahl gültiger Pixel im Block (Rand-/Küstenzellen)


def _monate(jahre: tuple[int, int]) -> list[tuple[int, int]]:
    return [(j, m) for j in range(jahre[0], jahre[1] + 1) for m in range(1, 13)]


def kuenstlicher_wuerfel(
    *,
    feld: str = "allangle",
    ny: int = 40,
    nx: int = 80,
    jahre: tuple[int, int] = (2013, 2025),
    seed: int = 0,
    saison_amplitude: float = 0.3,
    rauschen_relativ: float = 0.05,
    heterogen_sigma: float = 0.0,
    rauschen_verteilung: str = "normal",
    trend_pro_jahr: float = 0.0,
    anteil_dunkel: float = 0.3,
    helligkeit_median: float = 5.0,
    helligkeit_sigma: float = 1.1,
    aufgefuellt_mittel: float = 0.10,
    ereignisse: tuple[Ereignis, ...] = (),
    nicht_fertig: tuple[tuple[int, int], ...] = (),
    halb_geschrieben: tuple[tuple[int, int], ...] = (),
    breite_start: float = 60.0,
    ar1: float = 0.0,
) -> xr.Dataset:
    """Baut einen künstlichen Würfel mit fester Zeitachse `jahre` (Januar des ersten bis Dezember des letzten).

    `nicht_fertig`: Monate, die (wie im echten Würfel) leer und nicht fertig sind.
    `halb_geschrieben`: Monate mit Werten in den Feldern, aber `monat_fertig` = 0 (Absturz beim Schreiben).
    `ar1`: Autokorrelation des Rauschens von Monat zu Monat (0 = unabhängig, wie bisher; die Varianz
    des Rauschens bleibt gleich: e_t = ar1·e_(t-1) + sqrt(1-ar1²)·Zufall). Mit 0 sind die Zufallszahlen
    exakt dieselben wie ohne diesen Parameter (bestehende Tests bleiben gleich).
    """
    if not -1 < ar1 < 1:
        raise ValueError("ar1 muss zwischen -1 und 1 liegen.")
    rng = np.random.default_rng(seed)
    monate = _monate(jahre)
    zeit = np.array([np.datetime64(f"{j:04d}-{m:02d}-01", "ns") for j, m in monate])
    breite = breite_start - 0.125 - np.arange(ny) * 0.25
    laenge = -180 + 0.125 + np.arange(nx) * 0.25

    hell = np.exp(rng.normal(np.log(helligkeit_median), helligkeit_sigma, size=(ny, nx)))  # lognormal, Median in nW
    dunkel = rng.random((ny, nx)) < anteil_dunkel
    grund = np.where(dunkel, rng.uniform(0.0, 0.15, size=(ny, nx)), hell)
    amplitude = saison_amplitude * rng.uniform(0.5, 1.0, size=(ny, nx))
    phase = rng.uniform(0, 12, size=(ny, nx))
    streu_faktor = np.exp(heterogen_sigma * rng.standard_normal((ny, nx))) if heterogen_sigma else np.ones((ny, nx))
    p_aufgefuellt = np.clip(rng.beta(2.0, 2.0 / max(aufgefuellt_mittel, 1e-6) - 2.0, size=(ny, nx)), 0, 1) if aufgefuellt_mittel > 0 else np.zeros((ny, nx))

    n_zeit = len(monate)
    mittel = np.empty((n_zeit, ny, nx), dtype="float32")
    gueltig = np.full((n_zeit, ny, nx), 3600, dtype="int16")
    aufgefuellt = np.empty((n_zeit, ny, nx), dtype="int16")
    num = np.full((n_zeit, ny, nx), 5.0, dtype="float32")

    vorher = None
    for i, (j, m) in enumerate(monate):
        saison = 1.0 + amplitude * np.cos(2 * np.pi * (m - phase) / 12.0)
        if rauschen_verteilung == "normal":
            roh = rng.standard_normal((ny, nx))
        elif rauschen_verteilung == "t3":  # schwere Ränder (Student-t mit 3 Freiheitsgraden, auf Varianz 1 skaliert)
            roh = rng.standard_t(3, size=(ny, nx)) / np.sqrt(3.0)
        else:
            raise ValueError(f"Unbekannte Rauschverteilung: {rauschen_verteilung}")
        if ar1 and vorher is not None:
            roh = ar1 * vorher + np.sqrt(1.0 - ar1 * ar1) * roh
        vorher = roh
        rauschen = rauschen_relativ * streu_faktor * roh
        wachstum = (1.0 + trend_pro_jahr) ** (j - jahre[0])
        wert = grund * wachstum * saison * (1.0 + rauschen) + np.where(dunkel, 0.02 * rng.standard_normal((ny, nx)), 0.0)
        mittel[i] = np.clip(wert, 0.0, None)
        aufgefuellt[i] = rng.binomial(3600, p_aufgefuellt)

    for e in ereignisse:
        start = monate.index(e.monat)
        for k in range(e.dauer_monate):
            i = start + k
            block = (i, slice(*e.zeilen), slice(*e.spalten))
            mittel[block] = np.clip(mittel[block] * e.faktor + e.zusatz, 0.0, None)
            if e.aufgefuellt_anteil is not None:
                aufgefuellt[block] = int(round(e.aufgefuellt_anteil * 3600))
            if e.gueltige_pixel is not None:
                gueltig[block] = e.gueltige_pixel
                aufgefuellt[block] = np.minimum(aufgefuellt[block], e.gueltige_pixel)

    fertig = np.ones(n_zeit, dtype="int8")
    for m in nicht_fertig:
        i = monate.index(m)
        mittel[i] = np.nan
        gueltig[i] = 0
        aufgefuellt[i] = 0
        num[i] = np.nan
        fertig[i] = 0
    for m in halb_geschrieben:
        i = monate.index(m)
        fertig[i] = 0  # Werte bleiben stehen, wie nach einem Absturz vor dem Fertig-Markieren

    dims = ("zeit", "breite", "laenge")
    beobachtet = np.clip(gueltig - aufgefuellt, 0, 3600).astype("int16")
    # Für künstliche Daten sind aufgefüllte Pixel wertunabhängig verteilt,
    # daher ist das Mittel über beobachtete Pixel ≈ das Gesamt-Mittel.
    mittel_beobachtet = np.where(beobachtet > 0, mittel, np.nan).astype("float32")
    return xr.Dataset(
        {
            f"{feld}_mittel": (dims, mittel),
            f"{feld}_mittel_beobachtet": (dims, mittel_beobachtet),
            f"{feld}_gueltige_pixel": (dims, gueltig),
            f"{feld}_beobachtete_pixel": (dims, beobachtet),
            f"{feld}_num": (dims, num),
            f"{feld}_aufgefuellt_pixel": (dims, aufgefuellt),
            "monat_fertig": (("zeit",), fertig),
        },
        coords={"zeit": zeit, "breite": breite, "laenge": laenge},
    )
