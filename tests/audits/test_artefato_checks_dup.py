# tests/audits/test_artefato_checks_dup.py
from scripts.audits.artefato_lint import checks_dup as cd, config
C = config.load()

def test_near_dup_textual_bloqueia():
    a = "A regra de fila RQ exige editar tres arquivos no worker e no start."
    b = "A regra de fila RQ exige editar tres arquivos no worker e no start de novo."
    fs = cd.compare_blocks({"docs/a.md": a, "docs/b.md": b}, C)
    assert any(f.code == "D5" and f.severity == "block" for f in fs)

def test_textos_distintos_nao_disparam():
    fs = cd.compare_blocks({"docs/a.md": "frete para manaus", "docs/b.md": "balanco contabil sped"}, C)
    assert fs == []

def test_semantic_stub_noop():
    # Onda 0: semantic e no-op (sem Voyage); so garante interface
    assert cd.semantic_compare({"docs/a.md": "x"}, C) == []
