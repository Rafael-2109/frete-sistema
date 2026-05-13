"""Testes substituir_chassi_entre_seps (S20=a + CR-2/CR-10/CR-11).

Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase5-auxiliares.md Task 1
"""
import uuid

import pytest

from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaLoja,
    AssaiLoja, AssaiModelo, AssaiMoto,
    AssaiSeparacao, AssaiSeparacaoItem,
    AssaiNfQpa, AssaiDivergencia,
    PEDIDO_STATUS_ABERTO,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_CARREGADA, SEPARACAO_STATUS_FATURADA,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
    EVENTO_SEPARADA, EVENTO_CARREGADA, EVENTO_FATURADA,
    NF_STATUS_BATEU,
    DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
)
from app.motos_assai.services import (
    substituir_chassi_entre_seps, emitir_evento, status_efetivo,
    SeparacaoValidationError, SeparacaoCrossLojaError, registrar_chassi,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def test_substituir_chassi_origem_em_separacao_destino_em_separacao(app, admin_user):
    """S20=a: chassi move de sep_origem (EM_SEPARACAO) para sep_destino (EM_SEPARACAO).

    Eventos: SEPARADA -> DISPONIVEL -> SEPARADA (3 eventos novos).
    """
    with app.app_context():
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        lojas = AssaiLoja.query.limit(2).all()
        assert len(lojas) >= 2, 'Precisa de pelo menos 2 lojas para testar cross-loja'
        loja_a, loja_b = lojas[0], lojas[1]

        uid = _uid()
        pedido = AssaiPedidoVenda(numero=f'TST-S1-{uid}', status=PEDIDO_STATUS_ABERTO,
                                  criado_por_id=admin_user.id)
        db.session.add(pedido); db.session.flush()
        for loja in (loja_a, loja_b):
            db.session.add(AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id))
        db.session.flush()

        # Chassi separado em sep_a (loja A)
        chassi = f'TST_S1_{_uid()}'
        moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
        db.session.add(moto); db.session.flush()
        for ev in [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL, EVENTO_SEPARADA]:
            emitir_evento(chassi, ev, admin_user.id)

        sep_a = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja_a.id,
                               status=SEPARACAO_STATUS_EM_SEPARACAO)
        db.session.add(sep_a); db.session.flush()
        db.session.add(AssaiSeparacaoItem(
            separacao_id=sep_a.id, chassi=chassi, modelo_id=modelo.id,
            valor_unitario_qpa=1000.0,
        ))

        sep_b = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja_b.id,
                               status=SEPARACAO_STATUS_EM_SEPARACAO)
        db.session.add(sep_b)
        db.session.commit()

        # Substituir
        result = substituir_chassi_entre_seps(
            chassi=chassi,
            sep_origem_id=sep_a.id,
            sep_destino_id=sep_b.id,
            operador_id=admin_user.id,
        )
        db.session.commit()

        assert result['chassi'] == chassi
        assert result['divergencia_id'] is None  # sep_a EM_SEPARACAO, sem NF

        # Item migrado para sep_b
        assert AssaiSeparacaoItem.query.filter_by(
            separacao_id=sep_a.id, chassi=chassi,
        ).first() is None
        assert AssaiSeparacaoItem.query.filter_by(
            separacao_id=sep_b.id, chassi=chassi,
        ).first() is not None

        # S20=a: ultimo evento e SEPARADA, anterior DISPONIVEL
        assert status_efetivo(chassi) == EVENTO_SEPARADA
        db.session.rollback()


def test_substituir_chassi_destino_faturada_bloqueada(app, admin_user):
    """CR-11: sep_destino FATURADA deve ser bloqueada (cancele NF antes)."""
    with app.app_context():
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        lojas = AssaiLoja.query.limit(2).all()
        loja_a, loja_b = lojas[0], lojas[1]

        uid = _uid()
        pedido = AssaiPedidoVenda(numero=f'TST-S2-{uid}', status=PEDIDO_STATUS_ABERTO,
                                  criado_por_id=admin_user.id)
        db.session.add(pedido); db.session.flush()
        db.session.add(AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja_a.id))
        db.session.add(AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja_b.id))
        db.session.flush()

        chassi = f'TST_S2_{_uid()}'
        moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
        db.session.add(moto); db.session.flush()
        for ev in [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL, EVENTO_SEPARADA]:
            emitir_evento(chassi, ev, admin_user.id)

        sep_a = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja_a.id,
                               status=SEPARACAO_STATUS_EM_SEPARACAO)
        db.session.add(sep_a); db.session.flush()
        db.session.add(AssaiSeparacaoItem(
            separacao_id=sep_a.id, chassi=chassi, modelo_id=modelo.id,
            valor_unitario_qpa=1000.0,
        ))

        sep_b = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja_b.id,
                               status=SEPARACAO_STATUS_FATURADA)
        db.session.add(sep_b)
        db.session.commit()

        with pytest.raises(SeparacaoValidationError, match='FATURADA'):
            substituir_chassi_entre_seps(
                chassi=chassi,
                sep_origem_id=sep_a.id,
                sep_destino_id=sep_b.id,
                operador_id=admin_user.id,
            )
        db.session.rollback()


def test_registrar_chassi_em_outra_loja_levanta_cross_loja(app, admin_user):
    """Task 2: registrar_chassi detecta CHASSI_OUTRA_LOJA e levanta exception."""
    with app.app_context():
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        lojas = AssaiLoja.query.limit(2).all()
        loja_a, loja_b = lojas[0], lojas[1]

        uid = _uid()
        pedido = AssaiPedidoVenda(numero=f'TST-S3-{uid}', status=PEDIDO_STATUS_ABERTO,
                                  criado_por_id=admin_user.id)
        db.session.add(pedido); db.session.flush()
        for loja in (loja_a, loja_b):
            db.session.add(AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id))
        db.session.flush()

        # Chassi em sep_a (loja A) status SEPARADA
        chassi = f'TST_S3_{_uid()}'
        moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
        db.session.add(moto); db.session.flush()
        for ev in [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL, EVENTO_SEPARADA]:
            emitir_evento(chassi, ev, admin_user.id)

        sep_a = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja_a.id,
                               status=SEPARACAO_STATUS_EM_SEPARACAO)
        db.session.add(sep_a); db.session.flush()
        db.session.add(AssaiSeparacaoItem(
            separacao_id=sep_a.id, chassi=chassi, modelo_id=modelo.id,
            valor_unitario_qpa=1000.0,
        ))

        sep_b = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja_b.id,
                               status=SEPARACAO_STATUS_EM_SEPARACAO)
        db.session.add(sep_b)
        db.session.commit()

        # Tentar registrar em sep_b (loja B) — deve levantar SeparacaoCrossLojaError
        with pytest.raises(SeparacaoCrossLojaError) as exc_info:
            registrar_chassi(
                pedido_id=pedido.id, loja_id=loja_b.id,
                chassi=chassi,
                registrada_por_id=admin_user.id,
                separacao_id=sep_b.id,
            )

        exc = exc_info.value
        assert exc.sep_origem_id == sep_a.id
        assert exc.loja_origem_id == loja_a.id
        assert exc.loja_destino_id == loja_b.id
        assert exc.chassi == chassi
        db.session.rollback()
