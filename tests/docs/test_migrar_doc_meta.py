import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.docs import migrar_doc_meta as M
from scripts.audits.artefato_lint import config, checks_struct, checks_content

def test_classify_minimiza_desmascaramento():
    casos = {
        ".claude/references/ssw/pops/POP-D06-x.md": "how-to",
        ".claude/references/ssw/fluxos/F01-x.md": "explanation",
        ".claude/references/ssw/visao-geral/x.md": "state",
        "docs/inventario-2026-05/99-historia/CHECKPOINT_x.md": "scratch",
        "docs/inventario-2026-05/00-decisoes/D007-x.md": "explanation",
        "app/odoo/CLAUDE.md": "explanation",
        ".claude/references/INFRAESTRUTURA.md": "reference",
        "docs/blueprint-agente/eixo-x.md": "explanation",
        "docs/hora/CHECKLIST_TAGPLUS_GO_LIVE.md": "how-to",
        "docs/devolucao/RUNBOOK_X.md": "how-to",
    }
    for rel, esperado in casos.items():
        tipo, _c = M.classify(rel, "conteudo")
        assert tipo == esperado, f"{rel}: esperava {esperado}, veio {tipo}"

def test_dry_run_nao_escreve(tmp_path, capsys):
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "INDEX.md").write_text("# i", encoding="utf-8")
    alvo = tmp_path / "docs" / "longo.md"
    alvo.write_text("# Titulo\n\n" + "\n".join(f"## S{i}\n\ntexto" for i in range(40)), encoding="utf-8")
    antes = alvo.read_text(encoding="utf-8")
    assert M.run(scope_root=tmp_path, paths=["docs/longo.md"], hub="docs/INDEX.md", write=False) == 0
    assert alvo.read_text(encoding="utf-8") == antes, "dry-run NAO pode escrever no doc real"
    out = capsys.readouterr().out
    assert "docs/longo.md" in out

def test_write_carimba_e_fica_verde(tmp_path):
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "INDEX.md").write_text("# i", encoding="utf-8")
    alvo = tmp_path / "docs" / "conhecimento.md"
    alvo.write_text("# Conhecimento\n\n" + "\n".join(f"## S{i}\n\ntexto" for i in range(40)), encoding="utf-8")
    assert M.run(scope_root=tmp_path, paths=["docs/conhecimento.md"], hub="docs/INDEX.md", write=True) == 0
    cfg = config.load()
    fs = checks_struct.check_file(alvo, tmp_path, cfg) + checks_content.check_file(alvo, tmp_path, cfg)
    blk = [(f.code, f.message) for f in fs if f.severity == "block"]
    assert blk == [], f"pos-carimbo deve ficar SEM bloqueante; restou {blk}"
    txt1 = alvo.read_text(encoding="utf-8")
    M.run(scope_root=tmp_path, paths=["docs/conhecimento.md"], hub="docs/INDEX.md", write=True)
    assert alvo.read_text(encoding="utf-8") == txt1, "segundo --write nao pode re-carimbar (idempotente)"

def test_tipo_override_flipa_classify(tmp_path):
    """--tipo/--camada forcam o tipo, sobrepondo o classify (review de cluster)."""
    (tmp_path / ".claude" / "references").mkdir(parents=True)
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "INDEX.md").write_text("# i", encoding="utf-8")
    alvo = tmp_path / ".claude" / "references" / "STUDY_X.md"
    alvo.write_text("# Study X\n\ntexto de estudo\n", encoding="utf-8")
    assert M.classify(".claude/references/STUDY_X.md", "x")[0] == "reference", "sem override = reference"
    M.run(scope_root=tmp_path, paths=[".claude/references/STUDY_X.md"], hub="docs/INDEX.md",
          write=True, tipo_override="explanation", camada_override="L3")
    txt = alvo.read_text(encoding="utf-8")
    assert "tipo: explanation" in txt and "camada: L3" in txt, txt[:120]
