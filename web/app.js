/*
 * ALEPH – Oberflächen-Gerüst (Woche 2, ARCHITECTURE.md Abschnitt 10)
 *
 * Alles auf dieser Seite ist Beispieldaten (web/beispieldaten/*.js). Es gibt
 * noch keine echte Anomalieerkennung – dieses Skript testet nur, ob Globus,
 * flache Karte, Suche, Filter, Liste/Detailansicht und Mehrfachauswahl wie
 * vorgesehen funktionieren.
 *
 * Wichtige Regel (Rückmeldung 2026-09-22): Eine Anomalie ist immer
 * "beobachtet" (Abschnitt 7). Höhere Evidenzstufen gehören zu Verknüpfungen
 * mit einer Theorie (Abschnitt 8) oder zu Projektionen (eigene Datei,
 * niemals Anomalien) – siehe beispiel_projektionen.js.
 *
 * Kombinationsfilter (Rückmeldung 2026-09-23): Ein "UND"-Treffer zwischen
 * Datenquellen ist KEINE geprüfte Verknüpfung, sondern nur ein zeitliches
 * und räumliches Zusammenfallen – Evidenzstufe "beobachtet" (Koinzidenz,
 * Abschnitt 8). Zeitfenster und räumliche Regel sind Einstellungen
 * (#komb-fenster, #komb-regel), nicht im Code fest verdrahtet.
 *
 * Flache Karte / Equal Earth (Rückmeldung 2026-09-23): MapLibre GL JS kennt
 * nur "mercator" und "globe" (beide auf Web-Mercator-Kacheln aufgebaut) –
 * keine Equal-Earth-Unterstützung. Die flache Ansicht läuft deshalb über
 * OpenLayers, das Rasterquellen automatisch in eine andere Projektion
 * umrechnen kann (siehe "Flache Karte" weiter unten). Der Globus bleibt
 * unverändert MapLibre.
 */
(function () {
  "use strict";

  var EPOCH_YEAR = 2013;
  var STAERKE_RANK = { "auffällig": 1, "stark": 2, "extrem": 3 };
  var STAERKE_SORT = { "extrem": 0, "stark": 1, "auffällig": 2 };
  var STAERKE_FARBE = {
    "auffällig": "#e2b04f",
    "stark": "#d9822f",
    "extrem": "#c14a34"
  };
  var DATENLAGE_INFO = {
    "gut": { text: "gut – Basislinie und Beobachtungen ausreichend", farbe: "#4a8f89" },
    "mittel": { text: "mittel – eingeschränkte Basislinie oder lückenhafte Beobachtungen", farbe: "#d9a441" },
    "dünn": { text: "dünn – Aussage unsicher, wenige gültige Beobachtungen", farbe: "#8a5a52" }
  };
  var EVIDENZ_TEXT = {
    "beobachtet": "Ereignisse fallen zeitlich/räumlich zusammen, Theorie dazu noch nicht geprüft (Koinzidenz).",
    "statistische Assoziation": "Theorie an unabhängigen Testdaten bestätigt (Abschnitt 8).",
    "Modellprojektion": "Aus bestätigten Zusammenhängen abgeleitete Entwicklung, mit dokumentierten Annahmen.",
    "hypothetisches Szenario": "Was-wäre-wenn – Annahme über die Zukunft, ausdrücklich keine Vorhersage."
  };
  // Okabe-Ito-Palette: für die meisten Formen von Farbenblindheit
  // unterscheidbar. Zusätzlich bekommt jede Auswahl eine Nummer, damit die
  // Unterscheidung nicht allein von der Farbe abhängt.
  var AUSWAHL_FARBEN = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"];
  var QUELLEN = [
    { key: "nachtlicht", label: "Nachtlicht" },
    { key: "vegetation", label: "Vegetation" },
    { key: "brände", label: "Brände" },
    { key: "no2", label: "Luftqualität (NO₂)" },
    { key: "niederschlag", label: "Niederschlag" },
    { key: "schiffsverkehr", label: "Schiffsverkehr" }
  ];

  var anomalien = window.ALEPH_BEISPIEL_ANOMALIEN;
  var theorien = window.ALEPH_BEISPIEL_THEORIEN;
  var orte = window.ALEPH_ORTE;
  var projektionen = window.ALEPH_BEISPIEL_PROJEKTIONEN;
  var datenverfuegbarkeit = window.ALEPH_BEISPIEL_DATENVERFUEGBARKEIT;

  function monthIndex(ym) {
    var parts = ym.split("-");
    var y = parseInt(parts[0], 10);
    var m = parseInt(parts[1], 10);
    return (y - EPOCH_YEAR) * 12 + (m - 1);
  }

  function monthLabel(idx) {
    var y = EPOCH_YEAR + Math.floor(idx / 12);
    var m = (idx % 12) + 1;
    return y + "-" + String(m).padStart(2, "0");
  }

  function parseMonthInput(str) {
    var m = /^\s*(\d{4})-(\d{2})\s*$/.exec(String(str));
    if (!m) return null;
    var mo = parseInt(m[2], 10);
    if (mo < 1 || mo > 12) return null;
    return monthIndex(m[1] + "-" + m[2]);
  }

  function centroid(polygonCoords) {
    var ring = polygonCoords[0];
    var sx = 0, sy = 0;
    for (var i = 0; i < ring.length - 1; i++) {
      sx += ring[i][0];
      sy += ring[i][1];
    }
    var n = ring.length - 1;
    return [sx / n, sy / n];
  }

  function haversineKm(a, b) {
    var R = 6371;
    var lat1 = (a[1] * Math.PI) / 180, lat2 = (b[1] * Math.PI) / 180;
    var dLat = ((b[1] - a[1]) * Math.PI) / 180;
    var dLon = ((b[0] - a[0]) * Math.PI) / 180;
    var x = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    var y = 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
    return R * y;
  }

  function polygonRadiusKm(f) {
    var c = centroid(f.geometry.coordinates);
    var ring = f.geometry.coordinates[0];
    var max = 0;
    for (var i = 0; i < ring.length - 1; i++) {
      var d = haversineKm(c, ring[i]);
      if (d > max) max = d;
    }
    return max;
  }

  function byId(id) { return document.getElementById(id); }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // "Heute" wird beim Laden aus dem tatsächlichen Datum berechnet, nicht
  // fest eingetragen – damit die Zeitachse auch später noch richtig teilt.
  var now = new Date();
  var HEUTE_INDEX = (now.getFullYear() - EPOCH_YEAR) * 12 + now.getMonth();

  // ---------- Karte (Globus, MapLibre) ----------

  var map = new maplibregl.Map({
    container: "map",
    center: [15, 20],
    zoom: 1.2,
    minZoom: 0.4,
    maxZoom: 9,
    attributionControl: { compact: true },
    style: {
      version: 8,
      projection: { type: "globe" },
      // Für die Nummern-Beschriftung der Mehrfachauswahl nötig (Symbol-Layer).
      glyphs: "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
      // Kein "light"/"sky" mit Richtung, damit keine Beleuchtung einen
      // Sonnenstand andeutet (Rückmeldung 2026-09-22) – beide Basiskarten
      // sind fertige Kompositen, keine in Echtzeit beleuchtete 3D-Szene.
      sources: {
        "eox-night": {
          type: "raster",
          tiles: [
            "https://tiles.maps.eox.at/wmts/1.0.0/blackmarble_3857/default/g/{z}/{y}/{x}.jpg"
          ],
          tileSize: 256,
          attribution:
            '© <a href="https://maps.eox.at" target="_blank" rel="noopener">EOX IT Services</a> – Nachtlicht-Komposit: NASA Black Marble (VIIRS)'
        },
        "eox-day": {
          type: "raster",
          tiles: [
            "https://tiles.maps.eox.at/wmts/1.0.0/bluemarble_3857/default/g/{z}/{y}/{x}.jpg"
          ],
          tileSize: 256,
          attribution:
            '© <a href="https://maps.eox.at" target="_blank" rel="noopener">EOX IT Services</a> – Tageskomposit: NASA Blue Marble'
        },
        "eox-overlay": {
          type: "raster",
          tiles: [
            "https://tiles.maps.eox.at/wmts/1.0.0/overlay_3857/default/g/{z}/{y}/{x}.png"
          ],
          tileSize: 256
        }
      },
      layers: [
        { id: "void", type: "background", paint: { "background-color": "#070a12" } },
        { id: "basemap-night", type: "raster", source: "eox-night" },
        { id: "basemap-day", type: "raster", source: "eox-day", layout: { visibility: "none" } },
        { id: "overlay", type: "raster", source: "eox-overlay", paint: { "raster-opacity": 0.5 } }
      ]
    }
  });

  // Kein GlobeControl (MapLibre-eigener Globus/Mercator-Umschalter) mehr:
  // Die flache Ansicht läuft jetzt über die eigene "Flache Karte" (Equal
  // Earth, siehe unten), nicht über MapLibres Mercator-Modus. Der Globus
  // bleibt fest auf "globe".
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");

  // ---------- Basiskarte umschalten (Nachtlicht / Tag) ----------

  var basemapToggle = byId("basemap-toggle");
  var basemapHint = byId("basemap-hint");
  var basemapMode = "nacht";

  function setBasemap(mode) {
    basemapMode = mode;
    if (map.getLayer("basemap-night")) {
      map.setLayoutProperty("basemap-night", "visibility", mode === "nacht" ? "visible" : "none");
      map.setLayoutProperty("basemap-day", "visibility", mode === "tag" ? "visible" : "none");
    }
    if (olLayerNight) {
      olLayerNight.setVisible(mode === "nacht");
      olLayerDay.setVisible(mode === "tag");
    }
    basemapToggle.textContent = mode === "nacht" ? "Tagkarte" : "Nachtkarte";
    basemapToggle.setAttribute("aria-pressed", mode === "tag" ? "true" : "false");
    basemapHint.textContent = mode === "nacht"
      ? "Nachtlicht-Komposit (Jahresmittel), keine Echtzeit"
      : "Tageskomposit (NASA Blue Marble, Jahresmittel), keine Echtzeit";
  }
  basemapToggle.addEventListener("click", function () {
    setBasemap(basemapMode === "nacht" ? "tag" : "nacht");
  });

  var hoverPopup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 8 });

  // Aktuell sichtbare (gefilterte) Features und Kombinationsfilter-Infos –
  // von applyFilters() gepflegt, von der Liste und beiden Karten gelesen.
  var aktuellGefiltert = anomalien.features.slice();
  var aktuellKombInfo = {};
  var ausgewaehlt = []; // ids, für die Mehrfachauswahl/den Vergleich

  map.on("load", function () {
    map.setProjection({ type: "globe" });
    setBasemap("nacht");

    map.addSource("anomalien", {
      type: "geojson",
      data: anomalien,
      generateId: true
    });

    map.addLayer({
      id: "anomalien-fill",
      type: "fill",
      source: "anomalien",
      paint: {
        "fill-color": [
          "match", ["get", "staerke_band"],
          "auffällig", STAERKE_FARBE["auffällig"],
          "stark", STAERKE_FARBE["stark"],
          "extrem", STAERKE_FARBE["extrem"],
          "#e2b04f"
        ],
        "fill-opacity": 0.38
      }
    });

    map.addLayer({
      id: "anomalien-linie",
      type: "line",
      source: "anomalien",
      paint: {
        "line-color": [
          "match", ["get", "staerke_band"],
          "auffällig", STAERKE_FARBE["auffällig"],
          "stark", STAERKE_FARBE["stark"],
          "extrem", STAERKE_FARBE["extrem"],
          "#e2b04f"
        ],
        "line-width": 1.4,
        "line-opacity": 0.9
      }
    });

    map.addLayer({
      id: "anomalien-fokus",
      type: "line",
      source: "anomalien",
      filter: ["==", ["get", "fokusgebiet"], true],
      paint: {
        "line-color": "#f0c876",
        "line-width": 2.2,
        "line-dasharray": [1.5, 1.5]
      }
    });

    // Mehrfachauswahl: eigene Farbe pro Anomalie (Okabe-Ito, für
    // Farbenblindheit geeignet) plus Nummer, damit nicht nur die Farbe
    // unterscheidet.
    map.addLayer({
      id: "anomalien-auswahl-linie",
      type: "line",
      source: "anomalien",
      filter: ["in", ["get", "id"], ["literal", []]],
      paint: { "line-color": "#ffffff", "line-width": 4, "line-opacity": 0.95 }
    });

    map.addLayer({
      id: "anomalien-auswahl-label",
      type: "symbol",
      source: "anomalien",
      filter: ["in", ["get", "id"], ["literal", []]],
      layout: {
        "text-field": "",
        "text-font": ["Noto Sans Bold"],
        "text-size": 13,
        "text-allow-overlap": true,
        "text-ignore-placement": true
      },
      paint: { "text-color": "#111318", "text-halo-color": "#ffffff", "text-halo-width": 1.6 }
    });

    map.on("mouseenter", "anomalien-fill", function () { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", "anomalien-fill", function () {
      map.getCanvas().style.cursor = "";
      hoverPopup.remove();
    });

    map.on("mousemove", "anomalien-fill", function (e) {
      var f = e.features[0];
      var p = f.properties;
      hoverPopup
        .setLngLat(e.lngLat)
        .setHTML(
          '<div class="map-popup-title">' + escapeHtml(p.name) + "</div>" +
          '<div class="map-popup-sub">' + escapeHtml(p.ort_label) + "</div>"
        )
        .addTo(map);
    });

    map.on("click", "anomalien-fill", function (e) {
      var props = e.features[0].properties;
      showDetail(normalizeProps(props));
    });

    populateQuellenFilter();
    applyFilters();
  });

  function normalizeProps(props) {
    // GeoJSON properties kommen von MapLibre mit JSON-stringifizierten
    // Arrays/Objekten zurück (layer, verknuepfungen).
    var out = {};
    for (var k in props) {
      out[k] = props[k];
    }
    ["layer", "verknuepfungen"].forEach(function (key) {
      if (typeof out[key] === "string") {
        try { out[key] = JSON.parse(out[key]); } catch (e) { out[key] = []; }
      }
    });
    return out;
  }

  // ---------- Flache Karte (OpenLayers, Equal-Earth-Projektion) ----------
  //
  // MapLibre kennt nur "mercator"/"globe" (beide Web-Mercator-Kacheln).
  // OpenLayers kann eine Rasterquelle dagegen automatisch in eine andere
  // Projektion umrechnen (siehe OpenLayers-Tutorial "raster-reprojection"),
  // wenn man ihr die Formel für diese Projektion gibt. Die Formel für Equal
  // Earth (Šavrič/Jenny/Jenny 2018) ist unten von Hand eingetragen und
  // eigenständig auf Rundreise-Genauigkeit getestet (siehe LOG.md).

  var EE_A1 = 1.340264, EE_A2 = -0.081106, EE_A3 = 0.000893, EE_A4 = 0.003796;
  var EE_M = Math.sqrt(3) / 2;
  var EE_ITER = 20;
  var EE_R = 6378137; // gleicher Kugelradius wie Web Mercator – nur für eine vertraute Größenordnung

  function equalEarthForward(lonLat) {
    var lambda = (lonLat[0] * Math.PI) / 180;
    var phi = (lonLat[1] * Math.PI) / 180;
    var theta = Math.asin(EE_M * Math.sin(phi));
    var theta2 = theta * theta;
    var theta6 = theta2 * theta2 * theta2;
    var denom = EE_M * (EE_A1 + 3 * EE_A2 * theta2 + theta6 * (7 * EE_A3 + 9 * EE_A4 * theta2));
    var x = (lambda * Math.cos(theta)) / denom;
    var y = theta * (EE_A1 + EE_A2 * theta2 + theta6 * (EE_A3 + EE_A4 * theta2));
    return [x * EE_R, y * EE_R];
  }

  function equalEarthInverse(xy) {
    var x = xy[0] / EE_R, y = xy[1] / EE_R;
    var theta = y;
    for (var i = 0; i < EE_ITER; i++) {
      var theta2 = theta * theta;
      var theta6 = theta2 * theta2 * theta2;
      var fTheta = theta * (EE_A1 + EE_A2 * theta2 + theta6 * (EE_A3 + EE_A4 * theta2)) - y;
      var fPrime = EE_A1 + 3 * EE_A2 * theta2 + theta6 * (7 * EE_A3 + 9 * EE_A4 * theta2);
      var delta = fTheta / fPrime;
      theta -= delta;
      if (Math.abs(delta) < 1e-12) break;
    }
    var theta2 = theta * theta;
    var theta6 = theta2 * theta2 * theta2;
    var denom = EE_M * (EE_A1 + 3 * EE_A2 * theta2 + theta6 * (7 * EE_A3 + 9 * EE_A4 * theta2));
    var lambda = (x * denom) / Math.cos(theta);
    var phi = Math.asin(Math.sin(theta) / EE_M);
    return [(lambda * 180) / Math.PI, (phi * 180) / Math.PI];
  }

  var aktiveAnsicht = "globus"; // "globus" | "flach"
  var olMap = null;
  var olEqualEarthProj = null;
  var olAnomalienSource = null;
  var olAuswahlSource = null;
  var olLayerNight = null, olLayerDay = null;
  var olGeoJsonFormat = null;

  function ensureFlatMap() {
    if (olMap) return;

    var eeExtent = (function () {
      var xMax = equalEarthForward([180, 0])[0];
      var yMax = equalEarthForward([0, 90])[1];
      return [-xMax, -yMax, xMax, yMax];
    })();

    olEqualEarthProj = new ol.proj.Projection({
      code: "ALEPH:equalearth",
      units: "m",
      extent: eeExtent
    });
    ol.proj.addProjection(olEqualEarthProj);
    ol.proj.addCoordinateTransforms(
      "EPSG:4326",
      olEqualEarthProj,
      function (coord) { return equalEarthForward(coord); },
      function (coord) { return equalEarthInverse(coord); }
    );

    olLayerNight = new ol.layer.Tile({
      source: new ol.source.XYZ({
        url: "https://tiles.maps.eox.at/wmts/1.0.0/blackmarble_3857/default/g/{z}/{y}/{x}.jpg",
        projection: "EPSG:3857",
        attributions: '© EOX IT Services – Nachtlicht-Komposit: NASA Black Marble (VIIRS)'
      }),
      visible: basemapMode === "nacht"
    });
    olLayerDay = new ol.layer.Tile({
      source: new ol.source.XYZ({
        url: "https://tiles.maps.eox.at/wmts/1.0.0/bluemarble_3857/default/g/{z}/{y}/{x}.jpg",
        projection: "EPSG:3857",
        attributions: '© EOX IT Services – Tageskomposit: NASA Blue Marble'
      }),
      visible: basemapMode === "tag"
    });
    var olLayerOverlay = new ol.layer.Tile({
      source: new ol.source.XYZ({
        url: "https://tiles.maps.eox.at/wmts/1.0.0/overlay_3857/default/g/{z}/{y}/{x}.png",
        projection: "EPSG:3857"
      }),
      opacity: 0.5
    });

    olGeoJsonFormat = new ol.format.GeoJSON();
    olAnomalienSource = new ol.source.Vector();
    olAuswahlSource = new ol.source.Vector();

    function olStaerkeFarbe(feature) {
      return STAERKE_FARBE[feature.get("staerke_band")] || "#e2b04f";
    }

    var olLayerAnomalien = new ol.layer.Vector({
      source: olAnomalienSource,
      style: function (feature) {
        var farbe = olStaerkeFarbe(feature);
        var styles = [new ol.style.Style({
          fill: new ol.style.Fill({ color: farbe + "61" }), // ~38% Deckkraft, wie auf dem Globus
          stroke: new ol.style.Stroke({ color: farbe, width: 1.4 })
        })];
        if (feature.get("fokusgebiet")) {
          styles.push(new ol.style.Style({
            stroke: new ol.style.Stroke({ color: "#f0c876", width: 2.2, lineDash: [5, 5] })
          }));
        }
        return styles;
      }
    });

    var olLayerAuswahl = new ol.layer.Vector({
      source: olAuswahlSource,
      style: function (feature) {
        return new ol.style.Style({
          stroke: new ol.style.Stroke({ color: feature.get("auswahlFarbe"), width: 4 }),
          text: new ol.style.Text({
            text: String(feature.get("auswahlNummer")),
            font: "bold 13px 'IBM Plex Sans', sans-serif",
            fill: new ol.style.Fill({ color: "#111318" }),
            stroke: new ol.style.Stroke({ color: "#ffffff", width: 3 })
          })
        });
      }
    });

    olMap = new ol.Map({
      target: "map-flat",
      layers: [olLayerNight, olLayerDay, olLayerOverlay, olLayerAnomalien, olLayerAuswahl],
      view: new ol.View({
        projection: olEqualEarthProj,
        center: [0, 0],
        extent: eeExtent,
        zoom: 2
      })
    });
    olMap.getView().fit(eeExtent, { size: olMap.getSize(), padding: [90, 24, 132, 24] });

    olMap.on("pointermove", function (e) {
      if (e.dragging) return;
      var hit = olMap.hasFeatureAtPixel(e.pixel, { layerFilter: function (l) { return l === olLayerAnomalien; } });
      olMap.getTargetElement().style.cursor = hit ? "pointer" : "";
    });
    olMap.on("click", function (e) {
      olMap.forEachFeatureAtPixel(e.pixel, function (feature) {
        showDetail(feature.getProperties().__props);
        return true;
      }, { layerFilter: function (l) { return l === olLayerAnomalien; } });
    });

    syncFlacheKarteFeatures();
    updateAuswahlLayer();
  }

  function syncFlacheKarteFeatures() {
    if (!olAnomalienSource) return;
    olAnomalienSource.clear();
    aktuellGefiltert.forEach(function (f) {
      var geom = new ol.geom.Polygon(f.geometry.coordinates).transform("EPSG:4326", olEqualEarthProj);
      var feature = new ol.Feature({ geometry: geom });
      feature.setProperties(Object.assign({}, f.properties, { __props: f.properties }));
      olAnomalienSource.addFeature(feature);
    });
  }

  function panTo(lonLat, globusZoom) {
    if (aktiveAnsicht === "globus") {
      map.flyTo({ center: lonLat, zoom: globusZoom, duration: 1400 });
    } else {
      ensureFlatMap();
      olMap.getView().animate({ center: equalEarthForward(lonLat), zoom: 5, duration: 1400 });
    }
  }

  var viewToggle = byId("view-toggle");
  var mapGlobus = byId("map");
  var mapFlach = byId("map-flat");
  viewToggle.addEventListener("click", function () {
    setAnsicht(aktiveAnsicht === "globus" ? "flach" : "globus");
  });

  function setAnsicht(modus) {
    aktiveAnsicht = modus;
    if (modus === "flach") {
      mapGlobus.hidden = true;
      mapFlach.hidden = false;
      ensureFlatMap();
      olMap.updateSize();
      viewToggle.textContent = "Globus";
      viewToggle.setAttribute("aria-pressed", "true");
    } else {
      mapFlach.hidden = true;
      mapGlobus.hidden = false;
      viewToggle.textContent = "Flache Karte";
      viewToggle.setAttribute("aria-pressed", "false");
      map.resize();
    }
  }

  // ---------- Filter ----------

  var filterPanel = byId("filter-panel");
  var filterToggle = byId("filter-toggle");
  var filterClose = byId("filter-close");

  function openFilter() {
    filterPanel.classList.add("is-open");
    filterPanel.setAttribute("aria-hidden", "false");
    filterToggle.setAttribute("aria-expanded", "true");
  }
  function closeFilter() {
    filterPanel.classList.remove("is-open");
    filterPanel.setAttribute("aria-hidden", "true");
    filterToggle.setAttribute("aria-expanded", "false");
  }
  filterToggle.addEventListener("click", function () {
    if (filterPanel.classList.contains("is-open")) closeFilter(); else openFilter();
  });
  filterClose.addEventListener("click", closeFilter);

  // Region- und Typ-Dropdowns aus den Beispieldaten befüllen
  var regionSelect = byId("f-region");
  var typSelect = byId("f-typ");
  (function populateSelects() {
    var regionen = [], typen = [];
    anomalien.features.forEach(function (f) {
      if (regionen.indexOf(f.properties.region) === -1) regionen.push(f.properties.region);
      if (typen.indexOf(f.properties.typ) === -1) typen.push(f.properties.typ);
    });
    regionen.sort().forEach(function (r) {
      var opt = document.createElement("option");
      opt.value = r; opt.textContent = r;
      regionSelect.appendChild(opt);
    });
    typen.sort().forEach(function (t) {
      var opt = document.createElement("option");
      opt.value = t; opt.textContent = t;
      typSelect.appendChild(opt);
    });
  })();

  var staerkeBtns = Array.prototype.slice.call(document.querySelectorAll("#f-staerke .seg-btn"));
  var minStaerke = "auffällig";
  staerkeBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      staerkeBtns.forEach(function (b) { b.classList.remove("is-active"); });
      btn.classList.add("is-active");
      minStaerke = btn.getAttribute("data-value");
      applyFilters();
    });
  });

  var evidenzChecks = Array.prototype.slice.call(document.querySelectorAll("#f-evidenz input"));
  evidenzChecks.forEach(function (cb) { cb.addEventListener("change", applyFilters); });

  var fokusCheck = byId("f-fokus");
  fokusCheck.addEventListener("change", applyFilters);

  regionSelect.addEventListener("change", applyFilters);
  typSelect.addEventListener("change", applyFilters);

  // Kombinationsfilter über Datenquellen (UND/ODER)
  var quellenContainer = byId("f-quellen");
  var quellenChecks = [];
  function populateQuellenFilter() {
    QUELLEN.forEach(function (q) {
      var label = document.createElement("label");
      label.className = "check-row";
      var cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = q.key;
      cb.addEventListener("change", applyFilters);
      label.appendChild(cb);
      label.appendChild(document.createTextNode(" " + q.label));
      quellenContainer.appendChild(label);
      quellenChecks.push(cb);
    });
  }

  var kombModusBtns = Array.prototype.slice.call(document.querySelectorAll("#f-komb-modus .seg-btn"));
  var kombModus = "oder";
  kombModusBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      kombModusBtns.forEach(function (b) { b.classList.remove("is-active"); });
      btn.classList.add("is-active");
      kombModus = btn.getAttribute("data-value");
      applyFilters();
    });
  });

  var kombFensterInput = byId("komb-fenster");
  kombFensterInput.addEventListener("change", applyFilters);
  var kombRegelSelect = byId("komb-regel");
  kombRegelSelect.addEventListener("change", applyFilters);

  // Zeitschieber (von/bis) + Text-Felder + Kartenbild-Pin
  var timeStartInput = byId("time-start");
  var timeEndInput = byId("time-end");
  var timeStartText = byId("time-start-text");
  var timeEndText = byId("time-end-text");
  var timePin = byId("time-pin");
  var pinReadout = byId("tl-pin-readout");
  var rangeFill = byId("range-fill");
  var rangeProjection = byId("range-projection");
  var rangeToday = byId("range-today");

  var TL_MIN = parseInt(timeStartInput.min, 10);
  var TL_MAX = parseInt(timeStartInput.max, 10);

  function pct(idx) { return ((clamp(idx, TL_MIN, TL_MAX) - TL_MIN) / (TL_MAX - TL_MIN)) * 100; }

  function updateRangeUi() {
    var s = parseInt(timeStartInput.value, 10);
    var e = parseInt(timeEndInput.value, 10);
    if (s > e) { s = e; timeStartInput.value = String(s); }
    var pctS = pct(s), pctE = pct(e);
    rangeFill.style.left = pctS + "%";
    rangeFill.style.width = (pctE - pctS) + "%";
    timeStartText.value = monthLabel(s);
    timeEndText.value = monthLabel(e);
  }

  timeStartInput.addEventListener("input", function () {
    if (parseInt(timeStartInput.value, 10) > parseInt(timeEndInput.value, 10)) {
      timeStartInput.value = timeEndInput.value;
    }
    updateRangeUi();
    applyFilters();
  });
  timeEndInput.addEventListener("input", function () {
    if (parseInt(timeEndInput.value, 10) < parseInt(timeStartInput.value, 10)) {
      timeEndInput.value = timeStartInput.value;
    }
    updateRangeUi();
    applyFilters();
  });

  function onTimeTextChange(textInput, rangeInput, otherRangeInput, isStart) {
    var idx = parseMonthInput(textInput.value);
    if (idx === null) {
      textInput.value = monthLabel(parseInt(rangeInput.value, 10));
      return;
    }
    idx = clamp(idx, TL_MIN, TL_MAX);
    var other = parseInt(otherRangeInput.value, 10);
    if (isStart && idx > other) idx = other;
    if (!isStart && idx < other) idx = other;
    rangeInput.value = String(idx);
    updateRangeUi();
    applyFilters();
  }
  timeStartText.addEventListener("change", function () { onTimeTextChange(timeStartText, timeStartInput, timeEndInput, true); });
  timeEndText.addEventListener("change", function () { onTimeTextChange(timeEndText, timeEndInput, timeStartInput, false); });

  updateRangeUi();

  // "heute" und der schraffierte Projektionsbereich (nur Modellprojektion /
  // hypothetisches Szenario, nie Anomalien)
  (function setupTodayAndProjectionZone() {
    var todayPct = pct(HEUTE_INDEX);
    rangeToday.style.left = todayPct + "%";
    if (HEUTE_INDEX < TL_MAX) {
      rangeProjection.style.left = todayPct + "%";
      rangeProjection.style.width = (100 - todayPct) + "%";
      rangeProjection.hidden = false;
    } else {
      rangeProjection.hidden = true;
    }
  })();

  // Kartenbild-Pin: unabhängig vom Zeitraum-Filter, wählt nur, welcher
  // Monat als Hinweistext angezeigt wird. Es gibt noch keine echten
  // Monatsbilder – vorerst bleibt das Kartenbild selbst unverändert.
  function updatePinUi() {
    var idx = parseInt(timePin.value, 10);
    pinReadout.textContent = "Kartenbild-Monat: " + monthLabel(idx) + " – Monatsbilder mit echten Daten folgen; angezeigt wird weiterhin das vorhandene Komposit.";
  }
  timePin.value = String(clamp(HEUTE_INDEX, TL_MIN, TL_MAX));
  timePin.addEventListener("input", updatePinUi);
  updatePinUi();

  byId("filter-reset").addEventListener("click", function () {
    regionSelect.value = "alle";
    typSelect.value = "alle";
    evidenzChecks.forEach(function (cb) { cb.checked = true; });
    fokusCheck.checked = false;
    minStaerke = "auffällig";
    staerkeBtns.forEach(function (b) { b.classList.toggle("is-active", b.getAttribute("data-value") === "auffällig"); });
    quellenChecks.forEach(function (cb) { cb.checked = false; });
    kombModus = "oder";
    kombModusBtns.forEach(function (b) { b.classList.toggle("is-active", b.getAttribute("data-value") === "oder"); });
    kombFensterInput.value = "1";
    timeStartInput.value = timeStartInput.min;
    timeEndInput.value = timeEndInput.max;
    updateRangeUi();
    applyFilters();
  });

  function currentFilterState() {
    var evidenzstufen = evidenzChecks.filter(function (cb) { return cb.checked; }).map(function (cb) { return cb.value; });
    return {
      region: regionSelect.value,
      typ: typSelect.value,
      evidenzstufen: evidenzstufen,
      minStaerke: minStaerke,
      onlyFocus: fokusCheck.checked,
      timeStart: parseInt(timeStartInput.value, 10),
      timeEnd: parseInt(timeEndInput.value, 10),
      kombQuellen: quellenChecks.filter(function (cb) { return cb.checked; }).map(function (cb) { return cb.value; }),
      kombModus: kombModus,
      kombFenster: parseInt(kombFensterInput.value, 10) || 0,
      kombRegel: kombRegelSelect.value
    };
  }

  // Evidenzstufe einer Anomalie ist immer "beobachtet" (Abschnitt 7). Der
  // Filter prüft deshalb die eigene Stufe UND die Stufen aller
  // Verknüpfungen – nur so bleibt "statistische Assoziation" im Filter
  // sinnvoll nutzbar. "Modellprojektion"/"hypothetisches Szenario" treffen
  // hier bewusst nie zu: die kommen nur bei Projektionen vor.
  function evidenzstufenVon(props) {
    var werte = [props.evidenzstufe];
    (props.verknuepfungen || []).forEach(function (v) { werte.push(v.evidenzstufe); });
    return werte;
  }

  function featurePasses(props, state) {
    if (state.region !== "alle" && props.region !== state.region) return false;
    if (state.typ !== "alle" && props.typ !== state.typ) return false;
    var stufen = evidenzstufenVon(props);
    var passtEvidenz = stufen.some(function (s) { return state.evidenzstufen.indexOf(s) !== -1; });
    if (!passtEvidenz) return false;
    if (STAERKE_RANK[props.staerke_band] < STAERKE_RANK[state.minStaerke]) return false;
    if (state.onlyFocus && !props.fokusgebiet) return false;
    var fStart = monthIndex(props.start);
    var fEnde = monthIndex(props.ende);
    if (fEnde < state.timeStart || fStart > state.timeEnd) return false;
    return true;
  }

  // Räumliche/zeitliche Nähe zweier Anomalien für den Kombinationsfilter.
  // "regel" ist absichtlich ein Parameter (aus #komb-regel gelesen) statt
  // fest im Code zu stehen – aktuell ist "gitterzelle-naeherung" die einzige
  // hinterlegte Regel: eine grobe Näherung über sich berührende
  // Umkreise der Anomalie-Polygone. Eine echte gemeinsame Gitterzelle gibt
  // es erst mit den Analyse-Würfeln (Abschnitt 4).
  function raeumlichZeitlichNah(fA, fB, fensterMonate, regel) {
    var aStart = monthIndex(fA.properties.start), aEnde = monthIndex(fA.properties.ende);
    var bStart = monthIndex(fB.properties.start), bEnde = monthIndex(fB.properties.ende);
    var zeitlichNah = bStart <= aEnde + fensterMonate && aStart <= bEnde + fensterMonate;
    if (!zeitlichNah) return false;

    if (regel === "gitterzelle-naeherung" || !regel) {
      var ca = centroid(fA.geometry.coordinates), cb = centroid(fB.geometry.coordinates);
      var d = haversineKm(ca, cb);
      return d <= polygonRadiusKm(fA) + polygonRadiusKm(fB);
    }
    return false;
  }

  // Kombiniert mehrere Datenquellen mit UND/ODER. Gibt die passenden
  // Features zurück sowie pro id einen Hinweis, ob es ein UND-Treffer war
  // (und über welche anderen Anomalien er zustande kam).
  function berechneKombination(features, quellen, modus, fensterMonate, regel) {
    var deckung = features.map(function (f) {
      var q = (f.properties.layer || []).filter(function (l) { return quellen.indexOf(l) !== -1; });
      return { f: f, quellen: q };
    }).filter(function (d) { return d.quellen.length > 0; });

    var info = {};

    if (modus === "oder") {
      deckung.forEach(function (d) {
        info[d.f.properties.id] = { istUnd: false, partner: [] };
      });
      return { treffer: deckung.map(function (d) { return d.f; }), info: info };
    }

    var treffer = [];
    deckung.forEach(function (d) {
      var restQuellen = quellen.filter(function (q) { return d.quellen.indexOf(q) === -1; });
      var partner = [];
      if (restQuellen.length) {
        deckung.forEach(function (d2) {
          if (d2.f === d.f) return;
          if (!raeumlichZeitlichNah(d.f, d2.f, fensterMonate, regel)) return;
          var deckt = d2.quellen.some(function (q) { return restQuellen.indexOf(q) !== -1; });
          if (deckt) partner.push(d2);
        });
      }
      var abgedeckt = restQuellen.every(function (q) {
        return partner.some(function (p) { return p.quellen.indexOf(q) !== -1; });
      });
      if (restQuellen.length === 0 || abgedeckt) {
        treffer.push(d.f);
        info[d.f.properties.id] = {
          istUnd: true,
          partner: partner.map(function (p) { return { id: p.f.properties.id, name: p.f.properties.name, ort: p.f.properties.ort_label }; })
        };
      }
    });
    return { treffer: treffer, info: info };
  }

  function applyFilters() {
    if (!map.getSource("anomalien")) return;
    var state = currentFilterState();
    var attributGefiltert = anomalien.features.filter(function (f) { return featurePasses(f.properties, state); });

    var finalFeatures = attributGefiltert;
    var kombInfo = {};
    if (state.kombQuellen.length) {
      var ergebnis = berechneKombination(attributGefiltert, state.kombQuellen, state.kombModus, state.kombFenster, state.kombRegel);
      finalFeatures = ergebnis.treffer;
      kombInfo = ergebnis.info;
    }

    aktuellGefiltert = finalFeatures;
    aktuellKombInfo = kombInfo;

    map.getSource("anomalien").setData({ type: "FeatureCollection", features: finalFeatures });
    syncFlacheKarteFeatures();
    byId("filter-count").textContent = String(finalFeatures.length);

    renderVerfuegbarkeitStreifen(state.kombQuellen);
    updateAuswahlLayer();
    if (invState === "liste") renderListe();
  }

  // ---------- Rechte Leiste: Liste ↔ Detail ----------

  var investigation = byId("investigation");
  var investigationContent = byId("investigation-content");
  var invBackBtn = byId("investigation-back");
  var invFullscreenBtn = byId("investigation-fullscreen");
  var invCloseBtn = byId("investigation-close");
  var invReopenBtn = byId("investigation-reopen");

  var invState = "liste"; // "liste" | "detail"
  var invFullscreen = false;

  function setPanelOpen(offen) {
    investigation.classList.toggle("is-open", offen);
    investigation.setAttribute("aria-hidden", offen ? "false" : "true");
    invReopenBtn.hidden = offen;
  }

  function verlasseVollbild() {
    invFullscreen = false;
    investigation.classList.remove("is-fullscreen");
    invFullscreenBtn.textContent = "⤢";
    invFullscreenBtn.title = "Vollbild";
  }

  function showListe() {
    invState = "liste";
    invBackBtn.hidden = true;
    invFullscreenBtn.hidden = true;
    verlasseVollbild();
    renderListe();
    setPanelOpen(true);
  }

  function showDetail(props) {
    invState = "detail";
    invBackBtn.hidden = false;
    invFullscreenBtn.hidden = false;
    renderDetail(props);
    setPanelOpen(true);
  }

  invBackBtn.addEventListener("click", showListe);
  invReopenBtn.addEventListener("click", showListe);
  invCloseBtn.addEventListener("click", function () {
    if (invState === "detail") showListe(); else setPanelOpen(false);
  });
  invFullscreenBtn.addEventListener("click", function () {
    invFullscreen = !invFullscreen;
    investigation.classList.toggle("is-fullscreen", invFullscreen);
    invFullscreenBtn.textContent = invFullscreen ? "⤡" : "⤢";
    invFullscreenBtn.title = invFullscreen ? "Vollbild verlassen" : "Vollbild";
  });

  // ---------- Mehrfachauswahl ----------

  function toggleAuswahl(id) {
    var idx = ausgewaehlt.indexOf(id);
    if (idx === -1) ausgewaehlt.push(id); else ausgewaehlt.splice(idx, 1);
    updateAuswahlLayer();
    if (invState === "liste") renderListe();
  }

  function updateAuswahlLayer() {
    if (map.getLayer("anomalien-auswahl-linie")) {
      if (!ausgewaehlt.length) {
        map.setFilter("anomalien-auswahl-linie", ["in", ["get", "id"], ["literal", []]]);
        map.setFilter("anomalien-auswahl-label", ["in", ["get", "id"], ["literal", []]]);
      } else {
        var farbAusdruck = ["match", ["get", "id"]];
        var nummerAusdruck = ["match", ["get", "id"]];
        ausgewaehlt.forEach(function (id, i) {
          var farbe = AUSWAHL_FARBEN[i % AUSWAHL_FARBEN.length];
          farbAusdruck.push(id, farbe);
          nummerAusdruck.push(id, String(i + 1));
        });
        farbAusdruck.push("#ffffff");
        nummerAusdruck.push("");
        map.setFilter("anomalien-auswahl-linie", ["in", ["get", "id"], ["literal", ausgewaehlt]]);
        map.setFilter("anomalien-auswahl-label", ["in", ["get", "id"], ["literal", ausgewaehlt]]);
        map.setPaintProperty("anomalien-auswahl-linie", "line-color", farbAusdruck);
        map.setLayoutProperty("anomalien-auswahl-label", "text-field", nummerAusdruck);
      }
    }

    if (olAuswahlSource) {
      olAuswahlSource.clear();
      ausgewaehlt.forEach(function (id, i) {
        var f = anomalien.features.filter(function (ff) { return ff.properties.id === id; })[0];
        if (!f) return;
        var geom = new ol.geom.Polygon(f.geometry.coordinates).transform("EPSG:4326", olEqualEarthProj);
        var feature = new ol.Feature({ geometry: geom });
        feature.set("auswahlFarbe", AUSWAHL_FARBEN[i % AUSWAHL_FARBEN.length]);
        feature.set("auswahlNummer", i + 1);
        olAuswahlSource.addFeature(feature);
      });
    }
  }

  // ---------- Liste ----------

  function findTheorie(id) {
    for (var i = 0; i < theorien.length; i++) {
      if (theorien[i].id === id) return theorien[i];
    }
    return null;
  }

  function renderListeZeile(f) {
    var p = f.properties;
    var farbe = STAERKE_FARBE[p.staerke_band];
    var info = aktuellKombInfo[p.id];
    var kombBadge = "";
    if (info) {
      kombBadge = info.istUnd
        ? '<span class="inv-liste-komb inv-liste-komb--und">UND-Treffer – zeitliches Zusammenfallen, beobachtet</span>'
        : '<span class="inv-liste-komb">ODER-Treffer</span>';
    }
    var ausgewaehltIdx = ausgewaehlt.indexOf(p.id);
    var auswahlFarbe = ausgewaehltIdx !== -1 ? AUSWAHL_FARBEN[ausgewaehltIdx % AUSWAHL_FARBEN.length] : null;

    return '<div class="inv-liste-zeile">' +
      '<label class="inv-liste-check" title="Zum Vergleich auswählen"' + (auswahlFarbe ? ' style="border-color:' + auswahlFarbe + '"' : '') + '>' +
      '<input type="checkbox" data-id="' + escapeHtml(p.id) + '"' + (ausgewaehltIdx !== -1 ? " checked" : "") + '>' +
      (ausgewaehltIdx !== -1 ? '<span class="inv-liste-check-num" style="background:' + auswahlFarbe + '">' + (ausgewaehltIdx + 1) + '</span>' : '') +
      '</label>' +
      '<button class="inv-liste-inhalt" data-id="' + escapeHtml(p.id) + '">' +
      '<span class="band-dot" style="background:' + farbe + '"></span>' +
      '<span class="inv-liste-text">' +
      '<span class="inv-liste-name">' + escapeHtml(p.name) + (p.hinweis ? ' <span class="inv-liste-hinweis">' + escapeHtml(p.hinweis) + '</span>' : '') + '</span>' +
      '<span class="inv-liste-sub">' + escapeHtml(p.ort_label) + " · " + escapeHtml(p.start) + '</span>' +
      kombBadge +
      "</span>" +
      "</button>" +
      "</div>";
  }

  function renderListe() {
    var sortiert = aktuellGefiltert.slice().sort(function (a, b) {
      var sa = STAERKE_SORT[a.properties.staerke_band], sb = STAERKE_SORT[b.properties.staerke_band];
      if (sa !== sb) return sa - sb;
      return monthIndex(b.properties.start) - monthIndex(a.properties.start);
    });

    var chips = "";
    if (ausgewaehlt.length) {
      chips = '<div class="inv-auswahl-tray">' +
        '<div class="inv-auswahl-head">Ausgewählt zum Vergleich (' + ausgewaehlt.length + ')' +
        '<button id="inv-auswahl-leeren" class="text-btn" type="button">leeren</button></div>' +
        ausgewaehlt.map(function (id, i) {
          var f = anomalien.features.filter(function (ff) { return ff.properties.id === id; })[0];
          if (!f) return "";
          var farbe = AUSWAHL_FARBEN[i % AUSWAHL_FARBEN.length];
          return '<button class="inv-auswahl-chip" data-id="' + escapeHtml(id) + '" style="border-color:' + farbe + '">' +
            '<span class="inv-auswahl-num" style="background:' + farbe + '">' + (i + 1) + "</span>" +
            escapeHtml(f.properties.name) +
            "</button>";
        }).join("") +
        "</div>";
    }

    var rows = sortiert.length
      ? sortiert.map(renderListeZeile).join("")
      : '<div class="inv-liste-leer">Keine Beispiel-Anomalien sichtbar – Filter prüfen.</div>';

    investigationContent.innerHTML =
      '<div class="inv-liste-head"><h2>Sichtbare Anomalien</h2>' +
      '<p class="inv-liste-count">' + sortiert.length + ' von ' + anomalien.features.length + ' Beispiel-Anomalien, sortiert nach Stärke</p></div>' +
      chips +
      '<div class="inv-liste">' + rows + "</div>";

    Array.prototype.slice.call(investigationContent.querySelectorAll(".inv-liste-check input")).forEach(function (cb) {
      cb.addEventListener("click", function (e) { e.stopPropagation(); });
      cb.addEventListener("change", function (e) {
        e.stopPropagation();
        toggleAuswahl(cb.getAttribute("data-id"));
      });
    });
    Array.prototype.slice.call(investigationContent.querySelectorAll(".inv-liste-inhalt")).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var f = anomalien.features.filter(function (ff) { return ff.properties.id === btn.getAttribute("data-id"); })[0];
        if (f) { flyToFeature(f); showDetail(f.properties); }
      });
    });
    Array.prototype.slice.call(investigationContent.querySelectorAll(".inv-auswahl-chip")).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var f = anomalien.features.filter(function (ff) { return ff.properties.id === btn.getAttribute("data-id"); })[0];
        if (f) { flyToFeature(f); showDetail(f.properties); }
      });
    });
    var leerenBtn = byId("inv-auswahl-leeren");
    if (leerenBtn) {
      leerenBtn.addEventListener("click", function () {
        ausgewaehlt = [];
        updateAuswahlLayer();
        renderListe();
      });
    }
  }

  // ---------- Detail ----------

  function renderVerknuepfungen(verknuepfungen) {
    if (!verknuepfungen || !verknuepfungen.length) {
      return '<div class="inv-field-value" style="color:var(--paper-ink-dim); font-size:12.5px;">Noch keine Verknüpfung – entsteht erst mit aleph/link/ (Abschnitt 8).</div>';
    }
    return verknuepfungen.map(function (v) {
      if (v.typ === "bewegung") {
        var herkunftF = anomalien.features.filter(function (f) { return f.properties.id === v.herkunft; })[0];
        var zielF = anomalien.features.filter(function (f) { return f.properties.id === v.ziel; })[0];
        var herkunftName = herkunftF ? herkunftF.properties.ort_label : v.herkunft;
        var zielName = zielF ? zielF.properties.ort_label : v.ziel;
        return '<div class="inv-verknuepfung inv-verknuepfung--bewegung">' +
          '<div class="inv-verknuepfung-titel">' + escapeHtml(herkunftName) + ' <span class="inv-verknuepfung-pfeil">→</span> ' + escapeHtml(zielName) + "</div>" +
          '<div class="inv-verknuepfung-stufe">Evidenzstufe: ' + escapeHtml(v.evidenzstufe) + "</div>" +
          '<div class="inv-verknuepfung-text">' + escapeHtml(EVIDENZ_TEXT[v.evidenzstufe] || "") + "</div>" +
          (v.hinweis ? '<div class="inv-verknuepfung-text">' + escapeHtml(v.hinweis) + "</div>" : "") +
          "</div>";
      }
      var t = findTheorie(v.theorie);
      var titel = t ? t.titel : v.theorie;
      return '<div class="inv-verknuepfung">' +
        '<button class="inv-theorie-link" data-theorie="' + escapeHtml(v.theorie) + '">' + escapeHtml(titel) + "</button>" +
        '<div class="inv-verknuepfung-stufe">Evidenzstufe: ' + escapeHtml(v.evidenzstufe) + "</div>" +
        '<div class="inv-verknuepfung-text">' + escapeHtml(EVIDENZ_TEXT[v.evidenzstufe] || "") + "</div>" +
        (v.hinweis ? '<div class="inv-verknuepfung-text">' + escapeHtml(v.hinweis) + "</div>" : "") +
        "</div>";
    }).join("");
  }

  function renderKombinationsHinweis(id) {
    var info = aktuellKombInfo[id];
    if (!info) return "";
    if (!info.istUnd) {
      return '<div class="inv-field"><div class="inv-field-label">Kombinationsfilter</div><div class="inv-field-value">ODER-Treffer – mindestens eine der gewählten Datenquellen betroffen.</div></div>';
    }
    var partnerText = info.partner.length
      ? info.partner.map(function (p) { return escapeHtml(p.name) + " (" + escapeHtml(p.ort) + ")"; }).join("; ")
      : "deckt alle gewählten Quellen bereits selbst ab";
    return '<div class="inv-field"><div class="inv-field-label">Kombinationsfilter</div><div class="inv-field-value">UND-Treffer – zeitliches Zusammenfallen, Evidenzstufe beobachtet. <span class="inv-field-note">Kein belegter Zusammenhang, nur Koinzidenz (Abschnitt 8). Zusammen mit: ' + partnerText + '.</span></div></div>';
  }

  function renderDetail(props) {
    var bandColor = STAERKE_FARBE[props.staerke_band] || "#e2b04f";
    var datenlageInfo = DATENLAGE_INFO[props.datenlage];

    investigationContent.innerHTML =
      '<span class="inv-badge">Beispieldaten</span>' +
      (props.hinweis ? '<span class="inv-badge inv-badge--hinweis">' + escapeHtml(props.hinweis) + "</span>" : "") +
      '<h2 class="inv-title">' + escapeHtml(props.name) + "</h2>" +
      '<p class="inv-sub">' + escapeHtml(props.ort_label) + " · " + escapeHtml(props.start) + (props.start !== props.ende ? " bis " + escapeHtml(props.ende) : "") + "</p>" +

      '<div class="inv-field"><div class="inv-field-label">Evidenzstufe der Anomalie</div><div class="inv-field-value">' + escapeHtml(props.evidenzstufe) + ' <span class="inv-field-note">– jede Anomalie ist eine direkte Messung (Abschnitt 7)</span></div></div>' +
      '<div class="inv-field"><div class="inv-field-label">Typ-Sicherheit</div><div class="inv-field-value">' + escapeHtml(props.typ_sicherheit) + (props.typ_sicherheit === "abgeleitet" ? " – vermutlich, aus indirekten Signalen erschlossen" : "") + "</div></div>" +
      '<div class="inv-field"><div class="inv-field-label">Datenlage</div><div class="inv-field-value">' + escapeHtml(datenlageInfo ? datenlageInfo.text : props.datenlage) + "</div></div>" +
      '<div class="inv-field"><div class="inv-field-label">Stärke und Richtung</div><div class="inv-field-value"><span class="band-dot" style="background:' + bandColor + '"></span>' + escapeHtml(props.staerke_band) + ", " + escapeHtml(props.richtung) + "</div></div>" +
      '<div class="inv-field"><div class="inv-field-label">Beteiligte Layer</div><div class="inv-field-value">' + escapeHtml((props.layer || []).join(", ")) + "</div></div>" +
      '<div class="inv-field"><div class="inv-field-label">Fokusgebiet</div><div class="inv-field-value">' + (props.fokusgebiet ? "ja – feinere Analyse vorgesehen (Abschnitt 4a)" : "nein – globales Monatsraster") + "</div></div>" +
      renderKombinationsHinweis(props.id) +

      '<div class="inv-placeholder">' +
      "<h3>Zeitreihe</h3>" +
      '<div class="inv-placeholder-box">' + escapeHtml(props.zeitreihe) + "</div>" +
      "<h3>Nachrichten und Konfliktereignisse</h3>" +
      '<div class="inv-placeholder-box">' + escapeHtml(props.nachrichten) + "</div>" +
      "<h3>Verknüpfungen</h3>" +
      renderVerknuepfungen(props.verknuepfungen) +
      "</div>";

    Array.prototype.slice.call(investigationContent.querySelectorAll(".inv-theorie-link")).forEach(function (link) {
      link.addEventListener("click", function () {
        var t = findTheorie(link.getAttribute("data-theorie"));
        if (t) openTheorie(t);
      });
    });
  }

  // ---------- Theorie- und Projektions-Kärtchen (teilen sich ein Panel) ----------

  var theoriePanel = byId("theorie-panel");
  var theorieContent = byId("theorie-content");

  function openTheorie(t) {
    var verknuepft = anomalien.features.filter(function (f) {
      return (f.properties.verknuepfungen || []).some(function (v) { return v.theorie === t.id; });
    });
    var listHtml = verknuepft.length
      ? verknuepft.map(function (f) {
          var v = f.properties.verknuepfungen.filter(function (vv) { return vv.theorie === t.id; })[0];
          return '<button class="theorie-anomalie-link" data-id="' + escapeHtml(f.properties.id) + '">' +
            escapeHtml(f.properties.name) + " – " + escapeHtml(f.properties.ort_label) +
            '<span class="theorie-anomalie-stufe">' + escapeHtml(v.evidenzstufe) + "</span>" +
            "</button>";
        }).join("")
      : '<div class="inv-field-value" style="font-size:12.5px; color:var(--paper-ink-dim);">Keine Beispiel-Anomalie in diesem Gerüst ist mit dieser Theorie verknüpft.</div>';

    var statusHinweis = t.status_hinweis ? '<div class="inv-verknuepfung-text">' + escapeHtml(t.status_hinweis) + "</div>" : "";

    theorieContent.innerHTML =
      '<span class="inv-badge">Beispieldaten</span>' +
      "<h3>" + escapeHtml(t.titel) + "</h3>" +
      '<div class="inv-field-label">Disziplin</div><div class="inv-field-value">' + escapeHtml(t.disziplin) + "</div>" +
      '<div class="inv-field-label">Status</div><div class="inv-field-value">' + escapeHtml(t.status) + "</div>" +
      statusHinweis +
      '<div class="inv-field-label">Kurzbeschreibung</div><div class="inv-field-value" style="font-size:13px;">' + escapeHtml(t.beschreibung) + "</div>" +
      '<div class="inv-field-label" style="margin-top:14px;">Verknüpfte Beispiel-Anomalien</div>' + listHtml;

    theoriePanel.classList.add("is-open");
    theoriePanel.setAttribute("aria-hidden", "false");

    Array.prototype.slice.call(theorieContent.querySelectorAll(".theorie-anomalie-link")).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var f = anomalien.features.filter(function (ff) { return ff.properties.id === btn.getAttribute("data-id"); })[0];
        if (f) {
          closeTheorie();
          flyToFeature(f);
          showDetail(f.properties);
        }
      });
    });
  }

  function openProjektion(p) {
    var theorieHtml = "";
    if (p.theorie) {
      var t = findTheorie(p.theorie);
      if (t) {
        theorieHtml = '<div class="inv-field-label" style="margin-top:14px;">Aufbauend auf Theorie</div>' +
          '<button class="inv-theorie-link" data-theorie="' + escapeHtml(t.id) + '">' + escapeHtml(t.titel) + "</button>";
      }
    }
    theorieContent.innerHTML =
      '<span class="inv-badge inv-badge--projektion">Beispiel-Projektion, keine Anomalie</span>' +
      "<h3>" + escapeHtml(p.titel) + "</h3>" +
      '<div class="inv-field-label">Evidenzstufe</div><div class="inv-field-value">' + escapeHtml(p.evidenzstufe) + "</div>" +
      '<div class="inv-verknuepfung-text">' + escapeHtml(EVIDENZ_TEXT[p.evidenzstufe] || "") + "</div>" +
      '<div class="inv-field-label" style="margin-top:10px;">Zeitraum</div><div class="inv-field-value">' + escapeHtml(p.von) + " bis " + escapeHtml(p.bis) + "</div>" +
      '<div class="inv-field-label">Ort</div><div class="inv-field-value">' + escapeHtml(p.ort_label) + "</div>" +
      '<div class="inv-field-label">Beschreibung</div><div class="inv-field-value" style="font-size:13px;">' + escapeHtml(p.beschreibung) + "</div>" +
      theorieHtml;

    theoriePanel.classList.add("is-open");
    theoriePanel.setAttribute("aria-hidden", "false");

    var link = theorieContent.querySelector(".inv-theorie-link");
    if (link) {
      link.addEventListener("click", function () {
        var t = findTheorie(link.getAttribute("data-theorie"));
        if (t) openTheorie(t);
      });
    }
  }

  function closeTheorie() {
    theoriePanel.classList.remove("is-open");
    theoriePanel.setAttribute("aria-hidden", "true");
  }
  byId("theorie-close").addEventListener("click", closeTheorie);

  // ---------- Projektions-Markierungen auf der Zeitachse ----------

  (function renderProjektionsMarker() {
    var container = byId("tl-proj-dots");
    projektionen.forEach(function (p) {
      var dot = document.createElement("button");
      dot.type = "button";
      dot.className = "tl-proj-dot";
      dot.style.left = pct(monthIndex(p.von)) + "%";
      dot.title = p.titel + " (" + p.evidenzstufe + ", Beispiel-Projektion)";
      dot.setAttribute("aria-label", p.titel);
      dot.addEventListener("click", function () { openProjektion(p); });
      container.appendChild(dot);
    });
  })();

  // ---------- Datenverfügbarkeit über der Zeitachse (einklappbar) ----------

  var availToggle = byId("tl-availability-toggle");
  var availRows = byId("tl-availability-rows");
  var availCaret = byId("tl-availability-caret");
  var availOffen = true;
  availToggle.addEventListener("click", function () {
    availOffen = !availOffen;
    availRows.hidden = !availOffen;
    availToggle.setAttribute("aria-expanded", String(availOffen));
    availCaret.textContent = availOffen ? "▾" : "▸";
  });

  function renderVerfuegbarkeitStreifen(aktiveQuellen) {
    availRows.innerHTML = "";
    var zeigen = aktiveQuellen && aktiveQuellen.length
      ? datenverfuegbarkeit.filter(function (d) { return aktiveQuellen.indexOf(d.quelle) !== -1; })
      : datenverfuegbarkeit;

    zeigen.forEach(function (d) {
      var row = document.createElement("div");
      row.className = "tl-avail-row";

      var label = document.createElement("span");
      label.className = "tl-avail-label";
      label.textContent = d.kurz;
      row.appendChild(label);

      var track = document.createElement("span");
      track.className = "tl-avail-track";
      var bar = document.createElement("span");
      bar.className = "tl-avail-bar";
      var left = pct(monthIndex(d.von));
      var right = pct(monthIndex(d.bis));
      bar.style.left = left + "%";
      bar.style.width = Math.max(0.6, right - left) + "%";
      bar.style.background = (DATENLAGE_INFO[d.datenlage] || {}).farbe || "#5c6785";
      bar.title = d.layer + ": " + d.von + " bis " + d.bis + " (Datenlage: " + d.datenlage + ", Beispielzeitraum)";
      track.appendChild(bar);
      row.appendChild(track);

      availRows.appendChild(row);
    });
  }
  renderVerfuegbarkeitStreifen([]);

  // ---------- Suche ----------

  var searchInput = byId("search-input");
  var searchResults = byId("search-results");

  function norm(s) { return String(s).toLowerCase(); }

  function flyToFeature(f) {
    var c = centroid(f.geometry.coordinates);
    panTo(c, 4.2);
  }

  function renderSearch(query) {
    var q = norm(query);
    if (!q) { searchResults.hidden = true; searchResults.innerHTML = ""; return; }

    var orteHits = orte.filter(function (o) { return norm(o.name).indexOf(q) !== -1 || norm(o.land).indexOf(q) !== -1; }).slice(0, 4);
    var anomalienHits = anomalien.features.filter(function (f) {
      var p = f.properties;
      return norm(p.name).indexOf(q) !== -1 || norm(p.ort_label).indexOf(q) !== -1 || norm(p.typ).indexOf(q) !== -1;
    }).slice(0, 4);
    var theorienHits = theorien.filter(function (t) { return norm(t.titel).indexOf(q) !== -1 || norm(t.disziplin).indexOf(q) !== -1; }).slice(0, 3);

    var html = "";
    if (!orteHits.length && !anomalienHits.length && !theorienHits.length) {
      html = '<div class="search-empty">Keine Treffer in Orten, Beispiel-Anomalien oder Theorien.</div>';
    } else {
      if (orteHits.length) {
        html += '<div class="search-group-label">Orte</div>';
        orteHits.forEach(function (o) {
          html += '<button class="search-item" data-kind="ort" data-lon="' + o.lon + '" data-lat="' + o.lat + '">' +
            escapeHtml(o.name) + '<span class="item-sub">' + escapeHtml(o.land) + "</span></button>";
        });
      }
      if (anomalienHits.length) {
        html += '<div class="search-group-label">Beispiel-Anomalien</div>';
        anomalienHits.forEach(function (f) {
          html += '<button class="search-item" data-kind="anomalie" data-id="' + escapeHtml(f.properties.id) + '">' +
            escapeHtml(f.properties.name) + '<span class="item-sub">' + escapeHtml(f.properties.ort_label) + "</span></button>";
        });
      }
      if (theorienHits.length) {
        html += '<div class="search-group-label">Theorien</div>';
        theorienHits.forEach(function (t) {
          html += '<button class="search-item" data-kind="theorie" data-id="' + escapeHtml(t.id) + '">' +
            escapeHtml(t.titel) + '<span class="item-sub">' + escapeHtml(t.disziplin) + "</span></button>";
        });
      }
    }
    searchResults.innerHTML = html;
    searchResults.hidden = false;

    Array.prototype.slice.call(searchResults.querySelectorAll(".search-item")).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var kind = btn.getAttribute("data-kind");
        if (kind === "ort") {
          panTo([parseFloat(btn.getAttribute("data-lon")), parseFloat(btn.getAttribute("data-lat"))], 5);
        } else if (kind === "anomalie") {
          var f = anomalien.features.filter(function (ff) { return ff.properties.id === btn.getAttribute("data-id"); })[0];
          if (f) { flyToFeature(f); showDetail(f.properties); }
        } else if (kind === "theorie") {
          var t = findTheorie(btn.getAttribute("data-id"));
          if (t) openTheorie(t);
        }
        searchResults.hidden = true;
        searchInput.value = "";
      });
    });
  }

  searchInput.addEventListener("input", function () { renderSearch(searchInput.value); });
  searchInput.addEventListener("focus", function () { if (searchInput.value) renderSearch(searchInput.value); });
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".search-wrap")) { searchResults.hidden = true; }
  });

  // ---------- Tastatur ----------

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (invState === "detail") showListe();
    closeTheorie();
    closeFilter();
    searchResults.hidden = true;
  });

  // ---------- Start: Liste sofort sichtbar, auch bevor die Karte geladen ist ----------

  showListe();
})();
