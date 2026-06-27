"""Smoke tests HTTP das telas de perfis/permissoes HORA (render + fluxo basico).

Exercita o render real dos templates novos/alterados: perfis_lista, perfil_form,
permissoes_lista (accordion + partial _matriz_permissoes) e auth/listar_usuarios.
"""
import uuid

from app.auth.models import Usuario
from app.hora.services import perfil_service


def _novo_usuario(db, *, perfil='administrador', sistema_lojas=True):
    u = Usuario(
        nome='Usuario Rota',
        email=f'{uuid.uuid4().hex[:10]}@test.local',
        senha_hash='x',
        perfil=perfil,
        status='ativo',
        sistema_lojas=sistema_lojas,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _login(client, usuario):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(usuario.id)
        sess['_fresh'] = True


def test_get_perfis_lista_ok(client, db):
    _login(client, _novo_usuario(db))
    resp = client.get('/hora/permissoes/perfis')
    assert resp.status_code == 200
    assert 'Perfis de acesso'.encode() in resp.data


def test_criar_perfil_e_editar_render(client, db):
    _login(client, _novo_usuario(db))
    resp = client.post(
        '/hora/permissoes/perfis/novo',
        data={'nome': 'Vendedor Loja'},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    p = perfil_service.get_perfil_por_slug('hora_vendedor_loja')
    assert p is not None
    # tela de edicao do esqueleto renderiza (inclui o partial da matriz)
    resp_edit = client.get(f'/hora/permissoes/perfis/{p.id}')
    assert resp_edit.status_code == 200
    assert b'perm_vendas_ver' in resp_edit.data  # checkbox da matriz presente


def test_salvar_skeleton_via_post(client, db):
    _login(client, _novo_usuario(db))
    p = perfil_service.criar_perfil('Operador Rota')
    resp = client.post(
        f'/hora/permissoes/perfis/{p.id}/salvar',
        data={'nome': 'Operador Rota', 'perm_estoque_ver': '1', 'perm_vendas_ver': '1'},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    sk = perfil_service.get_skeleton(p.id)
    assert sk['estoque']['ver'] is True
    assert sk['vendas']['ver'] is True
    assert sk['lojas']['ver'] is False


def test_permissoes_lista_accordion_render(client, db):
    admin = _novo_usuario(db)
    _login(client, admin)
    # usuario HORA com perfil aplicado p/ exercitar badge + accordion + matriz
    p = perfil_service.criar_perfil('Perfil Render')
    perfil_service.salvar_skeleton(p.id, {'estoque': {'ver': True}})
    alvo = _novo_usuario(db, perfil='financeiro', sistema_lojas=True)
    perfil_service.aplicar_perfil_em_usuario(alvo.id, p.slug)

    resp = client.get('/hora/permissoes')
    assert resp.status_code == 200
    assert b'accordion' in resp.data
    assert b'Perfil Render' in resp.data           # badge do perfil HORA
    assert b'Aplicar perfil' in resp.data           # seletor de perfil no card
    assert b'Redefinir pelo perfil' in resp.data    # botao redefinir (usuario tem perfil)


def test_aplicar_perfil_via_post(client, db):
    _login(client, _novo_usuario(db))
    p = perfil_service.criar_perfil('Perfil Post')
    perfil_service.salvar_skeleton(p.id, {'vendas': {'ver': True, 'criar': True}})
    alvo = _novo_usuario(db, perfil='financeiro', sistema_lojas=True)

    resp = client.post(
        f'/hora/permissoes/{alvo.id}/perfil',
        data={'perfil_hora_slug': p.slug},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert alvo.perfil == p.slug


def test_auth_listar_usuarios_render_com_perfil_hora(client, db):
    admin = _novo_usuario(db)
    _login(client, admin)
    p = perfil_service.criar_perfil('Perfil Auth')
    alvo = _novo_usuario(db, perfil='financeiro', sistema_lojas=True)
    perfil_service.aplicar_perfil_em_usuario(alvo.id, p.slug)

    resp = client.get('/auth/usuarios')
    assert resp.status_code == 200
    # nome amigavel do perfil HORA aparece (nao o slug cru)
    assert b'Perfil Auth' in resp.data
