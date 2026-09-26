"""Regionen als feste VNP46A3-Kachellisten (Vorrang beim Laden, Auftrag 2026-09-26).

Eine Region ist eine feste Liste von Kachelpositionen (hXXvYY) aus der
Referenzliste `vnp46a3_kachelpositionen.txt`. Sie wird NICHT nach Augenmaß
festgelegt, sondern abgeleitet:

- Zell-Länder-Zuordnung `laender/zell_einheiten/` (Flächenanteil je 0,25°-Zelle
  und Einheit, gebaut aus Natural Earth 5.1.1, UN M49, sondereinheiten.yaml),
- UN-Liste M49 (`aleph/layers/un_m49.py`, Spalte „Region Name“),
- Regel: Eine Kachel gehört zur Region, wenn mindestens eine ihrer
  40 × 40 Zellen einen Flächenanteil > 0 einer Einheit hat, deren
  übergeordneter M49-Eintrag in einer der Regionen liegt.

Bekannte Folgen der Regel (stehen auch im Kopf der Listen-Datei):
- Einheiten ohne M49-Eintrag („unklar“) zählen nicht. Geprüft: Ihre Zellen
  außerhalb der Regions-Kacheln liegen alle in Amerika, Ozeanien oder der
  Antarktis (z. B. Süd-Georgien, Guantánamo, Hans-Insel).
- Überseegebiete, die Natural Earth mit dem Mutterstaat zusammenfasst (z. B.
  Französisch-Guayana in Frankreich, M49-Region Europa), ziehen einzelne
  Kacheln in Amerika oder Ozeanien mit in die Region („gemischte Kacheln“).
  Das verlängert Stufe 1 etwas, verliert aber nichts.
- Kacheln nördlich 80° N (Zeile v00) stehen nicht in der Referenzliste
  (NASA liefert sie nicht) und damit auch nicht in der Region.

Aufruf zum (Neu-)Erzeugen der Liste (liest nur, schreibt nur die Listen-Datei):
    .venv/bin/python -m aleph.layers.vnp46a3_regionen
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

AFRIKA_EUROPA_ASIEN = "afrika_europa_asien"
REGIONEN = {AFRIKA_EUROPA_ASIEN: ("Africa", "Europe", "Asia")}
REGION_TEXT = {AFRIKA_EUROPA_ASIEN: "Afrika-Europa-Asien"}
_ORDNER = Path(__file__).parent
ZELLEN_PRO_KACHEL = 40  # 10° / 0,25°


class RegionFehler(RuntimeError):
    """Die Kachelliste einer Region fehlt, ist inkonsistent oder passt nicht zur Referenzliste."""


def listen_pfad(region: str) -> Path:
    if region not in REGIONEN:
        raise RegionFehler(f"Unbekannte Region '{region}'. Bekannt: {', '.join(REGIONEN)}.")
    return _ORDNER / f"vnp46a3_kacheln_{region}.txt"


def kachel_von_zelle(zeile: int, spalte: int) -> str:
    """Kachelposition einer 0,25°-Zelle (Zeile 0 = Nordrand 90°, Spalte 0 = Westrand −180°)."""
    return f"h{spalte // ZELLEN_PRO_KACHEL:02d}v{zeile // ZELLEN_PRO_KACHEL:02d}"


def leite_ab(region: str) -> dict:
    """Leitet die Kachelliste einer Region ab (liest SSD: Zell-Zuordnung und M49).

    Rückgabe: dict mit `kacheln` (sortiert, nur Referenzpositionen), `ausserhalb_referenz`,
    `gemischt` (Kacheln mit Land der Region UND anderer Regionen), `ohne_region_ausserhalb`
    (Einheiten ohne M49-Region mit Zellen in Kacheln außerhalb der Region) und `quellen`.
    """
    import json

    import pandas as pd

    from aleph.core import io
    from aleph.layers import un_m49, vnp46a3

    ziel_regionen = REGIONEN[region]
    ordner = io.aleph_data_dir() / "laender" / "zell_einheiten"
    manifest = json.loads((ordner / "manifest.json").read_text(encoding="utf-8"))
    einheiten = pd.read_parquet(ordner / "einheiten.parquet", columns=["einheit_id", "name", "un_m49"])
    zuordnung = pd.read_parquet(ordner / "zuordnung.parquet", columns=["zeile", "spalte", "einheit_id", "anteil"])
    m49, m49_manifest = un_m49.lade()
    region_je_m49 = dict(zip(m49["m49"], m49["region"]))

    z = zuordnung[zuordnung["anteil"] > 0].merge(einheiten, on="einheit_id", how="left")
    if z["name"].isna().any():
        raise RegionFehler("Zell-Zuordnung verweist auf Einheiten, die in der Einheitentabelle fehlen.")
    z["region"] = z["un_m49"].map(region_je_m49)
    z["kachel"] = [kachel_von_zelle(r, s) for r, s in zip(z["zeile"], z["spalte"])]

    in_region = set(z.loc[z["region"].isin(ziel_regionen), "kachel"])
    referenz = vnp46a3.lies_referenz_positionen()
    andere = set(z.loc[z["region"].notna() & ~z["region"].isin(ziel_regionen) & (z["region"] != ""), "kachel"])
    ohne = z[z["region"].isna() | (z["region"] == "")]
    return {
        "kacheln": sorted(in_region & referenz),
        "ausserhalb_referenz": sorted(in_region - referenz),
        "gemischt": sorted(in_region & andere & referenz),
        "ohne_region_ausserhalb": sorted(set(ohne.loc[~ohne["kachel"].isin(in_region), "name"])),
        "referenz_anzahl": len(referenz),
        "quellen": {
            "zell_einheiten_erstellt": manifest.get("erstellt_utc"),
            "zell_einheiten_sha256_zuordnung": manifest["dateien"]["zuordnung.parquet"],
            "m49_abruf": m49_manifest.get("ordner"),
        },
    }


def schreibe_liste(region: str, ergebnis: dict | None = None) -> Path:
    """Schreibt die Kachelliste mit Kopf (Herkunft, Datum, Regel, Anzahl, Besonderheiten)."""
    ergebnis = ergebnis or leite_ab(region)
    q = ergebnis["quellen"]
    kopf = [
        f"# VNP46A3-Kacheln der Region {REGION_TEXT[region]} ({region})",
        f"# Erzeugt: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC mit aleph/layers/vnp46a3_regionen.py",
        f"# Regel: Kachel der Referenzliste (vnp46a3_kachelpositionen.txt, {ergebnis['referenz_anzahl']} Positionen) mit",
        "#   mindestens einer 0,25°-Zelle, deren Flächenanteil > 0 einer Einheit gehört, deren",
        f"#   übergeordneter UN-M49-Eintrag in der Region {', '.join(REGIONEN[region])} liegt.",
        f"# Quellen: laender/zell_einheiten (erstellt {q['zell_einheiten_erstellt']}, zuordnung.parquet SHA-256",
        f"#   {q['zell_einheiten_sha256_zuordnung']}); UN M49 Abruf {q['m49_abruf']}.",
        f"# Anzahl: {len(ergebnis['kacheln'])}",
        "# Nicht in der Referenzliste (NASA liefert sie nicht, deshalb nicht enthalten): "
        + (", ".join(ergebnis["ausserhalb_referenz"]) or "keine"),
        "# Gemischte Kacheln (auch Land anderer Regionen, meist Überseegebiete, die Natural Earth dem",
        "#   Mutterstaat zuordnet): " + (", ".join(ergebnis["gemischt"]) or "keine"),
        "# Einheiten ohne M49-Region mit Zellen außerhalb dieser Kacheln: "
        + (", ".join(ergebnis["ohne_region_ausserhalb"]) or "keine"),
    ]
    pfad = listen_pfad(region)
    pfad.write_text("\n".join(kopf + ergebnis["kacheln"]) + "\n", encoding="utf-8")
    return pfad


def lies_region(region: str) -> set[str]:
    """Liest die Kachelliste einer Region und prüft sie (Anzahl im Kopf, nur Referenzpositionen)."""
    from aleph.layers import vnp46a3

    pfad = listen_pfad(region)
    if not pfad.exists():
        raise RegionFehler(f"Kachelliste {pfad.name} fehlt. Mit `python -m aleph.layers.vnp46a3_regionen` erzeugen.")
    anzahl_kopf = None
    kacheln: list[str] = []
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if zeile.startswith("# Anzahl:"):
            anzahl_kopf = int(zeile.split(":", 1)[1])
        elif zeile and not zeile.startswith("#"):
            kacheln.append(zeile)
    if anzahl_kopf is None or anzahl_kopf != len(kacheln) or len(set(kacheln)) != len(kacheln):
        raise RegionFehler(f"{pfad.name}: Anzahl im Kopf ({anzahl_kopf}) passt nicht zu {len(kacheln)} Einträgen oder Doppelte.")
    fremd = sorted(set(kacheln) - vnp46a3.lies_referenz_positionen())
    if fremd:
        raise RegionFehler(f"{pfad.name}: Positionen außerhalb der Referenzliste: {', '.join(fremd)}.")
    return set(kacheln)


def pruefsumme(positionen: set[str]) -> str:
    """SHA-256 über die sortierten Positionen (unabhängig vom Dateikopf, z. B. dem Erzeugungsdatum)."""
    import hashlib

    return hashlib.sha256("\n".join(sorted(positionen)).encode("ascii")).hexdigest()


def zellmaske(positionen: set[str], breite: int = 720, laenge: int = 1440) -> np.ndarray:
    """Bool-Maske (Zeile 0 = Nordrand) der 0,25°-Zellen, die in den genannten Kacheln liegen."""
    maske = np.zeros((breite, laenge), dtype=bool)
    for p in positionen:
        h, v = int(p[1:3]), int(p[4:6])
        maske[v * ZELLEN_PRO_KACHEL:(v + 1) * ZELLEN_PRO_KACHEL, h * ZELLEN_PRO_KACHEL:(h + 1) * ZELLEN_PRO_KACHEL] = True
    return maske


def main() -> int:
    ergebnis = leite_ab(AFRIKA_EUROPA_ASIEN)
    pfad = schreibe_liste(AFRIKA_EUROPA_ASIEN, ergebnis)
    print(f"{pfad.name}: {len(ergebnis['kacheln'])} Kacheln")
    print(f"  nicht in Referenzliste: {', '.join(ergebnis['ausserhalb_referenz']) or 'keine'}")
    print(f"  gemischt: {', '.join(ergebnis['gemischt']) or 'keine'}")
    print(f"  ohne M49-Region außerhalb: {', '.join(ergebnis['ohne_region_ausserhalb']) or 'keine'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
