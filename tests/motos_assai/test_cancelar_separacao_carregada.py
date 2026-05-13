"""Testes: cancelar_separacao deve aceitar sep em status CARREGADA.

Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md (Task 14)
"""
import uuid

import pytest

from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaLoja,
    AssaiLoja, AssaiModelo, AssaiMoto,
    AssaiSeparacao, AssaiSeparacaoItem,
    PEDIDO_STATUS_ABERTO,
    SEPARACAO_STATUS_CARREGADA, SEPARACAO_STATUS_CANCELADA, SEPARACAO_STATUS_FATURADA,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
    EVENTO_SEPARADA, EVENTO_CARREGADA,
)
from app.motos_assai.services import (
    cancelar_separacao, emitir_evento, status_efetivo,
    SeparacaoValidationError,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def test_cancelar_separacao_carregada_aceita(app, admin_user):
    """Sep CARREGADA pode ser cancelada — chassis voltam DISPONIVEL."""
    with app.app_context():
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        loja = AssaiLoja.query.first()

        uid = _uid()
        pedido = AssaiPedidoVenda(numero=f'TST-CC-{uid}', status=PEDIDO_STATUS_ABERTO,
                                  criado_por_id=admin_user.id)
        db.session.add(pedido); db.session.flush()
        pvl = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
        db.session.add(pvl); db.session.flush()

        sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id,
                             status=SEPARACAO_STATUS_CARREGADA)
        db.session.add(sep); db.session.flush()

        chassi = f'TST_CC_{_uid()}'
        moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
        db.session.add(moto); db.session.flush()
        db.session.add(AssaiSeparacaoItem(
            separacao_id=sep.id, chassi=chassi, modelo_id=modelo.id,
            valor_unitario_qpa=1000.0,
        ))
        for ev in [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
                   EVENTO_SEPARADA, EVENTO_CARREGADA]:
            emitir_evento(chassi, ev, admin_user.id)
        db.session.commit()

        cancelar_separacao(sep.id, motivo='Teste cancel CARREGADA',
                           operador_id=admin_user.id)
        # cancelar_separacao ja faz commit interno

        sep_ref = AssaiSeparacao.query.get(sep.id)
        assert sep_ref.status == SEPARACAO_STATUS_CANCELADA
        # Chassi voltou DISPONIVEL (ultimo evento)
        assert status_efetivo(chassi) == EVENTO_DISPONIVEL
        db.session.rollback()


def test_cancelar_separacao_faturada_continua_bloqueada(app, admin_user):
    """FATURADA continua nao podendo ser cancelada (precisa cancelar NF antes)."""
    with app.app_context():
        loja = AssaiLoja.query.first()

        uid = _uid()
        pedido = AssaiPedidoVenda(numero=f'TST-CF-{uid}', status=PEDIDO_STATUS_ABERTO,
                                  criado_por_id=admin_user.id)
        db.session.add(pedido); db.session.flush()
        pvl = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
        db.session.add(pvl); db.session.flush()

        sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id,
                             status=SEPARACAO_STATUS_FATURADA)
        db.session.add(sep)
        db.session.commit()

        with pytest.raises(SeparacaoValidationError, match='FATURADA'):
            cancelar_separacao(sep.id, motivo='Tentativa', operador_id=admin_user.id)
        db.session.rollback()
