/*
 * BEISPIELDATEN – plausible, aber erfundene Zeiträume.
 *
 * Zeigt über der Zeitachse für jede Datenquelle einen dünnen Streifen: von
 * wann bis wann Daten vorliegen sollen, Farbe = Datenlage (gut/mittel/dünn).
 * Die echten Zeiträume kommen später aus layers.yaml (ARCHITECTURE.md
 * Abschnitt 5), sobald die Layer eingetragen sind – bisher existiert
 * layers.yaml noch nicht. Bis dahin: plausible Werte aus den Angaben in
 * Abschnitt 5 (z. B. VNP46A3 seit 2013, siehe docs/sources/vnp46a3.md).
 */
window.ALEPH_BEISPIEL_DATENVERFUEGBARKEIT = [
  { "layer": "Nachtlicht (VIIRS VNP46A3)", "kurz": "Licht", "von": "2013-01", "bis": "2025-12", "datenlage": "gut" },
  { "layer": "Vegetation (MODIS NDVI)", "kurz": "Veget.", "von": "2013-01", "bis": "2025-12", "datenlage": "gut" },
  { "layer": "Brände (FIRMS)", "kurz": "Brände", "von": "2013-01", "bis": "2025-12", "datenlage": "gut" },
  { "layer": "Luftqualität (OMI NO₂)", "kurz": "NO₂", "von": "2013-01", "bis": "2024-12", "datenlage": "mittel" },
  { "layer": "Niederschlag (GPM IMERG)", "kurz": "Regen", "von": "2014-06", "bis": "2025-12", "datenlage": "mittel" },
  { "layer": "Schiffsverkehr (AIS, Global Fishing Watch)", "kurz": "Schiffe", "von": "2017-01", "bis": "2025-12", "datenlage": "dünn" }
];
