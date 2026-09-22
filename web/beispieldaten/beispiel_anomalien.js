/*
 * BEISPIELDATEN – keine echten Messungen.
 *
 * Format nach ARCHITECTURE.md Abschnitt 7 ("Anomalien benennen"). Jedes Feature
 * entspricht einer benannten Anomalie mit: id, name (angezeigter Typ),
 * typ_sicherheit, layer, gebiet (= Polygon-Geometrie), start, ende, richtung,
 * staerke_band, datenlage, evidenzstufe, zeitreihe (Verweis), version.
 *
 * Diese 18 Einträge dienen ausschließlich dazu, das Oberflächen-Gerüst
 * (Woche 2) zu testen: Globus, Suchleiste, Filter, Untersuchungsansicht.
 * Sobald echte Layer und die Erkennung (Abschnitt 6) laufen, wird diese
 * Datei durch den Export aus aleph/export/ ersetzt.
 */
window.ALEPH_BEISPIEL_ANOMALIEN = {
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "id": "bm-001",
        "beispiel": true,
        "name": "Anomalie: Waldbrand",
        "typ": "Waldbrand",
        "typ_sicherheit": "direkt gemessen",
        "layer": ["brände", "vegetation"],
        "region": "Amerika",
        "ort_label": "Amazonasrand, Rondônia (Beispiel)",
        "start": "2024-08",
        "ende": "2024-10",
        "richtung": "Anstieg",
        "staerke_band": "stark",
        "datenlage": "gut",
        "evidenzstufe": "beobachtet",
        "fokusgebiet": false,
        "theorie": null,
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-62.5,-9.2861],[-62.0598,-9.2029],[-61.8131,-9.5801],[-61.9674,-9.9705],[-62.1258,-10.3076],[-62.5,-10.4129],[-62.9035,-10.3473],[-63.1945,-10.0224],[-62.9837,-9.6451],[-62.7866,-9.4112],[-62.5,-9.2861]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-002",
        "beispiel": true,
        "name": "Anomalie: Stromausfall",
        "typ": "Stromausfall",
        "typ_sicherheit": "abgeleitet",
        "layer": ["nachtlicht"],
        "region": "Europa",
        "ort_label": "Region Kyiv (Fokusgebiet, Beispiel)",
        "start": "2024-01",
        "ende": "2024-01",
        "richtung": "Rückgang",
        "staerke_band": "extrem",
        "datenlage": "mittel",
        "evidenzstufe": "beobachtet",
        "fokusgebiet": true,
        "theorie": null,
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[30.5,51.7238],[31.7166,51.4674],[31.7518,50.6593],[31.7745,50.136],[31.6608,49.3816],[30.5,49.1948],[29.4216,49.4539],[29.0459,50.0988],[28.8064,50.7508],[29.4529,51.3187],[30.5,51.7238]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-003",
        "beispiel": true,
        "name": "Anomalie: Stromausfall im Konfliktgebiet",
        "typ": "Stromausfall im Konfliktgebiet",
        "typ_sicherheit": "abgeleitet",
        "layer": ["nachtlicht"],
        "region": "Europa",
        "ort_label": "Ostukraine, Region Donetsk (Fokusgebiet, Beispiel)",
        "start": "2023-11",
        "ende": "2024-02",
        "richtung": "Rückgang",
        "staerke_band": "extrem",
        "datenlage": "mittel",
        "evidenzstufe": "statistische Assoziation",
        "fokusgebiet": true,
        "theorie": "konflikt-vertreibung",
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[37.8,48.9367],[38.7679,48.8914],[39.2325,48.3115],[39.4118,47.6496],[38.8064,47.0731],[37.8,47.1562],[37.0836,47.3402],[36.0093,47.6107],[36.4522,48.293],[36.9789,48.7563],[37.8,48.9367]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-004",
        "beispiel": true,
        "name": "Anomalie: Dürre",
        "typ": "Dürre",
        "typ_sicherheit": "abgeleitet",
        "layer": ["niederschlag", "vegetation"],
        "region": "Afrika",
        "ort_label": "Horn von Afrika (Beispiel)",
        "start": "2022-03",
        "ende": "2023-06",
        "richtung": "Rückgang",
        "staerke_band": "stark",
        "datenlage": "gut",
        "evidenzstufe": "statistische Assoziation",
        "fokusgebiet": false,
        "theorie": "duerre-migration",
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[40.5,6.5458],[40.7979,6.4078],[41.0701,6.1842],[40.9976,5.8392],[40.7911,5.6015],[40.5,5.4021],[40.0507,5.385],[39.8083,5.7765],[39.8189,6.2201],[40.18,6.438],[40.5,6.5458]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-005",
        "beispiel": true,
        "name": "Anomalie: Abholzung",
        "typ": "Abholzung",
        "typ_sicherheit": "abgeleitet",
        "layer": ["vegetation", "brände"],
        "region": "Asien",
        "ort_label": "Zentral-Borneo (Beispiel)",
        "start": "2021-05",
        "ende": "2021-12",
        "richtung": "Rückgang",
        "staerke_band": "stark",
        "datenlage": "mittel",
        "evidenzstufe": "beobachtet",
        "fokusgebiet": false,
        "theorie": null,
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[113.9,-0.3325],[114.3144,-0.4298],[114.5864,-0.777],[114.6305,-1.2373],[114.314,-1.5697],[113.9,-1.7616],[113.6174,-1.3889],[113.3121,-1.191],[113.1693,-0.7626],[113.5028,-0.4534],[113.9,-0.3325]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-006",
        "beispiel": true,
        "name": "Anomalie: Stadtwachstum",
        "typ": "Stadtwachstum",
        "typ_sicherheit": "abgeleitet",
        "layer": ["nachtlicht"],
        "region": "Asien",
        "ort_label": "Siedlungsrand Delhi (Beispiel)",
        "start": "2019-01",
        "ende": "2023-12",
        "richtung": "Anstieg",
        "staerke_band": "auffällig",
        "datenlage": "gut",
        "evidenzstufe": "beobachtet",
        "fokusgebiet": false,
        "theorie": null,
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[77.4,28.9605],[77.6444,28.8953],[77.738,28.6964],[77.7,28.5144],[77.5579,28.4092],[77.4,28.26],[77.1926,28.3494],[77.0152,28.4902],[77.081,28.691],[77.1611,28.8887],[77.4,28.9605]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-007",
        "beispiel": true,
        "name": "Anomalie: neue Schifffahrtsroute",
        "typ": "neue Schifffahrtsroute",
        "typ_sicherheit": "direkt gemessen",
        "layer": ["schiffsverkehr"],
        "region": "Arktis",
        "ort_label": "Nördlicher Seeweg, Karasee (Beispiel)",
        "start": "2020-07",
        "ende": "2020-10",
        "richtung": "Anstieg",
        "staerke_band": "auffällig",
        "datenlage": "dünn",
        "evidenzstufe": "beobachtet",
        "fokusgebiet": false,
        "theorie": null,
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[90.0,75.2867],[90.5894,75.21],[91.2425,75.1045],[90.9083,74.9236],[90.7268,74.7411],[90.0,74.7067],[89.4438,74.8019],[88.8404,74.9025],[89.1118,75.0747],[89.3097,75.2459],[90.0,75.2867]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-008",
        "beispiel": true,
        "name": "Anomalie: vermutliche Kriegsschäden",
        "typ": "vermutliche Kriegsschäden",
        "typ_sicherheit": "abgeleitet",
        "layer": ["brände", "nachtlicht"],
        "region": "Naher Osten",
        "ort_label": "Gaza-Streifen (Fokusgebiet, Beispiel)",
        "start": "2023-10",
        "ende": "2024-04",
        "richtung": "Rückgang",
        "staerke_band": "extrem",
        "datenlage": "dünn",
        "evidenzstufe": "beobachtet",
        "fokusgebiet": true,
        "theorie": null,
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[34.45,32.4307],[35.3649,32.5737],[35.4277,31.7709],[35.7755,31.1328],[35.039,30.8088],[34.45,30.5582],[33.5214,30.4103],[33.4223,31.2153],[33.1623,31.8567],[33.7221,32.3543],[34.45,32.4307]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-009",
        "beispiel": true,
        "name": "Anomalie: Bevölkerungsbewegung",
        "typ": "Bevölkerungsbewegung",
        "typ_sicherheit": "abgeleitet",
        "layer": ["nachtlicht"],
        "region": "Naher Osten",
        "ort_label": "Grenzregion Syrien/Türkei (Beispiel)",
        "start": "2023-02",
        "ende": "2023-08",
        "richtung": "Rückgang",
        "staerke_band": "stark",
        "datenlage": "mittel",
        "evidenzstufe": "statistische Assoziation",
        "fokusgebiet": false,
        "theorie": "konflikt-vertreibung",
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[37.0,37.1172],[37.4307,36.9765],[37.6095,36.6592],[37.8803,36.2701],[37.3463,36.1168],[37.0,35.8703],[36.4486,35.89],[36.412,36.3464],[36.2358,36.6996],[36.5134,37.0384],[37.0,37.1172]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-010",
        "beispiel": true,
        "name": "Anomalie: unerklärte Veränderung in Nachtlicht und NO₂",
        "typ": "unerklärte Veränderung",
        "typ_sicherheit": "unerklärt",
        "layer": ["nachtlicht", "no2"],
        "region": "Asien",
        "ort_label": "Region Tengiz, Kasachstan (Beispiel)",
        "start": "2022-06",
        "ende": "2022-09",
        "richtung": "Anstieg",
        "staerke_band": "auffällig",
        "datenlage": "mittel",
        "evidenzstufe": "beobachtet",
        "fokusgebiet": false,
        "theorie": null,
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[51.1,47.4256],[51.3618,47.3453],[51.5564,47.201],[51.4747,47.0171],[51.414,46.8058],[51.1,46.7347],[50.8077,46.8261],[50.7354,47.0193],[50.6562,47.1982],[50.8519,47.3325],[51.1,47.4256]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-011",
        "beispiel": true,
        "name": "Anomalie: Dürre",
        "typ": "Dürre",
        "typ_sicherheit": "abgeleitet",
        "layer": ["niederschlag", "vegetation"],
        "region": "Europa",
        "ort_label": "Iberische Halbinsel, Mittelspanien (Beispiel)",
        "start": "2022-05",
        "ende": "2022-09",
        "richtung": "Rückgang",
        "staerke_band": "auffällig",
        "datenlage": "gut",
        "evidenzstufe": "beobachtet",
        "fokusgebiet": false,
        "theorie": "duerre-migration",
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-4.5,39.8069],[-4.2533,39.762],[-4.0303,39.6178],[-4.1191,39.4045],[-4.2596,39.2446],[-4.5,39.1719],[-4.7017,39.2857],[-4.8898,39.4023],[-4.9127,39.6035],[-4.7746,39.7916],[-4.5,39.8069]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-012",
        "beispiel": true,
        "name": "Anomalie: Waldbrand",
        "typ": "Waldbrand",
        "typ_sicherheit": "direkt gemessen",
        "layer": ["brände", "vegetation"],
        "region": "Ozeanien",
        "ort_label": "Südost-Australien (Beispiel)",
        "start": "2019-12",
        "ende": "2020-01",
        "richtung": "Anstieg",
        "staerke_band": "extrem",
        "datenlage": "gut",
        "evidenzstufe": "beobachtet",
        "fokusgebiet": false,
        "theorie": null,
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[149.5,-35.4357],[150.3503,-35.5592],[150.8815,-36.1392],[150.5475,-36.7736],[150.0954,-37.1588],[149.5,-37.5105],[148.8008,-37.2736],[148.0267,-36.8848],[148.1031,-36.1351],[148.6718,-35.5837],[149.5,-35.4357]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-013",
        "beispiel": true,
        "name": "Anomalie: unerklärte Veränderung in Nachtlicht",
        "typ": "unerklärte Veränderung",
        "typ_sicherheit": "unerklärt",
        "layer": ["nachtlicht"],
        "region": "Afrika",
        "ort_label": "Golf von Guinea, vor Lagos (Beispiel)",
        "start": "2021-09",
        "ende": "2021-11",
        "richtung": "Anstieg",
        "staerke_band": "auffällig",
        "datenlage": "dünn",
        "evidenzstufe": "beobachtet",
        "fokusgebiet": false,
        "theorie": null,
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[3.4,6.6765],[3.6032,6.6779],[3.7286,6.5061],[3.7535,6.2859],[3.5567,6.1856],[3.4,6.1279],[3.2468,6.1905],[3.1405,6.3162],[3.0639,6.5085],[3.2484,6.6073],[3.4,6.6765]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-014",
        "beispiel": true,
        "name": "Anomalie: Stromausfall",
        "typ": "Stromausfall",
        "typ_sicherheit": "abgeleitet",
        "layer": ["nachtlicht"],
        "region": "Amerika",
        "ort_label": "Region Caracas (Beispiel)",
        "start": "2019-03",
        "ende": "2019-03",
        "richtung": "Rückgang",
        "staerke_band": "extrem",
        "datenlage": "mittel",
        "evidenzstufe": "beobachtet",
        "fokusgebiet": false,
        "theorie": null,
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-66.9,11.3661],[-66.1903,11.4604],[-65.7781,10.8584],[-65.6278,10.0935],[-66.3293,9.7277],[-66.9,9.5537],[-67.6198,9.5258],[-68.0253,10.1405],[-67.84,10.8003],[-67.6038,11.4524],[-66.9,11.3661]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-015",
        "beispiel": true,
        "name": "Anomalie: Dürre",
        "typ": "Dürre",
        "typ_sicherheit": "abgeleitet",
        "layer": ["niederschlag", "vegetation"],
        "region": "Asien",
        "ort_label": "Indus-Becken (Beispiel)",
        "start": "2018-11",
        "ende": "2019-05",
        "richtung": "Rückgang",
        "staerke_band": "stark",
        "datenlage": "mittel",
        "evidenzstufe": "Modellprojektion",
        "fokusgebiet": false,
        "theorie": "duerre-migration",
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[70.5,28.2751],[70.8149,27.8845],[71.2538,27.7172],[71.0589,27.3389],[71.018,26.8676],[70.5,27.0231],[70.0042,26.8947],[69.7646,27.2881],[69.7053,27.729],[69.9792,28.1359],[70.5,28.2751]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-016",
        "beispiel": true,
        "name": "Anomalie: neue Schifffahrtsroute",
        "typ": "neue Schifffahrtsroute",
        "typ_sicherheit": "direkt gemessen",
        "layer": ["schiffsverkehr"],
        "region": "Asien",
        "ort_label": "Ausweichroute Straße von Malakka (Beispiel)",
        "start": "2021-01",
        "ende": "2021-04",
        "richtung": "Anstieg",
        "staerke_band": "auffällig",
        "datenlage": "gut",
        "evidenzstufe": "beobachtet",
        "fokusgebiet": false,
        "theorie": null,
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[98.5,3.7926],[98.6833,3.7519],[98.7871,3.5931],[98.7916,3.4054],[98.6768,3.2571],[98.5,3.1608],[98.3372,3.2763],[98.1802,3.3963],[98.2738,3.5734],[98.3332,3.7292],[98.5,3.7926]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-017",
        "beispiel": true,
        "name": "Anomalie: Bevölkerungsbewegung",
        "typ": "Bevölkerungsbewegung",
        "typ_sicherheit": "abgeleitet",
        "layer": ["nachtlicht"],
        "region": "Afrika",
        "ort_label": "Sahelrand, Niger (Beispiel, hypothetisches Szenario)",
        "start": "2026-01",
        "ende": "2026-12",
        "richtung": "Rückgang",
        "staerke_band": "stark",
        "datenlage": "dünn",
        "evidenzstufe": "hypothetisches Szenario",
        "fokusgebiet": false,
        "theorie": "duerre-migration",
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Kein Nachrichtenkontext – hypothetisches Szenario, ausdrücklich keine Vorhersage",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[12.6,14.1357],[13.0384,14.0867],[13.3566,13.7391],[13.1503,13.3261],[13.0307,12.9236],[12.6,12.807],[12.1892,12.9502],[12.1048,13.3436],[12.1304,13.6484],[12.2419,13.9793],[12.6,14.1357]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "id": "bm-018",
        "beispiel": true,
        "name": "Anomalie: Abholzung",
        "typ": "Abholzung",
        "typ_sicherheit": "abgeleitet",
        "layer": ["vegetation"],
        "region": "Afrika",
        "ort_label": "Kongobecken (Beispiel)",
        "start": "2020-01",
        "ende": "2024-12",
        "richtung": "Rückgang",
        "staerke_band": "stark",
        "datenlage": "mittel",
        "evidenzstufe": "beobachtet",
        "fokusgebiet": false,
        "theorie": null,
        "zeitreihe": "Platzhalter – wird mit echtem Layer-Export befüllt",
        "nachrichten": "Platzhalter – GDELT-Anbindung folgt in Woche 5/6",
        "version": "beispiel-v0"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[24.5,-0.4714],[24.8995,-0.4502],[25.0487,-0.8218],[25.0078,-1.165],[24.8677,-1.5061],[24.5,-1.6269],[24.1341,-1.5036],[23.9143,-1.1903],[23.9723,-0.8286],[24.1758,-0.5539],[24.5,-0.4714]]]
      }
    }
  ]
};
