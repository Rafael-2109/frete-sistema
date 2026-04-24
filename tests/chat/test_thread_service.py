"""
Tests para ThreadService — Task 6 chat in-app.

Requer DB local PostgreSQL com tabelas chat_* criadas (migration Task 3).
Cada teste usa emails unicos para evitar colisoes entre runs.
"""
import pytest

from app.chat.services.thread_service import ThreadService
from app.chat.models import ChatMember


def test_get_or_create_dm_cria_se_nao_existe(db_session, user_factory):
    a = user_factory(email='tsa1@t.local')
    b = user_factory(email='tsb1@t.local')

    thread = ThreadService.get_or_create_dm(a, b)
    assert thread.id is not None
    assert thread.tipo == 'dm'
    members = ChatMember.query.filter_by(thread_id=thread.id).all()
    assert {m.user_id for m in members} == {a.id, b.id}


def test_get_or_create_dm_retorna_existente(db_session, user_factory):
    a = user_factory(email='tsa2@t.local')
    b = user_factory(email='tsb2@t.local')
    t1 = ThreadService.get_or_create_dm(a, b)
    t2 = ThreadService.get_or_create_dm(b, a)
    assert t1.id == t2.id


def test_get_or_create_system_dm(db_session, user_factory):
    u = user_factory(email='tssys@t.local')
    t = ThreadService.get_or_create_system_dm(u)
    assert t.tipo == 'system_dm'
    assert t.criado_por_id == u.id


def test_lazy_entity_thread_not_exists_returns_none(db_session):
    result = ThreadService.get_entity_thread('pedido', 'VCD999')
    assert result is None


def test_create_entity_thread(db_session, user_factory):
    owner = user_factory(email='tsow@t.local')
    t = ThreadService.create_entity_thread('pedido', 'VCD001', creator=owner)
    assert t.entity_type == 'pedido'
    assert t.entity_id == 'VCD001'
    members = ChatMember.query.filter_by(thread_id=t.id).all()
    assert len(members) == 1
    assert members[0].user_id == owner.id
    assert members[0].role == 'owner'


def test_permission_required_to_create_dm(db_session, user_factory):
    a = user_factory(email='tslow@t.local')             # NACOM only
    b = user_factory(email='tshigh@t.local', carvia=True)  # NACOM+CARVIA
    with pytest.raises(PermissionError):
        ThreadService.get_or_create_dm(a, b)  # a NAO e superset de b
