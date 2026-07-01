"""B2 — recategorizacao/descategorizacao nao pode des-excluir a perna PRINCIPAL do
Pix-no-Credito (compra-principal do split ou funding de liquidez).

Bug auditado: os paths que gravam excluir_relatorio (transacoes.categorizar/
categorizar_lote/descategorizar e categorizacao_service.categorizar_lote) nao respeitavam
eh_pix_credito; recategorizar a compra-leg para uma categoria normal punha excluir=False
e o principal (ja contado no Pix-saida) passava a contar 2x (R$2.660 em 6 grupos em prod).

Guard puro (le atributos, sem DB): funding e compra-principal do split ficam protegidos;
juros e pix-saida NAO (sao despesa visivel).
"""
from decimal import Decimal

import pytest

from app.pessoal.services.pix_credito_service import (
    deve_permanecer_excluida_pix_credito,
)


class _Tx:
    def __init__(self, eh_pix_credito=False, observacao=None,
                 historico='', historico_completo=None):
        self.eh_pix_credito = eh_pix_credito
        self.observacao = observacao
        self.historico = historico
        self.historico_completo = historico_completo


def test_guard_protege_compra_principal_do_split():
    tx = _Tx(
        eh_pix_credito=True,
        observacao=(' [Pix no Credito: original R$100.00, principal R$100.00, '
                    'juros R$0.00; principal lancado no Pix NuConta id=5]'),
        historico='ANDREA XAVIER',
    )
    assert deve_permanecer_excluida_pix_credito(tx) is True


def test_guard_protege_funding():
    tx = _Tx(
        eh_pix_credito=True,
        historico_completo='VALOR ADICIONADO NA CONTA POR CARTAO DE CREDITO - PIX NO CREDITO',
    )
    assert deve_permanecer_excluida_pix_credito(tx) is True


def test_guard_nao_protege_juros():
    tx = _Tx(
        eh_pix_credito=True,
        observacao='Juros do Pix no Credito (split da compra cartao id=42)',
        historico='JUROS PIX NO CREDITO - ANDREA',
        historico_completo='JUROS PIX NO CREDITO - ANDREA',
    )
    assert deve_permanecer_excluida_pix_credito(tx) is False


def test_guard_nao_protege_pix_saida():
    tx = _Tx(
        eh_pix_credito=True,
        historico_completo='TRANSFERENCIA ENVIADA PELO PIX - ANDREA XAVIER',
    )
    assert deve_permanecer_excluida_pix_credito(tx) is False


def test_guard_ignora_transacao_normal():
    tx = _Tx(eh_pix_credito=False, historico_completo='IFOOD DELIVERY')
    assert deve_permanecer_excluida_pix_credito(tx) is False


@pytest.mark.integration
def test_categorizar_lote_service_nao_des_exclui_compra_principal(pessoal_ctx, make_transacao):
    """Wiring: o pipeline/categorizar_lote NAO pode des-excluir a compra-principal do split."""
    from app.pessoal.services.categorizacao_service import categorizar_lote

    tx = make_transacao(
        tipo='debito', valor=Decimal('100.00'),
        eh_pix_credito=True, excluir_relatorio=True, status='CATEGORIZADO',
        historico='ANDREA XAVIER',
        observacao=(' [Pix no Credito: original R$100.00, principal R$100.00, '
                    'juros R$0.00; principal lancado no Pix NuConta id=5]'),
    )
    categorizar_lote([tx])
    assert tx.excluir_relatorio is True
