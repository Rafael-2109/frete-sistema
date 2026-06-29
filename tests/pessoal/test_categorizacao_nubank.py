"""Tests das heuristicas de categorizacao especificas do Nubank.

Cobre:
- Transferencia entre contas proprias (memo cita numero de conta propria)
- Pagamento de fatura (debito) -> eh_pagamento_cartao
- "Pagamento recebido" (credito no cartao) -> excluir_relatorio (nao e receita)
"""
from decimal import Decimal
from uuid import uuid4

import pytest

from app import db as _db
from app.pessoal.models import PessoalConta
from app.pessoal.services.categorizacao_service import categorizar_transacao


@pytest.fixture
def conta_bradesco(pessoal_ctx, membro):
    """Conta corrente Bradesco propria com numero_conta (origem dos depositos)."""
    c = PessoalConta(
        nome=f'Bradesco CC {uuid4().hex[:6]}',
        tipo='conta_corrente',
        banco='bradesco',
        numero_conta='128948-9',
        membro_id=membro.id,
        ativa=True,
    )
    _db.session.add(c)
    _db.session.commit()
    pessoal_ctx['contas'].append(c.id)
    return c


def test_deposito_de_conta_propria_vira_transferencia(make_transacao, conta_bradesco):
    """Credito na NuConta citando a conta Bradesco propria = transferencia entre contas."""
    t = make_transacao(
        tipo='credito',
        valor=Decimal('3000.00'),
        hash_transacao='nb_dep_propria',
        historico=(
            'Transferência recebida pelo Pix - RENATA GALAFASSI DE QUEIROZ - '
            '•••.529.541-•• - BCO BRADESCO S.A. (0237) Agência: 111 Conta: 128948-9'
        ),
    )
    r = categorizar_transacao(t)
    assert r.eh_transferencia_propria is True
    assert r.excluir_relatorio is True
    assert r.status == 'CATEGORIZADO'


def test_pix_para_terceiro_nao_vira_transferencia(make_transacao, conta_bradesco):
    """Conta de terceiro no memo (Mercado Pago) NAO e transferencia propria."""
    t = make_transacao(
        tipo='debito',
        valor=Decimal('22.00'),
        hash_transacao='nb_pix_terceiro',
        historico=(
            'Transferência enviada pelo Pix - Uyara Queiroz Costa - '
            'MERCADO PAGO IP LTDA. (0323) Agência: 1 Conta: 1847312458-4'
        ),
    )
    r = categorizar_transacao(t)
    assert r.eh_transferencia_propria is False


def test_pagamento_de_fatura_debito_vira_pagamento_cartao(make_transacao, conta_bradesco):
    t = make_transacao(tipo='debito', valor=Decimal('7531.07'), historico='Pagamento de fatura')
    r = categorizar_transacao(t)
    assert r.eh_pagamento_cartao is True
    assert r.excluir_relatorio is True


def test_pagamento_recebido_credito_e_excluido(make_transacao, conta_bradesco):
    """'Pagamento recebido' (credito no cartao) nao e receita -> excluir_relatorio."""
    t = make_transacao(tipo='credito', valor=Decimal('5000.00'), historico='Pagamento recebido')
    r = categorizar_transacao(t)
    assert r.excluir_relatorio is True
    assert r.eh_pagamento_cartao is False  # nao e a saida na CC
    assert r.eh_transferencia_propria is False
