/*
 * ALEPH – Feld „Nachtlicht und Wirtschaftsleistung“ (Teil 3b, 2026-09-28)
 *
 * Liest nur daten/nachtlicht_bip.js: die Ergebnisdatei der Auswertung aus ~/ALEPH
 * (aleph/link/nachtlicht_bip_querschnitt.py). Hier wird NICHTS gerechnet außer der Lage
 * der Punkte auf dem Bildschirm und der Linie aus Steigung und Achsenabschnitt der Datei.
 * Evidenzstufe: statistische Assoziation. Querschnitt, ein Jahr, Afrika-Europa-Asien,
 * kein Beleg für Ursache und Wirkung. Jahre ab 2023 gibt es hier nicht (gesperrt).
 */
(function () {
  "use strict";

  var G = window.ALEPH_GLOBUS, A = window.ALEPH_NACHTLICHT_BIP;
  if (!G) return;
  var esc = G.esc;
  var jahr = "2018";

  function byId(id) { return document.getElementById(id); }
  function de(x, n) { return Number(x).toLocaleString("de-DE", { minimumFractionDigits: n, maximumFractionDigits: n }); }
  function pz(x) { return x == null ? "–" : Math.floor(x * 100 + 1e-9) + " %"; }

  // ---------- Aufbau ----------

  var knopf = document.createElement("button");
  knopf.className = "corner-btn";
  knopf.id = "auswertung-auf";
  knopf.textContent = "Nachtlicht × Wirtschaft";
  knopf.setAttribute("aria-expanded", "false");
  document.querySelector(".corner-group--right").appendChild(knopf);

  var feld = document.createElement("section");
  feld.id = "auswertung";
  feld.className = "auswertung";
  feld.hidden = true;
  feld.setAttribute("aria-label", "Nachtlicht und Wirtschaftsleistung");
  document.body.appendChild(feld);

  function oeffne(an) {
    feld.hidden = !an;
    knopf.setAttribute("aria-expanded", an ? "true" : "false");
    if (an) zeichne();
  }
  knopf.addEventListener("click", function () { oeffne(feld.hidden); });

  function einheitFuer(code) {
    var beste = null, idx = G.einheiten();
    Object.keys(idx).forEach(function (id) {
      var p = idx[id].properties;
      if (p.weltbank_code !== code || String(p.ebene).indexOf("Land") !== 0) return;
      if (!beste || (p.flaeche_km2 || 0) > (idx[beste].properties.flaeche_km2 || 0)) beste = id;
    });
    return beste;
  }

  function geheZuLand(code) {
    var id = einheitFuer(code);
    if (!id) return;
    oeffne(false);
    G.springeZuEinheit(id);
  }

  // ---------- Punktwolke (SVG) ----------

  var B = 600, H = 330, RAND = { l: 58, r: 32, o: 12, u: 40 };

  function streudiagramm(j) {
    var pkt = j.punkte, r = j.varianten.haupt;
    var xs = pkt.map(function (p) { return p.x; }), ys = pkt.map(function (p) { return p.y; });
    var x0 = Math.floor(Math.min.apply(null, xs) / Math.LN10) * Math.LN10, x1 = Math.ceil(Math.max.apply(null, xs) / Math.LN10) * Math.LN10;
    var y0 = Math.floor(Math.min.apply(null, ys) / Math.LN10) * Math.LN10, y1 = Math.ceil(Math.max.apply(null, ys) / Math.LN10) * Math.LN10;
    function sx(x) { return RAND.l + (x - x0) / (x1 - x0) * (B - RAND.l - RAND.r); }
    function sy(y) { return H - RAND.u - (y - y0) / (y1 - y0) * (H - RAND.o - RAND.u); }
    var teile = [];
    // Gitter und Achsen (Zehnerpotenzen)
    var GELD = { 8: "100 Mio.", 9: "1 Mrd.", 10: "10 Mrd.", 11: "100 Mrd.", 12: "1 Bio.", 13: "10 Bio.", 14: "100 Bio." };
    for (var e = Math.round(x0 / Math.LN10); e <= Math.round(x1 / Math.LN10); e++) {
      var xx = sx(e * Math.LN10);
      teile.push('<line class="ad-gitter" x1="' + xx + '" x2="' + xx + '" y1="' + RAND.o + '" y2="' + (H - RAND.u) + '"/>');
      teile.push('<text class="ad-achse" x="' + xx + '" y="' + (H - RAND.u + 15) + '" text-anchor="middle">' + (GELD[e] || "1e" + e) + "</text>");
    }
    for (var f = Math.round(y0 / Math.LN10); f <= Math.round(y1 / Math.LN10); f++) {
      var yy = sy(f * Math.LN10);
      teile.push('<line class="ad-gitter" x1="' + RAND.l + '" x2="' + (B - RAND.r) + '" y1="' + yy + '" y2="' + yy + '"/>');
      teile.push('<text class="ad-achse" x="' + (RAND.l - 6) + '" y="' + (yy + 3.5) + '" text-anchor="end">10<tspan dy="-5" font-size="8">' + f + "</tspan></text>");
    }
    teile.push('<text class="ad-achse ad-titel" x="' + ((B + RAND.l) / 2) + '" y="' + (H - 6) + '" text-anchor="middle">reales BIP ' + esc(jahr) + " (US-Dollar, konstante Preise 2015, log. Skala)</text>");
    teile.push('<text class="ad-achse ad-titel" transform="translate(13 ' + ((H - RAND.u + RAND.o) / 2) + ') rotate(-90)" text-anchor="middle">Jahres-Lichtsumme (log. Skala)</text>');
    // Linie
    teile.push('<line class="ad-linie" x1="' + sx(x0) + '" y1="' + sy(r.achsenabschnitt + r.steigung * x0) + '" x2="' + sx(x1) + '" y2="' + sy(r.achsenabschnitt + r.steigung * x1) + '"/>');
    // Punkte mit Kürzeln
    pkt.forEach(function (p) {
      var cx = sx(p.x), cy = sy(p.y), mark = p.kennzeichen && p.kennzeichen.length;
      var tip = p.name + " (" + p.code + "): " + (p.faktor >= 1 ? de(p.faktor, 1) + "-mal mehr" : de(1 / p.faktor, 1) + "-mal weniger") +
        " Licht als die Linie" + (mark ? " · " + p.kennzeichen.join("; ") : "");
      teile.push('<g class="ad-punkt' + (mark ? " ad-punkt--mark" : "") + '" data-code="' + esc(p.code) + '" tabindex="0" role="button" aria-label="' + esc(tip) + '">' +
        "<title>" + esc(tip) + "</title>" +
        '<circle class="ad-treffer" cx="' + cx + '" cy="' + cy + '" r="9"/>' +
        '<circle class="ad-kreis" cx="' + cx + '" cy="' + cy + '" r="4"/>' +
        '<text class="ad-kuerzel" x="' + (cx + 5.5) + '" y="' + (cy - 4) + '">' + esc(p.code) + "</text></g>");
    });
    return '<svg class="ad-svg" viewBox="0 0 ' + B + " " + H + '" role="img" aria-label="Punktwolke Nachtlicht gegen reales BIP ' + esc(jahr) + '">' + teile.join("") + "</svg>";
  }

  // ---------- Inhalt ----------

  function variantenTabelle() {
    var zeilen = Object.keys(A.varianten_text).map(function (k) {
      var z = ["2018", "2019"].map(function (y) {
        var v = A.jahre[y] && A.jahre[y].varianten[k];
        return v ? "<td>" + de(v.steigung, 2) + " [" + de(v.steigung_unten, 2) + "; " + de(v.steigung_oben, 2) + "]</td><td>" + de(v.r2, 2) + "</td><td>" + v.n + "</td>" : "<td colspan=3>–</td>";
      }).join("");
      return "<tr><th>" + esc(A.varianten_text[k]) + "</th>" + z + "</tr>";
    }).join("");
    return '<table class="ad-tabelle"><thead><tr><th></th><th colspan="3">2018</th><th colspan="3">2019</th></tr>' +
      "<tr><th>Rechnung</th><th>Steigung [95 %]</th><th>R²</th><th>n</th><th>Steigung [95 %]</th><th>R²</th><th>n</th></tr></thead><tbody>" + zeilen + "</tbody></table>";
  }

  function ausgeschlossen(j) {
    function ausserhalb(l) { return l.gruende.some(function (g) { return g.indexOf("nicht vollständig geladen") === 0 || g.indexOf("nicht in Afrika-Europa-Asien") === 0; }); }
    var liste = j.laender.filter(function (l) { return !l.aufgenommen && l.bip != null && !ausserhalb(l); });
    var amerika = j.laender.filter(function (l) { return !l.aufgenommen && ausserhalb(l); }).length;
    var ohneBip = j.laender.filter(function (l) { return !l.aufgenommen && l.bip == null; }).length;
    return "<ul class=\"ad-liste\">" + liste.map(function (l) {
      return "<li><b>" + esc(l.name) + "</b> (" + esc(l.code) + "): " + esc(l.gruende.join("; ")) + "</li>";
    }).join("") + "</ul><p class=\"ad-klein\">Außerdem nicht aufgenommen: " + amerika + " Länder und Gebiete außerhalb der Region oder noch nicht vollständig geladen (Amerika, Ozeanien), und " +
      ohneBip + " Einträge ohne reales BIP der Weltbank für " + esc(jahr) + ". Gebiete ohne eigene Weltbank-Zahl " +
      "(z. B. Taiwan, der östliche Teil der Westsahara, Nordzypern, Krim) gehören zu keinem Weltbank-Land und sind nicht Teil der Rechnung.</p>";
  }

  function zeichne() {
    if (!A || !A.verfuegbar) {
      feld.innerHTML = '<div class="ad-kopf"><h2>Nachtlicht und Wirtschaftsleistung</h2><button class="icon-btn ad-zu" aria-label="Schließen">✕</button></div>' +
        '<div class="hinweis hinweis--stark">Nicht verfügbar: ' + esc(A ? A.grund : "Datei daten/nachtlicht_bip.js fehlt") + "</div>";
      return;
    }
    var j = A.jahre[jahr], r = j.varianten.haupt;
    var gegen = jahr === "2018" ? "2019" : "2018", rg = A.jahre[gegen] && A.jahre[gegen].varianten.haupt;
    var abw = j.groesste_abweichung.map(function (p) {
      return "<li>" + esc(p.name) + " (" + esc(p.code) + "): " + (p.faktor >= 1 ? de(p.faktor, 1) + "-mal mehr" : de(1 / p.faktor, 1) + "-mal weniger") + " Licht als die Linie</li>";
    }).join("");
    var gas = Object.keys(A.gasfackel_hinweis.laender).map(function (c) { return A.gasfackel_hinweis.laender[c] + " (" + c + ")"; }).join(", ");
    feld.innerHTML =
      '<div class="ad-kopf"><h2>Nachtlicht und Wirtschaftsleistung ' + esc(jahr) + "</h2>" +
      '<div class="ad-schalter" role="group" aria-label="Jahr">' + ["2018", "2019"].map(function (y) {
        return '<button class="ad-jahr' + (y === jahr ? " is-aktiv" : "") + '" data-jahr="' + y + '">' + y + "</button>";
      }).join("") + '</div><button class="icon-btn ad-zu" aria-label="Schließen">✕</button></div>' +
      '<p class="ad-satz">Über ' + r.n + " Länder hinweg geht 1 % mehr reales BIP im Mittel mit etwa " + de(r.steigung, 2) +
      " % mehr Nachtlicht einher (95-%-Bereich " + de(r.steigung_unten, 2) + " bis " + de(r.steigung_oben, 2) + "; R² " + de(r.r2, 2) + ")" +
      (rg ? "; " + gegen + ": " + de(rg.steigung, 2) + " [" + de(rg.steigung_unten, 2) + "; " + de(rg.steigung_oben, 2) + "]." : ".") + "</p>" +
      streudiagramm(j) +
      '<div class="ad-legende"><span><svg width="12" height="12"><circle cx="6" cy="6" r="4" class="ad-kreis"/></svg> Land</span>' +
      '<span><svg width="12" height="12"><circle cx="6" cy="6" r="4" class="ad-kreis ad-kreis--mark"/></svg> Land mit Kennzeichen (z. B. wenige gute Monate, Gasfackel-Hinweis)</span>' +
      '<span><svg width="18" height="12"><line x1="1" y1="6" x2="17" y2="6" class="ad-linie"/></svg> Linie (kleinste Quadrate)</span>' +
      "<span>Punkt anklicken: zum Land fliegen</span></div>" +
      '<div class="ad-rahmen"><div><b>Evidenzstufe: statistische Assoziation</b></div>' +
      "<div>Querschnitt, ein Jahr, Afrika-Europa-Asien, kein Beleg für Ursache und Wirkung</div>" +
      "<div>" + r.n + ' Länder · <a href="#" class="ad-link" data-ziel="ad-aus">Liste der ausgeschlossenen Länder</a></div></div>' +
      '<details class="ad-details"><summary>Gegenrechnungen (2018 und 2019 nebeneinander)</summary>' + variantenTabelle() + "</details>" +
      '<details class="ad-details"><summary>Die 10 Länder mit der größten Abweichung von der Linie</summary><ol class="ad-liste">' + abw + "</ol>" +
      '<p class="ad-klein">Gasfackeln sind nicht herausgerechnet. Hinweis auf viel Licht aus Fördergebieten gibt es bisher für ' + esc(gas) +
      " (" + esc(A.gasfackel_hinweis.grundlage) + "). Für die übrigen Länder der Liste ist kein Grund geprüft.</p></details>" +
      '<details class="ad-details" id="ad-aus"><summary>Ausgeschlossene Länder mit Grund</summary>' + ausgeschlossen(j) + "</details>" +
      '<details class="ad-details"><summary>Wie gerechnet</summary><p class="ad-klein">' +
      "Jahreswert je Zelle: Mittel der Monate mit mindestens 50 % beobachteten Pixeln und ohne Schnee-Verdacht, nur bei mindestens 6 solchen Monaten. " +
      "Licht einer Grenzzelle nach Flächenanteil verteilt. Ausgeschlossen: Weltbank-Gebiet weicht ab (Georgien, Moldau, Tansania, Marokko, Zypern), " +
      "unter 50 % des Lichts aus Zellen nur dieses Landes, unter 90 % des Lichts mit gültigem Jahreswert, nicht vollständig geladen. " +
      "Steigung aus ln(Licht) gegen ln(BIP); 95-%-Bereich per Bootstrap über Länder (" + (r.bootstrap_n || "") + " Wiederholungen). " +
      "Feld: " + esc(A.feld) + ". Sicht: " + esc(A.sicht) + ". Ein Literaturvergleich entfällt: " + esc(A.literaturvergleich) + ". " +
      "Methodenprüfung: " + esc(A.statistik_pruefer) + ". Stand " + esc(A.erstellt_utc) + ".</p></details>";
  }

  feld.addEventListener("click", function (e) {
    if (e.target.closest(".ad-zu")) { oeffne(false); return; }
    var jb = e.target.closest(".ad-jahr");
    if (jb) { jahr = jb.getAttribute("data-jahr"); zeichne(); return; }
    var l = e.target.closest(".ad-link");
    if (l) { e.preventDefault(); var d = byId(l.getAttribute("data-ziel")); d.open = true; d.scrollIntoView({ block: "start" }); return; }
    var p = e.target.closest(".ad-punkt");
    if (p) geheZuLand(p.getAttribute("data-code"));
  });
  feld.addEventListener("keydown", function (e) {
    var p = e.target.closest && e.target.closest(".ad-punkt");
    if (p && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); geheZuLand(p.getAttribute("data-code")); }
  });

  document.addEventListener("aleph-bereit", function (e) {
    var h = e.detail || {};
    if (h.auswertung) { jahr = h.auswertung === "2019" ? "2019" : "2018"; oeffne(true); }
  });
})();
