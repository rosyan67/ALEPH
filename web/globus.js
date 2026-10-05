/*
 * ALEPH – Globus mit echten Daten (Nachtlicht und Einheiten)
 *
 * Liest nur die Dateien in web/daten/, die aleph/export/globus.py erzeugt:
 *   datenstand.js   welche Monate fertig sind und angezeigt werden dürfen
 *   einheiten.js    Länder und Sondereinheiten (UN-Sicht) oder "nicht verfügbar"
 *   nachtlicht_<JJJJ-MM>.js   ein Monat, gepackt (zlib + Base64)
 *
 * Wichtigste Regel: Fehlende Daten sind nie dunkel. Zellen ohne gültigen
 * Pixel ("keine Daten", grau), Zellen mit zu wenig beobachteten Pixeln
 * ("zu wenig Messungen", intern "Datenlage unzureichend", braun) und noch
 * nicht geladene Zellen (blau) bekommen je ein eigenes gestreiftes Muster;
 * nur gemessene Werte bekommen eine Farbe aus der Skala.
 *
 * Aufbau der Seite nach dem alten Gerüst (Kopfleiste, linke Leiste, Dossier
 * rechts, Zeitleiste unten); die Legende ist immer sichtbar.
 *
 * Zur Lage auf dem Globus: MapLibre legt ein Bild linear in Web-Mercator-
 * Koordinaten auf die Kugel. Das Würfel-Raster ist aber gleichabständig in
 * Grad. Deshalb wird es hier Zeile für Zeile in Mercator-Zeilen umgerechnet
 * (nächste Zelle), bevor es als Bild auf den Globus kommt. Mercator reicht
 * nur bis 85,05° N/S; die Polkappen darüber zeigt die Karte ohne Nachtlicht.
 *
 * Prüf-Parameter in der Adresse (für Bildschirmfotos, optional):
 *   #monat=2018-03&blick=13.4,52.5,4&einheit=krim&punkt=34.1,44.95&leiste=1
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
  // „noch nicht geladen“ (Monat nur für Afrika-Europa-Asien vollständig): bläulich,
  // waagerecht gestreift - weder dunkel noch mit „keine Daten“ zu verwechseln.
  var NICHT_A = [150, 158, 214], NICHT_B = [96, 106, 168];
  var ANTEIL_NICHT_GELADEN = 254;

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
  // 2023–2025 ist Validierungs- und Endtestzeitraum: nie auswählbar, auch wenn eine Datei es anböte.
  var GESPERRT_AB = "2023-01";
  DS.angezeigt = (DS.angezeigt || []).filter(function (m) { return m < GESPERRT_AB; });

  // ---------- Zahlen und Farben ----------

  function zahl(v) {
    if (v < 0.1) return "unter 0,1";
    var s = v >= 100 ? String(Math.round(v / 10) * 10) : Number(v.toPrecision(2)).toString();
    return s.replace(".", ",");
  }
  function t(v) { return Math.log10(v + 0.1); }
  function eine(v) { return v.toFixed(1).replace(".", ","); } // eine Nachkommastelle, damit die Differenz nachrechenbar bleibt
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

  function zeigeVergleichsLegende(an, monat) {
    byId("legende-normal").hidden = an;
    byId("legende-vergleich").hidden = !an;
    if (an) byId("vgl-monate").textContent = monat + " minus " + vorjahr(monat);
    byId("vergleich-an").checked = vergleichAn;
    byId("vergleich-an").disabled = !vergleichMoeglich(monat);
    byId("vergleich-zeile").title = vergleichMoeglich(monat) ? "" : "Nur für Monate 2019 (Vergleich mit demselben Monat 2018)";
    document.body.classList.toggle("vergleich-aktiv", an);
  }

  function baueVergleichsLegende() {
    var teile = [], n = 40;
    for (var i = 0; i <= n; i++) {
      var t = -1 + 2 * i / n, d = (t < 0 ? -1 : 1) * 0.5 * (Math.pow(1 + DIFF_MAX / 0.5, Math.abs(t)) - 1);
      teile.push("rgb(" + diffFarbe(d).join(",") + ") " + (100 * i / n).toFixed(1) + "%");
    }
    byId("vgl-verlauf").style.background = "linear-gradient(to right," + teile.join(",") + ")";
    var achse = byId("vgl-achse");
    [-20, -5, -1, 0, 1, 5, 20].forEach(function (d) {
      var span = document.createElement("span");
      span.style.left = (50 + 50 * diffT(d)) + "%";
      span.textContent = (d > 0 ? "+" : d < 0 ? "−" : "") + Math.abs(d);
      achse.appendChild(span);
    });
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
      // Nach dem Ausführen wird das Element wieder entfernt (die Daten stehen dann in window.ALEPH_NACHTLICHT).
      s.onload = function () { s.remove(); ok(); };
      s.onerror = function () { s.remove(); fehler(new Error("Datei nicht gefunden: " + pfad)); };
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

  var laedt = {}; // monat -> Promise, solange der Monat geladen wird (kein doppeltes Laden)
  function ladeMonat(monat) {
    if (geladen[monat]) return Promise.resolve(geladen[monat]);
    if (laedt[monat]) return laedt[monat];
    var p = ladeMonatNeu(monat);
    laedt[monat] = p;
    function fertig() { delete laedt[monat]; }
    p.then(fertig, fertig);
    return p;
  }

  function ladeMonatNeu(monat) {
    zeit("start " + monat);
    return ladeSkript("daten/nachtlicht_" + monat + ".js").then(function () {
      var e = window.ALEPH_NACHTLICHT && window.ALEPH_NACHTLICHT[monat];
      if (!e) throw new Error("Monat " + monat + " nicht in der Datei");
      zeit("skript geladen");
      // Der gepackte Text wird nach dem Entpacken nicht mehr gebraucht (Speicher beim Abspielen).
      delete window.ALEPH_NACHTLICHT[monat];
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
        if (a === (e.anteil_nicht_geladen || ANTEIL_NICHT_GELADEN)) {
          c3 = (y % SCHRAFFUR) < SCHRAFFUR / 2 ? NICHT_A : NICHT_B;
          px[o] = c3[0]; px[o + 1] = c3[1]; px[o + 2] = c3[2];
        } else if (a === e.anteil_keine_daten) {
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

  // ---------- Vergleich mit dem Vorjahresmonat (Teil 4, nur 2019 gegen 2018) ----------
  // Differenz nur in Zellen, die in BEIDEN Monaten einen gezeigten Wert haben (≥ 50 % beobachtet, geladen,
  // gültiger Pixel). Alle anderen: „kein Vergleich möglich“ (eigenes Karomuster, nie eine Farbe der Skala).
  // Beobachtete Differenz, nicht auf Signifikanz geprüft.
  var VERGLEICH_JAHR = "2019";
  var DIFF_MAX = 20; // nW·cm⁻²·sr⁻¹; darüber gleiche Farbe wie ±20
  var DIFF_MITTE = [58, 62, 72], DIFF_DUNKLER = [80, 150, 235], DIFF_HELLER = [240, 96, 70];
  var KEIN_VGL_A = [176, 181, 192], KEIN_VGL_B = [122, 127, 138];
  var vergleichAn = false;
  var diffBilder = {};

  function vorjahr(monat) { return (Number(monat.slice(0, 4)) - 1) + monat.slice(4); }
  function vergleichMoeglich(monat) {
    return monat && monat.slice(0, 4) === VERGLEICH_JAHR && DS.angezeigt.indexOf(vorjahr(monat)) >= 0;
  }
  function vergleichAktiv(monat) { return vergleichAn && vergleichMoeglich(monat); }

  function diffT(d) {
    var t = Math.log10(1 + Math.abs(d) / 0.5) / Math.log10(1 + DIFF_MAX / 0.5);
    return Math.min(1, t) * (d < 0 ? -1 : 1);
  }
  function diffFarbe(d) {
    var t = diffT(d), ziel = t < 0 ? DIFF_DUNKLER : DIFF_HELLER, f = Math.abs(t);
    return [0, 1, 2].map(function (k) { return Math.round(DIFF_MITTE[k] + f * (ziel[k] - DIFF_MITTE[k])); });
  }
  function vergleichbar(e, a) { return a <= 100 && a >= e.min_beobachtet_prozent; }

  function baueDiffBild(neu, alt) {
    var e = neu.meta, spalteVon = new Int32Array(BILD);
    for (var x = 0; x < BILD; x++) spalteVon[x] = Math.min(e.laenge - 1, Math.floor(((x + 0.5) * 360 / BILD) / 0.25));
    var leinwand = document.createElement("canvas");
    leinwand.width = BILD; leinwand.height = BILD;
    var ctx = leinwand.getContext("2d"), bild = ctx.createImageData(BILD, BILD), px = bild.data;
    for (var y = 0; y < BILD; y++) {
      var lat = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 0.5) / BILD))) * 180 / Math.PI;
      var basis = Math.min(e.breite - 1, Math.max(0, Math.floor((90 - lat) / 0.25))) * e.laenge;
      for (var x2 = 0; x2 < BILD; x2++) {
        var i = basis + spalteVon[x2], o = 4 * (y * BILD + x2), c;
        if (vergleichbar(e, neu.anteil[i]) && vergleichbar(alt.meta, alt.anteil[i])) {
          c = diffFarbe(neu.wert[i] / e.wert_skala - alt.wert[i] / alt.meta.wert_skala);
        } else {
          c = ((Math.floor(x2 / 6) + Math.floor(y / 6)) % 2) ? KEIN_VGL_A : KEIN_VGL_B;
        }
        px[o] = c[0]; px[o + 1] = c[1]; px[o + 2] = c[2]; px[o + 3] = 255;
      }
    }
    ctx.putImageData(bild, 0, 0);
    return leinwand.toDataURL("image/png");
  }

  function zustandText(monat) {
    var e = (DS.monate || []).filter(function (x) { return x.monat === monat; })[0];
    return e && e.zustand_text ? e.zustand_text : "vollständig";
  }

  function zelleAn(lon, lat) {
    var zeile = Math.min(719, Math.max(0, Math.floor((90 - lat) / 0.25)));
    var l = ((lon + 180) % 360 + 360) % 360 - 180;
    var spalte = Math.min(1439, Math.max(0, Math.floor((l + 180) / 0.25)));
    return { zeile: zeile, spalte: spalte };
  }

  function klassenName(meta, a) {
    if (a === (meta.anteil_nicht_geladen || ANTEIL_NICHT_GELADEN)) return "noch nicht geladen";
    if (a === meta.anteil_keine_daten) return "keine Daten";
    if (a < meta.min_beobachtet_prozent) return "zu wenig Messungen";
    return "Wert";
  }

  function nachtlichtAn(lon, lat) {
    var m = aktiverMonat && geladen[aktiverMonat];
    if (!m || !nachtlichtSichtbar) return null;
    var z = zelleAn(lon, lat), i = z.zeile * m.meta.laenge + z.spalte, a = m.anteil[i];
    var r = { monat: aktiverMonat, zeile: z.zeile, spalte: z.spalte, nord: 90 - 0.25 * z.zeile, west: -180 + 0.25 * z.spalte };
    if (Math.abs(lat) > MERC_MAX) r.ausserhalbBild = true;
    var alt = vergleichAktiv(aktiverMonat) && geladen[vorjahr(aktiverMonat)];
    if (alt) {
      var a0 = alt.anteil[i];
      r.vorjahr = vorjahr(aktiverMonat);
      if (vergleichbar(m.meta, a) && vergleichbar(alt.meta, a0)) {
        var w1 = m.wert[i] / m.meta.wert_skala, w0 = alt.wert[i] / alt.meta.wert_skala, d = w1 - w0;
        r.klasse = "Differenz"; r.differenz = d; r.wert = w1; r.wertVorjahr = w0;
        r.wertText = (d > 0 ? "+" : d < 0 ? "−" : "±") + eine(Math.abs(d));
        r.text = "Differenz " + r.wertText + " " + DS.einheit + " (" + eine(w0) + " → " + eine(w1) + "), beobachtet, nicht auf Signifikanz geprüft";
      } else {
        r.klasse = "kein Vergleich"; r.kurz = "kein Vergleich möglich";
        r.erklaerung = "Nicht in beiden Monaten ein gezeigter Wert (" + r.vorjahr + ": " + klassenName(alt.meta, a0) + "; " + aktiverMonat + ": " + klassenName(m.meta, a) + ").";
        r.text = "kein Vergleich möglich";
      }
      return r;
    }
    if (a === (m.meta.anteil_nicht_geladen || ANTEIL_NICHT_GELADEN)) {
      r.klasse = "noch nicht geladen"; r.kurz = "noch nicht geladen";
      r.erklaerung = "In diesem Monat ist bisher nur Afrika-Europa-Asien geladen; diese Zelle folgt, der Download läuft.";
      r.text = "noch nicht geladen (in diesem Monat ist bisher nur Afrika-Europa-Asien geladen)";
    } else if (a === m.meta.anteil_keine_daten) {
      r.klasse = "keine Daten"; r.kurz = "keine Daten";
      r.erklaerung = "Kein gültiger Pixel: keine Kachel, Polarsommer ohne Nacht oder Fehlwert.";
      r.text = "keine Daten (kein gültiger Pixel)";
    } else if (a < m.meta.min_beobachtet_prozent) {
      r.klasse = "Datenlage unzureichend"; r.anteil = a; r.kurz = "zu wenig Messungen";
      r.erklaerung = "Nur " + a + " % der Pixel im Monat beobachtet (Grenze " + m.meta.min_beobachtet_prozent + " %); der Rest ist aufgefüllt oder ohne gültigen Wert.";
      r.text = "zu wenig Messungen (" + a + " % beobachtet)";
    } else {
      r.klasse = "Wert"; r.anteil = a; r.wert = m.wert[i] / m.meta.wert_skala;
      r.wertText = m.wert[i] >= m.meta.wert_max_code ? "mindestens " + zahl(r.wert) + " (Obergrenze der Speicherung)" : zahl(r.wert);
      r.text = r.wertText + " " + DS.einheit + " (" + a + " % der Pixel beobachtet)";
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
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
  map.addControl(new maplibregl.AttributionControl({
    compact: true,
    customAttribution: "Nachtlicht: NASA VIIRS Black Marble VNP46A3 · Umrisse: Natural Earth 5.1.1 · UN M49"
  }), "bottom-right");

  var aktiverMonat = null;
  var nachtlichtSichtbar = true;
  var gewaehlt = null; // einheit_id
  var einheitenIndex = {};
  var START_BLICK = { center: [15, 30], zoom: 1.4 };
  var letzteAuswahl = null; // {p: Eigenschaften oder null, punkt: [lon, lat] oder null} – für Monatswechsel

  // Schnittstelle für Zusatzteile (Blickpunkte, Länderwerte, Auswertung, Vergleich). Die Datenlogik
  // (Laden, Selbsttest, Farben, Klassen) bleibt hier; Zusatzteile lesen nur und zeigen an.
  var API = window.ALEPH_GLOBUS = {
    map: map,
    dossierZusatz: [], // Funktionen (p, n) -> HTML, erscheinen im Dossier unter dem Nachtlicht-Kasten
    beiMonat: [], // Funktionen (monat) nach jedem Monatswechsel
    setzeMonat: function (m) { return setzeMonat(m); },
    aktiverMonat: function () { return aktiverMonat; },
    monatDaten: function (m) { return geladen[m] || null; },
    ladeMonat: function (m) { return ladeMonat(m); },
    zeigeEinheit: function (id, punkt) { return zeigeEinheit(id, punkt); },
    springeZuEinheit: function (id) { return springeZuEinheit(id); },
    einheit: function (id) { return einheitenIndex[id] ? einheitenIndex[id].properties : null; },
    einheiten: function () { return einheitenIndex; },
    schliesseDossier: function () { schliesseDossier(); },
    dossierOffen: function () { return byId("info").classList.contains("is-open"); },
    esc: esc,
    zahl: zahl
  };

  // ---------- Monat: Zeitleiste über alle Monate vor 2023 ----------
  // Der Regler läuft über ALLE Kalendermonate der Zeitleiste, auch über nicht auswählbare (z. B. „zurückgestellt“),
  // damit gleiche Abstände gleiche Zeit bedeuten und kein Monat still fehlt. Landet er auf einem nicht auswählbaren
  // Monat, springt er zum nächsten auswählbaren in Bewegungsrichtung und sagt das sichtbar.
  // Auswählbar ist nur, was der Export als Datei ausgegeben hat (DS.angezeigt).
  var LEISTE = ((DS.zeitleiste && DS.zeitleiste.length) ? DS.zeitleiste
    : DS.angezeigt.map(function (m) { return { monat: m, auswaehlbar: true, zustand: null, zustand_text: zustandText(m) }; }))
    .filter(function (e) { return e.monat < GESPERRT_AB; })
    .map(function (e) {
      var k = {}; Object.keys(e).forEach(function (s) { k[s] = e[s]; });
      k.auswaehlbar = !!e.auswaehlbar && DS.angezeigt.indexOf(e.monat) >= 0;
      return k;
    });
  API.zeitleiste = function () { return LEISTE; };

  function leistenIndex(monat) {
    for (var i = 0; i < LEISTE.length; i++) if (LEISTE[i].monat === monat) return i;
    return -1;
  }
  function naechsterWaehlbarer(i, richtung) {
    for (var j = i; j >= 0 && j < LEISTE.length; j += richtung) if (LEISTE[j].auswaehlbar) return j;
    return -1;
  }
  // Klasse im Zustandsband: vollständig / nur Afrika-Europa-Asien / zurückgestellt / sonst nicht auswählbar.
  function bandKlasse(e) {
    if (e.auswaehlbar) return e.zustand === 4 ? "tl-z--region" : "tl-z--voll";
    return e.zustand_text === "zurückgestellt" ? "tl-z--zurueck" : "tl-z--fehlt";
  }
  function leistenTitel(e) {
    return e.monat + ": " + e.zustand_text + (e.grund ? " – " + e.grund + " (Download, zuletzt versucht " + e.zurueckgestellt_seit + ")" : "") +
      (e.auswaehlbar ? "" : " – nicht auswählbar");
  }
  // Zusammenhängende Monate gleichen Zustands als Bereiche, z. B. „2013-01 bis 2017-12: nur Afrika-Europa-Asien (60)“.
  function leistenBereiche() {
    var b = [];
    LEISTE.forEach(function (e) {
      var letzter = b[b.length - 1];
      if (letzter && letzter.text === e.zustand_text) { letzter.bis = e.monat; letzter.n++; }
      else b.push({ von: e.monat, bis: e.monat, text: e.zustand_text, n: 1 });
    });
    return b.map(function (x) { return (x.n > 1 ? x.von + " bis " + x.bis : x.von) + ": " + x.text + " (" + x.n + ")"; });
  }

  function zeigeUebersprungen(e, gezeigt) {
    var el = byId("monat-hinweis");
    if (!e) { el.hidden = true; return; }
    el.innerHTML = "<b>" + esc(e.monat) + ": " + esc(e.zustand_text) + "</b>" +
      (e.grund ? " – " + esc(e.grund) + " (Download, zuletzt versucht " + esc(e.zurueckgestellt_seit) + ")" : "") +
      ". Nicht auswählbar; gezeigt wird " + esc(gezeigt) + ".";
    el.hidden = false;
  }

  function zeigeMonatWahl(monat) {
    var i = leistenIndex(monat);
    byId("monat-regler").value = i;
    byId("monat-name").textContent = monat;
    byId("monat-zustand").textContent = zustandText(monat);
    byId("monat-zurueck").disabled = naechsterWaehlbarer(i - 1, -1) < 0;
    byId("monat-vor").disabled = naechsterWaehlbarer(i + 1, 1) < 0;
    Array.prototype.forEach.call(byId("monat-marken").children, function (el) {
      el.classList.toggle("is-aktiv", el.getAttribute("data-jahr") === monat.slice(0, 4));
    });
    Array.prototype.forEach.call(byId("monat-band").children, function (el, j) { el.classList.toggle("is-aktiv", j === i); });
  }

  function baueMonatWahl() {
    var n = LEISTE.length, marken = byId("monat-marken"), band = byId("monat-band");
    byId("monat-regler").max = Math.max(0, n - 1);
    byId("monat-regler").disabled = DS.angezeigt.length < 2;
    function pos(i) { return n > 1 ? 100 * i / (n - 1) : 50; }
    // Jahresmarken: Strich und Jahreszahl an jedem Januar (und am ersten Monat).
    LEISTE.forEach(function (e, i) {
      if (i !== 0 && e.monat.slice(5) !== "01") return;
      var s = document.createElement("span");
      s.className = "tl-jahr";
      s.style.left = pos(i) + "%";
      s.textContent = e.monat.slice(0, 4);
      s.setAttribute("data-jahr", e.monat.slice(0, 4));
      marken.appendChild(s);
    });
    // Zustandsband: ein Feld je Monat, Zustand als Farbe und im Tooltip; Klick wählt den Monat.
    var breite = n > 1 ? 100 / (n - 1) : 100;
    LEISTE.forEach(function (e, i) {
      var f = document.createElement("span");
      f.className = "tl-z " + bandKlasse(e);
      f.style.left = (pos(i) - breite / 2) + "%";
      f.style.width = breite + "%";
      f.title = leistenTitel(e);
      f.setAttribute("data-monat", e.monat);
      band.appendChild(f);
    });
    band.addEventListener("click", function (ev) {
      var m = ev.target.getAttribute("data-monat");
      if (!m) return;
      spiele(false);
      var j = leistenIndex(m);
      waehleIndex(j, j >= leistenIndex(aktiverMonat) ? 1 : -1);
    });
    // Legende des Bandes; nicht auswählbare Monate werden ausdrücklich genannt.
    var fehlend = LEISTE.filter(function (e) { return !e.auswaehlbar; });
    byId("monat-band-legende").innerHTML =
      '<span><span class="tl-z-muster tl-z--voll"></span>vollständig</span>' +
      '<span><span class="tl-z-muster tl-z--region"></span>nur Afrika-Europa-Asien</span>' +
      (fehlend.length ? '<span class="tl-z-fehlt"><span class="tl-z-muster ' + bandKlasse(fehlend[0]) + '"></span>' +
        fehlend.map(function (e) { return esc(e.monat) + " " + esc(e.zustand_text); }).join(", ") + " – nicht auswählbar</span>" : "");
    byId("monat-wahl").hidden = false;
    byId("monat-band-legende").hidden = false;
  }

  // Index der Zeitleiste wählen; nicht auswählbare Monate werden in Richtung `richtung` übersprungen (mit Hinweis).
  function waehleIndex(i, richtung) {
    var e = LEISTE[i];
    if (!e) return Promise.resolve();
    var j = e.auswaehlbar ? i : naechsterWaehlbarer(i, richtung || 1);
    if (j < 0) j = naechsterWaehlbarer(i, -(richtung || 1));
    if (j < 0) return Promise.resolve();
    zeigeUebersprungen(e.auswaehlbar ? null : e, LEISTE[j].monat);
    if (LEISTE[j].monat === aktiverMonat) { zeigeMonatWahl(aktiverMonat); return Promise.resolve(); }
    return setzeMonat(LEISTE[j].monat);
  }

  // ---------- Abspielen: Monat für Monat ----------
  // Zeigt jeden auswählbaren Monat der Reihe nach; nicht auswählbare werden übersprungen und genannt.
  // Pause zwischen zwei Monaten erst NACH dem Laden, damit ein langsamer Rechner nicht hinterherhinkt.
  var SPIEL_PAUSE_MS = 1200;
  var spielt = false, spielTimer = null;
  function spiele(an) {
    if (spielt === an) return;
    spielt = an;
    clearTimeout(spielTimer);
    var k = byId("abspielen");
    k.textContent = an ? "❚❚" : "▶";
    k.setAttribute("aria-label", an ? "Anhalten" : "Monat für Monat abspielen");
    k.title = an ? "Anhalten" : "Monat für Monat abspielen";
    byId("spiel-hinweis").hidden = !an;
    if (!an) return;
    var i = leistenIndex(aktiverMonat);
    if (naechsterWaehlbarer(i + 1, 1) < 0) { // am Ende: von vorn
      var erster = naechsterWaehlbarer(0, 1);
      if (erster >= 0) { setzeMonat(LEISTE[erster].monat).then(weiter, function () { spiele(false); }); return; }
    }
    spielSchritt();
  }
  function weiter() { if (spielt) spielTimer = setTimeout(spielSchritt, SPIEL_PAUSE_MS); }
  function spielSchritt() {
    if (!spielt) return;
    var i = leistenIndex(aktiverMonat), j = naechsterWaehlbarer(i + 1, 1);
    if (j < 0) { spiele(false); return; }
    var uebersprungen = LEISTE.slice(i + 1, j);
    zeigeUebersprungen(uebersprungen.length ? uebersprungen[0] : null, LEISTE[j].monat);
    setzeMonat(LEISTE[j].monat).then(weiter, function () { spiele(false); });
  }

  // ---------- Speicher: höchstens SPEICHER_MONATE entpackte Monate behalten ----------
  // Jeder Monat belegt entpackt rund 3 MB plus ein Bild; beim Abspielen über 119 Monate würde der Speicher des
  // MacBook Pro 2015 sonst volllaufen. Der aktive Monat und sein Vorjahresmonat (Vergleich) bleiben immer.
  var SPEICHER_MONATE = 8;
  var benutzt = []; // Reihenfolge der letzten Nutzung
  function merkeBenutzt(monat) {
    benutzt = benutzt.filter(function (m) { return m !== monat; });
    benutzt.push(monat);
    var schutz = [aktiverMonat, aktiverMonat && vorjahr(aktiverMonat)];
    for (var k = 0; benutzt.length > SPEICHER_MONATE && k < benutzt.length;) {
      var m = benutzt[k];
      if (schutz.indexOf(m) >= 0) { k++; continue; }
      delete geladen[m];
      delete diffBilder[m];
      benutzt.splice(k, 1);
    }
  }

  var letzteAnfrage = 0;
  function setzeMonat(monat) {
    var anfrage = ++letzteAnfrage;
    return ladeMonat(monat).then(function (m) {
      if (!vergleichAktiv(monat)) return [m, null];
      return ladeMonat(vorjahr(monat)).then(function (v) { return [m, v]; });
    }).then(function (paar) {
      // Inzwischen wurde ein anderer Monat gewählt (z. B. schnelles Ziehen am Regler): dieses Ergebnis verwerfen,
      // sonst könnte am Ende ein anderer Monat zu sehen sein, als der Regler zeigt.
      if (anfrage !== letzteAnfrage) return paar[0];
      var m = paar[0], v = paar[1];
      aktiverMonat = monat;
      merkeBenutzt(monat);
      if (v) merkeBenutzt(vorjahr(monat));
      var url = m.bildUrl;
      if (v) url = diffBilder[monat] || (diffBilder[monat] = baueDiffBild(m, v));
      zeigeVergleichsLegende(!!v, monat);
      var quelle = map.getSource("nachtlicht");
      var ecken = [[-180, MERC_MAX], [180, MERC_MAX], [180, -MERC_MAX], [-180, -MERC_MAX]];
      if (quelle) quelle.updateImage({ url: url, coordinates: ecken });
      else {
        map.addSource("nachtlicht", { type: "image", url: url, coordinates: ecken });
        map.addLayer({ id: "nachtlicht", type: "raster", source: "nachtlicht", paint: { "raster-fade-duration": 0 } },
          // Kein "raster-resampling: nearest": Das ließ die Karte in Chromes Software-Grafik
          // (Prüfumgebung) einfrieren. Folge: An Zellgrenzen werden Farben leicht gemischt.
          map.getLayer("einheiten-fuellung") ? "einheiten-fuellung" : undefined);
      }
      map.setLayoutProperty("nachtlicht", "visibility", nachtlichtSichtbar ? "visible" : "none");
      zeigeMonatWahl(monat);
      var hinweis = byId("nachtlicht-hinweis");
      if (m.meta.zustand === 4) {
        hinweis.className = "dock-hinweis";
        hinweis.innerHTML = "<b>" + esc(monat) + " ist bisher nur für Afrika, Europa und Asien vollständig geladen.</b> " +
          'Die übrigen Zellen sind <span class="feld feld--nicht"></span> „noch nicht geladen“ – das heißt nicht dunkel. ' +
          "Einzelne Kacheln außerhalb (z. B. Französisch-Guayana, Azoren) sind schon geladen, weil sie Land eines Staates der Region enthalten.";
        hinweis.hidden = false;
      } else {
        hinweis.hidden = true;
      }
      zeigeDatenstand();
      aktualisiereDossier();
      API.beiMonat.forEach(function (f) { try { f(monat); } catch (err) { zeigeFehler("Zusatzteil: " + err.message); } });
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
        "fill-color": "#ffffff",
        "fill-opacity": 0 // unsichtbar, nur zum Anklicken; eine Tönung würde mit „zu wenig Messungen“ verwechselt
      }
    });
    map.addLayer({
      id: "einheiten-linie", type: "line", source: "einheiten",
      filter: ["!", ["get", "sondereinheit"]],
      paint: { "line-color": "#ffffff", "line-opacity": 0.55, "line-width": 0.7 }
    });
    // Auswahl unter den Sondereinheiten-Linien, damit deren Kategoriefarbe sichtbar bleibt.
    map.addLayer({
      id: "auswahl-linie", type: "line", source: "einheiten",
      filter: ["==", ["get", "einheit_id"], ""],
      paint: { "line-color": "#ffffff", "line-width": 3 }
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
    baueSonderListe();
    baueSuche();
  }

  function setzeGrenzenSichtbar(an) {
    ["einheiten-fuellung", "einheiten-linie", "sonder-linie", "auswahl-linie"].forEach(function (id) {
      if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", an ? "visible" : "none");
    });
  }

  // ---------- Dossier: Angaben zur angeklickten Stelle ----------

  function feld(wert) {
    if (wert === null || wert === undefined || wert === "") return '<span class="inv-leer">— keine Angabe in der Einheitentabelle</span>';
    var s = esc(wert);
    return /^unklar/.test(String(wert)) ? '<span class="unklar">' + s + "</span>" : s;
  }

  function unEintrag(p) {
    if (p.un_m49) return esc(p.un_name) + " (M49 " + esc(p.un_m49) + ")";
    if (p.un_art === "nicht in M49") return "nicht in M49";
    return '<span class="unklar">unklar</span> – kein übergeordneter UN-Eintrag belegt';
  }

  function katBadges(p) {
    var b = [];
    (p.kategorien ? p.kategorien.split(",") : []).forEach(function (k) {
      k = k.trim();
      if (!k) return;
      b.push('<span class="inv-badge inv-badge--kat"><span class="kat-strich" style="color:' + (FARBE_KATEGORIE[k] || "#fff") + '"></span>' + esc(k) + "</span>");
    });
    return b;
  }

  function einheitHtml(p) {
    var badges = ['<span class="inv-badge">' + esc(p.ebene) + "</span>"].concat(katBadges(p));
    if (p.kleiner_als_eine_zelle) badges.push('<span class="inv-badge inv-badge--hell">zu klein für 0,25°</span>');
    var zeilen = [
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
    return {
      kopf: '<div class="inv-badges">' + badges.join("") + "</div>" +
        '<h2 class="inv-title">' + esc(p.name) + "</h2>" +
        '<p class="inv-sub">Übergeordneter UN-Eintrag: ' + unEintrag(p) + "</p>",
      felder: '<div class="inv-abschnitt">Einheit – belegte Festlegung, keine Messung</div>' +
        zeilen.map(function (z) {
          return '<div class="inv-field"><div class="inv-field-label">' + z[0] + '</div><div class="inv-field-value">' + z[1] + "</div></div>";
        }).join("") +
        '<p class="inv-fuss">Quelle: Einheitentabelle <code>laender/zell_einheiten</code> (erstellt ' + esc(EH.erstellt_utc) +
        "), gebaut aus Natural Earth 5.1.1, UN M49 und <code>sondereinheiten.yaml</code>. " +
        "Umriss und Kennzeichnung hängen nicht vom angezeigten Monat ab (fester Stand Mai 2022); ab wann ein Status gilt, steht unter „Gültigkeit“.</p>"
    };
  }

  var KLASSEN_FELD = { "keine Daten": "feld--keine", "Datenlage unzureichend": "feld--duenn", "noch nicht geladen": "feld--nicht", "kein Vergleich": "feld--keinvgl" };

  function nachtlichtHtml(n) {
    if (!n) {
      if (!aktiverMonat) return "";
      return '<div class="inv-messung"><div class="inv-messung-kopf"><span>Nachtlicht ' + esc(aktiverMonat) + "</span></div>" +
        '<div class="inv-messung-note">Für den Nachtlichtwert auf eine Stelle im Gebiet klicken.</div></div>';
    }
    var ort = n.nord.toFixed(2).replace(".", ",") + "° bis " + (n.nord - 0.25).toFixed(2).replace(".", ",") + "° Breite, " +
      n.west.toFixed(2).replace(".", ",") + "° bis " + (n.west + 0.25).toFixed(2).replace(".", ",") + "° Länge";
    var inhalt;
    if (n.klasse === "Differenz") {
      inhalt = '<div class="inv-messung-wert">' + esc(n.wertText) + ' <span class="einheit">' + esc(DS.einheit) + "</span></div>" +
        '<div class="inv-messung-note">Differenz ' + esc(n.monat) + " minus " + esc(n.vorjahr) + ": " + esc(eine(n.wertVorjahr)) + " → " + esc(eine(n.wert)) +
        ". Beobachtete Differenz, nicht auf Signifikanz geprüft.</div>";
    } else if (n.klasse === "Wert") {
      inhalt = '<div class="inv-messung-wert">' + esc(n.wertText) + ' <span class="einheit">' + esc(DS.einheit) + "</span></div>" +
        '<div class="inv-messung-note">' + n.anteil + " % der Pixel im Monat beobachtet · Wert auf zwei gültige Ziffern gerundet</div>";
    } else {
      inhalt = '<div class="inv-messung-klasse"><span class="feld ' + KLASSEN_FELD[n.klasse] + '"></span>' + esc(n.kurz) + "</div>" +
        '<div class="inv-messung-note">' + esc(n.erklaerung) + " Das ist keine Messung von Dunkelheit.</div>";
    }
    var kopfText = n.vorjahr ? "Vergleich " + n.monat + " mit " + n.vorjahr : n.monat + " · " + zustandText(n.monat);
    return '<div class="inv-messung"><div class="inv-messung-kopf"><span>Nachtlicht ' + esc(kopfText) +
      '</span><span class="inv-evidenz">beobachtet</span></div>' + inhalt +
      '<div class="inv-messung-note">Zelle ' + ort + (n.ausserhalbBild ? " (über 85° – auf dem Globus nicht gezeichnet)" : "") + "</div></div>";
  }

  function oeffneDossier() {
    var el = byId("info");
    el.classList.add("is-open");
    el.setAttribute("aria-hidden", "false");
    document.body.classList.add("dossier-offen");
  }
  function schliesseDossier() {
    var el = byId("info");
    el.classList.remove("is-open");
    el.setAttribute("aria-hidden", "true");
    document.body.classList.remove("dossier-offen");
    waehle(null);
  }

  function zusatzHtml(p, n) {
    return API.dossierZusatz.map(function (f) {
      try { return f(p, n) || ""; } catch (err) { return '<div class="hinweis hinweis--stark">Zusatzfeld fehlerhaft: ' + esc(err.message) + "</div>"; }
    }).join("");
  }

  function aktualisiereDossier() {
    if (!letzteAuswahl || !byId("info").classList.contains("is-open")) return;
    var q = letzteAuswahl.punkt;
    zeigeInfo(letzteAuswahl.p, q ? nachtlichtAn(q[0], q[1]) : null, q, true);
  }

  function zeigeInfo(p, n, punkt, scrollBehalten) {
    var html;
    letzteAuswahl = { p: p, punkt: punkt || null };
    if (p) {
      var e = einheitHtml(p);
      html = e.kopf + nachtlichtHtml(n) + zusatzHtml(p, n) + e.felder;
    } else {
      html = '<div class="inv-badges"><span class="inv-badge inv-badge--hell">keine Einheit</span></div>' +
        '<h2 class="inv-title">Keine Einheit</h2><p class="inv-sub">An dieser Stelle liegt keine Einheit der Tabelle (z. B. offenes Meer).</p>' +
        nachtlichtHtml(n);
    }
    var oben = byId("info-inhalt").scrollTop;
    byId("info-inhalt").innerHTML = html;
    byId("info-inhalt").scrollTop = scrollBehalten ? oben : 0;
    oeffneDossier();
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
    zeigeInfo(f.properties, punkt ? nachtlichtAn(punkt[0], punkt[1]) : null, punkt);
  }

  function springeZuEinheit(id) {
    var f = einheitenIndex[id];
    if (f && f.geometry) {
      map.fitBounds(umfang(f.geometry), { padding: { top: 140, bottom: 150, left: 60, right: 460 }, maxZoom: 6, duration: 900 });
    }
    zeigeEinheit(id);
  }

  function klick(e) {
    var treffer = map.getLayer("einheiten-fuellung") && map.getLayoutProperty("einheiten-fuellung", "visibility") !== "none"
      ? map.queryRenderedFeatures(e.point, { layers: ["einheiten-fuellung"] }) : [];
    var p = treffer.length ? treffer[0].properties : null;
    // Eigenschaften kommen als Text zurück: Wahrheitswerte zurückholen.
    if (p) p = einheitenIndex[p.einheit_id].properties;
    waehle(p ? p.einheit_id : null);
    zeigeInfo(p, nachtlichtAn(e.lngLat.lng, e.lngLat.lat), [e.lngLat.lng, e.lngLat.lat]);
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

  // ---------- Suche (nur Einheiten aus der Tabelle) ----------

  function normal(s) {
    return String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  }

  function baueSuche() {
    var feldEl = byId("suche-einheit"), liste = byId("suche-treffer");
    var alle = EH.geojson.features.map(function (f) {
      var p = f.properties;
      return { id: p.einheit_id, name: p.name, sonder: !!p.sondereinheit, kat: p.hauptkategorie, sub: p.un_name || "", schluessel: normal(p.name) };
    });
    var aktiv = -1;

    function eintrag(t) {
      var strich = t.sonder ? '<span class="kat-strich" style="color:' + (FARBE_KATEGORIE[t.kat] || "#fff") + '"></span>' : "";
      var sub = t.sonder ? esc(t.kat) : (t.sub && t.sub !== t.name ? "UN: " + esc(t.sub) : "");
      return '<button class="search-item" role="option" data-id="' + esc(t.id) + '">' + strich + "<span>" + esc(t.name) + "</span>" +
        (sub ? '<span class="item-sub">' + sub + "</span>" : "") + "</button>";
    }

    function zeichne() {
      var q = normal(feldEl.value.trim());
      aktiv = -1;
      if (!q) { liste.hidden = true; return; }
      var treffer = alle.filter(function (t) { return t.schluessel.indexOf(q) >= 0; })
        .sort(function (a, b) { return (a.schluessel.indexOf(q) === 0 ? 0 : 1) - (b.schluessel.indexOf(q) === 0 ? 0 : 1) || a.name.localeCompare(b.name, "de"); });
      var sonder = treffer.filter(function (t) { return t.sonder; }).slice(0, 8);
      var staaten = treffer.filter(function (t) { return !t.sonder; }).slice(0, 8);
      var html = "";
      if (staaten.length) html += '<div class="search-group-label">Staaten und Gebiete</div>' + staaten.map(eintrag).join("");
      if (sonder.length) html += '<div class="search-group-label">Sondereinheiten</div>' + sonder.map(eintrag).join("");
      liste.innerHTML = html || '<div class="search-empty">Keine Einheit in der Tabelle heißt so. Gesucht wird nur in Länder- und Gebietsnamen.</div>';
      liste.hidden = false;
    }

    function markiere(i) {
      var knoepfe = liste.querySelectorAll(".search-item");
      if (!knoepfe.length) return;
      aktiv = (i + knoepfe.length) % knoepfe.length;
      Array.prototype.forEach.call(knoepfe, function (k, j) { k.classList.toggle("is-aktiv", j === aktiv); });
      knoepfe[aktiv].scrollIntoView({ block: "nearest" });
    }

    function nimm(id) {
      liste.hidden = true;
      feldEl.value = "";
      feldEl.blur();
      springeZuEinheit(id);
    }

    feldEl.addEventListener("input", zeichne);
    feldEl.addEventListener("focus", zeichne);
    feldEl.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); markiere(aktiv + 1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); markiere(aktiv - 1); }
      else if (e.key === "Enter") {
        var knoepfe = liste.querySelectorAll(".search-item");
        var k = knoepfe[aktiv >= 0 ? aktiv : 0];
        if (k) nimm(k.getAttribute("data-id"));
      } else if (e.key === "Escape") { liste.hidden = true; feldEl.blur(); }
    });
    liste.addEventListener("mousedown", function (e) {
      var k = e.target.closest(".search-item");
      if (k) { e.preventDefault(); nimm(k.getAttribute("data-id")); }
    });
    feldEl.addEventListener("blur", function () { setTimeout(function () { liste.hidden = true; }, 120); });
  }

  // ---------- Linke Leiste ----------

  function setzeEbenenLeiste(offen) {
    var p = byId("ebenen-panel");
    p.classList.toggle("is-open", offen);
    p.setAttribute("aria-hidden", offen ? "false" : "true");
    byId("ebenen-auf").setAttribute("aria-expanded", offen ? "true" : "false");
    document.body.classList.toggle("ebenen-offen", offen);
  }

  function zeigeDatenstand() {
    var z = DS.status_zaehlung, b = DS.status_bedeutung;
    var status = Object.keys(z).map(function (k) { return z[k] + " " + (b[k] || ("Status " + k)); }).join(", ");
    var stand = aktiverMonat && geladen[aktiverMonat];
    var zeilen = [
      ["Zeitleiste", DS.angezeigt.length ? DS.angezeigt.length + " Monate auswählbar; " + leistenBereiche().join("; ") : "kein Monat"],
      ["Würfel", DS.monate_gesamt + " Monate (" + (DS.zeitraum_offen || "vor 2023") + "): " + status],
      ["Gesperrt", "2023–2025 (Validierungs- und Endtestzeitraum): weder auswählbar noch angezeigt, auch nicht mitgezählt"],
      ["Feld", DS.feld],
      ["Quelle", DS.quelle],
      ["Evidenzstufe", DS.evidenzstufe || "beobachtet"],
      ["Einheiten", EH && EH.verfuegbar ? "Natural Earth 5.1.1 (Umrisse), UN M49, sondereinheiten.yaml; Tabelle erstellt " + EH.erstellt_utc : "nicht angezeigt"],
      ["Export", DS.erstellt_utc]
    ];
    if (stand) {
      var st = stand.meta.statistik, f = function (x) { return x.toLocaleString("de-DE"); };
      zeilen.push(["Zellen " + aktiverMonat, f(st.zellen_mit_wert) + " mit Wert, " + f(st.zellen_keine_daten) + " keine Daten, " +
        f(st.zellen_datenlage_unzureichend) + " zu wenig Messungen, " + f(st.zellen_nicht_geladen || 0) +
        " noch nicht geladen (von " + f(st.zellen_gesamt) + ")" +
        (st.zellen_oben_begrenzt ? "; " + f(st.zellen_oben_begrenzt) + " an der Obergrenze abgeschnitten" : "")]);
      zeilen.push(["Selbsttest", "Kontrollzellen stimmen; " + stand.pruefText]);
    }
    byId("datenstand").innerHTML = "<dl>" + zeilen.map(function (r) { return "<dt>" + esc(r[0]) + "</dt><dd>" + esc(r[1]) + "</dd>"; }).join("") + "</dl>";

    // Kurzfassung, immer sichtbar in der Zeitleiste
    byId("quelle-zeile").innerHTML = "Quelle: <b>NASA VIIRS Black Marble VNP46A3</b> (LAADS DAAC) · Evidenzstufe <b>" +
      esc(DS.evidenzstufe || "beobachtet") + "</b> · Datenstand " + esc(DS.erstellt_utc.replace("T", " ").replace("Z", " UTC")) +
      " · 2023–2025 gesperrt";
  }

  function baueSonderListe() {
    var sonder = EH.geojson.features.filter(function (f) { return f.properties.sondereinheit; });
    byId("anzahl-sonder").textContent = sonder.length;
    var gruppen = ["besetzt/Konfliktzone", "umstritten", "Sonderstatus/autonom"];
    var html = "";
    gruppen.forEach(function (g) {
      var liste = sonder.filter(function (f) { return f.properties.hauptkategorie === g; })
        .sort(function (a, b) { return a.properties.name.localeCompare(b.properties.name, "de"); });
      if (!liste.length) return;
      html += '<div class="listen-kopf"><span class="kat-strich" style="color:' + FARBE_KATEGORIE[g] + '"></span>' + esc(g) + " (" + liste.length + ")</div>";
      liste.forEach(function (f) {
        html += '<button class="listen-eintrag" data-id="' + esc(f.properties.einheit_id) + '">' + esc(f.properties.name) + "</button>";
      });
    });
    byId("sonder-liste").innerHTML = html;
    byId("sonder-liste").addEventListener("click", function (e) {
      var id = e.target.getAttribute("data-id");
      if (id) springeZuEinheit(id);
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
  baueVergleichsLegende();
  zeigeDatenstand();

  var h = hashWerte();
  if (h.blick) {
    var b = h.blick.split(",").map(Number);
    map.jumpTo({ center: [b[0], b[1]], zoom: b[2] || 3 });
  }
  if (h.leiste === "1") setzeEbenenLeiste(true);

  byId("ebenen-auf").addEventListener("click", function () { setzeEbenenLeiste(!byId("ebenen-panel").classList.contains("is-open")); });
  byId("ebenen-zu").addEventListener("click", function () { setzeEbenenLeiste(false); });
  byId("blick-erde").addEventListener("click", function () { map.easeTo({ center: START_BLICK.center, zoom: START_BLICK.zoom, bearing: 0, pitch: 0, duration: 900 }); });
  byId("an-nachtlicht").addEventListener("change", function (e) {
    nachtlichtSichtbar = e.target.checked;
    if (map.getLayer("nachtlicht")) map.setLayoutProperty("nachtlicht", "visibility", nachtlichtSichtbar ? "visible" : "none");
  });
  byId("an-grenzen").addEventListener("change", function (e) { setzeGrenzenSichtbar(e.target.checked); });
  byId("monat-regler").addEventListener("input", function (e) {
    spiele(false);
    var i = Number(e.target.value), jetzt = leistenIndex(aktiverMonat);
    if (LEISTE[i] && LEISTE[i].monat !== aktiverMonat) waehleIndex(i, i >= jetzt ? 1 : -1);
  });
  byId("monat-zurueck").addEventListener("click", function () {
    spiele(false);
    waehleIndex(leistenIndex(aktiverMonat) - 1, -1);
  });
  byId("monat-vor").addEventListener("click", function () {
    spiele(false);
    waehleIndex(leistenIndex(aktiverMonat) + 1, 1);
  });
  byId("abspielen").addEventListener("click", function () { spiele(!spielt); });
  API.spiele = function (an) { spiele(!!an); };
  byId("info-zu").addEventListener("click", schliesseDossier);
  byId("vergleich-an").addEventListener("change", function (e) {
    vergleichAn = e.target.checked;
    if (aktiverMonat) setzeMonat(aktiverMonat);
  });
  API.vergleich = function (an) { vergleichAn = !!an; return aktiverMonat ? setzeMonat(aktiverMonat) : Promise.resolve(); };
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape" || e.target.id === "suche-einheit") return;
    if (byId("info").classList.contains("is-open")) schliesseDossier();
    else setzeEbenenLeiste(false);
  });

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

    // Quellenzeile der Karte nur als (i)-Knopf: Die Quelle steht fest in der Zeitleiste,
    // die ausgeklappte Zeile würde sonst in die Zeitleiste ragen.
    var attrib = document.querySelector(".maplibregl-ctrl-attrib");
    if (attrib) { attrib.classList.remove("maplibregl-compact-show"); attrib.removeAttribute("open"); }

    // Grund des Globus: überall "keine Daten", bis ein gemessenes Bild darüber liegt
    // (auch die Polkappen über 85°, die das Mercator-Bild nicht abdeckt).
    map.addImage("keine-daten", schraffurBild());
    map.setPaintProperty("raum", "background-pattern", "keine-daten");

    // Einheiten – oder deutlich sagen, warum keine Grenzen gezeigt werden.
    if (EH && EH.verfuegbar) {
      einheitenEinbauen();
    } else {
      var grund = "Keine Ländergrenzen angezeigt: " + (EH ? EH.grund : "Datei daten/einheiten.js fehlt") +
        ". Ohne vollständige Einheitentabelle zeigt ALEPH absichtlich auch keine Standardgrenzen (sonst würden z. B. umstrittene Gebiete einem Staat zugeschlagen).";
      var hin = byId("einheiten-hinweis");
      hin.className = "hinweis hinweis--stark";
      hin.textContent = grund;
      hin.hidden = false;
      byId("einheiten-legende").innerHTML = '<div class="legende-trenner">Einheiten</div><div class="hinweis hinweis--stark">' + esc(grund) + "</div>";
      byId("block-einheiten").hidden = true;
      byId("an-grenzen").disabled = true;
      byId("an-grenzen").checked = false;
      byId("suche-einheit").disabled = true;
      byId("suche-einheit").placeholder = "Suche nicht verfügbar (keine Einheitentabelle)";
    }

    // Nachtlicht – nur Monate, die der Export als fertig ausgegeben hat.
    if (!DS.angezeigt.length) {
      var hn = byId("nachtlicht-hinweis");
      hn.className = "dock-hinweis dock-hinweis--stark";
      hn.innerHTML = "<b>Noch kein Nachtlicht-Monat vollständig geladen.</b> Nachtlicht wird deshalb nicht angezeigt; der Globus trägt überall das Muster „keine Daten“. " +
        "Im Würfel: " + esc(Object.keys(DS.status_zaehlung).map(function (k) { return DS.status_zaehlung[k] + " × " + (DS.status_bedeutung[k] || k); }).join(", ")) +
        ". Sobald ein Monat fertig ist: „Globus aktualisieren.command“ doppelklicken.";
      hn.hidden = false;
      byId("an-nachtlicht").checked = false;
      byId("an-nachtlicht").disabled = true;
    } else {
      baueMonatWahl();
      var start = (h.monat && DS.angezeigt.indexOf(h.monat) >= 0) ? h.monat
        : (DS.angezeigt.filter(function (m) { return m.indexOf("2018") === 0; })[0] || DS.angezeigt[0]);
      if (h.vergleich === "1") vergleichAn = true;
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
        window.ALEPH_BEREIT_MS = Math.round(performance.now()); // für scripts/globus_startzeit.py
        document.body.setAttribute("data-bereit", "1");
        document.dispatchEvent(new CustomEvent("aleph-bereit", { detail: h }));
      });
    });
  });
})();
