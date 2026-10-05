"""Startzeit des Globus messen (nur Prüfung; verändert keine Daten).

Öffnet web/globus.html mehrmals in Chrome ohne Fenster (wie scripts/globus_fotos.py, Software-Grafik) und
misst je Durchgang:
- skripte_ms: bis alle Datendateien und Programmteile geladen und ausgeführt sind (DOMContentLoaded),
- bereit_ms: bis der Globus mit dem ersten Monat fertig gezeichnet ist (data-bereit="1"),
- js_heap_mb: belegter JavaScript-Speicher danach,
- daten_mb: Größe der beim Start geladenen Dateien in web/daten/ (ohne Monatsdateien, die erst bei Auswahl laden).

Die Software-Grafik ist deutlich langsamer als ein echtes Chrome-Fenster mit Grafikkarte; die Werte taugen
für den Vergleich vorher/nachher, nicht als absolute Startzeit auf dem Präsentationsrechner.

Zeitlimits wie in globus_fotos.py (CHROME_START_S, SEITE_BEREIT_S; nur lokale Verbindung zu Chrome).

Aufruf:  python scripts/globus_startzeit.py [durchgaenge]
"""

from __future__ import annotations

import asyncio
import json
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from globus_fotos import CHROME, CHROME_START_S, PORT, SEITE, SEITE_BEREIT_S, Tab, _json  # noqa: E402


def startdateien() -> list[Path]:
    """Dateien aus web/daten/, die globus.html beim Start per <script> lädt."""
    html = SEITE.read_text(encoding="utf-8")
    return [SEITE.parent / p for p in re.findall(r'<script src="(daten/[^"]+)"', html)]


async def messen(durchgaenge: int) -> list[dict]:
    profil = tempfile.mkdtemp(prefix="aleph_chrome_")
    proc = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={profil}",
                             "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--allow-file-access-from-files",
                             "--window-size=1440,900", "--hide-scrollbars", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    werte = []
    try:
        async with aiohttp.ClientSession() as s:
            t0 = time.time()
            while True:
                try:
                    seite = [x for x in await _json(s, f"http://127.0.0.1:{PORT}/json") if x.get("type") == "page"][0]
                    break
                except (RuntimeError, IndexError):
                    if time.time() - t0 > CHROME_START_S:
                        raise RuntimeError("Chrome hat den DevTools-Anschluss nicht rechtzeitig geöffnet")
                    await asyncio.sleep(1)
            async with s.ws_connect(seite["webSocketDebuggerUrl"], max_msg_size=0) as ws:
                tab = Tab(ws)
                await tab.cmd("Emulation.setDeviceMetricsOverride", width=1440, height=900, deviceScaleFactor=1, mobile=False)
                for _ in range(durchgaenge):
                    await tab.cmd("Page.navigate", url="about:blank")
                    await tab.cmd("Page.navigate", url=SEITE.as_uri())
                    t1 = time.time()
                    while not await tab.js('document.body && document.body.getAttribute("data-bereit") === "1"'):
                        if time.time() - t1 > SEITE_BEREIT_S:
                            raise RuntimeError(f"Seite nicht bereit nach {SEITE_BEREIT_S} s")
                        await asyncio.sleep(0.2)
                    r = await tab.js(
                        '(function(){var n=performance.getEntriesByType("navigation")[0];'
                        'var f=document.getElementById("fehler");'
                        'return {skripte_ms:Math.round(n.domContentLoadedEventEnd),'
                        'bereit_ms:Math.round(window.ALEPH_BEREIT_MS||performance.now()),'
                        'js_heap_mb:performance.memory?Math.round(performance.memory.usedJSHeapSize/1e6):null,'
                        'monate:(window.ALEPH_DATENSTAND&&window.ALEPH_DATENSTAND.angezeigt||[]).length,'
                        'fehler:f&&!f.hidden?f.textContent:""};})()')
                    werte.append(r)
                    print(json.dumps(r, ensure_ascii=False))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    return werte


def main(argv=None) -> int:
    a = argv if argv is not None else sys.argv[1:]
    n = int(a[0]) if a else 3
    groessen = {p.name: round(p.stat().st_size / 1e6, 2) for p in startdateien() if p.exists()}
    print("Beim Start geladene Datendateien (MB):", json.dumps(groessen, ensure_ascii=False),
          "Summe", round(sum(groessen.values()), 1))
    w = asyncio.run(messen(n))
    for k in ("skripte_ms", "bereit_ms", "js_heap_mb"):
        v = [x[k] for x in w if x.get(k) is not None]
        if v:
            print(f"{k}: Median {statistics.median(v)}  (Werte {v})")
    return 1 if any(x["fehler"] for x in w) else 0


if __name__ == "__main__":
    raise SystemExit(main())
