"""Testes finalizar_carregamento Fase 1 (identificar/criar sep alvo).

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md §6 Fase 1
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md Task 5
"""
import uuid
import pytest
from decimal import Decimal

from app import db
from app.motos_assai.models import (
    AssaiLoja, AssaiModelo, AssaiPedidoVenda, AssaiPedidoVendaLoja,
    AssaiPedidoVendaItem, AssaiSeparacao, AssaiSeparacaoItem, AssaiMoto,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_CARREGADA,
    PEDIDO_STATUS_ABERTO,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
)
from app.motos_assai.services.moto_evento_service import emitir_evento
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, escanear_carregamento_item, finalizar_carregamento,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _setup_pedido(admin):
    """Pedido novo + 1 loja + saldo 20 motos do modelo DOT (qtd alta evita Fase 3)."""
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    loja = AssaiLoja.query.first()

    uid = _uid()
    pedido = AssaiPedidoVenda(
        numero=f'TST-CAR-F1-{uid}', status=PEDIDO_STATUS_ABERTO,
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
        qtd_pedida=20, valor_unitario=Decimal('1000.00'), valor_total=Decimal('20000.00'),
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


def test_fase1_sem_sep_cria_sep_carregada_automatica(app, admin_user):
    """Q4/Q6: sem sep previa, finalizar Carregamento cria sep em CARREGADA."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido(admin_user)
        chassi = f'TST_F1_{_uid()}'
        _criar_chassi(modelo, chassi, admin_user)
        db.session.commit()

        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi, operador_id=admin_user.id)
        db.session.commit()

        sep_alvo = finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        assert sep_alvo.status == SEPARACAO_STATUS_CARREGADA
        assert sep_alvo.pedido_id == pedido.id
        assert sep_alvo.loja_id == loja.id
        # A9: fechada_em + fechada_por_id usam operador do carregamento
        assert sep_alvo.fechada_em is not None
        assert sep_alvo.fechada_por_id == admin_user.id
        db.session.rollback()


def test_fase1_uma_sep_em_separacao_e_alvo(app, admin_user):
    """Sep EM_SEPARACAO eh alvo (apenas 1 candidata)."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido(admin_user)
        chassi = f'TST_F1_{_uid()}'
        _criar_chassi(modelo, chassi, admin_user)
        sep_existente = AssaiSeparacao(
            pedido_id=pedido.id, loja_id=loja.id,
            status=SEPARACAO_STATUS_EM_SEPARACAO,
        )
        db.session.add(sep_existente)
        db.session.commit()
        sep_existente_id = sep_existente.id

        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi, operador_id=admin_user.id)
        db.session.commit()

        sep_alvo = finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        assert sep_alvo.id == sep_existente_id
        assert sep_alvo.status == SEPARACAO_STATUS_CARREGADA  # transicionou
        db.session.rollback()


def test_fase1_n_seps_escolhe_mais_chassis_em_comum(app, admin_user):
    """Q5: match por chassis em comum (Sep_A tem 5 dos chassis do car, Sep_B tem 1)."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido(admin_user)

        # Carregamento: 6 chassis [C1..C6]
        chassis = [f'TST_F1_{_uid()}' for _ in range(6)]
        for c in chassis:
            _criar_chassi(modelo, c, admin_user)

        # Sep_A: tem [C1..C5] (5 em comum)
        sep_a = AssaiSeparacao(
            pedido_id=pedido.id, loja_id=loja.id,
            status=SEPARACAO_STATUS_FECHADA,
        )
        db.session.add(sep_a)
        db.session.flush()
        for c in chassis[:5]:
            db.session.add(AssaiSeparacaoItem(
                separacao_id=sep_a.id, chassi=c, modelo_id=modelo.id,
                valor_unitario_qpa=Decimal('1000.00'),
            ))

        # Sep_B: tem so [C6] (1 em comum)
        sep_b = AssaiSeparacao(
            pedido_id=pedido.id, loja_id=loja.id,
            status=SEPARACAO_STATUS_FECHADA,
        )
        db.session.add(sep_b)
        db.session.flush()
        db.session.add(AssaiSeparacaoItem(
            separacao_id=sep_b.id, chassi=chassis[5], modelo_id=modelo.id,
            valor_unitario_qpa=Decimal('1000.00'),
        ))
        db.session.commit()
        sep_a_id = sep_a.id

        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        for c in chassis:
            escanear_carregamento_item(car.id, c, operador_id=admin_user.id)
        db.session.commit()

        sep_alvo = finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        # Sep_A tem mais chassis em comum (5 vs 1)
        assert sep_alvo.id == sep_a_id
        db.session.rollback()


def test_fase1_sep_carregada_NAO_eh_alvo(app, admin_user):
    """S18=b/A2: sep em CARREGADA NAO entra no match (ja tem carregamento - 1:1)."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido(admin_user)
        chassi = f'TST_F1_{_uid()}'
        _criar_chassi(modelo, chassi, admin_user)

        sep_carregada = AssaiSeparacao(
            pedido_id=pedido.id, loja_id=loja.id,
            status=SEPARACAO_STATUS_CARREGADA,
        )
        db.session.add(sep_carregada)
        db.session.flush()
        db.session.add(AssaiSeparacaoItem(
            separacao_id=sep_carregada.id, chassi=chassi, modelo_id=modelo.id,
            valor_unitario_qpa=Decimal('1000.00'),
        ))
        db.session.commit()
        sep_carregada_id = sep_carregada.id

        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi, operador_id=admin_user.id)
        db.session.commit()

        sep_alvo = finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        # Sep nova foi criada (CARREGADA existente foi ignorada)
        assert sep_alvo.id != sep_carregada_id
        assert sep_alvo.status == SEPARACAO_STATUS_CARREGADA
        db.session.rollback()
