/*
 * ALEPH – Oberflächen-Gerüst (Woche 2, ARCHITECTURE.md Abschnitt 10)
 *
 * Alles auf dieser Seite ist Beispieldaten (web/data/*.js). Es gibt noch
 * keine echte Anomalieerkennung – dieses Skript testet nur, ob Globus,
 * Suche, Filter und Untersuchungsansicht wie vorgesehen funktionieren.
 */
(function () {
  "use strict";

  var EPOCH_YEAR = 2013;
  var STAERKE_RANK = { "auffällig": 1, "stark": 2, "extrem": 3 };
  var STAERKE_FARBE = {
    "auffällig": "#e2b04f",
    "stark": "#d9822f",
    "extrem": "#c14a34"
  };

  var anomalien = window.ALEPH_BEISPIEL_ANOMALIEN;
  var theorien = window.ALEPH_BEISPIEL_THEORIEN;
  var orte = window.ALEPH_ORTE;

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

  function byId(id) { return document.getElementById(id); }

  // ---------- Karte ----------

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
      sources: {
        "eox-blackmarble": {
          type: "raster",
          tiles: [
            "https://tiles.maps.eox.at/wmts/1.0.0/blackmarble_3857/default/g/{z}/{y}/{x}.jpg"
          ],
          tileSize: 256,
          attribution:
            '© <a href="https://maps.eox.at" target="_blank" rel="noopener">EOX IT Services</a> – Nachtlicht-Basiskarte: NASA Black Marble (VIIRS)'
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
        { id: "blackmarble", type: "raster", source: "eox-blackmarble" },
        { id: "overlay", type: "raster", source: "eox-overlay", paint: { "raster-opacity": 0.5 } }
      ],
      sky: {
        "atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, 1, 5, 1, 7, 0]
      },
      light: { anchor: "map", position: [1.5, 90, 80] }
    }
  });

  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");
  map.addControl(new maplibregl.GlobeControl(), "bottom-right");

  var hoverPopup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 8 });

  map.on("load", function () {
    map.setProjection({ type: "globe" });

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
      openInvestigation(normalizeProps(props));
    });

    applyFilters();
  });

  function normalizeProps(props) {
    // GeoJSON properties come back from MapLibre with arrays JSON-stringified.
    var out = {};
    for (var k in props) {
      out[k] = props[k];
    }
    if (typeof out.layer === "string") {
      try { out.layer = JSON.parse(out.layer); } catch (e) { out.layer = [out.layer]; }
    }
    return out;
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
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

  // Zeitschieber
  var timeStartInput = byId("time-start");
  var timeEndInput = byId("time-end");
  var rangeFill = byId("range-fill");
  var readoutStart = byId("time-readout-start");
  var readoutEnd = byId("time-readout-end");

  function updateRangeUi() {
    var min = parseInt(timeStartInput.min, 10);
    var max = parseInt(timeStartInput.max, 10);
    var s = parseInt(timeStartInput.value, 10);
    var e = parseInt(timeEndInput.value, 10);
    if (s > e) { s = e; timeStartInput.value = String(s); }
    var pctS = ((s - min) / (max - min)) * 100;
    var pctE = ((e - min) / (max - min)) * 100;
    rangeFill.style.left = pctS + "%";
    rangeFill.style.width = (pctE - pctS) + "%";
    readoutStart.textContent = monthLabel(s);
    readoutEnd.textContent = monthLabel(e);
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
  updateRangeUi();

  byId("filter-reset").addEventListener("click", function () {
    regionSelect.value = "alle";
    typSelect.value = "alle";
    evidenzChecks.forEach(function (cb) { cb.checked = true; });
    fokusCheck.checked = false;
    minStaerke = "auffällig";
    staerkeBtns.forEach(function (b) { b.classList.toggle("is-active", b.getAttribute("data-value") === "auffällig"); });
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
      timeEnd: parseInt(timeEndInput.value, 10)
    };
  }

  function featurePasses(props, state) {
    if (state.region !== "alle" && props.region !== state.region) return false;
    if (state.typ !== "alle" && props.typ !== state.typ) return false;
    if (state.evidenzstufen.indexOf(props.evidenzstufe) === -1) return false;
    if (STAERKE_RANK[props.staerke_band] < STAERKE_RANK[state.minStaerke]) return false;
    if (state.onlyFocus && !props.fokusgebiet) return false;
    var fStart = monthIndex(props.start);
    var fEnde = monthIndex(props.ende);
    if (fEnde < state.timeStart || fStart > state.timeEnd) return false;
    return true;
  }

  function applyFilters() {
    if (!map.getSource("anomalien")) return;
    var state = currentFilterState();
    var gefiltert = anomalien.features.filter(function (f) { return featurePasses(f.properties, state); });
    map.getSource("anomalien").setData({ type: "FeatureCollection", features: gefiltert });
    byId("filter-count").textContent = String(gefiltert.length);
  }

  // ---------- Untersuchungsansicht ----------

  var investigation = byId("investigation");
  var investigationContent = byId("investigation-content");

  var DATENLAGE_TEXT = {
    "gut": "gut – Basislinie und Beobachtungen ausreichend",
    "mittel": "mittel – eingeschränkte Basislinie oder lückenhafte Beobachtungen",
    "dünn": "dünn – Aussage unsicher, wenige gültige Beobachtungen"
  };

  function findTheorie(id) {
    for (var i = 0; i < theorien.length; i++) {
      if (theorien[i].id === id) return theorien[i];
    }
    return null;
  }

  function openInvestigation(props) {
    var bandColor = STAERKE_FARBE[props.staerke_band] || "#e2b04f";
    var theorieHtml = "";
    if (props.theorie) {
      var t = findTheorie(props.theorie);
      if (t) {
        theorieHtml =
          '<button class="inv-theorie-link" data-theorie="' + escapeHtml(t.id) + '">' +
          "Betroffene Theorie ansehen: " + escapeHtml(t.titel) +
          "</button>";
      }
    } else {
      theorieHtml = '<div class="inv-field-value" style="color:var(--paper-ink-dim); font-size:12.5px;">Noch keine Theorie verknüpft – Verknüpfung entsteht erst mit aleph/link/.</div>';
    }

    investigationContent.innerHTML =
      '<span class="inv-badge">Beispieldaten</span>' +
      '<h2 class="inv-title">' + escapeHtml(props.name) + "</h2>" +
      '<p class="inv-sub">' + escapeHtml(props.ort_label) + " · " + escapeHtml(props.start) + (props.start !== props.ende ? " bis " + escapeHtml(props.ende) : "") + "</p>" +

      '<div class="inv-field"><div class="inv-field-label">Evidenzstufe</div><div class="inv-field-value">' + escapeHtml(props.evidenzstufe) + "</div></div>" +
      '<div class="inv-field"><div class="inv-field-label">Typ-Sicherheit</div><div class="inv-field-value">' + escapeHtml(props.typ_sicherheit) + (props.typ_sicherheit === "abgeleitet" ? " – vermutlich, aus indirekten Signalen erschlossen" : "") + "</div></div>" +
      '<div class="inv-field"><div class="inv-field-label">Datenlage</div><div class="inv-field-value">' + escapeHtml(DATENLAGE_TEXT[props.datenlage] || props.datenlage) + "</div></div>" +
      '<div class="inv-field"><div class="inv-field-label">Stärke und Richtung</div><div class="inv-field-value"><span class="band-dot" style="background:' + bandColor + '"></span>' + escapeHtml(props.staerke_band) + ", " + escapeHtml(props.richtung) + "</div></div>" +
      '<div class="inv-field"><div class="inv-field-label">Beteiligte Layer</div><div class="inv-field-value">' + escapeHtml((props.layer || []).join(", ")) + "</div></div>" +
      '<div class="inv-field"><div class="inv-field-label">Fokusgebiet</div><div class="inv-field-value">' + (props.fokusgebiet ? "ja – feinere Analyse vorgesehen (Abschnitt 4a)" : "nein – globales Monatsraster") + "</div></div>" +

      '<div class="inv-placeholder">' +
      "<h3>Zeitreihe</h3>" +
      '<div class="inv-placeholder-box">' + escapeHtml(props.zeitreihe) + "</div>" +
      "<h3>Nachrichten und Konfliktereignisse</h3>" +
      '<div class="inv-placeholder-box">' + escapeHtml(props.nachrichten) + "</div>" +
      "<h3>Verknüpfte Theorie</h3>" +
      theorieHtml +
      "</div>";

    investigation.classList.add("is-open");
    investigation.setAttribute("aria-hidden", "false");

    var link = investigationContent.querySelector(".inv-theorie-link");
    if (link) {
      link.addEventListener("click", function () {
        var t = findTheorie(link.getAttribute("data-theorie"));
        if (t) openTheorie(t);
      });
    }
  }

  function closeInvestigation() {
    investigation.classList.remove("is-open");
    investigation.setAttribute("aria-hidden", "true");
  }
  byId("investigation-close").addEventListener("click", closeInvestigation);

  // ---------- Theorie-Panel ----------

  var theoriePanel = byId("theorie-panel");
  var theorieContent = byId("theorie-content");

  function openTheorie(t) {
    var verknuepft = anomalien.features.filter(function (f) { return f.properties.theorie === t.id; });
    var listHtml = verknuepft.length
      ? verknuepft.map(function (f) {
          return '<button class="theorie-anomalie-link" data-id="' + escapeHtml(f.properties.id) + '">' +
            escapeHtml(f.properties.name) + " – " + escapeHtml(f.properties.ort_label) +
            "</button>";
        }).join("")
      : '<div class="inv-field-value" style="font-size:12.5px; color:var(--paper-ink-dim);">Keine Beispiel-Anomalie in diesem Gerüst ist mit dieser Theorie verknüpft.</div>';

    theorieContent.innerHTML =
      '<span class="inv-badge">Beispieldaten</span>' +
      "<h3>" + escapeHtml(t.titel) + "</h3>" +
      '<div class="inv-field-label">Disziplin</div><div class="inv-field-value">' + escapeHtml(t.disziplin) + "</div>" +
      '<div class="inv-field-label">Status</div><div class="inv-field-value">' + escapeHtml(t.status) + " – wie jede neue Theorie, bis zur Prüfung an Daten (Abschnitt 8)</div>" +
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
          openInvestigation(f.properties);
        }
      });
    });
  }
  function closeTheorie() {
    theoriePanel.classList.remove("is-open");
    theoriePanel.setAttribute("aria-hidden", "true");
  }
  byId("theorie-close").addEventListener("click", closeTheorie);

  // ---------- Suche ----------

  var searchInput = byId("search-input");
  var searchResults = byId("search-results");

  function norm(s) { return String(s).toLowerCase(); }

  function flyToFeature(f) {
    var c = centroid(f.geometry.coordinates);
    map.flyTo({ center: c, zoom: 4.2, duration: 1400 });
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
          map.flyTo({ center: [parseFloat(btn.getAttribute("data-lon")), parseFloat(btn.getAttribute("data-lat"))], zoom: 5, duration: 1400 });
        } else if (kind === "anomalie") {
          var f = anomalien.features.filter(function (ff) { return ff.properties.id === btn.getAttribute("data-id"); })[0];
          if (f) { flyToFeature(f); openInvestigation(f.properties); }
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
    closeInvestigation();
    closeTheorie();
    closeFilter();
    searchResults.hidden = true;
  });
})();
