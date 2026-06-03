from scripts.audits.artefato_lint import config

def test_config_carrega_limiares_fixados():
    c = config.load()
    assert c.dup_textual_block == 0.85
    assert c.dup_semantic_block == 0.92
    assert c.toc_min_lines == 100
    assert any("docs" in g for g in c.managed_doc_globs)
    assert "atualmente" in c.banned_time_sensitive
    assert "dezenas" in c.banned_hedge

def test_config_tem_secoes_por_tipo():
    c = config.load()
    # Onda 4 (calibracao hibrida): reference exige so Papel; Fontes virou opcional (D2 advisory).
    assert set(["Papel"]).issubset(set(c.required_sections["reference"]))
    assert "Fontes" not in c.required_sections["reference"]
    assert set(["Rollback", "Verificacao"]).issubset(set(c.required_sections["runbook"]))
    assert set(["Status", "Contexto", "Decisao", "Consequencias"]).issubset(set(c.required_sections["adr"]))
