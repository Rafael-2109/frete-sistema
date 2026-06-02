# tests/audits/test_artefato_checks_script.py
from scripts.audits.artefato_lint import checks_script as csr, config
C = config.load()

def _w(tmp, rel, txt):
    p = tmp / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(txt, encoding="utf-8"); return p

def test_id_hardcoded(tmp_path):
    p = _w(tmp_path, "scripts/inventario_2026_05/consolidar_lote_104000015.py", "x=1\n")
    fs = csr.check_file(p, tmp_path, C, index_basenames=set())
    assert any(f.code == "SC-ID" for f in fs)

def test_script_orfao(tmp_path):
    p = _w(tmp_path, "scripts/inventario_2026_05/foo.py", "# tipo: script\n# etapa: 1\n# doc-dono: x\n# hub: y\n")
    fs = csr.check_file(p, tmp_path, C, index_basenames=set())
    assert any(f.code == "SC-ORFAO" for f in fs)

def test_script_indexado_ok(tmp_path):
    p = _w(tmp_path, "scripts/inventario_2026_05/foo.py", "# tipo: script\n# etapa: 1\n# doc-dono: x\n# hub: y\n")
    fs = csr.check_file(p, tmp_path, C, index_basenames={"foo.py"})
    assert [f for f in fs if f.code == "SC-ORFAO"] == []
