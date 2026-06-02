# tests/audits/test_artefato_checks_content.py
from pathlib import Path
from scripts.audits.artefato_lint import checks_content as cc, config
C = config.load()

REF = ("<!-- doc:meta\ntipo: reference\ncamada: L2\nsot_de: x\nhub: docs/INDEX.md\n"
       "superseded_by: —\natualizado: 2026-06-01\n-->\n# T\n")

def _w(tmp, rel, txt):
    p = tmp / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(txt, encoding="utf-8"); return p

def test_marker_refutado(tmp_path):
    p = _w(tmp_path, "docs/a.md", REF + "tabela X 🔴 TABELA REFUTADA\n## Fontes\n")
    fs = cc.check_file(p, tmp_path, C)
    assert any(f.code == "B5" for f in fs)

def test_hedge_banido(tmp_path):
    p = _w(tmp_path, "docs/a.md", REF + "havia varios registros\n## Fontes\nFONTE: x\n")
    fs = cc.check_file(p, tmp_path, C)
    assert any(f.code == "D4" for f in fs)

def test_reference_sem_citacao(tmp_path):
    p = _w(tmp_path, "docs/a.md", REF + "afirmo um fato\n")  # sem ## Fontes nem FONTE:
    fs = cc.check_file(p, tmp_path, C)
    assert any(f.code == "D2" for f in fs)

def test_acuracia_campo_inexistente(tmp_path):
    # schema fake
    sd = tmp_path / ".claude/skills/consultando-sql/schemas/tables"; sd.mkdir(parents=True)
    (sd / "separacao.json").write_text('{"fields":[{"name":"qtd_saldo"}]}', encoding="utf-8")
    p = _w(tmp_path, "docs/a.md", REF + "use Separacao.campo_inexistente\n## Fontes\nFONTE: x\n")
    fs = cc.check_file(p, tmp_path, C)
    assert any(f.code == "D3" for f in fs)
