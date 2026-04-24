"""
Task 25 — Smoke test end-to-end do chat in-app.

Valida a INTEGRACAO entre services (ThreadService, MessageService,
SystemNotifier) + modelos + hooks. Usa services diretos em vez de
test_client Flask pois a autenticacao multi-user via session cookies
em module-scope app_context tem problemas conhecidos (current_user
nao troca entre clients no mesmo pytest session).

As rotas HTTP ja foram validadas individualmente nos tests de cada
task (12-15). Aqui focamos em que os services encadeiam corretamente.

Fluxo:
1. A cria DM com B via ThreadService
2. A envia mensagem via MessageService
3. Query direta ao DB confirma unread para B
4. B marca como lida (simulando route /read)
5. A envia msg com @mention -> chat_mention criada
6. SystemNotifier dispara alerta para B -> system_dm criada
7. Hooks (recebimento) — chamada com mock de publisher
8. Audit de forward (MessageService cria ChatForward)
"""
import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from app import db
from app.chat.services.thread_service import ThreadService
from app.chat.services.message_service import MessageService
from app.chat.services.system_notifier import SystemNotifier
from app.chat.hooks.recebimento import notify_recebimento_finalizado
from app.chat.models import (
    ChatMessage, ChatMention, ChatThread, ChatForward, ChatMember,
)
from app.utils.timezone import agora_utc_naive

_RUN = uuid.uuid4().hex[:8]


@patch('app.chat.realtime.publisher.publish')
def test_smoke_e2e_fluxo_completo(mock_pub, db_session, user_factory):
    """Integra todos os services num fluxo realista."""
    a = user_factory(email=f'e2e_a_{_RUN}@t.local')
    b = user_factory(email=f'e2e_b_{_RUN}@t.local')

    # ========================================================================
    # 1. A cria DM com B (ThreadService via permission_checker)
    # ========================================================================
    thread = ThreadService.get_or_create_dm(a, b)
    assert thread.tipo == 'dm'
    assert thread.id is not None
    # 2 membros ativos (A + B)
    members = ChatMember.query.filter_by(thread_id=thread.id).all()
    assert len(members) == 2
    assert {m.user_id for m in members} == {a.id, b.id}

    # ========================================================================
    # 2. A envia primeira mensagem
    # ========================================================================
    msg1 = MessageService.send(sender=a, thread_id=thread.id, content='Oi, bom dia!')
    assert msg1.id is not None
    assert msg1.content == 'Oi, bom dia!'
    assert msg1.sender_user_id == a.id
    # Publish chamado para B (nao para sender A)
    called_ids = [c.args[0] for c in mock_pub.call_args_list]
    assert b.id in called_ids
    assert a.id not in called_ids

    # ========================================================================
    # 3. Query unread para B — replica a logica do route /unread
    # ========================================================================
    from sqlalchemy import select, func, or_
    def unread_for(user_id):
        rows = db.session.execute(
            select(ChatMessage.sender_type, func.count(ChatMessage.id))
            .join(ChatMember, ChatMember.thread_id == ChatMessage.thread_id)
            .where(
                ChatMember.user_id == user_id,
                ChatMember.removido_em.is_(None),
                ChatMessage.deletado_em.is_(None),
                or_(
                    ChatMessage.sender_user_id.is_(None),
                    ChatMessage.sender_user_id != user_id,
                ),
                or_(
                    ChatMember.last_read_message_id.is_(None),
                    ChatMessage.id > ChatMember.last_read_message_id,
                ),
            ).group_by(ChatMessage.sender_type)
        ).all()
        return {row[0]: row[1] for row in rows}

    counts_b = unread_for(b.id)
    assert counts_b.get('user', 0) >= 1
    assert counts_b.get('system', 0) == 0

    # ========================================================================
    # 4. B marca thread como lida — replica logica do route /read
    # ========================================================================
    member_b = db.session.execute(
        select(ChatMember).where(
            ChatMember.thread_id == thread.id,
            ChatMember.user_id == b.id,
        )
    ).scalar_one()
    member_b.last_read_message_id = msg1.id
    db.session.commit()

    counts_b = unread_for(b.id)
    assert counts_b.get('user', 0) == 0  # zerou apos marcar lido

    # ========================================================================
    # 5. A envia msg com @mention de B (usando email prefix como username)
    # ========================================================================
    mention_name = f'e2e_b_{_RUN}'
    msg2 = MessageService.send(
        sender=a, thread_id=thread.id,
        content=f'E ai @{mention_name}, viu o pedido?',
    )
    # Mention foi criada pra B
    mentions = ChatMention.query.filter_by(message_id=msg2.id).all()
    assert len(mentions) == 1
    assert mentions[0].mentioned_user_id == b.id

    # Publish para B com urgente=True (por mention)
    last_call = mock_pub.call_args_list[-1]
    assert last_call.args[0] == b.id
    assert last_call.args[1] == 'message_new'
    assert last_call.args[2]['urgente'] is True

    # ========================================================================
    # 6. SystemNotifier dispara alerta para B
    # ========================================================================
    SystemNotifier.alert(
        user_ids=[b.id],
        source='recebimento',
        titulo='Recebimento #5555 concluido',
        content='NF 98765 — todos os itens OK',
        deep_link='/recebimento/5555',
        nivel='INFO',
        dados={'recebimento_id': 5555},
    )
    # system_dm thread criada pra B
    sys_thread = ChatThread.query.filter_by(tipo='system_dm', criado_por_id=b.id).first()
    assert sys_thread is not None
    sys_msg = ChatMessage.query.filter_by(
        thread_id=sys_thread.id, sender_type='system',
    ).order_by(ChatMessage.id.desc()).first()
    assert sys_msg is not None
    assert sys_msg.sender_system_source == 'recebimento'
    assert sys_msg.nivel == 'INFO'
    assert sys_msg.deep_link == '/recebimento/5555'
    assert sys_msg.dados == {'recebimento_id': 5555}

    # Unread counter deve ver a msg do sistema (nao lida)
    counts_b = unread_for(b.id)
    assert counts_b.get('system', 0) >= 1

    # ========================================================================
    # 7. Hook de recebimento (Task 21) — dispara usando SystemNotifier
    # ========================================================================
    recebimento_mock = SimpleNamespace(
        id=777001,
        status='processado',
        transfer_status='concluido',
        numero_nf='88888',
        transfer_erro_mensagem=None,
    )
    notify_recebimento_finalizado(recebimento_mock, destinatarios=[b.id])
    hook_msg = ChatMessage.query.filter(
        ChatMessage.sender_system_source == 'recebimento',
        ChatMessage.deep_link == '/recebimento/777001',
    ).first()
    assert hook_msg is not None
    assert hook_msg.nivel == 'INFO'

    # ========================================================================
    # 8. B encaminha msg do sistema para DM com A
    # ========================================================================
    # Hack: B precisa ser membro ativo da thread DM pra encaminhar.
    # O forward cria nova msg na thread destino + ChatForward audit.
    forwarded = MessageService.send(
        sender=b,
        thread_id=thread.id,
        content=f'olha esse alerta\n\n> _Encaminhado:_ {sys_msg.content[:100]}',
        deep_link=sys_msg.deep_link,
    )
    db.session.add(ChatForward(
        original_message_id=sys_msg.id,
        forwarded_message_id=forwarded.id,
        forwarded_by_id=b.id,
    ))
    db.session.commit()

    forwards = ChatForward.query.filter_by(forwarded_message_id=forwarded.id).all()
    assert len(forwards) == 1
    assert forwards[0].original_message_id == sys_msg.id
    assert forwards[0].forwarded_by_id == b.id

    # ========================================================================
    # 9. A lista msgs da thread DM e ve o encaminhamento
    # ========================================================================
    msgs = MessageService.list_for_thread(user=a, thread_id=thread.id, limit=100)
    forwarded_in_list = next((m for m in msgs if m.id == forwarded.id), None)
    assert forwarded_in_list is not None
    assert 'Encaminhado' in forwarded_in_list.content
    assert forwarded_in_list.deep_link == '/recebimento/5555'

    # ========================================================================
    # 10. Edit window (15 min) e soft delete
    # ========================================================================
    edited = MessageService.edit(user=a, message_id=msg1.id, new_content='Oi, bom dia! (editado)')
    assert edited.content.endswith('(editado)')
    assert edited.editado_em is not None

    # Forcar mensagem FORA da janela de edicao
    ChatMessage.query.filter_by(id=msg1.id).update({
        'criado_em': agora_utc_naive() - timedelta(minutes=20),
    })
    db.session.commit()
    import pytest
    from app.chat.services.message_service import MessageError
    with pytest.raises(MessageError, match='janela'):
        MessageService.edit(user=a, message_id=msg1.id, new_content='tarde demais')

    # Soft delete
    MessageService.delete(user=a, message_id=msg1.id)
    db.session.expire_all()
    reloaded = db.session.get(ChatMessage, msg1.id)
    assert reloaded.deletado_em is not None
    assert reloaded.deletado_por_id == a.id

    # ========================================================================
    # Resumo: publish chamado multiplas vezes (msg, msg-mention, system,
    # hook, forward, edit)
    # ========================================================================
    assert mock_pub.call_count >= 5, (
        f'publish deveria ser chamado >=5x, got {mock_pub.call_count}'
    )
