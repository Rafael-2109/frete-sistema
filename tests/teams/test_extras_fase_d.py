"""Extras Fase D — truncamento, fila concatenada, reset de conversa.

D1: _sanitizar_texto nao trunca mais em 3.8K (function ja splita em blocos de
    3.5K; Teams aceita ~28KB) — teto defensivo novo: 24K.
D2: 2a mensagem durante processamento CONCATENA na queued (antes sobrescrevia
    e a 1a sumia silenciosamente).
D4: fast-path 'nova conversa' expira a sessao ativa sem esperar TTL de 2h.
"""
import uuid

import pytest

from app import create_app, db as _db


@pytest.fixture(scope='module')
def app_ctx():
    _app = create_app()
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    with _app.app_context():
        yield _app


class TestTruncamentoD1:
    def test_10k_chars_nao_trunca(self, app_ctx):
        from app.teams.services import _sanitizar_texto
        texto = ("linha de resposta longa\n" * 500).strip()  # ~12K chars
        out = _sanitizar_texto(texto)
        assert 'resposta truncada' not in out
        assert len(out) > 10000

    def test_30k_chars_trunca_no_teto_defensivo(self, app_ctx):
        from app.teams.services import _sanitizar_texto
        texto = ("x" * 100 + "\n\n") * 300  # ~30K chars
        out = _sanitizar_texto(texto)
        assert len(out) <= 24100
        assert 'resposta truncada' in out


class TestFilaConcatenaD2:
    def test_segunda_mensagem_concatena(self, app_ctx, monkeypatch):
        import app.teams.bot_routes as br
        from app.teams.models import TeamsTask
        monkeypatch.setattr(br, 'TEAMS_BOT_API_KEY', 'test-key')
        conv = f'19:fila{uuid.uuid4().hex}@thread.v2'
        ativa = TeamsTask(conversation_id=conv, user_name='Fila',
                          status='processing', mensagem='em andamento')
        _db.session.add(ativa)
        _db.session.commit()
        client = app_ctx.test_client()
        try:
            r1 = client.post('/api/teams/bot/message', json={
                'mensagem': 'primeira pendente', 'usuario': 'Fila',
                'conversation_id': conv,
            }, headers={'X-API-Key': 'test-key'})
            assert r1.get_json()['status'] == 'queued'
            r2 = client.post('/api/teams/bot/message', json={
                'mensagem': 'segunda pendente', 'usuario': 'Fila',
                'conversation_id': conv,
            }, headers={'X-API-Key': 'test-key'})
            assert r2.get_json()['status'] == 'queued'
            queued = TeamsTask.query.filter_by(
                conversation_id=conv, status='queued').all()
            assert len(queued) == 1
            assert 'primeira pendente' in queued[0].mensagem
            assert 'segunda pendente' in queued[0].mensagem
        finally:
            _db.session.rollback()
            TeamsTask.query.filter_by(conversation_id=conv).delete()
            from app.auth.models import Usuario
            fantasma = Usuario.query.filter(
                Usuario.nome == 'Fila',
                Usuario.email.like('%@teams.nacomgoya.local')).first()
            if fantasma:
                _db.session.delete(fantasma)
            _db.session.commit()


class TestResetConversaD4:
    def test_regex_reset(self, app_ctx):
        from app.teams.services import _should_reset_conversa
        assert _should_reset_conversa('nova conversa')
        assert _should_reset_conversa('  Resetar Conversa  ')
        assert _should_reset_conversa('reiniciar sessão')
        assert _should_reset_conversa('reiniciar sessao')
        assert not _should_reset_conversa('nova conversa sobre o pedido X')
        assert not _should_reset_conversa('quero uma nova separacao')
        assert not _should_reset_conversa('')
        assert not _should_reset_conversa(None)

    def test_executa_reset_expira_sessao(self, app_ctx):
        from app.agente.models import AgentSession
        from app.teams.services import _executar_reset_conversa
        conv = f'19:reset{uuid.uuid4().hex[:20]}@thread.v2'
        s = AgentSession(
            session_id=f'teams_{conv}',
            user_id=1,
            title='reset test',
            data={'messages': [], 'total_tokens': 0, 'channel': 'teams'},
        )
        _db.session.add(s)
        _db.session.commit()
        try:
            out = _executar_reset_conversa(conv)
            assert out['ok'] is True
            _db.session.expire_all()
            fresh = _db.session.merge(s)
            # updated_at empurrado para o passado -> TTL cria sessao nova
            from datetime import timedelta
            from app.utils.timezone import agora_utc_naive
            assert fresh.updated_at < agora_utc_naive() - timedelta(hours=3)
        finally:
            _db.session.rollback()
            _db.session.delete(_db.session.merge(s))
            _db.session.commit()

    def test_reset_sem_sessao_ainda_ok(self, app_ctx):
        from app.teams.services import _executar_reset_conversa
        out = _executar_reset_conversa(f'19:inexistente{uuid.uuid4().hex}')
        assert out['ok'] is True  # nada a expirar = ja esta "novo"
