"""Erzeugungszeit und PGE-Version der Eingangsprodukte (VNP46A1, VNP46A2 je Kachel h20v05 am 15. des Monats;
VNP02DNB erste Datei des 15.) für 2013-01..2022-12, aus dem öffentlichen CMR. Nur Metadaten.
Netzwerkregel: Zeitlimit, wachsende Pausen, Meldung je Wiederholung."""
import json
import sys
import time
import urllib.request

ZEITLIMIT_SEKUNDEN = 90  # CMR antwortet sonst in 1-5 s
VERSUCHE = 4
PAUSE_BASIS_SEKUNDEN = 10  # 10, 20, 40 s


def hole(url):
    for v in range(VERSUCHE):
        try:
            with urllib.request.urlopen(url, timeout=ZEITLIMIT_SEKUNDEN) as r:
                return json.loads(r.read())
        except Exception as f:  # noqa: BLE001
            if v == VERSUCHE - 1:
                raise
            p = PAUSE_BASIS_SEKUNDEN * 2**v
            print(f"CMR Versuch {v + 1}/{VERSUCHE} gescheitert ({type(f).__name__}), Pause {p} s", file=sys.stderr, flush=True)
            time.sleep(p)


def info(produkt, tag, kachel=None):
    url = (f"https://cmr.earthdata.nasa.gov/search/granules.umm_json?short_name={produkt}&version=2"
           f"&temporal={tag}T00:00:00Z,{tag}T23:59:59Z&page_size=2000")
    d = hole(url)
    for it in d["items"]:
        u = it["umm"]
        name = u["DataGranule"]["Identifiers"][0]["Identifier"]
        if kachel and f".{kachel}." not in name:
            continue
        return {"datei": name, "pge": u.get("PGEVersionClass", {}).get("PGEVersion"),
                "erzeugt": u["DataGranule"].get("ProductionDateTime"), "treffer": d.get("hits")}
    return {"datei": None, "treffer": d.get("hits")}


aus = {}
for j in range(2013, 2023):
    for m in range(1, 13):
        tag = f"{j}-{m:02d}-15"
        aus[tag] = {p: info(p, tag, "h20v05") for p in ("VNP46A1", "VNP46A2")}
        aus[tag]["VNP02DNB"] = info("VNP02DNB", tag)
        print(tag, {k: (v.get("pge"), (v.get("erzeugt") or "")[:10]) for k, v in aus[tag].items()}, flush=True)
json.dump(aus, open(sys.argv[1], "w"), indent=1)
