from pathlib import Path
from scripts.audits.artefato_lint import checks_reach, config

CFG = config.load()
ROOT = Path(".")

def _run(docs):
    return checks_reach.check_reachability(docs, CFG, ROOT)

def _codes(fs, sub):
    return [f for f in fs if f.code == "C8" and sub in f.message]

def test_hub_lista_filho_reachable():
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "`docs/INDEX.md`"},
            "docs/INDEX.md": {"tipo": "index", "hub": "docs/INDEX.md", "text": "- [a](./sub/a.md)"},
            "docs/sub/a.md": {"tipo": "reference", "hub": "docs/INDEX.md", "text": "x"}}
    fs = _run(docs)
    assert not [f for f in fs if f.path == "docs/sub/a.md" and "orfao" in f.message]

def test_doc_sem_hub_orfao():
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "nada"},
            "b.md": {"tipo": "reference", "hub": None, "text": "x"}}
    fs = _run(docs)
    assert any(f.path == "b.md" and "orfao" in f.message and f.severity == "report" for f in fs)

def test_bidir_doc_declara_hub_mas_hub_nao_lista():
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "`I.md`"},
            "I.md": {"tipo": "index", "hub": "I.md", "text": "sem ponteiros"},
            "a.md": {"tipo": "reference", "hub": "I.md", "text": "x"}}
    fs = _run(docs)
    assert _codes(fs, "item-9")

def test_codespan_credita_aresta():
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "`H.md`"},
            "H.md": {"tipo": "index", "hub": "H.md", "text": "ponteiro `c.md` aqui"},
            "c.md": {"tipo": "reference", "hub": "H.md", "text": "x"}}
    fs = _run(docs)
    assert not [f for f in fs if f.path == "c.md" and "orfao" in f.message]

def test_link_only_nao_propaga_por_doc_conteudo():
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "`H.md`"},
            "H.md": {"tipo": "index", "hub": "H.md", "text": "- [x](X.md)"},
            "X.md": {"tipo": "reference", "hub": "H.md", "text": "- [y](Y.md)"},
            "Y.md": {"tipo": "reference", "hub": None, "text": "z"}}
    fs = _run(docs)
    assert any(f.path == "Y.md" and "orfao" in f.message for f in fs)

def test_claude_md_modulo_propaga():
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "`app/x/CLAUDE.md`"},
            "app/x/CLAUDE.md": {"tipo": "", "hub": None, "text": "- [r](ROADMAP.md)"},
            "app/x/ROADMAP.md": {"tipo": "reference", "hub": None, "text": "x"}}
    fs = _run(docs)
    assert not [f for f in fs if f.path == "app/x/ROADMAP.md" and "orfao" in f.message]

def test_severidade_report_nao_altera_exit():
    from scripts.audits.artefato_lint import findings
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "nada"},
            "o.md": {"tipo": "reference", "hub": None, "text": "x"}}
    fs = _run(docs)
    assert fs and findings.exit_code(fs) == 0

def test_hub_missing_file():
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "`a.md`"},
            "a.md": {"tipo": "reference", "hub": "naoexiste/INDEX.md", "text": "x"}}
    fs = _run(docs)
    assert _codes(fs, "inexistente")

def test_tool_reachable_skill_nao_e_orfao():
    # .claude/skills/** = reachable-by-tool: NUNCA vira C8-ORPHAN (invariante do plano item 7)
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "nada"},
            ".claude/skills/foo/SKILL.md": {"tipo": "", "hub": None, "text": "x"}}
    fs = _run(docs)
    assert not [f for f in fs if f.path == ".claude/skills/foo/SKILL.md"]

def test_fenced_nao_credita_aresta():
    # link dentro de bloco fenced NAO conta como aresta -> filho fica orfao
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "`H.md`"},
            "H.md": {"tipo": "index", "hub": "H.md", "text": "```\n- [c](./c.md)\n```"},
            "c.md": {"tipo": "reference", "hub": None, "text": "x"}}
    fs = _run(docs)
    assert any(f.path == "c.md" and "orfao" in f.message for f in fs)
