"""Regressao PAD-A Onda 3: a zona de scripts de inventario/estoque deve permanecer governada.

Trava o resultado da Onda 3: todo script GIT-TRACKED da zona (`scripts/inventario_2026_05/**`
+ `app/odoo/estoque/scripts/**`) deve estar indexado (sem SC-ORFAO), ter header
(`# etapa:`/`# doc-dono:`, sem SC-HEADER) e nao ter ID de objeto no nome (sem SC-ID).

Considera APENAS arquivos rastreados pelo git. O `script_audit.py --report-only` escaneia o
filesystem (rglob), entao acabaria flaggando scripts LOCAIS gitignored (ex: ad-hoc de operacao
em `auditoria/`, ignorados em .gitignore) que nao fazem parte do repo e que governanca nao
cobre. O filtro git-tracked evita esse falso-negativo em ambientes de dev (passa em checkout
limpo/CI E no working tree local com extras gitignored).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _tracked_files() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
    ).stdout
    return set(out.split("\n"))


def _audit_findings_tracked() -> list[str]:
    out = subprocess.run(
        [sys.executable, "scripts/audits/script_audit.py", "--report-only"],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout
    tracked = _tracked_files()
    findings = []
    for ln in out.splitlines():
        if not ln.startswith("SC-"):
            continue
        parts = ln.split()
        # formato: "SC-XXX  block  <path>:<line>  <msg...>"
        if len(parts) < 3:
            continue
        path = parts[2].split(":", 1)[0]
        if path in tracked:
            findings.append(ln)
    return findings


def test_zona_inventario_tracked_governada():
    findings = _audit_findings_tracked()
    assert findings == [], (
        f"todo script git-tracked da zona deve estar governado (0 achados script_audit); "
        f"achou {len(findings)}: {findings[:10]}"
    )
