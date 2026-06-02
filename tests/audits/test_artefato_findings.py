# tests/audits/test_artefato_findings.py
from scripts.audits.artefato_lint.findings import Finding, exit_code, render

def test_exit_code_block():
    fs = [Finding("C1", "x.md", 1, "header faltando", "block")]
    assert exit_code(fs) == 1

def test_exit_code_ok_quando_so_report():
    fs = [Finding("D5", "x.md", 1, "near-dup 0.80", "report")]
    assert exit_code(fs) == 0

def test_render_inclui_codigo_e_path():
    out = render([Finding("C7", "docs/x.md", 12, "link morto ../y.md", "block")])
    assert "C7" in out and "docs/x.md" in out and "12" in out
