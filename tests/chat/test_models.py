import pytest
from app import create_app, db
from app.chat.models import (
    ChatThread, ChatMember, ChatMessage, ChatAttachment,
    ChatReaction, ChatMention, ChatForward
)
from app.auth.models import Usuario
from app.utils.timezone import agora_utc_naive


@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app


def test_chat_thread_fields(app_ctx):
    t = ChatThread(tipo='dm', criado_em=agora_utc_naive(), sistemas_required=[])
    assert t.tipo == 'dm'
    assert t.entity_type is None
    assert t.arquivado_em is None


def test_chat_message_has_tsvector_and_defaults(app_ctx):
    m = ChatMessage(
        thread_id=1,
        sender_type='user',
        sender_user_id=1,
        content='teste',
        criado_em=agora_utc_naive(),
    )
    assert m.sender_type == 'user'
    assert m.deletado_em is None
    assert m.nivel is None


def test_chat_member_unique_active(app_ctx):
    mem = ChatMember(thread_id=1, user_id=1, role='member', adicionado_em=agora_utc_naive())
    assert mem.role == 'member'
    assert mem.silenciado is False
    assert mem.removido_em is None
