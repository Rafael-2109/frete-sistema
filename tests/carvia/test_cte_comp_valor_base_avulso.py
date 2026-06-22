"""Teste do fix: valor_base liquido para emissao SSW de CTe complementar.

Causa-raiz (REVISAO 2026-06-22): o worker ssw_cte_complementar_jobs lia o valor
liquido de `emissao.custo_entrega.valor`, que e None no CTe complementar AVULSO
(TDE/Diaria sem CustoEntrega de contrapartida) -> AttributeError -> a emissao
nunca chegava ao SSW. O service ja permitia criar o avulso (custo_entrega_id
opcional), mas a emissao quebrava.

Fix: o liquido passou a ser persistido em `emissao.valor_base` (com OU sem CE) e
o helper `_resolver_valor_base_ssw` resolve a fonte com fallback ao CE legado,
devolvendo None (caller marca ERRO) em vez de crashar quando nao ha fonte.

Importante: valor_base e o LIQUIDO; quem aplica PIS/COFINS + ICMS (grossing-up)
e o SSW 222 ao vivo. Por isso o worker NUNCA deve usar valor_calculado (que ja
tem imposto) como base — cobraria imposto sobre imposto. Teste puro, sem DB.
"""
from decimal import Decimal
from types import SimpleNamespace

from app.carvia.workers.ssw_cte_complementar_jobs import _resolver_valor_base_ssw


def test_avulso_usa_valor_base_sem_ce():
    # CTe complementar AVULSO: sem CustoEntrega, valor_base = valor a cobrar.
    emissao = SimpleNamespace(valor_base=Decimal('300.00'), custo_entrega=None)
    assert _resolver_valor_base_ssw(emissao) == 300.00


def test_com_ce_prioriza_valor_base_persistido():
    # valor_base e a fonte canonica mesmo havendo CE (no fluxo com CE sao iguais).
    emissao = SimpleNamespace(
        valor_base=Decimal('250.00'),
        custo_entrega=SimpleNamespace(valor=Decimal('250.00')),
    )
    assert _resolver_valor_base_ssw(emissao) == 250.00


def test_legado_sem_valor_base_cai_no_ce():
    # Emissao anterior a coluna valor_base (NULL): fallback ao custo_entrega.valor.
    emissao = SimpleNamespace(
        valor_base=None,
        custo_entrega=SimpleNamespace(valor=Decimal('180.50')),
    )
    assert _resolver_valor_base_ssw(emissao) == 180.50


def test_avulso_legado_sem_fonte_retorna_none():
    # Avulso legado (sem valor_base e sem CE): caller marca ERRO, nao crasha.
    emissao = SimpleNamespace(valor_base=None, custo_entrega=None)
    assert _resolver_valor_base_ssw(emissao) is None
