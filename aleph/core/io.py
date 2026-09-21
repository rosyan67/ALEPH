"""Gemeinsamer Lade- und Speicherweg für alle Layer.

Bisher enthalten: der Speicherwächter. Jeder Ladelauf ruft `pruefe_speicher`
vor jedem Monat auf und stoppt, bevor die Festplatte voll läuft.
"""

import shutil

MIN_FREI_GB = 20  # Stopp, wenn weniger frei ist (1 GB = 1024³ Byte, wie im Finder/df)


class SpeicherZuKnapp(RuntimeError):
    """Zu wenig freier Speicherplatz: der Ladelauf wird gestoppt."""


def freier_speicher_gb(pfad=".") -> float:
    """Freier Speicherplatz auf dem Datenträger, auf dem `pfad` liegt, in GB."""
    return shutil.disk_usage(pfad).free / 1024**3


def pruefe_speicher(pfad=".", minimum_gb=MIN_FREI_GB) -> None:
    """Stoppt mit `SpeicherZuKnapp`, wenn weniger als `minimum_gb` frei sind."""
    frei = freier_speicher_gb(pfad)
    if frei < minimum_gb:
        raise SpeicherZuKnapp(
            f"Nur noch {frei:.1f} GB frei, Untergrenze ist {minimum_gb} GB. "
            "Lauf gestoppt. Bereits fertig verarbeitete Monate bleiben erhalten."
        )
