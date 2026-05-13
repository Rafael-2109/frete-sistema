import uuid
import pytest
from app import db
from app.motos_assai.services import (
    listar_pedidos_consolidaveis, criar_consolidado,
    calcular_totalizadores_por_modelo, gerar_numero_po,
    CompraValidationError,
)
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiCompraMotochefe,
    AssaiCompraMotochefePedido,
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_PARCIALMENTE_FATURADO,
)


def _criar_pedido_minimo(numero, admin_user):
    # Sufixo único para evitar colisão de constraint entre execuções
    sufixo = uuid.uuid4().hex[:8]
    p = AssaiPedidoVenda(
        numero=f'{numero}-{sufixo}',
        status=PEDIDO_STATUS_ABERTO,
        criado_por_id=admin_user.id,
    )
    db.session.add(p)
    db.session.flush()
    return p


def test_gerar_numero_po_sequencial(app):
    with app.app_context():
        n = gerar_numero_po()
        assert n.startswith('MA-')
        assert len(n.split('-')) == 3


def test_criar_consolidado_vazio_falha(app, admin_user):
    with app.app_context():
        with pytest.raises(CompraValidationError, match='Selecione'):
            criar_consolidado([], None, admin_user.id)


def test_criar_consolidado_pedido_inexistente_falha(app, admin_user):
    with app.app_context():
        with pytest.raises(CompraValidationError, match='não encontrados'):
            criar_consolidado([999999], None, admin_user.id)


def test_criar_consolidado_sucesso(app, admin_user):
    with app.app_context():
        p = _criar_pedido_minimo('TEST-CONSOL-001', admin_user)
        compra = criar_consolidado(
            pedido_ids=[p.id],
            motochefe_cnpj='37542484000100',
            criada_por_id=admin_user.id,
        )
        assert compra.numero.startswith('MA-')
        assert compra.status == 'ABERTA'

        # R4.2 (Big Bang Task 20): pedido permanece ABERTO ate primeira NF.
        # Antes: transicionava para EM_PRODUCAO automaticamente.
        p_after = AssaiPedidoVenda.query.get(p.id)
        assert p_after.status == PEDIDO_STATUS_ABERTO

        # Link N:N existe
        link = AssaiCompraMotochefePedido.query.filter_by(
            compra_id=compra.id, pedido_id=p.id,
        ).first()
        assert link is not None

        db.session.rollback()


def test_consolidar_pedido_nao_aberto_falha(app, admin_user):
    with app.app_context():
        p = _criar_pedido_minimo('TEST-CONSOL-002', admin_user)
        # R4.2 (Big Bang Task 20): EM_PRODUCAO removido. Usar PARCIALMENTE_FATURADO
        # como exemplo de status nao-ABERTO para validar a guarda.
        p.status = PEDIDO_STATUS_PARCIALMENTE_FATURADO
        db.session.flush()
        with pytest.raises(CompraValidationError, match='não estão em ABERTO'):
            criar_consolidado([p.id], None, admin_user.id)
        db.session.rollback()
