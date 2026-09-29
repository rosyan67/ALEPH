"""Globus unsichtbar in Chrome öffnen, prüfen und Bildschirmfotos machen (nur für Prüfungen und Ersatzbilder).

Startet Google Chrome ohne Fenster (headless, Software-Grafik), steuert es über das DevTools-Protokoll
(aiohttp, schon in der Umgebung) und macht je Ansicht ein Foto. Es wird nichts an Daten verändert.
Nur lokale Dateien (file://), kein Netzwerkzugriff nach außen.

Zeitlimits (Regel „Netzwerk“ in CLAUDE.md, hier nur lokale Verbindung zu Chrome):
- CHROME_START_S: so lange wird auf den DevTools-Anschluss gewartet (Chrome startet auf dem MacBook 2015 in
  wenigen Sekunden; 30 s lassen Reserve, danach Abbruch mit Meldung).
- SEITE_BEREIT_S: so lange wird auf data-bereit="1" gewartet (Globus mit Software-Grafik braucht 10–40 s).
- Wiederholung: der DevTools-Anschluss wird bis zu 3-mal mit wachsender Pause (1, 2, 4 s) versucht.

Aufruf:  python scripts/globus_fotos.py <ausgabeordner> <name>=<hash> [<name>=<hash> ...]
         <hash> ist der Teil hinter # in der Adresse, z. B. zeitreihe=DEU oder vergleich=DEU,EGY&index=1
         Zusatz „@<js>“ hinter dem Hash führt nach dem Laden JavaScript aus (z. B. einen Klick).
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import aiohttp

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME_START_S = 30
SEITE_BEREIT_S = 90
VERBINDUNG_VERSUCHE = 3
PORT = 9333
SEITE = Path(__file__).resolve().parents[1] / "web" / "globus.html"


async def _json(session, url):
    for versuch in range(VERBINDUNG_VERSUCHE):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                return await r.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError):
            print(f"  DevTools nicht erreichbar, Versuch {versuch + 1}", file=sys.stderr)
            await asyncio.sleep(2 ** versuch)
    raise RuntimeError("DevTools-Anschluss nicht erreichbar")


class Tab:
    def __init__(self, ws):
        self.ws, self.n = ws, 0

    async def cmd(self, methode, **params):
        self.n += 1
        mid = self.n
        await self.ws.send_json({"id": mid, "method": methode, "params": params})
        while True:
            m = await asyncio.wait_for(self.ws.receive_json(), timeout=SEITE_BEREIT_S)
            if m.get("id") == mid:
                if "error" in m:
                    raise RuntimeError(f"{methode}: {m['error']}")
                return m.get("result", {})

    async def js(self, ausdruck):
        r = await self.cmd("Runtime.evaluate", expression=ausdruck, returnByValue=True, awaitPromise=True)
        return r.get("result", {}).get("value")


async def fotos(ziel: Path, ansichten: list[tuple[str, str, str]], breite=1440, hoehe=900) -> dict:
    ziel.mkdir(parents=True, exist_ok=True)
    profil = tempfile.mkdtemp(prefix="aleph_chrome_")
    proc = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={profil}",
                             "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--allow-file-access-from-files",
                             f"--window-size={breite},{hoehe}", "--hide-scrollbars", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ergebnis = {}
    try:
        async with aiohttp.ClientSession() as s:
            t0 = time.time()
            while True:
                try:
                    liste = await _json(s, f"http://127.0.0.1:{PORT}/json")
                    seite = [x for x in liste if x.get("type") == "page"][0]
                    break
                except (RuntimeError, IndexError):
                    if time.time() - t0 > CHROME_START_S:
                        raise RuntimeError("Chrome hat den DevTools-Anschluss nicht rechtzeitig geöffnet")
                    await asyncio.sleep(1)
            async with s.ws_connect(seite["webSocketDebuggerUrl"], max_msg_size=0) as ws:
                tab = Tab(ws)
                await tab.cmd("Emulation.setDeviceMetricsOverride", width=breite, height=hoehe, deviceScaleFactor=1, mobile=False)
                for name, hsh, nachher in ansichten:
                    await tab.cmd("Page.navigate", url="about:blank")
                    await tab.cmd("Page.navigate", url=SEITE.as_uri() + "#" + hsh)
                    t1 = time.time()
                    while not await tab.js('document.body && document.body.getAttribute("data-bereit") === "1"'):
                        if time.time() - t1 > SEITE_BEREIT_S:
                            raise RuntimeError(f"{name}: Seite nicht bereit nach {SEITE_BEREIT_S} s")
                        await asyncio.sleep(0.5)
                    if nachher:
                        await tab.js(nachher)
                    await asyncio.sleep(4)  # Flug der Kamera und Zeichnen abwarten
                    fehler = await tab.js('(function(){var f=document.getElementById("fehler");return f&&!f.hidden?f.textContent:"";})()')
                    bild = await tab.cmd("Page.captureScreenshot", format="png")
                    pfad = ziel / f"{name}.png"
                    pfad.write_bytes(base64.b64decode(bild["data"]))
                    ergebnis[name] = {"datei": str(pfad), "fehler": fehler, "sekunden": round(time.time() - t1, 1)}
                    print(f"{name}: {pfad.name}, bereit nach {ergebnis[name]['sekunden']} s, Fehleranzeige: {fehler or 'keine'}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    return ergebnis


def main(argv=None) -> int:
    a = argv if argv is not None else sys.argv[1:]
    if len(a) < 2:
        print(__doc__)
        return 2
    ansichten = []
    for teil in a[1:]:
        name, _, rest = teil.partition("=")
        hsh, _, nachher = rest.partition("@")
        ansichten.append((name, hsh, nachher))
    e = asyncio.run(fotos(Path(a[0]), ansichten))
    print(json.dumps(e, ensure_ascii=False))
    return 1 if any(v["fehler"] for v in e.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
