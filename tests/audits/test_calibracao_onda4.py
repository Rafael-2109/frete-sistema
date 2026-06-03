import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.audits.artefato_lint import config, checks_struct, checks_content

def _write(tmp_path, rel, text):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p

def test_reference_sem_fontes_nao_gera_c5(tmp_path):
    cfg = config.load()
    doc = ("<!-- doc:meta\ntipo: reference\ncamada: L2\nsot_de: x\n"
           "hub: docs/INDEX.md\nsuperseded_by: —\natualizado: 2026-06-02\n-->\n"
           "# T\n\n> **Papel:** y.\n\n## Conteudo\n\nfoo\n")
    p = _write(tmp_path, "docs/x.md", doc)
    (tmp_path / "docs" / "INDEX.md").write_text("# i", encoding="utf-8")
    codes = [f.code for f in checks_struct.check_file(p, tmp_path, cfg)]
    assert "C5" not in codes, f"Fontes nao deve mais ser obrigatoria em reference; achou {codes}"

def test_d2_fontes_advisory_quando_flag_false(tmp_path):
    cfg = config.load()
    doc = ("<!-- doc:meta\ntipo: reference\ncamada: L2\nsot_de: x\n"
           "hub: docs/INDEX.md\nsuperseded_by: —\natualizado: 2026-06-02\n-->\n"
           "# T\n\n> **Papel:** y.\n\n## Conteudo\n\nfoo sem citacao\n")
    p = _write(tmp_path, "docs/y.md", doc)
    fs = checks_content.check_file(p, tmp_path, cfg)
    d2 = [f for f in fs if f.code == "D2"]
    assert d2, "D2 ainda deve ser EMITIDO (visibilidade)"
    assert all(f.severity == "report" for f in d2), f"D2 deve ser advisory: {[f.severity for f in d2]}"

def test_skill_md_isento_de_c6(tmp_path):
    cfg = config.load()
    body = "---\nname: foo\ndescription: bar\n---\n\n# Skill\n" + ("\nlinha" * 130)
    p = _write(tmp_path, ".claude/skills/foo/SKILL.md", body)
    codes = [f.code for f in checks_struct.check_file(p, tmp_path, cfg)]
    assert "C6" not in codes, f"SKILL.md deve ser isento de C6; achou {codes}"
