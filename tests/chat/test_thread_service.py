"""
Tests para ThreadService — Task 6 chat in-app.

Requer DB local PostgreSQL com tabelas chat_* criadas (migration Task 3).
Cada teste usa emails unicos por run (prefixo _RUN) para evitar colisoes
entre runs — services commitam e fixture db_session nao isola (bug #5 CLAUDE.md).
"""
import uuid

import pytest

from app.chat.services.thread_service import ThreadService
from app.chat.models import ChatMember


_RUN = uuid.uuid4().hex[:8]


def test_get_or_create_dm_cria_se_nao_existe(db_session, user_factory):
    a = user_factory(email=f'tsa1_{_RUN}@t.local')
    b = user_factory(email=f'tsb1_{_RUN}@t.local')

    thread = ThreadService.get_or_create_dm(a, b)
    assert thread.id is not None
    assert thread.tipo == 'dm'
    members = ChatMember.query.filter_by(thread_id=thread.id).all()
    assert {m.user_id for m in members} == {a.id, b.id}


def test_get_or_create_dm_retorna_existente(db_session, user_factory):
    a = user_factory(email=f'tsa2_{_RUN}@t.local')
    b = user_factory(email=f'tsb2_{_RUN}@t.local')
    t1 = ThreadService.get_or_create_dm(a, b)
    t2 = ThreadService.get_or_create_dm(b, a)
    assert t1.id == t2.id


def test_get_or_create_system_dm(db_session, user_factory):
    u = user_factory(email=f'tssys_{_RUN}@t.local')
    t = ThreadService.get_or_create_system_dm(u)
    assert t.tipo == 'system_dm'
    assert t.criado_por_id == u.id


def test_lazy_entity_thread_not_exists_returns_none(db_session):
    # entity_id unique por run — get_entity_thread nao cria, mas evita race com
    # outro teste que cria a mesma entity_id em paralelo.
    result = ThreadService.get_entity_thread('pedido', f'VCD999_{_RUN}')
    assert result is None


def test_create_entity_thread(db_session, user_factory):
    owner = user_factory(email=f'tsow_{_RUN}@t.local')
    t = ThreadService.create_entity_thread('pedido', f'VCD001_{_RUN}', creator=owner)
    assert t.entity_type == 'pedido'
    assert t.entity_id == f'VCD001_{_RUN}'
    members = ChatMember.query.filter_by(thread_id=t.id).all()
    assert len(members) == 1
    assert members[0].user_id == owner.id
    assert members[0].role == 'owner'


def test_permission_required_to_create_dm(db_session, user_factory):
    a = user_factory(email=f'tslow_{_RUN}@t.local')              # NACOM only
    b = user_factory(email=f'tshigh_{_RUN}@t.local', carvia=True)  # NACOM+CARVIA
    with pytest.raises(PermissionError):
        ThreadService.get_or_create_dm(a, b)  # a NAO e superset de b
