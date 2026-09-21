"""NASA-Earthdata-Login für alle NASA-Layer.

Die Zugangsdaten stehen nur in .env (EARTHDATA_USERNAME, EARTHDATA_PASSWORD)
und werden zur Laufzeit geladen. Dieses Modul gibt niemals einen Wert aus,
auch keine Fehlermeldung: Ausgegeben wird nur "Login geklappt" oder
"Login fehlgeschlagen".

Aufruf zum Testen (im Projektordner):
    .venv/bin/python -m aleph.core.auth
"""

import contextlib
import io
import logging
from pathlib import Path

import earthaccess
from dotenv import load_dotenv

ENV_DATEI = Path(__file__).resolve().parents[2] / ".env"


def earthdata_login() -> bool:
    """Meldet sich bei NASA Earthdata an. True bei Erfolg, sonst False.

    earthaccess liest die Zugangsdaten selbst aus den Umgebungsvariablen
    (strategy="environment"). Eigene Ausgaben von earthaccess und jede
    Fehlermeldung werden verworfen, damit nichts durchsickern kann.
    """
    load_dotenv(ENV_DATEI)
    logging.disable(logging.CRITICAL)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            auth = earthaccess.login(strategy="environment")
        return bool(getattr(auth, "authenticated", False))
    except Exception:
        return False
    finally:
        logging.disable(logging.NOTSET)


def main() -> int:
    ok = earthdata_login()
    print("Login geklappt" if ok else "Login fehlgeschlagen")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
