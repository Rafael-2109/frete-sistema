"""Testes determinísticos do script consultando_venda_loja (Onda F).

Mock de atributos REAIS dos módulos (não patch.dict de sys.modules) + mock do
`db` inteiro no modo vendas → zero DB, zero PROD, zero app_context, $0 token.
"""
import datetime
import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".claude/skills/consultando-venda-loja/scripts/consultando_venda_loja.py"


def _load():
    spec = importlib.util.spec_from_file_location("consultando_venda_loja_mod", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["consultando_venda_loja_mod"] = mod
    spec.loader.exec_module(mod)
    return mod


def _row(**kw):
    return SimpleNamespace(**kw)


# ---------------------------------------------------------------- helpers
def test_parse_loja_ids():
    m = _load()
    assert m._parse_loja_ids("2,5") == [2, 5]
    assert m._parse_loja_ids("") is None
    assert m._parse_loja_ids(None) is None
    assert m._parse_loja_ids("x") is None


def test_json_default():
    m = _load()
    assert m._json_default(Decimal("1.50")) == 1.5
    assert m._json_default(datetime.date(2026, 6, 2)) == "2026-06-02"


# ---------------------------------------------------------------- modo vendas
def test_run_vendas_escopo_e_shaping():
    m = _load()
    lojas_rows = [_row(id=2, apelido="TATUAPE")]
    vendas_rows = [_row(id=9, status="CONFIRMADO", loja_id=2, data_venda="2026-06-01",
                        valor_total=12000, valor_frete=0, vendedor="Ana",
                        forma_pagamento="A_VISTA", nf_saida_numero=None,
                        cpf_cliente="12345678901", nome_cliente="Cliente X",
                        origem_criacao="MANUAL")]
    itens_rows = [_row(venda_id=9, numero_chassi="ABC123", modelo="BOB", cor="VERMELHA",
                       preco_final=12000, desconto_aplicado=990, desconto_percentual=7.62)]
    nfe_rows = []
    div_rows = []

    with patch.object(m, "db", MagicMock()) as dbmock:
        dbmock.session.execute.return_value.fetchall.side_effect = [
            lojas_rows, vendas_rows, itens_rows, nfe_rows, div_rows]
        res = m._run_vendas(loja_ids=[2], pode_ver_todas=False, venda_id=None,
                            chassi=None, status=None, somente_pendentes_nfe=False)

    assert res["escopo_aplicado"] == {"loja_ids": [2], "pode_ver_todas": False}
    assert res["total_vendas"] == 1
    v = res["vendas"][0]
    assert v["id"] == 9 and v["loja_apelido"] == "TATUAPE"
    assert v["nfe_status"] == "SEM_NFE"
    assert v["divergencias_abertas"] == 0
    assert v["itens"][0]["numero_chassi"] == "ABC123"
    assert v["itens"][0]["modelo"] == "BOB"


def test_run_vendas_escopo_nao_admin_monta_filtro_any():
    m = _load()
    with patch.object(m, "db", MagicMock()) as dbmock:
        # vendas vazia -> so 2 execucoes (lojas, vendas); sem itens/nfe/div
        dbmock.session.execute.return_value.fetchall.side_effect = [[], []]
        m._run_vendas([2], False, None, None, None, False)
        # 2a chamada de execute = query de vendas; checa que o SQL tem ANY(:ids)
        sql_vendas = dbmock.session.execute.call_args_list[1].args[0].text
    assert "= ANY(:ids)" in sql_vendas


def test_run_vendas_admin_sem_filtro_loja():
    m = _load()
    with patch.object(m, "db", MagicMock()) as dbmock:
        dbmock.session.execute.return_value.fetchall.side_effect = [[], []]
        m._run_vendas(None, True, None, None, None, False)
        sql_vendas = dbmock.session.execute.call_args_list[1].args[0].text
    assert "= ANY(:ids)" not in sql_vendas


def test_run_vendas_somente_pendentes_nfe():
    m = _load()
    with patch.object(m, "db", MagicMock()) as dbmock:
        dbmock.session.execute.return_value.fetchall.side_effect = [[], []]
        m._run_vendas(None, True, None, None, None, True)
        sql_vendas = dbmock.session.execute.call_args_list[1].args[0].text
    assert "v.nf_saida_numero IS NULL" in sql_vendas


# ---------------------------------------------------------------- modo preco
def test_run_preco_lookup_e_validacao():
    m = _load()
    preco_ret = {"preco": Decimal("12990.00"), "fonte": "modelo",
                 "tipo_pagamento": "A_VISTA", "preco_a_vista": Decimal("12990.00"),
                 "preco_a_prazo": Decimal("13990.00")}
    valid_ret = {"modelo_id": 10, "preco_referencia": Decimal("12990.00"),
                 "desconto_rs": Decimal("990.00"), "desconto_pct": Decimal("7.62"),
                 "tabela_id": 5, "divergencia": None}
    with patch("app.hora.services.venda_service.buscar_preco_para_pedido", return_value=preco_ret), \
         patch("app.hora.services.venda_service.validar_desconto_tabela", return_value=valid_ret):
        res = m._run_preco(modelo_id=10, modelo_nome=None,
                           forma_pagamento="A_VISTA", preco_final="12000")
    assert res["modelo_id"] == 10
    assert res["preco_tabela"] == Decimal("12990.00")
    assert res["preco_a_prazo"] == Decimal("13990.00")
    assert res["validacao_desconto"]["desconto_pct"] == Decimal("7.62")
    assert res["validacao_desconto"]["divergencia"] is None


def test_run_preco_sem_preco_final_nao_valida():
    m = _load()
    preco_ret = {"preco": Decimal("12990.00"), "fonte": "modelo",
                 "preco_a_vista": Decimal("12990.00"), "preco_a_prazo": None}
    with patch("app.hora.services.venda_service.buscar_preco_para_pedido", return_value=preco_ret):
        res = m._run_preco(10, None, "A_VISTA", None)
    assert "validacao_desconto" not in res
    assert res["preco_tabela"] == Decimal("12990.00")


# ---------------------------------------------------------------- modo margem
def test_run_margem_respeita_escopo():
    m = _load()
    venda = SimpleNamespace(id=9, loja_id=2)
    preview_ret = {"venda_total": Decimal("12000"), "frete": Decimal("0"),
                   "custo_moto_total": Decimal("9000"), "liquido": Decimal("3000"),
                   "margem_bruta": Decimal("9000"), "margem_pct": Decimal("75.00"),
                   "tem_custo_faltante": False, "itens": []}
    with patch("app.hora.models.venda.HoraVenda") as HV, \
         patch("app.hora.services.venda_preview_service.montar_preview", return_value=preview_ret):
        HV.query.get.return_value = venda
        ok = m._run_margem(venda_id=9, loja_ids=[2], pode_ver_todas=False)
        fora = m._run_margem(venda_id=9, loja_ids=[7], pode_ver_todas=False)

    assert ok["escopo_ok"] is True
    assert ok["preview"]["margem_pct"] == Decimal("75.00")
    assert fora.get("erro") == "fora_de_escopo"


def test_run_margem_admin_ve_qualquer_loja():
    m = _load()
    venda = SimpleNamespace(id=9, loja_id=None)
    preview_ret = {"margem_pct": Decimal("10.0")}
    with patch("app.hora.models.venda.HoraVenda") as HV, \
         patch("app.hora.services.venda_preview_service.montar_preview", return_value=preview_ret):
        HV.query.get.return_value = venda
        res = m._run_margem(venda_id=9, loja_ids=None, pode_ver_todas=True)
    assert res["escopo_ok"] is True


def test_run_margem_venda_inexistente():
    m = _load()
    with patch("app.hora.models.venda.HoraVenda") as HV, \
         patch("app.hora.services.venda_preview_service.montar_preview"):
        HV.query.get.return_value = None
        res = m._run_margem(venda_id=999, loja_ids=None, pode_ver_todas=True)
    assert res.get("erro") == "venda_nao_encontrada"
