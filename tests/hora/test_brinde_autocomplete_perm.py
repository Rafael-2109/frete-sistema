"""CAUSA-RAIZ do 'brinde some na criacao': o autocomplete de peca exigia APENAS
`pecas_estoque/ver`. Vendedor que so tem `vendas/*` recebia 302 -> a lista de
pecas nao abria -> ele nao selecionava a peca -> hidden brinde_peca_id ficava
vazio -> a rota descartava a linha em silencio -> brinde nao era gravado.

Correcao: o catalogo (read-only) tambem libera para quem cria/edita pedido de
venda (vendas/criar | vendas/editar), pois brinde e parte do pedido de venda.
"""
import uuid

from app.auth.models import Usuario
from app.hora.services import permissao_service


def _vendedor_sem_pecas(db):
    """Tem vendas/criar+editar, mas NAO pecas_estoque/ver (perfil real do vendedor)."""
    u = Usuario(nome='Vendedor Sem Pecas', email=f'{uuid.uuid4().hex[:10]}@t.local',
                senha_hash='x', perfil='vendedor', status='ativo', sistema_lojas=True)
    db.session.add(u)
    db.session.flush()
    permissao_service.salvar_matriz_completa(u.id, {
        'vendas': {'ver': True, 'criar': True, 'editar': True},
    })
    return u


def _sem_perms_hora(db):
    """Nem vendas/* nem pecas_estoque/ver."""
    u = Usuario(nome='Sem Perms', email=f'{uuid.uuid4().hex[:10]}@t.local',
                senha_hash='x', perfil='vendedor', status='ativo', sistema_lojas=True)
    db.session.add(u)
    db.session.flush()
    permissao_service.salvar_matriz_completa(u.id, {'dashboard': {'ver': True}})
    return u


def _login(client, u):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(u.id)
        sess['_fresh'] = True


def test_vendedor_que_cria_pedido_acessa_autocomplete_peca(client, db, peca_factory):
    """Quem tem vendas/criar busca pecas p/ brinde, mesmo sem pecas_estoque/ver."""
    peca_factory(descricao='CAPACETE TESTE')
    _login(client, _vendedor_sem_pecas(db))
    resp = client.get('/hora/autocomplete/peca?q=CAP', follow_redirects=False)
    assert resp.status_code == 200
    assert any('CAPACETE TESTE' in (i.get('descricao') or '') for i in resp.get_json())


def test_usuario_sem_vendas_nem_pecas_segue_bloqueado(client, db, peca_factory):
    """Sem vendas/* e sem pecas_estoque/ver -> bloqueado (302 acesso negado)."""
    peca_factory(descricao='CAPACETE TESTE')
    _login(client, _sem_perms_hora(db))
    resp = client.get('/hora/autocomplete/peca?q=CAP', follow_redirects=False)
    assert resp.status_code != 200
