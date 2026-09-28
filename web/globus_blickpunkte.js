/*
 * ALEPH – Blickpunkte für die Vorführung (Teil 2, 2026-09-28)
 *
 * Sechs voreingestellte Ansichten. Ein Klick fliegt hin, wählt den Monat und öffnet
 * bei Bedarf das Dossier eines Landes. Die Texte beschreiben nur, was man SIEHT
 * (Evidenzstufe „beobachtet“); jede Zahl im Text ist aus den exportierten Monatsdateien
 * (web/daten/nachtlicht_<Monat>.js) abgelesen, Zellwert in nW·cm⁻²·sr⁻¹ – gerundet.
 *
 * Monatswahl: Anteil der Zellen im Ausschnitt mit gültigem Wert (≥ 50 % beobachtet),
 * gerechnet am 2026-09-28 über alle 24 Monate; gewählt wurde ein Monat mit hoher
 * Abdeckung, kein Winter im Norden und kein Monsun in Indien (Juni–August: 74–90 %):
 *   Nil 2018-10: 100 %   Korea 2018-10: 100 %   Nigerdelta 2018-11: 100 %
 *   Irak 2018-10: 100 %  Indien 2018-03: 96 %   Europa 2018-09: 100 %
 *
 * Belegwerte (Zelle, Monat wie oben):
 *   Kairo 44, Niltal bei Asyut 11, Westwüste 27° N 28° O 0,0, Ostwüste 26° N 33° O 0,0
 *   Seoul 35, Daegu 21, Busan 21, Pjöngjang 0,6, Nordkorea 40° N 127° O 0,0
 *   Nigerdelta: hellste Delta-Zelle 33 (5,6° N 6,4° O); Port Harcourt 5,4. (Die Zelle mit 47 bei 4,4° N 8,4° O
 *   liegt östlich des Deltas an der Küste und wird im Text deshalb nicht genannt.)
 *   Bagdad 78, hellste Zelle südwestlich von Basra 112 (30,3° N 47,4° O), Mossul 9, Westirak 0,0
 *   Delhi 50, Kolkata 23, Mumbai 21, Thar 27° N 71° O 0,4, Tibet 32° N 85° O 0,0
 *   Brüssel 31, Madrid 43, Mailand 22, Oslo 16, Lappland 67° N 25° O 0,02
 *   Anteil der Zellen eines Landes (Flächenanteil ≥ 0,5) mit Wert über 1: Südkorea 65 %, Nordkorea 0 %
 *   (2018-10); Indien 23 % (2018-03), Kasten Gangesebene 24,5–30° N/76–88° O 34 %, Zentralindien
 *   19–24° N/76–84° O 10 %; Belgien 81 %, Niederlande 68 %, Frankreich 24 % (2018-09)
 *   Niltal: Assuan 8,9, Luxor 9,2, Sohag 11, Minya 5,8 (2018-10)
 *   Euphrat (2018-10): Ramadi 14, Falludscha 12, Hilla 10, Samawa 6,6, Nasiriya 11; Tigris: Kut 3,5, Amara 28
 *   Indien nur indische Zellen (Flächenanteil ≥ 0,5), ohne Delhi: 24,5–30° N 30 % über 1, 19–24° N/76–84° O 10 %
 *   (Nachprüfung auf Hinweis des Plausibilitäts-Prüfers, 2026-09-28)
 *
 * Aufruf für Bildschirmfotos: globus.html#blickpunkt=korea
 */
(function () {
  "use strict";

  var BLICKPUNKTE = [
    {
      id: "nil", titel: "Nildelta und Ägypten", monat: "2018-10",
      mitte: [31.2, 27.8], zoom: 4.6, einheit: "land_EGY", punkt: [31.24, 30.05],
      text: "Das Licht folgt dem Nil: ein schmales helles Band von Assuan bis Kairo, dazu das breit aufgehellte Delta. " +
        "Die Wüste links und rechts davon ist gemessen dunkel (Zellwert 0,0), nicht fehlend."
    },
    {
      id: "korea", titel: "Korea, Nord und Süd", monat: "2018-10",
      mitte: [127.5, 38.2], zoom: 5.2, einheit: "land_PRK", punkt: [125.75, 39.03],
      text: "In Südkorea ist knapp zwei Drittel der Zellen heller als 1 (Seoul 35, Busan 21), in Nordkorea keine einzige. " +
        "Pjöngjang erscheint nur als kleiner schwacher Fleck (0,6)."
    },
    {
      id: "nigerdelta", titel: "Nigerdelta", monat: "2018-11",
      mitte: [6.6, 5.3], zoom: 5.9, einheit: "land_NGA", punkt: [6.375, 5.625],
      text: "Im Delta liegen einzelne sehr helle Punkte auch abseits der großen Städte (bis 33; Port Harcourt 5).",
      vermutung: "Gasfackeln der Öl- und Gasförderung – naheliegend, aber nicht an einer Fackel-Datenbank geprüft."
    },
    {
      id: "irak", titel: "Irak", monat: "2018-10",
      mitte: [44.5, 32.6], zoom: 5.0, einheit: "land_IRQ", punkt: [47.35, 30.3],
      text: "Das Licht liegt entlang von Euphrat und Tigris (Bagdad 78) und in einer Gruppe sehr heller Punkte südwestlich von Basra (bis rund 110, heller als Bagdad). " +
        "Die Wüste im Westen ist gemessen dunkel."
    },
    {
      id: "indien", titel: "Indien", monat: "2018-03",
      mitte: [80.5, 22.5], zoom: 3.7, einheit: "land_IND", punkt: [77.21, 28.61],
      text: "Viele einzelne helle Städte (Delhi 50, Kolkata 23, Mumbai 21). In der Gangesebene im Norden liegen schwächere Lichter dicht beieinander " +
        "(zwischen 24,5 und 30° N knapp ein Drittel der indischen Zellen über 1, ohne Delhi; in Zentralindien ein Zehntel); die Wüste Thar und Tibet sind fast dunkel."
    },
    {
      id: "europa", titel: "Europa", monat: "2018-09",
      mitte: [10, 50], zoom: 3.4, einheit: null, punkt: null,
      text: "Ein dichtes Netz heller Städte. In Belgien sind vier Fünftel der Zellen heller als 1, in Frankreich ein Viertel (Brüssel 31, Madrid 43). " +
        "Nach Norden wird es spärlich: Lappland ist fast dunkel (0,02)."
    }
  ];

  var G = window.ALEPH_GLOBUS;
  if (!G) return;
  var esc = G.esc;

  function byId(id) { return document.getElementById(id); }

  function baue() {
    var box = document.createElement("section");
    box.id = "blickpunkte";
    box.className = "blickpunkte";
    box.setAttribute("aria-label", "Blickpunkte");
    box.innerHTML = '<div class="bp-kopf">Blickpunkte</div><div class="bp-knoepfe">' +
      BLICKPUNKTE.map(function (b) {
        return '<button class="bp-knopf" data-bp="' + b.id + '">' + esc(b.titel) + "</button>";
      }).join("") + '</div><div id="bp-karte" class="bp-karte" hidden></div>';
    document.body.appendChild(box);
    box.addEventListener("click", function (e) {
      var k = e.target.closest(".bp-knopf");
      if (k) geheZu(k.getAttribute("data-bp"));
      if (e.target.closest(".bp-zu")) { byId("bp-karte").hidden = true; markiere(null); }
    });
  }

  function markiere(id) {
    Array.prototype.forEach.call(document.querySelectorAll(".bp-knopf"), function (k) {
      k.classList.toggle("is-aktiv", k.getAttribute("data-bp") === id);
    });
  }

  function geheZu(id) {
    var b = BLICKPUNKTE.filter(function (x) { return x.id === id; })[0];
    if (!b) return;
    markiere(id);
    var karte = byId("bp-karte");
    karte.innerHTML = '<div class="bp-karte-kopf"><span class="bp-titel">' + esc(b.titel) + '</span><button class="icon-btn bp-zu" aria-label="Schließen">✕</button></div>' +
      '<p class="bp-text">' + esc(b.text) + "</p>" +
      (b.vermutung ? '<p class="bp-vermutung"><b>Vermutung, nicht geprüft:</b> ' + esc(b.vermutung) + "</p>" : "") +
      '<div class="bp-fuss">Monat ' + esc(b.monat) + ' · Evidenzstufe <b>beobachtet</b> · Zahlen: Zellwerte in nW·cm⁻²·sr⁻¹</div>';
    karte.hidden = false;
    G.setzeMonat(b.monat).then(function () {
      var rechts = b.einheit ? 420 : 0;
      G.map.flyTo({ center: b.mitte, zoom: b.zoom, bearing: 0, pitch: 0, duration: 1600, padding: { top: 60, bottom: 120, left: 340, right: rechts } });
      if (b.einheit) G.zeigeEinheit(b.einheit, b.punkt);
      else if (G.dossierOffen()) G.schliesseDossier();
    });
  }

  window.ALEPH_BLICKPUNKTE = BLICKPUNKTE;
  baue();
  document.addEventListener("aleph-bereit", function (e) {
    var h = e.detail || {};
    if (h.blickpunkt) {
      geheZu(h.blickpunkt);
      // Für Bildschirmfotos: Bescheid geben, wenn der Flug vorbei ist.
      G.map.once("moveend", function () { G.map.once("idle", function () { document.body.setAttribute("data-blickpunkt", h.blickpunkt); }); });
    }
  });
})();
