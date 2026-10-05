/*
 * ALEPH – Niederschlag als zweite, umschaltbare Ebene (Auftrag 2026-10-05, Teil 3).
 *
 * Liest nur daten/niederschlag_stand.js und daten/niederschlag_<JJJJ-MM>.js (aleph/export/globus_niederschlag.py).
 * Quelle: NASA GPM IMERG Final Run V07B (monatlich), auf 0,25° flächengewichtet. Evidenzstufe „beobachtet“
 * (Satellitenschätzung, an Regenmesser angepasst; Zellenmittel, kein Stationswert).
 *
 * Regeln:
 * - Eigene Farbskala: EIN Farbton (Grün), hell = trocken, dunkel = nass. Sie teilt keine Farbe mit dem Nachtlicht
 *   (Blau-Violett-Orange-Gelb), den Datenlage-Mustern (grau, braun, blau gestreift) oder den Linien der
 *   Sondereinheiten (orange, rosa, hellblau).
 * - Fehlende Werte nie als 0 mm: „keine Daten“ (kein gültiger Quellpixel) und „zu wenig Messungen“ (unter 50 %
 *   gültige Fläche, Regel des Layers) haben dieselben gestreiften Muster wie beim Nachtlicht.
 * - Der Monat folgt der Zeitleiste. Nur eine Ebene ist zu sehen; der Vorjahresvergleich gilt nur für Nachtlicht.
 * - Monate ab 2023 werden nie geladen (dritte Sperre nach Export und Zeitleiste).
 */
(function () {
  "use strict";
  var G = window.ALEPH_GLOBUS, NS = window.ALEPH_NIEDERSCHLAG_STAND;
  if (!G) return;
  var esc = G.esc, byId = function (id) { return document.getElementById(id); };
  var GESPERRT_AB = "2023-01";
  var MERC_MAX = 85.0511287798066, BILD = 2048, SCHRAFFUR = 16;
  var KEINE_A = [138, 144, 153], KEINE_B = [112, 118, 128];
  var DUENN_A = [176, 160, 128], DUENN_B = [120, 110, 92];
  // Sequenziell, ein Farbton (Grün), logarithmisch in mm/Monat.
  var STUFEN = [
    [0, [247, 245, 224]], [10, [217, 239, 170]], [30, [166, 217, 140]], [75, [107, 190, 110]],
    [150, [49, 155, 84]], [300, [18, 118, 64]], [600, [0, 80, 48]], [1200, [0, 48, 32]]
  ];
  var SPEICHER_MONATE = 4;

  var aktiv = false, geladen = {}, benutzt = [], monatJetzt = null, laedt = {};
  var monate = NS && NS.verfuegbar ? (NS.monate || []).filter(function (m) { return m < GESPERRT_AB; }) : [];

  function t(v) { return Math.log10(v + 1); }
  function farbe(v) {
    if (v <= STUFEN[0][0]) return STUFEN[0][1];
    for (var i = 1; i < STUFEN.length; i++) {
      if (v <= STUFEN[i][0]) {
        var a = STUFEN[i - 1], b = STUFEN[i], f = (t(v) - t(a[0])) / (t(b[0]) - t(a[0]));
        return [0, 1, 2].map(function (k) { return Math.round(a[1][k] + f * (b[1][k] - a[1][k])); });
      }
    }
    return STUFEN[STUFEN.length - 1][1];
  }
  function mm(v) {
    if (v < 1) return "unter 1";
    var s = v >= 100 ? String(Math.round(v / 10) * 10) : String(Math.round(v));
    return s.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  }

  // ---------- Bedienung: Umschalter in der Zeitleiste, Legende ----------

  var umschalter = document.createElement("div");
  umschalter.className = "ebenen-wahl";
  umschalter.innerHTML = '<span class="tl-label">Ebene</span>' +
    '<button class="ad-jahr is-aktiv" data-ebene="nachtlicht">Nachtlicht</button>' +
    '<button class="ad-jahr" data-ebene="niederschlag"' + (monate.length ? "" : " disabled") + '>Niederschlag</button>' +
    (monate.length ? "" : '<span class="tl-klein">Niederschlag nicht verfügbar: ' + esc(NS ? NS.grund : "Datei daten/niederschlag_stand.js fehlt") + "</span>");
  var dock = byId("zeitleiste");
  dock.insertBefore(umschalter, dock.firstChild);

  var legende = document.createElement("div");
  legende.id = "legende-niederschlag";
  legende.hidden = true;
  byId("legende").insertBefore(legende, byId("einheiten-legende"));
  function baueLegende() {
    var teile = [], n = 40, max = STUFEN[STUFEN.length - 1][0];
    for (var i = 0; i <= n; i++) {
      var v = Math.pow(10, t(max) * i / n) - 1;
      teile.push("rgb(" + farbe(v).join(",") + ") " + (100 * i / n).toFixed(1) + "%");
    }
    // Beschriftung ohne 600 (stünde zu dicht an „≥ 1.200“).
    var achse = STUFEN.filter(function (s) { return s[0] !== 600; }).map(function (s, i, alle) {
      return '<span style="left:' + (100 * t(s[0]) / t(max)) + '%">' + (i === alle.length - 1 ? "≥ " : "") + s[0].toLocaleString("de-DE") + "</span>";
    }).join("");
    legende.innerHTML =
      '<div class="legende-kopf"><span class="legende-titel">Niederschlag, Monatssumme</span><span class="legende-einheit">mm/Monat</span></div>' +
      '<div class="verlauf" style="background:linear-gradient(to right,' + teile.join(",") + ')"></div>' +
      '<div class="verlauf-achse">' + achse + "</div>" +
      '<div class="legende-zeile"><span class="feld" style="background:rgb(' + STUFEN[0][1].join(",") + ')"></span><span><b>hell</b> = trocken (0 mm gemessen), <b>dunkelgrün</b> = nass</span></div>' +
      '<div class="legende-trenner">ohne gültige Messung – gestreift, nie „0 mm“</div>' +
      '<div class="legende-zeile"><span class="feld feld--keine"></span><span><b>keine Daten</b>: kein gültiger Satellitenwert (vor allem an den Polen)</span></div>' +
      '<div class="legende-zeile"><span class="feld feld--duenn"></span><span><b>zu wenig Messungen</b>: unter ' + esc(NS.min_gueltig_prozent) + " % der Zellfläche gültig</span></div>" +
      '<div class="ns-legende-hinweis">Evidenzstufe <b>beobachtet</b>: Satellitenschätzung, an Regenmesser angepasst. Zellenmittel über rund 28 × 28 km, kein Stationswert.</div>';
  }

  // ---------- Laden, Selbsttest, Bild ----------

  function ladeSkript(pfad) {
    return new Promise(function (ok, fehler) {
      var s = document.createElement("script");
      s.src = pfad;
      s.onload = function () { s.remove(); ok(); };
      s.onerror = function () { s.remove(); fehler(new Error("Datei nicht gefunden: " + pfad)); };
      document.head.appendChild(s);
    });
  }
  function bytes(b64) { var bin = atob(b64), u = new Uint8Array(bin.length); for (var i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u; }
  function hex(buf) { return Array.prototype.map.call(new Uint8Array(buf), function (b) { return ("0" + b.toString(16)).slice(-2); }).join(""); }

  function lade(monat) {
    if (monat >= GESPERRT_AB || monate.indexOf(monat) < 0) return Promise.reject(new Error("kein Niederschlag für " + monat));
    if (geladen[monat]) return Promise.resolve(geladen[monat]);
    if (laedt[monat]) return laedt[monat];
    var p = ladeSkript("daten/niederschlag_" + monat + ".js").then(function () {
      var e = window.ALEPH_NIEDERSCHLAG && window.ALEPH_NIEDERSCHLAG[monat];
      if (!e) throw new Error("Monat " + monat + " nicht in der Datei");
      delete window.ALEPH_NIEDERSCHLAG[monat];
      var strom = new Blob([bytes(e.daten_b64)]).stream().pipeThrough(new DecompressionStream("deflate"));
      return new Response(strom).arrayBuffer().then(function (buf) {
        var n = e.breite * e.laenge;
        if (buf.byteLength !== 5 * n) throw new Error("Niederschlag " + monat + ": falsche Datenlänge");
        var wert = new Uint16Array(buf.slice(0, 2 * n)), anteil = new Uint8Array(buf, 2 * n, n), fehler = new Uint16Array(buf.slice(3 * n));
        Object.keys(e.kontrolle).forEach(function (ort) {
          var k = e.kontrolle[ort], i = k.zeile * e.laenge + k.spalte;
          if (wert[i] !== k.wert_code || anteil[i] !== k.anteil) throw new Error("Selbsttest Niederschlag fehlgeschlagen (" + ort + ")");
        });
        var pruef = (window.crypto && crypto.subtle) ? crypto.subtle.digest("SHA-256", buf).then(function (h) {
          if (hex(h) !== e.sha256_roh) throw new Error("Prüfsumme Niederschlag " + monat + " stimmt nicht");
        }) : Promise.resolve();
        return pruef.then(function () {
          geladen[monat] = { meta: e, wert: wert, anteil: anteil, fehler: fehler, bild: baueBild(e, wert, anteil) };
          benutzt = benutzt.filter(function (m) { return m !== monat; }).concat([monat]);
          while (benutzt.length > SPEICHER_MONATE) { var alt = benutzt.shift(); if (alt !== monatJetzt) delete geladen[alt]; }
          return geladen[monat];
        });
      });
    });
    laedt[monat] = p;
    p.then(function () { delete laedt[monat]; }, function () { delete laedt[monat]; });
    return p;
  }

  function baueBild(e, wert, anteil) {
    var lut = new Uint8Array(65536 * 3);
    for (var c = 0; c < 65536; c++) { var f = farbe(c / e.wert_skala); lut[3 * c] = f[0]; lut[3 * c + 1] = f[1]; lut[3 * c + 2] = f[2]; }
    var spalteVon = new Int32Array(BILD);
    for (var x = 0; x < BILD; x++) spalteVon[x] = Math.min(e.laenge - 1, Math.floor(((x + 0.5) * 360 / BILD) / 0.25));
    var lw = document.createElement("canvas");
    lw.width = BILD; lw.height = BILD;
    var ctx = lw.getContext("2d"), bild = ctx.createImageData(BILD, BILD), px = bild.data, grenze = e.min_gueltig_prozent;
    for (var y = 0; y < BILD; y++) {
      var lat = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 0.5) / BILD))) * 180 / Math.PI;
      var basis = Math.min(e.breite - 1, Math.max(0, Math.floor((90 - lat) / 0.25))) * e.laenge;
      for (var x2 = 0; x2 < BILD; x2++) {
        var i = basis + spalteVon[x2], o = 4 * (y * BILD + x2), a = anteil[i], c3;
        if (a === e.anteil_keine_daten) c3 = ((x2 + y) % SCHRAFFUR) < SCHRAFFUR / 2 ? KEINE_A : KEINE_B;
        else if (a < grenze) c3 = ((x2 - y + 4 * BILD) % SCHRAFFUR) < SCHRAFFUR / 3 ? DUENN_A : DUENN_B;
        else { var w = wert[i]; c3 = [lut[3 * w], lut[3 * w + 1], lut[3 * w + 2]]; }
        px[o] = c3[0]; px[o + 1] = c3[1]; px[o + 2] = c3[2]; px[o + 3] = 255;
      }
    }
    ctx.putImageData(bild, 0, 0);
    return lw.toDataURL("image/png");
  }

  // ---------- Anzeige ----------

  var map = G.map, ECKEN = [[-180, MERC_MAX], [180, MERC_MAX], [180, -MERC_MAX], [-180, -MERC_MAX]];
  var hinweis = document.createElement("div");
  hinweis.className = "dock-hinweis";
  hinweis.hidden = true;
  dock.insertBefore(hinweis, umschalter.nextSibling);

  function zeigeHinweis(html, stark) {
    hinweis.className = "dock-hinweis" + (stark ? " dock-hinweis--stark" : "");
    hinweis.innerHTML = html;
    hinweis.hidden = !html;
  }

  function zeigeMonat(monat) {
    monatJetzt = monat;
    if (!aktiv) return Promise.resolve();
    if (monate.indexOf(monat) < 0) {
      if (map.getLayer("niederschlag")) map.setLayoutProperty("niederschlag", "visibility", "none");
      zeigeHinweis("<b>Niederschlag " + esc(monat) + ":</b> kein Monat im IMERG-Würfel vor 2023 – hier wird kein Niederschlag gezeigt.", true);
      G.aktualisiereDossier();
      return Promise.resolve();
    }
    return lade(monat).then(function (d) {
      if (monatJetzt !== monat || !aktiv) return;
      var q = map.getSource("niederschlag");
      if (q) q.updateImage({ url: d.bild, coordinates: ECKEN });
      else {
        map.addSource("niederschlag", { type: "image", url: d.bild, coordinates: ECKEN });
        map.addLayer({ id: "niederschlag", type: "raster", source: "niederschlag", paint: { "raster-fade-duration": 0 } },
          map.getLayer("einheiten-fuellung") ? "einheiten-fuellung" : undefined);
      }
      map.setLayoutProperty("niederschlag", "visibility", "visible");
      zeigeHinweis(d.meta.kalibrierung_trmm
        ? "<b>" + esc(monat) + " ist noch TRMM-kalibriert</b> (bis 2014-05, danach GPM): Vergleiche über Mitte 2014 hinweg können einen Bruch der Messreihe enthalten."
        : "", false);
      G.aktualisiereDossier();
    }).catch(function (err) {
      zeigeHinweis("<b>Niederschlag " + esc(monat) + " wird nicht angezeigt:</b> " + esc(err.message), true);
    });
  }

  function quelleZeile() {
    if (!aktiv) return;
    // Der Zustand unter dem Monat beschreibt sonst den Ladestand des Nachtlichts; hier eindeutig benennen.
    var mz = byId("monat-zustand"), m = G.aktiverMonat();
    if (mz && m) {
      var nl = ((G.zeitleiste ? G.zeitleiste() : []).filter(function (e) { return e.monat === m; })[0] || {}).zustand_text;
      mz.innerHTML = "Niederschlag: " + (monate.indexOf(m) >= 0 ? "weltweit" : "fehlt") + (nl ? "<br>Nachtlicht: " + esc(nl) : "");
    }
    byId("quelle-zeile").innerHTML = "Quelle: <b>NASA GPM IMERG Final Run " + esc(NS.version) + "</b> (GES DISC, DOI 10.5067/GPM/IMERG/3B-MONTH/07) · " +
      "Evidenzstufe <b>beobachtet</b> (Satellitenschätzung, an Regenmesser angepasst) · Einheit mm/Monat · 2023–2025 gesperrt" +
      '<br><span class="tl-klein">' + esc(NS.quellenangabe) + "</span>";
  }

  function setzeEbene(ebene) {
    var an = ebene === "niederschlag" && monate.length > 0;
    if (an === aktiv) return;
    aktiv = an;
    Array.prototype.forEach.call(umschalter.querySelectorAll("button"), function (b) {
      b.classList.toggle("is-aktiv", b.getAttribute("data-ebene") === (an ? "niederschlag" : "nachtlicht"));
    });
    if (an && G.vergleich) G.vergleich(false);
    G.nachtlichtSichtbar(!an);
    byId("legende-normal").hidden = an;
    legende.hidden = !an;
    document.body.classList.toggle("ebene-niederschlag", an);
    var badge = document.querySelector(".brand-badge");
    if (badge) badge.textContent = (an ? "Niederschlag" : "Nachtlicht") + " · Evidenzstufe: beobachtet";
    if (an) {
      byId("nachtlicht-hinweis").hidden = true;
      quelleZeile();
      zeigeMonat(G.aktiverMonat());
    } else {
      if (map.getLayer("niederschlag")) map.setLayoutProperty("niederschlag", "visibility", "none");
      zeigeHinweis("", false);
      if (G.aktiverMonat()) G.setzeMonat(G.aktiverMonat()); // stellt Nachtlicht-Hinweis und Quellenzeile wieder her
    }
  }
  G.setzeEbene = setzeEbene;

  umschalter.addEventListener("click", function (e) {
    var b = e.target.closest("button[data-ebene]");
    if (b && !b.disabled) setzeEbene(b.getAttribute("data-ebene"));
  });

  G.beiMonat.push(function (monat) {
    monatJetzt = monat;
    if (!aktiv) return;
    byId("nachtlicht-hinweis").hidden = true;
    byId("legende-normal").hidden = true;
    quelleZeile();
    zeigeMonat(monat);
  });

  function werteAn(lon, lat) {
    var d = aktiv && geladen[monatJetzt];
    if (!d) return null;
    var zeile = Math.min(719, Math.max(0, Math.floor((90 - lat) / 0.25)));
    var l = ((lon + 180) % 360 + 360) % 360 - 180, spalte = Math.min(1439, Math.max(0, Math.floor((l + 180) / 0.25)));
    var i = zeile * d.meta.laenge + spalte, a = d.anteil[i];
    var r = { anteil: a, nord: 90 - 0.25 * zeile, west: -180 + 0.25 * spalte, meta: d.meta };
    if (a === d.meta.anteil_keine_daten) r.klasse = "keine Daten";
    else if (a < d.meta.min_gueltig_prozent) r.klasse = "zu wenig Messungen";
    else { r.klasse = "Wert"; r.wert = d.wert[i] / d.meta.wert_skala; r.fehler = d.fehler[i]; }
    return r;
  }

  G.zeigerZusatz.push(function (lon, lat) {
    var r = werteAn(lon, lat);
    if (!r) return "";
    return "Niederschlag " + monatJetzt + ": " + (r.klasse === "Wert" ? mm(r.wert) + " mm (± " + mm(r.fehler) + ")" : r.klasse);
  });

  G.messungZusatz.push(function (punkt) {
    if (!aktiv) return "";
    if (!punkt) return '<div class="inv-messung"><div class="inv-messung-kopf"><span>Niederschlag ' + esc(monatJetzt || "") +
      '</span><span class="inv-evidenz">beobachtet</span></div><div class="inv-messung-note">Für den Niederschlag auf eine Stelle klicken.</div></div>';
    var r = werteAn(punkt[0], punkt[1]);
    if (!r) return '<div class="inv-messung"><div class="inv-messung-kopf"><span>Niederschlag ' + esc(monatJetzt || "") +
      '</span></div><div class="inv-messung-note">Für diesen Monat ist kein Niederschlag geladen.</div></div>';
    var inhalt;
    if (r.klasse === "Wert") {
      inhalt = '<div class="inv-messung-wert">' + mm(r.wert) + ' <span class="einheit">mm/Monat</span></div>' +
        '<div class="inv-messung-note">Zufälliger Fehler laut Anbieter: ± ' + mm(r.fehler) + " mm (als Zellenmittel eine Obergrenze) · " + r.anteil + " % der Zellfläche gültig</div>";
    } else {
      inhalt = '<div class="inv-messung-klasse"><span class="feld ' + (r.klasse === "keine Daten" ? "feld--keine" : "feld--duenn") + '"></span>' + esc(r.klasse) + "</div>" +
        '<div class="inv-messung-note">' + (r.klasse === "keine Daten" ? "Kein gültiger Satellitenwert in dieser Zelle." : "Nur " + r.anteil + " % der Zellfläche gültig (Grenze " + r.meta.min_gueltig_prozent + " %).") +
        " Das ist keine Messung von 0 mm.</div>";
    }
    var kennz = [];
    if (Math.abs(punkt[1]) > NS.verminderte_guete_ab_breite) kennz.push("Jenseits von " + NS.verminderte_guete_ab_breite + "° verminderte Güte (gefrorene Flächen, kein Infrarot).");
    if (r.meta.kalibrierung_trmm) kennz.push("Monat noch TRMM-kalibriert (bis 2014-05).");
    kennz.push("Zellenmittel über rund 28 × 28 km, kein Stationswert; einzelne Orte können um 25–40 % von Stationen abweichen (IMERG-Prüfung 2018).");
    var ort = r.nord.toFixed(2).replace(".", ",") + "° bis " + (r.nord - 0.25).toFixed(2).replace(".", ",") + "° Breite, " +
      r.west.toFixed(2).replace(".", ",") + "° bis " + (r.west + 0.25).toFixed(2).replace(".", ",") + "° Länge";
    return '<div class="inv-messung"><div class="inv-messung-kopf"><span>Niederschlag ' + esc(monatJetzt) + " · GPM IMERG</span>" +
      '<span class="inv-evidenz">beobachtet</span></div>' + inhalt +
      kennz.map(function (k) { return '<div class="inv-messung-note">' + esc(k) + "</div>"; }).join("") +
      '<div class="inv-messung-note">Zelle ' + ort + "</div></div>";
  });

  if (monate.length) baueLegende();
  document.addEventListener("aleph-bereit", function (e) {
    if ((e.detail || {}).ebene === "niederschlag") setzeEbene("niederschlag");
  });
  // Für Prüfungen von außen (Fotos): auf das fertige Bild warten können.
  G.niederschlagBereit = function () { return !!(aktiv && geladen[monatJetzt]); };
})();
