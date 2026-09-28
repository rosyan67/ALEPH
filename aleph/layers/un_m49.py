"""UN-Länder- und Gebietsliste „Standard country or area codes for statistical use (M49)“.

Oberste Zuordnungsebene für Länder in ALEPH (Anweisung vom 2026-09-26, Punkt 7a): ALEPH trifft keine
eigenen Souveränitätsentscheidungen, sondern folgt der Sicht der Vereinten Nationen. Grundlage ist diese
Liste der UN-Statistikabteilung (UNSD). Steckbrief: docs/sources/un_m49.md.

Nutzt denselben Lade- und Speicherweg wie alle Quellen (aleph/core/io.py: SSD-Pfad, Speicherwächter;
Hilfsordner, Manifest mit Prüfsumme zuletzt, erst dann umbenennen). Geladen werden zwei Seiten
unverändert (HTML): die Übersichtstabelle und die Hauptseite (mit „Questions & Answers“, dort stehen die
Hinweise zu Kosovo und Taiwan). Die englische Tabelle wird ohne Zusatzbibliothek gelesen.

Kein Erkennungs-Layer: liefert nur die Liste (Code, Name, ISO-alpha3) für aleph/layers/zell_einheiten.py.
"""

import hashlib
import html
import json
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from aleph.core import io

SEITEN = {
    "uebersicht": "https://unstats.un.org/unsd/methodology/m49/overview/",
    "hauptseite": "https://unstats.un.org/unsd/methodology/m49/",
}
# Eigene Zählung am 2026-09-25 22:30 UTC (Abruf der Übersicht): 248 Einträge in der englischen Tabelle.
# Die Seite nennt selbst keine Zahl. Eine andere Zahl bricht ab (Liste geändert, erst prüfen).
ANZAHL_GEMESSEN = 248
# Netzwerkregel (CLAUDE.md): Zeitlimit je Anfrage und Wiederholung mit wachsenden Pausen
# (5, 10, 20 s; zusammen 35 s). Das reicht für kurze Störungen; eine längere Störung soll
# mit klarer Meldung abbrechen statt still zu warten. Jede Wiederholung wird gemeldet.
TIMEOUT_SEKUNDEN = 120  # eine HTML-Seite; großzügig, weil der UN-Server langsam sein kann
MAX_VERSUCHE = 4
WARTEZEIT_BASIS_SEKUNDEN = 5
ORDNER_MUSTER = re.compile(r"^\d{8}T\d{6}Z$")
SPALTEN = {"Country or Area": "name", "M49 Code": "m49", "ISO-alpha3 Code": "iso3", "Region Name": "region", "Sub-region Name": "subregion"}

META = {
    "name": "UN M49 (Standard country or area codes for statistical use)",
    "quelle": "United Nations Statistics Division, " + SEITEN["uebersicht"],
    "zugang": "frei, ohne Konto",
    "rolle": "oberste Ebene der Länderzuordnung (UN-Sicht), kein Erkennungs-Layer",
    "vorbehalt_der_quelle": (
        "Wörtlich auf der Hauptseite: „The designations employed and the presentation of material at this site do not "
        "imply the expression of any opinion whatsoever on the part of the Secretariat of the United Nations concerning "
        "the legal status of any country, territory, city or area or of its authorities, or concerning the delimitation "
        "of its frontiers or boundaries.“ M49 enthält keine Grenzlinien."
    ),
}


class M49Fehler(RuntimeError):
    """Abruf oder Inhalt stimmt nicht: Abbruch, es gibt keinen Ersatz."""


def _hole(url):
    letzter = None
    for versuch in range(1, MAX_VERSUCHE + 1):
        try:
            antwort = requests.get(url, timeout=TIMEOUT_SEKUNDEN, headers={"User-Agent": "Mozilla/5.0 (ALEPH)"})
            if 400 <= antwort.status_code < 500 and antwort.status_code != 429:
                raise M49Fehler(f"UNSD lehnt den Abruf ab (HTTP {antwort.status_code}): {url}")
            antwort.raise_for_status()
            return antwort.content
        except M49Fehler:
            raise
        except requests.RequestException as fehler:
            letzter = fehler
            if versuch < MAX_VERSUCHE:
                pause = WARTEZEIT_BASIS_SEKUNDEN * 2 ** (versuch - 1)
                print(f"UN M49: Versuch {versuch}/{MAX_VERSUCHE} gescheitert ({type(fehler).__name__}), "
                      f"neuer Versuch in {pause} s: {url}", file=sys.stderr, flush=True)
                time.sleep(pause)
    raise M49Fehler(f"Abruf gescheitert nach {MAX_VERSUCHE} Versuchen: {url} ({letzter})")


def lies_tabelle(roh_html):
    """Englische Tabelle (id downloadTableEN) als DataFrame mit Spalten name, m49 (Text, 3 Ziffern), iso3, region, subregion."""
    text = roh_html.decode("utf-8") if isinstance(roh_html, bytes) else roh_html
    try:
        anfang = text.index('id = "downloadTableEN"')
    except ValueError as fehler:
        raise M49Fehler("Englische M49-Tabelle nicht gefunden (Seitenaufbau geändert?).") from fehler
    tabelle = text[anfang : text.index("</table>", anfang)]
    zeilen = re.findall(r"<tr.*?</tr>", tabelle, re.S)

    def zellen(zeile):
        return [html.unescape(re.sub(r"<[^>]+>", "", z)).strip() for z in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", zeile, re.S)]

    kopf = zellen(zeilen[0])
    fehlend = [s for s in SPALTEN if s not in kopf]
    if fehlend:
        raise M49Fehler(f"Spalten fehlen in der M49-Tabelle: {fehlend}")
    daten = pd.DataFrame([dict(zip(kopf, zellen(z))) for z in zeilen[1:]])
    daten = daten[list(SPALTEN)].rename(columns=SPALTEN)
    if not daten["m49"].str.fullmatch(r"\d{3}").all():
        raise M49Fehler("M49-Codes sind nicht alle dreistellig.")
    if daten["m49"].duplicated().any():
        raise M49Fehler("M49-Codes sind nicht eindeutig.")
    return daten.reset_index(drop=True)


def basis():
    return io.rohdaten_pfad("un_m49")


def download(abrufzeit=None):
    """Lädt beide Seiten nach raw/un_m49/<Abrufzeitpunkt>/ (Manifest zuletzt). Liefert den Ordner."""
    io.pruefe_speicher()
    abrufzeit = abrufzeit or datetime.now(timezone.utc)
    name = abrufzeit.strftime("%Y%m%dT%H%M%SZ")
    ziel = basis() / name
    hilfs = ziel.with_name(name + ".tmp")
    if ziel.exists() or hilfs.exists():
        raise M49Fehler(f"Abruf-Ordner {name} existiert schon; es wird nichts überschrieben.")
    hilfs.mkdir(parents=True)
    try:
        dateien = {}
        for schluessel, url in SEITEN.items():
            inhalt = _hole(url)
            datei = f"{schluessel}.html"
            (hilfs / datei).write_bytes(inhalt)
            dateien[schluessel] = {"url": url, "datei": datei, "bytes": len(inhalt), "sha256": hashlib.sha256(inhalt).hexdigest()}
        tabelle = lies_tabelle((hilfs / "uebersicht.html").read_bytes())
        if len(tabelle) != ANZAHL_GEMESSEN:
            raise M49Fehler(f"M49-Tabelle hat {len(tabelle)} Einträge, bei der Prüfung am 2026-09-25 waren es {ANZAHL_GEMESSEN}.")
        manifest = {"abruf_utc": abrufzeit.strftime("%Y-%m-%dT%H:%M:%SZ"), "seiten": dateien, "anzahl_eintraege": len(tabelle)}
        (hilfs / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    except BaseException:
        shutil.rmtree(hilfs, ignore_errors=True)
        raise
    hilfs.rename(ziel)
    return ziel


def letzter_abruf():
    b = basis()
    if not b.is_dir():
        return None
    fertig = sorted(o for o in b.iterdir() if o.is_dir() and ORDNER_MUSTER.match(o.name) and (o / "manifest.json").is_file())
    return fertig[-1] if fertig else None


def lade(abruf_ordner=None):
    """Liefert (Tabelle, Manifest) des (neuesten) Abrufs; prüft die Prüfsummen."""
    abruf_ordner = Path(abruf_ordner) if abruf_ordner else letzter_abruf()
    if abruf_ordner is None:
        raise M49Fehler("M49 ist nicht geladen. Zuerst download() ausführen.")
    manifest = json.loads((abruf_ordner / "manifest.json").read_text(encoding="utf-8"))
    for eintrag in manifest["seiten"].values():
        if hashlib.sha256((abruf_ordner / eintrag["datei"]).read_bytes()).hexdigest() != eintrag["sha256"]:
            raise M49Fehler(f"Prüfsumme von {eintrag['datei']} stimmt nicht mit dem Manifest überein.")
    tabelle = lies_tabelle((abruf_ordner / "uebersicht.html").read_bytes())
    if len(tabelle) != manifest["anzahl_eintraege"]:
        raise M49Fehler("Tabelle passt nicht zum Manifest.")
    manifest["ordner"] = abruf_ordner.name
    return tabelle, manifest


def hauptseite_text(abruf_ordner=None):
    """Text der Hauptseite (ohne HTML), um Belegstellen (Questions & Answers) im geladenen Original nachzuprüfen."""
    abruf_ordner = Path(abruf_ordner) if abruf_ordner else letzter_abruf()
    roh = (abruf_ordner / "hauptseite.html").read_text(encoding="utf-8", errors="replace")
    roh = re.sub(r"<script.*?</script>|<style.*?</style>", "", roh, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", roh)))


def main():
    ziel = download()
    tabelle, _ = lade(ziel)
    print(f"UN M49 geladen: raw/un_m49/{ziel.name} ({len(tabelle)} Einträge)")


if __name__ == "__main__":
    main()
