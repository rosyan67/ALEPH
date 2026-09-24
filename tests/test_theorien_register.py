"""Prüft die Pflichtangaben zur Quellenprüfung im Theorie-Register (theories/*.yaml).

Regel (CLAUDE.md, ARCHITECTURE.md Abschnitt 8): Jede Quelle trägt
`citation_verified` (true/false) und `verifiziert_umfang` (metadaten |
originaltext). `originaltext` nur bei `citation_verified: true`; `null` nur bei
`citation_verified: false`.
"""

import glob
from pathlib import Path

import pytest
import yaml

THEORIEN = sorted(glob.glob(str(Path(__file__).resolve().parents[1] / "theories" / "*.yaml")))
UMFANG = {"metadaten", "originaltext"}


def _quellen():
    for datei in THEORIEN:
        eintrag = yaml.safe_load(Path(datei).read_text(encoding="utf-8"))
        for i, quelle in enumerate(eintrag["quellen"]):
            yield pytest.param(quelle, id=f"{Path(datei).stem}#{i}")


def test_register_ist_nicht_leer():
    assert len(THEORIEN) >= 8


@pytest.mark.parametrize("quelle", _quellen())
def test_quelle_hat_gueltigen_verifiziert_umfang(quelle):
    assert isinstance(quelle.get("citation_verified"), bool)
    assert "verifiziert_umfang" in quelle, "Pflichtfeld verifiziert_umfang fehlt"
    umfang = quelle["verifiziert_umfang"]
    if quelle["citation_verified"]:
        assert umfang in UMFANG
    else:
        assert umfang in UMFANG | {None}


@pytest.mark.parametrize("quelle", _quellen())
def test_originaltext_nur_bei_bestaetigter_quelle(quelle):
    if quelle["verifiziert_umfang"] == "originaltext":
        assert quelle["citation_verified"] is True


def test_anzahl_quellen_und_verteilung_sind_stabil_dokumentiert():
    """74 Quellen (Stand 2026-09-24); nur 4 mit ausdrücklich gelesenem Volltext."""
    alle = [q for d in THEORIEN for q in yaml.safe_load(Path(d).read_text(encoding="utf-8"))["quellen"]]
    assert len(alle) == 74
    assert sum(1 for q in alle if q["verifiziert_umfang"] == "originaltext") == 4
