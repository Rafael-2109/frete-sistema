"""A1 — Dashboard (competencia) deve somar valor_efetivo (valor - valor_compensado).

Bug auditado: dashboard_service somava PessoalTransacao.valor NOMINAL filtrando so
excluir_relatorio=False, ignorando valor_compensado — divergindo do fluxo_caixa_service
(que usa _EXPR_VALOR_EFETIVO) e inflando receita/despesa (~R$1,4M em producao).

Isola cada assercao num mes futuro vazio (2099) para somar exatamente as tx do teste.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.pessoal.services import dashboard_service


@pytest.mark.integration
def test_resumo_mensal_desconta_valor_compensado(pessoal_ctx, make_transacao):
    # credito 1000 com 600 compensado -> receita efetiva = 400
    make_transacao(
        tipo='credito', valor=Decimal('1000.00'),
        valor_compensado=Decimal('600.00'),
        excluir_relatorio=False, data=date(2099, 1, 15),
    )
    resumo = dashboard_service.calcular_resumo_mensal(2099, 1)
    assert resumo['total_receitas'] == 400.0


@pytest.mark.integration
def test_gastos_por_categoria_desconta_valor_compensado(
    pessoal_ctx, make_transacao, categoria_alimentacao,
):
    # debito 1000 com 700 compensado -> gasto efetivo da categoria = 300
    make_transacao(
        tipo='debito', valor=Decimal('1000.00'),
        valor_compensado=Decimal('700.00'), categoria_id=categoria_alimentacao.id,
        excluir_relatorio=False, data=date(2099, 2, 10),
    )
    linhas = dashboard_service.gastos_por_categoria(2099, 2)
    alvo = next((l for l in linhas if l['categoria_id'] == categoria_alimentacao.id), None)
    assert alvo is not None, 'categoria deveria aparecer com gasto'
    assert alvo['gasto'] == 300.0


@pytest.mark.integration
def test_tendencia_mensal_desconta_valor_compensado(pessoal_ctx, make_transacao):
    make_transacao(
        tipo='debito', valor=Decimal('1000.00'),
        valor_compensado=Decimal('600.00'),
        excluir_relatorio=False, data=date(2099, 3, 12),
    )
    serie = dashboard_service.tendencia_mensal(2099, 3, meses=2)
    alvo = next((m for m in serie if m['mes'] == '2099-03'), None)
    assert alvo is not None
    assert alvo['despesas'] == 400.0


@pytest.mark.integration
def test_comparativo_anual_desconta_valor_compensado(pessoal_ctx, make_transacao):
    # ano_ref=2099, mes 6 (indice 5)
    make_transacao(
        tipo='credito', valor=Decimal('1000.00'),
        valor_compensado=Decimal('600.00'),
        excluir_relatorio=False, data=date(2099, 6, 20),
    )
    comp = dashboard_service.comparativo_anual(2099)
    assert comp['receitas_atual'][5] == 400.0


@pytest.mark.integration
def test_evolucao_por_categoria_desconta_valor_compensado(
    pessoal_ctx, make_transacao, categoria_alimentacao,
):
    make_transacao(
        tipo='debito', valor=Decimal('1000.00'),
        valor_compensado=Decimal('600.00'), categoria_id=categoria_alimentacao.id,
        excluir_relatorio=False, data=date(2099, 4, 8),
    )
    evol = dashboard_service.evolucao_por_categoria(
        2099, 4, meses=2, categoria_ids=[categoria_alimentacao.id],
    )
    serie = next(
        (s for s in evol['series'] if s['categoria_id'] == categoria_alimentacao.id), None,
    )
    assert serie is not None
    # valores alinhado a evol['meses']; o mes 2099-04 e o ultimo da janela
    idx = next(i for i, m in enumerate(evol['meses']) if m['mes'] == '2099-04')
    assert serie['valores'][idx] == 400.0
