"""Smoke das rotas de Coletas CarVia — render real (test client + login mock).

Pega erros de runtime (url_for de endpoint inexistente, atributo no template) que o
compile do Jinja nao pega. Login via patch('flask_login.utils._get_user') (padrao do projeto).
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app.carvia.services.documentos.coleta_service import CarviaColetaService


def _user():
    u = MagicMock()
    u.is_authenticated = True
    u.sistema_carvia = True
    u.perfil = 'administrador'
    u.email = 'test@bot'
    return u


def test_listar_e_criar_render(db, client):
    with patch('flask_login.utils._get_user', return_value=_user()):
        assert client.get('/carvia/coletas').status_code == 200
        assert client.get('/carvia/coletas/criar').status_code == 200


def test_detalhe_render_rascunho_e_coletada(db, client):
    # RASCUNHO com 1 linha
    coleta = CarviaColetaService.criar_coleta(
        contratado_nome='Ze', placa='ABC1D23', valor_coleta=Decimal('300'),
        local_cd='TENENTE_MARQUES', usuario='test@bot')
    CarviaColetaService.adicionar_linha(coleta, numero_nf='123', nome_cliente_rascunho='Loja X', qtd_motos=2)
    db.session.commit()  # savepoint commit (revertido no teardown) — visivel ao request
    with patch('flask_login.utils._get_user', return_value=_user()):
        assert client.get(f'/carvia/coletas/{coleta.id}').status_code == 200
        # sugerir-nf (AJAX) responde JSON 200
        linha = coleta.nfs.first()
        r = client.get(f'/carvia/coletas/linhas/{linha.id}/sugerir-nf')
        assert r.status_code == 200
        assert r.get_json()['success'] is True

    # COLETADA (congelada) ainda renderiza
    CarviaColetaService.marcar_coletada(coleta, usuario='test@bot')
    db.session.commit()
    with patch('flask_login.utils._get_user', return_value=_user()):
        assert client.get(f'/carvia/coletas/{coleta.id}').status_code == 200


def test_guard_sem_carvia_redireciona(db, client):
    u = _user(); u.sistema_carvia = False
    with patch('flask_login.utils._get_user', return_value=u):
        r = client.get('/carvia/coletas')
        assert r.status_code in (301, 302)  # redirect (acesso negado)
