/*
 * ALEPH – aufklappbares Feld „Über ALEPH“ (Teil 5, 2026-09-28). Kurz, ohne Werbesprache.
 * Der Datenstand wird aus daten/datenstand.js gelesen, nicht fest eingetragen.
 */
(function () {
  "use strict";
  var G = window.ALEPH_GLOBUS, DS = window.ALEPH_DATENSTAND;
  if (!G || !DS) return;
  var esc = G.esc;

  var knopf = document.createElement("button");
  knopf.className = "corner-btn";
  knopf.id = "ueber-auf";
  knopf.textContent = "Über ALEPH";
  knopf.setAttribute("aria-expanded", "false");
  document.querySelector(".corner-group--right").appendChild(knopf);

  var m = DS.angezeigt || [];
  // Nicht auswählbare Monate (z. B. zurückgestellt) werden genannt, nicht still weggelassen.
  var fehlend = (G.zeitleiste ? G.zeitleiste() : []).filter(function (e) { return !e.auswaehlbar; })
    .map(function (e) { return e.monat + " " + e.zustand_text; });
  var zeitraum = m.length ? m[0] + " bis " + m[m.length - 1] + " (" + m.length + " Monate" +
    (fehlend.length ? "; nicht auswählbar: " + fehlend.join(", ") : "") + ")" : "noch kein Monat";
  var nurRegion = (DS.monate || []).filter(function (x) { return x.zustand === 4; }).length;

  var feld = document.createElement("section");
  feld.id = "ueber";
  feld.className = "ueber";
  feld.hidden = true;
  feld.setAttribute("aria-label", "Über ALEPH");
  feld.innerHTML =
    '<div class="ad-kopf"><h2>Über ALEPH</h2><button class="icon-btn ueber-zu" aria-label="Schließen">✕</button></div>' +
    "<p>ALEPH bringt frei verfügbare Satelliten- und Statistikdaten auf ein gemeinsames Raster und zeigt sie auf einem Globus. " +
    "Ziel ist, auffällige Veränderungen zu finden und mögliche Zusammenhänge an Daten zu prüfen, statt sie zu behaupten.</p>" +
    "<h3>Vier Evidenzstufen</h3><dl class=\"ueber-stufen\">" +
    "<dt>beobachtet</dt><dd>direkt in Daten gemessen, z. B. das Nachtlicht einer Zelle</dd>" +
    "<dt>statistische Assoziation</dt><dd>ein Zusammenhang, an Daten gerechnet, z. B. Nachtlicht und BIP im Querschnitt – keine Ursache</dd>" +
    "<dt>Modellprojektion</dt><dd>Ergebnis eines Modells mit genannten Annahmen (noch keine auf dem Globus)</dd>" +
    "<dt>hypothetisches Szenario</dt><dd>Was-wäre-wenn, ausdrücklich keine Vorhersage (noch keine auf dem Globus)</dd></dl>" +
    "<h3>Datenstand</h3><ul>" +
    "<li>Nachtlicht: NASA VIIRS Black Marble VNP46A3, " + esc(zeitraum) +
    (nurRegion ? "; davon " + nurRegion + " Monate bisher nur für Afrika, Europa und Asien vollständig (Amerika und Ozeanien werden noch geladen)" : "") + ".</li>" +
    "<li>Wirtschaft: Weltbank World Development Indicators (reales BIP, BIP pro Kopf, Bevölkerung).</li>" +
    "<li>Grenzen: Natural Earth 5.1.1 und UN-Länderliste M49; Stand Mai 2022, nicht zeitabhängig.</li>" +
    "<li>Stand dieser Anzeige: " + esc(String(DS.erstellt_utc).replace("T", " ").replace("Z", " UTC")) + ".</li></ul>" +
    "<h3>Als Nächstes</h3><p>Niederschlag (NASA GPM IMERG), Vegetation (MODIS) und Konfliktereignisse (ACLED) als weitere Ebenen; danach die Prüfung einzelner Theorien an Daten.</p>" +
    "<h3>Regeln</h3><ul>" +
    "<li>Umstrittene, besetzte und Sonderstatus-Gebiete sind eigene Einheiten mit Quelle. ALEPH entscheidet keine Souveränitätsfragen.</li>" +
    "<li>2023 bis 2025 ist für die spätere Prüfung gesperrt und wird hier nicht gezeigt.</li>" +
    "<li>Fehlende Daten sind nie „dunkel“: Sie haben eigene gestreifte Muster.</li>" +
    "<li>Jede Aussage nennt ihre Evidenzstufe und ihre Unsicherheit.</li></ul>";
  document.body.appendChild(feld);

  function oeffne(an) { feld.hidden = !an; knopf.setAttribute("aria-expanded", an ? "true" : "false"); }
  knopf.addEventListener("click", function () { oeffne(feld.hidden); });
  feld.addEventListener("click", function (e) { if (e.target.closest(".ueber-zu")) oeffne(false); });
  document.addEventListener("aleph-bereit", function (e) { if ((e.detail || {}).ueber === "1") oeffne(true); });
})();
