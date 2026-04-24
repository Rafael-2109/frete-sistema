"""
Regression tests para findings da auditoria P0 (fix/chat-audit-p0).

Cada teste referencia o ID do finding (C2, C3, C4, C7, A6, A7).
Services commitam — emails unicos por run.
"""
import uuid

import pytest

from app import db
from app.chat.models import ChatMember, ChatThread
from app.chat.services.message_service import MessageService, MessageError
from app.chat.services.thread_service import ThreadService
from app.chat.utils import url_safe
from app.chat.realtime.sse import _catchup_events


_RUN = uuid.uuid4().hex[:8]


# ============================================================================
# C2 — IDOR em add_member (CRITICO)
# ============================================================================

class TestC2AddMemberIDOR:
    """
    Antes do fix: qualquer user podia se auto-adicionar em qualquer thread
    fazendo POST /threads/<id>/members {user_id: self.id}.
    `pode_adicionar(self, self)` retorna True por subset-de-si-mesmo.
    """

    def test_dm_nao_aceita_novos_membros(self, db_session, user_factory):
        alice = user_factory(email=f'c2_alice_{_RUN}@t.local')
        bob = user_factory(email=f'c2_bob_{_RUN}@t.local')
        charlie = user_factory(email=f'c2_char_{_RUN}@t.local')

        dm = ThreadService.get_or_create_dm(alice, bob)
        # Charlie tenta se auto-adicionar na DM Alice↔Bob
        with pytest.raises(PermissionError, match='nao aceita novos membros'):
            ThreadService.add_member(dm, charlie, charlie)

    def test_system_dm_nao_aceita_novos_membros(self, db_session, user_factory):
        alice = user_factory(email=f'c2_sd_alice_{_RUN}@t.local')
        bob = user_factory(email=f'c2_sd_bob_{_RUN}@t.local')

        sd = ThreadService.get_or_create_system_dm(alice)
        with pytest.raises(PermissionError, match='nao aceita novos membros'):
            ThreadService.add_member(sd, bob, bob)

    def test_group_actor_precisa_ser_owner(self, db_session, user_factory):
        owner = user_factory(email=f'c2_ow_{_RUN}@t.local')
        charlie = user_factory(email=f'c2_ch_{_RUN}@t.local')

        # Cria grupo com owner
        thread = ChatThread(tipo='group', titulo='T', criado_por_id=owner.id, sistemas_required=[])
        db.session.add(thread)
        db.session.flush()
        db.session.add(ChatMember(
            thread_id=thread.id, user_id=owner.id, role='owner',
            adicionado_por_id=owner.id,
        ))
        db.session.commit()

        # Charlie NAO e membro; tenta se auto-adicionar
        with pytest.raises(PermissionError, match='nao e membro'):
            ThreadService.add_member(thread, charlie, charlie)

    def test_group_membro_comum_nao_adiciona(self, db_session, user_factory):
        owner = user_factory(email=f'c2_go_{_RUN}@t.local')
        member = user_factory(email=f'c2_gm_{_RUN}@t.local')
        outsider = user_factory(email=f'c2_go2_{_RUN}@t.local')

        thread = ChatThread(tipo='group', titulo='T2', criado_por_id=owner.id, sistemas_required=[])
        db.session.add(thread)
        db.session.flush()
        db.session.add(ChatMember(
            thread_id=thread.id, user_id=owner.id, role='owner',
            adicionado_por_id=owner.id,
        ))
        db.session.add(ChatMember(
            thread_id=thread.id, user_id=member.id, role='member',
            adicionado_por_id=owner.id,
        ))
        db.session.commit()

        # member (role='member') tenta adicionar outsider — nao deve poder
        with pytest.raises(PermissionError, match='precisa ser owner'):
            ThreadService.add_member(thread, member, outsider)

    def test_group_owner_adiciona_ok(self, db_session, user_factory):
        owner = user_factory(email=f'c2_oo_{_RUN}@t.local')
        outsider = user_factory(email=f'c2_out_{_RUN}@t.local')

        thread = ChatThread(tipo='group', titulo='T3', criado_por_id=owner.id, sistemas_required=[])
        db.session.add(thread)
        db.session.flush()
        db.session.add(ChatMember(
            thread_id=thread.id, user_id=owner.id, role='owner',
            adicionado_por_id=owner.id,
        ))
        db.session.commit()

        mem = ThreadService.add_member(thread, owner, outsider)
        assert mem.user_id == outsider.id

    def test_admin_global_bypassa(self, db_session, user_factory):
        owner = user_factory(email=f'c2_ag_ow_{_RUN}@t.local')
        admin = user_factory(email=f'c2_ag_ad_{_RUN}@t.local', perfil='administrador')
        target = user_factory(email=f'c2_ag_tg_{_RUN}@t.local')

        thread = ChatThread(tipo='group', titulo='T4', criado_por_id=owner.id, sistemas_required=[])
        db.session.add(thread)
        db.session.flush()
        db.session.add(ChatMember(
            thread_id=thread.id, user_id=owner.id, role='owner',
            adicionado_por_id=owner.id,
        ))
        db.session.commit()

        # Admin NAO e membro mas pode adicionar (bypass)
        mem = ThreadService.add_member(thread, admin, target)
        assert mem.user_id == target.id


# ============================================================================
# C3 — SSE catchup vaza preview de mensagens soft-deletadas (ALTO)
# ============================================================================

class TestC3CatchupDeletedFilter:
    """
    Antes do fix: _catchup_events fazia SELECT sem filter deletado_em,
    vazando preview via Last-Event-ID para clientes que reconectavam
    apos delete. REST API filtra via _message_dict mas SSE nao.
    """

    def test_catchup_nao_inclui_deletadas(self, db_session, user_factory):
        a = user_factory(email=f'c3_a_{_RUN}@t.local')
        b = user_factory(email=f'c3_b_{_RUN}@t.local')
        dm = ThreadService.get_or_create_dm(a, b)

        # A envia 2 mensagens
        m1 = MessageService.send(sender=a, thread_id=dm.id, content='primeira')
        m2 = MessageService.send(sender=a, thread_id=dm.id, content='SECRETA')
        # Delete da SECRETA
        MessageService.delete(a, m2.id)

        # B reconecta com Last-Event-ID anterior ao m1 — deveria receber m1
        # mas NAO m2 (deletada).
        events = list(_catchup_events(b.id, m1.id - 1))
        bodies = ''.join(events)
        assert 'primeira' in bodies
        assert 'SECRETA' not in bodies
        # Confirma que m2.id nao aparece em nenhum event id
        assert f'id: {m2.id}\n' not in bodies


# ============================================================================
# C4 — deep_link sem validacao em POST /messages (MEDIO → valido via server)
# ============================================================================

class TestC4DeepLinkValidation:
    """
    Antes do fix: MessageService.send aceitava deep_link arbitrario
    (javascript:, //evil.com, /\t/evil.com). Validacao so existia em
    share_routes._url_safe — enviar direto por /messages escapava.
    """

    def test_url_safe_rejeita_javascript(self):
        assert not url_safe('javascript:alert(1)')

    def test_url_safe_rejeita_data(self):
        assert not url_safe('data:text/html,<script>alert(1)</script>')

    def test_url_safe_rejeita_file(self):
        assert not url_safe('file:///etc/passwd')

    def test_url_safe_rejeita_protocol_relative(self):
        assert not url_safe('//evil.com/phish')

    def test_url_safe_rejeita_tab_injection(self):
        """`/\\t/evil.com` — urlparse da netloc='evil.com', mas normalizacao
        do browser resolve como open redirect. Bloquear antes de urlparse."""
        assert not url_safe('/\t/evil.com')
        assert not url_safe('/\n/evil.com')
        assert not url_safe('/\r/evil.com')
        assert not url_safe('\t/path')

    def test_url_safe_aceita_https(self):
        assert url_safe('https://example.com/path')

    def test_url_safe_aceita_http(self):
        assert url_safe('http://example.com')

    def test_url_safe_aceita_path_absoluto(self):
        assert url_safe('/carteira/pedido/123')

    def test_url_safe_rejeita_vazio(self):
        assert not url_safe('')
        assert not url_safe(None)  # type: ignore[arg-type]

    def test_send_bloqueia_deep_link_invalido(self, db_session, user_factory):
        a = user_factory(email=f'c4_a_{_RUN}@t.local')
        b = user_factory(email=f'c4_b_{_RUN}@t.local')
        dm = ThreadService.get_or_create_dm(a, b)

        with pytest.raises(MessageError, match='deep_link invalido'):
            MessageService.send(
                sender=a, thread_id=dm.id, content='ola',
                deep_link='javascript:alert(1)',
            )

    def test_send_aceita_deep_link_none(self, db_session, user_factory):
        a = user_factory(email=f'c4_n_a_{_RUN}@t.local')
        b = user_factory(email=f'c4_n_b_{_RUN}@t.local')
        dm = ThreadService.get_or_create_dm(a, b)
        # deep_link=None e deep_link='' devem passar (campo opcional)
        m1 = MessageService.send(sender=a, thread_id=dm.id, content='a', deep_link=None)
        assert m1.deep_link is None
        m2 = MessageService.send(sender=a, thread_id=dm.id, content='b', deep_link='')
        assert m2.deep_link == ''


# ============================================================================
# C7 — race condition em get_or_create_dm (BAIXO — mitigado com advisory lock)
# ============================================================================

class TestC7DmRaceSerializedByLock:
    """
    Nao testa concorrencia real (DB lock so verificavel com 2 conexoes),
    mas valida que o lock nao quebra o happy path e que o dedup
    funciona em chamadas sequenciais do mesmo par.
    """

    def test_dm_par_sempre_mesma_thread(self, db_session, user_factory):
        a = user_factory(email=f'c7_a_{_RUN}@t.local')
        b = user_factory(email=f'c7_b_{_RUN}@t.local')

        t1 = ThreadService.get_or_create_dm(a, b)
        t2 = ThreadService.get_or_create_dm(b, a)   # inverte ordem
        t3 = ThreadService.get_or_create_dm(a, b)
        assert t1.id == t2.id == t3.id


# ============================================================================
# A6 — edit nao verificava deletado_em (vazamento via SSE message_edit)
# ============================================================================

class TestA6EditDeletedBlocked:
    def test_edit_mensagem_deletada_falha(self, db_session, user_factory):
        a = user_factory(email=f'a6_a_{_RUN}@t.local')
        b = user_factory(email=f'a6_b_{_RUN}@t.local')
        dm = ThreadService.get_or_create_dm(a, b)

        msg = MessageService.send(sender=a, thread_id=dm.id, content='original')
        MessageService.delete(a, msg.id)

        with pytest.raises(MessageError, match='deletada nao pode ser editada'):
            MessageService.edit(a, msg.id, 'tentando ressuscitar')


# ============================================================================
# A7 — delete nao publicava SSE message_delete
# ============================================================================

class TestA7DeletePublishesSse:
    def test_delete_publica_evento(self, db_session, user_factory, monkeypatch):
        a = user_factory(email=f'a7_a_{_RUN}@t.local')
        b = user_factory(email=f'a7_b_{_RUN}@t.local')
        dm = ThreadService.get_or_create_dm(a, b)
        msg = MessageService.send(sender=a, thread_id=dm.id, content='x')

        published = []

        def _capture_publish(user_id, event, data):
            published.append((user_id, event, data))

        # Patch do publish usado em delete — import tardio no proprio modulo
        monkeypatch.setattr(
            'app.chat.realtime.publisher.publish',
            _capture_publish,
        )

        MessageService.delete(a, msg.id)

        # Ao menos 1 evento message_delete publicado para algum membro
        delete_events = [p for p in published if p[1] == 'message_delete']
        assert len(delete_events) >= 1
        assert delete_events[0][2]['message_id'] == msg.id
        assert delete_events[0][2]['thread_id'] == dm.id
