/*
 * ALEPH – Ländervergleich (2026-09-29)
 *
 * Bis zu 4 Länder nebeneinander, als kleine Grafiken mit GLEICHEN Achsen (gleiche Zeitachse, gleicher
 * Wertebereich über alle Länder). Liest nur daten/laender_zeitreihen.js über die Bausteine der Länderansicht
 * (window.ALEPH_ZR). Es wird nichts gerechnet und kein Zusammenhang behauptet.
 *
 * Farben: Jedes Land behält seine Farbe, solange es im Vergleich ist (Farbe folgt dem Land, nicht der
 * Reihenfolge). Die vier Farben sind so gewählt, dass sie nicht wie die Farben der Datenlage (grau, beige,
 * blau-lila gestreift, rot markiert) oder der Sondereinheiten (orange, rosa, hellblau) aussehen, und mit dem
 * Farbprüfer der Datenvisualisierungs-Regeln geprüft (auf dem dunklen Feld: Rot-Grün-Schwäche ΔE ≥ 9,9,
 * normales Sehen ΔE ≥ 17,8). Zusätzlich hat jedes Land eine eigene Form und sein Kürzel steht daneben, damit
 * nichts nur an der Farbe hängt.
 * Einstieg: Suche im Feld, Knopf „Zum Vergleich hinzufügen“ im Länderfeld (Klick auf dem Globus),
 * Klick in der Punktwolke (Schalter „Klick fügt zum Vergleich hinzu“). Adresse: #laendervergleich=DEU,EGY&index=1
 * (NICHT #vergleich=…: das ist der Schlüssel des Vorjahresvergleichs auf dem Globus).
 */
(function () {
  "use strict";

  var G = window.ALEPH_GLOBUS, ZR = window.ALEPH_ZR;
  if (!G || !ZR) return;
  var Z = ZR.Z, esc = G.esc, MAX = 4;
  var PLAETZE = [
    { farbe: "#14966e", form: "kreis", name: "grün, Kreis" },
    { farbe: "#9a6ff0", form: "quadrat", name: "violett, Quadrat" },
    { farbe: "#aab030", form: "dreieck", name: "gelbgrün, Dreieck" },
    { farbe: "#d9532c", form: "raute", name: "rostrot, Raute" }
  ];
  var auswahl = []; // [{code, platz}]
  var zustand = { index: false, bezug: "summe", punktwolkeKlick: false, meldung: "" };

  function platzVon(code) { for (var i = 0; i < auswahl.length; i++) if (auswahl[i].code === code) return PLAETZE[auswahl[i].platz]; return null; }
  function symbol(p, groesse) {
    var g = groesse || 12;
    return '<svg class="vg-sym" width="' + g + '" height="' + g + '" aria-hidden="true">' + ZR.form(p.form, g / 2, g / 2, g * 0.3, 'fill="' + p.farbe + '"') + "</svg>";
  }

  // ---------- Aufbau ----------
  var knopf = document.createElement("button");
  knopf.className = "corner-btn";
  knopf.id = "vergleich-auf";
  knopf.setAttribute("aria-expanded", "false");
  var gruppe = document.querySelector(".corner-group--right");
  gruppe.appendChild(knopf);
  function knopfText() { knopf.textContent = "Ländervergleich" + (auswahl.length ? " (" + auswahl.length + ")" : ""); }
  knopfText();

  var feld = document.createElement("section");
  feld.id = "laendervergleich";
  feld.className = "auswertung zr vg";
  feld.hidden = true;
  feld.setAttribute("aria-label", "Ländervergleich");
  document.body.appendChild(feld);

  function oeffne() {
    var aw = document.getElementById("auswertung");
    if (aw && !aw.hidden) aw.hidden = true;
    document.dispatchEvent(new CustomEvent("aleph-feld-auf", { detail: "vergleich" }));
    feld.hidden = false;
    knopf.setAttribute("aria-expanded", "true");
    zeichne();
  }
  function schliesse() { feld.hidden = true; knopf.setAttribute("aria-expanded", "false"); }
  knopf.addEventListener("click", function () { if (feld.hidden) oeffne(); else schliesse(); });
  document.addEventListener("aleph-feld-auf", function (e) { if (e.detail !== "vergleich") schliesse(); });

  function hinzu(code, oeffnen) {
    zustand.meldung = "";
    if (!Z || !Z.verfuegbar || !Z.laender[code]) {
      zustand.meldung = "Für „" + code + "“ gibt es keine Zeitreihe.";
    } else if (!platzVon(code)) {
      if (auswahl.length >= MAX) {
        zustand.meldung = "Höchstens " + MAX + " Länder. Bitte zuerst ein Land entfernen (✕ neben dem Namen).";
      } else {
        var belegt = auswahl.map(function (a) { return a.platz; }), frei = 0;
        while (belegt.indexOf(frei) >= 0) frei++;
        auswahl.push({ code: code, platz: frei });
      }
    }
    knopfText();
    markierePunktwolke();
    if (oeffnen) oeffne(); else if (!feld.hidden) zeichne();
  }
  function entferne(code) {
    auswahl = auswahl.filter(function (a) { return a.code !== code; });
    zustand.meldung = "";
    knopfText();
    markierePunktwolke();
    zeichne();
  }

  // ---------- Suche ----------
  function normal(s) { return String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, ""); }
  function treffer(q) {
    q = normal(q.trim());
    if (!q || !Z || !Z.verfuegbar) return [];
    return Object.keys(Z.laender).filter(function (c) {
      return normal(ZR.landName(c)).indexOf(q) >= 0 || normal(Z.laender[c].name).indexOf(q) >= 0 || normal(c) === q;
    }).sort(function (a, b) { return ZR.landName(a).localeCompare(ZR.landName(b), "de"); }).slice(0, 8);
  }

  // ---------- Grafiken ----------
  var BREITE = 400;
  function landGrafiken(bz, achse) {
    var laender = auswahl.map(function (a) { return { code: a.code, p: PLAETZE[a.platz], l: Z.laender[a.code], name: ZR.landName(a.code) }; });
    function kopf(x) { return symbol(x.p) + " " + esc(x.name) + ' <span class="zr-code">' + esc(x.code) + "</span>"; }
    var html = "";
    if (zustand.index) {
      var alle = [], je = laender.map(function (x) {
        var lp = ZR.indexPunkte(x.l, bz.jahr, x.name, bz.lichtName + " (Jahreswert)");
        var bp = bz.bip ? ZR.indexPunkte(x.l, bz.bip, x.name, bz.bipName) : [];
        alle.push(lp, bp);
        return { x: x, lp: lp, bp: bp };
      });
      var b = ZR.indexBereich(alle);
      html += '<div class="zr-gkopf"><span class="zr-gtitel">Index (2018 = 100): ' + esc(bz.lichtName) + " als Jahreswert" + (bz.bip ? " und " + esc(bz.bipName) : "") +
        '</span><span class="zr-geinheit">gleiche Achse für alle Länder</span></div><div class="vg-raster">' + je.map(function (e) {
          if (!e.lp.length && !e.bp.length) return ZR.leereGrafik(kopf(e.x), "Kein Index: kein gültiger Wert für 2018.");
          var reihen = [{ farbe: e.x.p.farbe, form: e.x.p.form, maxAbstand: 12, punkte: e.lp, beschriftung: e.lp.length ? "Licht" : "" }];
          if (bz.bip) reihen.push({ farbe: e.x.p.farbe, form: e.x.p.form, strich: "4 3", hohl: true, maxAbstand: 12,
            punkte: e.bp.map(function (q) { q.art = q.art; return q; }), beschriftung: e.bp.length ? "BIP" : "" });
          return ZR.grafik({ achse: achse, y0: b.y0, y1: b.y1, bezugsLinie: 100, hoehe: 170, breite: BREITE, titel: kopf(e.x), titelText: e.x.name, reihen: reihen });
        }).join("") + "</div>";
      if (bz.bip) html += '<div class="ad-legende"><span><svg width="18" height="10"><line x1="1" y1="5" x2="17" y2="5" stroke="var(--text)" stroke-width="2"/></svg> Licht (durchgezogen)</span>' +
        '<span><svg width="18" height="10"><line x1="1" y1="5" x2="17" y2="5" stroke="var(--text)" stroke-width="2" stroke-dasharray="4 3"/></svg> ' + esc(bz.bipName) + " (gestrichelt)</span><span>Linie bei 100 = Stand 2018</span></div>";
      html += '<div class="zr-klein">Die Jahreswerte beruhen je Jahr auf unterschiedlichen guten Monaten; kleine Indexunterschiede können daher aus der Messung stammen. ' +
        "Ein Index vergleicht jedes Land nur mit sich selbst (2018); er sagt nichts über die Größe der Länder." + (bz.hinweis ? " " + esc(bz.hinweis) : "") + "</div>";
      return html;
    }
    // absolut: Zeile Nachtlicht monatlich, Zeile BIP – je Zeile gleicher Wertebereich für alle Länder
    var mp = laender.map(function (x) { return ZR.monatsPunkte(x.l, bz, x.name); });
    var bm = ZR.bereich(mp, true);
    html += '<div class="zr-gkopf"><span class="zr-gtitel">Nachtlicht monatlich – ' + esc(bz.lichtName) + '</span><span class="zr-geinheit">' + esc(bz.einheit) +
      " · gleiche Achse für alle Länder</span></div>" + '<div class="vg-raster">' + laender.map(function (x, i) {
        if (!mp[i].length) return ZR.leereGrafik(kopf(x), "Kein Monatswert (" + esc(x.l.monate.length ? ZR.statusText(x.l.monate[x.l.monate.length - 1]) : "keine Daten") + ").");
        return ZR.grafik({ achse: achse, y0: bm.y0, y1: bm.y1, breite: BREITE, titel: kopf(x), titelText: x.name, reihen: [{ farbe: x.p.farbe, form: x.p.form, maxAbstand: 1, klein: true, punkte: mp[i] }] });
      }).join("") + "</div>" +
      '<div class="ad-legende"><span>voll: Summe über die gemessene Fläche (mind. 90 %)</span><span>hohl: Schnee-Verdacht</span><span>hohl und blass: unter 90 % gemessen, nur Teilsumme</span><span>Lücke = kein Wert</span></div>';
    if (bz.bip) {
      var bp = laender.map(function (x) { return ZR.jahrPunkte(x.l, bz.bip, x.name, bz.bipName); });
      var bb = ZR.bereich(bp, true);
      html += '<div class="zr-gkopf"><span class="zr-gtitel">' + esc(bz.bipName) + ' (Weltbank, jährlich)</span><span class="zr-geinheit">' + esc(bz.bipEinheit) +
        " · gleiche Achse für alle Länder</span></div>" + '<div class="vg-raster">' + laender.map(function (x, i) {
          if (!bp[i].length) return ZR.leereGrafik(kopf(x), "Kein Weltbank-Wert.");
          return ZR.grafik({ achse: achse, y0: bb.y0, y1: bb.y1, breite: BREITE, hoehe: 110, titel: kopf(x), titelText: x.name, reihen: [{ farbe: x.p.farbe, form: x.p.form, maxAbstand: 12, punkte: bp[i] }] });
        }).join("") + "</div>";
    } else {
      html += '<div class="zr-hinweis">' + esc(bz.hinweis) + "</div>";
    }
    return html;
  }

  function tabelle(bz) {
    var jahre = [];
    auswahl.forEach(function (a) { Object.keys(Z.laender[a.code].jahre).forEach(function (j) { if (jahre.indexOf(j) < 0) jahre.push(j); }); });
    jahre.sort();
    var sig2 = ZR.sig2;
    var kopf = "<tr><th>Land</th>" + jahre.map(function (j) { return "<th>Licht " + j + "</th>"; }).join("") +
      (bz.bip ? jahre.map(function (j) { return "<th>" + (bz.bip === "bip_real" ? "BIP " : "BIP/Kopf ") + j + "</th>"; }).join("") : "") + "</tr>";
    var zeilen = auswahl.map(function (a) {
      var l = Z.laender[a.code], p = PLAETZE[a.platz];
      var licht = jahre.map(function (j) {
        var e = l.jahre[j];
        if (!e) return "<td>–</td>";
        if (zustand.index) { var v = (l.index[bz.jahr] || {})[j]; return "<td>" + (v != null ? v : "–") + "</td>"; }
        return "<td>" + (e[bz.jahr] != null ? sig2(e[bz.jahr]) : '<span class="zr-fehlt" title="' + esc(e.licht_grund || "") + '">–</span>') + "</td>";
      }).join("");
      var bip = bz.bip ? jahre.map(function (j) {
        var e = l.jahre[j];
        if (!e) return "<td>–</td>";
        var vl = e[bz.bip + "_vorlaeufig"] ? " (vorl.)" : "";
        if (zustand.index) { var v = (l.index[bz.bip] || {})[j]; return "<td>" + (v != null ? v + vl : "–") + "</td>"; }
        return "<td>" + (e[bz.bip] != null ? sig2(e[bz.bip]) + vl : "–") + "</td>";
      }).join("") : "";
      return "<tr><th>" + symbol(p, 10) + " " + esc(ZR.landName(a.code)) + " (" + esc(a.code) + ")</th>" + licht + bip + "</tr>";
    }).join("");
    return '<div class="zr-tkopf">Vergleichstabelle' + (zustand.index ? " (Index, 2018 = 100)" : " (Jahreswerte)") + "</div>" +
      '<div class="vg-tabwrap"><table class="ad-tabelle zr-tabelle"><thead>' + kopf + "</thead><tbody>" + zeilen + "</tbody></table></div>" +
      '<div class="zr-klein">Licht: Jahreswert nach den Regeln der Auswertung 2018; „–“ = kein gültiger Jahreswert (Grund in der Länderansicht). ' +
      "Weltbank-Werte „(vorl.)“ = vorläufig.</div>";
  }

  function kennzeichenKurz() {
    var z = auswahl.map(function (a) {
      var k = Z.laender[a.code].kennzeichen, t = [];
      if (k.gebiet_weltbank === "abweichend") t.push("Gebiet der Weltbank-Zahl weicht ab");
      else if (k.gebiet_weltbank === "unklar") t.push("Gebiet der Weltbank-Zahl unklar");
      if (k.monate_nicht_geladen) t.push("in " + k.monate_nicht_geladen + " Monaten noch nicht geladen");
      if (k.monate_gering) t.push("geringe Abdeckung in " + k.monate_gering + " Monaten");
      if (k.monate_schnee) t.push("Schnee-Verdacht in " + k.monate_schnee + " Monaten");
      if (k.nord65_prozent) t.push(k.nord65_prozent + " % des Lichts nördlich von 65° N");
      if (!k.pro_kopf_erlaubt) t.push("kein Pro-Kopf-Wert");
      return "<li>" + symbol(PLAETZE[a.platz], 10) + " <b>" + esc(ZR.landName(a.code)) + "</b>: " + (t.length ? esc(t.join("; ")) : "keine Kennzeichen") + "</li>";
    }).join("");
    return '<ul class="ad-liste vg-kennz">' + z + "</ul>";
  }

  function zeichne() {
    var suchText = (feld.querySelector("#vg-suche") || {}).value || "";
    var kopf = '<div class="ad-kopf"><h2>Ländervergleich</h2><button class="icon-btn ad-zu" aria-label="Schließen">✕</button></div>';
    if (!Z || !Z.verfuegbar) {
      feld.innerHTML = kopf + '<div class="hinweis hinweis--stark">Nicht verfügbar: ' + esc(Z ? Z.grund : "Datei daten/laender_zeitreihen.js fehlt") + "</div>";
      return;
    }
    var chips = auswahl.map(function (a) {
      return '<span class="vg-chip">' + symbol(PLAETZE[a.platz]) + " " + esc(ZR.landName(a.code)) + ' <span class="zr-code">' + esc(a.code) +
        '</span><button class="vg-weg" data-code="' + esc(a.code) + '" aria-label="' + esc(ZR.landName(a.code)) + ' entfernen">✕</button></span>';
    }).join("");
    var modus = '<div class="ad-schalter" role="group" aria-label="Darstellung">' +
      '<button class="ad-jahr vg-modus' + (!zustand.index ? " is-aktiv" : "") + '" data-index="0">absolut</button>' +
      '<button class="ad-jahr vg-modus' + (zustand.index ? " is-aktiv" : "") + '" data-index="1">Index (2018 = 100)</button></div>';
    var bez = '<div class="ad-schalter" role="group" aria-label="Bezugsgröße">' + Object.keys(ZR.BEZUG).map(function (k) {
      return '<button class="ad-jahr vg-bezug' + (zustand.bezug === k ? " is-aktiv" : "") + '" data-bezug="' + k + '">' + esc(ZR.BEZUG[k].knopf) + "</button>";
    }).join("") + "</div>";
    var suche = '<div class="vg-suchzeile"><input id="vg-suche" type="text" autocomplete="off" placeholder="Land hinzufügen (bis zu ' + MAX + ') …" value="' + esc(suchText) + '"' +
      (auswahl.length >= MAX ? " disabled" : "") + '><div id="vg-treffer" class="vg-treffer"></div></div>';
    var inhalt;
    if (!auswahl.length) {
      inhalt = '<div class="zr-leer">Noch kein Land gewählt. Land suchen, auf dem Globus ein Land anklicken und „Zum Vergleich hinzufügen“ wählen, ' +
        "oder in der Punktwolke „Nachtlicht × Wirtschaft“ den Schalter „Klick fügt zum Vergleich hinzu“ einschalten.</div>";
    } else {
      var bz = ZR.BEZUG[zustand.bezug], achse = ZR.zeitachse();
      inhalt = kennzeichenKurz() + landGrafiken(bz, achse) + tabelle(bz);
    }
    feld.innerHTML = kopf + '<div class="vg-chips">' + chips + suche + "</div>" +
      (zustand.meldung ? '<div class="hinweis hinweis--stark">' + esc(zustand.meldung) + "</div>" : "") +
      '<div class="zr-schalter">' + modus + bez + "</div>" + ZR.rahmen() + inhalt + ZR.datenstand() +
      '<div class="zr-klein">Farben der Länder: ' + PLAETZE.map(function (p) { return symbol(p, 10) + " " + esc(p.name); }).join(" · ") +
      " – bewusst verschieden von den Farben für Datenlage und Sondereinheiten; jedes Land hat zusätzlich eine eigene Form.</div>";
    var s = feld.querySelector("#vg-suche");
    if (suchText && s) { s.focus(); s.setSelectionRange(suchText.length, suchText.length); zeigeTreffer(); }
  }

  function zeigeTreffer() {
    var s = feld.querySelector("#vg-suche"), box = feld.querySelector("#vg-treffer");
    if (!s || !box) return;
    var t = treffer(s.value);
    box.innerHTML = t.map(function (c) {
      return '<button class="search-item vg-nimm" data-code="' + esc(c) + '"><span>' + esc(ZR.landName(c)) + '</span><span class="item-sub">' + esc(c) + "</span></button>";
    }).join("") || (s.value.trim() ? '<div class="search-empty">Kein Land mit Zeitreihe heißt so.</div>' : "");
  }

  feld.addEventListener("input", function (e) { if (e.target.id === "vg-suche") zeigeTreffer(); });
  feld.addEventListener("keydown", function (e) {
    if (e.target.id !== "vg-suche" || e.key !== "Enter") return;
    var erster = feld.querySelector(".vg-nimm");
    if (erster) { e.target.value = ""; hinzu(erster.getAttribute("data-code")); }
  });
  feld.addEventListener("click", function (e) {
    if (e.target.closest(".ad-zu")) { schliesse(); return; }
    var n = e.target.closest(".vg-nimm");
    if (n) { var s = feld.querySelector("#vg-suche"); if (s) s.value = ""; hinzu(n.getAttribute("data-code")); return; }
    var w = e.target.closest(".vg-weg");
    if (w) { entferne(w.getAttribute("data-code")); return; }
    var m = e.target.closest(".vg-modus");
    if (m) { zustand.index = m.getAttribute("data-index") === "1"; zeichne(); return; }
    var b = e.target.closest(".vg-bezug");
    if (b) { zustand.bezug = b.getAttribute("data-bezug"); zeichne(); }
  });

  // ---------- Punktwolke: Länder im Vergleich markieren, Klick zum Hinzufügen ----------
  function markierePunktwolke() {
    var aw = document.getElementById("auswertung");
    if (!aw) return;
    Array.prototype.forEach.call(aw.querySelectorAll(".vg-ring"), function (r) { r.parentNode.removeChild(r); });
    Array.prototype.forEach.call(aw.querySelectorAll(".ad-punkt"), function (g) {
      var p = platzVon(g.getAttribute("data-code"));
      if (!p) return;
      var k = g.querySelector(".ad-kreis");
      var cx = Number(k.getAttribute("cx")), cy = Number(k.getAttribute("cy"));
      var ns = "http://www.w3.org/2000/svg", ring = document.createElementNS(ns, "g");
      ring.setAttribute("class", "vg-ring");
      ring.innerHTML = ZR.form(p.form, cx, cy, 7.5, 'fill="none" stroke="' + p.farbe + '" stroke-width="2.4"') +
        '<text x="' + (cx + 9) + '" y="' + (cy + 12) + '" fill="' + p.farbe + '" font-size="10" font-weight="600" font-family="IBM Plex Sans, sans-serif">' + esc(g.getAttribute("data-code")) + "</text>";
      g.appendChild(ring);
    });
    var leg = aw.querySelector(".ad-legende");
    if (leg && !aw.querySelector(".vg-pw-zeile")) {
      var z = document.createElement("div");
      z.className = "vg-pw-zeile";
      leg.parentNode.insertBefore(z, leg.nextSibling);
    }
    var zeile = aw.querySelector(".vg-pw-zeile");
    if (zeile) {
      zeile.innerHTML = '<label class="vg-pw-schalter"><input type="checkbox" id="vg-pw-klick"' + (zustand.punktwolkeKlick ? " checked" : "") +
        "> Klick fügt zum Ländervergleich hinzu (statt zum Land zu fliegen)</label>" +
        (auswahl.length ? '<span class="vg-pw-liste">Im Vergleich: ' + auswahl.map(function (a) {
          return symbol(PLAETZE[a.platz], 10) + " " + esc(a.code);
        }).join(" ") + ' · <a href="#" class="vg-pw-auf">Vergleich öffnen</a></span>' : "");
    }
  }
  var aw0 = document.getElementById("auswertung");
  if (aw0) {
    new MutationObserver(function (liste) {
      // nur neu zeichnen, wenn das Feld selbst neu aufgebaut wurde (nicht bei eigenen Markierungen)
      if (liste.some(function (m) { return m.target === aw0; })) markierePunktwolke();
    }).observe(aw0, { childList: true });
    aw0.addEventListener("change", function (e) { if (e.target.id === "vg-pw-klick") zustand.punktwolkeKlick = e.target.checked; });
    aw0.addEventListener("click", function (e) {
      var a = e.target.closest(".vg-pw-auf");
      if (a) { e.preventDefault(); oeffne(); return; }
      var p = e.target.closest(".ad-punkt");
      if (p && zustand.punktwolkeKlick) {
        e.stopPropagation();
        hinzu(p.getAttribute("data-code"));
      }
    }, true);
  }

  // ---------- Adresse: #laendervergleich=DEU,EGY,IND,NGA&index=1&bezug=pro_kopf ----------
  document.addEventListener("aleph-bereit", function (e) {
    var h = e.detail || {};
    if (h.bezug && ZR.BEZUG[h.bezug]) zustand.bezug = h.bezug;
    if (h.index === "1") zustand.index = true;
    if (h.laendervergleich) {
      h.laendervergleich.split(",").slice(0, MAX).forEach(function (c) { if (c) hinzu(c.trim().toUpperCase()); });
      if (!h.auswertung) oeffne();
    }
  });

  window.ALEPH_VERGLEICH = { hinzu: hinzu, entferne: entferne, oeffne: oeffne, liste: function () { return auswahl.map(function (a) { return a.code; }); } };
})();
