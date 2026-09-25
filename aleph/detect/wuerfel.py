"""Lesefunktion für Datenwürfel: liefert NUR Monate, die als fertig markiert sind.

Hintergrund (LOG.md, Prüfung durch statistik-pruefer 2026-09-22, Auflage A1): Im Würfel
sind „Monat noch nicht geladen" und „keine Daten" in den Wert- und Zählvariablen gleich
kodiert (Wert NaN, Zähler 0). Nur die Variable `monat_fertig` (0/1 je Monat) trennt sie.
Wer direkt aus dem Würfel liest, könnte einen nicht geladenen Monat für „überall dunkel"
oder „Datenlage unzureichend" halten und einen Rückgang melden, der keiner ist.

Regeln dieser Funktionen:
- Ein Monat, der nicht als fertig markiert ist, wird NIE geliefert, auch wenn schon Werte
  in seinen Feldern stehen (Absturz mitten im Schreiben).
- Wird ein Monat ausdrücklich verlangt und ist nicht fertig, gibt es einen Fehler
  (`MonatNichtFertig`), nicht leere Daten.
- Ein Würfel ohne `monat_fertig` wird abgelehnt (alter Aufbau).

Die Funktionen kennen keinen Layer: Sie brauchen nur eine Zeitachse `zeit`, die Variable
`monat_fertig` und die gewünschten Variablen. Sie arbeiten mit einem Pfad zu einem
Zarr-Würfel oder mit einem schon geöffneten `xarray.Dataset` (für Tests).
"""

from pathlib import Path

import numpy as np
import xarray as xr

FERTIG_VARIABLE = "monat_fertig"  # muss zu aleph.layers.vnp46a3.FERTIG_VARIABLE passen (Test prüft das)


class MonatNichtFertig(RuntimeError):
    """Ein verlangter Monat ist im Würfel nicht als fertig markiert (nicht geladen)."""


class WuerfelFormatFehler(RuntimeError):
    """Der Würfel hat nicht den erwarteten Aufbau (Zeitachse oder `monat_fertig` fehlt)."""


def _oeffne(wuerfel) -> tuple[xr.Dataset, bool]:
    """Gibt (Dataset, muss_geschlossen_werden) zurück."""
    if isinstance(wuerfel, xr.Dataset):
        return wuerfel, False
    pfad = Path(wuerfel)
    if not pfad.exists():
        raise WuerfelFormatFehler(f"Würfel {pfad.name} nicht gefunden.")
    return xr.open_zarr(pfad, chunks=None), True


def _pruefe_format(ds: xr.Dataset) -> None:
    if "zeit" not in ds.coords and "zeit" not in ds.dims:
        raise WuerfelFormatFehler("Der Würfel hat keine Zeitachse `zeit`.")
    if FERTIG_VARIABLE not in ds:
        raise WuerfelFormatFehler(
            f"Der Würfel hat keine Variable `{FERTIG_VARIABLE}` (alter Aufbau?). "
            "Ohne sie ist nicht zu unterscheiden, ob ein Monat geladen ist. Nichts wird gelesen."
        )


def _als_monat(zeit: np.datetime64) -> tuple[int, int]:
    datum = np.datetime64(zeit, "M").astype(object)
    return datum.year, datum.month


def fertige_monate(wuerfel) -> list[tuple[int, int]]:
    """Alle Monate mit `monat_fertig == 1`, zeitlich aufsteigend, als (Jahr, Monat)."""
    ds, schliessen = _oeffne(wuerfel)
    try:
        _pruefe_format(ds)
        zeiten = ds["zeit"].values
        fertig = ds[FERTIG_VARIABLE].values
    finally:
        if schliessen:
            ds.close()
    monate = [_als_monat(z) for z, f in zip(zeiten, fertig) if int(f) == 1]
    return sorted(monate)


def zeitachse_monate(wuerfel) -> list[tuple[int, int]]:
    """Alle Monate der Zeitachse, fertig oder nicht (zum Erkennen fehlender Monate)."""
    ds, schliessen = _oeffne(wuerfel)
    try:
        _pruefe_format(ds)
        zeiten = ds["zeit"].values
    finally:
        if schliessen:
            ds.close()
    return [_als_monat(z) for z in zeiten]


def gitter(wuerfel) -> tuple[np.ndarray, np.ndarray]:
    """Breiten- und Längenkoordinaten des Würfels (für leere Ergebnisse nicht geladener Monate)."""
    ds, schliessen = _oeffne(wuerfel)
    try:
        _pruefe_format(ds)
        return ds["breite"].values, ds["laenge"].values
    finally:
        if schliessen:
            ds.close()


def lies_monate(wuerfel, monate: list[tuple[int, int]], variablen: list[str]) -> xr.Dataset:
    """Liest genau die verlangten Monate (in der verlangten Reihenfolge) und Variablen.

    Ist auch nur ein Monat nicht fertig oder nicht auf der Zeitachse, gibt es
    `MonatNichtFertig` mit der Liste der betroffenen Monate; es wird nichts geliefert.
    """
    ds, schliessen = _oeffne(wuerfel)
    try:
        _pruefe_format(ds)
        fehlend_variablen = [v for v in variablen if v not in ds]
        if fehlend_variablen:
            raise WuerfelFormatFehler(f"Variablen fehlen im Würfel: {', '.join(fehlend_variablen)}.")
        achse = [_als_monat(z) for z in ds["zeit"].values]
        fertig = ds[FERTIG_VARIABLE].values
        position = {m: i for i, m in enumerate(achse)}
        nicht_fertig = [m for m in monate if m not in position or int(fertig[position[m]]) != 1]
        if nicht_fertig:
            raise MonatNichtFertig(
                "Diese Monate sind im Würfel nicht als fertig markiert (nicht geladen oder unvollständig) "
                "und werden nicht geliefert: " + ", ".join(f"{j:04d}-{mo:02d}" for j, mo in nicht_fertig) + ". "
                "Ein nicht geladener Monat ist nicht dasselbe wie „keine Daten“."
            )
        indizes = [position[m] for m in monate]
        auswahl = ds[variablen].isel(zeit=indizes).load()
    finally:
        if schliessen:
            ds.close()
    return auswahl


def lies_fertige_monate(
    wuerfel,
    variablen: list[str],
    von: tuple[int, int] | None = None,
    bis: tuple[int, int] | None = None,
) -> xr.Dataset:
    """Liest alle fertigen Monate (optional zwischen `von` und `bis`, beide eingeschlossen).

    Nicht fertige Monate fehlen in der Antwort (die Zeitachse ist lückenhaft, aber ehrlich).
    Gibt es keinen fertigen Monat im Bereich, kommt ein leeres Dataset mit `zeit` der Länge 0.
    """
    monate = [m for m in fertige_monate(wuerfel) if (von is None or m >= von) and (bis is None or m <= bis)]
    if not monate:
        ds, schliessen = _oeffne(wuerfel)
        try:
            return ds[variablen].isel(zeit=[]).load()
        finally:
            if schliessen:
                ds.close()
    return lies_monate(wuerfel, monate, variablen)
