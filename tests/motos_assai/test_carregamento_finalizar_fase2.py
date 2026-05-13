"""Testes finalizar_carregamento Fase 2 (sobrescrever sep alvo + S2 realocacao + R1.1).

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md §6 Fase 2
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md Task 6
"""
import uuid
import pytest
from decimal import Decimal

from app import db
from app.motos_assai.models import (
    AssaiLoja, AssaiModelo, AssaiPedidoVenda, AssaiPedidoVendaLoja,
    AssaiPedidoVendaItem, AssaiSeparacao, AssaiSeparacaoItem,
    AssaiSeparacaoSaldoModelo, AssaiMoto,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    PEDIDO_STATUS_ABERTO,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
    EVENTO_SEPARADA, EVENTO_CARREGADA,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, escanear_carregamento_item, finalizar_carregamento,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _setup_pedido(admin):
    """Pedido novo + 1 loja + saldo 30 motos do modelo DOT (qtd alta evita Fase 3)."""
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    loja = AssaiLoja.query.first()

    uid = _uid()
    pedido = AssaiPedidoVenda(
        numero=f'TST-CAR-F2-{uid}', status=PEDIDO_STATUS_ABERTO,
        criado_por_id=admin.id,
    )
    db.session.add(pedido)
    db.session.flush()
    pvl = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
    db.session.add(pvl)
    db.session.flush()
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=pedido.id, pedido_loja_id=pvl.id, loja_id=loja.id,
        modelo_id=modelo.id,
        qtd_pedida=30, valor_unitario=Decimal('1000.00'), valor_total=Decimal('30000.00'),
    ))
    db.session.flush()
    return pedido, loja, modelo


def _criar_chassi(modelo, chassi, admin):
    moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
    db.session.add(moto)
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin.id)
    emitir_evento(chassi, EVENTO_MONTADA, admin.id)
    emitir_evento(chassi, EVENTO_DISPONIVEL, admin.id)
    return moto


def test_fase2_chassis_adicionados_emitem_separada(app, admin_user):
    """Chassis no Carregamento mas nao na sep alvo recebem evento SEPARADA + CARREGADA (Fase 4)."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido(admin_user)
        chassi_new = f'TST_F2N_{_uid()}'
        _criar_chassi(modelo, chassi_new, admin_user)
        db.session.commit()

        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi_new, operador_id=admin_user.id)
        db.session.commit()

        sep_alvo = finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        # Item criado na sep
        item = AssaiSeparacaoItem.query.filter_by(
            separacao_id=sep_alvo.id, chassi=chassi_new,
        ).first()
        assert item is not None

        # Apos Fase 2: status efetivo = SEPARADA (Fase 4 emitira CARREGADA depois)
        # Aqui Fase 4 ainda nao foi implementada, entao chassi fica em SEPARADA.
        assert status_efetivo(chassi_new) == EVENTO_SEPARADA
        db.session.rollback()


def test_fase2_chassis_removidos_voltam_disponivel(app, admin_user):
    """Chassis na sep mas nao no Carregamento - vao DISPONIVEL (R1.1) ou realocam (S2)."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido(admin_user)
        chassi_old1 = f'TST_F2O1_{_uid()}'
        chassi_old2 = f'TST_F2O2_{_uid()}'
        chassi_new = f'TST_F2N_{_uid()}'
        for c in [chassi_old1, chassi_old2, chassi_new]:
            _criar_chassi(modelo, c, admin_user)

        sep_existente = AssaiSeparacao(
            pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA,
        )
        db.session.add(sep_existente)
        db.session.flush()
        for c in [chassi_old1, chassi_old2]:
            db.session.add(AssaiSeparacaoItem(
                separacao_id=sep_existente.id, chassi=c, modelo_id=modelo.id,
                valor_unitario_qpa=Decimal('1000.00'),
            ))
            emitir_evento(c, EVENTO_SEPARADA, operador_id=admin_user.id)
        db.session.commit()

        # Carregamento substitui OLD1/OLD2 por NEW
        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi_new, operador_id=admin_user.id)
        db.session.commit()

        sep_alvo = finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        # OLD1 e OLD2 expulsos (nao ha outra sep ativa para realocar)
        assert status_efetivo(chassi_old1) == EVENTO_DISPONIVEL  # R1.1 fallback
        assert status_efetivo(chassi_old2) == EVENTO_DISPONIVEL
        # NEW vai para SEPARADA (Fase 4 emite CARREGADA depois)
        assert status_efetivo(chassi_new) == EVENTO_SEPARADA

        # Sep alvo agora so tem NEW
        items = AssaiSeparacaoItem.query.filter_by(separacao_id=sep_alvo.id).all()
        chassis_sep = {it.chassi for it in items}
        assert chassis_sep == {chassi_new}
        db.session.rollback()


def test_fase2_chassis_expulsos_realocam_em_outra_sep_com_saldo(app, admin_user):
    """S2=b: chassis expulsos da sep alvo realocam em outra sep com saldo (qtd_planejada disponivel)."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido(admin_user)
        chassi_old = f'TST_F2_OLD_{_uid()}'
        chassi_new = f'TST_F2_NEW_{_uid()}'
        _criar_chassi(modelo, chassi_old, admin_user)
        _criar_chassi(modelo, chassi_new, admin_user)

        # Sep_A (alvo): tem OLD, qtd_planejada=1
        sep_a = AssaiSeparacao(
            pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_EM_SEPARACAO,
        )
        db.session.add(sep_a)
        db.session.flush()
        db.session.add(AssaiSeparacaoSaldoModelo(
            separacao_id=sep_a.id, modelo_id=modelo.id, qtd_planejada=1,
        ))
        db.session.add(AssaiSeparacaoItem(
            separacao_id=sep_a.id, chassi=chassi_old, modelo_id=modelo.id,
            valor_unitario_qpa=Decimal('1000.00'),
        ))
        emitir_evento(chassi_old, EVENTO_SEPARADA, operador_id=admin_user.id)

        # Sep_B (outra sep com saldo): qtd_planejada=2 mas vazia (saldo livre = 2)
        sep_b = AssaiSeparacao(
            pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_EM_SEPARACAO,
        )
        db.session.add(sep_b)
        db.session.flush()
        db.session.add(AssaiSeparacaoSaldoModelo(
            separacao_id=sep_b.id, modelo_id=modelo.id, qtd_planejada=2,
        ))
        db.session.commit()
        sep_b_id = sep_b.id

        # Carregamento adiciona NEW, expulsa OLD da Sep_A
        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi_new, operador_id=admin_user.id)
        db.session.commit()

        finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        # OLD deve ter sido REALOCADO em Sep_B (S2=b), nao DISPONIVEL
        assert status_efetivo(chassi_old) == EVENTO_SEPARADA  # ainda separada (em Sep_B)
        item_realoc = AssaiSeparacaoItem.query.filter_by(
            separacao_id=sep_b_id, chassi=chassi_old,
        ).first()
        assert item_realoc is not None
        db.session.rollback()
