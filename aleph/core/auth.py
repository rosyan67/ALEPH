"""NASA-Earthdata-Login für alle NASA-Layer.

Die Zugangsdaten stehen nur in .env (EARTHDATA_USERNAME, EARTHDATA_PASSWORD)
und werden zur Laufzeit geladen. Dieses Modul gibt niemals einen Wert aus,
auch keine Fehlermeldung: Ausgegeben wird nur "Login geklappt" oder
"Login fehlgeschlagen", bei Fehlern dazu die Art des Fehlers (Klassenname,
HTTP-Status), nie der Meldungstext von earthaccess oder requests.

Wiederholung (Auftrag 2026-09-27): Am 26.09. um 22:01 UTC hat ein einziger
fehlgeschlagener Login den ganzen Download beendet; 16 Stunden gingen
verloren, im Browser ging der Login danach wieder. Ursache im Code:
`earthaccess.login()` legt bei JEDEM Aufruf eine neue Sitzung an und ruft
dabei `https://urs.earthdata.nasa.gov/profile` ab (Store.__init__, ohne
Zeitlimit). Ein kurzer Netz- oder Serverfehler dort wurde zu „Login
fehlgeschlagen“, obwohl die Zugangsdaten stimmten. Deshalb:
- `earthdata_login()` ordnet den Fehler ein (`LoginErgebnis.art`):
  `ABGELEHNT` (NASA weist die Zugangsdaten zurück), `NICHT_ERREICHBAR`
  (Netz, Zeitüberschreitung, Serverfehler, Wartung), `ZUGANGSDATEN_FEHLEN`.
- `login_mit_wiederholung()` wiederholt mit wachsenden Pausen
  (`LOGIN_PAUSEN_MINUTEN`, zusammen gut eine Stunde). Ist der Dienst danach
  weiter nicht erreichbar, wird bis `LOGIN_AUSFALL_HOECHSTENS_STUNDEN` alle
  `LOGIN_AUSFALL_PAUSE_MINUTEN` weiter versucht. Wird die Anmeldung auch am
  Ende der Reihe noch abgelehnt, ist Schluss mit einer verständlichen Meldung.
  Fehlen die Zugangsdaten ganz, wird sofort abgebrochen (Warten ändert
  nichts).
- Bekannte Grenze: earthaccess meldet eine abgelehnte Anmeldung
  (`LoginAttemptFailure`) ohne HTTP-Status. Antwortet der Anmeldedienst
  während einer Wartung an dieser Stelle mit einem Fehler, sieht das aus wie
  „abgelehnt“ und endet nach der Reihe (gut eine Stunde) statt nach 12
  Stunden. Das ist so gewählt, weil falsche Zugangsdaten nicht 12 Stunden
  lang wiederholt werden sollen (Kontosperre möglich).

Aufruf zum Testen (im Projektordner):
    .venv/bin/python -m aleph.core.auth
"""

import concurrent.futures
import contextlib
import io
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import earthaccess
import requests
from dotenv import load_dotenv
from earthaccess.exceptions import LoginAttemptFailure, LoginStrategyUnavailable, ServiceOutage

ENV_DATEI = Path(__file__).resolve().parents[2] / ".env"

OK = "ok"
ABGELEHNT = "abgelehnt"
NICHT_ERREICHBAR = "nicht erreichbar"
ZUGANGSDATEN_FEHLEN = "Zugangsdaten fehlen"

# Pausen zwischen den Login-Versuchen, wachsend: Eine kurze Störung (wie am
# 26.09.) ist nach 1-2 Minuten überbrückt; eine längere wird nicht mit Anfragen
# überflutet. Zusammen 63 Minuten, also die verlangte Größenordnung „bis etwa
# 60 Minuten“. Nach dem letzten Versuch dieser Reihe endet eine ABGELEHNTE
# Anmeldung.
LOGIN_PAUSEN_MINUTEN = (1, 2, 5, 10, 15, 30)

# Ist der Anmeldedienst nach der Reihe weiterhin NICHT ERREICHBAR (Netz,
# Serverfehler, Wartung), wird in diesem Abstand weiter versucht: Der Lauf
# verliert dann nur die Zeit der Störung selbst, statt ganz zu enden.
LOGIN_AUSFALL_PAUSE_MINUTEN = 30

# Obergrenze für das Warten auf einen nicht erreichbaren Anmeldedienst,
# gezählt ab dem ersten Fehlschlag. Gleich lang wie die Notbremse je Monat
# (vnp46a3.MONAT_NOTBREMSE_SEKUNDEN, 12 h): Länger soll der Lauf nicht
# unbeobachtet warten; dann soll ein Mensch nachsehen (Netz? NASA?).
LOGIN_AUSFALL_HOECHSTENS_STUNDEN = 12

# Zeitlimit je Login-Versuch. earthaccess ruft beim Login /profile OHNE
# Zeitlimit ab; hinge diese Anfrage, bliebe der Lauf sonst unbegrenzt stehen
# (Befund plausibilitaets-pruefer 2026-09-27). Ein normaler Login dauert
# Sekunden; 2 Minuten lassen einer langsamen Leitung reichlich Luft. Ein
# hängender Versuch zählt als „nicht erreichbar“; sein Thread wird aufgegeben
# (er lässt sich nicht beenden, sein Ergebnis wird ignoriert), wie bei den
# Kachel-Downloads in aleph/layers/vnp46a3.py.
LOGIN_ZEITLIMIT_SEKUNDEN = 120


@dataclass
class LoginErgebnis:
    """Ergebnis eines Login-Versuchs. Wahr genau dann, wenn der Login geklappt hat.

    `beschreibung` enthält nur die Art des Fehlers (Klassenname, HTTP-Status),
    nie einen Meldungstext, damit keine Zugangsdaten durchsickern können.
    """

    art: str
    beschreibung: str = ""
    versuche: int = 1
    gewartet_sekunden: float = 0.0

    @property
    def ok(self) -> bool:
        return self.art == OK

    def __bool__(self) -> bool:
        return self.ok


def _einordnen(fehler: BaseException) -> LoginErgebnis:
    if isinstance(fehler, LoginStrategyUnavailable):
        return LoginErgebnis(ZUGANGSDATEN_FEHLEN, "EARTHDATA_USERNAME/EARTHDATA_PASSWORD nicht gesetzt")
    if isinstance(fehler, LoginAttemptFailure):
        return LoginErgebnis(ABGELEHNT, "Anmeldedienst lehnt die Anmeldung ab (LoginAttemptFailure)")
    if isinstance(fehler, requests.HTTPError):
        status = getattr(getattr(fehler, "response", None), "status_code", None)
        if status in (401, 403):
            return LoginErgebnis(ABGELEHNT, f"HTTP {status}")
        return LoginErgebnis(NICHT_ERREICHBAR, f"HTTP {status}" if status else "HTTPError")
    if isinstance(fehler, (requests.RequestException, OSError, ServiceOutage)):
        return LoginErgebnis(NICHT_ERREICHBAR, type(fehler).__name__)
    # Unbekannte Art: wie „abgelehnt“ behandeln (endet nach der Reihe), damit
    # ein Programmfehler nicht 12 Stunden lang wiederholt wird.
    return LoginErgebnis(ABGELEHNT, f"unbekannter Fehler ({type(fehler).__name__})")


def earthdata_login(zeitlimit_sekunden: float = LOGIN_ZEITLIMIT_SEKUNDEN) -> LoginErgebnis:
    """Meldet sich bei NASA Earthdata an. Wahr bei Erfolg (siehe `LoginErgebnis`).

    earthaccess liest die Zugangsdaten selbst aus den Umgebungsvariablen
    (strategy="environment"). Eigene Ausgaben von earthaccess und jede
    Fehlermeldung werden verworfen, damit nichts durchsickern kann.
    """
    load_dotenv(ENV_DATEI)
    logging.disable(logging.CRITICAL)
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            future = pool.submit(earthaccess.login, strategy="environment")
            try:
                auth = future.result(timeout=zeitlimit_sekunden)
            except concurrent.futures.TimeoutError:
                return LoginErgebnis(NICHT_ERREICHBAR, f"keine Antwort nach {zeitlimit_sekunden:.0f} s")
        if getattr(auth, "authenticated", False):
            return LoginErgebnis(OK)
        return LoginErgebnis(ABGELEHNT, "nicht angemeldet (ohne Fehlermeldung)")
    except Exception as fehler:  # bewusst breit: jeder Fehler wird eingeordnet, nie ausgegeben
        return _einordnen(fehler)
    finally:
        pool.shutdown(wait=False)
        logging.disable(logging.NOTSET)


def _jetzt_utc() -> datetime:
    return datetime.now(timezone.utc)


def login_mit_wiederholung(
    login=earthdata_login,
    melde=None,
    schlafe=time.sleep,
    pausen_minuten=LOGIN_PAUSEN_MINUTEN,
    ausfall_pause_minuten=LOGIN_AUSFALL_PAUSE_MINUTEN,
    ausfall_hoechstens_stunden=LOGIN_AUSFALL_HOECHSTENS_STUNDEN,
) -> LoginErgebnis:
    """Login mit Wiederholung (Regeln siehe Moduldoku). Gibt das letzte Ergebnis zurück.

    `login` liefert ein `LoginErgebnis` oder bool (False zählt als „abgelehnt,
    Art unbekannt“). `melde(text)` bekommt je Fehlschlag eine Zeile, die mit
    „wartet auf NASA-Login, Versuch n“ beginnt (das Status-Skript erkennt sie),
    und nach Erfolg eine Zeile „NASA-Login wieder erfolgreich“.
    """
    versuch = 0
    gewartet = 0.0
    while True:
        versuch += 1
        ergebnis = login()
        if not isinstance(ergebnis, LoginErgebnis):
            ergebnis = LoginErgebnis(OK) if ergebnis else LoginErgebnis(ABGELEHNT, "Login meldet Fehlschlag")
        ergebnis.versuche, ergebnis.gewartet_sekunden = versuch, gewartet
        if ergebnis.ok:
            if versuch > 1 and melde is not None:
                melde(f"NASA-Login wieder erfolgreich (Versuch {versuch}, nach {gewartet / 60:.0f} Minuten Warten).")
            return ergebnis
        if ergebnis.art == ZUGANGSDATEN_FEHLEN:
            return ergebnis
        if versuch <= len(pausen_minuten):
            pause = pausen_minuten[versuch - 1]
        elif (
            ergebnis.art == NICHT_ERREICHBAR
            and gewartet + ausfall_pause_minuten * 60 <= ausfall_hoechstens_stunden * 3600
        ):
            pause = ausfall_pause_minuten
        else:
            return ergebnis
        if melde is not None:
            naechster = _jetzt_utc() + timedelta(minutes=pause)
            melde(
                f"wartet auf NASA-Login, Versuch {versuch} fehlgeschlagen ({ergebnis.art}: {ergebnis.beschreibung}); "
                f"nächster Versuch in {pause} Minuten, um {naechster:%H:%M} UTC."
            )
        schlafe(pause * 60)
        gewartet += pause * 60


def abbruch_meldung(ergebnis: LoginErgebnis) -> str:
    """Verständliche Meldung, wenn `login_mit_wiederholung` endgültig gescheitert ist."""
    dauer = ergebnis.gewartet_sekunden / 60
    dauer_text = f"{dauer / 60:.1f} Stunden" if dauer >= 90 else f"{dauer:.0f} Minuten"
    rest = "Fertige Monate und geladene Rohdaten bleiben erhalten; scripts/vnp46a3_start.sh setzt fort."
    if ergebnis.art == ZUGANGSDATEN_FEHLEN:
        return (
            "NASA-Earthdata-Login nicht möglich: EARTHDATA_USERNAME und EARTHDATA_PASSWORD fehlen in .env. "
            + rest
        )
    if ergebnis.art == NICHT_ERREICHBAR:
        return (
            f"NASA-Earthdata-Login nach {ergebnis.versuche} Versuchen in {dauer_text} weiterhin nicht erreichbar "
            f"({ergebnis.beschreibung}). Vermutlich eine Störung des Netzes oder bei NASA, nicht die Zugangsdaten. "
            "Internetverbindung prüfen und im Browser bei Earthdata anmelden; wenn das geht, neu starten. " + rest
        )
    return (
        f"NASA-Earthdata-Login nach {ergebnis.versuche} Versuchen in {dauer_text} weiterhin abgelehnt "
        f"({ergebnis.beschreibung}). Vermutlich stimmen die Zugangsdaten nicht (mehr) oder das Konto ist gesperrt: "
        "im Browser bei Earthdata anmelden und EARTHDATA_USERNAME/EARTHDATA_PASSWORD in .env prüfen. " + rest
    )


def main() -> int:
    ergebnis = earthdata_login()
    print("Login geklappt" if ergebnis else "Login fehlgeschlagen")
    return 0 if ergebnis else 1


if __name__ == "__main__":
    raise SystemExit(main())
