"""Erste Auswertung Nachtlicht × reales BIP: Querschnitt über Länder, ein Jahr (2018, Gegenprobe 2019).

Evidenzstufe: statistische Assoziation (Querschnitt, ein Jahr, Afrika-Europa-Asien). KEIN Beleg für Ursache
und Wirkung, keine Prüfung des Theorie-Eintrags `theories/nachtlicht-wirtschaft.yaml` (dieser verlangt ein Panel
mit Länder- und Jahres-Effekten, also Veränderung innerhalb eines Landes; hier wird zwischen Ländern verglichen).

Auftrag 2026-09-28 (Teil 3b). Regeln sind VOR der ersten Rechnung festgelegt und werden nicht an Ergebnisse
angepasst. Wo der Auftrag eine Größe nicht genau festlegt, steht hier die eigene Festlegung (markiert „F“):

1. Jahreswert je Zelle
   - „guter Monat“: Zelle gültig nach dem Verknüpfungsgerüst (`zellen_klassen`: gültiger Pixel vorhanden,
     mindestens 50 % der Pixel beobachtet, Mittel endlich) UND kein Schnee-Verdacht nach der bestehenden Regel
     (`aleph/detect/schnee.py`, SchneeRegel() mit Standardwerten).
   - Jahreswert A = Mittel der Lichtdichte (Mittel beobachteter Pixel × gültige Pixel / 3600, wie im Gerüst)
     über die guten Monate; nur bei mindestens 6 guten Monaten, sonst „nicht bestimmbar“.
   - F: „wenige gute Monate“ = 6 bis 8 gute Monate (weniger als drei Viertel des Jahres).
   - Zellen mit Mitte nördlich von 65° N werden gekennzeichnet (Anteil des Landeslichts aus diesen Zellen).
2. Verteilung einer gemischten Zelle nach Flächenanteil wie im Gerüst („normiert“: Licht × Anteil des Landes an
   der Landfläche der Zelle; Zellen mit weniger als 5 % Land werden nicht verteilt, s_min 0,05). Sicht „so wie die
   Weltbank zählt“ mit unklaren Gebieten (Standard des Gerüsts).
   Gegenrechnung „nur reine Zellen“: Lichtsumme nur aus Zellen, deren Land ganz zu diesem Land gehört.
   F: „ganz“ = Anteil des Landes an der Landfläche der Zelle mindestens 99,9 % (Rundung der Flächen).
3. Ausschluss der Länder, deren Weltbank-Gebiet laut `berichte/2026-09-26_weltbank-gebiete.md` abweicht
   (Kurzfassung: Georgien, Moldau, Tansania, Marokko, Zypern). Gelesen aus `sondereinheiten.yaml`
   (`weltbank_laender`, gebiet „abweichend“) und gegen diese Liste aus dem Bericht geprüft: weichen sie ab,
   bricht die Rechnung ab.
4. Reinheit R = Anteil des Landeslichts aus reinen Zellen (Festlegung „ganz“ wie in 2). Ausschluss bei R < 0,5;
   Gegenrechnungen mit 0,3 und 0,7.
5. Mindestabdeckung nach Licht: A-Licht / (A-Licht + geschätztes Licht der Zellen ohne Jahreswert) ≥ 0,9.
   F: Schätzwert einer Zelle ohne Jahreswert = Mittel der Lichtdichte über ALLE Monate des Jahres, in denen sie
   überhaupt einen gültigen Mittelwert hat (auch unter 50 % beobachtet, auch mit Schnee-Verdacht). Er dient nur
   der Gewichtung, nie der Summe. Zellen ganz ohne Messwert im Jahr haben keinen Schätzwert; ihre Fläche wird
   ausgewiesen („Fläche ohne jede Messung“).
6. Länder, bei denen mehr als ein Drittel des Lichts aus Zellen mit wenigen guten Monaten stammt: drin lassen,
   kennzeichnen; Gegenrechnung ohne diese Länder.
7. BIP: NY.GDP.MKTP.KD (konstante US-Dollar, Basisjahr 2015) desselben Jahres aus der ALEPH-Weltbank-Tabelle.
   Nur Länder, die in allen 12 Monaten des Jahres vollständig geladen sind (keine Zelle des Landes „noch nicht
   geladen“; die Polkappen ohne NASA-Kachel zählen wie auf dem Globus als „keine Daten“, nicht als „nicht geladen“).
   Nachtrag 2026-09-28 nach dem ersten Lauf (Umsetzungsfehler, keine Schwelle geändert): Zusätzlich muss das Land
   zur Region gehören. Sonst liefen Karibikstaaten mit, deren Kacheln wegen der französischen Antillen zufällig
   geladen sind. Region eines Weltbank-Landes = M49-Region (UN) seiner Einheiten, nach Fläche überwiegend; derselbe
   Weg wie bei der Kachelliste der Region (`aleph/layers/vnp46a3_regionen.py`, `leite_ab`).

Rechnung: y = ln(Jahres-Lichtsumme), x = ln(reales BIP); gewöhnliche kleinste Quadrate; Steigung mit 95-%-Bereich
aus einem Bootstrap über Länder (Paare ziehen, 2000 Wiederholungen, fester Startwert, Perzentile), R², Zahl der
Länder. Länder mit Lichtsumme 0 können nicht logarithmiert werden und werden mit Grund ausgeschlossen.
Abweichung von der Linie = Rest in ln(Licht); Faktor exp(Rest) = „so viel mal mehr/weniger Licht als die Linie“.

Gasfackeln: benannt, nicht herausgerechnet. Grundlage ist NUR die frühere Plausibilitätsprüfung
(`berichte/2026-09-26_statistik-geruest.md`: großer Lichtanteil aus Fördergebieten bei Irak, Nigeria, Algerien).
Nicht an einer Fackel-Datenbank geprüft.

Literaturvergleich: entfällt. Die Quellen im Theorie-Eintrag sind nur mit `verifiziert_umfang: metadaten` geprüft,
und sie meinen eine andere Größe (BIP auf Licht, Panel mit festen Effekten).

Zeiträume: nur 2013–2022 erlaubt (2023–2025 gesperrt); gerechnet wird 2018 und 2019.

Aufruf: python -m aleph.link.nachtlicht_bip_querschnitt   (schreibt auswertungen/nachtlicht_bip_querschnitt/ auf der SSD)
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from aleph.core import io
from aleph.detect.schnee import SchneeRegel, schnee_verdacht
from aleph.link.nachtlicht_einheiten import VerknuepfungsEinstellungen, zellen_klassen

VERSION = "0.1.0"
FELD = "allangle"  # Standardfeld des Würfels und des Verknüpfungsgerüsts
REGION = "afrika_europa_asien"
REGIONEN_M49 = ("Africa", "Europe", "Asia")
GESPERRT_AB_JAHR = 2023
JAHRE = (2018, 2019)
AUSGABE_ORDNER = ("auswertungen", "nachtlicht_bip_querschnitt")
BIP_INDIKATOR = "NY.GDP.MKTP.KD"

# Liste aus berichte/2026-09-26_weltbank-gebiete.md, Kurzfassung „Klar belegt, Gebiet passt nicht zur Grenzdatei“
# (Georgien, Moldau, Tansania, Marokko, Zypern). Die Rechnung liest die YAML und prüft gegen diese Liste.
ABWEICHEND_LAUT_BERICHT = frozenset({"GEO", "MDA", "TZA", "MAR", "CYP"})
GASFACKEL_HINWEIS = {
    "IRQ": "Irak", "NGA": "Nigeria", "DZA": "Algerien",
}
GASFACKEL_GRUNDLAGE = ("frühere Plausibilitätsprüfung (Bericht 2026-09-26 statistik-geruest): großer Lichtanteil aus "
                       "Fördergebieten; nicht an einer Fackel-Datenbank geprüft")


@dataclass(frozen=True)
class Regeln:
    min_gute_monate: int = 6
    wenige_gute_monate_bis: int = 8
    nord_grenze_grad: float = 65.0
    rein_ab: float = 0.999
    reinheit_grenze: float = 0.5
    reinheit_gegen: tuple[float, float] = (0.3, 0.7)
    min_abdeckung_licht: float = 0.9
    wenige_monate_anteil: float = 1 / 3
    bootstrap_n: int = 2000
    bootstrap_startwert: int = 20260928
    verknuepfung: VerknuepfungsEinstellungen = VerknuepfungsEinstellungen()


# ------------------------------------------------------------------ Zellen: Jahreswert


class JahresSammler:
    """Sammelt Monat für Monat je Zelle: Summe und Zahl guter Monate, Summe und Zahl aller Monate mit Mittelwert,
    und ob die Zelle in irgendeinem Monat „noch nicht geladen“ war."""

    def __init__(self, form):
        self.summe_gut = np.zeros(form)
        self.n_gut = np.zeros(form, dtype="int16")
        self.summe_alle = np.zeros(form)
        self.n_alle = np.zeros(form, dtype="int16")
        self.nicht_geladen = np.zeros(form, dtype=bool)
        self.monate = 0

    def monat(self, kalendermonat, mittel, gueltig, aufgefuellt, nicht_geladen, breite, regeln: Regeln):
        klasse, licht, beob = zellen_klassen(mittel, gueltig, aufgefuellt, nicht_geladen,
                                             regeln.verknuepfung.min_beobachtet_anteil)
        schnee = schnee_verdacht(breite, kalendermonat, beob, regeln.verknuepfung.schnee_regel)
        gut = (klasse == 0) & ~schnee
        self.summe_gut += np.where(gut, licht, 0.0)
        self.n_gut += gut
        # Für den Schätzwert (nur Gewichtung): jeder Monat mit gültigem Pixel und endlichem Mittel.
        x = np.asarray(mittel, dtype="float64")
        g = np.nan_to_num(np.asarray(gueltig, dtype="float64"), nan=0.0)
        irgendwas = (klasse != 1) & (g > 0) & np.isfinite(x)
        self.summe_alle += np.where(irgendwas, x * g / 3600.0, 0.0)
        self.n_alle += irgendwas
        if nicht_geladen is not None:
            self.nicht_geladen |= np.asarray(nicht_geladen, bool)
        self.monate += 1

    def ergebnis(self, regeln: Regeln):
        with np.errstate(invalid="ignore", divide="ignore"):
            jahreswert = np.where(self.n_gut >= regeln.min_gute_monate, self.summe_gut / self.n_gut, np.nan)
            schaetzwert = np.where(self.n_alle > 0, self.summe_alle / self.n_alle, np.nan)
        return {"jahreswert": jahreswert, "schaetzwert": schaetzwert, "n_gut": self.n_gut.copy(),
                "nicht_geladen": self.nicht_geladen.copy(), "monate": self.monate}


# ------------------------------------------------------------------ Länder


def zelle_land_tabelle(einheiten: pd.DataFrame, zuordnung: pd.DataFrame, zellflaeche_zeile: np.ndarray,
                       regeln: Regeln) -> pd.DataFrame:
    """Je (Zelle, Weltbank-Land): Gewicht w = Zellfläche × Anteil des Landes / Landanteil der Zelle, Reinheit."""
    e = regeln.verknuepfung
    sicht = einheiten[einheiten["weltbank_code"].notna()]
    if not e.mit_unklar:
        sicht = sicht[sicht["weltbank_art"] != "unklar"]
    land = zuordnung.groupby(["zeile", "spalte"])["anteil"].sum().rename("land_anteil")
    z = zuordnung.merge(sicht[["einheit_id", "weltbank_code"]], on="einheit_id", how="inner")
    t = z.groupby(["weltbank_code", "zeile", "spalte"], as_index=False).agg(anteil=("anteil", "sum"),
                                                                             flaeche_km2=("flaeche_km2", "sum"))
    t = t.join(land, on=["zeile", "spalte"])
    t["zellflaeche_km2"] = zellflaeche_zeile[t["zeile"].to_numpy()]
    verteilt = t["land_anteil"].to_numpy() >= e.s_min
    if e.verteilung == "normiert":
        w = t["zellflaeche_km2"].to_numpy() * t["anteil"].to_numpy() / t["land_anteil"].to_numpy()
    else:
        w = t["flaeche_km2"].to_numpy()
    t["gewicht_km2"] = np.where(verteilt, w, 0.0)
    t["verteilt"] = verteilt
    t["rein"] = (t["anteil"] / t["land_anteil"]) >= regeln.rein_ab
    return t


def laender_jahr(t: pd.DataFrame, zellen: dict, breite: np.ndarray, regeln: Regeln) -> pd.DataFrame:
    """Lichtsummen und Kennzahlen je Weltbank-Land für ein Jahr."""
    zi, si = t["zeile"].to_numpy(), t["spalte"].to_numpy()
    a = zellen["jahreswert"][zi, si]
    s = zellen["schaetzwert"][zi, si]
    n = zellen["n_gut"][zi, si]
    ng = zellen["nicht_geladen"][zi, si]
    w = t["gewicht_km2"].to_numpy()
    hat_a = np.isfinite(a)
    licht = np.where(hat_a, a * w, 0.0)
    gewicht_nenner = np.where(hat_a, a * w, np.where(np.isfinite(s), s * w, 0.0))
    ohne_messung = ~hat_a & ~np.isfinite(s) & (w > 0)
    nord = breite[zi] > regeln.nord_grenze_grad
    wenig = hat_a & (n <= regeln.wenige_gute_monate_bis)
    rein = t["rein"].to_numpy()
    d = pd.DataFrame({
        "weltbank_code": t["weltbank_code"].to_numpy(), "licht": licht, "nenner": gewicht_nenner,
        "licht_rein": np.where(rein, licht, 0.0), "licht_wenig": np.where(wenig, licht, 0.0),
        "licht_nord": np.where(nord, licht, 0.0), "flaeche": t["flaeche_km2"].to_numpy(),
        "flaeche_ohne_messung": np.where(ohne_messung, t["flaeche_km2"].to_numpy(), 0.0),
        "flaeche_nicht_geladen": np.where(ng, t["flaeche_km2"].to_numpy(), 0.0),
        "flaeche_ohne_jahreswert": np.where(~hat_a, t["flaeche_km2"].to_numpy(), 0.0),
    })
    g = d.groupby("weltbank_code").sum()
    with np.errstate(invalid="ignore", divide="ignore"):
        g["abdeckung_licht"] = g["licht"] / g["nenner"]
        g["reinheit_licht"] = g["licht_rein"] / g["licht"]
        g["anteil_wenige_monate"] = g["licht_wenig"] / g["licht"]
        g["anteil_nord65"] = g["licht_nord"] / g["licht"]
        g["anteil_flaeche_ohne_jahreswert"] = g["flaeche_ohne_jahreswert"] / g["flaeche"]
        g["anteil_flaeche_ohne_messung"] = g["flaeche_ohne_messung"] / g["flaeche"]
    return g.rename(columns={"licht": "licht_summe", "licht_rein": "licht_summe_rein"})


# ------------------------------------------------------------------ Regression


def regression(x: np.ndarray, y: np.ndarray, n_boot: int, startwert: int) -> dict:
    """OLS y = a + b x; Bootstrap über Paare (Perzentil-Bereich 2,5–97,5 %)."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n = len(x)
    if n < 3:
        return {"n": n, "steigung": None, "achsenabschnitt": None, "r2": None, "steigung_unten": None, "steigung_oben": None}
    b, a = np.polyfit(x, y, 1)
    rest = y - (a + b * x)
    r2 = 1 - (rest ** 2).sum() / ((y - y.mean()) ** 2).sum()
    rng = np.random.default_rng(startwert)
    boot = np.empty(n_boot)
    for i in range(n_boot):
        k = rng.integers(0, n, n)
        xx = x[k]
        if np.ptp(xx) == 0:
            boot[i] = np.nan
            continue
        boot[i] = np.polyfit(xx, y[k], 1)[0]
    unten, oben = np.nanpercentile(boot, [2.5, 97.5])
    return {"n": n, "steigung": float(b), "achsenabschnitt": float(a), "r2": float(r2),
            "steigung_unten": float(unten), "steigung_oben": float(oben), "bootstrap_n": n_boot,
            "bootstrap_startwert": startwert}


# ------------------------------------------------------------------ Auswahl und Varianten


def auswahl(g: pd.DataFrame, bip: pd.Series, gebiet: dict, namen: dict, regeln: Regeln,
            reinheit_grenze: float | None = None, region: dict | None = None) -> pd.DataFrame:
    """Kennzeichnet je Land: aufgenommen ja/nein, Ausschlussgründe (alle), Kennzeichen."""
    rg = regeln.reinheit_grenze if reinheit_grenze is None else reinheit_grenze
    zeilen = []
    for code in sorted(set(g.index) | set(bip.index)):
        gruende, zeichen = [], []
        z = g.loc[code] if code in g.index else None
        b = bip.get(code, np.nan)
        if not np.isfinite(b):
            gruende.append("kein reales BIP der Weltbank für dieses Jahr")
        if z is None:
            gruende.append("keine Zelle in der Zuordnung (zu klein für 0,25° oder ohne Weltbank-Sicht)")
        else:
            if z["flaeche_nicht_geladen"] > 0:
                gruende.append("nicht vollständig geladen (Teile außerhalb Afrika-Europa-Asien)")
            elif region is not None and region.get(code) not in REGIONEN_M49:
                gruende.append(f"nicht in Afrika-Europa-Asien (M49-Region {region.get(code) or 'unbekannt'}), obwohl geladen")
            if gebiet.get(code) == "abweichend":
                gruende.append("Weltbank-Gebiet weicht ab (Bericht 2026-09-26 weltbank-gebiete)")
            if not z["licht_summe"] > 0:
                gruende.append("Lichtsumme 0 oder nicht bestimmbar (ln nicht möglich)")
            else:
                if not z["abdeckung_licht"] >= regeln.min_abdeckung_licht:
                    gruende.append(f"Abdeckung nach Licht {z['abdeckung_licht']:.0%} unter {regeln.min_abdeckung_licht:.0%}")
                if not z["reinheit_licht"] >= rg:
                    gruende.append(f"Reinheit {z['reinheit_licht']:.0%} unter {rg:.0%} (Licht aus Zellen mit anderen Ländern)")
                if z["anteil_wenige_monate"] > regeln.wenige_monate_anteil:
                    zeichen.append(f"{z['anteil_wenige_monate']:.0%} des Lichts aus Zellen mit nur 6–8 guten Monaten")
                if z["anteil_nord65"] > 0:
                    zeichen.append(f"{z['anteil_nord65']:.0%} des Lichts nördlich von 65° N")
            if gebiet.get(code) == "unklar":
                zeichen.append("Gebiet der Weltbank-Zahl unklar")
            if z["anteil_flaeche_ohne_messung"] > 0.01:
                zeichen.append(f"{z['anteil_flaeche_ohne_messung']:.0%} der Fläche ohne jede Messung im Jahr")
        if code in GASFACKEL_HINWEIS:
            zeichen.append("Gasfackel-Hinweis (nicht herausgerechnet)")
        zeilen.append({
            "code": code, "name": namen.get(code, code), "bip": b,
            "licht_summe": None if z is None else z["licht_summe"],
            "licht_summe_rein": None if z is None else z["licht_summe_rein"],
            "abdeckung_licht": None if z is None else z["abdeckung_licht"],
            "reinheit_licht": None if z is None else z["reinheit_licht"],
            "anteil_wenige_monate": None if z is None else z["anteil_wenige_monate"],
            "anteil_nord65": None if z is None else z["anteil_nord65"],
            "gebiet_weltbank": gebiet.get(code, "keine Angabe gefunden"),
            "wenige_monate": bool(z is not None and z["licht_summe"] > 0 and z["anteil_wenige_monate"] > regeln.wenige_monate_anteil),
            "aufgenommen": not gruende, "gruende": gruende, "kennzeichen": zeichen,
        })
    return pd.DataFrame(zeilen)


def rechne_varianten(g, bip, gebiet, namen, regeln: Regeln, region: dict | None = None) -> tuple[dict, pd.DataFrame]:
    haupt = auswahl(g, bip, gebiet, namen, regeln, region=region)
    varianten = {}

    def reg(tab, spalte="licht_summe"):
        t = tab[tab["aufgenommen"]]
        t = t[t[spalte] > 0]
        return regression(np.log(t["bip"].to_numpy(float)), np.log(t[spalte].to_numpy(float)),
                          regeln.bootstrap_n, regeln.bootstrap_startwert), list(t["code"])

    varianten["haupt"], _ = reg(haupt)
    varianten["nur_reine_zellen"], _ = reg(haupt, "licht_summe_rein")
    for grenze in regeln.reinheit_gegen:
        varianten[f"reinheit_{int(grenze * 100)}"], _ = reg(auswahl(g, bip, gebiet, namen, regeln, grenze, region))
    varianten["ohne_wenige_monate"], _ = reg(haupt[~haupt["wenige_monate"]])
    varianten["zusatz_ohne_unklares_gebiet"], _ = reg(haupt[haupt["gebiet_weltbank"] != "unklar"])
    return varianten, haupt


VARIANTEN_TEXT = {
    "haupt": "Hauptrechnung (Regeln 1–7)",
    "nur_reine_zellen": "Gegenrechnung Regel 2: Licht nur aus Zellen, die ganz zu einem Land gehören",
    "reinheit_30": "Gegenrechnung Regel 4: Reinheit mindestens 30 %",
    "reinheit_70": "Gegenrechnung Regel 4: Reinheit mindestens 70 %",
    "ohne_wenige_monate": "Gegenrechnung Regel 6: ohne Länder mit über einem Drittel Licht aus Zellen mit 6–8 guten Monaten",
    "zusatz_ohne_unklares_gebiet": "Zusatz (nicht im Auftrag, Empfehlung Weltbank-Bericht): ohne Länder mit unklarem Weltbank-Gebiet",
}


def region_je_land(einheiten: pd.DataFrame) -> dict:
    """M49-Region (UN) je Weltbank-Code: die Region, auf die der größte Teil der Fläche seiner Einheiten fällt."""
    from aleph.layers import un_m49

    m49, _ = un_m49.lade()
    reg = dict(zip(m49["m49"], m49["region"]))
    e = einheiten[einheiten["weltbank_code"].notna()].copy()
    e["region"] = e["un_m49"].map(reg)
    e = e[e["region"].notna() & (e["region"] != "")]
    f = e.groupby(["weltbank_code", "region"])["flaeche_km2"].sum().reset_index()
    f = f.sort_values("flaeche_km2", ascending=False).drop_duplicates("weltbank_code")
    return dict(zip(f["weltbank_code"], f["region"]))


# ------------------------------------------------------------------ Gesamtablauf


def _git_stand():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=10,
                              cwd=Path(__file__).resolve().parents[2]).stdout.strip()
    except Exception:
        return ""


def rechne_jahr(jahr: int, t: pd.DataFrame, regeln: Regeln) -> tuple[pd.DataFrame, np.ndarray]:
    from aleph.layers import vnp46a3, vnp46a3_regionen

    if jahr >= GESPERRT_AB_JAHR:
        raise ValueError(f"{jahr}: 2023–2025 ist Validierungs- und Endtestzeitraum, gesperrt.")
    variablen = [f"{FELD}_mittel_beobachtet", f"{FELD}_gueltige_pixel", f"{FELD}_aufgefuellt_pixel"]
    geliefert = vnp46a3_regionen.zellmaske(vnp46a3.lies_referenz_positionen(), 720, 1440)
    sammler, breite = None, None
    for monat in range(1, 13):
        zustand = vnp46a3.monatsstatus(jahr, monat)
        if zustand not in (vnp46a3.MONAT_FERTIG, vnp46a3.MONAT_REGION_VOLLSTAENDIG):
            raise ValueError(f"{jahr}-{monat:02d} ist nicht fertig (Zustand {zustand}); Jahreswert nicht rechenbar.")
        ds = vnp46a3.lies_monate_mit_region([(jahr, monat)], variablen, REGION)
        breite = ds["breite"].values
        if sammler is None:
            sammler = JahresSammler((len(breite), len(ds["laenge"].values)))
        nicht_geladen = ds["nicht_geladen"].values[0] & geliefert
        sammler.monat(monat, ds[variablen[0]].values[0], ds[variablen[1]].values[0], ds[variablen[2]].values[0],
                      nicht_geladen, breite, regeln)
    zellen = sammler.ergebnis(regeln)
    return laender_jahr(t, zellen, breite, regeln), zellen


def rechne(jahre=JAHRE, regeln: Regeln | None = None) -> dict:
    from aleph.layers import weltbank, zell_einheiten

    regeln = regeln or Regeln()
    for j in jahre:
        if j >= GESPERRT_AB_JAHR:
            raise ValueError(f"{j}: gesperrt (2023–2025).")
    einheiten, zuordnung, _, manifest = zell_einheiten.lade()
    sonder = zell_einheiten.lade_sonderliste().get("weltbank_laender", {})
    gebiet = {k: v.get("gebiet") for k, v in sonder.items()}
    abweichend = {k for k, v in gebiet.items() if v == "abweichend"}
    if abweichend != ABWEICHEND_LAUT_BERICHT:
        raise ValueError(f"Liste „abweichend“ in der YAML {sorted(abweichend)} passt nicht zum Bericht "
                         f"{sorted(ABWEICHEND_LAUT_BERICHT)}; bitte klären, nicht raten.")
    t = zelle_land_tabelle(einheiten, zuordnung, zell_einheiten.zellflaechen_km2(), regeln)
    region = region_je_land(einheiten)
    wb = weltbank.lese_tabelle()
    namen = dict(wb.drop_duplicates("land_iso3").set_index("land_iso3")["land_name"])
    ergebnis = {"jahre": {}, "regeln": {k: v for k, v in asdict(regeln).items() if k != "verknuepfung"},
                "verknuepfung": {k: (str(v) if k == "schnee_regel" else v) for k, v in asdict(regeln.verknuepfung).items()}}
    for jahr in jahre:
        g, zellen = rechne_jahr(jahr, t, regeln)
        b = wb[(wb["indikator"] == BIP_INDIKATOR) & (wb["jahr"] == jahr) & wb["hat_wert"]].set_index("land_iso3")["wert"]
        varianten, haupt = rechne_varianten(g, b, gebiet, namen, regeln, region)
        rein = haupt[haupt["aufgenommen"]].copy()
        r = varianten["haupt"]
        rein["x"] = np.log(rein["bip"].astype(float))
        rein["y"] = np.log(rein["licht_summe"].astype(float))
        rein["rest"] = rein["y"] - (r["achsenabschnitt"] + r["steigung"] * rein["x"])
        rein["faktor"] = np.exp(rein["rest"])
        abw = rein.reindex(rein["rest"].abs().sort_values(ascending=False).index).head(10)
        zellstat = {
            "zellen_mit_jahreswert": int(np.isfinite(zellen["jahreswert"]).sum()),
            "zellen_ohne_jahreswert_mit_messung": int((~np.isfinite(zellen["jahreswert"]) & np.isfinite(zellen["schaetzwert"])).sum()),
            "monate": zellen["monate"],
        }
        ergebnis["jahre"][str(jahr)] = {
            "varianten": varianten,
            "laender": _records(haupt),
            "punkte": _records(rein[["code", "name", "x", "y", "rest", "faktor", "kennzeichen", "abdeckung_licht",
                                     "reinheit_licht", "anteil_wenige_monate", "anteil_nord65", "gebiet_weltbank"]]),
            "groesste_abweichung": _records(abw[["code", "name", "rest", "faktor"]]),
            "zellen": zellstat,
        }
    ergebnis.update({
        "titel": "Nachtlicht und reales BIP, Querschnitt über Länder",
        "evidenzstufe": "statistische Assoziation",
        "rahmen": "Querschnitt, ein Jahr, Afrika-Europa-Asien, kein Beleg für Ursache und Wirkung",
        "y": "ln(Jahres-Lichtsumme, nW·cm⁻²·sr⁻¹ × km²)", "x": "ln(reales BIP, konstante US-Dollar 2015, NY.GDP.MKTP.KD)",
        "varianten_text": VARIANTEN_TEXT,
        "gasfackel_hinweis": {"laender": GASFACKEL_HINWEIS, "grundlage": GASFACKEL_GRUNDLAGE},
        "literaturvergleich": "entfällt (Quellen nur Metadaten geprüft; andere Größe: BIP auf Licht, Panel)",
        "statistik_pruefer": "nicht eingesetzt (Anweisung des Nutzers 2026-09-28: kein statistik-pruefer in dieser Sitzung)",
        "feld": f"{FELD}_mittel_beobachtet (AllAngle, schneefrei)",
        "sicht": "so wie die Weltbank zählt (mit unklaren Gebieten)",
        "version": VERSION, "git": _git_stand(),
        "zuordnung_manifest": manifest.get("erstellt_utc"),
        "weltbank_abruf": str(wb["abruf_utc"].iloc[0]),
        "erstellt_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    return ergebnis


def _wert(v):
    if isinstance(v, (np.floating, float)):
        return None if not np.isfinite(v) else float(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def _records(df: pd.DataFrame) -> list[dict]:
    return [{k: _wert(v) for k, v in z.items()} for z in df.to_dict(orient="records")]


def schreibe(ergebnis: dict) -> Path:
    ordner = io.aleph_data_dir().joinpath(*AUSGABE_ORDNER)
    ordner.mkdir(parents=True, exist_ok=True)
    pfad = ordner / "ergebnis.json"
    hilfs = pfad.with_suffix(".json.tmp")
    hilfs.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")
    hilfs.replace(pfad)
    return pfad


def main(argv=None) -> int:
    e = rechne()
    pfad = schreibe(e)
    for jahr, j in e["jahre"].items():
        r = j["varianten"]["haupt"]
        print(f"{jahr}: n={r['n']}, Steigung {r['steigung']:.2f} [{r['steigung_unten']:.2f}; {r['steigung_oben']:.2f}], R² {r['r2']:.2f}")
    print(f"geschrieben: {pfad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
