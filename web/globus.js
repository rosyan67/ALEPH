/*
 * ALEPH – Globus mit echten Daten (Nachtlicht und Einheiten)
 *
 * Liest nur die Dateien in web/daten/, die aleph/export/globus.py erzeugt:
 *   datenstand.js   welche Monate fertig sind und angezeigt werden dürfen
 *   einheiten.js    Länder und Sondereinheiten (UN-Sicht) oder "nicht verfügbar"
 *   nachtlicht_<JJJJ-MM>.js   ein Monat, gepackt (zlib + Base64)
 *
 * Wichtigste Regel: Fehlende Daten sind nie dunkel. Zellen ohne gültigen
 * Pixel ("keine Daten") und Zellen mit zu wenig beobachteten Pixeln
 * ("Datenlage unzureichend") bekommen je ein eigenes, grau schraffiertes
 * Muster; nur gemessene Werte bekommen eine Farbe aus der Skala.
 *
 * Zur Lage auf dem Globus: MapLibre legt ein Bild linear in Web-Mercator-
 * Koordinaten auf die Kugel. Das Würfel-Raster ist aber gleichabständig in
 * Grad. Deshalb wird es hier Zeile für Zeile in Mercator-Zeilen umgerechnet
 * (nächste Zelle), bevor es als Bild auf den Globus kommt. Mercator reicht
 * nur bis 85,05° N/S; die Polkappen darüber zeigt die Karte ohne Nachtlicht.
 *
 * Prüf-Parameter in der Adresse (für Bildschirmfotos, optional):
 *   #monat=2018-03&blick=13.4,52.5,4&einheit=krim&punkt=34.1,44.95
 */
(function () {
  "use strict";

  var DS = window.ALEPH_DATENSTAND;
  var EH = window.ALEPH_EINHEITEN;
  var MERC_MAX = 85.0511287798066;
  var BILD = 2048; // Kantenlänge des Mercator-Bildes in Pixeln
  var SCHRAFFUR = 16; // Streifenabstand im Bild (Pixel)

  var FARBE_KATEGORIE = {
    "umstritten": "#e69f00",
    "besetzt/Konfliktzone": "#cc79a7",
    "Sonderstatus/autonom": "#56b4e9"
  };
  // Farbskala (logarithmisch) für gemessene Werte in nW·cm⁻²·sr⁻¹.
  var STUFEN = [
    [0, [11, 26, 46]],
    [0.5, [31, 45, 92]],
    [2, [75, 58, 140]],
    [8, [156, 63, 134]],
    [25, [219, 95, 85]],
    [80, [245, 165, 74]],
    [250, [253, 232, 160]]
  ];
  var KEINE_A = [138, 144, 153], KEINE_B = [112, 118, 128];
  var DUENN_A = [176, 160, 128], DUENN_B = [120, 110, 92];

  function byId(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function zeigeFehler(text) {
    var el = byId("fehler");
    el.textContent = text;
    el.hidden = false;
  }
  window.addEventListener("error", function (e) { zeigeFehler("Fehler in der Seite: " + e.message); });

  if (!DS) {
    zeigeFehler("Die Datei daten/datenstand.js fehlt. Bitte zuerst „Globus aktualisieren.command“ ausführen.");
    return;
  }
  if (DS.pruefansicht) byId("pruef-banner").hidden = false;

  // ---------- Zahlen und Farben ----------

  function zahl(v) {
    if (v < 0.1) return "unter 0,1";
    var s = v >= 100 ? String(Math.round(v / 10) * 10) : Number(v.toPrecision(2)).toString();
    return s.replace(".", ",");
  }
  function t(v) { return Math.log10(v + 0.1); }
  function farbeFuer(v) {
    if (v <= STUFEN[0][0]) return STUFEN[0][1];
    for (var i = 1; i < STUFEN.length; i++) {
      if (v <= STUFEN[i][0]) {
        var a = STUFEN[i - 1], b = STUFEN[i];
        var f = (t(v) - t(a[0])) / (t(b[0]) - t(a[0]));
        return [0, 1, 2].map(function (k) { return Math.round(a[1][k] + f * (b[1][k] - a[1][k])); });
      }
    }
    return STUFEN[STUFEN.length - 1][1];
  }

  function baueLegende() {
    var teile = [];
    var n = 40, max = STUFEN[STUFEN.length - 1][0];
    for (var i = 0; i <= n; i++) {
      var tt = t(0) + (t(max) - t(0)) * i / n;
      var v = Math.pow(10, tt) - 0.1;
      var c = farbeFuer(v);
      teile.push("rgb(" + c.join(",") + ") " + (100 * i / n).toFixed(1) + "%");
    }
    byId("verlauf").style.background = "linear-gradient(to right," + teile.join(",") + ")";
    var achse = byId("verlauf-achse");
    STUFEN.forEach(function (s, i) {
      var pos = 100 * (t(s[0]) - t(0)) / (t(max) - t(0));
      var span = document.createElement("span");
      span.style.left = pos + "%";
      span.textContent = (i === STUFEN.length - 1 ? "≥ " : "") + String(s[0]).replace(".", ",");
      achse.appendChild(span);
    });
    byId("einheit").textContent = DS.einheit;
    byId("min-proz").textContent = DS.min_beobachtet_prozent;
  }

  // ---------- Nachtlicht-Monat laden, entpacken, prüfen ----------

  var geladen = {}; // monat -> {wert: Uint16Array, anteil: Uint8Array, meta, bildUrl}
  var ZEITEN = window.ALEPH_ZEITEN = []; // Messpunkte (ms) für die Prüfung der Geschwindigkeit
  function zeit(name) { ZEITEN.push(name + " " + Math.round(performance.now())); }

  function ladeSkript(pfad) {
    return new Promise(function (ok, fehler) {
      var s = document.createElement("script");
      s.src = pfad;
      s.onload = ok;
      s.onerror = function () { fehler(new Error("Datei nicht gefunden: " + pfad)); };
      document.head.appendChild(s);
    });
  }

  function base64ZuBytes(b64) {
    var bin = atob(b64);
    var u8 = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    return u8;
  }

  function entpacke(b64) {
    var strom = new Blob([base64ZuBytes(b64)]).stream().pipeThrough(new DecompressionStream("deflate"));
    return new Response(strom).arrayBuffer();
  }

  function hex(buf) {
    return Array.prototype.map.call(new Uint8Array(buf), function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
  }

  function ladeMonat(monat) {
    if (geladen[monat]) return Promise.resolve(geladen[monat]);
    zeit("start " + monat);
    return ladeSkript("daten/nachtlicht_" + monat + ".js").then(function () {
      var e = window.ALEPH_NACHTLICHT && window.ALEPH_NACHTLICHT[monat];
      if (!e) throw new Error("Monat " + monat + " nicht in der Datei");
      zeit("skript geladen");
      return entpacke(e.daten_b64).then(function (buf) {
        zeit("entpackt");
        var n = e.breite * e.laenge;
        if (buf.byteLength !== 3 * n) throw new Error("Monat " + monat + ": falsche Datenlänge");
        var wert = new Uint16Array(buf.slice(0, 2 * n)); // Intel-Mac: little endian wie die Datei
        var anteil = new Uint8Array(buf, 2 * n, n);
        // Selbsttest 1: Kontrollzellen müssen exakt stimmen.
        Object.keys(e.kontrolle).forEach(function (name) {
          var k = e.kontrolle[name], i = k.zeile * e.laenge + k.spalte;
          if (wert[i] !== k.wert_code || anteil[i] !== k.anteil) {
            throw new Error("Selbsttest fehlgeschlagen (" + name + "): Daten falsch entpackt");
          }
        });
        // Selbsttest 2: Prüfsumme über alle Bytes, wenn der Browser sie rechnen kann.
        var pruef = (window.crypto && crypto.subtle)
          ? crypto.subtle.digest("SHA-256", buf).then(function (h) {
              if (hex(h) !== e.sha256_roh) throw new Error("Prüfsumme des Monats " + monat + " stimmt nicht");
              return "Prüfsumme stimmt";
            })
          : Promise.resolve("Prüfsumme im Browser nicht prüfbar, nur Kontrollzellen");
        return pruef.then(function (pruefText) {
          zeit("geprüft");
          geladen[monat] = { wert: wert, anteil: anteil, meta: e, pruefText: pruefText, bildUrl: baueBild(e, wert, anteil) };
          return geladen[monat];
        });
      });
    });
  }

  function baueBild(e, wert, anteil) {
    zeit("bild start");
    var lut = new Uint8Array(65536 * 3);
    for (var code = 0; code < 65536; code++) {
      var c = farbeFuer(code / e.wert_skala);
      lut[3 * code] = c[0]; lut[3 * code + 1] = c[1]; lut[3 * code + 2] = c[2];
    }
    var spalteVon = new Int32Array(BILD);
    for (var x = 0; x < BILD; x++) {
      var lon = -180 + (x + 0.5) * 360 / BILD;
      spalteVon[x] = Math.min(e.laenge - 1, Math.floor((lon + 180) / 0.25));
    }
    var leinwand = document.createElement("canvas");
    leinwand.width = BILD; leinwand.height = BILD;
    var ctx = leinwand.getContext("2d");
    var bild = ctx.createImageData(BILD, BILD);
    var px = bild.data, grenze = e.min_beobachtet_prozent;
    for (var y = 0; y < BILD; y++) {
      var mercY = Math.PI * (1 - 2 * (y + 0.5) / BILD);
      var lat = Math.atan(Math.sinh(mercY)) * 180 / Math.PI;
      var zeile = Math.min(e.breite - 1, Math.max(0, Math.floor((90 - lat) / 0.25)));
      var basis = zeile * e.laenge;
      for (var x2 = 0; x2 < BILD; x2++) {
        var i = basis + spalteVon[x2], o = 4 * (y * BILD + x2), a = anteil[i], c3;
        if (a === e.anteil_keine_daten) {
          c3 = ((x2 + y) % SCHRAFFUR) < SCHRAFFUR / 2 ? KEINE_A : KEINE_B;
          px[o] = c3[0]; px[o + 1] = c3[1]; px[o + 2] = c3[2];
        } else if (a < grenze) {
          c3 = ((x2 - y + 4 * BILD) % SCHRAFFUR) < SCHRAFFUR / 3 ? DUENN_A : DUENN_B;
          px[o] = c3[0]; px[o + 1] = c3[1]; px[o + 2] = c3[2];
        } else {
          var w = wert[i];
          px[o] = lut[3 * w]; px[o + 1] = lut[3 * w + 1]; px[o + 2] = lut[3 * w + 2];
        }
        px[o + 3] = 255;
      }
    }
    zeit("bild gerechnet");
    ctx.putImageData(bild, 0, 0);
    var url = leinwand.toDataURL("image/png");
    zeit("png erzeugt " + url.length);
    return url;
  }

  function zelleAn(lon, lat) {
    var zeile = Math.min(719, Math.max(0, Math.floor((90 - lat) / 0.25)));
    var l = ((lon + 180) % 360 + 360) % 360 - 180;
    var spalte = Math.min(1439, Math.max(0, Math.floor((l + 180) / 0.25)));
    return { zeile: zeile, spalte: spalte };
  }

  function nachtlichtAn(lon, lat) {
    var m = aktiverMonat && geladen[aktiverMonat];
    if (!m || !nachtlichtSichtbar) return null;
    var z = zelleAn(lon, lat), i = z.zeile * m.meta.laenge + z.spalte, a = m.anteil[i];
    var r = { monat: aktiverMonat, zeile: z.zeile, spalte: z.spalte, nord: 90 - 0.25 * z.zeile, west: -180 + 0.25 * z.spalte };
    if (Math.abs(lat) > MERC_MAX) r.ausserhalbBild = true;
    if (a === m.meta.anteil_keine_daten) { r.klasse = "keine Daten"; r.text = "keine Daten (kein gültiger Pixel)"; }
    else if (a < m.meta.min_beobachtet_prozent) { r.klasse = "Datenlage unzureichend"; r.anteil = a; r.text = "Datenlage unzureichend (" + a + " % beobachtet)"; }
    else {
      r.klasse = "Wert"; r.anteil = a; r.wert = m.wert[i] / m.meta.wert_skala;
      var wertText = m.wert[i] >= m.meta.wert_max_code ? "mindestens " + zahl(r.wert) + " (Obergrenze der Speicherung)" : zahl(r.wert);
      r.text = wertText + " " + DS.einheit + " (" + a + " % der Pixel beobachtet)";
    }
    return r;
  }

  // ---------- Karte ----------

  var map = new maplibregl.Map({
    container: "map",
    center: [15, 30],
    zoom: 1.4,
    minZoom: 0.4,
    maxZoom: 9,
    attributionControl: false,
    style: {
      version: 8,
      projection: { type: "globe" },
      sources: {},
      layers: [{ id: "raum", type: "background", paint: { "background-color": "#04060b" } }]
    }
  });
  window.ALEPH_KARTE = map; // nur für Prüfungen von außen (Bildschirmfotos)
  map.on("error", function (e) { zeigeFehler("Kartenfehler: " + (e && e.error ? e.error.message : "unbekannt")); });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");
  map.addControl(new maplibregl.AttributionControl({
    compact: true,
    customAttribution: "Nachtlicht: NASA VIIRS Black Marble VNP46A3 · Umrisse: Natural Earth 5.1.1 · UN M49"
  }), "bottom-right");

  var aktiverMonat = null;
  var nachtlichtSichtbar = true;
  var gewaehlt = null; // einheit_id
  var einheitenIndex = {};

  function setzeMonat(monat) {
    return ladeMonat(monat).then(function (m) {
      aktiverMonat = monat;
      var quelle = map.getSource("nachtlicht");
      var ecken = [[-180, MERC_MAX], [180, MERC_MAX], [180, -MERC_MAX], [-180, -MERC_MAX]];
      if (quelle) quelle.updateImage({ url: m.bildUrl, coordinates: ecken });
      else {
        map.addSource("nachtlicht", { type: "image", url: m.bildUrl, coordinates: ecken });
        map.addLayer({ id: "nachtlicht", type: "raster", source: "nachtlicht", paint: { "raster-fade-duration": 0 } },
          // Kein "raster-resampling: nearest": Das ließ die Karte in Chromes Software-Grafik
          // (Prüfumgebung) einfrieren. Folge: An Zellgrenzen werden Farben leicht gemischt.
          map.getLayer("einheiten-fuellung") ? "einheiten-fuellung" : undefined);
      }
      map.setLayoutProperty("nachtlicht", "visibility", nachtlichtSichtbar ? "visible" : "none");
      byId("monat").value = monat;
      zeigeDatenstand();
      return m;
    }).catch(function (err) {
      zeigeFehler("Nachtlicht " + monat + " wird nicht angezeigt: " + err.message);
      throw err;
    });
  }

  function einheitenEinbauen() {
    var gj = EH.geojson;
    gj.features.forEach(function (f) { einheitenIndex[f.properties.einheit_id] = f; });
    map.addSource("einheiten", { type: "geojson", data: gj, tolerance: 0.2 });
    map.addLayer({
      id: "einheiten-fuellung", type: "fill", source: "einheiten",
      paint: {
        "fill-color": ["match", ["get", "hauptkategorie"],
          "umstritten", FARBE_KATEGORIE["umstritten"],
          "besetzt/Konfliktzone", FARBE_KATEGORIE["besetzt/Konfliktzone"],
          "Sonderstatus/autonom", FARBE_KATEGORIE["Sonderstatus/autonom"],
          "#ffffff"],
        "fill-opacity": 0 // unsichtbar, nur zum Anklicken; eine Tönung würde mit der Schraffur verwechselt
      }
    });
    map.addLayer({
      id: "einheiten-linie", type: "line", source: "einheiten",
      filter: ["!", ["get", "sondereinheit"]],
      paint: { "line-color": "#ffffff", "line-opacity": 0.55, "line-width": 0.7 }
    });
    map.addLayer({
      id: "sonder-linie", type: "line", source: "einheiten",
      filter: ["get", "sondereinheit"],
      paint: {
        "line-color": ["match", ["get", "hauptkategorie"],
          "umstritten", FARBE_KATEGORIE["umstritten"],
          "besetzt/Konfliktzone", FARBE_KATEGORIE["besetzt/Konfliktzone"],
          "Sonderstatus/autonom", FARBE_KATEGORIE["Sonderstatus/autonom"],
          "#ffffff"],
        "line-width": 2, "line-dasharray": [2, 1.2]
      }
    });
    map.addLayer({
      id: "auswahl-linie", type: "line", source: "einheiten",
      filter: ["==", ["get", "einheit_id"], ""],
      paint: { "line-color": "#ffffff", "line-width": 3 }
    });
    baueSonderListe();
  }

  function setzeGrenzenSichtbar(an) {
    ["einheiten-fuellung", "einheiten-linie", "sonder-linie", "auswahl-linie"].forEach(function (id) {
      if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", an ? "visible" : "none");
    });
  }

  // ---------- Angaben zur angeklickten Stelle ----------

  function feld(wert) {
    if (wert === null || wert === undefined || wert === "") return '<span class="klein">— (keine Angabe in der Einheitentabelle)</span>';
    var s = esc(wert);
    return /^unklar/.test(String(wert)) ? '<span class="unklar">' + s + "</span>" : s;
  }

  function unEintrag(p) {
    if (p.un_m49) return esc(p.un_name) + " (M49 " + esc(p.un_m49) + ")";
    if (p.un_art === "nicht in M49") return "nicht in M49";
    return '<span class="unklar">unklar</span> – kein übergeordneter UN-Eintrag belegt';
  }

  function einheitHtml(p) {
    var marken = ['<span class="marke-k">' + esc(p.ebene) + "</span>"];
    (p.kategorien ? p.kategorien.split(",") : []).forEach(function (k) {
      k = k.trim();
      marken.push('<span class="marke-k" style="color:' + (FARBE_KATEGORIE[k] || "#fff") + '">' + esc(k) + "</span>");
    });
    if (p.kleiner_als_eine_zelle) marken.push('<span class="marke-k">zu klein für 0,25°</span>');
    var zeilen = [
      ["Übergeordneter UN-Eintrag", unEintrag(p)],
      ["Art der UN-Zuordnung", feld(p.un_art)],
      ["UN-Beleg", feld(p.un_beleg)],
      ["UN-Status", feld(p.un_status)],
      ["Beansprucht von", feld(p.beansprucht_von)],
      ["Verwaltet von", feld(p.verwaltet_von)],
      ["Anerkennung", feld(p.anerkennung)],
      ["Gültigkeit", feld(p.gueltig)],
      ["Weltbank-Sicht", p.weltbank_code ? esc(p.weltbank_code) + " (" + esc(p.weltbank_art) + ")" : feld(p.weltbank_art ? "kein Code (" + p.weltbank_art + ")" : "")],
      ["Umriss (Quelle)", feld(p.herkunft_umriss)],
      ["Fläche laut Grenzdatei", p.flaeche_km2 != null ? esc(Math.round(p.flaeche_km2).toLocaleString("de-DE")) + " km²" : feld("")]
    ];
    if (p.umriss_hinweis) zeilen.push(["Hinweis zum Umriss", feld(p.umriss_hinweis)]);
    return "<h2>" + esc(p.name) + "</h2>" +
      '<div class="marken">' + marken.join("") + "</div>" +
      '<table class="info-tabelle">' + zeilen.map(function (z) { return "<tr><th>" + z[0] + "</th><td>" + z[1] + "</td></tr>"; }).join("") + "</table>" +
      '<p class="klein">Quelle: Einheitentabelle <code>laender/zell_einheiten</code> (erstellt ' + esc(EH.erstellt_utc) +
      "), gebaut aus Natural Earth 5.1.1, UN M49 und <code>sondereinheiten.yaml</code>. Keine Messung, sondern eine belegte Festlegung. " +
      "Umriss und Kennzeichnung hängen nicht vom angezeigten Monat ab (fester Stand Mai 2022); ab wann ein Status gilt, steht unter „Gültigkeit“.</p>";
  }

  function nachtlichtHtml(n) {
    if (!n) return "";
    var ort = n.nord.toFixed(2).replace(".", ",") + "° bis " + (n.nord - 0.25).toFixed(2).replace(".", ",") + "° Breite, " +
      n.west.toFixed(2).replace(".", ",") + "° bis " + (n.west + 0.25).toFixed(2).replace(".", ",") + "° Länge";
    return '<div class="info-abschnitt"><h3>Nachtlicht ' + esc(n.monat) + ' <span class="evidenz">beobachtet</span></h3>' +
      "<div>" + esc(n.text) + "</div>" +
      '<div class="klein">Zelle ' + ort + (n.ausserhalbBild ? " (über 85° – auf dem Globus nicht gezeichnet)" : "") + "</div></div>";
  }

  function zeigeInfo(p, n) {
    var html = p ? einheitHtml(p) : "<h2>Keine Einheit</h2><p class='klein'>An dieser Stelle liegt keine Einheit der Tabelle (z. B. offenes Meer).</p>";
    byId("info-inhalt").innerHTML = html + nachtlichtHtml(n);
    byId("info").hidden = false;
  }

  function waehle(id) {
    gewaehlt = id;
    if (map.getLayer("auswahl-linie")) map.setFilter("auswahl-linie", ["==", ["get", "einheit_id"], id || ""]);
  }

  function umfang(geom) {
    var b = [180, 90, -180, -90];
    (function lauf(c) {
      if (typeof c[0] === "number") {
        b[0] = Math.min(b[0], c[0]); b[1] = Math.min(b[1], c[1]); b[2] = Math.max(b[2], c[0]); b[3] = Math.max(b[3], c[1]);
      } else c.forEach(lauf);
    })(geom.coordinates);
    return [[b[0], b[1]], [b[2], b[3]]];
  }

  function zeigeEinheit(id, punkt) {
    var f = einheitenIndex[id];
    if (!f) { zeigeFehler("Einheit „" + id + "“ steht nicht in der Einheitentabelle."); return; }
    waehle(id);
    zeigeInfo(f.properties, punkt ? nachtlichtAn(punkt[0], punkt[1]) : null);
  }

  function klick(e) {
    var treffer = map.getLayer("einheiten-fuellung") && map.getLayoutProperty("einheiten-fuellung", "visibility") !== "none"
      ? map.queryRenderedFeatures(e.point, { layers: ["einheiten-fuellung"] }) : [];
    var p = treffer.length ? treffer[0].properties : null;
    // Eigenschaften kommen als Text zurück: Wahrheitswerte zurückholen.
    if (p) p = einheitenIndex[p.einheit_id].properties;
    waehle(p ? p.einheit_id : null);
    zeigeInfo(p, nachtlichtAn(e.lngLat.lng, e.lngLat.lat));
  }

  var zeigerPlan = null;
  function zeiger(e) {
    if (zeigerPlan) return;
    zeigerPlan = requestAnimationFrame(function () {
      zeigerPlan = null;
      var ll = e.lngLat, teile = [];
      teile.push(Math.abs(ll.lat).toFixed(1).replace(".", ",") + "° " + (ll.lat >= 0 ? "N" : "S") + " " +
        Math.abs(ll.lng).toFixed(1).replace(".", ",") + "° " + (ll.lng >= 0 ? "O" : "W"));
      var n = nachtlichtAn(ll.lng, ll.lat);
      if (n) teile.push("Nachtlicht: " + n.text);
      if (map.getLayer("einheiten-fuellung") && map.getLayoutProperty("einheiten-fuellung", "visibility") !== "none") {
        var t2 = map.queryRenderedFeatures(e.point, { layers: ["einheiten-fuellung"] });
        if (t2.length) teile.push(t2[0].properties.name);
      }
      var el = byId("zeiger");
      el.textContent = teile.join(" · ");
      el.hidden = false;
    });
  }

  // ---------- Seitenleiste ----------

  function zeigeDatenstand() {
    var z = DS.status_zaehlung, b = DS.status_bedeutung;
    var status = Object.keys(z).map(function (k) { return z[k] + " " + (b[k] || ("Status " + k)); }).join(", ");
    var stand = aktiverMonat && geladen[aktiverMonat];
    var zeilen = [
      ["Angezeigt", DS.angezeigt.length ? DS.angezeigt.join(", ") : "kein Monat"],
      ["Würfel", DS.monate_gesamt + " Monate (2013-01 bis 2025-12): " + status],
      ["Gesperrt", "2023–2025 (Validierungs- und Endtestzeitraum), nie angezeigt" +
        (DS.fertig_gesperrt_endtest.length ? "; fertig, aber gesperrt: " + DS.fertig_gesperrt_endtest.join(", ") : "")],
      ["Feld", DS.feld],
      ["Quelle", DS.quelle],
      ["Einheiten", EH && EH.verfuegbar ? "Natural Earth 5.1.1 (Umrisse), UN M49, sondereinheiten.yaml; Tabelle erstellt " + EH.erstellt_utc : "nicht angezeigt"],
      ["Export", DS.erstellt_utc]
    ];
    if (stand) {
      var st = stand.meta.statistik, f = function (x) { return x.toLocaleString("de-DE"); };
      zeilen.push(["Zellen " + aktiverMonat, f(st.zellen_mit_wert) + " mit Wert, " + f(st.zellen_keine_daten) + " keine Daten, " +
        f(st.zellen_datenlage_unzureichend) + " Datenlage unzureichend (von " + f(st.zellen_gesamt) + ")" +
        (st.zellen_oben_begrenzt ? "; " + f(st.zellen_oben_begrenzt) + " an der Obergrenze abgeschnitten" : "")]);
      zeilen.push(["Selbsttest", "Kontrollzellen stimmen; " + stand.pruefText]);
    }
    byId("datenstand").innerHTML = "<dl>" + zeilen.map(function (r) { return "<dt>" + esc(r[0]) + "</dt><dd>" + esc(r[1]) + "</dd>"; }).join("") + "</dl>";
  }

  function baueSonderListe() {
    var sonder = EH.geojson.features.filter(function (f) { return f.properties.sondereinheit; });
    byId("anzahl-sonder").textContent = sonder.length;
    var gruppen = ["besetzt/Konfliktzone", "umstritten", "Sonderstatus/autonom"];
    function zeichne(filter) {
      var q = (filter || "").toLowerCase();
      var html = "";
      gruppen.forEach(function (g) {
        var liste = sonder.filter(function (f) {
          return f.properties.hauptkategorie === g && (!q || f.properties.name.toLowerCase().indexOf(q) >= 0);
        }).sort(function (a, b) { return a.properties.name.localeCompare(b.properties.name, "de"); });
        if (!liste.length) return;
        html += '<div class="listen-kopf"><span class="punkt" style="background:' + FARBE_KATEGORIE[g] + '"></span>' + esc(g) + " (" + liste.length + ")</div>";
        liste.forEach(function (f) {
          html += '<button class="listen-eintrag" data-id="' + esc(f.properties.einheit_id) + '">' + esc(f.properties.name) + "</button>";
        });
      });
      byId("sonder-liste").innerHTML = html;
    }
    zeichne("");
    byId("suche").addEventListener("input", function (e) { zeichne(e.target.value); });
    byId("sonder-liste").addEventListener("click", function (e) {
      var id = e.target.getAttribute("data-id");
      if (!id) return;
      var f = einheitenIndex[id];
      if (f.geometry) map.fitBounds(umfang(f.geometry), { padding: 120, maxZoom: 6, duration: 900 });
      zeigeEinheit(id);
    });
  }

  function hashWerte() {
    var r = {};
    location.hash.replace(/^#/, "").split("&").forEach(function (teil) {
      var kv = teil.split("=");
      if (kv[0]) r[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1] || "");
    });
    return r;
  }

  // ---------- Start ----------

  baueLegende();
  zeigeDatenstand();

  var h = hashWerte();
  if (h.blick) {
    var b = h.blick.split(",").map(Number);
    map.jumpTo({ center: [b[0], b[1]], zoom: b[2] || 3 });
  }

  byId("an-nachtlicht").addEventListener("change", function (e) {
    nachtlichtSichtbar = e.target.checked;
    if (map.getLayer("nachtlicht")) map.setLayoutProperty("nachtlicht", "visibility", nachtlichtSichtbar ? "visible" : "none");
  });
  byId("an-grenzen").addEventListener("change", function (e) { setzeGrenzenSichtbar(e.target.checked); });
  byId("monat").addEventListener("change", function (e) { setzeMonat(e.target.value); });
  byId("info-zu").addEventListener("click", function () { byId("info").hidden = true; waehle(null); });

  function schraffurBild() {
    var n = SCHRAFFUR, d = new Uint8Array(n * n * 4);
    for (var y = 0; y < n; y++) for (var x = 0; x < n; x++) {
      var c = ((x + y) % n) < n / 2 ? KEINE_A : KEINE_B, o = 4 * (y * n + x);
      d[o] = c[0]; d[o + 1] = c[1]; d[o + 2] = c[2]; d[o + 3] = 255;
    }
    return { width: n, height: n, data: d };
  }

  map.on("load", function () {
    var arbeit = [];

    // Grund des Globus: überall "keine Daten", bis ein gemessenes Bild darüber liegt
    // (auch die Polkappen über 85°, die das Mercator-Bild nicht abdeckt).
    map.addImage("keine-daten", schraffurBild());
    map.setPaintProperty("raum", "background-pattern", "keine-daten");

    // Einheiten – oder deutlich sagen, warum keine Grenzen gezeigt werden.
    if (EH && EH.verfuegbar) {
      einheitenEinbauen();
    } else {
      var hin = byId("einheiten-hinweis");
      hin.className = "hinweis hinweis--stark";
      hin.textContent = "Keine Ländergrenzen angezeigt: " + (EH ? EH.grund : "Datei daten/einheiten.js fehlt") +
        ". Ohne vollständige Einheitentabelle zeigt ALEPH absichtlich auch keine Standardgrenzen (sonst würden z. B. umstrittene Gebiete einem Staat zugeschlagen).";
      hin.hidden = false;
      byId("einheiten-legende").hidden = true;
      byId("an-grenzen").disabled = true;
    }

    // Nachtlicht – nur Monate, die der Export als fertig ausgegeben hat.
    if (!DS.angezeigt.length) {
      var hn = byId("nachtlicht-hinweis");
      hn.className = "hinweis hinweis--stark";
      hn.innerHTML = "<b>Noch kein Nachtlicht-Monat vollständig geladen.</b> Nach der Vollständigkeitsregel vom 25.09.2026 zählt nur ein Monat mit allen Kacheln (Status „fertig“). " +
        "Im Würfel: " + esc(Object.keys(DS.status_zaehlung).map(function (k) { return DS.status_zaehlung[k] + " × " + (DS.status_bedeutung[k] || k); }).join(", ")) +
        ". Sobald ein Monat fertig ist: „Globus aktualisieren.command“ doppelklicken.";
      hn.hidden = false;
      byId("legende").style.opacity = 0.45;
      byId("an-nachtlicht").checked = false;
      byId("an-nachtlicht").disabled = true;
    } else {
      var sel = byId("monat");
      DS.angezeigt.forEach(function (m) {
        var o = document.createElement("option");
        o.value = m; o.textContent = m;
        sel.appendChild(o);
      });
      byId("monat-wahl").hidden = false;
      var start = (h.monat && DS.angezeigt.indexOf(h.monat) >= 0) ? h.monat
        : (DS.angezeigt.filter(function (m) { return m.indexOf("2018") === 0; })[0] || DS.angezeigt[0]);
      arbeit.push(setzeMonat(start));
    }

    map.on("click", klick);
    map.on("mousemove", zeiger);
    map.on("mouseout", function () { byId("zeiger").hidden = true; });

    Promise.all(arbeit).catch(function () {}).then(function () {
      map.once("idle", function () {
        if (h.einheit && EH && EH.verfuegbar) {
          zeigeEinheit(h.einheit, h.punkt ? h.punkt.split(",").map(Number) : null);
        } else if (h.punkt) {
          // wie ein echter Klick an dieser Stelle
          var q = h.punkt.split(",").map(Number);
          klick({ point: map.project(q), lngLat: { lng: q[0], lat: q[1] } });
        }
        document.body.setAttribute("data-bereit", "1");
      });
    });
  });
})();
