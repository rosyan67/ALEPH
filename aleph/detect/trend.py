"""Trend je Zelle: Mann-Kendall mit Sen-Steigung, zwei Korrekturen für Autokorrelation (Statistisches
Grundgerüst, Stand 2026-09-26, nur mit künstlichen Daten geprüft, NICHT auf echte Daten angewandt).

Ablauf (`trend_je_zelle`):
1. Eingang: Monatswerte (Zeit × Breite × Länge), NaN = fehlend. Fehlend heißt: Monat nicht geladen,
   Zelle „nicht geladen“ (Zustand 4 außerhalb der Region), keine Daten, Fehlwert oder unter 50 %
   beobachteten Pixeln. Fehlendes wird nie 0 und geht in keinen Test ein (`lies_reihe`).
2. Schnee: Zellmonate mit Schnee-Verdacht (aleph/detect/schnee.py) werden standardmäßig herausgenommen
   (`schnee_ausschliessen`), gezählt in `n_schnee_ausgeschlossen`. Begründung: Ein Trend über Monate
   mit wechselnder Pixel-Auswahl mischt zwei verschiedene Mittelwerte.
3. Jahreszeit: Von jedem Wert wird der Median desselben Kalendermonats der Zelle abgezogen (nur
   Kalendermonate mit mindestens `Mindestlaengen.je_kalendermonat` Werten; sonst fallen deren Werte weg).
   Getestet wird die Reihe der Abweichungen. Abgezogen wird nur das NIVEAU je Kalendermonat; Mann-Kendall
   vergleicht danach alle Paare (auch Januar mit Juli). Wächst die Jahreszeit-Schwankung mit dem Niveau,
   bleibt ein Rest im 12-Monats-Abstand, den Hamed-Rao mit 3 Lags nicht sieht (nicht am künstlichen
   Würfel geprüft). Der Median stammt nur aus dem untersuchten Zeitfenster (kein Datenleck in spätere Jahre);
   fällt ein Kalendermonat in einzelnen Jahren weg (Schnee), stammt sein Median aus den übrigen Jahren, was
   bei echtem Trend die Steigung leicht verschieben kann (nicht geprüft).
4. Mann-Kendall (unkorrigiert) und Sen-Steigung mit 95-%-Band, ab `Mindestlaengen.mann_kendall`
   gültigen Werten; darunter „nicht bestimmbar“ (NaN), keine Zahl.
5. Zwei Korrekturen für Autokorrelation als GETRENNTE Felder, ab `Mindestlaengen.autokorrelation`:
   Hamed-Rao (Varianz von S) und Prewhitening nach Yue et al. (Reihe). Beide werden je Karte mit
   Benjamini-Hochberg auf αFDR = 2·αglobal (Wilks 2016) korrigiert. Sind sie sich nicht einig, ist
   das ein Unsicherheits-Kennzeichen (`uneinig`), keine Wahlmöglichkeit. `trend_beide`: beide melden.
   EHRLICH: Yue ist bei Autokorrelation freigiebiger als gar keine Korrektur; `trend_beide` war deshalb in
   ALLEN Prüfungen am künstlichen Würfel genau gleich Hamed-Rao. Es ist keine doppelte Absicherung.
5b. Mindestgröße (`min_zellen`, Standard 4, wie die Anomalieerkennung): Gemeldet (`trend_gemeldet`) wird
   eine Zelle nur, wenn sie mit mindestens 3 Nachbarn gleicher Richtung (8er-Nachbarschaft, Datumsgrenze
   geschlossen) eine `trend_beide`-Gruppe bildet. Grund: Hamed-Rao hält das Niveau bei Autokorrelation
   nicht (siehe unten); einzelne falsche Zellen fallen so weg. Das schützt NUR, solange das Rauschen
   räumlich unabhängig ist; bei räumlich zusammenhängendem Rauschen nicht (nicht simuliert).
6. Diagnose: Moran's I (dünn besetzte 8er-Nachbarschaft, Datumsgrenze geschlossen) auf den Resten
   (Abweichung minus Sen-Gerade) für einige Zeitpunkte und auf der Karte der z-Werte. Ein deutlich
   positives I heißt: Nachbarzellen sind nicht unabhängig; die BH-Garantie (unabhängig oder positiv
   abhängig) und die Wilks-Regel (für „mäßige bis starke“ Korrelation) sind dann einzuordnen.
7. Pflichtfelder jeder Ausgabe: Evidenzstufe („beobachtet“), Unsicherheit (Sen-Band, `uneinig`),
   Anzahl gültiger Werte (`n_gueltig`), Methode und Version (Attribute).

Was nicht garantiert ist:
- Die p-Werte sind Normalnäherungen; bei Reihen mit vielen gleichen Werten (dunkle Zellen, 0) ist S
  klein und der Test unempfindlich, aber nicht falsch.
- Die Korrekturen halten das Fehlerniveau bei zeitlicher Abhängigkeit NICHT (künstlicher Würfel, 20 Würfel
  à 2 000 Zellen ohne Trend, BH q = 0,10): Bei AR(1) 0,5 meldeten mit Hamed-Rao 90 % der Würfel mindestens
  eine Zelle (Ziel etwa 10 %), 0,33 % der Fläche; mit eingepflanzten Trends waren 98 von 498 Meldungen
  falsch (etwa 20 % statt höchstens 10 %). Bei AR 0,8: 100 % der Würfel, 4,2 % der Fläche. Die echte
  Autokorrelation der Nachtlichtreihen ist nicht gemessen; vor jeder Trendkarte im Kalibrierungszeitraum
  (2013–2019) die Verteilung von r1 bestimmen. Die Mindestgröße (5b) mildert das, Zahlen im Bericht
  berichte/2026-09-26_statistik-geruest.md. Einzelheiten der Verfahren nicht am Originaltext geprüft.
- `sen_unten`/`sen_oben` sind mit der UNKORRIGIERTEN Varianz gerechnet und bei abhängigen Reihen zu schmal;
  `sen_unten_hr`/`sen_oben_hr` nutzen die Hamed-Rao-Varianz (nur Status 2) und sind das anzuzeigende Band.
- Ein Bruch im Messsystem (Sensor, Aufbereitung) erscheint als Trend. Das Verfahren erkennt ihn nicht.
- Endtest-Sperre: Monate ab 2023-01 nur mit `endtest_freigabe=True` (wie aleph/detect/anomalie.py).
"""

import warnings
from dataclasses import dataclass, field

import numpy as np
import xarray as xr

from aleph.detect import statistik as st
from aleph.detect import wuerfel as lesen
from aleph.detect.anomalie import ENDTEST_AB, EndtestGesperrt, zusammenhaengende_gruppen
from aleph.detect.schnee import SchneeRegel, schnee_verdacht

TREND_VERSION = "0.1.0"
METHODE = (
    "Mann-Kendall mit Sen-Steigung auf Abweichungen vom Kalendermonats-Median; Autokorrelation korrigiert "
    "nach Hamed-Rao (1998) und nach Yue et al. (2002, Prewhitening), getrennt; Benjamini-Hochberg mit "
    "αFDR = 2·αglobal (Wilks 2016)"
)
STATUS_TEXT = {0: "nicht bestimmbar (zu wenige gültige Werte)", 1: "nur unkorrigiert bestimmbar (zu kurz für Autokorrektur)",
               2: "bestimmt"}


@dataclass(frozen=True)
class TrendEinstellungen:
    min_beobachtet_anteil: float = 0.5  # wie Anomalieerkennung (Schwellen.min_beobachtet_anteil)
    alpha_global: float = st.ALPHA_GLOBAL
    mindest: st.Mindestlaengen = field(default_factory=st.Mindestlaengen)
    schnee_ausschliessen: bool = True
    schnee_regel: SchneeRegel = field(default_factory=SchneeRegel)
    niveau_band: float = 0.95
    block_zellen: int = 4000  # Zellen je Rechenblock (Speicher: etwa 45 kB je Zelle für die Sen-Steigung)
    moran_zeitpunkte: int = 12
    helligkeit_relativ: float = 1.0  # relative Steigung nur, wo der Median >= 1 nW·cm⁻²·sr⁻¹
    min_zellen: int = 4  # Mindestgröße einer gemeldeten Trendgruppe (wie Schwellen.min_zellen der Anomalie)


def lies_reihe(wuerfel, feld: str, von: tuple[int, int], bis: tuple[int, int], region_maske: np.ndarray | None = None,
               min_beobachtet_anteil: float = 0.5, endtest_freigabe: bool = False) -> dict:
    """Liest Monatsreihen für den Trend. Nur fertige Monate (1) und, mit `region_maske`, Monate mit Zustand 4.

    Nicht fertige Monate fehlen ganz (NaN-Scheiben), nicht geladene Zellen, Zellen ohne gültige Pixel und
    Zellen unter `min_beobachtet_anteil` sind NaN. Rückgabe: dict mit `werte` (Zeit × Breite × Länge,
    float32), `beobachtet_anteil`, `monate` (alle Monate von..bis), `zustand` je Monat („fehlt“, „fertig“,
    „nur Region“), `breite`, `laenge`.
    """
    if bis >= ENDTEST_AB and not endtest_freigabe:
        raise EndtestGesperrt(f"Trend bis {bis[0]:04d}-{bis[1]:02d} reicht in den Endtest-Zeitraum ab 2023-01.")
    achse = [m for m in lesen.zeitachse_monate(wuerfel) if von <= m <= bis]
    fertig = set(lesen.fertige_monate(wuerfel))
    breite, laenge = lesen.gitter(wuerfel)
    variablen = [f"{feld}_mittel_beobachtet", f"{feld}_gueltige_pixel", f"{feld}_aufgefuellt_pixel"]
    werte = np.full((len(achse), len(breite), len(laenge)), np.nan, dtype="float32")
    anteil = np.full(werte.shape, np.nan, dtype="float32")
    zustand = []
    for i, m in enumerate(achse):
        try:
            if region_maske is not None:
                ds = lesen.lies_monate_mit_region(wuerfel, [m], variablen, region_maske)
            elif m in fertig:
                ds = lesen.lies_monate(wuerfel, [m], variablen)
            else:
                zustand.append("fehlt")
                continue
        except lesen.MonatNichtFertig:
            zustand.append("fehlt")
            continue
        g = ds[variablen[1]].values[0].astype("float64")
        a = ds[variablen[2]].values[0].astype("float64")
        beob = np.where((g > 0) & (a >= 0) & (a <= g), (g - a) / 3600.0, np.nan)
        x = ds[variablen[0]].values[0].astype("float64")
        ok = np.isfinite(x) & np.isfinite(beob) & (beob >= min_beobachtet_anteil)
        if "nicht_geladen" in ds:
            ok &= ~ds["nicht_geladen"].values[0]
        werte[i] = np.where(ok, x, np.nan)
        anteil[i] = np.where(np.isfinite(beob), beob, np.nan)
        zustand.append("fertig" if m in fertig else "nur Region")
    return {"werte": werte, "beobachtet_anteil": anteil, "monate": achse, "zustand": zustand, "breite": breite, "laenge": laenge}


def _jahreszeit_abziehen(werte: np.ndarray, monate: list[tuple[int, int]], min_je_monat: int) -> tuple[np.ndarray, np.ndarray]:
    """Abweichung vom Median desselben Kalendermonats je Zelle. Kalendermonate mit zu wenigen Werten -> NaN."""
    ergebnis = np.full(werte.shape, np.nan, dtype="float32")
    median_gesamt = np.full(werte.shape[1:], np.nan)
    kalender = np.array([m for _, m in monate])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        for k in range(1, 13):
            idx = np.flatnonzero(kalender == k)
            if idx.size == 0:
                continue
            teil = werte[idx]
            anzahl = np.isfinite(teil).sum(axis=0)
            med = np.nanmedian(teil, axis=0)
            ok = anzahl >= min_je_monat
            ergebnis[idx] = np.where(ok[None], teil - med[None], np.nan)
        median_gesamt = np.nanmedian(werte, axis=0)
    return ergebnis, median_gesamt


@dataclass
class TrendErgebnis:
    zellen: xr.Dataset
    zusammenfassung: dict
    einstellungen: TrendEinstellungen
    version: str = TREND_VERSION


def trend_je_zelle(werte: np.ndarray, monate: list[tuple[int, int]], breite: np.ndarray, laenge: np.ndarray,
                   beobachtet_anteil: np.ndarray | None = None, einstellungen: TrendEinstellungen | None = None,
                   endtest_freigabe: bool = False) -> TrendErgebnis:
    """Trend je Zelle über `monate` (lückenlose Monatsachse, fehlende Monate als NaN-Scheiben).

    `werte`: (Zeit, Breite, Länge); `beobachtet_anteil` gleiche Form (für den Schnee-Verdacht; ohne ihn
    wird kein Schnee-Verdacht gebildet, das steht dann in der Zusammenfassung).
    """
    e = einstellungen or TrendEinstellungen()
    if max(monate) >= ENDTEST_AB and not endtest_freigabe:
        raise EndtestGesperrt("Trend reicht in den Endtest-Zeitraum ab 2023-01; nur mit endtest_freigabe=True.")
    werte = np.array(werte, dtype="float32", copy=True)
    t_len, ny, nx = werte.shape
    if len(monate) != t_len:
        raise ValueError("monate und Zeitachse von werte passen nicht zusammen.")
    schritte = [(j - monate[0][0]) * 12 + (m - monate[0][1]) for j, m in monate]
    if schritte != list(range(t_len)):
        raise ValueError("monate muss eine lückenlose Monatsachse sein (fehlende Monate als NaN übergeben).")

    n_schnee = np.zeros((ny, nx), dtype="int16")
    schnee_info = "nicht gebildet (kein beobachteter Anteil übergeben)"
    if beobachtet_anteil is not None:
        for i, (_, m) in enumerate(monate):
            verdacht = schnee_verdacht(breite, m, beobachtet_anteil[i], e.schnee_regel) & np.isfinite(werte[i])
            n_schnee += verdacht
            if e.schnee_ausschliessen:
                werte[i][verdacht] = np.nan
        schnee_info = "ausgeschlossen" if e.schnee_ausschliessen else "gezählt, nicht ausgeschlossen"

    abw, median_niveau = _jahreszeit_abziehen(werte, monate, e.mindest.je_kalendermonat)
    y_alle = abw.reshape(t_len, ny * nx)
    n_alle = np.isfinite(y_alle).sum(axis=0)
    felder = {k: np.full(ny * nx, np.nan) for k in (
        "sen_steigung", "sen_unten", "sen_oben", "sen_unten_hr", "sen_oben_hr", "z_mk", "p_mk", "z_hamed_rao", "p_hamed_rao", "faktor_hamed_rao",
        "z_yue", "p_yue", "r1_yue")}
    status = np.zeros(ny * nx, dtype="int8")
    status[n_alle >= e.mindest.mann_kendall] = 1
    status[n_alle >= e.mindest.autokorrelation] = 2
    kandidaten = np.flatnonzero(status > 0)
    for start in range(0, kandidaten.size, e.block_zellen):
        idx = kandidaten[start:start + e.block_zellen]
        y = y_alle[:, idx].astype("float64")
        mk = st.mann_kendall(y)
        sen = st.sen_steigung(y, mk["var_s"], e.niveau_band, behalte_sortierung=True)
        felder["sen_steigung"][idx] = sen["steigung"] * 12.0  # je Jahr
        felder["sen_unten"][idx] = sen["unten"] * 12.0
        felder["sen_oben"][idx] = sen["oben"] * 12.0
        felder["z_mk"][idx] = mk["z"]
        voll = status[idx] == 2
        if voll.any():
            yv = y[:, voll]
            b = sen["steigung"][voll]
            hr = st.hamed_rao(yv, b, mk["var_s"][voll])
            z_hr = np.full(b.shape, np.nan)
            ok = np.isfinite(hr["var_s"]) & (hr["var_s"] > 0)
            s_v = mk["s"][voll]
            z_hr[ok] = (s_v[ok] - np.sign(s_v[ok])) / np.sqrt(hr["var_s"][ok])
            z_hr[(~ok) & (s_v == 0)] = 0.0
            yue = st.yue_vorbleichung(yv, b)
            mk_yue = st.mann_kendall(yue["reihe"])
            ziel = idx[voll]
            felder["z_hamed_rao"][ziel] = z_hr
            felder["faktor_hamed_rao"][ziel] = hr["faktor"]
            felder["z_yue"][ziel] = np.where(mk_yue["n"] >= e.mindest.autokorrelation, mk_yue["z"], np.nan)
            felder["r1_yue"][ziel] = yue["r1"]
            unten_hr, oben_hr = st.sen_band(sen["_sortiert"][:, voll], sen["paare"][voll], hr["var_s"], e.niveau_band)
            felder["sen_unten_hr"][ziel] = unten_hr * 12.0
            felder["sen_oben_hr"][ziel] = oben_hr * 12.0
        del sen
    for name in ("mk", "hamed_rao", "yue"):
        felder[f"p_{name}"] = st.normal_zweiseitig(felder[f"z_{name}"])
    q = st.alpha_fdr(e.alpha_global)
    sig_mk = st.benjamini_hochberg(felder["p_mk"], q)
    sig_hr = st.benjamini_hochberg(felder["p_hamed_rao"], q)
    sig_yue = st.benjamini_hochberg(felder["p_yue"], q)
    beide_bestimmt = np.isfinite(felder["p_hamed_rao"]) & np.isfinite(felder["p_yue"])
    uneinig = beide_bestimmt & (sig_hr != sig_yue)
    trend_beide = beide_bestimmt & sig_hr & sig_yue & (np.sign(felder["z_hamed_rao"]) == np.sign(felder["z_yue"]))
    gemeldet = np.zeros(ny * nx, dtype=bool)
    for vorz in (1, -1):
        maske = (trend_beide & (np.sign(felder["z_hamed_rao"]) == vorz)).reshape(ny, nx)
        gruppen, anzahl = zusammenhaengende_gruppen(maske)
        if anzahl:
            groesse = np.bincount(gruppen.ravel(), minlength=anzahl + 1)
            gross = groesse >= e.min_zellen
            gross[0] = False
            gemeldet |= gross[gruppen].ravel()
    med = median_niveau.reshape(-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        relativ = np.where(med >= e.helligkeit_relativ, 100.0 * felder["sen_steigung"] / med, np.nan)

    form = (ny, nx)
    dims = ("breite", "laenge")

    def karte(a, dtype="float32"):
        return (dims, np.asarray(a).reshape(form).astype(dtype))

    zellen = xr.Dataset(
        {
            "sen_steigung": karte(felder["sen_steigung"]), "sen_unten": karte(felder["sen_unten"]),
            "sen_oben": karte(felder["sen_oben"]), "sen_unten_hr": karte(felder["sen_unten_hr"]),
            "sen_oben_hr": karte(felder["sen_oben_hr"]), "sen_relativ_prozent": karte(relativ),
            "z_mk": karte(felder["z_mk"]), "p_mk": karte(felder["p_mk"]),
            "z_hamed_rao": karte(felder["z_hamed_rao"]), "p_hamed_rao": karte(felder["p_hamed_rao"]),
            "faktor_hamed_rao": karte(felder["faktor_hamed_rao"]),
            "z_yue": karte(felder["z_yue"]), "p_yue": karte(felder["p_yue"]), "r1_yue": karte(felder["r1_yue"]),
            "signifikant_unkorrigiert": karte(sig_mk, bool), "signifikant_hamed_rao": karte(sig_hr, bool),
            "signifikant_yue": karte(sig_yue, bool), "uneinig": karte(uneinig, bool), "trend_beide": karte(trend_beide, bool),
            "trend_gemeldet": karte(gemeldet, bool),
            "n_gueltig": karte(n_alle, "int16"), "n_schnee_ausgeschlossen": (dims, n_schnee), "status": karte(status, "int8"),
        },
        coords={"breite": breite, "laenge": laenge},
        attrs={
            "evidenzstufe": "beobachtet",
            "methode": METHODE,
            "version": f"trend {TREND_VERSION}, statistik {st.STATISTIK_VERSION}",
            "unsicherheit": ("sen_unten_hr/sen_oben_hr: 95-%-Band der Sen-Steigung mit Hamed-Rao-Varianz (anzuzeigen); "
                             "sen_unten/sen_oben: ohne Autokorrektur, zu schmal; uneinig: Korrekturen widersprechen sich; "
                             "Fehlerniveau bei Autokorrelation nicht eingehalten (Modulkopf)"),
            "einheit_steigung": "nW·cm⁻²·sr⁻¹ je Jahr (Abweichung vom Kalendermonats-Median)",
            "alpha_fdr": q,
            "status_codes": "; ".join(f"{k} {v}" for k, v in STATUS_TEXT.items()),
            "schnee": schnee_info,
            "zeitraum": f"{monate[0][0]:04d}-{monate[0][1]:02d} bis {monate[-1][0]:04d}-{monate[-1][1]:02d}",
        },
    )
    zusammenfassung = _zusammenfassung(zellen, abw, e)
    return TrendErgebnis(zellen=zellen, zusammenfassung=zusammenfassung, einstellungen=e)


def _zusammenfassung(z: xr.Dataset, abw: np.ndarray, e: TrendEinstellungen) -> dict:
    breite = z["breite"].values
    bestimmt = z["status"].values == 2
    ergebnis = {
        "zellen_gesamt": int(z["status"].size),
        "zellen_bestimmt": int(bestimmt.sum()),
        "zellen_nur_unkorrigiert": int((z["status"].values == 1).sum()),
        "zellen_nicht_bestimmbar": int((z["status"].values == 0).sum()),
    }
    for name in ("signifikant_unkorrigiert", "signifikant_hamed_rao", "signifikant_yue", "uneinig", "trend_beide", "trend_gemeldet"):
        maske = z[name].values
        ergebnis[f"{name}_zellen"] = int((maske & bestimmt).sum())  # gleiche Bezugsmenge wie der Flächenanteil
        ergebnis[f"{name}_flaechenanteil"] = st.flaechenanteil(maske, bestimmt, breite) if bestimmt.any() else float("nan")
    ergebnis["moran"] = _moran_diagnose(z, abw, e)
    return ergebnis


def _moran_diagnose(z: xr.Dataset, abw: np.ndarray, e: TrendEinstellungen) -> dict:
    """Moran's I der Reste (Abweichung minus Sen-Gerade) an einigen Zeitpunkten und der z-Karte (Hamed-Rao)."""
    bestimmt = z["status"].values == 2
    if int(bestimmt.sum()) < e.mindest.moran_zellen:
        return {"status": f"nicht bestimmbar (weniger als {e.mindest.moran_zellen} bestimmte Zellen)"}
    w, ys, xs = st.nachbarschaft(bestimmt)
    t_len = abw.shape[0]
    b = z["sen_steigung"].values[ys, xs] / 12.0
    zeitpunkte = np.unique(np.linspace(0, t_len - 1, min(e.moran_zeitpunkte, t_len)).astype(int))
    reihe = abw[:, ys, xs].astype("float64")
    t = np.arange(t_len)[:, None]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        achse = np.nanmedian(reihe - b[None] * t, axis=0)
    rest = reihe - (achse[None] + b[None] * t)
    werte_i = []
    for k in zeitpunkte:
        spalte = rest[k]
        ok = np.isfinite(spalte)
        if ok.sum() < e.mindest.moran_zellen:
            continue
        if ok.all():
            werte_i.append(float(st.morans_i(spalte, w)["i"][0]))
        else:
            teil = w[ok][:, ok]
            werte_i.append(float(st.morans_i(spalte[ok], teil)["i"][0]))
    z_karte = z["z_hamed_rao"].values[ys, xs]
    ok = np.isfinite(z_karte)
    i_z = st.morans_i(z_karte[ok], w[ok][:, ok]) if ok.sum() >= e.mindest.moran_zellen else None
    return {
        "reste_i_median": float(np.median(werte_i)) if werte_i else float("nan"),
        "reste_i_min": float(np.min(werte_i)) if werte_i else float("nan"),
        "reste_i_max": float(np.max(werte_i)) if werte_i else float("nan"),
        "reste_zeitpunkte": len(werte_i),
        "z_karte_i": float(i_z["i"][0]) if i_z else float("nan"),
        "erwartung_unabhaengig": float(-1.0 / (int(ok.sum()) - 1)) if ok.sum() > 1 else float("nan"),
        "hinweis": "Diagnose: deutlich positives I = Nachbarzellen abhängig; kein Test mit Garantie.",
    }
