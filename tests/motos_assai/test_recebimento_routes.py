"""Testes dos endpoints AJAX do wizard de recebimento físico.

Cobre:
  POST /recebimento/validar-chassi
  POST /recebimento/registrar
  POST /recebimento/finalizar/<id>

Usa rollback para não poluir banco. Login via session fixture.
"""

import uuid
import json
import pytest
from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiReciboMotochefe, AssaiReciboItem, AssaiModelo,
    RECIBO_STATUS_AGUARDANDO, RECIBO_STATUS_EM_CONFERENCIA,
    RECIBO_STATUS_CONCLUIDO, RECIBO_STATUS_COM_DIVERGENCIA,
    DIVERGENCIA_CHASSI_EXTRA, DIVERGENCIA_MOTO_FALTANDO,
)
from app.motos_assai.services.compra_service import criar_consolidado


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _setup_recibo_e_itens(app, admin_user, chassis_lista):
    """Cria recibo com itens, retorna (recibo, modelo)."""
    with app.app_context():
        numero = f'RT-{_uid()}'
        p = AssaiPedidoVenda(numero=numero, criado_por_id=admin_user.id, status='ABERTO')
        db.session.add(p)
        db.session.flush()
        compra = criar_consolidado([p.id], None, admin_user.id)

        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        assert modelo, 'Pré-requisito: modelo DOT seeded'

        recibo = AssaiReciboMotochefe(
            compra_id=compra.id,
            numero_recibo=f'REC-{_uid()}',
            status=RECIBO_STATUS_AGUARDANDO,
            criado_por_id=admin_user.id,
        )
        db.session.add(recibo)
        db.session.flush()

        for chassi in chassis_lista:
            db.session.add(AssaiReciboItem(
                recibo_id=recibo.id,
                chassi=chassi,
                modelo_id=modelo.id,
                modelo_texto_recibo='DOT 1000W',
                cor_texto='PRETO',
                conferido=False,
            ))
        db.session.flush()
        return recibo.id, modelo.id


# ---------------------------------------------------------------------------
# POST /recebimento/validar-chassi
# ---------------------------------------------------------------------------

def test_validar_chassi_route_ok(app, admin_user, login_admin):
    """Endpoint valida chassi presente no recibo → ok=True, na_nf=True."""
    with app.app_context():
        chassi = f'RV{_uid()}'
        recibo_id, _ = _setup_recibo_e_itens(app, admin_user, [chassi])

        resp = login_admin.post(
            '/motos-assai/recebimento/validar-chassi',
            json={'recibo_id': recibo_id, 'chassi': chassi},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['ok'] is True
        assert data['na_nf'] is True
        assert data['ja_conferido'] is False
        db.session.rollback()


def test_validar_chassi_route_extra(app, admin_user, login_admin):
    """Chassi não no recibo → ok=False, na_nf=False."""
    with app.app_context():
        recibo_id, _ = _setup_recibo_e_itens(app, admin_user, [f'RV{_uid()}'])

        resp = login_admin.post(
            '/motos-assai/recebimento/validar-chassi',
            json={'recibo_id': recibo_id, 'chassi': f'EXTRA{_uid()}'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['ok'] is False
        assert data['na_nf'] is False
        db.session.rollback()


def test_validar_chassi_route_sem_parametros(app, admin_user, login_admin):
    """Body sem recibo_id ou chassi → 400."""
    with app.app_context():
        resp = login_admin.post(
            '/motos-assai/recebimento/validar-chassi',
            json={},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['ok'] is False


def test_validar_chassi_route_sem_login(app, client):
    """Sem autenticação → redirecionamento (não 200)."""
    resp = client.post(
        '/motos-assai/recebimento/validar-chassi',
        json={'recibo_id': 1, 'chassi': 'TESTE123'},
    )
    # Flask-Login redireciona para login
    assert resp.status_code in {302, 401, 403}


# ---------------------------------------------------------------------------
# POST /recebimento/registrar
# ---------------------------------------------------------------------------

def test_registrar_route_ok(app, admin_user, login_admin):
    """Registra chassi → 200, ok=True, item_id presente."""
    with app.app_context():
        chassi = f'REG{_uid()}'
        recibo_id, modelo_id = _setup_recibo_e_itens(app, admin_user, [chassi])

        resp = login_admin.post(
            '/motos-assai/recebimento/registrar',
            json={
                'recibo_id': recibo_id,
                'chassi': chassi,
                'modelo_id': modelo_id,
                'cor': 'PRETO',
                'qr_code_lido': True,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['ok'] is True
        assert data['item_id'] is not None
        assert data['conferidos'] == 1
        assert data['total'] == 1
        db.session.rollback()


def test_registrar_route_chassi_extra(app, admin_user, login_admin):
    """Chassi extra (não no recibo) → 200, tipo_divergencia=CHASSI_EXTRA."""
    with app.app_context():
        recibo_id, modelo_id = _setup_recibo_e_itens(app, admin_user, [f'ORIG{_uid()}'])
        chassi_extra = f'XTRA{_uid()}'

        resp = login_admin.post(
            '/motos-assai/recebimento/registrar',
            json={
                'recibo_id': recibo_id,
                'chassi': chassi_extra,
                'modelo_id': modelo_id,
                'cor': 'AZUL',
                'qr_code_lido': False,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['ok'] is True
        assert data['tipo_divergencia'] == DIVERGENCIA_CHASSI_EXTRA
        db.session.rollback()


def test_registrar_route_sem_modelo_400(app, admin_user, login_admin):
    """modelo_id=None → 400 com erro."""
    with app.app_context():
        chassi = f'REG{_uid()}'
        recibo_id, _ = _setup_recibo_e_itens(app, admin_user, [chassi])

        resp = login_admin.post(
            '/motos-assai/recebimento/registrar',
            json={
                'recibo_id': recibo_id,
                'chassi': chassi,
                'modelo_id': None,
                'cor': 'PRETO',
                'qr_code_lido': False,
            },
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['ok'] is False
        db.session.rollback()


def test_registrar_route_chassi_vazio_400(app, admin_user, login_admin):
    """chassi em branco → 400."""
    with app.app_context():
        recibo_id, modelo_id = _setup_recibo_e_itens(app, admin_user, [f'TST{_uid()}'])

        resp = login_admin.post(
            '/motos-assai/recebimento/registrar',
            json={
                'recibo_id': recibo_id,
                'chassi': '   ',
                'modelo_id': modelo_id,
                'cor': 'PRETO',
                'qr_code_lido': False,
            },
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['ok'] is False


# ---------------------------------------------------------------------------
# POST /recebimento/finalizar/<id>
# ---------------------------------------------------------------------------

def test_finalizar_route_sem_faltantes(app, admin_user, login_admin):
    """Todos conferidos → 200, status CONCLUIDO e redirect presente."""
    with app.app_context():
        chassi = f'FIN{_uid()}'
        recibo_id, modelo_id = _setup_recibo_e_itens(app, admin_user, [chassi])

        # Registra via route (para garantir consistência com a rota)
        login_admin.post(
            '/motos-assai/recebimento/registrar',
            json={
                'recibo_id': recibo_id,
                'chassi': chassi,
                'modelo_id': modelo_id,
                'cor': 'PRETO',
                'qr_code_lido': True,
            },
        )

        resp = login_admin.post(
            f'/motos-assai/recebimento/finalizar/{recibo_id}',
            json={'confirmar_faltantes': False},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['ok'] is True
        assert data['status'] == RECIBO_STATUS_CONCLUIDO
        assert 'redirect' in data
        db.session.rollback()


def test_finalizar_route_com_faltantes_sem_confirmar_400(app, admin_user, login_admin):
    """Chassis pendentes + confirmar_faltantes=False → 400."""
    with app.app_context():
        recibo_id, _ = _setup_recibo_e_itens(app, admin_user, [f'FAL{_uid()}'])
        # Não confere nenhum

        resp = login_admin.post(
            f'/motos-assai/recebimento/finalizar/{recibo_id}',
            json={'confirmar_faltantes': False},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['ok'] is False
        db.session.rollback()


def test_finalizar_route_com_faltantes_confirmados(app, admin_user, login_admin):
    """Chassis pendentes + confirmar_faltantes=True → 200, status COM_DIVERGENCIA."""
    with app.app_context():
        recibo_id, _ = _setup_recibo_e_itens(app, admin_user, [f'FAL{_uid()}'])
        # Não confere nenhum

        resp = login_admin.post(
            f'/motos-assai/recebimento/finalizar/{recibo_id}',
            json={'confirmar_faltantes': True},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['ok'] is True
        assert data['status'] == RECIBO_STATUS_COM_DIVERGENCIA
        db.session.rollback()
