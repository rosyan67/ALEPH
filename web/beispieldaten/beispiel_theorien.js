/*
 * BEISPIELDATEN – Kurzfassung des Theorie-Registers (ARCHITECTURE.md Abschnitt 8).
 * Die vollständigen Einträge liegen später als YAML unter theories/. Diese Datei
 * dient nur dazu, die Suche und die Untersuchungsansicht im Oberflächen-Gerüst
 * zu testen, solange theories/ noch nicht existiert.
 *
 * Zwei Theorien haben hier den Status "bestätigt", damit sich Verknüpfungen
 * mit Evidenzstufe "statistische Assoziation" in der Untersuchungsansicht
 * überhaupt zeigen und testen lassen. Das ist erfunden: Es gab noch keinen
 * echten Permutationstest gegen Testdaten (Abschnitt 8, Schritt 3). Im echten
 * Theorie-Register steht hier "ungeprüft", bis Woche 5/6 das tatsächlich prüft.
 */
window.ALEPH_BEISPIEL_THEORIEN = [
  {
    "id": "duerre-migration",
    "titel": "Dürre verstärkt Abwanderung aus ländlichen Regionen",
    "disziplin": "Umweltökonomie / Migrationsforschung",
    "status": "bestätigt",
    "status_hinweis": "Status hier nur beispielhaft gesetzt (Beispieldaten) – ein echter Permutationstest wurde noch nicht durchgeführt.",
    "beschreibung": "Ernteausfälle senken Einkommen, betroffene Haushalte wandern in Städte ab. Prüfbar mit Niederschlag, Vegetation, Nachtlicht, IDMC."
  },
  {
    "id": "klima-konflikt",
    "titel": "Niederschlags- und Hitzeschocks erhöhen das Konfliktrisiko",
    "disziplin": "Konfliktforschung / Klimatologie",
    "status": "ungeprüft",
    "beschreibung": "Klimaschocks verschärfen Ressourcenknappheit und erhöhen die Konfliktwahrscheinlichkeit. Prüfbar mit Niederschlag, Temperatur, ACLED."
  },
  {
    "id": "ressourcenfluch",
    "titel": "Rohstoffreichtum erhöht das Konfliktrisiko (Ressourcenfluch)",
    "disziplin": "Politische Ökonomie",
    "status": "ungeprüft",
    "beschreibung": "Rohstoffreichtum begünstigt Konflikte um Kontrolle der Fördereinnahmen. Prüfbar mit Weltbank-Rohstoffdaten, ACLED, Nachtlicht an Förderstätten."
  },
  {
    "id": "nahrungspreise-unruhen",
    "titel": "Steigende Nahrungsmittelpreise gehen Protesten voraus",
    "disziplin": "Politikwissenschaft / Ökonomie",
    "status": "ungeprüft",
    "beschreibung": "Preisschocks bei Grundnahrungsmitteln erhöhen die Protestwahrscheinlichkeit. Prüfbar mit FAO-Preisdaten, ACLED."
  },
  {
    "id": "konflikt-vertreibung",
    "titel": "Gewalt führt zu Abwanderung, sichtbar an Nachtlicht und Vertreibungszahlen",
    "disziplin": "Konfliktforschung / Migrationsforschung",
    "status": "bestätigt",
    "status_hinweis": "Status hier nur beispielhaft gesetzt (Beispieldaten) – ein echter Permutationstest wurde noch nicht durchgeführt.",
    "beschreibung": "Bewaffnete Gewalt führt zu Bevölkerungsbewegung, messbar über Nachtlicht-Rückgang am Herkunftsort. Prüfbar mit ACLED, Nachtlicht, IDMC/UNHCR."
  }
];
