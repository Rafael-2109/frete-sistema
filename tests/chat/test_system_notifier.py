"""
Testes para SystemNotifier — Task 9 do plano chat-inapp.
"""
import uuid
from unittest.mock import patch

from app.chat.services.system_notifier import SystemNotifier
from app.chat.models import ChatMessage, ChatThread

_RUN = uuid.uuid4().hex[:8]


@patch('app.chat.realtime.publisher.publish')
def test_alert_cria_thread_system_e_mensagem(mock_pub, db_session, user_factory):
    u = user_factory(email=f'sn_u_{_RUN}@t.local')
    SystemNotifier.alert(
        user_ids=[u.id],
        source='recebimento',
        titulo='Teste',
        content='corpo',
        deep_link='/recebimento/1',
        nivel='ATENCAO',
        dados={'id': 1},
    )
    t = ChatThread.query.filter_by(tipo='system_dm', criado_por_id=u.id).first()
    assert t is not None
    msg = ChatMessage.query.filter_by(thread_id=t.id).order_by(ChatMessage.id.desc()).first()
    assert msg.sender_type == 'system'
    assert msg.sender_system_source == 'recebimento'
    assert msg.nivel == 'ATENCAO'
    assert msg.deep_link == '/recebimento/1'
    assert msg.dados == {'id': 1}
    assert mock_pub.call_count == 1


@patch('app.chat.realtime.publisher.publish')
def test_alert_multi_user(mock_pub, db_session, user_factory):
    a = user_factory(email=f'ma_{_RUN}@t.local')
    b = user_factory(email=f'mb_{_RUN}@t.local')
    SystemNotifier.alert(
        user_ids=[a.id, b.id], source='dfe', titulo='X', content='Y',
        deep_link='/x', nivel='CRITICO',
    )
    assert mock_pub.call_count == 2
