# -*- coding: utf-8 -*-
"""
Testes do fix IMP-2026-06-05-001 — quarentena + idempotência de lançamento.

Bug original: ComprovanteLancamentoService.lancar_no_odoo cria o account.payment
ANTES de reconciliar. Se uma etapa posterior (reconciliação título/extrato) lança
exceção, o except salvava erro_lancamento mas NÃO mudava o status — o lançamento
ficava preso em CONFIRMADO. Como lancar_batch reprocessa todos os CONFIRMADO, cada
nova rodada criava OUTRO payment órfão postado não reconciliado no Odoo (duplicação).

Fix (apenas em services, sem tocar models/routes):
1. Guarda de idempotência: se já existe odoo_payment_id de execução anterior e o
   payment está postado no Odoo, NÃO criar outro (vai para quarentena 'ERRO').
   Se o payment_id é resíduo de rollback (não existe no Odoo), limpa e prossegue.
2. Quarentena: se o payment foi criado nesta execução mas a reconciliação falhou,
   o status vai para STATUS_QUARENTENA ('ERRO') — que o batch NÃO reprocessa.

Estratégia de teste: igual a tests/carvia/test_admin_delete_fatura_fk.py — o fixture
`db` roda em begin_nested()+rollback() e o service faz db.session.commit(); por isso
o commit é substituído por flush() durante a chamada, mantendo tudo no savepoint.
"""
import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.financeiro.models_comprovante import (
    ComprovantePagamentoBoleto,
    LancamentoComprovante,
)
from app.financeiro.services.comprovante_lancamento_service import (
    ComprovanteLancamentoService,
)


def _criar_comp_e_lanc(db, status='CONFIRMADO', odoo_payment_id=None):
    """Cria um comprovante + lançamento mínimos para o fluxo de lançamento."""
    comp = ComprovantePagamentoBoleto(
        tipo='boleto',
        numero_agendamento=f'AG-{uuid.uuid4().hex[:12]}',
        data_pagamento=date(2026, 6, 6),
        valor_pago=100,
        odoo_journal_id=10,
        odoo_statement_line_id=None,  # sem extrato -> pula reconciliação de extrato
        odoo_move_id=None,
    )
    db.session.add(comp)
    db.session.flush()

    lanc = LancamentoComprovante(
        comprovante_id=comp.id,
        odoo_move_line_id=5001,
        odoo_partner_id=42,
        odoo_company_id=1,
        nf_numero='12345',
        parcela=1,
        match_score=100,
        status=status,
        odoo_payment_id=odoo_payment_id,
        # valor do título == valor pago -> sem juros (caminho payment outbound simples)
        odoo_valor_residual=100,
        odoo_valor_original=100,
    )
    db.session.add(lanc)
    db.session.flush()
    return comp, lanc


def _baixa_service_feliz():
    """MagicMock de BaixaPagamentosService com fluxo de sucesso (sem extrato)."""
    bs = MagicMock()
    # Título com saldo em aberto (não quitado) na empresa 1
    bs.buscar_titulo_por_id.return_value = {
        'reconciled': False,
        'amount_residual': -100.0,
        'company_id': [1, 'NACOM'],
        'full_reconcile_id': [42, 'REC/42'],
    }
    bs.criar_pagamento_outbound.return_value = (777, 'PAY/777')
    bs.postar_pagamento.return_value = None
    bs.buscar_linhas_payment.return_value = {'debit_line_id': 10, 'credit_line_id': 11}
    bs.reconciliar.return_value = None
    # connection.search_read p/ account.payment (idempotência): default -> não existe
    bs.connection.search_read.return_value = []
    return bs


@pytest.fixture(autouse=True)
def _sem_sync_extrato():
    """Neutraliza o ConciliacaoSyncService (chamada Odoo non-blocking) nos testes."""
    with patch(
        'app.financeiro.services.conciliacao_sync_service.ConciliacaoSyncService'
    ) as mock_sync:
        mock_sync.return_value.sync_comprovante_para_extrato.return_value = None
        yield mock_sync


def test_erro_apos_criar_payment_vai_para_quarentena(db):
    """Payment criado + falha na etapa seguinte -> status ERRO (batch não reprocessa)."""
    _comp, lanc = _criar_comp_e_lanc(db)
    lanc_id = lanc.id

    bs = _baixa_service_feliz()
    # Payment é criado, mas buscar_linhas_payment (pós-criação) explode
    bs.buscar_linhas_payment.side_effect = RuntimeError('falha simulada pós-criação')

    service = ComprovanteLancamentoService()
    service._baixa_service = bs

    with patch.object(db.session, 'commit', db.session.flush):
        resultado = service.lancar_no_odoo(lanc_id, 'tester')

    db.session.expire_all()
    lanc_db = db.session.get(LancamentoComprovante, lanc_id)

    assert resultado['sucesso'] is False
    assert lanc_db.status == ComprovanteLancamentoService.STATUS_QUARENTENA
    assert lanc_db.status != 'CONFIRMADO'  # não fica preso (cerne do bug)
    assert lanc_db.erro_lancamento  # erro registrado
    # Payment foi criado uma vez (não duplicou)
    assert bs.criar_pagamento_outbound.call_count == 1


def test_erro_antes_de_criar_payment_mantem_confirmado(db):
    """Falha ANTES de criar o payment -> mantém CONFIRMADO (seguro reprocessar)."""
    _comp, lanc = _criar_comp_e_lanc(db)
    lanc_id = lanc.id

    bs = _baixa_service_feliz()
    # Falha na própria criação do payment (nenhum payment chega a existir)
    bs.criar_pagamento_outbound.side_effect = RuntimeError('falha na criação')

    service = ComprovanteLancamentoService()
    service._baixa_service = bs

    with patch.object(db.session, 'commit', db.session.flush):
        resultado = service.lancar_no_odoo(lanc_id, 'tester')

    db.session.expire_all()
    lanc_db = db.session.get(LancamentoComprovante, lanc_id)

    assert resultado['sucesso'] is False
    assert lanc_db.status == 'CONFIRMADO'  # pode ser reprocessado com segurança
    assert lanc_db.odoo_payment_id is None


def test_idempotencia_payment_existente_nao_duplica(db):
    """odoo_payment_id já setado + payment postado no Odoo -> NÃO cria 2º payment."""
    _comp, lanc = _criar_comp_e_lanc(db, odoo_payment_id=55493)
    lanc_id = lanc.id

    bs = _baixa_service_feliz()
    # account.payment 55493 existe e está postado
    bs.connection.search_read.return_value = [{'id': 55493, 'state': 'posted'}]

    service = ComprovanteLancamentoService()
    service._baixa_service = bs

    with patch.object(db.session, 'commit', db.session.flush):
        resultado = service.lancar_no_odoo(lanc_id, 'tester')

    db.session.expire_all()
    lanc_db = db.session.get(LancamentoComprovante, lanc_id)

    assert resultado['sucesso'] is False
    assert resultado.get('quarentena') is True
    assert lanc_db.status == ComprovanteLancamentoService.STATUS_QUARENTENA
    # NUNCA chamou criar_pagamento_outbound (anti-duplicação)
    bs.criar_pagamento_outbound.assert_not_called()


def test_residuo_de_rollback_limpa_e_relanca(db):
    """odoo_payment_id resíduo (payment inexistente no Odoo) -> limpa e cria normal."""
    _comp, lanc = _criar_comp_e_lanc(db, odoo_payment_id=55493)
    lanc_id = lanc.id

    bs = _baixa_service_feliz()
    # account.payment 55493 NÃO existe (rollback) -> search_read retorna []
    bs.connection.search_read.return_value = []

    service = ComprovanteLancamentoService()
    service._baixa_service = bs

    with patch.object(db.session, 'commit', db.session.flush):
        resultado = service.lancar_no_odoo(lanc_id, 'tester')

    db.session.expire_all()
    lanc_db = db.session.get(LancamentoComprovante, lanc_id)

    assert resultado['sucesso'] is True
    assert lanc_db.status == 'LANCADO'
    assert lanc_db.odoo_payment_id == 777  # novo payment criado
    assert bs.criar_pagamento_outbound.call_count == 1


def test_fluxo_feliz_lancado(db):
    """Regressão: fluxo normal sem erros -> LANCADO."""
    _comp, lanc = _criar_comp_e_lanc(db)
    lanc_id = lanc.id

    bs = _baixa_service_feliz()
    service = ComprovanteLancamentoService()
    service._baixa_service = bs

    with patch.object(db.session, 'commit', db.session.flush):
        resultado = service.lancar_no_odoo(lanc_id, 'tester')

    db.session.expire_all()
    lanc_db = db.session.get(LancamentoComprovante, lanc_id)

    assert resultado['sucesso'] is True
    assert lanc_db.status == 'LANCADO'
    assert lanc_db.odoo_payment_id == 777
