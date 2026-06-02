# tests/audits/test_artefato_checks_struct.py
from pathlib import Path
from scripts.audits.artefato_lint import checks_struct as cs, config
C = config.load()

def _w(tmp, rel, txt):
    p = tmp / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(txt, encoding="utf-8"); return p

HEAD = ("<!-- doc:meta\ntipo: reference\ncamada: L2\nsot_de: x\n"
        "hub: docs/INDEX.md\nsuperseded_by: —\natualizado: 2026-06-01\n-->\n")

def test_c1_header_invalido_tipo(tmp_path):
    p = _w(tmp_path, "docs/a.md", "<!-- doc:meta\ntipo: bogus\ncamada: L2\nhub: docs/INDEX.md\natualizado: 2026-06-01\nsot_de: x\n-->\n# T\n## Fontes\n")
    fs = cs.check_file(p, tmp_path, C)
    assert any(f.code == "C1" for f in fs)

def test_c3_hub_inexistente(tmp_path):
    p = _w(tmp_path, "docs/a.md", HEAD + "# T\n## Fontes\n")
    fs = cs.check_file(p, tmp_path, C)
    assert any(f.code == "C3" for f in fs)  # docs/INDEX.md nao existe

def test_c5_reference_sem_fontes(tmp_path):
    _w(tmp_path, "docs/INDEX.md", "<!-- doc:meta\ntipo: index\ncamada: L1\nhub: docs/INDEX.md\natualizado: 2026-06-01\nsot_de: —\n-->\n# i\n")
    p = _w(tmp_path, "docs/a.md", HEAD + "# T\nconteudo sem secao fontes\n")
    fs = cs.check_file(p, tmp_path, C)
    assert any(f.code == "C5" for f in fs)

def test_c7_link_rot(tmp_path):
    _w(tmp_path, "docs/INDEX.md", "<!-- doc:meta\ntipo: index\ncamada: L1\nhub: docs/INDEX.md\natualizado: 2026-06-01\nsot_de: —\n-->\n# i\n")
    p = _w(tmp_path, "docs/a.md", HEAD + "# T\nveja [x](../nao_existe.md)\n## Fontes\n")
    fs = cs.check_file(p, tmp_path, C)
    assert any(f.code == "C7" for f in fs)

def test_ok_completo(tmp_path):
    _w(tmp_path, "docs/INDEX.md", "<!-- doc:meta\ntipo: index\ncamada: L1\nhub: docs/INDEX.md\natualizado: 2026-06-01\nsot_de: —\n-->\n# i\n")
    p = _w(tmp_path, "docs/a.md", HEAD + "# T\n> **Papel:** descreve.\n## Fontes\nok\n")
    fs = cs.check_file(p, tmp_path, C)
    assert [f for f in fs if f.severity == "block"] == []

# --- Extra C7 cases (mandated by task spec) ---

def test_c7_root_relative_dead_link(tmp_path):
    """Root-relative dead link: docs/nao_existe.md (contains '/', not starting with '.')"""
    _w(tmp_path, "docs/INDEX.md", "<!-- doc:meta\ntipo: index\ncamada: L1\nhub: docs/INDEX.md\natualizado: 2026-06-01\nsot_de: —\n-->\n# i\n")
    p = _w(tmp_path, "docs/a.md", HEAD + "# T\n> **Papel:** descreve.\nveja [x](docs/nao_existe.md)\n## Fontes\n")
    fs = cs.check_file(p, tmp_path, C)
    assert any(f.code == "C7" for f in fs), "Root-relative dead link must produce C7"

def test_c7_valid_link_no_finding(tmp_path):
    """A VALID link must NOT produce C7."""
    _w(tmp_path, "docs/INDEX.md", "<!-- doc:meta\ntipo: index\ncamada: L1\nhub: docs/INDEX.md\natualizado: 2026-06-01\nsot_de: —\n-->\n# i\n")
    p = _w(tmp_path, "docs/a.md", HEAD + "# T\n> **Papel:** descreve.\nveja [indice](docs/INDEX.md)\n## Fontes\n")
    fs = cs.check_file(p, tmp_path, C)
    assert not any(f.code == "C7" for f in fs), "Valid root-relative link must NOT produce C7"

# --- C5 "Papel" via blockquote convention (PAD-A anatomia, spec §5) ---

def test_c5_papel_via_blockquote_ok(tmp_path):
    """reference com `> **Papel:**` (SEM heading ## Papel) + ## Fontes -> sem block."""
    _w(tmp_path, "docs/INDEX.md", "<!-- doc:meta\ntipo: index\ncamada: L1\nhub: docs/INDEX.md\natualizado: 2026-06-01\nsot_de: —\n-->\n# i\n")
    p = _w(tmp_path, "docs/a.md", HEAD + "# T\n> **Papel:** x\n## Fontes\nok\n")
    fs = cs.check_file(p, tmp_path, C)
    assert [f for f in fs if f.severity == "block"] == []

def test_c5_papel_com_texto_ok(tmp_path):
    """reference com `> **Papel deste doc:**` (texto antes do :) -> sem block."""
    _w(tmp_path, "docs/INDEX.md", "<!-- doc:meta\ntipo: index\ncamada: L1\nhub: docs/INDEX.md\natualizado: 2026-06-01\nsot_de: —\n-->\n# i\n")
    p = _w(tmp_path, "docs/a.md", HEAD + "# T\n> **Papel deste doc:** x\n## Fontes\nok\n")
    fs = cs.check_file(p, tmp_path, C)
    assert [f for f in fs if f.severity == "block"] == []

def test_c5_reference_sem_papel(tmp_path):
    """reference com ## Fontes mas SEM nenhum **Papel:** -> C5."""
    _w(tmp_path, "docs/INDEX.md", "<!-- doc:meta\ntipo: index\ncamada: L1\nhub: docs/INDEX.md\natualizado: 2026-06-01\nsot_de: —\n-->\n# i\n")
    p = _w(tmp_path, "docs/a.md", HEAD + "# T\nconteudo sem papel\n## Fontes\nok\n")
    fs = cs.check_file(p, tmp_path, C)
    assert any(f.code == "C5" for f in fs)
