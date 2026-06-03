"""Regressao da Onda 4a (Fundacao & Calibracao): canary conforme + calibracao C6 sustentada."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def audit_out():
    return subprocess.run(
        [sys.executable, "scripts/audits/doc_audit.py", "--report-only", "--skip-dup"],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout


def test_canary_hora_conforme(audit_out):
    """docs/hora carimbado na 4a nao pode ter achado estrutural (C1/C3/C5/C6/C7)."""
    bad = [
        l for l in audit_out.splitlines()
        if l[:2] in ("C1", "C3", "C5", "C6", "C7") and "docs/hora" in l
    ]
    assert bad == [], f"docs/hora deve estar conforme; achou {bad}"


def test_c6_zerado_apos_isencao_skill_md(audit_out):
    """A isencao de C6 para SKILL.md (calibracao 4a) deve manter C6 global em 0."""
    c6 = [l for l in audit_out.splitlines() if l.startswith("C6")]
    assert c6 == [], f"C6 deve estar zerado (SKILL.md isento); achou {len(c6)}: {c6[:5]}"


def test_toolchain_importavel():
    """Os modulos da toolchain importam sem erro (smoke de pacote scripts.docs)."""
    sys.path.insert(0, str(ROOT))
    from scripts.docs import _doc_meta, migrar_doc_meta, completar_index  # noqa: F401
    assert callable(migrar_doc_meta.classify)
    assert callable(completar_index.run)
    assert callable(_doc_meta.build_header)
