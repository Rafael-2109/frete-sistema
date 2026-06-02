# tests/audits/test_artefato_zones.py
from scripts.audits.artefato_lint import zones, config

C = config.load()

def test_doc_gerenciado():
    assert zones.is_managed_doc("docs/x.md", C) is True
    assert zones.is_managed_doc(".claude/references/Y.md", C) is True
    assert zones.is_managed_doc("README.md", C) is False  # raiz nao-CLAUDE nao e gerenciado por glob

def test_script_operacional():
    assert zones.is_operational_script("scripts/inventario_2026_05/15_x.py", C) is True
    assert zones.is_operational_script("app/utils/foo.py", C) is False

def test_ignore_e_scratch():
    assert zones.is_ignored("app/tests/fixtures/x.md", C) is True
    assert zones.is_scratch("<!-- doc:meta\ntipo: scratch\n-->\n") is True

def test_deep_subpaths():
    # Extra assertions: ** must match ANY depth (not just one level) on Python 3.12
    assert zones.is_managed_doc("docs/a/b/c/x.md", C) is True
    assert zones.is_operational_script("scripts/inventario_2026_05/sub/dir/15_x.py", C) is True
