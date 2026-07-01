import uuid
from decimal import Decimal

from app import db
from app.motos_assai.models import AssaiEstoqueMovimento, AssaiPeca
from app.motos_assai.services.peca_service import criar_peca
from app.motos_assai.services.movimento_service import saldo


def _limpar_peca(app, pid):
    """Limpa a peça de teste + seu ledger (FK ondelete='RESTRICT' exige apagar
    as movimentações antes da peça)."""
    with app.app_context():
        AssaiEstoqueMovimento.query.filter_by(peca_id=pid).delete()
        p = db.session.get(AssaiPeca, pid)
        if p:
            db.session.delete(p)
        db.session.commit()


def test_lista_estoque_200(login_admin):
    assert login_admin.get('/motos-assai/estoque-pecas').status_code == 200


def test_entrada_avulsa_incrementa_saldo(login_admin, app, admin_user):
    with app.app_context():
        p = criar_peca(nome=f'PZE{uuid.uuid4().hex[:6].upper()}', operador_id=admin_user.id)
        db.session.commit()
        pid = p.id
    try:
        resp = login_admin.post('/motos-assai/estoque-pecas/entrada', data={
            'peca_id': pid, 'quantidade': '5', 'custo_unitario': '10,00', 'recebimento_ref': 'LOTE1'})
        assert resp.status_code in (302, 200)
        with app.app_context():
            assert saldo(pid) == Decimal('5.000')
    finally:
        _limpar_peca(app, pid)


def test_detalhe_404_peca_inexistente(login_admin):
    resp = login_admin.get('/motos-assai/estoque-pecas/999999999', follow_redirects=True)
    assert resp.status_code == 200  # redireciona para lista com flash


def test_detalhe_200_apos_entrada(login_admin, app, admin_user):
    with app.app_context():
        p = criar_peca(nome=f'PZD{uuid.uuid4().hex[:6].upper()}', operador_id=admin_user.id)
        db.session.commit()
        pid = p.id
    try:
        login_admin.post('/motos-assai/estoque-pecas/entrada', data={
            'peca_id': pid, 'quantidade': '3', 'custo_unitario': '5,00'})
        resp = login_admin.get(f'/motos-assai/estoque-pecas/{pid}')
        assert resp.status_code == 200
    finally:
        _limpar_peca(app, pid)


def test_entrada_malformada_nao_500(login_admin, app, admin_user):
    """Espelha a lição do Task 10: quantidade/custo malformado deve dar
    flash gracioso, não estourar 500 nem gravar linha no ledger."""
    with app.app_context():
        p = criar_peca(nome=f'PZBAD{uuid.uuid4().hex[:6].upper()}', operador_id=admin_user.id)
        db.session.commit()
        pid = p.id
    try:
        resp = login_admin.post('/motos-assai/estoque-pecas/entrada', data={
            'peca_id': pid, 'quantidade': 'abc', 'custo_unitario': '10,00'})
        assert resp.status_code in (302, 200)
        with app.app_context():
            assert saldo(pid) == Decimal('0')
    finally:
        _limpar_peca(app, pid)


def test_ajustar_e_descartar_fluxo(login_admin, app, admin_user):
    with app.app_context():
        p = criar_peca(nome=f'PZAJ{uuid.uuid4().hex[:6].upper()}', operador_id=admin_user.id)
        db.session.commit()
        pid = p.id
    try:
        login_admin.post('/motos-assai/estoque-pecas/entrada', data={
            'peca_id': pid, 'quantidade': '10', 'custo_unitario': '2,00'})
        resp = login_admin.post('/motos-assai/estoque-pecas/ajustar', data={
            'peca_id': pid, 'delta': '-2', 'motivo': 'contagem física'})
        assert resp.status_code in (302, 200)
        with app.app_context():
            assert saldo(pid) == Decimal('8.000')

        resp = login_admin.post('/motos-assai/estoque-pecas/descartar', data={
            'peca_id': pid, 'quantidade': '3'})
        assert resp.status_code in (302, 200)
        with app.app_context():
            assert saldo(pid) == Decimal('5.000')
    finally:
        _limpar_peca(app, pid)
