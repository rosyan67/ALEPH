import json, ast, datetime as dt, sys
S = sys.argv[1]
tage = {}
tage.update(json.load(open(f"{S}/wechsel_teil0.json")))
for l in open(f"{S}/wechsel_teil1.log"):
    d, rest = l.split(" ", 1)
    tage[d] = ast.literal_eval(rest.strip())
tage.update(json.load(open(f"{S}/wechsel_teil2.json")))
a = dt.date(2013, 1, 1); fehlt = []
while a <= dt.date(2022, 12, 31):
    if str(a) not in tage: fehlt.append(str(a))
    a += dt.timedelta(days=1)
leer = [d for d, z in tage.items() if not z]
print("Tage", len(tage), "fehlend", fehlt[:10], len(fehlt), "ohne Dateien", leer[:20], len(leer))
aus = {"quelle": "NASA CMR granules.umm_json, short_name=VNP02DNB, version=2; Zähler je Tag: 'PGE Erzeugungsmonat' -> Dateien",
       "abgerufen": "2026-10-05", "tage": dict(sorted((k, v) for k, v in tage.items() if k < "2023"))}
json.dump(aus, open(sys.argv[2], "w"), indent=0)
