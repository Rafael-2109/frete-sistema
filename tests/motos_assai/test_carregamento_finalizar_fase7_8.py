"""Testes finalizar_carregamento Fases 7-8 (divergencia NF + recalcular pedido).

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md §6 Fases 7-8
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md Tasks 11-12
"""
import uuid
import pytest
from decimal import Decimal

from app import db
from app.motos_assai.models import (
    AssaiLoja, AssaiModelo, AssaiPedidoVenda, AssaiPedidoVendaLoja,
    AssaiPedidoVendaItem, AssaiSeparacao, AssaiSeparacaoItem, AssaiMoto,
    AssaiNfQpa, AssaiNfQpaItem, AssaiDivergencia,
    SEPARACAO_STATUS_FECHADA,
    PEDIDO_STATUS_ABERTO,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
    EVENTO_SEPARADA,
    NF_STATUS_BATEU, NF_STATUS_DIVERGENTE,
    NF_STATUS_CANCELADA,
    DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO,
    DIVERGENCIA_TIPO_CARREGAMENTO_CHASSI_FORA_NF,
)
from app.motos_assai.services.moto_evento_service import emitir_evento
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
        numero=f'TST-CAR-F7_8-{uid}', status=PEDIDO_STATUS_ABERTO,
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
# Fase 7 - Divergencia se NF BATEU
# ============================================================

def test_fase7_nf_bateu_chassi_fora_carregamento_cria_divergencia(app, admin_user):
    """A4: NF BATEU + Carregamento difere -> cria divergencia + NF vai para DIVERGENTE."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido(admin_user)
        chassi_c1 = f'TST_F7C1_{_uid()}'
        chassi_c2 = f'TST_F7C2_{_uid()}'  # estava na NF, mas nao no carregamento
        chassi_c3 = f'TST_F7C3_{_uid()}'  # esta no carregamento, mas nao na NF
        for c in [chassi_c1, chassi_c2, chassi_c3]:
            _criar_chassi(modelo, c, admin_user)

        sep = AssaiSeparacao(
            pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA,
        )
        db.session.add(sep)
        db.session.flush()
        for c in [chassi_c1, chassi_c2]:
            db.session.add(AssaiSeparacaoItem(
                separacao_id=sep.id, chassi=c, modelo_id=modelo.id,
                valor_unitario_qpa=Decimal('1000.00'),
            ))
            emitir_evento(c, EVENTO_SEPARADA, operador_id=admin_user.id)

        nf = AssaiNfQpa(
            chave_44=f'{_uid()}'.ljust(44, '0')[:44], numero=f'NF{_uid()}',
            loja_id=loja.id,
            separacao_id=sep.id, status_match=NF_STATUS_BATEU,
        )
        db.session.add(nf)
        db.session.flush()
        for c in [chassi_c1, chassi_c2]:
            db.session.add(AssaiNfQpaItem(
                nf_id=nf.id, chassi=c, modelo_extraido='DOT',
                valor_extraido=Decimal('1000.00'),
            ))
        db.session.commit()
        nf_id = nf.id

        # Carregamento real: tem c1 + c3. c2 NAO foi carregado, c3 NAO esta na NF.
        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi_c1, operador_id=admin_user.id)
        escanear_carregamento_item(car.id, chassi_c3, operador_id=admin_user.id)
        db.session.commit()

        finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        # Divergencia para c3 (Carregamento tem mas NF nao)
        div_car = AssaiDivergencia.query.filter_by(
            chassi=chassi_c3, tipo=DIVERGENCIA_TIPO_CARREGAMENTO_CHASSI_FORA_NF,
        ).first()
        assert div_car is not None
        assert div_car.nf_id == nf_id

        # Divergencia para c2 (NF tem mas Carregamento nao)
        div_nf = AssaiDivergencia.query.filter_by(
            chassi=chassi_c2, tipo=DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO,
        ).first()
        assert div_nf is not None

        # A4: NF muda de BATEU para DIVERGENTE
        nf_ref = AssaiNfQpa.query.get(nf_id)
        assert nf_ref.status_match == NF_STATUS_DIVERGENTE
        db.session.rollback()


def test_fase7_nf_nao_bateu_ignora(app, admin_user):
    """S22=a: Carregamento ignora NFs DIVERGENTE/NAO_RECONCILIADO/CANCELADA."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido(admin_user)
        chassi = f'TST_F7N_{_uid()}'
        _criar_chassi(modelo, chassi, admin_user)

        sep = AssaiSeparacao(
            pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA,
        )
        db.session.add(sep)
        db.session.flush()

        nf = AssaiNfQpa(
            chave_44=f'D{_uid()}'.ljust(44, '0')[:44], numero=f'NF{_uid()}',
            loja_id=loja.id,
            separacao_id=sep.id, status_match=NF_STATUS_DIVERGENTE,
        )
        db.session.add(nf)
        db.session.commit()
        nf_id = nf.id

        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi, operador_id=admin_user.id)
        db.session.commit()

        finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        # NAO deve criar divergencia (NF nao esta BATEU)
        divs = AssaiDivergencia.query.filter_by(nf_id=nf_id).all()
        assert len(divs) == 0
        db.session.rollback()


def test_fase7_a3_filtra_nf_cancelada(app, admin_user):
    """A3: query filtra NFs CANCELADA - busca apenas NF ativa."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido(admin_user)
        chassi = f'TST_F7A3_{_uid()}'
        _criar_chassi(modelo, chassi, admin_user)

        sep = AssaiSeparacao(
            pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA,
        )
        db.session.add(sep)
        db.session.flush()

        # NF cancelada (deve ser ignorada na query)
        nf_cancelada = AssaiNfQpa(
            chave_44=f'C{_uid()}'.ljust(44, '0')[:44], numero=f'NF{_uid()}',
            loja_id=loja.id,
            separacao_id=sep.id, status_match=NF_STATUS_CANCELADA,
        )
        db.session.add(nf_cancelada)
        db.session.commit()
        sep_id = sep.id

        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi, operador_id=admin_user.id)
        db.session.commit()

        finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        # NAO deve criar divergencia (NF cancelada nao deve ser confrontada)
        divs = AssaiDivergencia.query.filter_by(separacao_id=sep_id).all()
        assert len(divs) == 0
        db.session.rollback()


# ============================================================
# Fase 8 - recalcular_status_pedido (A13 defensivo)
# ============================================================

def test_fase8_recalcular_status_pedido_chamado(app, admin_user, monkeypatch):
    """A13: finalizar_carregamento chama recalcular_status_pedido defensivamente."""
    with app.app_context():
        from app.motos_assai.services import pedido_status_service
        chamadas = []

        original = pedido_status_service.recalcular_status_pedido

        def spy(pid):
            chamadas.append(pid)
            return original(pid)

        monkeypatch.setattr(pedido_status_service, 'recalcular_status_pedido', spy)
        # Patch tambem no namespace de carregamento_service (que importou
        # `recalcular_status_pedido` no topo). Sem isso o patch nao tem efeito.
        monkeypatch.setattr(
            'app.motos_assai.services.carregamento_service.recalcular_status_pedido',
            spy,
        )

        pedido, loja, modelo = _setup_pedido(admin_user)
        chassi = f'TST_F8_{_uid()}'
        _criar_chassi(modelo, chassi, admin_user)
        db.session.commit()

        car = criar_carregamento(pedido.id, loja.id, operador_id=admin_user.id)
        db.session.flush()
        escanear_carregamento_item(car.id, chassi, operador_id=admin_user.id)
        db.session.commit()

        finalizar_carregamento(car.id, operador_id=admin_user.id)
        db.session.commit()

        assert pedido.id in chamadas
        db.session.rollback()
