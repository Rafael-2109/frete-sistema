"""Testes finalizar_carregamento Fases 4-6 (sep CARREGADA + Excel + mirror).

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md §6 Fases 4-6
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md Tasks 8-10
"""
import uuid
import pytest
from decimal import Decimal

from app import db
from app.motos_assai.models import (
    AssaiLoja, AssaiModelo, AssaiPedidoVenda, AssaiPedidoVendaLoja,
    AssaiPedidoVendaItem, AssaiSeparacao, AssaiSeparacaoItem, AssaiMoto,
    AssaiCarregamento, AssaiPedidoExcel,
    SEPARACAO_STATUS_FECHADA, SEPARACAO_STATUS_CARREGADA,
    CARREGAMENTO_STATUS_FINALIZADO,
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
    """Pedido novo + 1 loja + saldo 10 motos do modelo DOT."""
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    loja = AssaiLoja.query.first()

    uid = _uid()
    pedido = AssaiPedidoVenda(
        numero=f'TST-CAR-F4_5_6-{uid}', status=PEDIDO_STATUS_ABERTO,
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
        qtd_pedida=10, valor_unitario=Decimal('1000.00'), valor_total=Decimal('10000.00'),
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


# ============================================================
# Fase 4 - Sep CARREGADA + emitir evento CARREGADA
# ============================================================

def test_fase4_sep_alvo_status_carregada_apos_finalize(app, admin_user):
    """Sep alvo fica em CARREGADA depois do finalize."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido(admin_user)
        chassi = f'TST_F4S_{_uid()}'
        _criar_chassi(modelo, chassi, admin_user)
        db.session.commit()

        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi, operador_id=admin_user.id)
        db.session.commit()

        sep_alvo = finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        assert sep_alvo.status == SEPARACAO_STATUS_CARREGADA
        db.session.rollback()


def test_fase4_carregamento_status_finalizado(app, admin_user):
    """Carregamento fica FINALIZADO + finalizado_em + separacao_id setados."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido(admin_user)
        chassi = f'TST_F4F_{_uid()}'
        _criar_chassi(modelo, chassi, admin_user)
        db.session.commit()

        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        car_id = car.id
        escanear_carregamento_item(car.id, chassi, operador_id=admin_user.id)
        db.session.commit()

        finalizar_carregamento(car_id, operador_id=admin_user.id)
        db.session.commit()

        car_ref = AssaiCarregamento.query.get(car_id)
        assert car_ref.status == CARREGAMENTO_STATUS_FINALIZADO
        assert car_ref.finalizado_em is not None
        assert car_ref.finalizado_por_id == admin_user.id
        assert car_ref.separacao_id is not None  # vinculo Sep <-> Carregamento (Q2)
        db.session.rollback()


def test_fase4_emite_evento_carregada_para_todos_chassis(app, admin_user):
    """Fase 4 emite evento CARREGADA para TODOS chassis do carregamento."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido(admin_user)
        chassis = [f'TST_F4E{i}_{_uid()}' for i in range(3)]
        for c in chassis:
            _criar_chassi(modelo, c, admin_user)
        db.session.commit()

        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        for c in chassis:
            escanear_carregamento_item(car.id, c, operador_id=admin_user.id)
        db.session.commit()

        finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        for c in chassis:
            assert status_efetivo(c) == EVENTO_CARREGADA
        db.session.rollback()


# ============================================================
# Fase 5 - regenerar Excel Q.P.A. (versionado)
# ============================================================

def test_fase5_excel_versao_1_quando_nao_havia_anterior(app, admin_user):
    """Sem Excel anterior, novo Excel sai com versao=1, ativo=True."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido(admin_user)
        chassi = f'TST_F5V1_{_uid()}'
        _criar_chassi(modelo, chassi, admin_user)
        db.session.commit()

        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi, operador_id=admin_user.id)
        db.session.commit()

        sep_alvo = finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        excels = AssaiPedidoExcel.query.filter_by(separacao_id=sep_alvo.id).all()
        assert len(excels) == 1
        assert excels[0].versao == 1
        assert excels[0].ativo is True
        assert excels[0].pedido_id == pedido.id
        assert 'Carregamento finalizado' in (excels[0].motivo_regeneracao or '')
        db.session.rollback()


def test_fase5_excel_versao_n_plus_1_quando_havia_anterior(app, admin_user):
    """Com Excel anterior, novo Excel sai com versao=N+1 e antigo fica ativo=False."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido(admin_user)
        chassi = f'TST_F5V2_{_uid()}'
        _criar_chassi(modelo, chassi, admin_user)

        sep_existente = AssaiSeparacao(
            pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA,
        )
        db.session.add(sep_existente)
        db.session.flush()
        db.session.add(AssaiPedidoExcel(
            pedido_id=pedido.id, separacao_id=sep_existente.id,
            s3_key='legado.xlsx', versao=1, ativo=True,
        ))
        db.session.commit()
        sep_existente_id = sep_existente.id

        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi, operador_id=admin_user.id)
        db.session.commit()

        sep_alvo = finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        assert sep_alvo.id == sep_existente_id  # mesma sep
        excels = (AssaiPedidoExcel.query
                  .filter_by(separacao_id=sep_alvo.id)
                  .order_by(AssaiPedidoExcel.versao)
                  .all())
        assert len(excels) == 2
        assert excels[0].versao == 1 and excels[0].ativo is False  # antigo desativado
        assert excels[1].versao == 2 and excels[1].ativo is True   # novo ativo
        db.session.rollback()


# ============================================================
# Fase 6 - sincronizar mirror Nacom
# ============================================================

def test_fase6_mirror_nacom_atualizado(app, admin_user):
    """Apos finalize, mirror Nacom deve refletir os chassis da sep alvo."""
    with app.app_context():
        from app.separacao.models import Separacao
        from app.motos_assai.services.separacao_mirror_service import (
            mirror_assai_to_separacao, lote_id_de,
        )

        pedido, loja, modelo = _setup_pedido(admin_user)
        chassi = f'TST_F6_{_uid()}'
        _criar_chassi(modelo, chassi, admin_user)

        # Pre-condicao: ja precisa ter linha espelho previa para sincronizar mexer.
        # Como a sep e criada DENTRO do finalize, sincronizar so funciona se lote ja existe.
        # Para teste real do mirror via sep CARREGADA, precisamos primeiro criar sep FECHADA,
        # rodar mirror inicial, depois finalize_carregamento usar essa sep e disparar
        # sincronizar para refletir delta.
        sep_existente = AssaiSeparacao(
            pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA,
        )
        db.session.add(sep_existente)
        db.session.flush()
        # Espelhar no mirror Nacom (precondicao para sincronizar funcionar depois)
        # Item novo na sep para mirror inicial criar linha
        db.session.add(AssaiSeparacaoItem(
            separacao_id=sep_existente.id, chassi=chassi,
            modelo_id=modelo.id, valor_unitario_qpa=Decimal('1000.00'),
        ))
        emitir_evento(chassi, EVENTO_SEPARADA, operador_id=admin_user.id)
        db.session.commit()
        sep_existente_id = sep_existente.id

        # Mirror inicial
        mirror_assai_to_separacao(sep_existente_id)
        db.session.commit()

        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi, operador_id=admin_user.id)
        db.session.commit()

        sep_alvo = finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        # Linha em separacao Nacom deve continuar refletindo o chassi
        lote_id = lote_id_de(sep_alvo.id)
        linhas = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
        assert len(linhas) == 1
        assert linhas[0].chassi_assai == chassi
        db.session.rollback()
