"""Verknüpfungsgerüst Nachtlicht × Einheiten × Weltbank-Sicht (Stand 2026-09-26, TECHNIKPROBE).

Was hier passiert: Nachtlicht je Einheit und Monat aus Würfel × Zell-Länder-Zuordnung, mit Abdeckung und
Zustand, dann zusammengefasst je Weltbank-Land in der Sicht „so wie die Weltbank zählt“. Es wird KEIN
BIP gelesen, keine Regression gerechnet und keine Aussage über einen Zusammenhang getroffen.
Evidenzstufe der Summen: „beobachtet“ (Summe gemessener Strahldichten über Flächen).

Grundlagen (gelesen, nicht neu erfunden):
- Zuordnung Zelle → Einheit nach Flächenanteil: aleph/layers/zell_einheiten.py (`lade()`), Bericht
  berichte/2026-09-26_zell-laender-zuordnung.md; Weltbank-Sicht `weltbank_sicht()`, Reinheit `reinheit()`.
- Welche Gebiete die Weltbank-Zahlen abdecken: berichte/2026-09-26_weltbank-gebiete.md und Abschnitt
  `weltbank_laender` in aleph/layers/sondereinheiten.yaml (passt / unklar / abweichend je Land).
- Vorschlag des statistik-pruefer (Bericht Zell-Zuordnung, Empfehlung 1) für Küsten- und Grenzzellen:
  Lichtsumme einer Zelle L = Mittel × Zahl gültiger Pixel × Pixelfläche; Anteil einer Einheit = L × a / S
  (a = Flächenanteil der Einheit an der Zelle, S = Summe der Landanteile der Zelle); Zellen mit S < s_min
  nicht verteilen, getrennt ausweisen.
- Befund 2026-09-26 (Würfel gelesen, 2018-01): Meerpixel sind im Würfel GÜLTIG und dunkel (Mittelmeer,
  Rotes Meer, Persischer Golf: 3600 gültige Pixel, Wert 0), keine Fehlwerte. Das Licht einer Küstenzelle
  kommt also fast ganz vom Land; die Normierung durch S schiebt es auf die Landeinheiten.

Lichtsumme: Einheit nW·cm⁻²·sr⁻¹ · km² (Strahldichte mal Fläche). Gerechnet mit dem Mittel über
BEOBACHTETE Pixel (ohne aufgefüllte), hochgerechnet auf alle gültigen Pixel der Zelle.

Fehlende Daten werden nie 0: Zellen „nicht geladen“ (Zustand 4 außerhalb der Region), „keine Daten“
(kein gültiger Pixel) und „Datenlage unzureichend“ (< 50 % beobachtet) gehen NICHT in die Summe ein und
werden als Flächenanteile ausgewiesen. Liegt die Abdeckung unter `min_abdeckung`, ist `licht_summe` NaN
(die Teilsumme steht getrennt in `licht_summe_abgedeckt`).

Grenzen (Plausibilitätsprüfung und statistik-pruefer 2026-09-26):
- Zwischen 90 und 100 % Abdeckung ist die Landessumme eine UNTERGRENZE. Die Abdeckung ist ein FLÄCHENmaß;
  Licht ist auf Städte konzentriert. Geschätzt fehlten 2018-01 z. B. bei Tansania etwa 9 %, bei Japan etwa
  11 % des Lichts, obwohl weniger Fläche fehlte. Vor der ersten Regression eine lichtgewichtete Abdeckung
  (erwarteter Lichtanteil der fehlenden Zellen aus Kalibrierungsjahren desselben Kalendermonats) ergänzen.
- Gasfackeln zählen als Licht (Irak, Nigeria, Algerien: großer Teil der Summe), ebenso beleuchtete
  Gewächshäuser (Vermutung zur hellen Zelle bei Närpes, Finnland). Für eine BIP-Auswertung auszuweisen.
- Kleine Küstenländer hängen stark an der Verteilung „normiert“ (mit „flaechenanteil“ fiele Bahrain auf 38 %).
- Tansania und Länder mit Reinheit < 0,5 sind hier nur markiert; vor der ersten Regression ausschließen
  (Empfehlung statistik-pruefer) und die Gegenproben (s_min 0,01 / 0,2, „flaechenanteil“, ohne „unklar“) rechnen.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from aleph.detect.schnee import SchneeRegel, schnee_verdacht

VERKNUEPFUNG_VERSION = "0.1.0"
METHODE = ("Lichtsumme je Zelle = Mittel beobachteter Pixel × gültige Pixel/3600 × Zellfläche; verteilt auf Einheiten "
           "nach Flächenanteil (normiert auf die Landfläche der Zelle); Summe je Weltbank-Land in der Sicht „so wie die "
           "Weltbank zählt“")
PIXEL_PRO_ZELLE = 3600

# Wie die Weltbank-Sicht (aleph/layers/zell_einheiten.weltbank_sicht) die „abweichenden“ Länder abbildet
# (Grundlage: berichte/2026-09-26_weltbank-gebiete.md, Tabelle; Einheiten ohne Weltbank-Code in der YAML):
ABWEICHUNG_IN_SICHT = {
    "GEO": "berücksichtigt (Abchasien und Südossetien sind eigene Einheiten ohne Weltbank-Code)",
    "MDA": "berücksichtigt (Transnistrien ist eigene Einheit ohne Weltbank-Code)",
    "CYP": "berücksichtigt (Nordzypern ist eigene Einheit ohne Weltbank-Code); Bevölkerung nicht als Nenner",
    "MAR": "teilweise (beide Teile der Westsahara zählen zu MAR; ob die Weltbank die ganze Westsahara meint, ist unklar)",
    "TZA": "NICHT berücksichtigt (BIP nur Festland, Sansibar steckt im Umriss Tansanias)",
}


@dataclass(frozen=True)
class VerknuepfungsEinstellungen:
    """Offene Entscheidungen als einstellbare Werte (Standard und Begründung je Feld).

    - `verteilung` „normiert“: L × a / S (Vorschlag statistik-pruefer; Meerpixel sind dunkel und gültig, also
      gehört das Licht der Zelle zum Land). Gegenprobe „flaechenanteil“: L × a (verteilt Licht gleichmäßig über
      die ganze Zelle, auch aufs Meer; unterschätzt Küstenstädte).
    - `s_min` 0,05: Zellen mit weniger als 5 % Land werden nicht verteilt (sonst würde das Licht von Schiffen oder
      Plattformen auf einen Landzipfel geschoben). Gegenproben 0,01 und 0,2 empfohlen (statistik-pruefer).
    - `reinheit_grenze` 0,5 (bei `reinheit_schwelle` 0,9): Länder, deren Fläche zu weniger als 50 % in Zellen
      liegt, in denen sie mindestens 90 % des Landes stellen, sind „Mischzellen“-Länder (Vorschlag
      statistik-pruefer „z. B. R < 0,5“). Hier nur gekennzeichnet, nicht ausgeschlossen.
    - `tansania` „markieren“: BIP nur Festland, Sansibar steckt im Umriss (Weltbank-Bericht). „ausschliessen“
      nimmt Tansania aus der Tabelle. „sansibar_abziehen“ ist nicht gebaut (keine Sansibar-Geometrie).
    - `min_abdeckung` 0,9: Unter 90 % abgedeckter Fläche ist die Summe um mehr als ein Zehntel unvollständig und
      wird nicht als Landessumme ausgegeben. Eigene Festlegung, nicht kalibriert.
    - `min_beobachtet_anteil` 0,5: wie Anomalieerkennung und Globus.
    - `mit_unklar` True: Hauptsicht nach Empfehlung statistik-pruefer (sonst verlöre z. B. Guyana 74 % seiner
      Fläche); Gegenprobe False.
    """

    verteilung: str = "normiert"
    s_min: float = 0.05
    reinheit_schwelle: float = 0.9
    reinheit_grenze: float = 0.5
    tansania: str = "markieren"
    min_abdeckung: float = 0.9
    min_beobachtet_anteil: float = 0.5
    mit_unklar: bool = True
    schnee_regel: SchneeRegel = SchneeRegel()

    def __post_init__(self):
        if self.verteilung not in ("normiert", "flaechenanteil"):
            raise ValueError("verteilung: „normiert“ oder „flaechenanteil“.")
        if self.tansania not in ("markieren", "ausschliessen", "sansibar_abziehen"):
            raise ValueError("tansania: „markieren“, „ausschliessen“ oder „sansibar_abziehen“.")
        if self.tansania == "sansibar_abziehen":
            raise NotImplementedError("Sansibar abziehen ist nicht gebaut: Es gibt noch keine Sansibar-Einheit "
                                      "(Geometrie aus der Natural-Earth-Provinzdatei wäre nötig).")
        if not (0 <= self.s_min < 1 and 0 < self.min_abdeckung <= 1 and 0 < self.min_beobachtet_anteil <= 1):
            raise ValueError("Grenzwerte außerhalb des erlaubten Bereichs.")


def zellen_klassen(mittel_beob, gueltig, aufgefuellt, nicht_geladen, min_beobachtet_anteil):
    """Je Zelle: Klasse (0 gültig, 1 nicht geladen, 2 keine Daten, 3 unzureichend) und Lichtdichte-Faktor.

    Rückgabe: (klasse int8, licht_je_km2 float64 = Mittel × gültig/3600 in gültigen Zellen, sonst NaN,
    beobachtet_anteil)."""
    x = np.asarray(mittel_beob, dtype="float64")
    g = np.nan_to_num(np.asarray(gueltig, dtype="float64"), nan=0.0)
    a = np.nan_to_num(np.asarray(aufgefuellt, dtype="float64"), nan=0.0)
    ng = np.zeros(x.shape, bool) if nicht_geladen is None else np.asarray(nicht_geladen, bool)
    beob = np.where((g > 0) & (a >= 0) & (a <= g), (g - a) / PIXEL_PRO_ZELLE, np.nan)
    klasse = np.zeros(x.shape, dtype="int8")
    klasse[(g <= 0) | ~np.isfinite(beob)] = 2
    klasse[(klasse == 0) & ((beob < min_beobachtet_anteil) | ~np.isfinite(x))] = 3
    klasse[ng] = 1
    licht = np.where(klasse == 0, x * g / PIXEL_PRO_ZELLE, np.nan)
    return klasse, licht, beob


def nachtlicht_je_einheit(monat: tuple[int, int], zustand: str, mittel_beob, gueltig, aufgefuellt, nicht_geladen,
                          zuordnung: pd.DataFrame, breite: np.ndarray, e: VerknuepfungsEinstellungen | None = None) -> pd.DataFrame:
    """Nachtlicht je Einheit für einen Monat. `zuordnung`: Spalten zeile, spalte, einheit_id, flaeche_km2, anteil.

    Spalten des Ergebnisses: einheit_id, monat, zustand, flaeche_km2, flaeche_abgedeckt_km2, abdeckung,
    anteil_nicht_geladen, anteil_keine_daten, anteil_unzureichend, anteil_nicht_verteilt (Küstenzellen unter
    s_min), anteil_schnee_verdacht, licht_summe_abgedeckt, licht_summe, n_zellen, evidenzstufe, methode, version.
    """
    e = e or VerknuepfungsEinstellungen()
    klasse, licht, beob = zellen_klassen(mittel_beob, gueltig, aufgefuellt, nicht_geladen, e.min_beobachtet_anteil)
    schnee = schnee_verdacht(breite, monat[1], beob, e.schnee_regel)
    z = zuordnung[["zeile", "spalte", "einheit_id", "flaeche_km2", "anteil"]].copy()
    zi, si = z["zeile"].to_numpy(), z["spalte"].to_numpy()
    land = z.groupby(["zeile", "spalte"])["anteil"].transform("sum").to_numpy()
    k = klasse[zi, si]
    nicht_verteilt = (k == 0) & (land < e.s_min)
    gilt = (k == 0) & ~nicht_verteilt
    faktor = np.where(land > 0, 1.0 / land, np.nan) if e.verteilung == "normiert" else np.ones(len(z))
    zellflaeche = z["flaeche_km2"].to_numpy() / np.where(z["anteil"].to_numpy() > 0, z["anteil"].to_numpy(), np.nan)
    if e.verteilung == "normiert":
        beitrag = licht[zi, si] * zellflaeche * z["anteil"].to_numpy() * faktor
    else:
        beitrag = licht[zi, si] * z["flaeche_km2"].to_numpy()
    f = z["flaeche_km2"].to_numpy()
    z = z.assign(
        _f=f, _gilt=np.where(gilt, f, 0.0), _ng=np.where(k == 1, f, 0.0), _kd=np.where(k == 2, f, 0.0),
        _unz=np.where(k == 3, f, 0.0), _nv=np.where(nicht_verteilt, f, 0.0), _schnee=np.where(schnee[zi, si] & (k == 0), f, 0.0),
        _licht=np.where(gilt, beitrag, 0.0),
    )
    g = z.groupby("einheit_id").agg(
        flaeche_km2=("_f", "sum"), flaeche_abgedeckt_km2=("_gilt", "sum"), _ng=("_ng", "sum"), _kd=("_kd", "sum"),
        _unz=("_unz", "sum"), _nv=("_nv", "sum"), _schnee=("_schnee", "sum"), licht_summe_abgedeckt=("_licht", "sum"),
        n_zellen=("_f", "size"),
    )
    with np.errstate(invalid="ignore", divide="ignore"):
        g["abdeckung"] = g["flaeche_abgedeckt_km2"] / g["flaeche_km2"]
        for kurz, name in (("_ng", "anteil_nicht_geladen"), ("_kd", "anteil_keine_daten"), ("_unz", "anteil_unzureichend"),
                           ("_nv", "anteil_nicht_verteilt"), ("_schnee", "anteil_schnee_verdacht")):
            g[name] = g[kurz] / g["flaeche_km2"]
    g.loc[g["flaeche_abgedeckt_km2"] <= 0, "licht_summe_abgedeckt"] = np.nan
    g["licht_summe"] = g["licht_summe_abgedeckt"].where(g["abdeckung"] >= e.min_abdeckung)
    g = g.drop(columns=["_ng", "_kd", "_unz", "_nv", "_schnee"]).reset_index()
    g.insert(1, "monat", f"{monat[0]:04d}-{monat[1]:02d}")
    g.insert(2, "zustand", zustand)
    g["evidenzstufe"] = "beobachtet"
    g["methode"] = METHODE + f"; Verteilung {e.verteilung}, s_min {e.s_min}"
    g["version"] = VERKNUEPFUNG_VERSION
    return g


def je_weltbank_land(je_einheit: pd.DataFrame, einheiten: pd.DataFrame, weltbank_laender: dict,
                     reinheit: pd.DataFrame | None = None, e: VerknuepfungsEinstellungen | None = None) -> pd.DataFrame:
    """Summe je Weltbank-Land in der Sicht „so wie die Weltbank zählt“, mit Kennzeichen.

    `einheiten`: Tabelle aus zell_einheiten.lade() (einheit_id, weltbank_code, weltbank_art).
    `weltbank_laender`: Abschnitt `weltbank_laender` der Sonderliste (Code → {gebiet, beleg}).
    `reinheit`: Ergebnis von zell_einheiten.reinheit(...) (Index Weltbank-Code, Spalte reinheit) oder None.
    """
    e = e or VerknuepfungsEinstellungen()
    sicht = einheiten[einheiten["weltbank_code"].notna()]
    if not e.mit_unklar:
        sicht = sicht[sicht["weltbank_art"] != "unklar"]
    d = je_einheit.merge(sicht[["einheit_id", "weltbank_code", "weltbank_art", "ebene"]], on="einheit_id", how="inner")
    # Unklar zugeordnete SONDEReinheiten (z. B. Kaschmir bei Indien); ob die Grundeinheit selbst „unklar“ ist,
    # sagt `gebiet_weltbank` (aus der Weltbank-Prüfung je Land).
    sonder = d["ebene"].astype(str).str.startswith("Sondereinheit")
    d["_unklar"] = np.where((d["weltbank_art"] == "unklar") & sonder, d["flaeche_km2"], 0.0)
    for name in ("anteil_nicht_geladen", "anteil_keine_daten", "anteil_unzureichend", "anteil_nicht_verteilt", "anteil_schnee_verdacht"):
        d["_" + name] = d[name] * d["flaeche_km2"]
    agg = {"flaeche_km2": ("flaeche_km2", "sum"), "flaeche_abgedeckt_km2": ("flaeche_abgedeckt_km2", "sum"),
           "licht_summe_abgedeckt": ("licht_summe_abgedeckt", lambda s: s.sum(min_count=1)),
           "_unklar": ("_unklar", "sum"), "n_einheiten": ("einheit_id", "size"), "n_zellen": ("n_zellen", "sum"),
           "monat": ("monat", "first"), "zustand": ("zustand", "first")}
    for name in ("anteil_nicht_geladen", "anteil_keine_daten", "anteil_unzureichend", "anteil_nicht_verteilt", "anteil_schnee_verdacht"):
        agg["_" + name] = ("_" + name, "sum")
    w = d.groupby("weltbank_code").agg(**agg)
    with np.errstate(invalid="ignore", divide="ignore"):
        w["abdeckung"] = w["flaeche_abgedeckt_km2"] / w["flaeche_km2"]
        for name in ("anteil_nicht_geladen", "anteil_keine_daten", "anteil_unzureichend", "anteil_nicht_verteilt", "anteil_schnee_verdacht"):
            w[name] = w["_" + name] / w["flaeche_km2"]
        w["anteil_unklare_flaeche"] = w["_unklar"] / w["flaeche_km2"]
    w = w.drop(columns=[c for c in w.columns if c.startswith("_")])
    w["licht_summe"] = w["licht_summe_abgedeckt"].where(w["abdeckung"] >= e.min_abdeckung)
    w["gebiet_weltbank"] = [weltbank_laender.get(c, {}).get("gebiet", "keine Angabe gefunden") for c in w.index]
    if reinheit is not None:
        w = w.join(reinheit[["reinheit"]], how="left")
    else:
        w["reinheit"] = np.nan
    w["kennzeichen"] = [_kennzeichen(c, zeile, e) for c, zeile in w.iterrows()]
    if e.tansania == "ausschliessen":
        w = w.drop(index="TZA", errors="ignore")
    w = w.reset_index().rename(columns={"index": "weltbank_code"})
    w["sicht"] = "so wie die Weltbank zählt" + (" (mit unklaren Gebieten)" if e.mit_unklar else " (ohne unklare Gebiete)")
    w["evidenzstufe"] = "beobachtet"
    w["methode"] = METHODE + f"; Verteilung {e.verteilung}, s_min {e.s_min}"
    w["version"] = VERKNUEPFUNG_VERSION
    return w


def _pz(x: float) -> str:
    """Anteil als ganze Prozent, abgerundet (89,5 % erscheint als 89 %, nie als „90 % unter 90 %“)."""
    return f"{int(np.floor(x * 100 + 1e-9))} %"


def _kennzeichen(code: str, z: pd.Series, e: VerknuepfungsEinstellungen) -> str:
    teile = []
    if z["anteil_nicht_geladen"] > 0.5:
        teile.append(f"überwiegend nicht geladen ({_pz(z['anteil_nicht_geladen'])} der Fläche; Monat bisher nur Afrika-Europa-Asien)")
    elif not z["abdeckung"] > 0:
        teile.append("keine Abdeckung")
    elif z["abdeckung"] < e.min_abdeckung:
        teile.append(f"Abdeckung {_pz(z['abdeckung'])} unter {_pz(e.min_abdeckung)}: keine Landessumme")
    if z["anteil_nicht_verteilt"] >= 0.05:
        teile.append(f"{_pz(z['anteil_nicht_verteilt'])} der Fläche in Zellen mit unter {_pz(e.s_min)} Land (Licht nicht verteilt)")
    if 0.005 <= z["anteil_nicht_geladen"] <= 0.5:
        teile.append(f"{_pz(z['anteil_nicht_geladen'])} der Fläche nicht geladen")
    if z["anteil_unzureichend"] >= 0.05:
        teile.append(f"{_pz(z['anteil_unzureichend'])} Datenlage unzureichend")
    if z["anteil_schnee_verdacht"] >= 0.05:
        teile.append(f"Schnee-Verdacht auf {_pz(z['anteil_schnee_verdacht'])}")
    gebiet = z["gebiet_weltbank"]
    if gebiet == "abweichend":
        teile.append("Gebiet weicht ab: " + ABWEICHUNG_IN_SICHT.get(code, "Abbildung in der Sicht nicht geklärt"))
    elif gebiet == "unklar":
        teile.append("Gebiet der Weltbank-Zahl unklar")
    if z["anteil_unklare_flaeche"] >= 0.01:
        teile.append(f"{_pz(z['anteil_unklare_flaeche'])} der Fläche in Sondergebieten mit unklarer Weltbank-Zuordnung")
    if np.isfinite(z["reinheit"]) and z["reinheit"] < e.reinheit_grenze:
        teile.append(f"Mischzellen (Reinheit {z['reinheit']:.1f})")
    if code == "TZA" and e.tansania == "markieren":
        teile.append("Tansania: BIP nur Festland")
    return "; ".join(teile)


def technikprobe(monat: tuple[int, int] = (2018, 1), e: VerknuepfungsEinstellungen | None = None) -> dict:
    """Technikprobe an einem echten Monat (Würfel und Zuordnung nur gelesen). KEINE Aussage über das BIP.

    Liest den Monat über aleph.layers.vnp46a3.lies_monate_mit_region (Zustand 1 oder 4 mit Nachweisprüfung).
    Monate ab 2023-01 werden verweigert.
    """
    from aleph.layers import vnp46a3, zell_einheiten

    e = e or VerknuepfungsEinstellungen()
    if monat >= (2023, 1):
        raise ValueError("Technikprobe nur vor 2023 (2023–2025 ist Validierung/Endtest).")
    zustand_code = vnp46a3.monatsstatus(*monat)
    zustand = {1: "vollständig", 4: "nur Afrika-Europa-Asien"}.get(zustand_code, f"Zustand {zustand_code}")
    felder = ["allangle_mittel_beobachtet", "allangle_gueltige_pixel", "allangle_aufgefuellt_pixel"]
    ds = vnp46a3.lies_monate_mit_region([monat], felder, "afrika_europa_asien")
    einheiten, zuordnung, _, manifest = zell_einheiten.lade()
    je_einheit = nachtlicht_je_einheit(
        monat, zustand, ds[felder[0]].values[0], ds[felder[1]].values[0], ds[felder[2]].values[0],
        ds["nicht_geladen"].values[0], zuordnung, ds["breite"].values, e)
    sonder = zell_einheiten.lade_sonderliste()
    sicht_einheiten = einheiten if e.mit_unklar else einheiten[einheiten["weltbank_art"] != "unklar"]
    rein = zell_einheiten.reinheit(sicht_einheiten, zuordnung, schwelle=e.reinheit_schwelle)
    laender = je_weltbank_land(je_einheit, einheiten, sonder.get("weltbank_laender", {}), rein, e)
    return {"je_einheit": je_einheit, "je_land": laender, "zustand": zustand, "zuordnung_manifest": manifest.get("ergebnis_sha256")}
