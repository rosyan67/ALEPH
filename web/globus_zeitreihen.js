/*
 * ALEPH – Länderansicht mit Zeitreihen (2026-09-29)
 *
 * Liest nur daten/laender_zeitreihen.js: die Ergebnisdatei aus ~/ALEPH (aleph/link/laender_zeitreihen.py,
 * Regeln F1–F9 im Modulkopf dort). Hier wird NICHTS gerechnet außer der Lage der Punkte auf dem Bildschirm.
 * Nachtlicht und Weltbank-Werte stehen NEBENEINANDER – kein Zusammenhang behauptet, keine Grafik mit zwei
 * y-Achsen: jede Größe hat ihre eigene kleine Grafik, alle mit derselben Zeitachse. Nur im Index-Modus
 * (2018 = 100) stehen Licht und BIP auf einer gemeinsamen Achse, weil beide dann dieselbe Einheit haben.
 * Fehlende Werte sind Lücken, nie 0. Monate und Jahre ab 2023 werden hier ein drittes Mal entfernt
 * (gesperrter Validierungs- und Endtestzeitraum; Export und Rechnung sperren schon).
 *
 * Schnittstelle für den Ländervergleich: window.ALEPH_ZR (Grafik-Bausteine, Bezüge, Namen).
 */
(function () {
  "use strict";

  var G = window.ALEPH_GLOBUS, Z = window.ALEPH_ZEITREIHEN;
  if (!G) return;
  var esc = G.esc;
  var GESPERRT_AB = "2023-01", GESPERRT_AB_JAHR = 2023;

  // ---------- dritte Sperre 2023–2025 ----------
  if (Z && Z.verfuegbar) {
    Z.monate = (Z.monate || []).filter(function (m) { return m < GESPERRT_AB; });
    Z.weltbank_jahre = (Z.weltbank_jahre || []).filter(function (j) { return Number(j) < GESPERRT_AB_JAHR; });
    Object.keys(Z.laender || {}).forEach(function (c) {
      var l = Z.laender[c];
      l.monate = l.monate.filter(function (p) { return p.monat < GESPERRT_AB; });
      Object.keys(l.gleitend).forEach(function (k) { l.gleitend[k] = l.gleitend[k].filter(function (p) { return p.monat < GESPERRT_AB; }); });
      Object.keys(l.saison).forEach(function (k) { l.saison[k].werte = l.saison[k].werte.filter(function (p) { return p.monat < GESPERRT_AB; }); });
      Object.keys(l.jahre).forEach(function (j) { if (Number(j) >= GESPERRT_AB_JAHR) delete l.jahre[j]; });
      Object.keys(l.index).forEach(function (k) {
        Object.keys(l.index[k]).forEach(function (j) { if (Number(j) >= GESPERRT_AB_JAHR) delete l.index[k][j]; });
      });
    });
  }

  // ---------- Bezugsgrößen: sinnvolle Paare ----------
  var BEZUG = {
    summe: { knopf: "Summe ↔ BIP", licht: "summe", jahr: "licht_summe", bip: "bip_real", bipName: "reales BIP",
      lichtName: "Lichtsumme", einheit: "nW·cm⁻²·sr⁻¹ × km²", bipEinheit: "US-Dollar, konstante Preise 2015" },
    pro_kopf: { knopf: "pro Kopf ↔ BIP pro Kopf", licht: "pro_kopf", jahr: "licht_pro_kopf", bip: "bip_pro_kopf", bipName: "BIP pro Kopf",
      lichtName: "Licht pro Kopf", einheit: "nW·cm⁻²·sr⁻¹ × km² je Einwohner", bipEinheit: "US-Dollar je Einwohner, konstante Preise 2015" },
    je_km2: { knopf: "pro km²", licht: "je_km2", jahr: "licht_je_km2", bip: null, bipName: null,
      lichtName: "Licht pro km²", einheit: "nW·cm⁻²·sr⁻¹",
      hinweis: "Eigene Kennzahl ohne BIP-Gegenstück: Licht pro km² zeigt eher Siedlungsdichte als Wirtschaftskraft." }
  };
  var FARBE_LICHT = "#8fb4e8", FARBE_BIP = "#e9e4d6";

  // ---------- Zahlen ----------
  function de(x, n) { return Number(x).toLocaleString("de-DE", { maximumFractionDigits: n == null ? 2 : n }); }
  function sig2(x) {
    if (x == null) return "–";
    if (x === 0) return "0";
    var a = Math.abs(x);
    if (a >= 1e12) return de(x / 1e12, a >= 1e13 ? 0 : 1) + " Bio.";
    if (a >= 1e9) return de(x / 1e9, a >= 1e10 ? 0 : 1) + " Mrd.";
    if (a >= 1e6) return de(x / 1e6, a >= 1e7 ? 0 : 1) + " Mio.";
    return de(Number(x.toPrecision(2)), 10);
  }
  function achseZahl(x) {
    var a = Math.abs(x);
    if (a >= 1e12) return de(x / 1e12, 1) + " Bio.";
    if (a >= 1e9) return de(x / 1e9, 1) + " Mrd.";
    if (a >= 1e6) return de(x / 1e6, 1) + " Mio.";
    if (a >= 1e3) return de(x, 0);
    return de(x, a >= 1 ? 1 : a >= 0.01 ? 3 : 5);
  }
  function schritte(y0, y1, n) {
    var roh = (y1 - y0) / (n || 4), p = Math.pow(10, Math.floor(Math.log10(roh || 1))), f = roh / p;
    var s = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p, t = [];
    for (var v = Math.ceil(y0 / s) * s; v <= y1 + s * 1e-9; v += s) t.push(Math.abs(v) < s * 1e-9 ? 0 : v);
    return t;
  }

  // ---------- Zeitachse (gemeinsam für alle Grafiken) ----------
  function mn(m) { return Number(m.slice(0, 4)) * 12 + Number(m.slice(5, 7)) - 1; }
  function jahrX(j) { return Number(j) * 12 + 5.5; }
  function zeitachse() {
    var jahre = (Z.weltbank_jahre || []).map(Number);
    var j0 = Math.min.apply(null, jahre.concat([Number(Z.monate[0].slice(0, 4))]));
    var j1 = Math.max.apply(null, jahre.concat([Number(Z.monate[Z.monate.length - 1].slice(0, 4))]));
    return { x0: j0 * 12, x1: (j1 + 1) * 12, jahre: (function () { var a = []; for (var j = j0; j <= j1; j++) a.push(j); return a; })() };
  }

  // ---------- Formen (zweite Kodierung neben der Farbe) ----------
  function form(art, cx, cy, r, attrs) {
    if (art === "quadrat") return '<rect x="' + (cx - r) + '" y="' + (cy - r) + '" width="' + 2 * r + '" height="' + 2 * r + '" ' + attrs + "/>";
    if (art === "dreieck") return '<path d="M' + cx + " " + (cy - r * 1.2) + "L" + (cx + r * 1.1) + " " + (cy + r * 0.8) + "L" + (cx - r * 1.1) + " " + (cy + r * 0.8) + 'Z" ' + attrs + "/>";
    if (art === "raute") return '<path d="M' + cx + " " + (cy - r * 1.25) + "L" + (cx + r * 1.25) + " " + cy + "L" + cx + " " + (cy + r * 1.25) + "L" + (cx - r * 1.25) + " " + cy + 'Z" ' + attrs + "/>";
    return '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" ' + attrs + "/>";
  }

  /*
   * Eine kleine Grafik. o = {achse, y0, y1, titel, einheit, nullLinie, hoehe, reihen: [{name, farbe, form, strich,
   * maxAbstand, beschriftung, punkte: [{x, y, art: "voll"|"hohl"|"blass", tip}]}]}
   * Linien verbinden nur aufeinanderfolgende VOLLE Punkte mit höchstens maxAbstand (Lücken bleiben Lücken).
   */
  var B = 760, RAND = { l: 70, r: 60, o: 8, u: 20 };
  function grafik(o) {
    var H = o.hoehe || 132, a = o.achse;
    function sx(x) { return RAND.l + (x - a.x0) / (a.x1 - a.x0) * (B - RAND.l - RAND.r); }
    function sy(y) { return H - RAND.u - (y - o.y0) / (o.y1 - o.y0) * (H - RAND.o - RAND.u); }
    var t = [];
    schritte(o.y0, o.y1, 3).forEach(function (v) {
      t.push('<line class="zr-gitter' + (v === 0 && o.nullLinie ? " zr-null" : "") + '" x1="' + RAND.l + '" x2="' + (B - RAND.r) + '" y1="' + sy(v) + '" y2="' + sy(v) + '"/>');
      t.push('<text class="ad-achse" x="' + (RAND.l - 6) + '" y="' + (sy(v) + 3.5) + '" text-anchor="end">' + esc(achseZahl(v)) + "</text>");
    });
    if (o.bezugsLinie != null) {
      t.push('<line class="zr-null" x1="' + RAND.l + '" x2="' + (B - RAND.r) + '" y1="' + sy(o.bezugsLinie) + '" y2="' + sy(o.bezugsLinie) + '"/>');
    }
    a.jahre.forEach(function (j) {
      var x = sx(j * 12);
      t.push('<line class="zr-jahr" x1="' + x + '" x2="' + x + '" y1="' + RAND.o + '" y2="' + (H - RAND.u) + '"/>');
      t.push('<text class="ad-achse" x="' + sx(j * 12 + 6) + '" y="' + (H - 6) + '" text-anchor="middle">' + j + "</text>");
    });
    t.push('<line class="zr-jahr" x1="' + sx(a.x1) + '" x2="' + sx(a.x1) + '" y1="' + RAND.o + '" y2="' + (H - RAND.u) + '"/>');
    o.reihen.forEach(function (r) {
      var pk = r.punkte.slice().sort(function (p, q) { return p.x - q.x; });
      for (var i = 1; i < pk.length; i++) {
        var p = pk[i - 1], q = pk[i];
        if (p.art === "voll" && q.art === "voll" && q.x - p.x <= (r.maxAbstand || 1) + 1e-9) {
          t.push('<line class="zr-linie" stroke="' + r.farbe + '"' + (r.strich ? ' stroke-dasharray="' + r.strich + '"' : "") +
            ' x1="' + sx(p.x) + '" y1="' + sy(p.y) + '" x2="' + sx(q.x) + '" y2="' + sy(q.y) + '"/>');
        }
      }
      pk.forEach(function (p) {
        var cx = sx(p.x), cy = sy(p.y), rr = r.klein ? 2.6 : 3.4;
        var stil = p.art === "voll" ? 'fill="' + r.farbe + '" stroke="var(--bg-panel)" stroke-width="1"'
          : p.art === "hohl" ? 'fill="var(--bg-panel)" stroke="' + r.farbe + '" stroke-width="1.6"'
          : 'fill="var(--bg-panel)" stroke="' + r.farbe + '" stroke-width="1.3" stroke-opacity="0.5" stroke-dasharray="2 1.5"';
        t.push('<g class="zr-punkt"><title>' + esc(p.tip) + "</title>" + form(r.form, cx, cy, 8, 'class="ad-treffer"') + form(r.form, cx, cy, rr, stil) + "</g>");
      });
      if (r.beschriftung && pk.length) {
        var l = pk[pk.length - 1];
        t.push('<text class="zr-direkt" x="' + (sx(l.x) + 7) + '" y="' + (sy(l.y) + 3.5) + '">' + esc(r.beschriftung) + "</text>");
      }
    });
    return '<div class="zr-grafik"><div class="zr-gkopf"><span class="zr-gtitel">' + o.titel + '</span><span class="zr-geinheit">' + esc(o.einheit || "") + "</span></div>" +
      '<svg class="ad-svg" viewBox="0 0 ' + B + " " + H + '" role="img" aria-label="' + esc(o.titelText || o.titel) + '">' + t.join("") + "</svg></div>";
  }
  function leereGrafik(titel, text) {
    return '<div class="zr-grafik"><div class="zr-gkopf"><span class="zr-gtitel">' + titel + '</span></div><div class="zr-leer">' + text + "</div></div>";
  }

  // ---------- Werte aus der Datei holen ----------
  var STATUS_ART = { gueltig: "voll", schnee: "hohl", gering: "blass" };
  function statusText(p) {
    if (p.status === "gueltig") return "Landessumme (" + p.abdeckung + " % der Fläche gemessen)";
    if (p.status === "schnee") return "Schnee-Verdacht auf " + p.schnee + " % der Fläche – Wert kann durch Schnee erhöht sein";
    if (p.status === "gering") return "nur " + p.abdeckung + " % der Fläche gemessen – Teilsumme, Untergrenze, keine Landessumme";
    if (p.status === "nicht_geladen") return p.nicht_geladen + " % der Fläche noch nicht geladen – kein Wert";
    return "keine Messung – kein Wert";
  }
  function monatsPunkte(l, bz, name) {
    return l.monate.filter(function (p) { return STATUS_ART[p.status] && p[bz.licht] != null; }).map(function (p) {
      return { x: mn(p.monat) + 0.5, y: p[bz.licht], art: STATUS_ART[p.status], monat: p.monat,
        tip: (name ? name + " · " : "") + p.monat + ": " + sig2(p[bz.licht]) + " · " + statusText(p) };
    });
  }
  function gleitPunkte(l, bz, name) {
    return (l.gleitend[bz.licht] || []).map(function (p) {
      return { x: mn(p.monat) + 0.5, y: p.wert, art: "voll", tip: (name ? name + " · " : "") + "12 Monate bis " + p.monat + ": " + sig2(p.wert) };
    });
  }
  function saisonPunkte(l, bz) {
    return (l.saison[bz.licht].werte || []).map(function (p) {
      return { x: mn(p.monat) + 0.5, y: p.wert, art: "voll", tip: p.monat + ": " + (p.wert > 0 ? "+" : "") + sig2(p.wert) + " gegenüber dem Median desselben Kalendermonats" };
    });
  }
  function jahrPunkte(l, feld, name, bezeichnung) {
    return Object.keys(l.jahre).filter(function (j) { return l.jahre[j][feld] != null; }).map(function (j) {
      var e = l.jahre[j];
      return { x: jahrX(j), y: e[feld], art: "voll",
        tip: (name ? name + " · " : "") + bezeichnung + " " + j + ": " + sig2(e[feld]) + (e[feld + "_vorlaeufig"] ? " (vorläufig)" : "") };
    });
  }
  function indexPunkte(l, feld, name, bezeichnung) {
    var idx = l.index[feld] || {};
    return Object.keys(idx).map(function (j) {
      return { x: jahrX(j), y: idx[j], art: "voll", tip: (name ? name + " · " : "") + bezeichnung + " " + j + ": " + idx[j] + " (2018 = 100)" };
    });
  }
  function bereich(punkteListen, nullBasis) {
    var ys = [];
    punkteListen.forEach(function (pl) { pl.forEach(function (p) { ys.push(p.y); }); });
    if (!ys.length) return null;
    var mx = Math.max.apply(null, ys), mi = Math.min.apply(null, ys);
    if (nullBasis) return { y0: 0, y1: mx > 0 ? mx * 1.08 : 1 };
    return { y0: mi, y1: mx };
  }
  function indexBereich(punkteListen) {
    var b = bereich(punkteListen, false) || { y0: 100, y1: 100 };
    return { y0: Math.floor((Math.min(b.y0, 100) - 3) / 5) * 5, y1: Math.ceil((Math.max(b.y1, 100) + 3) / 5) * 5 };
  }

  // ---------- Namen ----------
  var namenCache = {};
  function landEinheit(code) {
    var beste = null, idx = G.einheiten();
    Object.keys(idx).forEach(function (id) {
      var p = idx[id].properties;
      if (p.weltbank_code !== code || String(p.ebene).indexOf("Land") !== 0) return;
      if (!beste || (p.flaeche_km2 || 0) > (idx[beste].properties.flaeche_km2 || 0)) beste = id;
    });
    return beste;
  }
  function landName(code) {
    if (namenCache[code]) return namenCache[code];
    var id = landEinheit(code), p = id ? G.einheit(id) : null;
    namenCache[code] = p ? p.name : ((Z.laender[code] || {}).name || code);
    return namenCache[code];
  }

  // ---------- Kennzeichen, Hinweis, Datenstand ----------
  function kennzeichen(l) {
    var k = l.kennzeichen, b = [];
    if (k.gebiet_weltbank === "abweichend") b.push('<span class="lw-marke lw-marke--rot">Gebiet der Weltbank-Zahl weicht ab</span>');
    else if (k.gebiet_weltbank === "unklar") b.push('<span class="lw-marke">Gebiet der Weltbank-Zahl unklar</span>');
    if (k.monate_nicht_geladen) b.push('<span class="lw-marke lw-marke--rot">in ' + k.monate_nicht_geladen + " Monaten noch nicht geladen</span>");
    if (k.monate_gering) b.push('<span class="lw-marke lw-marke--rot">geringe Abdeckung in ' + k.monate_gering + " Monaten</span>");
    var ungueltig = Object.keys(l.jahre).filter(function (j) { var e = l.jahre[j]; return e.licht_berechnet && !e.licht_gueltig; });
    if (ungueltig.length) b.push('<span class="lw-marke lw-marke--rot">kein gültiger Jahreswert ' + ungueltig.join(", ") + "</span>");
    if (k.monate_schnee) b.push('<span class="lw-marke">Schnee-Verdacht in ' + k.monate_schnee + " Monaten</span>");
    if (k.nord65_prozent) b.push('<span class="lw-marke">' + k.nord65_prozent + " % des Lichts nördlich von 65° N (2018)</span>");
    if (k.reinheit_unter_50) b.push('<span class="lw-marke">Licht überwiegend aus Grenzzellen (Reinheit unter 50 %)</span>');
    if (!k.pro_kopf_erlaubt) b.push('<span class="lw-marke">kein Pro-Kopf-Wert: Bevölkerungszahl passt nicht zum Gebiet</span>');
    if (k.tansania) b.push('<span class="lw-marke">Tansania: BIP nur Festland</span>');
    return b.length ? '<div class="lw-marken">' + b.join("") + "</div>" : '<div class="zr-klein">Keine Kennzeichen.</div>';
  }
  function rahmen() {
    return '<div class="lw-warnung zr-warnung">Nebeneinander gestellt, kein Zusammenhang behauptet.</div>' +
      '<div class="ad-rahmen"><div><b>Evidenzstufe: beobachtet</b> – gemessenes Nachtlicht und amtliche Weltbank-Zahlen, jede für sich.</div>' +
      "<div>Kein Modell, keine Ursache-Wirkungs-Aussage. Ein gemeinsamer Verlauf im Index heißt nicht, dass das eine das andere erklärt.</div></div>";
  }
  function datenstand() {
    return '<div class="zr-quelle">Quellen: ' + esc(Z.quelle_licht) + " · " + esc(Z.quelle_weltbank) + " (Abruf " + esc(String(Z.weltbank_abruf).slice(0, 10)) +
      ") · Sicht: " + esc(Z.sicht) + " · Nachtlicht-Monate " + esc(Z.monate[0]) + " bis " + esc(Z.monate[Z.monate.length - 1]) +
      " · Rechnung Stand " + esc(String(Z.erstellt_utc).replace("T", " ").replace("Z", " UTC")) + " · 2023–2025 gesperrt</div>";
  }
  function regeln() {
    var r = Z.regeln;
    return '<details class="ad-details"><summary>Wie gerechnet</summary><ul class="ad-liste">' +
      "<li><b>Punkte:</b> " + esc(r.status) + ".</li><li><b>12-Monats-Durchschnitt:</b> " + esc(r.gleitend) + ".</li>" +
      "<li><b>Saisonbereinigt:</b> " + esc(r.saison) + ".</li><li><b>Jahreswert:</b> " + esc(r.jahr) + ".</li>" +
      "<li><b>Pro Kopf:</b> " + esc(r.pro_kopf) + ".</li><li><b>Pro km²:</b> " + esc(r.je_km2) + ".</li>" +
      "<li><b>Index:</b> " + esc(r.index) + ".</li></ul></details>";
  }
  function punktLegende() {
    function sym(stil) { return '<svg width="12" height="12"><circle cx="6" cy="6" r="3.6" ' + stil + "/></svg>"; }
    return '<div class="ad-legende">' +
      "<span>" + sym('fill="' + FARBE_LICHT + '"') + " Landessumme</span>" +
      "<span>" + sym('fill="var(--bg-panel)" stroke="' + FARBE_LICHT + '" stroke-width="1.6"') + " Schnee-Verdacht (≥ 5 % der Fläche)</span>" +
      "<span>" + sym('fill="var(--bg-panel)" stroke="' + FARBE_LICHT + '" stroke-width="1.3" stroke-opacity="0.5" stroke-dasharray="2 1.5"') +
      " unter 90 % gemessen: nur Teilsumme</span><span>Lücke = kein Wert (nie 0)</span></div>";
  }

  // ---------- Einzelansicht ----------
  var zustand = { code: null, index: false, bezug: "summe" };

  var feld = document.createElement("section");
  feld.id = "zeitreihe";
  feld.className = "auswertung zr";
  feld.hidden = true;
  feld.setAttribute("aria-label", "Länderansicht mit Zeitreihen");
  document.body.appendChild(feld);

  function schalter() {
    var modus = '<div class="ad-schalter" role="group" aria-label="Darstellung">' +
      '<button class="ad-jahr zr-modus' + (!zustand.index ? " is-aktiv" : "") + '" data-index="0">absolut</button>' +
      '<button class="ad-jahr zr-modus' + (zustand.index ? " is-aktiv" : "") + '" data-index="1">Index (2018 = 100)</button></div>';
    var bez = '<div class="ad-schalter" role="group" aria-label="Bezugsgröße">' + Object.keys(BEZUG).map(function (k) {
      return '<button class="ad-jahr zr-bezug' + (zustand.bezug === k ? " is-aktiv" : "") + '" data-bezug="' + k + '">' + esc(BEZUG[k].knopf) + "</button>";
    }).join("") + "</div>";
    return '<div class="zr-schalter">' + modus + bez + "</div>";
  }

  function jahresTabelle(l, bz) {
    var jahre = Object.keys(l.jahre).sort();
    var kopf, zeilen;
    if (zustand.index) {
      kopf = "<tr><th>Jahr</th><th>" + esc(bz.lichtName) + " (Jahreswert), Index</th>" + (bz.bip ? "<th>" + esc(bz.bipName) + ", Index</th>" : "") + "</tr>";
      zeilen = jahre.map(function (j) {
        var li = (l.index[bz.jahr] || {})[j], bi = bz.bip ? (l.index[bz.bip] || {})[j] : null;
        return "<tr><th>" + j + "</th><td>" + (li != null ? li : '<span class="zr-fehlt">' + esc(l.jahre[j].licht_grund || "kein Index") + "</span>") + "</td>" +
          (bz.bip ? "<td>" + (bi != null ? bi : "–") + "</td>" : "") + "</tr>";
      }).join("");
    } else {
      kopf = "<tr><th>Jahr</th><th>" + esc(bz.lichtName) + " (Jahreswert)</th>" + (bz.bip ? "<th>" + esc(bz.bipName) + "</th>" : "") + "<th>Bevölkerung</th></tr>";
      zeilen = jahre.map(function (j) {
        var e = l.jahre[j], lw = e[bz.jahr];
        return "<tr><th>" + j + "</th><td>" + (lw != null ? sig2(lw) : '<span class="zr-fehlt">' + esc(e.licht_grund || (bz.licht === "pro_kopf" ? "kein Pro-Kopf-Wert" : "kein Wert")) + "</span>") + "</td>" +
          (bz.bip ? "<td>" + (e[bz.bip] != null ? sig2(e[bz.bip]) + (e[bz.bip + "_vorlaeufig"] ? " (vorl.)" : "") : e[bz.bip + "_nicht_verwenden"] ? "nicht verwendet" : "–") + "</td>" : "") +
          "<td>" + (e.bevoelkerung != null ? sig2(e.bevoelkerung) : "–") + "</td></tr>";
      }).join("");
    }
    return '<table class="ad-tabelle zr-tabelle"><thead>' + kopf + "</thead><tbody>" + zeilen + "</tbody></table>";
  }

  function monatsTabelle(l, bz) {
    var gl = {}, sa = {};
    (l.gleitend[bz.licht] || []).forEach(function (p) { gl[p.monat] = p.wert; });
    (l.saison[bz.licht].werte || []).forEach(function (p) { sa[p.monat] = p.wert; });
    var zeilen = l.monate.map(function (p) {
      var w = p[bz.licht];
      return "<tr><th>" + p.monat + "</th><td>" + (w != null ? sig2(w) : "–") + "</td><td class=\"zr-links\">" + esc(statusText(p)) + "</td><td>" +
        (gl[p.monat] != null ? sig2(gl[p.monat]) : "–") + "</td><td>" + (sa[p.monat] != null ? (sa[p.monat] > 0 ? "+" : "") + sig2(sa[p.monat]) : "–") + "</td></tr>";
    }).join("");
    return '<details class="ad-details"><summary>Monatswerte als Tabelle (' + l.monate.length + " Monate)</summary>" +
      '<table class="ad-tabelle zr-tabelle"><thead><tr><th>Monat</th><th>' + esc(bz.lichtName) + '</th><th class="zr-links">Datenlage</th><th>12-Monats-Ø</th><th>saisonbereinigt</th></tr></thead><tbody>' +
      zeilen + "</tbody></table></details>";
  }

  function grafikenAbsolut(l, bz, achse) {
    var mp = monatsPunkte(l, bz), gp = gleitPunkte(l, bz);
    var reihe = function (p, extra) { var r = { name: bz.lichtName, farbe: FARBE_LICHT, form: "kreis", maxAbstand: 1, punkte: p }; for (var k in extra) r[k] = extra[k]; return r; };
    var teile = [];
    if (!mp.length) {
      teile.push(leereGrafik("a) Nachtlicht monatlich – " + esc(bz.lichtName),
        bz.licht === "pro_kopf" && !l.kennzeichen.pro_kopf_erlaubt ? "Kein Pro-Kopf-Wert: Die Bevölkerungszahl der Weltbank passt nicht zum Gebiet." :
          "Kein Monatswert: " + esc(l.monate.length ? statusText(l.monate[l.monate.length - 1]) : "keine Daten")));
    } else {
      var b = bereich([mp], true);
      teile.push(grafik({ achse: achse, y0: b.y0, y1: b.y1, titel: "a) Nachtlicht monatlich – " + esc(bz.lichtName), einheit: bz.einheit, reihen: [reihe(mp)] }));
    }
    if (gp.length) {
      var b2 = bereich([gp], true);
      teile.push(grafik({ achse: achse, y0: b2.y0, y1: b2.y1, titel: "b) Gleitender 12-Monats-Durchschnitt (ohne Modell)", einheit: bz.einheit, reihen: [reihe(gp, { klein: true })] }));
    } else {
      teile.push(leereGrafik("b) Gleitender 12-Monats-Durchschnitt (ohne Modell)",
        "Kein Wert: Es gibt noch keine 12 aufeinanderfolgenden Monate mit voller Landessumme ohne Schnee-Verdacht. Lücken werden nicht aufgefüllt."));
    }
    var s = l.saison[bz.licht];
    if (s.bestimmbar && s.werte.length) {
      var sp = saisonPunkte(l, bz), m = Math.max.apply(null, sp.map(function (p) { return Math.abs(p.y); })) * 1.1 || 1;
      teile.push(grafik({ achse: achse, y0: -m, y1: m, nullLinie: true, titel: "c) Saisonbereinigt: Abweichung vom Median desselben Kalendermonats",
        einheit: bz.einheit, reihen: [reihe(sp, { klein: true })] }) +
        '<div class="zr-klein">Nur ' + Math.min.apply(null, Object.keys(s.anzahl_je_kalendermonat).map(function (k) { return s.anzahl_je_kalendermonat[k]; })) +
        " Werte je Kalendermonat: Das Jahreszeitenmuster ist nur grob geschätzt. Beim Median aus 3 Werten ist je Kalendermonat eine Abweichung genau 0 (Eigenschaft des Verfahrens).</div>");
    } else {
      teile.push(leereGrafik("c) Saisonbereinigt", esc(s.grund || "noch nicht bestimmbar")));
    }
    if (bz.bip) {
      var bp = jahrPunkte(l, bz.bip, null, bz.bipName);
      if (bp.length) {
        var b3 = bereich([bp], true);
        teile.push(grafik({ achse: achse, y0: b3.y0, y1: b3.y1, titel: "d) " + esc(bz.bipName) + " (Weltbank, jährlich)", einheit: bz.bipEinheit,
          reihen: [{ name: bz.bipName, farbe: FARBE_BIP, form: "quadrat", maxAbstand: 12, punkte: bp }] }));
      } else {
        teile.push(leereGrafik("d) " + esc(bz.bipName) + " (Weltbank, jährlich)", "Kein Weltbank-Wert für diese Jahre" +
          (bz.bip === "bip_pro_kopf" && !l.kennzeichen.pro_kopf_erlaubt ? " (Pro-Kopf-Wert laut Weltbank-Tabelle nicht verwenden)." : ".")));
      }
    } else {
      teile.push('<div class="zr-hinweis">' + esc(bz.hinweis) + "</div>");
    }
    return teile.join("");
  }

  function grafikIndex(l, bz, achse, name) {
    var lp = indexPunkte(l, bz.jahr, name, bz.lichtName + " (Jahreswert)");
    var bp = bz.bip ? indexPunkte(l, bz.bip, name, bz.bipName) : [];
    if (!lp.length && !bp.length) return leereGrafik("Index (2018 = 100)", "Kein Index: kein gültiger Wert für 2018.");
    var b = indexBereich([lp, bp]);
    var reihen = [{ name: "Licht", farbe: FARBE_LICHT, form: "kreis", maxAbstand: 12, punkte: lp, beschriftung: lp.length ? "Licht" : "" }];
    if (bz.bip) reihen.push({ name: "BIP", farbe: FARBE_BIP, form: "quadrat", strich: "5 3", maxAbstand: 12, punkte: bp, beschriftung: bz.bip === "bip_real" ? "BIP" : "BIP/Kopf" });
    var leg = '<div class="ad-legende"><span><svg width="18" height="12"><line x1="1" y1="6" x2="17" y2="6" stroke="' + FARBE_LICHT + '" stroke-width="2"/>' +
      form("kreis", 9, 6, 3.4, 'fill="' + FARBE_LICHT + '"') + "</svg> Licht (" + esc(bz.lichtName) + ", Jahreswert)</span>" +
      (bz.bip ? '<span><svg width="18" height="12"><line x1="1" y1="6" x2="17" y2="6" stroke="' + FARBE_BIP + '" stroke-width="2" stroke-dasharray="5 3"/>' +
        form("quadrat", 9, 6, 3.4, 'fill="' + FARBE_BIP + '"') + "</svg> " + esc(bz.bipName) + " (Weltbank)</span>" : "") +
      "<span>Linie bei 100 = Stand 2018</span></div>";
    return leg + grafik({ achse: achse, y0: b.y0, y1: b.y1, bezugsLinie: 100, hoehe: 190,
      titel: "Index (2018 = 100): " + esc(bz.lichtName) + " als Jahreswert" + (bz.bip ? " und " + esc(bz.bipName) : ""), einheit: "2018 = 100", reihen: reihen });
  }

  function zeichne() {
    if (!Z || !Z.verfuegbar) {
      feld.innerHTML = '<div class="ad-kopf"><h2>Länderansicht</h2><button class="icon-btn ad-zu" aria-label="Schließen">✕</button></div>' +
        '<div class="hinweis hinweis--stark">Nicht verfügbar: ' + esc(Z ? Z.grund : "Datei daten/laender_zeitreihen.js fehlt") + "</div>";
      return;
    }
    var l = Z.laender[zustand.code];
    if (!l) {
      feld.innerHTML = '<div class="ad-kopf"><h2>Länderansicht</h2><button class="icon-btn ad-zu" aria-label="Schließen">✕</button></div>' +
        '<div class="hinweis hinweis--stark">Für „' + esc(zustand.code) + "“ gibt es keine Zeitreihe (keine Weltbank-Sicht).</div>";
      return;
    }
    var bz = BEZUG[zustand.bezug], achse = zeitachse(), name = landName(zustand.code);
    var inhalt = zustand.index
      ? grafikIndex(l, bz, achse, null) + '<div class="zr-klein">Licht als Jahreswert nach den Regeln der Auswertung 2018 (nur volle Jahre mit gültigem Wert), ' +
        "BIP als Weltbank-Jahreswert. Monatswerte, 12-Monats-Durchschnitt und Saisonbereinigung gibt es nur im Modus „absolut“." + (bz.hinweis ? " " + esc(bz.hinweis) : "") + "</div>"
      : punktLegende() + grafikenAbsolut(l, bz, achse);
    feld.innerHTML =
      '<div class="ad-kopf"><h2>Länderansicht: ' + esc(name) + ' <span class="zr-code">' + esc(zustand.code) + "</span></h2>" +
      (window.ALEPH_VERGLEICH ? '<button class="corner-btn zr-zumvgl" data-code="' + esc(zustand.code) + '">Zum Vergleich</button>' : "") +
      '<button class="icon-btn ad-zu" aria-label="Schließen">✕</button></div>' +
      schalter() + rahmen() + kennzeichen(l) + inhalt +
      '<div class="zr-tkopf">Gezeigte Werte</div>' + jahresTabelle(l, bz) + (zustand.index ? "" : monatsTabelle(l, bz)) + regeln() + datenstand();
  }

  function oeffne(code, optionen) {
    if (code) zustand.code = code;
    var aw = document.getElementById("auswertung");
    if (aw && !aw.hidden) aw.hidden = true; // nie zwei große Felder übereinander
    if (optionen) {
      if (optionen.index != null) zustand.index = !!optionen.index;
      if (optionen.bezug && BEZUG[optionen.bezug]) zustand.bezug = optionen.bezug;
    }
    document.dispatchEvent(new CustomEvent("aleph-feld-auf", { detail: "zeitreihe" }));
    feld.hidden = false;
    zeichne();
    feld.scrollTop = 0;
  }
  function schliesse() { feld.hidden = true; }

  feld.addEventListener("click", function (e) {
    if (e.target.closest(".ad-zu")) { schliesse(); return; }
    var m = e.target.closest(".zr-modus");
    if (m) { zustand.index = m.getAttribute("data-index") === "1"; zeichne(); return; }
    var b = e.target.closest(".zr-bezug");
    if (b) { zustand.bezug = b.getAttribute("data-bezug"); zeichne(); return; }
    var v = e.target.closest(".zr-zumvgl");
    if (v && window.ALEPH_VERGLEICH) { schliesse(); window.ALEPH_VERGLEICH.hinzu(v.getAttribute("data-code"), true); }
  });
  document.addEventListener("aleph-feld-auf", function (e) { if (e.detail !== "zeitreihe") schliesse(); });

  // ---------- Einstieg aus dem Länderfeld ----------
  G.dossierZusatz.push(function (p) {
    var code = p.weltbank_code;
    if (!code || !Z || !Z.verfuegbar || !Z.laender[code]) return "";
    return '<div class="zr-einstieg"><button class="zr-auf" data-code="' + esc(code) + '">Zeitreihen ansehen (' + esc(code) + ")</button>" +
      (window.ALEPH_VERGLEICH ? '<button class="zr-auf zr-auf--vgl" data-vgl="' + esc(code) + '">Zum Vergleich hinzufügen</button>' : "") +
      '<div class="lw-fuss">Nachtlicht monatlich und jährlich neben Weltbank-Werten, gleiche Zeitachse.</div></div>';
  });
  document.addEventListener("click", function (e) {
    var k = e.target.closest && e.target.closest(".zr-auf");
    if (!k) return;
    if (k.hasAttribute("data-vgl")) { if (window.ALEPH_VERGLEICH) window.ALEPH_VERGLEICH.hinzu(k.getAttribute("data-vgl"), true); return; }
    oeffne(k.getAttribute("data-code"));
  });

  // ---------- Adresse: #zeitreihe=DEU&index=1&bezug=pro_kopf ----------
  document.addEventListener("aleph-bereit", function (e) {
    var h = e.detail || {};
    if (h.zeitreihe) oeffne(h.zeitreihe, { index: h.index === "1", bezug: h.bezug });
  });

  window.ALEPH_ZEITREIHE = { oeffne: oeffne, schliesse: schliesse };
  window.ALEPH_ZR = {
    Z: Z, BEZUG: BEZUG, grafik: grafik, leereGrafik: leereGrafik, zeitachse: zeitachse, monatsPunkte: monatsPunkte,
    jahrPunkte: jahrPunkte, indexPunkte: indexPunkte, bereich: bereich, indexBereich: indexBereich, landName: landName,
    landEinheit: landEinheit, sig2: sig2, form: form, rahmen: rahmen, datenstand: datenstand, statusText: statusText
  };
})();
