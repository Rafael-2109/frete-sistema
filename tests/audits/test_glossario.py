# tests/audits/test_glossario.py
from scripts.audits.artefato_lint import checks_content as cc, config
C = config.load()

REF = ("<!-- doc:meta\ntipo: reference\ncamada: L2\nsot_de: x\nhub: docs/INDEX.md\n"
       "superseded_by: —\natualizado: 2026-06-02\n-->\n# T\n")

def _w(tmp, rel, txt):
    p = tmp / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(txt, encoding="utf-8"); return p

def test_glossario_termo_banido_dispara_d1(tmp_path):
    glos = {"empresa_id": "company_id"}
    p = _w(tmp_path, "docs/a.md", REF + "use empresa_id para filtrar\n## Fontes\nFONTE: x\n")
    fs = cc.check_glossario(p, tmp_path, C, glossario=glos)
    assert any(f.code == "D1" for f in fs)

def test_glossario_termo_canonico_nao_dispara(tmp_path):
    glos = {"empresa_id": "company_id"}
    p = _w(tmp_path, "docs/a.md", REF + "use company_id para filtrar\n## Fontes\nFONTE: x\n")
    fs = cc.check_glossario(p, tmp_path, C, glossario=glos)
    assert [f for f in fs if f.code == "D1"] == []

def test_glossario_pula_o_proprio_glossario(tmp_path):
    glos = {"empresa_id": "company_id"}
    p = _w(tmp_path, ".claude/references/GLOSSARIO.md", REF + "empresa_id e banido\n## Fontes\nFONTE: x\n")
    fs = cc.check_glossario(p, tmp_path, C, glossario=glos)
    assert [f for f in fs if f.code == "D1"] == []  # o glossario DEFINE os termos, nao se auto-acusa
