"""D1/D2 — atribuir_membro nao pode taguear terceiros como familiares.

Bugs auditados:
- D1: `nome in historico` (substring cru) casa 'RAFAEL' dentro de 'RAFAELA FERREIRA'/
  'AMAZONMKTPLC*RAFAELCAM' e nomes de terceiros -> membro errado (24 tx em prod).
- D2: cartao OFX (Nubank) sem titular/digitos cai no substring do nome do LOJISTA;
  deve usar o dono da conta.

Fixes: (1) match por fronteira de palavra (\\b); (2) cartao usa conta.membro_id (dono),
nunca deduz membro pelo nome do estabelecimento/contraparte.

Usa nomes INVENTADOS unicos por teste (o DB de teste ja tem os membros reais; nome e UNIQUE).
"""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app import db as _db
from app.pessoal.models import PessoalMembro, PessoalConta, PessoalTransacao
from app.pessoal.services.categorizacao_service import atribuir_membro


def _mk_membro(pessoal_ctx, nome, nome_completo=None):
    m = PessoalMembro(nome=nome, nome_completo=nome_completo, ativo=True)
    _db.session.add(m)
    _db.session.commit()
    pessoal_ctx['membros'].append(m.id)
    return m


@pytest.mark.integration
def test_word_boundary_nao_atribui_substring_de_nome(pessoal_ctx, make_transacao):
    tok = f'Xaral{uuid4().hex[:6]}'  # nome do membro
    m = _mk_membro(pessoal_ctx, tok, f'{tok} ZBORCK')
    # tok aparece como PREFIXO de uma palavra maior (tok+'S') -> substring, nao palavra inteira
    t = make_transacao(
        historico=f'COMPRA CARTAO | {tok}S FERREIRA MODAS', tipo='debito',
        hash_transacao=f'wb{uuid4().hex[:8]}',
    )
    membro_id, _ = atribuir_membro(t)
    assert membro_id != m.id


@pytest.mark.integration
def test_word_boundary_casa_nome_inteiro(pessoal_ctx, make_transacao):
    tok = f'Xaral{uuid4().hex[:6]}'
    m = _mk_membro(pessoal_ctx, tok, f'{tok} ZBORCK')
    t = make_transacao(
        historico=f'TRANSFERENCIA RECEBIDA PELO PIX - {tok} ZBORCK', tipo='credito',
        hash_transacao=f'wb{uuid4().hex[:8]}',
    )
    membro_id, _ = atribuir_membro(t)
    assert membro_id == m.id


@pytest.mark.integration
def test_cartao_usa_dono_da_conta_nao_lojista(pessoal_ctx, membro, importacao):
    """Cartao (sem titular/digitos): atribui o DONO da conta, nao o nome do lojista."""
    dono = membro  # dono do cartao (Teste_xxx, unico)
    tok = f'Yoralb{uuid4().hex[:6]}'
    homonimo = _mk_membro(pessoal_ctx, tok, f'{tok} GUSTAVO')  # nome aparece no lojista

    cartao = PessoalConta(
        nome=f'Nubank Cartao {uuid4().hex[:6]}', tipo='cartao_credito',
        banco='nubank', membro_id=dono.id, ativa=True,
    )
    _db.session.add(cartao)
    _db.session.commit()
    pessoal_ctx['contas'].append(cartao.id)

    t = PessoalTransacao(
        importacao_id=importacao.id, conta_id=cartao.id, data=date(2026, 4, 1),
        historico=f'{tok} GUSTAVO FERREIRA', historico_completo=f'{tok} GUSTAVO FERREIRA',
        valor=Decimal('50.00'), tipo='debito', status='PENDENTE',
        hash_transacao=f'cartao_membro_{uuid4().hex[:8]}',
    )
    _db.session.add(t)
    _db.session.commit()
    pessoal_ctx['transacoes'].append(t.id)

    membro_id, auto = atribuir_membro(t)
    assert membro_id == dono.id  # dono do cartao, nao o homonimo do lojista
    assert membro_id != homonimo.id
    assert auto is True
