"""Teste determinístico do gerador da skill gerando-controle-recebiveis.

Cobre a parte PURA (gerar_excel: situacao, agrupamento por gestor, subtotais,
drop de coluna vazia) sem tocar o banco. A query (buscar_titulos) é validada
contra PROD via MCP no fluxo dev, não aqui.
"""
import os
import sys

import pytest

_SCRIPTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..",
    ".claude", "skills", "gerando-controle-recebiveis", "scripts",
)
_SCRIPTS_DIR = os.path.abspath(_SCRIPTS_DIR)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import gerar_controle_recebiveis as G  # noqa: E402

openpyxl = pytest.importorskip("openpyxl")


def _titulos():
    return [
        # CONFIRMADO (pago) — gestor DENISE
        dict(titulo_nf="100", parcela="1", empresa=3, cnpj="42.385.121/0001-49",
             raz_social="A. T. BORGES LTDA", uf_cliente="SP", emissao="2026-04-01",
             vencimento="2026-05-01", valor_original=1000.0, valor_residual=0.0,
             parcela_paga=True, vendedor="Camila", gestor="VENDA INTERNA DENISE",
             situacao="CONFIRMADO"),
        # Vencido — gestor DENISE
        dict(titulo_nf="101", parcela="2", empresa=3, cnpj="42.385.121/0001-49",
             raz_social="A. T. BORGES LTDA", uf_cliente="SP", emissao="2026-04-01",
             vencimento="2026-06-01", valor_original=1000.0, valor_residual=1000.0,
             parcela_paga=False, vendedor="Camila", gestor="VENDA INTERNA DENISE",
             situacao="Vencido"),
        # Vencido — gestor MILER
        dict(titulo_nf="200", parcela="1", empresa=3, cnpj="07.258.484/0001-00",
             raz_social="IZANITA", uf_cliente="MG", emissao="2026-04-10",
             vencimento="2026-06-05", valor_original=500.0, valor_residual=500.0,
             parcela_paga=False, vendedor="Rep X", gestor="VENDA EXTERNA MILER",
             situacao="Vencido"),
        # Em Aberto — gestor MILER
        dict(titulo_nf="201", parcela="1", empresa=3, cnpj="07.258.484/0001-00",
             raz_social="IZANITA", uf_cliente="MG", emissao="2026-04-10",
             vencimento="2099-01-01", valor_original=500.0, valor_residual=500.0,
             parcela_paga=False, vendedor="Rep X", gestor="VENDA EXTERNA MILER",
             situacao="Em Aberto"),
        # Vencido — SEM gestor (cai para vendedor)
        dict(titulo_nf="300", parcela="1", empresa=3, cnpj="99.999.999/0001-00",
             raz_social="CLIENTE SEM EQUIPE", uf_cliente="RJ", emissao="2026-04-10",
             vencimento="2026-06-02", valor_original=250.0, valor_residual=250.0,
             parcela_paga=False, vendedor="Vendedor Z", gestor="", situacao="Vencido"),
    ]


def test_resumo_e_situacoes(tmp_path):
    fp = str(tmp_path / "c.xlsx")
    resumo = G.gerar_excel(_titulos(), fp)
    assert resumo["total"] == 5
    assert resumo["confirmado"] == 1
    assert resumo["vencido"] == 3
    assert resumo["em_aberto"] == 1
    # valor vencido = 1000 + 500 + 250
    assert resumo["valor_vencido"] == 1750.0
    assert os.path.getsize(fp) > 0


def test_abas_e_agrupamento_por_gestor(tmp_path):
    fp = str(tmp_path / "c.xlsx")
    G.gerar_excel(_titulos(), fp)
    wb = openpyxl.load_workbook(fp)
    assert wb.sheetnames == ["Titulos", "Vencidos"]
    venc_text = "\n".join(
        str(c.value) for row in wb["Vencidos"].iter_rows() for c in row if c.value
    )
    # 3 grupos na aba Vencidos: DENISE, MILER e o fallback por vendedor
    assert "Gestor: VENDA INTERNA DENISE" in venc_text
    assert "Gestor: VENDA EXTERNA MILER" in venc_text
    assert "Vendedor Z" in venc_text          # fallback quando gestor vazio
    assert "Subtotal" in venc_text
    assert "TOTAL GERAL VENCIDOS" in venc_text
    # Em Aberto (201) NAO entra em Vencidos
    assert "201" not in venc_text


def test_drop_coluna_gestor_quando_vazia(tmp_path):
    fp = str(tmp_path / "c.xlsx")
    titulos = [dict(t) for t in _titulos()]
    for t in titulos:
        t["gestor"] = ""           # todos sem gestor -> coluna Gestor sai
    G.gerar_excel(titulos, fp)
    wb = openpyxl.load_workbook(fp)
    headers = [c.value for c in wb["Titulos"][1]]
    assert "Gestor" not in headers
    assert "Cliente" in headers
