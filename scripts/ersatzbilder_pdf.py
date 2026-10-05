"""Ersatzbilder-PDF für die Präsentation bauen (falls der Laptop streikt).

Eingabe: eine JSON-Liste von Seiten [{"bild": "<pfad.png>", "titel": "...", "text": "..."}]. Daraus entsteht eine
HTML-Seite (eine Querformat-Seite je Bild, Bildunterschrift darunter), die Chrome ohne Fenster als PDF druckt
(DevTools-Befehl Page.printToPDF). Nur lokale Dateien, kein Netz.

Zeitlimits wie scripts/globus_fotos.py (CHROME_START_S; lokale Verbindung zu Chrome, Wiederholung mit wachsender Pause).

Aufruf:  python scripts/ersatzbilder_pdf.py <seiten.json> <ziel.pdf>
"""

from __future__ import annotations

import asyncio
import base64
import html
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from globus_fotos import CHROME, CHROME_START_S, PORT, Tab, _json  # noqa: E402

DRUCK_ZEITLIMIT_S = 120  # 20 Bilder à ~400 kB brauchen in Chrome wenige Sekunden; Reserve für das MacBook 2015


def baue_html(seiten: list[dict]) -> str:
    teile = []
    for i, s in enumerate(seiten, 1):
        teile.append(
            '<section class="seite"><img src="' + Path(s["bild"]).resolve().as_uri() + '">'
            '<div class="unter"><b>' + str(i) + " · " + html.escape(s["titel"]) + "</b> – " + html.escape(s["text"]) + "</div></section>")
    return ("<!doctype html><html lang=de><meta charset=utf-8><style>"
            "@page{size:297mm 210mm;margin:8mm}body{margin:0;font:11pt 'Helvetica Neue',Arial,sans-serif;color:#111}"
            ".seite{page-break-after:always;height:192mm;display:flex;flex-direction:column}"
            ".seite:last-child{page-break-after:auto}img{width:100%;height:170mm;object-fit:contain}"
            ".unter{margin-top:3mm;line-height:1.35}</style><body>" + "".join(teile) + "</body></html>")


async def drucke(html_pfad: Path, ziel: Path) -> None:
    profil = tempfile.mkdtemp(prefix="aleph_chrome_")
    proc = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={profil}",
                             "--allow-file-access-from-files", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
                await tab.cmd("Page.enable")
                await tab.cmd("Page.navigate", url=html_pfad.as_uri())
                t1 = time.time()
                while not await tab.js('document.readyState === "complete" && Array.prototype.every.call(document.images, function (i) { return i.complete && i.naturalWidth > 0; })'):
                    if time.time() - t1 > DRUCK_ZEITLIMIT_S:
                        raise RuntimeError("Bilder nicht rechtzeitig geladen (fehlt eine Datei?)")
                    await asyncio.sleep(0.5)
                r = await asyncio.wait_for(tab.cmd("Page.printToPDF", preferCSSPageSize=True, printBackground=True),
                                           timeout=DRUCK_ZEITLIMIT_S)
                ziel.write_bytes(base64.b64decode(r["data"]))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main(argv=None) -> int:
    a = argv if argv is not None else sys.argv[1:]
    if len(a) != 2:
        print(__doc__)
        return 2
    seiten = json.loads(Path(a[0]).read_text(encoding="utf-8"))
    for s in seiten:
        if not Path(s["bild"]).exists():
            print(f"Abbruch: Bild fehlt: {s['bild']}", file=sys.stderr)
            return 1
    with tempfile.TemporaryDirectory() as d:
        h = Path(d) / "ersatzbilder.html"
        h.write_text(baue_html(seiten), encoding="utf-8")
        asyncio.run(drucke(h, Path(a[1])))
    print(f"{len(seiten)} Seiten → {a[1]} ({Path(a[1]).stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
