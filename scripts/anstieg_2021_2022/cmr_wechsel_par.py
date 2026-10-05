"""Wie cmr_wechsel.py, aber 8 Tage gleichzeitig. Zeitlimit 90 s je Anfrage, 4 Versuche, Pausen 10/20/40 s."""
import json, sys, time, urllib.request, datetime as dt, collections, concurrent.futures as cf
ZEITLIMIT_SEKUNDEN = 90  # CMR antwortet sonst in 1-10 s; 90 s fängt langsame Seiten (~1 MB) ab
VERSUCHE = 4  # danach Abbruch mit Meldung, kein endloses Warten
PAUSE_BASIS_SEKUNDEN = 10  # wachsende Pausen 10, 20, 40 s
PARALLEL = 8  # 8 Tage gleichzeitig: sequenziell ~9 s je Tag (7 h für 2013-2020), so ~45 min; CMR ohne Fehler
def hole(url):
    for v in range(VERSUCHE):
        try:
            with urllib.request.urlopen(url, timeout=ZEITLIMIT_SEKUNDEN) as r: return json.loads(r.read())
        except Exception as f:
            if v == VERSUCHE - 1: raise
            p = PAUSE_BASIS_SEKUNDEN * 2**v; print(f"Versuch {v+1} gescheitert ({type(f).__name__}), Pause {p} s", file=sys.stderr, flush=True); time.sleep(p)
def tag(d):
    u = hole(f"https://cmr.earthdata.nasa.gov/search/granules.umm_json?short_name=VNP02DNB&version=2&temporal={d}T00:00:00Z,{d}T23:59:59Z&page_size=400")
    c = collections.Counter((it["umm"].get("PGEVersionClass", {}).get("PGEVersion"), it["umm"]["DataGranule"]["ProductionDateTime"][:7]) for it in u["items"])
    return str(d), {f"{k[0]} {k[1]}": n for k, n in c.items()}
a, e = [dt.date.fromisoformat(x) for x in sys.argv[1:3]]
tage = [a + dt.timedelta(days=i) for i in range((e - a).days + 1)]
aus = {}
with cf.ThreadPoolExecutor(PARALLEL) as pool:
    for i, (d, z) in enumerate(pool.map(tag, tage)):
        aus[d] = z
        if i % 50 == 0: print(d, z, flush=True)
json.dump(dict(sorted(aus.items())), open(sys.argv[3], "w"), indent=1)
print("FERTIG", len(aus))
