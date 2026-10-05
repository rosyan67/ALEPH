"""Holt je Monat 2013-01..2022-12 aus dem NASA-Katalog (CMR, öffentlich, ohne Anmeldung) für jede VNP46A3-Datei:
Dateiname, PGE-Version, Erzeugungszeit, Einfügedatum. Nur Metadaten, keine Daten. Schreibt cmr_herkunft.json.
Netzwerkregel: Zeitlimit je Anfrage, wachsende Pausen, Protokoll jeder Wiederholung."""
import json
import sys
import time
import urllib.request

ZEITLIMIT_SEKUNDEN = 90  # CMR antwortet sonst in 1-5 s; 90 s fängt langsame Seiten mit 2000 Einträgen ab
VERSUCHE = 4  # danach Abbruch mit Meldung, kein endloses Warten
PAUSE_BASIS_SEKUNDEN = 10  # 10, 20, 40 s

URL = ("https://cmr.earthdata.nasa.gov/search/granules.umm_json?short_name=VNP46A3&version=2"
       "&temporal={a}T00:00:00Z,{e}T00:00:00Z&page_size=2000")


def hole(url, headers):
    for v in range(VERSUCHE):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=ZEITLIMIT_SEKUNDEN) as r:
                return json.loads(r.read()), dict(r.headers)
        except Exception as f:  # noqa: BLE001
            if v == VERSUCHE - 1:
                raise
            p = PAUSE_BASIS_SEKUNDEN * 2**v
            print(f"CMR Versuch {v + 1}/{VERSUCHE} gescheitert ({type(f).__name__}), Pause {p} s", file=sys.stderr, flush=True)
            time.sleep(p)


aus = {}
for j in range(2013, 2023):
    for m in range(1, 13):
        a = f"{j}-{m:02d}-01"
        e = f"{j + (m == 12)}-{(m % 12) + 1:02d}-01"
        eintraege, headers, suche = [], {}, None
        while True:
            h = {"CMR-Search-After": suche} if suche else {}
            d, kopf = hole(URL.format(a=a, e=e), h)
            for it in d["items"]:
                u = it["umm"]
                name = u["DataGranule"]["Identifiers"][0]["Identifier"]
                if f".A{j}{(time.strptime(a, '%Y-%m-%d').tm_yday):03d}." not in name:
                    continue  # Nachbarmonat (Zeitspanne berührt die Grenze)
                eintraege.append({
                    "datei": name, "pge": u.get("PGEVersionClass", {}).get("PGEVersion"),
                    "erzeugt": u["DataGranule"].get("ProductionDateTime"),
                    "eingefuegt": next((x["Date"] for x in u.get("ProviderDates", []) if x["Type"] == "Insert"), None),
                    "version": u["CollectionReference"]["Version"],
                })
            suche = kopf.get("CMR-Search-After") or kopf.get("cmr-search-after")
            if not d["items"] or not suche:
                break
        aus[f"{j}-{m:02d}"] = eintraege
        print(f"{j}-{m:02d}: {len(eintraege)} Dateien", flush=True)
json.dump(aus, open(sys.argv[1], "w"))
