"""
Smoke test de integração dos Relatórios Semanais.

Não valida correção de negócio (isso depende de dados reais via MCP Render);
valida que o PIPELINE inteiro executa contra o banco local sem erro de
coluna/import e produz um .zip com as 3 planilhas .xlsx válidas.
"""
import io
import zipfile

import pytest


@pytest.mark.integration
def test_gerar_zip_retorna_3_planilhas_validas(db):
    from app.manufatura.services.relatorios_semanais_service import (
        RelatoriosSemanaisService,
    )

    conteudo = RelatoriosSemanaisService.gerar_zip()

    assert isinstance(conteudo, (bytes, bytearray))
    assert len(conteudo) > 0

    zf = zipfile.ZipFile(io.BytesIO(conteudo))
    nomes = set(zf.namelist())
    assert nomes == {
        "consumo_componentes.xlsx",
        "estoques.xlsx",
        "tempo_estoque.xlsx",
    }
    # cada entrada deve ser um xlsx válido (xlsx é um zip → magic 'PK')
    for nome in nomes:
        dados = zf.read(nome)
        assert dados[:2] == b"PK", f"{nome} não é um xlsx válido"


@pytest.mark.integration
def test_estoque_nunca_negativo_nos_relatorios(db):
    import pandas as pd

    from app.manufatura.services.relatorios_semanais_service import (
        RelatoriosSemanaisService,
    )

    planilhas = RelatoriosSemanaisService.gerar_planilhas()
    for nome, conteudo in planilhas.items():
        xls = pd.ExcelFile(io.BytesIO(conteudo))
        for aba in xls.sheet_names:
            df = xls.parse(aba)
            if "estoque" in df.columns:
                negativos = df.loc[df["estoque"] < 0, "estoque"].tolist()
                assert not negativos, f"{nome}/{aba} tem estoque negativo: {negativos[:5]}"


@pytest.mark.integration
def test_rotas_registradas_no_blueprint(app):
    from flask import url_for

    with app.test_request_context():
        assert url_for("relatorios_semanais.index") == "/manufatura/relatorios-semanais/"
        assert url_for("relatorios_semanais.gerar") == "/manufatura/relatorios-semanais/gerar"


@pytest.mark.integration
def test_pagina_index_renderiza(app):
    # LOGIN_DISABLED=True no fixture de app → login_required é ignorado
    client = app.test_client()
    resp = client.get("/manufatura/relatorios-semanais/")
    assert resp.status_code == 200
    assert "Relatórios Semanais".encode("utf-8") in resp.data
