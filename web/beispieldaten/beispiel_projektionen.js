/*
 * BEISPIELDATEN – keine echten Modelle.
 *
 * "Projektionen" sind keine Anomalien. Eine Anomalie ist laut Abschnitt 7
 * immer eine direkte Messung ("beobachtet"). Eine Projektion ist etwas
 * anderes: eine Aussage über die Zukunft, mit Evidenzstufe Modellprojektion
 * ("aus bestätigten Zusammenhängen abgeleitete Entwicklung", Abschnitt 8)
 * oder hypothetisches Szenario ("Was-wäre-wenn, ausdrücklich keine
 * Vorhersage"). Sie erscheinen deshalb nicht im Anomalie-Layer auf dem
 * Globus, sondern nur als Markierungen im schraffierten Bereich rechts von
 * "heute" auf der Zeitachse, mit eigener kleiner Ansicht beim Anklicken.
 *
 * Felder: id, titel, evidenzstufe, von/bis (JJJJ-MM, müssen in der Zukunft
 * liegen), ort_label, theorie (optional, Verweis auf beispiel_theorien.js),
 * beschreibung. Genau 2 Beispiele – mehr braucht das Gerüst nicht.
 */
window.ALEPH_BEISPIEL_PROJEKTIONEN = [
  {
    "id": "proj-001",
    "beispiel": true,
    "titel": "Modellprojektion: anhaltender Nachtlicht-Rückgang, Region Donetsk",
    "evidenzstufe": "Modellprojektion",
    "von": "2026-10",
    "bis": "2027-03",
    "ort_label": "Ostukraine, Region Donetsk (Beispiel-Projektion)",
    "theorie": "konflikt-vertreibung",
    "beschreibung": "Setzt voraus, dass sich das Muster aus der bestätigten Verknüpfung mit Konflikt-Vertreibung (siehe Anomalie bm-003) fortsetzt, solange die Gewalt anhält. Modellprojektion mit dokumentierten Annahmen – keine Vorhersage einzelner Ereignisse."
  },
  {
    "id": "proj-002",
    "beispiel": true,
    "titel": "Hypothetisches Szenario: verstärkte Abwanderung am Sahelrand",
    "evidenzstufe": "hypothetisches Szenario",
    "von": "2026-11",
    "bis": "2027-10",
    "ort_label": "Sahelrand, Niger (Beispiel, hypothetisches Szenario)",
    "theorie": "duerre-migration",
    "beschreibung": "Was-wäre-wenn: Sollte eine mehrjährige Dürre eintreten, wie stark könnte das Nachtlicht am Herkunftsort zurückgehen? Reine Annahme über die Zukunft, ausdrücklich keine Vorhersage."
  }
];
