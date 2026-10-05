"""Anomalieerkennung nach ARCHITECTURE.md Abschnitt 6 (Etappe 3, Version 0.1).

Pro Layer-Feld, pro Gitterzelle, pro Monat wird geprüft, ob der Wert ungewöhnlich weit
von dem entfernt liegt, was derselbe Kalendermonat in früheren Jahren zeigte.

Ablauf je Monat (`erkenne_monat`; über mehrere Monate `erkenne_zeitraum`):
1. Lesen: nur als fertig markierte Monate (aleph/detect/wuerfel.py). Ein nicht geladener
   Monat ist nie „keine Daten".
2. Datenlage je Zelle: Der Anteil BEOBACHTETER Pixel ist (gültige - aufgefüllte) / Pixel je
   Zelle. Aufgefüllte Pixel (Quality 2, aus historischen Daten ergänzt) zählen nie als
   beobachtet. Zellen mit weniger als `min_beobachtet_anteil` beobachteten Pixeln werden
   nicht bewertet („Datenlage unzureichend"); das gilt für den untersuchten Monat und für
   jeden Monat der Basislinie.
3. Basislinie: derselbe Kalendermonat aller FRÜHEREN Jahre, die fertig sind und in dieser
   Zelle ausreichende Datenlage haben. Der untersuchte Monat und spätere Jahre sind nie
   dabei. Weniger als `min_basisjahre` Werte: Zelle nicht bewertet.
4. Robuste Abweichung: z = (Wert - Median) / (Streuung * sqrt(1 + pi/(2n))), Streuung =
   max(1,4826 * MAD, gemeinsame Mindest-Streuung, `abs_min_streuung`). Der Faktor
   berücksichtigt, dass der Median selbst aus n Werten geschätzt ist (Varianz des Medians
   bei Normalverteilung etwa pi/(2n) mal Varianz der Einzelwerte).
5. NOMINELLER p-Wert aus der Standardnormalverteilung, dann Benjamini-Hochberg (`q_bh`) über
   ALLE bewertbaren Zellen des Monats, zusätzlich ein Mindestwert |z| >= `z_min_zelle` je
   Zelle. Ehrlich beschrieben: Bei bis zu etwa 87 000 bewertbaren Zellen ist jede Zelle mit
   |z| >= 5 automatisch auch BH-auffällig (p = 5,7e-7 gegen die Grenze 0,05/m). Erst bei
   sehr vielen Zellen (z. B. 1 Million) hält BH einzelne Zellen knapp über 5 zurück. Was in
   der Praxis wirkt, sind der feste Mindestwert |z| >= 5 und die Mindestgröße; BH ist die
   in Abschnitt 6 verlangte zusätzliche Korrektur. Eine Kontrolle der Falschmeldungsrate auf
   q_bh besteht NICHT (siehe unten).
6. Mindestgröße: Nur zusammenhängende Zellen gleicher Richtung (8er-Nachbarschaft, am
   Längengrad-Umbruch geschlossen) ab `min_zellen` werden gemeldet. Optional Mindestdauer
   (`min_dauer_monate`, nur in `erkenne_zeitraum`).
7. Ausgabe: Zellkarten und eine Ereignistabelle mit Band (auffällig / stark / extrem),
   Richtung (Anstieg / Rückgang) und Datenlage (gut / mittel / dünn). Evidenzstufe der
   Erkennung: `beobachtet` (Abweichung in gemessenen Daten; das Benennen folgt in Abschnitt 7).

Warum die gemeinsame Mindest-Streuung (reproduzierbar mit scripts/simuliere_mad_raender.py,
2 Millionen Zellen mal 3 Läufe, Startwert 7, reines normalverteiltes Rauschen ohne Anomalie):
Median/MAD aus wenigen Werten hat viel schwerere Ränder als die Normalverteilung, weil ein
zufällig kleines MAD den Nenner fast verschwinden lässt. Nur mit MAD überschreitet die Statistik
bei n = 5 Basisjahren den Wert 8 in 2,3 % der Fälle (Normalverteilung: 1e-15), bei n = 12 den Wert 12
in 5,7e-5 (Normal: 4e-33). Bei rund 500 000 Zellen je Monat würde die Korrektur damit nichts mehr
ausrichten. Die Mindest-Streuung (`pool_perzentil`, Standard 75. Perzentil der relativen Streuung
aller Zellen mit Basislinie, nur aus der Basislinie geschätzt, also unabhängig vom untersuchten
Wert) bringt den Rand bei GLEICHMÄSSIGEM Rauschen unter das Normalverteilungs-Niveau (T >= 4 in
etwa 5e-6 statt 6,3e-5; T >= 5 in keinem von 6 Millionen Fällen).

Nachtrag 2026-09-26 (Statistisches Grundgerüst, Version 0.2.0):
- BERICHTIGT: Die Basislinie nahm bisher `<feld>_mittel` (Mittel über beobachtete UND aufgefüllte Pixel),
  der untersuchte Monat dagegen `<feld>_mittel_beobachtet`. Beide Seiten nutzen jetzt das Mittel nur über
  beobachtete Pixel, wie der Kommentar in `_bewerte_monat` es schon verlangte. (Künstliche Würfel waren
  nicht betroffen, weil dort beide Mittel gleich sind; echte Daten wurden damit nie ausgewertet.)
- Klassischer z-Wert (Mittelwert/Standardabweichung, `z_klassisch`) PARALLEL zum robusten (Median/MAD).
  Beide mit derselben Mindest-Streuung, damit nur der Unterschied Mittel/Median bzw. Standardabweichung/MAD
  wirkt. `z_uneinig`: Die beiden Werte widersprechen sich bei der Zellschwelle (einer >= z_min_zelle, der
  andere nicht). Das ist ein DIAGNOSE-Kennzeichen (z. B. Ausreißer in der Basislinie), keine Auswahl:
  gemeldet wird weiter nach dem robusten Wert.
- Schnee-Verdacht (aleph/detect/schnee.py), gleiche Behandlung wie beim Trend (Auflage statistik-pruefer
  2026-09-26): Zellmonate mit Verdacht werden NICHT bewertet – im untersuchten Monat (Karte `schnee_verdacht`,
  Datenlage 0, also nie Teil eines Ereignisses) und in der Basislinie (Wert fällt heraus, zählt nicht zu
  n_basis). Grund: Moskau 2018-02 zeigt, dass solche Monate um ein Vielfaches abweichen können, und ein
  verschneiter Basismonat verschiebt Median und MAD. Verglichen wird ohnehin nur mit demselben Kalendermonat.
- Pflichtfelder in jeder Ereigniszeile: evidenzstufe, unsicherheit, n_zellen und n_basis_min (gültige
  Werte), methode, erkennung_version.

Endtest-Sperre (ARCHITECTURE.md 9a): Der Endtest (2023-2025) darf nur einmal pro Hauptversion
angesehen werden. Solange 2013-2017 nicht geladen sind, sind wegen `min_basisjahre` überhaupt
nur Monate ab 2023 bewertbar, also genau der Endtest-Zeitraum. Deshalb verweigern
`erkenne_monat` und `erkenne_zeitraum` Monate ab `ENDTEST_AB` ohne ausdrückliche
`endtest_freigabe=True` (`EndtestGesperrt`). Zu wissen: Auch bei vollständigem Würfel sind
2013-2017 nur Basis und nie bewertbar; der Kalibrierungszeitraum 2013-2019 hat für die
Erkennung selbst nur 24 bewertbare Monate (2018-2019) mit 5 bis 6 Basisjahren, also genau dort,
wo die p-Werte am schlechtesten sind. Das ist ein offenes Problem für die Kalibrierung, ebenso
der Widerspruch zwischen ARCHITECTURE.md 9 (Blindtest 2019-2024) und 9a (Endtest 2023-2025).
Die Sperre schützt nur `erkenne_monat` und `erkenne_zeitraum`; die Lesefunktionen in
`wuerfel.py` und `_bewerte_monat` sind offen. Jede Freigabe löst eine Warnung aus
(`EndtestFreigabeHinweis`), damit sie im Lauf sichtbar bleibt; ob der Endtest tatsächlich nur
einmal angesehen wird, kann der Code nicht durchsetzen. Der Endtest ist außerdem bei der Datenqualität
vorbelastet (siehe unten, 50-%-Grenze).

Was nicht garantiert ist (bitte nicht als Garantie darstellen):
- Sind die Zellen sehr unterschiedlich verrauscht, bleiben die p-Werte auch mit der
  Mindest-Streuung um Größenordnungen zu optimistisch (Simulation, Streuung der Zellen
  lognormal mit Sigma 0,5: bei T >= 5 das 175- bis 960-fache des Normalwerts (n = 12 bis 5), bei
  T >= 6 etwa das 10^4- bis 10^5-fache; bei Sigma 1,0 noch mehr; das Ausmaß der Verschiedenheit in
  echten Daten ist unbekannt).
  Sie sind nominell, der Anteil falscher Meldungen ist NICHT auf q_bh begrenzt. (Ebenso gilt
  „BH hält eine Zelle knapp über 5 zurück" nur, solange sonst nichts auffällt; bei einem Ereignis
  mit vielen starken Zellen wird die Grenze q*k/m deutlich weicher.) Auch bei
  exakten p-Werten würde BH höchstens den Anteil falscher ZELLEN kontrollieren (nicht
  falscher Ereignisse), je Monat und ohne Kontrolle über mehrere Monate. Im Test mit
  ungleichmäßigem Rauschen (48 Monate, 960 000 Zellen-Monate, Streuung lognormal Sigma 0,5)
  wurden 155 Zellen markiert, aber kein Ereignis gemeldet (gemessen 2026-09-24).
- Eine Falschalarmrate wird nicht genannt und kann an echten Daten nicht einfach „gezählt"
  werden, weil dort echte Ereignisse stecken. Nötig sind (a) der Vergleich des Mittelteils der
  |z|-Verteilung (Perzentile bis etwa 99,9 %) mit der Normalverteilung; das prüft nur die
  KALIBRIERUNG im Mittelteil, nicht die Rate jenseits von 5 Sigma, wo sich die Falschmeldung
  entscheidet und schwere Ränder typisch sind; große echte Ereignisse (über 0,1 % der Zellen) und
  Trends verfälschen auch den Mittelteil, (b) Einspritz-Tests (künstliche Änderungen in echte
  Kalibrierdaten einbauen) und (c) eine Stichprobe von Hand (ARCHITECTURE.md 9 und 9a).
- Räumlich zusammenhängende Störungen im untersuchten Monat (Wolken, Schnee, Sensor)
  erscheinen als echtes Ereignis; die Mindestgröße schützt nur bei räumlich unabhängigem
  Rauschen. Langsame Trends (Städtewachstum, LED-Umrüstung) verschieben z (Test: 8 % je Jahr,
  Median-z etwa +1,5, keine Ereignisse) UND blähen die MAD der Basislinie auf, was die Erkennung
  unempfindlicher macht; eine dauerhafte Änderung wandert nach einigen Jahren in die Basislinie
  und verschwindet (Ausbaustufe 2, STL, ist nicht Teil dieser Version).
- Schwere Ränder des Rauschens (Student-t, 3 Freiheitsgrade): 902 markierte Zellen von 960 000
  Zellen-Monaten, kein Ereignis (gemessen 2026-09-24, wie beim ungleichmäßigen Rauschen).
- Gemeinsame Verschiebungen eines ganzen Monats oder Jahres (Sensor, Aufbereitungsversion,
  Ausnahmejahre wie 2020 in der Basis) erzeugen Tausende Meldungen. Die Monatsdiagnose
  (`Erkennung.diagnose`, `warnung`) kennzeichnet einen solchen Monat als „verdächtig", ändert
  aber nichts an den Ereignissen (ARCHITECTURE.md 6.6: Messsystem-Brüche sind pro Layer zu
  dokumentieren).
- Rückgänge sind schwerer zu erkennen als Anstiege: Die Streuung beträgt mindestens
  rho * Median, und ein Rückgang ist auf -100 % begrenzt. Ein totaler Ausfall erreicht höchstens
  |z| = 1 / (rho * sqrt(1 + pi/(2n))); bei rho >= etwa 0,18 wird die Zellschwelle |z| >= 5 nie
  erreicht, bei rho >= etwa 0,08 das Band „extrem". Anstiege sind nach oben unbegrenzt. Die
  Bänder bedeuten für Anstieg und Rückgang deshalb nicht dasselbe („wie viele typische
  Schwankungen", nicht „wie viel Prozent"). Ob ein Wechsel auf ein Verhältnis oder eine
  logarithmische Skala nötig ist, klärt die Kalibrierung (das reale rho ist unbekannt).
- (Stand 2026-09-26: Ziel und Basislinie nutzen nur noch das Mittel über BEOBACHTETE Pixel. Der folgende
  Absatz beschreibt die frühere Nutzung des gemeinsamen Mittels und gilt so nicht mehr; das neue Risiko ist
  der Auswahl-Effekt: Sind nur wenige Pixel beobachtet, ist das Mittel eines anderen Teils der Zelle –
  siehe aleph/detect/schnee.py.) Früher: Der Zellmittelwert mischt beobachtete und aufgefüllte Pixel. Aufgefüllte Pixel sind aus historischen Daten abgeleitet und
  dämpfen deshalb eine echte Änderung (bei 50 % Auffüllung erscheint ein Rückgang um 90 %
  nur noch als etwa 45 %). Ebenso glättet die Auffüllung die Monate der Basislinie und
  verkleinert deren Streuung, was z vergrößert; die Dämpfung der Änderung im untersuchten
  Monat verkleinert z. Die Richtung des Nettoeffekts auf z ist unbekannt, ebenso die Größe;
  der Generator bildet die Kopplung nicht nach. Die Herkunft der Auffüllung (nur frühere oder
  auch spätere Daten?) ist NICHT geklärt: Stammen aufgefüllte Pixel auch aus späteren Daten,
  steckt in den Basismonaten Information aus der Zukunft (Datenleck in Validierung und Endtest).
  Das ist vor dem Einsatz auf echten Daten an der Produktbeschreibung des Anbieters zu klären.
- Zellen mit weniger als 3600 gültigen Pixeln (Rand, Küste) ändern ihre Zusammensetzung von
  Monat zu Monat; das kann Scheinänderungen erzeugen. Der Anteil beobachteter Pixel rechnet
  sie mit, gleicht die Zusammensetzung aber nicht aus.
- Die Fläche einer 0,25°-Zelle sinkt mit der Breite (bei 60°N halb, bei 80°N ein Sechstel);
  „mindestens 4 Zellen" heißt je nach Breite sehr verschiedene Flächen. Die Ereignistabelle
  nennt deshalb `flaeche_km2`.
- Die gemeinsame Mindest-Streuung ist nur nach der Zahl der Basisjahre gruppiert, nicht nach
  Helligkeit. Dunkle Zellen sind relativ verrauschter und können das Perzentil bestimmen;
  helle Zellen werden dann unempfindlicher. Zu prüfen in der Kalibrierung.
- Die 50-%-Grenze für beobachtete Pixel wurde nach den im LOG (2026-09-22) festgehaltenen
  Anteilen aufgefüllter Pixel des Testmonats 2024-01 gewählt (nur Datenqualität, nicht
  Ereignisse); 2024 liegt im Endtest-Zeitraum.
- Alle Schwellen sind Startwerte aus Überlegung und Simulation, nicht an echten Daten
  festgelegt. Sie stehen in `Schwellen` und werden im Kalibrierungszeitraum angepasst.
- `_num` (mittlere Nächte je Pixel) wird nicht verwendet, weil keine belastbare Untergrenze
  bekannt ist (Median bei near_nadir 1,4 Nächte, LOG 2026-09-22). Folge: Ein Monat, in dem
  Zellen überwiegend aus einer einzigen Nacht bestehen, ist verrauschter, und das ist räumlich
  zusammenhängend (Wolkengürtel, Regenzeit); solche Zellen können wie ein echtes Ereignis wirken.
- Die Simulationszahlen stammen von `scripts/simuliere_mad_raender.py` (Entwicklungswerkzeug,
  nicht Teil der Pipeline) mit dem heutigen Faktor sqrt(1 + pi/(2n)); die Ergebnisse stehen im LOG.md.
- Speicher: `erkenne_zeitraum` hält die Ergebnisse aller Monate im Arbeitsspeicher (je Monat
  einige Dutzend MB auf dem echten Gitter). Für lange Zeiträume abschnittsweise aufrufen.
- Die Zellkarte eines nicht geladenen oder nicht bewertbaren Monats hat überall Datenlage 0
  („unzureichend"); unterscheidbar ist das nur über `status` (steht auch als Attribut `status`
  im Zellen-Dataset).
"""

import warnings
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd
import xarray as xr

from aleph.detect import wuerfel as lesen
from aleph.detect.schnee import SchneeRegel, schnee_verdacht
from aleph.detect.statistik import benjamini_hochberg, normal_zweiseitig
from aleph.detect.statistik import zellflaeche_km2 as _zellflaeche_km2

ERKENNUNG_VERSION = "0.2.0"
METHODE = (
    "robuste Abweichung (Median/MAD, gemeinsame Mindest-Streuung) mit klassischem z (Mittel/Standardabweichung) "
    "parallel; derselbe Kalendermonat früherer Jahre; Benjamini-Hochberg auf nominellen p-Werten, |z| >= z_min, Mindestgröße"
)

# Endtest-Zeitraum (ARCHITECTURE.md 9a: 2023-2025, nur einmal pro Hauptversion ansehen).
ENDTEST_AB = (2023, 1)
ERDRADIUS_KM = 6371.0

DATENLAGE_NAMEN = {0: "unzureichend", 1: "dünn", 2: "mittel", 3: "gut"}
BAND_NAMEN = {0: "keines", 1: "auffällig", 2: "stark", 3: "extrem"}
RICHTUNG_NAMEN = {-1: "Rückgang", 1: "Anstieg"}


@dataclass(frozen=True)
class Schwellen:
    """Alle einstellbaren Werte an einer Stelle (Begründung: Modul-Doku und LOG.md 2026-09-24)."""

    pixel_pro_zelle: int = 3600  # 60 x 60 Rohpixel je 0,25°-Zelle (Nachtlicht)
    zellgroesse_grad: float = 0.25  # Kantenlänge einer Gitterzelle (ARCHITECTURE.md E1), für die Fläche

    # Datenlage
    min_beobachtet_anteil: float = 0.5  # darunter: unzureichend
    datenlage_mittel_anteil: float = 0.7
    datenlage_gut_anteil: float = 0.9
    min_basisjahre: int = 5  # darunter: unzureichend (Stufe „dünn" beginnt hier)
    datenlage_mittel_basisjahre: int = 6
    datenlage_gut_basisjahre: int = 8

    # Abweichung
    mad_faktor: float = 1.4826  # macht MAD bei Normalverteilung vergleichbar mit der Standardabweichung
    abs_min_streuung: float = 0.5  # nW·cm⁻²·sr⁻¹; verhindert Riesenwerte in dunklen Zellen
    pool_perzentil: float = 75.0
    pool_helligkeit: float = 1.0  # nur Zellen ab diesem Median bestimmen die gemeinsame relative Streuung
    min_zellen_fuer_pool: int = 100

    # Korrektur, Mindestwert, Mindestgröße, Dauer
    q_bh: float = 0.05
    z_min_zelle: float = 5.0
    min_zellen: int = 4
    min_dauer_monate: int = 1

    # Bänder (nach |z|)
    z_stark: float = 8.0
    z_extrem: float = 12.0

    # Monatsdiagnose „globale Verschiebung" (Startwerte, nicht kalibriert, nur an künstlichen Gittern
    # geprüft): Median der z-Werte und Anteil markierter Zellen, gebildet über die HELLEN bewertbaren
    # Zellen (Basislinien-Median >= pool_helligkeit; dunkle Zellen haben z nahe 0 und würden eine
    # Verschiebung verdünnen). Ein Median weit von 0 oder ein ungewöhnlich hoher Anteil deutet auf eine
    # Verschiebung des ganzen Monats statt auf lokale Ereignisse.
    diagnose_median_z: float = 0.5
    diagnose_anteil_markiert: float = 0.10  # ein großes lokales Ereignis (Land, Region) soll nicht als „global" gelten

    # Schnee-Verdacht (aleph/detect/schnee.py): betroffene Zellmonate werden nicht bewertet
    schnee_regel: SchneeRegel = field(default_factory=SchneeRegel)

    def __post_init__(self):
        if not (0 < self.min_beobachtet_anteil <= self.datenlage_mittel_anteil <= self.datenlage_gut_anteil <= 1):
            raise ValueError("Datenlage-Anteile müssen 0 < unzureichend <= mittel <= gut <= 1 erfüllen.")
        if not (2 <= self.min_basisjahre <= self.datenlage_mittel_basisjahre <= self.datenlage_gut_basisjahre):
            raise ValueError("Basisjahre müssen 2 <= min <= mittel <= gut erfüllen.")
        if not (0 < self.z_min_zelle <= self.z_stark <= self.z_extrem):
            raise ValueError("Bänder müssen 0 < z_min_zelle <= z_stark <= z_extrem erfüllen.")
        if not (0 < self.q_bh < 1):
            raise ValueError("q_bh muss zwischen 0 und 1 liegen.")
        if self.min_zellen < 1 or self.min_dauer_monate < 1:
            raise ValueError("min_zellen und min_dauer_monate müssen mindestens 1 sein.")
        if self.diagnose_median_z <= 0 or not (0 < self.diagnose_anteil_markiert <= 1):
            raise ValueError("Diagnose-Schwellen müssen positiv sein (Anteil höchstens 1).")


class EndtestGesperrt(RuntimeError):
    """Der Endtest-Zeitraum (ab `ENDTEST_AB`) wurde ohne ausdrückliche Freigabe verlangt."""


class EndtestFreigabeHinweis(UserWarning):
    """Der Endtest-Zeitraum wurde ausdrücklich freigegeben (bei künstlichen Daten unbedenklich)."""


def _pruefe_endtest(monate, freigabe: bool) -> None:
    gesperrt = sorted(m for m in monate if m >= ENDTEST_AB)
    if gesperrt and freigabe:
        warnings.warn(
            f"Endtest-Zeitraum freigegeben ({len(gesperrt)} Monate ab {gesperrt[0][0]:04d}-{gesperrt[0][1]:02d}). "
            "ARCHITECTURE.md 9a: nur einmal pro Hauptversion ansehen; diese Freigabe im LOG vermerken.",
            EndtestFreigabeHinweis,
            stacklevel=3,
        )
    if gesperrt and not freigabe:
        raise EndtestGesperrt(
            f"{len(gesperrt)} verlangte Monate ({gesperrt[0][0]:04d}-{gesperrt[0][1]:02d} bis "
            f"{gesperrt[-1][0]:04d}-{gesperrt[-1][1]:02d}) liegen im Endtest-Zeitraum ab "
            f"{ENDTEST_AB[0]:04d}-{ENDTEST_AB[1]:02d}. Der Endtest darf nur einmal pro Hauptversion "
            "angesehen werden (ARCHITECTURE.md 9a). Bereich mit `bis=` begrenzen oder mit "
            "`endtest_freigabe=True` ausdrücklich freigeben (bei künstlichen Daten unbedenklich)."
        )


SPALTEN_EREIGNISSE = [
    "id", "nr", "feld", "monat", "richtung", "band", "n_zellen", "flaeche_km2", "breite_mitte",
    "laenge_mitte", "breite_min", "breite_max", "laenge_min", "laenge_max", "z_median", "z_maximal",
    "aenderung_relativ_median", "datenlage", "aufgefuellt_anteil_mittel", "n_basis_min",
    "basis_von", "basis_bis", "n_fehlende_basismonate", "monat_verdaechtig", "anteil_z_uneinig",
    "anteil_schnee_verdacht", "unsicherheit", "methode", "evidenzstufe", "erkennung_version",
]


@dataclass
class Erkennung:
    """Ergebnis für einen Monat.

    `status`: „bewertet", „nicht bewertbar" (z. B. zu wenig fertige frühere Jahre) oder
    „nicht geladen" (Monat im Würfel nicht fertig; nur in `erkenne_zeitraum`). Ein nicht
    bewerteter Monat ist NICHT „keine Anomalie": `grund` sagt, warum.
    `diagnose`: Median aller z-Werte und Anteil markierter Zellen; `warnung` nennt einen
    Verdacht auf globale Verschiebung des ganzen Monats (leer, wenn unauffällig).
    """

    monat: tuple[int, int]
    feld: str
    status: str
    grund: str
    zellen: xr.Dataset
    ereignisse: pd.DataFrame
    basis_monate: list[tuple[int, int]]
    fehlende_basis_monate: list[tuple[int, int]]
    n_getestet: int = 0
    n_bh_nominal: int = 0
    n_zellen_gemeldet: int = 0
    diagnose: dict = field(default_factory=dict)
    warnung: str = ""
    mindest_streuung: dict = field(default_factory=dict)
    schwellen: Schwellen = field(default_factory=Schwellen)
    version: str = ERKENNUNG_VERSION

    def __post_init__(self):
        # Die Zellkarte allein kann „nicht geladen" nicht von „Datenlage unzureichend" unterscheiden; das Attribut schon.
        self.zellen.attrs["status"] = self.status
        self.zellen.attrs["grund"] = self.grund


@dataclass
class _Zellbewertung:
    """Zwischenergebnis je Monat, vor Mindestdauer und Mindestgröße."""

    z: np.ndarray
    p: np.ndarray
    datenlage: np.ndarray
    n_basis: np.ndarray
    beobachtet_anteil: np.ndarray
    aufgefuellt_anteil: np.ndarray
    aenderung_relativ: np.ndarray
    z_klassisch: np.ndarray
    z_uneinig: np.ndarray
    schnee: np.ndarray
    bh_nominal: np.ndarray  # BH auf nominellen p-Werten
    hell: np.ndarray  # bewertbar und Basislinien-Median >= pool_helligkeit (für die Monatsdiagnose)
    markiert: np.ndarray  # BH und |z| >= z_min_zelle
    vorzeichen: np.ndarray  # -1 / 0 / +1 der markierten Zellen
    n_getestet: int
    mindest_streuung: dict


def _variablen(feld: str) -> list[str]:
    return [f"{feld}_mittel", f"{feld}_mittel_beobachtet", f"{feld}_gueltige_pixel", f"{feld}_beobachtete_pixel", f"{feld}_aufgefuellt_pixel"]


def _nanmedian0(stapel: np.ndarray) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return np.nanmedian(stapel, axis=0)


def _beobachtet_anteil(gueltig: np.ndarray, aufgefuellt: np.ndarray, pixel: int) -> np.ndarray:
    """Anteil beobachteter Pixel: aufgefüllte zählen nie mit; unstimmige Zähler ergeben 0."""
    gueltig = gueltig.astype("float64")
    aufgefuellt = aufgefuellt.astype("float64")
    beobachtet = gueltig - aufgefuellt
    beobachtet = np.where((aufgefuellt < 0) | (aufgefuellt > gueltig) | (gueltig > pixel), 0.0, beobachtet)
    return np.clip(beobachtet, 0.0, None) / pixel


def _gemeinsame_streuung(n_basis, med, s_mad, s: Schwellen) -> tuple[np.ndarray, dict]:
    """Relative Mindest-Streuung je Zelle (aus der Basislinie aller Zellen, je Zahl der Basisjahre)."""
    rho = np.full(n_basis.shape, np.nan)
    info: dict = {}
    hell = (n_basis >= s.min_basisjahre) & np.isfinite(med) & (med >= s.pool_helligkeit)
    relativ = s_mad / np.maximum(np.abs(med), s.pool_helligkeit)
    global_werte = relativ[hell]
    global_rho = (
        float(np.percentile(global_werte, s.pool_perzentil)) if global_werte.size >= s.min_zellen_fuer_pool else np.nan
    )
    info["gesamt"] = {"zellen": int(global_werte.size), "rho": global_rho}
    for n in np.unique(n_basis[n_basis >= s.min_basisjahre]):
        gruppe = hell & (n_basis == n)
        if int(gruppe.sum()) >= s.min_zellen_fuer_pool:
            wert = float(np.percentile(relativ[gruppe], s.pool_perzentil))
        else:
            wert = global_rho
        rho[n_basis == n] = wert
        info[int(n)] = {"zellen": int(gruppe.sum()), "rho": wert}
    return rho, info


def _bewerte_monat(ziel: dict, basis: dict, s: Schwellen, schnee: np.ndarray | None = None,
                   schnee_basis: np.ndarray | None = None) -> _Zellbewertung:
    """Kern: Datenlage, robuste Abweichung, p-Werte, Benjamini-Hochberg, Mindestwert.

    `ziel`: Arrays (y, x) `mittel`, `gueltig`, `aufgefuellt` des untersuchten Monats.
    `basis`: Arrays (n, y, x) derselben Größen der Basismonate (nur frühere Jahre, nur fertige).
    `schnee`: optionale Bool-Karte Schnee-Verdacht im untersuchten Monat (diese Zellen werden nicht bewertet).
    `schnee_basis`: optional (n, y, x) Schnee-Verdacht der Basismonate (diese Werte fallen aus der Basislinie).
    """
    pixel = s.pixel_pro_zelle
    # Anomalieerkennung nutzt ausschließlich das Mittel über beobachtete Pixel
    # (ohne aufgefüllte). Das allgültige Mittel (`mittel`) bleibt im Würfel
    # zur Referenz; es wird hier nicht verwendet, damit aufgefüllte Daten aus
    # der Basislinie nicht in die Abweichung eingehen können.
    x = ziel["obs"].astype("float64")
    beob_ziel = _beobachtet_anteil(ziel["gueltig"], ziel["aufgefuellt"], pixel)
    ok_ziel = (beob_ziel >= s.min_beobachtet_anteil) & np.isfinite(x)
    schnee = np.zeros(x.shape, dtype=bool) if schnee is None else (np.asarray(schnee, bool) & ok_ziel)
    ok_ziel &= ~schnee

    if basis["mittel"].shape[0] > 0:
        beob_basis = _beobachtet_anteil(basis["gueltig"], basis["aufgefuellt"], pixel)
        ok_basis = beob_basis >= s.min_beobachtet_anteil
        if schnee_basis is not None:
            ok_basis &= ~np.asarray(schnee_basis, bool)
        werte = np.where(ok_basis & np.isfinite(basis["obs"]), basis["obs"].astype("float64"), np.nan)
    else:
        werte = np.full((0,) + x.shape, np.nan)
    n_basis = np.isfinite(werte).sum(axis=0).astype("int16")

    med = _nanmedian0(werte) if werte.shape[0] else np.full(x.shape, np.nan)
    mad = _nanmedian0(np.abs(werte - med[None])) if werte.shape[0] else np.full(x.shape, np.nan)
    s_mad = s.mad_faktor * mad

    rho, info = _gemeinsame_streuung(n_basis, med, s_mad, s)
    streuung = np.maximum.reduce(
        [
            np.nan_to_num(s_mad, nan=0.0),
            rho * np.maximum(np.abs(np.nan_to_num(med, nan=0.0)), s.pool_helligkeit),
            np.full(x.shape, s.abs_min_streuung),
        ]
    )
    bewertbar = ok_ziel & (n_basis >= s.min_basisjahre) & np.isfinite(rho) & np.isfinite(med)

    z = np.full(x.shape, np.nan)
    faktor = np.sqrt(1.0 + (np.pi / 2.0) / np.maximum(n_basis, 1))
    z[bewertbar] = ((x - med) / (streuung * faktor))[bewertbar]
    p = normal_zweiseitig(z)
    bh = benjamini_hochberg(p, s.q_bh)
    markiert = bh & (np.abs(z) >= s.z_min_zelle)
    vorzeichen = np.where(markiert, np.sign(z), 0).astype("int8")

    # Klassischer z-Wert parallel (Mittel und Standardabweichung der Basislinie, gleiche Mindest-Streuung;
    # Faktor sqrt(1 + 1/n): der Mittelwert ist selbst aus n Werten geschätzt).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        mittel_b = np.nanmean(werte, axis=0) if werte.shape[0] else np.full(x.shape, np.nan)
        sd_b = np.nanstd(werte, axis=0, ddof=1) if werte.shape[0] > 1 else np.full(x.shape, np.nan)
    streuung_k = np.maximum.reduce(
        [
            np.nan_to_num(sd_b, nan=0.0),
            rho * np.maximum(np.abs(np.nan_to_num(mittel_b, nan=0.0)), s.pool_helligkeit),
            np.full(x.shape, s.abs_min_streuung),
        ]
    )
    z_k = np.full(x.shape, np.nan)
    faktor_k = np.sqrt(1.0 + 1.0 / np.maximum(n_basis, 1))
    z_k[bewertbar] = ((x - mittel_b) / (streuung_k * faktor_k))[bewertbar]
    z_uneinig = bewertbar & ((np.abs(z) >= s.z_min_zelle) != (np.abs(z_k) >= s.z_min_zelle))

    datenlage = np.zeros(x.shape, dtype="int8")
    datenlage[bewertbar] = 1
    datenlage[bewertbar & (beob_ziel >= s.datenlage_mittel_anteil) & (n_basis >= s.datenlage_mittel_basisjahre)] = 2
    datenlage[bewertbar & (beob_ziel >= s.datenlage_gut_anteil) & (n_basis >= s.datenlage_gut_basisjahre)] = 3

    gueltig = ziel["gueltig"].astype("float64")
    aufgefuellt_anteil = np.where(gueltig > 0, ziel["aufgefuellt"].astype("float64") / np.maximum(gueltig, 1), np.nan)
    relativ = np.where(np.isfinite(med) & (med >= s.pool_helligkeit), (x - med) / np.where(med == 0, np.nan, med), np.nan)

    return _Zellbewertung(
        z=z, p=p, datenlage=datenlage, n_basis=n_basis, beobachtet_anteil=beob_ziel,
        aufgefuellt_anteil=aufgefuellt_anteil, aenderung_relativ=relativ, z_klassisch=z_k, z_uneinig=z_uneinig,
        schnee=schnee, bh_nominal=bh,
        hell=bewertbar & np.isfinite(med) & (med >= s.pool_helligkeit),
        markiert=markiert, vorzeichen=vorzeichen, n_getestet=int(bewertbar.sum()), mindest_streuung=info,
    )


# --- Zusammenhängende Zellen ----------------------------------------------------


def zusammenhaengende_gruppen(maske: np.ndarray) -> tuple[np.ndarray, int]:
    """Beschriftet zusammenhängende True-Zellen (8er-Nachbarschaft, Längengrad-Umbruch geschlossen).

    Rückgabe: (Beschriftung mit 0 = keine Zelle, Zahl der Gruppen). Achse 0 = Breite (kein
    Umbruch), Achse 1 = Länge (Umbruch: die letzte Spalte grenzt an die erste).
    """
    maske = np.asarray(maske, dtype=bool)
    ys, xs = np.nonzero(maske)
    n = ys.size
    beschriftung = np.zeros(maske.shape, dtype="int32")
    if n == 0:
        return beschriftung, 0
    index = np.full(maske.shape, -1, dtype="int64")
    index[ys, xs] = np.arange(n)
    eltern = np.arange(n)

    def finde(a: int) -> int:
        while eltern[a] != a:
            eltern[a] = eltern[eltern[a]]
            a = eltern[a]
        return a

    breite, laenge = maske.shape
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        ny = ys + dy
        nx = (xs + dx) % laenge
        innen = ny < breite
        nachbar = np.full(n, -1, dtype="int64")
        nachbar[innen] = index[ny[innen], nx[innen]]
        for a, b in zip(np.flatnonzero(nachbar >= 0), nachbar[nachbar >= 0]):
            ra, rb = finde(int(a)), finde(int(b))
            if ra != rb:
                eltern[max(ra, rb)] = min(ra, rb)
    wurzeln = np.array([finde(i) for i in range(n)])
    _, gruppen = np.unique(wurzeln, return_inverse=True)
    beschriftung[ys, xs] = gruppen + 1
    return beschriftung, int(gruppen.max()) + 1


def zellflaeche_km2(breite_mitte: np.ndarray, zellgroesse_grad: float = 0.25) -> np.ndarray:
    """Fläche von Gitterzellen (Kugelnäherung) in km² je Zellmittelpunkt-Breite (seit 2026-09-26 gemeinsame
    Umsetzung in aleph/detect/statistik.py; hier nur weitergereicht)."""
    return _zellflaeche_km2(breite_mitte, zellgroesse_grad)


def _unsicherheit_text(bew: "_Zellbewertung", maske: np.ndarray) -> str:
    teile = ["p-Werte nominell"]
    uneinig = float(bew.z_uneinig[maske].mean())
    if uneinig > 0:
        teile.append(f"klassischer und robuster z-Wert uneinig in {uneinig:.0%} der Zellen")
    schnee = float(bew.schnee[maske].mean())
    if schnee > 0:
        teile.append(f"Schnee-Verdacht in {schnee:.0%} der Zellen")
    return "; ".join(teile)


def _band(z_betrag: float, s: Schwellen) -> int:
    if z_betrag >= s.z_extrem:
        return 3
    if z_betrag >= s.z_stark:
        return 2
    return 1


def _monat_text(m: tuple[int, int]) -> str:
    return f"{m[0]:04d}-{m[1]:02d}"


def _meldungen(
    bew: _Zellbewertung, wirksam: np.ndarray, monat: tuple[int, int], feld: str,
    breite: np.ndarray, laenge: np.ndarray, s: Schwellen,
    basis_monate: list[tuple[int, int]] | None = None, fehlend: list[tuple[int, int]] | None = None,
    monat_verdaechtig: bool | None = None,
) -> tuple[xr.Dataset, pd.DataFrame, int]:
    """Bildet aus den markierten Zellen Ereignisse (Richtung getrennt, Mindestgröße)."""
    basis_monate = basis_monate or []
    fehlend = fehlend or []
    # Zellgröße aus den Würfelkoordinaten (Breitenabstand), nicht als feste Annahme; Rückfall auf die Einstellung.
    zellgroesse = float(abs(breite[1] - breite[0])) if len(breite) > 1 else s.zellgroesse_grad
    ereignis_nr = np.zeros(wirksam.shape, dtype="int32")
    band = np.zeros(wirksam.shape, dtype="int8")
    richtung = np.zeros(wirksam.shape, dtype="int8")
    zeilen = []
    nr = 0
    for vorz in (1, -1):
        beschr, anzahl = zusammenhaengende_gruppen(wirksam & (bew.vorzeichen == vorz))
        if anzahl == 0:
            continue
        groessen = np.bincount(beschr.ravel(), minlength=anzahl + 1)
        for g in range(1, anzahl + 1):
            if groessen[g] < s.min_zellen:
                continue
            nr += 1
            maske = beschr == g
            ereignis_nr[maske] = nr
            richtung[maske] = vorz
            z_zellen = np.abs(bew.z[maske])
            b = _band(float(np.median(z_zellen)), s)
            band[maske] = np.where(z_zellen >= s.z_extrem, 3, np.where(z_zellen >= s.z_stark, 2, 1))
            ys, xs = np.nonzero(maske)
            lat = breite[ys]
            lon = laenge[xs]
            lon_mitte = float(np.degrees(np.arctan2(np.sin(np.radians(lon)).mean(), np.cos(np.radians(lon)).mean())))
            relativ = ((lon - lon_mitte + 180.0) % 360.0) - 180.0
            zeilen.append(
                {
                    "id": f"{feld}-{monat[0]:04d}-{monat[1]:02d}-{nr:03d}",
                    "nr": nr,
                    "feld": feld,
                    "monat": pd.Timestamp(date(monat[0], monat[1], 1)),
                    "richtung": RICHTUNG_NAMEN[vorz],
                    "band": BAND_NAMEN[b],
                    "n_zellen": int(maske.sum()),
                    "flaeche_km2": float(zellflaeche_km2(lat, zellgroesse).sum()),
                    "breite_mitte": float(lat.mean()),
                    "laenge_mitte": lon_mitte,
                    "breite_min": float(lat.min()),
                    "breite_max": float(lat.max()),
                    "laenge_min": float(((lon_mitte + relativ.min() + 180.0) % 360.0) - 180.0),
                    "laenge_max": float(((lon_mitte + relativ.max() + 180.0) % 360.0) - 180.0),
                    "z_median": float(np.median(bew.z[maske])),
                    "z_maximal": float(bew.z[maske][np.argmax(z_zellen)]),
                    "aenderung_relativ_median": (
                        float(np.nanmedian(bew.aenderung_relativ[maske]))
                        if np.isfinite(bew.aenderung_relativ[maske]).any() else float("nan")
                    ),
                    "datenlage": DATENLAGE_NAMEN[int(bew.datenlage[maske].min())],
                    "aufgefuellt_anteil_mittel": float(np.nanmean(bew.aufgefuellt_anteil[maske])),
                    "n_basis_min": int(bew.n_basis[maske].min()),
                    "basis_von": _monat_text(min(basis_monate)) if basis_monate else "",
                    "basis_bis": _monat_text(max(basis_monate)) if basis_monate else "",
                    "n_fehlende_basismonate": len(fehlend),
                    "monat_verdaechtig": monat_verdaechtig,
                    "anteil_z_uneinig": float(bew.z_uneinig[maske].mean()),
                    "anteil_schnee_verdacht": float(bew.schnee[maske].mean()),
                    "unsicherheit": _unsicherheit_text(bew, maske),
                    "methode": METHODE,
                    "evidenzstufe": "beobachtet",
                    "erkennung_version": ERKENNUNG_VERSION,
                }
            )
    dims = ("breite", "laenge")
    zellen = xr.Dataset(
        {
            "z": (dims, bew.z.astype("float32")),
            "p_nominal": (dims, bew.p.astype("float32")),
            "z_klassisch": (dims, bew.z_klassisch.astype("float32")),
            "z_uneinig": (dims, bew.z_uneinig),
            "schnee_verdacht": (dims, bew.schnee),
            "datenlage": (dims, bew.datenlage),
            "n_basis": (dims, bew.n_basis),
            "beobachtet_anteil": (dims, bew.beobachtet_anteil.astype("float32")),
            "aufgefuellt_anteil": (dims, bew.aufgefuellt_anteil.astype("float32")),
            "bh_nominal": (dims, bew.bh_nominal),
            "markiert": (dims, bew.markiert),
            "gemeldet": (dims, ereignis_nr > 0),
            "ereignis_nr": (dims, ereignis_nr),
            "richtung": (dims, richtung),
            "band": (dims, band),
        },
        coords={"breite": breite, "laenge": laenge},
        attrs={"datenlage_codes": "0 unzureichend, 1 dünn, 2 mittel, 3 gut", "band_codes": "0 keines, 1 auffällig, 2 stark, 3 extrem",
               "evidenzstufe": "beobachtet", "methode": METHODE, "version": ERKENNUNG_VERSION,
               "unsicherheit": "p-Werte nominell (keine garantierte Falschmeldungsrate); z_uneinig und Datenlage je Zelle"},
    )
    tabelle = pd.DataFrame(zeilen, columns=SPALTEN_EREIGNISSE)
    return zellen, tabelle, int((ereignis_nr > 0).sum())


# --- Öffentliche Funktionen ------------------------------------------------------


def _basis_monate(fertig: list[tuple[int, int]], achse: list[tuple[int, int]], monat: tuple[int, int]):
    """Fertige frühere Jahre desselben Kalendermonats und solche, die auf der Achse stehen, aber nicht fertig sind."""
    jahr, mo = monat
    fertig_menge = set(fertig)
    basis = sorted(m for m in fertig if m[1] == mo and m[0] < jahr)
    fehlend = sorted(m for m in achse if m[1] == mo and m[0] < jahr and m not in fertig_menge)
    return basis, fehlend


def _leere_zellen(breite, laenge) -> xr.Dataset:
    form = (len(breite), len(laenge))
    leer = _Zellbewertung(
        z=np.full(form, np.nan), p=np.full(form, np.nan), datenlage=np.zeros(form, "int8"),
        n_basis=np.zeros(form, "int16"), beobachtet_anteil=np.full(form, np.nan),
        aufgefuellt_anteil=np.full(form, np.nan), aenderung_relativ=np.full(form, np.nan),
        z_klassisch=np.full(form, np.nan), z_uneinig=np.zeros(form, bool), schnee=np.zeros(form, bool),
        bh_nominal=np.zeros(form, bool), hell=np.zeros(form, bool), markiert=np.zeros(form, bool), vorzeichen=np.zeros(form, "int8"),
        n_getestet=0, mindest_streuung={},
    )
    zellen, _, _ = _meldungen(leer, np.zeros(form, bool), (2000, 1), "leer", np.asarray(breite), np.asarray(laenge), Schwellen())
    return zellen


def _lade(wuerfel, monat, feld, s: Schwellen):
    """Liest Ziel- und Basismonate. Rückgabe: (ziel, basis, breite, laenge, basis_monate, fehlend)."""
    fertig = lesen.fertige_monate(wuerfel)
    achse = lesen.zeitachse_monate(wuerfel)
    basis_monate, fehlend = _basis_monate(fertig, achse, monat)
    ds = lesen.lies_monate(wuerfel, [monat] + basis_monate, _variablen(feld))  # Fehler, wenn `monat` nicht fertig ist
    v_mittel, v_obs, v_gueltig, v_beob, v_aufg = _variablen(feld)
    ziel = {
        "mittel": ds[v_mittel].isel(zeit=0).values,
        "obs": ds[v_obs].isel(zeit=0).values,
        "gueltig": ds[v_gueltig].isel(zeit=0).values,
        "beobachtet": ds[v_beob].isel(zeit=0).values,
        "aufgefuellt": ds[v_aufg].isel(zeit=0).values,
    }
    if basis_monate:
        basis = {
            "mittel": ds[v_mittel].isel(zeit=slice(1, None)).values,
            "obs": ds[v_obs].isel(zeit=slice(1, None)).values,
            "gueltig": ds[v_gueltig].isel(zeit=slice(1, None)).values,
            "beobachtet": ds[v_beob].isel(zeit=slice(1, None)).values,
            "aufgefuellt": ds[v_aufg].isel(zeit=slice(1, None)).values,
        }
    else:
        leer = np.zeros((0,) + ziel["mittel"].shape)
        basis = {"mittel": leer, "obs": leer, "gueltig": leer, "beobachtet": leer, "aufgefuellt": leer}
    return ziel, basis, ds["breite"].values, ds["laenge"].values, basis_monate, fehlend


def _nicht_geladen(monat, feld, s, breite, laenge, zustand: int = 0) -> Erkennung:
    """`zustand`: Rohwert von `monat_fertig` (siehe aleph.detect.wuerfel.ZUSTANDSNAMEN), nur für
    den Grund-Text; am Verhalten ändert sich nichts (weiterhin ausschließlich Zustand 1 bewertet).
    """
    return Erkennung(
        monat=monat, feld=feld, status="nicht geladen",
        grund=(
            f"{_monat_text(monat)} ist im Würfel nicht als fertig markiert "
            f"(Zustand: {lesen.zustandstext(zustand)}). "
            "Das ist NICHT „keine Daten“ und NICHT „keine Anomalie“; der Monat wurde nicht bewertet."
        ),
        zellen=_leere_zellen(breite, laenge), ereignisse=pd.DataFrame(columns=SPALTEN_EREIGNISSE),
        basis_monate=[], fehlende_basis_monate=[], schwellen=s, diagnose=_diagnose_leer(),
    )


def _nicht_bewertbar(monat, feld, s, breite, laenge, basis_monate, fehlend) -> Erkennung:
    grund = (
        f"nur {len(basis_monate)} fertige frühere Jahre für denselben Kalendermonat, nötig sind mindestens "
        f"{s.min_basisjahre}"
        + (f"; auf der Zeitachse stehen aber nicht geladene Monate: {', '.join(f'{j:04d}-{m:02d}' for j, m in fehlend)}" if fehlend else "")
        + ". Das ist NICHT „keine Anomalie“, der Monat wurde nicht bewertet."
    )
    return Erkennung(
        monat=monat, feld=feld, status="nicht bewertbar", grund=grund, zellen=_leere_zellen(breite, laenge),
        ereignisse=pd.DataFrame(columns=SPALTEN_EREIGNISSE), basis_monate=basis_monate,
        fehlende_basis_monate=fehlend, schwellen=s, diagnose=_diagnose_leer(),
    )


def erkenne_monat(
    wuerfel, monat: tuple[int, int], feld: str, schwellen: Schwellen | None = None, endtest_freigabe: bool = False
) -> Erkennung:
    """Erkennt Anomalien eines Monats (Mindestdauer nicht angewendet, siehe `erkenne_zeitraum`).

    `monat`: (Jahr, Monat), muss im Würfel fertig sein, sonst `MonatNichtFertig`. Monate ab
    `ENDTEST_AB` nur mit `endtest_freigabe=True`, sonst `EndtestGesperrt`.
    `feld`: Präfix der Variablen (z. B. „allangle" oder „near_nadir"); bewusst ohne Standardwert,
    weil die Feldwahl noch offen ist (LOG.md, Etappe 2).
    """
    s = schwellen or Schwellen()
    _pruefe_endtest([monat], endtest_freigabe)
    ziel, basis, breite, laenge, basis_monate, fehlend = _lade(wuerfel, monat, feld, s)
    if len(basis_monate) < s.min_basisjahre:
        return _nicht_bewertbar(monat, feld, s, breite, laenge, basis_monate, fehlend)
    bew = _bewerte_monat(ziel, basis, s, _schnee(ziel, breite, monat, s), _schnee_basis(basis, breite, monat, s))
    return _fertige_erkennung(bew, bew.markiert, monat, feld, breite, laenge, basis_monate, fehlend, s)


def _schnee(ziel: dict, breite: np.ndarray, monat: tuple[int, int], s: Schwellen) -> np.ndarray:
    anteil = _beobachtet_anteil(ziel["gueltig"], ziel["aufgefuellt"], s.pixel_pro_zelle)
    anteil = np.where(np.asarray(ziel["gueltig"], dtype="float64") > 0, anteil, np.nan)
    return schnee_verdacht(breite, monat[1], anteil, s.schnee_regel)


def _schnee_basis(basis: dict, breite: np.ndarray, monat: tuple[int, int], s: Schwellen) -> np.ndarray | None:
    """Schnee-Verdacht der Basismonate (derselbe Kalendermonat wie `monat`)."""
    if basis["gueltig"].shape[0] == 0:
        return None
    return np.stack([_schnee({"gueltig": basis["gueltig"][i], "aufgefuellt": basis["aufgefuellt"][i]}, breite, monat, s)
                     for i in range(basis["gueltig"].shape[0])])


def _diagnose(bew: _Zellbewertung, s: Schwellen) -> dict:
    """Monatsdiagnose über die hellen bewertbaren Zellen; Werte None, wenn nichts bewertbar war."""
    n_hell = int(bew.hell.sum())
    if n_hell == 0:
        return {"median_z": None, "anteil_markiert": None, "n_helle_zellen": 0, "verdaechtig": None}
    median_z = float(np.median(bew.z[bew.hell]))
    anteil = float(bew.markiert[bew.hell].sum() / n_hell)
    verdaechtig = bool(abs(median_z) >= s.diagnose_median_z or anteil >= s.diagnose_anteil_markiert)
    return {"median_z": median_z, "anteil_markiert": anteil, "n_helle_zellen": n_hell, "verdaechtig": verdaechtig}


def _diagnose_leer() -> dict:
    return {"median_z": None, "anteil_markiert": None, "n_helle_zellen": 0, "verdaechtig": None}


def _fertige_erkennung(bew, wirksam, monat, feld, breite, laenge, basis_monate, fehlend, s) -> Erkennung:
    diagnose = _diagnose(bew, s)
    zellen, tabelle, n_gemeldet = _meldungen(
        bew, wirksam, monat, feld, breite, laenge, s, basis_monate, fehlend, monat_verdaechtig=diagnose["verdaechtig"]
    )
    status, grund = "bewertet", ""
    if bew.n_getestet == 0:
        status = "nicht bewertbar"
        grund = (
            "keine einzige Zelle bewertbar (Datenlage unzureichend oder Streuung nicht schätzbar, weniger als "
            f"{s.min_zellen_fuer_pool} Zellen mit Basislinie). Das ist NICHT „keine Anomalie“."
        )
    warnung = ""
    if diagnose["verdaechtig"]:
        warnung = (
            f"Ungewöhnlich breite Verschiebung in diesem Monat (Median der z-Werte der hellen Zellen "
            f"{diagnose['median_z']:+.2f}, {diagnose['anteil_markiert']:.1%} davon markiert). Mögliche Ursachen: "
            "Sensor oder Aufbereitungsversion, ein Ausnahmejahr in der Basislinie, ein langsamer Trend oder eine "
            "großräumige Störung; die Ursache ist nicht geklärt. Die Ereignisse dieses Monats sind mit Vorsicht zu lesen."
        )
    return Erkennung(
        monat=monat, feld=feld, status=status, grund=grund, zellen=zellen, ereignisse=tabelle,
        basis_monate=basis_monate, fehlende_basis_monate=fehlend, n_getestet=bew.n_getestet,
        n_bh_nominal=int(bew.bh_nominal.sum()), n_zellen_gemeldet=n_gemeldet,
        diagnose=diagnose, warnung=warnung, mindest_streuung=bew.mindest_streuung, schwellen=s,
    )


def erkenne_zeitraum(
    wuerfel, feld: str, von: tuple[int, int] | None = None, bis: tuple[int, int] | None = None,
    schwellen: Schwellen | None = None, endtest_freigabe: bool = False,
) -> list[Erkennung]:
    """Erkennt Anomalien für alle Monate der Zeitachse im Bereich, zeitlich aufsteigend.

    Jeder Monat der Zeitachse im Bereich bekommt einen Eintrag: „bewertet", „nicht bewertbar"
    oder „nicht geladen". Ein nicht geladener Monat verschwindet also nie stillschweigend aus
    der Liste. Monate ab `ENDTEST_AB` nur mit `endtest_freigabe=True` (`EndtestGesperrt`); ohne
    `bis` reicht der Bereich bis zum Ende der Zeitachse und wird deshalb abgelehnt.

    Mit `min_dauer_monate` > 1 zählt eine Zelle nur, wenn sie in dieser und den vorigen
    `min_dauer_monate - 1` Kalendermonaten unmittelbar hintereinander in GLEICHER Richtung
    markiert war (das Ereignis erscheint also erst im letzten Monat der Kette). Ein nicht
    geladener oder nicht bewertbarer Monat sowie eine Zelle, die in einem Zwischenmonat nicht
    bewertbar war, unterbricht die Kette (nie als „nicht auffällig", aber auch nie als auffällig).
    """
    s = schwellen or Schwellen()
    fertig = set(lesen.fertige_monate(wuerfel))
    zustaende = lesen.monat_zustaende(wuerfel)
    monate = [m for m in lesen.zeitachse_monate(wuerfel) if (von is None or m >= von) and (bis is None or m <= bis)]
    _pruefe_endtest(monate, endtest_freigabe)
    breite_achse, laenge_achse = lesen.gitter(wuerfel)
    ergebnisse: list[Erkennung] = []
    vorher_monat: tuple[int, int] | None = None
    vorher_vorzeichen = None
    lauf = None
    for monat in monate:
        if monat not in fertig:
            ergebnisse.append(
                _nicht_geladen(monat, feld, s, breite_achse, laenge_achse, zustaende.get(monat, 0))
            )
            vorher_monat, vorher_vorzeichen, lauf = None, None, None
            continue
        ziel, basis, breite, laenge, basis_monate, fehlend = _lade(wuerfel, monat, feld, s)
        if len(basis_monate) < s.min_basisjahre:
            ergebnisse.append(_nicht_bewertbar(monat, feld, s, breite, laenge, basis_monate, fehlend))
            vorher_monat, vorher_vorzeichen, lauf = None, None, None
            continue
        bew = _bewerte_monat(ziel, basis, s, _schnee(ziel, breite, monat, s), _schnee_basis(basis, breite, monat, s))
        angrenzend = vorher_monat is not None and (monat[0] * 12 + monat[1] - 1) == (vorher_monat[0] * 12 + vorher_monat[1])
        if angrenzend and lauf is not None:
            gleich = (bew.vorzeichen != 0) & (bew.vorzeichen == vorher_vorzeichen)
            lauf = np.where(gleich, lauf + 1, np.where(bew.vorzeichen != 0, 1, 0))
        else:
            lauf = np.where(bew.vorzeichen != 0, 1, 0)
        wirksam = bew.markiert & (lauf >= s.min_dauer_monate)
        ergebnisse.append(_fertige_erkennung(bew, wirksam, monat, feld, breite, laenge, basis_monate, fehlend, s))
        vorher_monat, vorher_vorzeichen = monat, bew.vorzeichen
    return ergebnisse
