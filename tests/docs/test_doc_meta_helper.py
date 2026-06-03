import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.docs import _doc_meta

def test_build_header_campos_obrigatorios():
    h = _doc_meta.build_header(tipo="explanation", hub="docs/INDEX.md",
                               data="2026-06-02", camada="L3", sot_de="—")
    for campo in ("tipo: explanation", "camada: L3", "sot_de: —",
                  "hub: docs/INDEX.md", "superseded_by: —", "atualizado: 2026-06-02"):
        assert campo in h, f"header faltando {campo!r}: {h}"
    assert h.startswith("<!-- doc:meta") and "-->" in h

def test_required_section_stubs_pula_papel():
    class _Cfg:
        required_sections = {"runbook": ["Papel", "Pre-condicoes", "Passos", "Rollback", "Verificacao"]}
    stubs = _doc_meta.required_section_stubs("runbook", _Cfg())
    assert stubs == ["## Pre-condicoes", "## Passos", "## Rollback", "## Verificacao"]
    assert all(not s.lower().endswith("papel") for s in stubs)

def test_gen_toc_pula_fenced_e_gera_anchors():
    txt = ("# T\n\n## Alpha\n\ntexto\n\n```\n## NaoConta\n```\n\n## Beta Dois\n\nfim\n")
    toc = _doc_meta.gen_toc(txt)
    assert "## Indice" in toc
    assert "- [Alpha](#alpha)" in toc
    assert "- [Beta Dois](#beta-dois)" in toc
    assert "NaoConta" not in toc, "heading dentro de fence nao entra no TOC"
