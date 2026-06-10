"""Falante do turno em grupos (Fase B — Task B1).

Cobre:
  - add_user_message(author=): persiste autor; sem author o dict fica identico
    ao formato atual (web inalterado).
  - _montar_prompt_teams: prefixa [Mensagem de: X] APENAS em conversa de grupo.
  - _construir_fallback_xml: inclui author quando presente nas mensagens.
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


def _nova_sessao():
    from app.agente.models import AgentSession
    s = AgentSession(
        session_id=f'teams_test_{uuid.uuid4().hex}',
        user_id=1,
        title='falante test',
        data={'messages': [], 'total_tokens': 0, 'channel': 'teams'},
    )
    _db.session.add(s)
    _db.session.commit()
    return s


def _cleanup(sessoes):
    try:
        _db.session.rollback()
        for s in sessoes:
            obj = _db.session.merge(s)
            _db.session.delete(obj)
        _db.session.commit()
    except Exception:
        _db.session.rollback()


class TestAddUserMessageAuthor:
    def test_author_persistido(self, app_ctx):
        s = _nova_sessao()
        try:
            msg = s.add_user_message('oi', author='Marcus')
            assert msg['author'] == 'Marcus'
            assert s.data['messages'][-1]['author'] == 'Marcus'
        finally:
            _cleanup([s])

    def test_sem_author_dict_identico_ao_atual(self, app_ctx):
        """Web inalterado: sem author, a mensagem NAO ganha chave nova."""
        s = _nova_sessao()
        try:
            msg = s.add_user_message('oi')
            assert 'author' not in msg
            assert set(msg.keys()) == {'id', 'role', 'content', 'timestamp'}
        finally:
            _cleanup([s])


class TestMontarPromptTeams:
    def test_grupo_prefixa_falante(self, app_ctx):
        from app.teams.services import _montar_prompt_teams
        prompt = _montar_prompt_teams('qual o estoque?', 'Marcus', 'groupChat')
        assert '[Mensagem de: Marcus]' in prompt
        assert prompt.index('[Mensagem de: Marcus]') < prompt.index('qual o estoque?')

    def test_channel_prefixa_falante(self, app_ctx):
        from app.teams.services import _montar_prompt_teams
        prompt = _montar_prompt_teams('oi', 'Rafael', 'channel')
        assert '[Mensagem de: Rafael]' in prompt

    def test_personal_nao_prefixa(self, app_ctx):
        from app.teams.services import _montar_prompt_teams
        prompt = _montar_prompt_teams('qual o estoque?', 'Marcus', 'personal')
        assert '[Mensagem de:' not in prompt
        assert 'qual o estoque?' in prompt


class TestFallbackXmlComAutor:
    def test_inclui_author_quando_presente(self, app_ctx):
        from app.teams.services import _construir_fallback_xml
        s = _nova_sessao()
        try:
            s.add_user_message('pergunta do rafael', author='Rafael')
            s.add_assistant_message(content='resposta 1')
            s.add_user_message('pergunta do marcus', author='Marcus')
            _db.session.commit()
            xml = _construir_fallback_xml(s)
            assert xml is not None
            assert '<msg role="user" author="Rafael">' in xml
            assert '<msg role="user" author="Marcus">' in xml
        finally:
            _cleanup([s])

    def test_sem_author_formato_atual(self, app_ctx):
        from app.teams.services import _construir_fallback_xml
        s = _nova_sessao()
        try:
            s.add_user_message('pergunta')
            s.add_assistant_message(content='resposta')
            _db.session.commit()
            xml = _construir_fallback_xml(s)
            assert xml is not None
            assert '<msg role="user">' in xml
            assert 'author=' not in xml
        finally:
            _cleanup([s])

    def test_uma_mensagem_retorna_none(self, app_ctx):
        """Preserva regra atual: fallback so com len(messages) > 1."""
        from app.teams.services import _construir_fallback_xml
        s = _nova_sessao()
        try:
            s.add_user_message('so uma')
            _db.session.commit()
            assert _construir_fallback_xml(s) is None
        finally:
            _cleanup([s])
