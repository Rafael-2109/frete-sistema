import uuid
import pytest
from decimal import Decimal
from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaLoja, AssaiPedidoVendaItem,
    AssaiLoja, AssaiModelo,
    AssaiMoto, AssaiSeparacao, AssaiSeparacaoItem,
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_EM_PRODUCAO,
    SEPARACAO_STATUS_FECHADA, SEPARACAO_STATUS_CANCELADA,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
)
from app.motos_assai.services import (
    get_ou_criar_separacao, saldo_pendente_por_modelo, registrar_chassi,
    desfazer_chassi, finalizar_separacao, cancelar_separacao,
    emitir_evento, status_efetivo,
    SeparacaoValidationError,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _setup(app, admin):
    """Cria pedido + 1 loja + 2 chassis disponíveis (DOT)."""
    modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
    loja = AssaiLoja.query.first()  # qualquer loja seeded

    uid = _uid()
    p = AssaiPedidoVenda(numero=f'TST-SEP-{uid}', status=PEDIDO_STATUS_EM_PRODUCAO,
                         criado_por_id=admin.id)
    db.session.add(p); db.session.flush()
    pvl = AssaiPedidoVendaLoja(pedido_id=p.id, loja_id=loja.id)
    db.session.add(pvl); db.session.flush()
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=p.id, pedido_loja_id=pvl.id, loja_id=loja.id, modelo_id=modelo_dot.id,
        qtd_pedida=2, valor_unitario=Decimal('6900'), valor_total=Decimal('13800'),
    ))
    db.session.flush()

    ch_a = f'TST_S_{_uid()}'
    ch_b = f'TST_S_{_uid()}'
    for ch in [ch_a, ch_b]:
        m = AssaiMoto(chassi=ch, modelo_id=modelo_dot.id, cor='CINZA')
        db.session.add(m); db.session.flush()
        emitir_evento(ch, EVENTO_ESTOQUE, admin.id)
        emitir_evento(ch, EVENTO_MONTADA, admin.id)
        emitir_evento(ch, EVENTO_DISPONIVEL, admin.id)
    db.session.commit()
    return p, loja, modelo_dot, ch_a, ch_b


def test_saldo_pendente_inicial(app, admin_user):
    with app.app_context():
        p, loja, _, ch_a, ch_b = _setup(app, admin_user)
        saldos = saldo_pendente_por_modelo(p.id, loja.id)
        assert len(saldos) == 1
        assert saldos[0]['qtd_pendente'] == 2
        db.session.rollback()


def test_registrar_chassi_decrementa_saldo(app, admin_user):
    with app.app_context():
        p, loja, _, ch_a, ch_b = _setup(app, admin_user)
        registrar_chassi(p.id, loja.id, ch_a, admin_user.id)
        saldos = saldo_pendente_por_modelo(p.id, loja.id)
        assert saldos[0]['qtd_separada'] == 1
        assert saldos[0]['qtd_pendente'] == 1
        db.session.rollback()


def test_chassi_nao_disponivel_falha(app, admin_user):
    with app.app_context():
        p, loja, _, ch_a, ch_b = _setup(app, admin_user)
        # Reverte um chassi de volta para REVERTIDA_PARA_MONTADA
        emitir_evento(ch_a, 'REVERTIDA_PARA_MONTADA', admin_user.id)
        db.session.commit()
        with pytest.raises(SeparacaoValidationError, match='DISPONIVEL'):
            registrar_chassi(p.id, loja.id, ch_a, admin_user.id)
        db.session.rollback()


def test_desfazer_devolve_chassi(app, admin_user):
    with app.app_context():
        p, loja, _, ch_a, ch_b = _setup(app, admin_user)
        r = registrar_chassi(p.id, loja.id, ch_a, admin_user.id)
        desfazer_chassi(r['item_id'], admin_user.id)
        assert status_efetivo(ch_a) == EVENTO_DISPONIVEL
        db.session.rollback()


def test_cancelar_devolve_todos(app, admin_user):
    with app.app_context():
        p, loja, _, ch_a, ch_b = _setup(app, admin_user)
        registrar_chassi(p.id, loja.id, ch_a, admin_user.id)
        registrar_chassi(p.id, loja.id, ch_b, admin_user.id)
        sep = AssaiSeparacao.query.filter_by(pedido_id=p.id, loja_id=loja.id).first()
        cancelar_separacao(sep.id, 'cancelado por teste', admin_user.id)
        sep_after = AssaiSeparacao.query.get(sep.id)
        assert sep_after.status == SEPARACAO_STATUS_CANCELADA
        assert status_efetivo(ch_a) == EVENTO_DISPONIVEL
        assert status_efetivo(ch_b) == EVENTO_DISPONIVEL
        db.session.rollback()


def test_finalizar_fechada(app, admin_user):
    with app.app_context():
        p, loja, _, ch_a, ch_b = _setup(app, admin_user)
        registrar_chassi(p.id, loja.id, ch_a, admin_user.id)
        sep = AssaiSeparacao.query.filter_by(pedido_id=p.id, loja_id=loja.id).first()
        finalizar_separacao(sep.id, admin_user.id)
        sep_after = AssaiSeparacao.query.get(sep.id)
        assert sep_after.status == SEPARACAO_STATUS_FECHADA
        db.session.rollback()


def test_idempotencia_get_ou_criar(app, admin_user):
    """get_ou_criar_separacao deve retornar a mesma separação se já existe ativa."""
    with app.app_context():
        p, loja, _, ch_a, ch_b = _setup(app, admin_user)
        sep1 = get_ou_criar_separacao(p.id, loja.id, admin_user.id)
        db.session.flush()
        sep2 = get_ou_criar_separacao(p.id, loja.id, admin_user.id)
        assert sep1.id == sep2.id
        db.session.rollback()
