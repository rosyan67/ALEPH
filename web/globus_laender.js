/*
 * ALEPH – Land anklicken: Nachtlicht und Weltbank nebeneinander (Teil 3a, 2026-09-28)
 *
 * Liest nur daten/laender.js (aleph/export/globus_laender.py). Es wird nichts gerechnet und
 * KEIN Zusammenhang behauptet: Links steht das gemessene Nachtlicht des gewählten Monats
 * (Summe und je km², mit Abdeckung), rechts stehen Weltbank-Werte des Kalenderjahres dieses Monats.
 * Weltbank-Werte ab 2023 werden nie gezeigt (gesperrter Zeitraum), auch wenn sie in der Datei stünden.
 */
(function () {
  "use strict";

  var G = window.ALEPH_GLOBUS, L = window.ALEPH_LAENDER;
  if (!G) return;
  var esc = G.esc;
  var GESPERRT_AB_JAHR = 2023;

  function de(x, stellen) {
    return Number(x).toLocaleString("de-DE", { maximumFractionDigits: stellen == null ? 2 : stellen });
  }
  function geld(x) {
    if (x >= 1e12) return de(x / 1e12, 2) + " Bio. US-$";
    if (x >= 1e9) return de(x / 1e9, 1) + " Mrd. US-$";
    if (x >= 1e6) return de(x / 1e6, 1) + " Mio. US-$";
    return de(x, 0) + " US-$";
  }
  function menschen(x) {
    if (x >= 1e9) return de(x / 1e9, 2) + " Mrd.";
    if (x >= 1e6) return de(x / 1e6, 1) + " Mio.";
    return de(x, 0);
  }

  function zeile(label, wert, fuss) {
    return '<div class="lw-zeile"><div class="lw-label">' + label + '</div><div class="lw-wert">' + wert + "</div>" +
      (fuss ? '<div class="lw-fuss">' + fuss + "</div>" : "") + "</div>";
  }

  function lichtSpalte(w, monat, bezug) {
    var inhalt;
    if (!w) {
      inhalt = zeile("Nachtlicht", '<span class="inv-leer">keine Angabe</span>');
    } else if (w.licht_summe == null) {
      inhalt = zeile("Lichtsumme", '<span class="lw-fehlt">keine Landessumme</span>',
        "Nur " + w.abdeckung_prozent + " % der Fläche mit gültiger Messung (Grenze 90 %). Fehlende Zellen werden nie als 0 gezählt.");
    } else {
      inhalt = zeile("Lichtsumme", esc(de(w.licht_summe, 0)), "nW·cm⁻²·sr⁻¹ × km²") +
        zeile("je km²", esc(de(w.licht_je_km2, 3)), "nW·cm⁻²·sr⁻¹") +
        zeile("Abdeckung", w.abdeckung_prozent + " % der Fläche", w.abdeckung_prozent < 100 ? "Summe ist eine Untergrenze: fehlende Zellen fehlen." : "");
    }
    return '<div class="lw-spalte"><div class="lw-kopf">Nachtlicht ' + esc(monat) + ' <span class="inv-evidenz">beobachtet</span></div>' +
      inhalt + '<div class="lw-quelle">NASA VIIRS Black Marble VNP46A3 · ' + esc(bezug) + "</div></div>";
  }

  function wbWert(e, art) {
    if (!e || !e[art]) return '<span class="inv-leer">keine Angabe</span>';
    if (e[art].nicht_verwenden) return '<span class="lw-fehlt">nicht verwendet</span>';
    if (e[art].wert == null) return '<span class="inv-leer">kein Wert</span>';
    var t = art === "bevoelkerung" ? menschen(e[art].wert) : geld(e[art].wert);
    return esc(t) + (e[art].vorlaeufig ? ' <span class="lw-klein">(vorläufig)</span>' : "");
  }

  function weltbankSpalte(code, jahr) {
    var wb = L.weltbank, land = wb.werte[code];
    var kopf = '<div class="lw-kopf">Weltbank ' + esc(jahr) + "</div>";
    if (jahr >= GESPERRT_AB_JAHR || wb.jahre.indexOf(jahr) < 0) {
      return '<div class="lw-spalte">' + kopf + zeile("Werte", '<span class="inv-leer">für dieses Jahr nicht angezeigt</span>') + "</div>";
    }
    if (!land) {
      return '<div class="lw-spalte">' + kopf + zeile("Werte", '<span class="inv-leer">kein Weltbank-Eintrag ' + esc(code) + "</span>") + "</div>";
    }
    var e = land.jahre[String(jahr)] || {};
    var fussPk = e.bip_pro_kopf_real && e.bip_pro_kopf_real.nicht_verwenden
      ? "Weltbank-Nenner passt hier nicht zur Bevölkerungsreihe (ALEPH-Weltbank-Tabelle)." : "konstante Preise, Basisjahr 2015";
    return '<div class="lw-spalte">' + kopf +
      zeile("reales BIP", wbWert(e, "bip_real"), "NY.GDP.MKTP.KD · konstante Preise, Basisjahr 2015") +
      zeile("BIP pro Kopf", wbWert(e, "bip_pro_kopf_real"), "NY.GDP.PCAP.KD · " + fussPk) +
      zeile("Bevölkerung", wbWert(e, "bevoelkerung"), "SP.POP.TOTL · Jahresmitte") +
      '<div class="lw-quelle">' + esc(wb.quelle) + ", Jahr " + esc(jahr) + ", abgerufen " + esc(String(wb.abruf_utc).slice(0, 10)) + "</div></div>";
  }

  function kennzeichen(w, code) {
    var b = [];
    if (!w) return "";
    var gebiet = w.gebiet_weltbank;
    if (gebiet === "abweichend") b.push('<span class="lw-marke lw-marke--rot">Gebiet der Weltbank-Zahl weicht ab</span>');
    else if (gebiet === "unklar") b.push('<span class="lw-marke">Gebiet der Weltbank-Zahl unklar</span>');
    if (w.abdeckung_prozent != null && w.abdeckung_prozent < 90) b.push('<span class="lw-marke lw-marke--rot">geringe Abdeckung (' + w.abdeckung_prozent + " %)</span>");
    var text = w.kennzeichen ? '<div class="lw-kennzeichen">' + esc(w.kennzeichen) + "</div>" : "";
    return (b.length ? '<div class="lw-marken">' + b.join("") + "</div>" : "") + text;
  }

  function dossierFeld(p) {
    if (!L || !L.verfuegbar) {
      return L ? '<div class="hinweis">Länderwerte nicht verfügbar: ' + esc(L.grund) + "</div>" : "";
    }
    var monat = G.aktiverMonat();
    if (!monat || !L.monate[monat]) return "";
    var jahr = Number(monat.slice(0, 4));
    var code = p.weltbank_code;
    var kopf = '<div class="lw-box"><div class="lw-titel">Nachtlicht und Wirtschaftsleistung</div>' +
      '<div class="lw-warnung">Nebeneinander gestellt, kein Zusammenhang behauptet.</div>';
    if (!code) {
      var u = L.monate[monat].einheit[p.einheit_id];
      return kopf + '<div class="lw-spalten">' + lichtSpalte(u, monat, "diese Einheit") +
        '<div class="lw-spalte"><div class="lw-kopf">Weltbank ' + esc(jahr) + "</div>" +
        zeile("Werte", '<span class="inv-leer">keine eigene Weltbank-Zahl für diese Einheit</span>') + "</div></div></div>";
    }
    var w = L.monate[monat].land[code];
    var name = (L.weltbank.werte[code] || {}).name || code;
    var hinweisSicht = p.ebene && String(p.ebene).indexOf("Sondereinheit") === 0
      ? '<div class="lw-kennzeichen">Diese Sondereinheit zählt in der Weltbank-Sicht zu ' + esc(name) + " (" + esc(code) +
        "). Beide Spalten gelten für das ganze Weltbank-Land, nicht nur für diese Einheit.</div>"
      : "";
    return kopf + hinweisSicht + kennzeichen(w, code) + '<div class="lw-spalten">' +
      lichtSpalte(w, monat, "Weltbank-Land " + name + " (" + code + ")") + weltbankSpalte(code, jahr) + "</div>" +
      '<div class="lw-methode">Licht: Summe gemessener Strahldichte über die Fläche des Weltbank-Landes (Sicht „' + esc(L.sicht) +
      "“), Grenzzellen nach Flächenanteil verteilt. Ein Monat gegen einen Jahreswert: nur zum Nebeneinanderlegen.</div></div>";
  }

  G.dossierZusatz.push(dossierFeld);
})();
