"""PGE-Version aller VNP02DNB-Dateien je Tag (CMR, öffentlich). Zeitlimit 90 s, 4 Versuche, Pausen 10/20/40 s."""
import json, sys, time, urllib.request, datetime as dt, collections
ZEITLIMIT_SEKUNDEN = 90  # CMR antwortet sonst in 1-10 s; 90 s fängt langsame Seiten (~1 MB) ab
VERSUCHE = 4  # danach Abbruch mit Meldung, kein endloses Warten
PAUSE_BASIS_SEKUNDEN = 10  # wachsende Pausen 10, 20, 40 s
def hole(url):
    for v in range(VERSUCHE):
        try:
            with urllib.request.urlopen(url, timeout=ZEITLIMIT_SEKUNDEN) as r: return json.loads(r.read())
        except Exception as f:
            if v == VERSUCHE - 1: raise
            p = PAUSE_BASIS_SEKUNDEN * 2**v; print(f"Versuch {v+1} gescheitert ({type(f).__name__}), Pause {p} s", file=sys.stderr); time.sleep(p)
a, e = [dt.date.fromisoformat(x) for x in sys.argv[1:3]]; aus = {}
d = a
while d <= e:
    u = hole(f"https://cmr.earthdata.nasa.gov/search/granules.umm_json?short_name=VNP02DNB&version=2&temporal={d}T00:00:00Z,{d}T23:59:59Z&page_size=400")
    c = collections.Counter((it["umm"].get("PGEVersionClass", {}).get("PGEVersion"), it["umm"]["DataGranule"]["ProductionDateTime"][:7]) for it in u["items"])
    aus[str(d)] = {f"{k[0]} {k[1]}": n for k, n in c.items()}; print(d, aus[str(d)], flush=True); d += dt.timedelta(days=1)
json.dump(aus, open(sys.argv[3], "w"), indent=1)
