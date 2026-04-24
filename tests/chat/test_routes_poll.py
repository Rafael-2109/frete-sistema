"""
Tests do endpoint /api/chat/poll — substitui SSE /stream no chat_client.js
(ver fix/chat-audit-p0 — elimina slot sustentado de worker gunicorn).
"""
import uuid

import pytest

from app.chat.services.message_service import MessageService
from app.chat.services.thread_service import ThreadService


_RUN = uuid.uuid4().hex[:8]


@pytest.fixture
def client(app):
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['WTF_CSRF_CHECK_DEFAULT'] = False
    return app.test_client()


def _login(client, user):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


def test_poll_vazio_primeiro_acesso(client, user_factory, db_session):
    u = user_factory(email=f'pv_{_RUN}@t.local')
    _login(client, u)
    resp = client.get('/api/chat/poll')
    assert resp.status_code == 200
    data = resp.json
    assert data['new'] == []
    assert data['edited'] == []
    assert data['deleted'] == []
    assert data['unread'] == {'system': 0, 'user': 0}
    assert 'server_ts' in data
    assert data['last_id'] == 0


def test_poll_retorna_novas_mensagens(client, user_factory, db_session):
    a = user_factory(email=f'pn_a_{_RUN}@t.local')
    b = user_factory(email=f'pn_b_{_RUN}@t.local')
    dm = ThreadService.get_or_create_dm(a, b)
    msg = MessageService.send(sender=a, thread_id=dm.id, content='ola bob')

    _login(client, b)
    resp = client.get('/api/chat/poll?since_id=0')
    assert resp.status_code == 200
    data = resp.json
    ids = [m['message_id'] for m in data['new']]
    assert msg.id in ids
    # unread deve contar a msg de A (que nao e do proprio B)
    assert data['unread']['user'] >= 1


def test_poll_incremental_nao_repete(client, user_factory, db_session):
    a = user_factory(email=f'pi_a_{_RUN}@t.local')
    b = user_factory(email=f'pi_b_{_RUN}@t.local')
    dm = ThreadService.get_or_create_dm(a, b)
    m1 = MessageService.send(sender=a, thread_id=dm.id, content='primeira')

    _login(client, b)
    r1 = client.get(f'/api/chat/poll?since_id=0')
    assert any(m['message_id'] == m1.id for m in r1.json['new'])
    last_id = r1.json['last_id']
    server_ts = r1.json['server_ts']

    # Segundo poll com since_id atualizado — nao deve re-entregar m1
    r2 = client.get(f'/api/chat/poll?since_id={last_id}&since_ts={server_ts}')
    assert m1.id not in [m['message_id'] for m in r2.json['new']]

    # Nova mensagem apos poll anterior deve aparecer
    m2 = MessageService.send(sender=a, thread_id=dm.id, content='segunda')
    r3 = client.get(f'/api/chat/poll?since_id={last_id}&since_ts={server_ts}')
    assert any(m['message_id'] == m2.id for m in r3.json['new'])


def test_poll_detecta_edit(client, user_factory, db_session):
    a = user_factory(email=f'pe_a_{_RUN}@t.local')
    b = user_factory(email=f'pe_b_{_RUN}@t.local')
    dm = ThreadService.get_or_create_dm(a, b)
    m1 = MessageService.send(sender=a, thread_id=dm.id, content='versao 1')

    _login(client, b)
    r1 = client.get('/api/chat/poll?since_id=0')
    last_id = r1.json['last_id']
    server_ts = r1.json['server_ts']

    MessageService.edit(a, m1.id, 'versao 2')

    r2 = client.get(f'/api/chat/poll?since_id={last_id}&since_ts={server_ts}')
    edited_ids = [m['message_id'] for m in r2.json['edited']]
    assert m1.id in edited_ids
    edited = next(m for m in r2.json['edited'] if m['message_id'] == m1.id)
    assert edited['new_content'] == 'versao 2'


def test_poll_detecta_delete_sem_vazar_content(client, user_factory, db_session):
    a = user_factory(email=f'pd_a_{_RUN}@t.local')
    b = user_factory(email=f'pd_b_{_RUN}@t.local')
    dm = ThreadService.get_or_create_dm(a, b)
    m1 = MessageService.send(sender=a, thread_id=dm.id, content='SECRETO')

    _login(client, b)
    r1 = client.get('/api/chat/poll?since_id=0')
    last_id = r1.json['last_id']
    server_ts = r1.json['server_ts']

    MessageService.delete(a, m1.id)

    r2 = client.get(f'/api/chat/poll?since_id={last_id}&since_ts={server_ts}')
    deleted_ids = [m['message_id'] for m in r2.json['deleted']]
    assert m1.id in deleted_ids
    # Payload de deleted NAO deve conter content
    deleted_entry = next(m for m in r2.json['deleted'] if m['message_id'] == m1.id)
    assert 'content' not in deleted_entry
    assert 'new_content' not in deleted_entry
    assert 'preview' not in deleted_entry


def test_poll_nao_vaza_msg_deletada_como_new(client, user_factory, db_session):
    """Mensagem deletada ANTES do primeiro poll nao pode aparecer em `new`."""
    a = user_factory(email=f'pnd_a_{_RUN}@t.local')
    b = user_factory(email=f'pnd_b_{_RUN}@t.local')
    dm = ThreadService.get_or_create_dm(a, b)
    m1 = MessageService.send(sender=a, thread_id=dm.id, content='SECRETO')
    MessageService.delete(a, m1.id)

    _login(client, b)
    resp = client.get('/api/chat/poll?since_id=0')
    ids = [m['message_id'] for m in resp.json['new']]
    assert m1.id not in ids


def test_poll_nao_vaza_thread_de_outro(client, user_factory, db_session):
    """B nao deve receber msgs de threads das quais nao e membro."""
    a = user_factory(email=f'pt_a_{_RUN}@t.local')
    other = user_factory(email=f'pt_o_{_RUN}@t.local')
    b = user_factory(email=f'pt_b_{_RUN}@t.local')

    # DM A↔Other; B nao e membro
    dm = ThreadService.get_or_create_dm(a, other)
    m1 = MessageService.send(sender=a, thread_id=dm.id, content='privado')

    _login(client, b)
    resp = client.get('/api/chat/poll?since_id=0')
    ids = [m['message_id'] for m in resp.json['new']]
    assert m1.id not in ids


def test_poll_requer_autenticacao(client):
    """Sem sessao autenticada, Flask-Login redireciona (302) ou retorna 401."""
    resp = client.get('/api/chat/poll')
    assert resp.status_code in (302, 401)


def test_poll_since_ts_invalido_nao_quebra(client, user_factory, db_session):
    """since_ts malformado nao deve retornar 500 — apenas ignorado."""
    u = user_factory(email=f'pti_{_RUN}@t.local')
    _login(client, u)
    resp = client.get('/api/chat/poll?since_ts=NOT_A_DATE')
    assert resp.status_code == 200
