/*
 * BEISPIELDATEN – plausible, aber erfundene Zeiträume.
 *
 * Zeigt über der Zeitachse für jede Datenquelle einen dünnen Streifen: von
 * wann bis wann Daten vorliegen sollen, Farbe = Datenlage (gut/mittel/dünn).
 * Die echten Zeiträume kommen später aus layers.yaml (ARCHITECTURE.md
 * Abschnitt 5), sobald die Layer eingetragen sind – bisher existiert
 * layers.yaml noch nicht. Bis dahin: plausible Werte aus den Angaben in
 * Abschnitt 5 (z. B. VNP46A3 seit 2013, siehe docs/sources/vnp46a3.md).
 *
 * `quelle` ist der kurze Schlüssel, der auch in `layer` der Beispiel-
 * Anomalien vorkommt (z. B. "nachtlicht") – damit lässt sich diese Datei
 * mit dem Kombinationsfilter (UND/ODER über Datenquellen) verknüpfen.
 */
window.ALEPH_BEISPIEL_DATENVERFUEGBARKEIT = [
  { "quelle": "nachtlicht", "layer": "Nachtlicht (VIIRS VNP46A3)", "kurz": "Licht", "von": "2013-01", "bis": "2025-12", "datenlage": "gut" },
  { "quelle": "vegetation", "layer": "Vegetation (MODIS NDVI)", "kurz": "Veget.", "von": "2013-01", "bis": "2025-12", "datenlage": "gut" },
  { "quelle": "brände", "layer": "Brände (FIRMS)", "kurz": "Brände", "von": "2013-01", "bis": "2025-12", "datenlage": "gut" },
  { "quelle": "no2", "layer": "Luftqualität (OMI NO₂)", "kurz": "NO₂", "von": "2013-01", "bis": "2024-12", "datenlage": "mittel" },
  { "quelle": "niederschlag", "layer": "Niederschlag (GPM IMERG)", "kurz": "Regen", "von": "2014-06", "bis": "2025-12", "datenlage": "mittel" },
  { "quelle": "schiffsverkehr", "layer": "Schiffsverkehr (AIS, Global Fishing Watch)", "kurz": "Schiffe", "von": "2017-01", "bis": "2025-12", "datenlage": "dünn" }
];
