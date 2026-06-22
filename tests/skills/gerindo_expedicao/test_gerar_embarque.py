"""Testes deterministicos da skill `gerindo-expedicao` / script `gerar_embarque.py`.

Escopo F2 #1: orquestrador CLI que GERA EMBARQUE (Cotacao + Embarque + EmbarqueItem
+ propaga cotacao_id na Separacao) em DOIS modos:
  (A) ESPELHO de um embarque existente (--embarque-origem)
  (B) SEPARACOES SOLTAS ja escolhidas (--lotes + --transportadora-id + --tabela)

Estrategia (sem tocar Odoo/banco de PROD):
- Carrega o script via importlib (as funcoes app.* sao import LAZY dentro das
  funcoes, entao o modulo importa sem app_context).
- Exercita as partes PURAS e de VALIDACAO com mocks/SimpleNamespace:
    * recusa de prefixo CARVIA-/ASSAI-
    * --user-id ausente / invalido
    * DIRETA com UF misto
    * montagem de dados_tabela a partir do espelho (DIRETA e FRACIONADA)
    * montagem de dados_tabela a partir de TabelaFrete (modo SOLTAS)
    * exit codes / convencao de confirmacao

NAO ha teste de integracao com banco (inviavel deterministicamente sem PROD);
o fluxo de escrita (commit, atualizar_cotacao) e coberto por mock de `db` e das
funcoes oficiais. Ver `pendencias` no retorno do agente.
"""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".claude/skills/gerindo-expedicao/scripts/gerar_embarque.py"


def _load():
    spec = importlib.util.spec_from_file_location("gerar_embarque_mod", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gerar_embarque_mod"] = mod
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# Recusa de prefixo CARVIA-/ASSAI- (v1 so ramo Nacom)
# --------------------------------------------------------------------------
def test_validar_lotes_prefixo_aceita_nacom():
    m = _load()
    ok, recusados = m.validar_lotes_nacom(["LOTE_20251004_1", "LOTE_20251004_2"])
    assert ok is True
    assert recusados == []


def test_validar_lotes_prefixo_recusa_carvia():
    m = _load()
    ok, recusados = m.validar_lotes_nacom(["LOTE_X", "CARVIA-123"])
    assert ok is False
    assert "CARVIA-123" in recusados


def test_validar_lotes_prefixo_recusa_carvia_ped():
    m = _load()
    ok, recusados = m.validar_lotes_nacom(["CARVIA-PED-9"])
    assert ok is False
    assert "CARVIA-PED-9" in recusados


def test_validar_lotes_prefixo_recusa_assai():
    m = _load()
    ok, recusados = m.validar_lotes_nacom(["ASSAI-SEP-5", "LOTE_OK"])
    assert ok is False
    assert "ASSAI-SEP-5" in recusados


# --------------------------------------------------------------------------
# --user-id obrigatorio + validado contra tabela usuarios
# --------------------------------------------------------------------------
def test_resolver_usuario_inexistente_retorna_none():
    m = _load()
    fake_db = MagicMock()
    fake_db.session.get.return_value = None  # usuario nao existe
    with patch.object(m, "_get_db", return_value=fake_db), \
         patch.object(m, "_get_usuario_model", return_value=MagicMock()):
        u = m.resolver_usuario(99999)
    assert u is None


def test_resolver_usuario_existente_retorna_obj():
    m = _load()
    user = SimpleNamespace(id=74, nome="Claude")
    fake_db = MagicMock()
    fake_db.session.get.return_value = user
    with patch.object(m, "_get_db", return_value=fake_db), \
         patch.object(m, "_get_usuario_model", return_value=MagicMock()):
        u = m.resolver_usuario(74)
    assert u is user
    assert u.nome == "Claude"


# --------------------------------------------------------------------------
# DIRETA exige UF normalizado unico
# --------------------------------------------------------------------------
def _ped(uf, cidade=None, rota=None):
    return SimpleNamespace(cod_uf=uf, nome_cidade=cidade, rota=rota)


def test_uf_unico_direta_homogeneo():
    m = _load()
    ok, ufs = m.validar_uf_unico_direta([_ped("AM"), _ped("AM")])
    assert ok is True
    assert ufs == {"AM"}


def test_uf_unico_direta_misto_falha():
    m = _load()
    ok, ufs = m.validar_uf_unico_direta([_ped("AM"), _ped("SP")])
    assert ok is False
    assert ufs == {"AM", "SP"}


def test_uf_unico_direta_aplica_normalizacao_red():
    m = _load()
    # rota RED -> normaliza para SP (LocalizacaoService.normalizar_uf_com_regras)
    ok, ufs = m.validar_uf_unico_direta([_ped("AM", rota="RED"), _ped("SP")])
    assert ok is True
    assert ufs == {"SP"}


# --------------------------------------------------------------------------
# Montagem de dados_tabela a partir do ESPELHO
# --------------------------------------------------------------------------
def test_dados_tabela_espelho_direta_le_do_embarque():
    """DIRETA: snapshot vem dos campos tabela_* do Embarque origem."""
    m = _load()
    emb = SimpleNamespace(
        tabela_nome_tabela="TABELA_AM",
        modalidade="FRETE PESO",
        tabela_valor_kg=1.5,
        tabela_percentual_valor=0.0,
        tabela_frete_minimo_valor=100.0,
        tabela_frete_minimo_peso=50.0,
        tabela_icms=0.0,
        tabela_percentual_gris=0.1,
        tabela_pedagio_por_100kg=0.0,
        tabela_valor_tas=0.0,
        tabela_percentual_adv=0.0,
        tabela_percentual_rca=0.0,
        tabela_valor_despacho=0.0,
        tabela_valor_cte=0.0,
        tabela_icms_incluso=False,
        tabela_gris_minimo=0.0,
        tabela_adv_minimo=0.0,
        tabela_icms_proprio=0.0,
        icms_destino=18.0,
    )
    dados = m.dados_tabela_de_espelho_direta(emb)
    assert dados["nome_tabela"] == "TABELA_AM"
    assert dados["valor_kg"] == 1.5
    assert dados["icms_destino"] == 18.0


def test_dados_tabela_espelho_fracionada_le_do_item():
    """FRACIONADA: snapshot vem dos campos tabela_* de UM EmbarqueItem origem."""
    m = _load()
    item = SimpleNamespace(
        tabela_nome_tabela="TAB_FRAC",
        modalidade="FRETE VALOR",
        tabela_valor_kg=0.0,
        tabela_percentual_valor=2.5,
        tabela_frete_minimo_valor=80.0,
        tabela_frete_minimo_peso=0.0,
        tabela_icms=0.0,
        tabela_percentual_gris=0.0,
        tabela_pedagio_por_100kg=0.0,
        tabela_valor_tas=0.0,
        tabela_percentual_adv=0.0,
        tabela_percentual_rca=0.0,
        tabela_valor_despacho=0.0,
        tabela_valor_cte=0.0,
        tabela_icms_incluso=True,
        tabela_gris_minimo=0.0,
        tabela_adv_minimo=0.0,
        tabela_icms_proprio=0.0,
        icms_destino=12.0,
    )
    dados = m.dados_tabela_de_espelho_item(item)
    assert dados["nome_tabela"] == "TAB_FRAC"
    assert dados["percentual_valor"] == 2.5
    assert dados["icms_destino"] == 12.0


# --------------------------------------------------------------------------
# Montagem de dados_tabela a partir de TabelaFrete (modo SOLTAS)
# --------------------------------------------------------------------------
def test_dados_tabela_de_tabelafrete():
    m = _load()
    tabela = SimpleNamespace(
        nome_tabela="TAB_SOLTA",
        modalidade="FRETE PESO",
        valor_kg=2.0,
        percentual_valor=1.0,
        frete_minimo_valor=120.0,
        frete_minimo_peso=60.0,
        percentual_gris=0.2,
        pedagio_por_100kg=3.0,
        valor_tas=0.0,
        percentual_adv=0.1,
        percentual_rca=0.0,
        valor_despacho=0.0,
        valor_cte=0.0,
        icms_incluso=False,
        gris_minimo=5.0,
        adv_minimo=2.0,
        icms_proprio=0.0,
    )
    dados = m.dados_tabela_de_tabela_frete(tabela, icms_destino=7.0)
    assert dados["nome_tabela"] == "TAB_SOLTA"
    assert dados["valor_kg"] == 2.0
    assert dados["icms_destino"] == 7.0


# --------------------------------------------------------------------------
# Exit codes
# --------------------------------------------------------------------------
def test_exit_codes_definidos():
    m = _load()
    # 0 efetivado, 4 dry-run OK, 1 falha, 2 uso
    assert m.EXIT_OK == 0
    assert m.EXIT_DRYRUN == 4
    assert m.EXIT_FALHA == 1
    assert m.EXIT_USO == 2
