"""Testes finalizar_carregamento Fase 3 (limite pedido + LIFO + S14 escalar).

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md §6 Fase 3
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md Task 7
"""
import uuid
import time
import pytest
from decimal import Decimal

from app import db
from app.motos_assai.models import (
    AssaiLoja, AssaiModelo, AssaiPedidoVenda, AssaiPedidoVendaLoja,
    AssaiPedidoVendaItem, AssaiSeparacao, AssaiSeparacaoItem, AssaiMoto,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_CARREGADA,
    PEDIDO_STATUS_ABERTO,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
    EVENTO_SEPARADA, EVENTO_CARREGADA,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, escanear_carregamento_item, finalizar_carregamento,
    CarregamentoExcedenteError,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _setup_pedido_qtd(admin, qtd_pedida=3):
    """Pedido novo + 1 loja + qtd_pedida do modelo DOT (qtd baixa permite testar excedente)."""
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    loja = AssaiLoja.query.first()

    uid = _uid()
    pedido = AssaiPedidoVenda(
        numero=f'TST-CAR-F3-{uid}', status=PEDIDO_STATUS_ABERTO,
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
        qtd_pedida=qtd_pedida,
        valor_unitario=Decimal('1000.00'),
        valor_total=Decimal('1000.00') * qtd_pedida,
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


def test_fase3_excedente_remove_LIFO_outras_seps(app, admin_user):
    """R1.2: excedente remove os mais RECENTES das outras seps."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido_qtd(admin_user, qtd_pedida=3)
        chassi_old = f'TST_F3O_{_uid()}'  # mais antigo
        chassi_new_outra = f'TST_F3OUT_{_uid()}'  # mais recente em outra sep
        chassi_n1 = f'TST_F3N1_{_uid()}'
        chassi_n2 = f'TST_F3N2_{_uid()}'
        for c in [chassi_old, chassi_new_outra, chassi_n1, chassi_n2]:
            _criar_chassi(modelo, c, admin_user)

        # Sep_outra: tem chassi_old (mais antigo) + chassi_new_outra (mais recente). Total=2
        sep_outra = AssaiSeparacao(
            pedido_id=pedido.id, loja_id=loja.id,
            status=SEPARACAO_STATUS_EM_SEPARACAO,
        )
        db.session.add(sep_outra)
        db.session.flush()
        item_old = AssaiSeparacaoItem(
            separacao_id=sep_outra.id, chassi=chassi_old,
            modelo_id=modelo.id, valor_unitario_qpa=Decimal('1000.00'),
        )
        db.session.add(item_old)
        db.session.flush()
        time.sleep(0.05)
        item_new = AssaiSeparacaoItem(
            separacao_id=sep_outra.id, chassi=chassi_new_outra,
            modelo_id=modelo.id, valor_unitario_qpa=Decimal('1000.00'),
        )
        db.session.add(item_new)
        emitir_evento(chassi_old, EVENTO_SEPARADA, operador_id=admin_user.id)
        emitir_evento(chassi_new_outra, EVENTO_SEPARADA, operador_id=admin_user.id)
        db.session.commit()
        sep_outra_id = sep_outra.id

        # Carregamento: 2 chassis novos. Total = 2+2 = 4 > pedido(3). Excedente=1.
        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi_n1, operador_id=admin_user.id)
        escanear_carregamento_item(car.id, chassi_n2, operador_id=admin_user.id)
        db.session.commit()

        finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        # Excedente=1. LIFO remove o mais recente (chassi_new_outra). chassi_old permanece.
        items_outra = AssaiSeparacaoItem.query.filter_by(separacao_id=sep_outra_id).all()
        chassis = {it.chassi for it in items_outra}
        assert chassis == {chassi_old}  # chassi_new_outra removido (LIFO)
        assert status_efetivo(chassi_new_outra) == EVENTO_DISPONIVEL
        assert status_efetivo(chassi_old) == EVENTO_SEPARADA
        db.session.rollback()


def test_fase3_escalar_quando_outras_seps_carregada_faturada(app, admin_user):
    """S14=a: se excedente nao cabe em (EM_SEPARACAO, FECHADA), escala via CarregamentoExcedenteError."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido_qtd(admin_user, qtd_pedida=3)
        chassi_carr1 = f'TST_F3C1_{_uid()}'
        chassi_carr2 = f'TST_F3C2_{_uid()}'
        chassi_n1 = f'TST_F3N1_{_uid()}'
        chassi_n2 = f'TST_F3N2_{_uid()}'
        for c in [chassi_carr1, chassi_carr2, chassi_n1, chassi_n2]:
            _criar_chassi(modelo, c, admin_user)

        # Sep_carregada: tem chassi_carr1 + chassi_carr2. NAO pode tirar (S14=a).
        sep_carr = AssaiSeparacao(
            pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_CARREGADA,
        )
        db.session.add(sep_carr)
        db.session.flush()
        for c in [chassi_carr1, chassi_carr2]:
            db.session.add(AssaiSeparacaoItem(
                separacao_id=sep_carr.id, chassi=c, modelo_id=modelo.id,
                valor_unitario_qpa=Decimal('1000.00'),
            ))
            emitir_evento(c, EVENTO_SEPARADA, operador_id=admin_user.id)
            emitir_evento(c, EVENTO_CARREGADA, operador_id=admin_user.id)
        db.session.commit()
        sep_carr_id = sep_carr.id

        # Carregamento: 2 chassis novos. Total = 2+2 = 4 > pedido(3). Excedente=1.
        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi_n1, operador_id=admin_user.id)
        escanear_carregamento_item(car.id, chassi_n2, operador_id=admin_user.id)
        db.session.commit()

        with pytest.raises(CarregamentoExcedenteError) as exc:
            finalizar_carregamento(car.id, operador_id=admin_user.id)

        assert exc.value.qtd_excedente == 1
        assert sep_carr_id in exc.value.seps_bloqueadas
        db.session.rollback()


def test_fase3_sem_excedente_no_op(app, admin_user):
    """Total <= pedido: Fase 3 nao remove nada."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido_qtd(admin_user, qtd_pedida=3)
        chassi_n1 = f'TST_F3SOK1_{_uid()}'
        chassi_n2 = f'TST_F3SOK2_{_uid()}'
        chassi_n3 = f'TST_F3SOK3_{_uid()}'
        for c in [chassi_n1, chassi_n2, chassi_n3]:
            _criar_chassi(modelo, c, admin_user)
        db.session.commit()

        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        for c in [chassi_n1, chassi_n2, chassi_n3]:
            escanear_carregamento_item(car.id, c, operador_id=admin_user.id)
        db.session.commit()

        sep_alvo = finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        items = AssaiSeparacaoItem.query.filter_by(separacao_id=sep_alvo.id).all()
        assert len(items) == 3  # qtd_pedida=3, sem excedente
        db.session.rollback()
