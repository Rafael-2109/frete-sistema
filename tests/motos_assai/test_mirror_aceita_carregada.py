"""Testes: mirror_assai_to_separacao aceita sep em CARREGADA e FATURADA (S12=a).

Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md (Task 15)

mirror agora aceita 3 estados terminais: FECHADA, CARREGADA, FATURADA.
EM_SEPARACAO continua bloqueando (sep ainda em montagem).
"""
import uuid

import pytest

from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaLoja,
    AssaiLoja, AssaiModelo, AssaiMoto,
    AssaiSeparacao, AssaiSeparacaoItem,
    PEDIDO_STATUS_ABERTO,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_CARREGADA, SEPARACAO_STATUS_FATURADA,
)
from app.motos_assai.services.separacao_mirror_service import (
    mirror_assai_to_separacao, MirrorValidationError,
)
from app.separacao.models import Separacao


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _setup_pedido_loja(admin):
    """Cria pedido + pvl + retorna (pedido, loja, modelo)."""
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    loja = AssaiLoja.query.first()
    uid = _uid()
    pedido = AssaiPedidoVenda(numero=f'TST-MR-{uid}', status=PEDIDO_STATUS_ABERTO,
                              criado_por_id=admin.id)
    db.session.add(pedido); db.session.flush()
    pvl = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
    db.session.add(pvl); db.session.flush()
    return pedido, loja, modelo


def _criar_sep_com_chassi(pedido, loja, modelo, status):
    """Cria sep + 1 item + moto. Retorna sep."""
    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=status)
    db.session.add(sep); db.session.flush()
    chassi = f'TST_MR_{_uid()}'
    moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
    db.session.add(moto); db.session.flush()
    db.session.add(AssaiSeparacaoItem(
        separacao_id=sep.id, chassi=chassi, modelo_id=modelo.id,
        valor_unitario_qpa=1000.0,
    ))
    db.session.flush()
    return sep


def test_mirror_aceita_status_carregada(app, admin_user):
    """S12=a: mirror espelha sep CARREGADA (pos-finalizar_carregamento)."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido_loja(admin_user)
        sep = _criar_sep_com_chassi(pedido, loja, modelo, SEPARACAO_STATUS_CARREGADA)
        db.session.commit()

        criadas = mirror_assai_to_separacao(sep.id)
        db.session.commit()

        assert criadas == 1
        linhas = Separacao.query.filter_by(
            separacao_lote_id=f'ASSAI-SEP-{sep.id}'
        ).all()
        assert len(linhas) == 1
        db.session.rollback()


def test_mirror_aceita_status_faturada(app, admin_user):
    """S1=b: sep nasce FATURADA via NF — mirror deve aceitar."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido_loja(admin_user)
        sep = _criar_sep_com_chassi(pedido, loja, modelo, SEPARACAO_STATUS_FATURADA)
        db.session.commit()

        criadas = mirror_assai_to_separacao(sep.id)
        db.session.commit()

        assert criadas == 1
        linhas = Separacao.query.filter_by(
            separacao_lote_id=f'ASSAI-SEP-{sep.id}'
        ).all()
        assert len(linhas) == 1
        db.session.rollback()


def test_mirror_rejeita_em_separacao(app, admin_user):
    """EM_SEPARACAO continua nao espelhando (sep nao finalizada)."""
    with app.app_context():
        pedido, loja, modelo = _setup_pedido_loja(admin_user)
        sep = _criar_sep_com_chassi(pedido, loja, modelo, SEPARACAO_STATUS_EM_SEPARACAO)
        db.session.commit()

        with pytest.raises(MirrorValidationError, match='EM_SEPARACAO'):
            mirror_assai_to_separacao(sep.id)
        db.session.rollback()
