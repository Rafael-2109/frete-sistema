"""Regressao PAD-A Onda 3: a zona de scripts de inventario/estoque deve permanecer governada.

Trava o resultado da Onda 3: script_audit.py nao pode achar NENHUM SC-ORFAO / SC-HEADER /
SC-ID na zona (`scripts/inventario_2026_05/**` + `app/odoo/estoque/scripts/**`). Se um novo
script for adicionado sem header/indice, ou um ID de objeto voltar a um nome, este teste falha.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _audit_zone_findings():
    out = subprocess.run(
        [sys.executable, "scripts/audits/script_audit.py", "--report-only"],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout
    return [ln for ln in out.splitlines() if ln.startswith("SC-")]


def test_zona_inventario_sem_orfao_header_id():
    findings = _audit_zone_findings()
    assert findings == [], (
        f"zona de scripts deve estar governada (0 achados script_audit); "
        f"achou {len(findings)}: {findings[:10]}"
    )
