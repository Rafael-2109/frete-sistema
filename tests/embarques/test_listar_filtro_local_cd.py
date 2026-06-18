"""Frente B — filtro por local_cd na listagem de embarques (acessos VM/TM do sidebar).

`GET /embarques/listar_embarques?local_cd=TENENTE_MARQUES` deve listar APENAS embarques
que tenham >=1 EmbarqueItem ativo daquele CD. A tela segue exibindo TODOS os itens de
cada embarque (o filtro decide QUAIS embarques aparecem, nao quais itens).

Inspeciona a LISTA selecionada pela rota via o signal `template_rendered` (robusto a
paginacao/HTML). Os embarques de teste recebem `numero` no topo (MAX+seq) para caírem
na 1a pagina (ordenacao numero desc, per_page=100).
"""
import uuid
from contextlib import contextmanager
from unittest.mock import patch, MagicMock

from flask import template_rendered
from sqlalchemy import text

from app.utils.local_cd import LOCAL_CD_VICTORIO_MARCHEZINE, LOCAL_CD_TENENTE_MARQUES


def _user():
    u = MagicMock()
    u.is_authenticated = True
    u.pode_acessar_embarques = lambda: True
    u.perfil = 'logistica'
    u.perfil_nome = 'Logistica'
    return u


@contextmanager
def _capturar_contexto(app):
    capturado = {}

    def _record(sender, template, context, **extra):
        capturado['template'] = template.name
        capturado['context'] = context

    template_rendered.connect(_record, app)
    try:
        yield capturado
    finally:
        template_rendered.disconnect(_record, app)


def _novo_embarque(db):
    """Embarque ativo COM numero no topo (MAX+1) -> 1a pagina da listagem desc."""
    numero = (db.session.execute(
        text("SELECT COALESCE(MAX(numero), 0) FROM embarques")).scalar() or 0) + 1
    eid = db.session.execute(text("""
        INSERT INTO embarques (numero, status, criado_em, criado_por, tipo_carga, tipo_cotacao)
        VALUES (:n, 'ativo', NOW(), 'test', 'FRACIONADA', 'FRACIONADA') RETURNING id
    """), {'n': numero}).scalar()
    return eid, numero


def _item(db, eid, local_cd, suf):
    db.session.execute(text("""
        INSERT INTO embarque_itens
            (embarque_id, separacao_lote_id, local_cd, cliente, pedido, uf_destino, cidade_destino, status)
        VALUES (:eid, :lote, :local, 'Cliente Teste', :ped, 'SP', 'Sao Paulo', 'ativo')
    """), {'eid': eid, 'lote': f'LOTE-{suf}', 'local': local_cd, 'ped': f'PED-{suf}'})


def _ids_da_listagem(client, app, query_string):
    with _capturar_contexto(app) as cap:
        with patch('flask_login.utils._get_user', return_value=_user()):
            resp = client.get(query_string)
        assert resp.status_code == 200, resp.status_code
        return {e.id for e in cap['context']['embarques']}


def test_filtro_tm_lista_so_embarques_com_item_tm(db, client, app):
    suf = uuid.uuid4().hex[:8]
    eid_misto, _ = _novo_embarque(db)              # VM + TM -> aparece em TM
    _item(db, eid_misto, LOCAL_CD_VICTORIO_MARCHEZINE, f'{suf}vm')
    _item(db, eid_misto, LOCAL_CD_TENENTE_MARQUES, f'{suf}tm')
    eid_vm, _ = _novo_embarque(db)                 # so VM -> NAO aparece em TM
    _item(db, eid_vm, LOCAL_CD_VICTORIO_MARCHEZINE, f'{suf}sovm')
    db.session.commit()

    ids = _ids_da_listagem(
        client, app, '/embarques/listar_embarques?local_cd=TENENTE_MARQUES&mostrar_todos=true')
    assert eid_misto in ids, 'embarque com item TM deveria aparecer'
    assert eid_vm not in ids, 'embarque so-VM NAO deveria aparecer no filtro TM'


def test_filtro_vm_inclui_misto_e_exclui_so_tm(db, client, app):
    suf = uuid.uuid4().hex[:8]
    eid_misto, _ = _novo_embarque(db)
    _item(db, eid_misto, LOCAL_CD_VICTORIO_MARCHEZINE, f'{suf}vm')
    _item(db, eid_misto, LOCAL_CD_TENENTE_MARQUES, f'{suf}tm')
    eid_so_tm, _ = _novo_embarque(db)
    _item(db, eid_so_tm, LOCAL_CD_TENENTE_MARQUES, f'{suf}sotm')
    db.session.commit()

    ids = _ids_da_listagem(
        client, app, '/embarques/listar_embarques?local_cd=VICTORIO_MARCHEZINE&mostrar_todos=true')
    assert eid_misto in ids
    assert eid_so_tm not in ids


def test_sem_filtro_lista_ambos(db, client, app):
    """Sentinela: sem local_cd, os dois embarques aparecem (filtro nao vaza)."""
    suf = uuid.uuid4().hex[:8]
    eid_tm, _ = _novo_embarque(db)
    _item(db, eid_tm, LOCAL_CD_TENENTE_MARQUES, f'{suf}tm')
    eid_vm, _ = _novo_embarque(db)
    _item(db, eid_vm, LOCAL_CD_VICTORIO_MARCHEZINE, f'{suf}vm')
    db.session.commit()

    ids = _ids_da_listagem(client, app, '/embarques/listar_embarques?mostrar_todos=true')
    assert eid_tm in ids and eid_vm in ids
