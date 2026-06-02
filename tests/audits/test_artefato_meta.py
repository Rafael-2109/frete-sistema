from scripts.audits.artefato_lint import meta

DOC = """<!-- doc:meta
tipo: reference
camada: L2
sot_de: regras de frete
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-01
-->
# Titulo
"""

def test_parse_header_html_comment():
    m = meta.parse_doc(DOC)
    assert m.found is True
    assert m.fields["tipo"] == "reference"
    assert m.fields["camada"] == "L2"
    assert m.fields["hub"] == ".claude/references/INDEX.md"

def test_parse_header_ausente():
    m = meta.parse_doc("# Sem header\n")
    assert m.found is False

def test_parse_script_header():
    s = '"""x"""\n# tipo: script\n# etapa: 15\n# doc-dono: docs/x.md\n# hub: scripts/INDEX.md\n'
    m = meta.parse_script(s)
    assert m.fields["etapa"] == "15"
    assert m.fields["doc-dono"] == "docs/x.md"
