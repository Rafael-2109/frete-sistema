import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.docs import completar_index as CI
from scripts.audits.artefato_lint import config, checks_struct

def test_cria_index_listando_todos_os_leaves(tmp_path):
    d = tmp_path / "docs" / "area"
    d.mkdir(parents=True)
    (d / "a.md").write_text("# Alpha", encoding="utf-8")
    (d / "b.md").write_text("# Beta", encoding="utf-8")
    assert CI.run(scope_root=tmp_path, subdir="docs/area", create=True, write=True) == 0
    idx = (d / "INDEX.md").read_text(encoding="utf-8")
    assert "tipo: index" in idx
    assert "a.md" in idx and "b.md" in idx
    assert "Alpha" in idx and "Beta" in idx
    # o INDEX gerado deve passar o lint (sem bloqueante)
    cfg = config.load()
    blk = [f for f in checks_struct.check_file(d / "INDEX.md", tmp_path, cfg) if f.severity == "block"]
    assert blk == [], f"INDEX gerado deve ser lint-verde; {[(f.code,f.message) for f in blk]}"

def test_dry_run_nao_grava(tmp_path):
    d = tmp_path / "docs" / "area2"
    d.mkdir(parents=True)
    (d / "a.md").write_text("# A", encoding="utf-8")
    assert CI.run(scope_root=tmp_path, subdir="docs/area2", create=True, write=False) == 0
    assert not (d / "INDEX.md").exists(), "dry-run nao pode gravar INDEX"

def test_completa_index_existente_so_faltantes(tmp_path):
    d = tmp_path / "docs" / "area3"
    d.mkdir(parents=True)
    (d / "a.md").write_text("# A", encoding="utf-8")
    (d / "b.md").write_text("# B", encoding="utf-8")
    (d / "INDEX.md").write_text(
        "<!-- doc:meta\ntipo: index\ncamada: L1\nsot_de: —\nhub: docs/area3/INDEX.md\n"
        "superseded_by: —\natualizado: 2026-06-02\n-->\n# area3\n\n> **Papel:** x. So ponteiros.\n\n- [A](a.md)\n",
        encoding="utf-8")
    assert CI.run(scope_root=tmp_path, subdir="docs/area3", create=False, write=True) == 0
    idx = (d / "INDEX.md").read_text(encoding="utf-8")
    assert idx.count("a.md") == 1, "nao pode duplicar o ja-listado"
    assert "b.md" in idx, "deve adicionar o faltante"

def test_nao_confunde_substring_de_outro_leaf(tmp_path):
    d = tmp_path / "docs" / "area4"
    d.mkdir(parents=True)
    (d / "a.md").write_text("# A", encoding="utf-8")
    (d / "ba.md").write_text("# BA", encoding="utf-8")
    (d / "INDEX.md").write_text(
        "<!-- doc:meta\ntipo: index\ncamada: L1\nsot_de: —\nhub: docs/area4/INDEX.md\n"
        "superseded_by: —\natualizado: 2026-06-02\n-->\n# area4\n\n> **Papel:** x. So ponteiros.\n\n- [BA](ba.md)\n",
        encoding="utf-8")
    assert CI.run(scope_root=tmp_path, subdir="docs/area4", create=False, write=True) == 0
    idx = (d / "INDEX.md").read_text(encoding="utf-8")
    assert "(a.md)" in idx, "'a.md' deve entrar (nao confundir com substring de 'ba.md')"
    assert idx.count("ba.md") == 1, "'ba.md' nao pode duplicar"
