"""Länderwerte für das Dossier des Globus (Teil 3a, 2026-09-28): Nachtlicht und Weltbank NEBENEINANDER.

Was hier passiert, und was nicht:
- Nachtlicht je Weltbank-Land und Monat kommt unverändert aus dem Verknüpfungsgerüst
  `aleph/link/nachtlicht_einheiten.py` (Standard-Einstellungen: Verteilung „normiert“, s_min 0,05,
  Mindestabdeckung 90 %, Sicht „so wie die Weltbank zählt“ mit unklaren Gebieten). Liegt die
  Abdeckung unter 90 %, gibt es KEINE Landessumme (das Gerüst setzt sie auf NaN); angezeigt wird dann
  nur die Abdeckung mit Kennzeichen. Evidenzstufe „beobachtet“.
- Weltbank-Werte (reales BIP NY.GDP.MKTP.KD, BIP pro Kopf NY.GDP.PCAP.KD, Bevölkerung SP.POP.TOTL) aus
  der ALEPH-Weltbank-Tabelle (`aleph/layers/weltbank.py`, `lese_tabelle`), nur für die Jahre der
  angezeigten Monate und NIE ab 2023 (Validierungs- und Endtestzeitraum). BIP pro Kopf, das die
  Weltbank-Tabelle als `nicht_verwenden` markiert (CYP, MAR, RUS, TZA, UKR: Nenner passt nicht zur
  Bevölkerung), wird nicht als Zahl ausgegeben.
- Es wird KEIN Zusammenhang gerechnet. Die Oberfläche stellt beides nebeneinander und sagt das.

Ausgabe: `daten/laender.js` (window.ALEPH_LAENDER).
"""

from __future__ import annotations

import math

import numpy as np

GESPERRT_AB_JAHR = 2023
WELTBANK_ANZEIGE = {
    "NY.GDP.MKTP.KD": "bip_real",
    "NY.GDP.PCAP.KD": "bip_pro_kopf_real",
    "SP.POP.TOTL": "bevoelkerung",
}
WELTBANK_QUELLE = "The World Bank: World Development Indicators (CC BY 4.0); Bevölkerung: UN World Population Prospects"


def _sig(x, stellen=2):
    """Auf `stellen` gültige Ziffern runden (keine Scheinpräzision); None für NaN."""
    if x is None or not np.isfinite(x):
        return None
    if x == 0:
        return 0.0
    return float(round(x, stellen - 1 - int(math.floor(math.log10(abs(x))))))


def _abgerundet_prozent(x):
    if x is None or not np.isfinite(x):
        return None
    return int(np.floor(x * 100 + 1e-9))


class Laenderwerte:
    """Sammelt je Monat die Länderwerte und am Ende die Weltbank-Werte."""

    def __init__(self):
        from aleph.layers import zell_einheiten
        from aleph.link.nachtlicht_einheiten import VerknuepfungsEinstellungen

        self.einstellungen = VerknuepfungsEinstellungen()
        self.einheiten, self.zuordnung, _, self.manifest = zell_einheiten.lade()
        self.weltbank_laender = zell_einheiten.lade_sonderliste().get("weltbank_laender", {})
        self.reinheit = zell_einheiten.reinheit(self.einheiten, self.zuordnung, schwelle=self.einstellungen.reinheit_schwelle)
        self.monate: dict[str, dict] = {}

    def monat(self, monat: str, zustand_text: str, ds_monat, nicht_geladen) -> None:
        """`ds_monat`: Dataset mit genau diesem Monat (Variablen allangle_*), `nicht_geladen`: Maske wie auf dem Globus."""
        from aleph.link.nachtlicht_einheiten import je_weltbank_land, nachtlicht_je_einheit

        jahr, mon = (int(t) for t in monat.split("-"))
        if jahr >= GESPERRT_AB_JAHR:
            raise ValueError(f"{monat} liegt im gesperrten Zeitraum")
        s = ds_monat.sel(zeit=f"{monat}-01")
        je_einheit = nachtlicht_je_einheit(
            (jahr, mon), zustand_text, s["allangle_mittel_beobachtet"].values, s["allangle_gueltige_pixel"].values,
            s["allangle_aufgefuellt_pixel"].values, nicht_geladen, self.zuordnung, ds_monat["breite"].values,
            self.einstellungen)
        land = je_weltbank_land(je_einheit, self.einheiten, self.weltbank_laender, self.reinheit, self.einstellungen)
        laender = {}
        for z in land.itertuples(index=False):
            summe = z.licht_summe if np.isfinite(z.licht_summe) else None
            laender[z.weltbank_code] = {
                "licht_summe": _sig(summe),
                "licht_je_km2": _sig(summe / z.flaeche_km2) if summe is not None else None,
                "abdeckung_prozent": _abgerundet_prozent(z.abdeckung),
                "flaeche_km2": _sig(z.flaeche_km2, 3),
                "nicht_geladen_prozent": _abgerundet_prozent(z.anteil_nicht_geladen),
                "schnee_verdacht_prozent": _abgerundet_prozent(z.anteil_schnee_verdacht),
                "gebiet_weltbank": z.gebiet_weltbank,
                "kennzeichen": z.kennzeichen,
            }
        # Einheiten ohne eigenen Weltbank-Code (z. B. Taiwan, Westsahara-Ost): eigener Wert der Einheit.
        ohne_code = set(self.einheiten.loc[self.einheiten["weltbank_code"].isna(), "einheit_id"])
        einheiten = {}
        for z in je_einheit[je_einheit["einheit_id"].isin(ohne_code)].itertuples(index=False):
            summe = z.licht_summe if np.isfinite(z.licht_summe) else None
            einheiten[z.einheit_id] = {
                "licht_summe": _sig(summe),
                "licht_je_km2": _sig(summe / z.flaeche_km2) if summe is not None and z.flaeche_km2 > 0 else None,
                "abdeckung_prozent": _abgerundet_prozent(z.abdeckung),
            }
        self.monate[monat] = {"land": laender, "einheit": einheiten}

    def weltbank(self, jahre: list[int]) -> dict:
        from aleph.layers import weltbank

        jahre = sorted({j for j in jahre if j < GESPERRT_AB_JAHR})
        t = weltbank.lese_tabelle()
        t = t[t["indikator"].isin(list(WELTBANK_ANZEIGE)) & t["jahr"].isin(jahre)]
        if (t["jahr"] >= GESPERRT_AB_JAHR).any():
            raise ValueError("Weltbank-Werte ab 2023 dürfen nicht angezeigt werden")
        werte: dict[str, dict] = {}
        for z in t.itertuples(index=False):
            land = werte.setdefault(z.land_iso3, {"name": z.land_name, "jahre": {}})
            eintrag = land["jahre"].setdefault(str(int(z.jahr)), {})
            nutzbar = bool(z.hat_wert) and not bool(z.nicht_verwenden)
            eintrag[WELTBANK_ANZEIGE[z.indikator]] = {
                "wert": _sig(float(z.wert), 3) if nutzbar else None,
                "vorlaeufig": bool(z.vorlaeufig),
                "nicht_verwenden": bool(z.nicht_verwenden),
            }
        abruf = str(t["abruf_utc"].iloc[0]) if len(t) else ""
        return {"jahre": jahre, "werte": werte, "abruf_utc": abruf, "quelle": WELTBANK_QUELLE,
                "einheiten": {"bip_real": "US-Dollar, konstante Preise (Basisjahr 2015)",
                              "bip_pro_kopf_real": "US-Dollar je Einwohner, konstante Preise (Basisjahr 2015)",
                              "bevoelkerung": "Personen (Jahresmitte)"},
                "indikatoren": {v: k for k, v in WELTBANK_ANZEIGE.items()}}

    def ergebnis(self) -> dict:
        from aleph.link.nachtlicht_einheiten import METHODE, VERKNUEPFUNG_VERSION

        jahre = [int(m[:4]) for m in self.monate]
        e = self.einstellungen
        return {
            "monate": self.monate,
            "weltbank": self.weltbank(jahre),
            "gebiet_weltbank": {k: v.get("gebiet") for k, v in self.weltbank_laender.items()},
            "methode": METHODE + f"; Verteilung {e.verteilung}, s_min {e.s_min}; Landessumme nur bei mindestens "
                                 f"{int(e.min_abdeckung * 100)} % abgedeckter Fläche",
            "version_verknuepfung": VERKNUEPFUNG_VERSION,
            "einheit_licht_summe": "nW·cm⁻²·sr⁻¹ × km²",
            "einheit_licht_je_km2": "nW·cm⁻²·sr⁻¹ (Lichtsumme geteilt durch Fläche)",
            "evidenzstufe_licht": "beobachtet",
            "sicht": "so wie die Weltbank zählt (mit unklaren Gebieten)",
        }
