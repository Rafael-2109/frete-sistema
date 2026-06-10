"""Merge de usuário fantasma Teams -> usuário real (Task A7).

Valida merge_usuario_teams (FK discovery via information_schema + reapontamento)
e _merge_usuario_fantasma (localiza fantasma pelo e-mail MD5 determinístico).
"""
import hashlib
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


def _novo_usuario(nome, email):
    from app.auth.models import Usuario
    u = Usuario(nome=nome, email=email, perfil='logistica', status='ativo')
    u.set_senha(uuid.uuid4().hex)
    _db.session.add(u)
    _db.session.commit()
    return u


def _nova_sessao(user_id):
    from app.agente.models import AgentSession
    s = AgentSession(
        session_id=f'teams_test_{uuid.uuid4().hex}',
        user_id=user_id,
        title='merge test',
        data={'messages': [], 'total_tokens': 0, 'channel': 'teams'},
    )
    _db.session.add(s)
    _db.session.commit()
    return s


def _cleanup(usuario_ids=(), sessoes=()):
    from app.auth.models import Usuario
    try:
        _db.session.rollback()
        for s in sessoes:
            obj = _db.session.merge(s)
            _db.session.delete(obj)
        for uid in usuario_ids:
            u = _db.session.get(Usuario, uid)
            if u:
                _db.session.delete(u)
        _db.session.commit()
    except Exception:
        _db.session.rollback()


class TestMergeUsuarioTeams:
    def test_dry_run_conta_sem_alterar(self, app_ctx):
        from app.teams.services import merge_usuario_teams
        suf = uuid.uuid4().hex[:8]
        fantasma = _novo_usuario(f'Dry {suf}', f'dry_f_{suf}@teams.nacomgoya.local')
        real = _novo_usuario(f'Dry Real {suf}', f'dry_r_{suf}@nacomgoya.com.br')
        sessao = _nova_sessao(fantasma.id)
        try:
            out = merge_usuario_teams(fantasma.id, real.id, dry_run=True)
            assert out['dry_run'] is True
            assert out['tabelas'].get('agent_sessions.user_id') == 1
            _db.session.expire_all()
            assert _db.session.merge(sessao).user_id == fantasma.id  # nada mudou
        finally:
            _cleanup(usuario_ids=[fantasma.id, real.id], sessoes=[sessao])

    def test_merge_real_reaponta_e_bloqueia_fantasma(self, app_ctx):
        from app.auth.models import Usuario
        from app.teams.services import merge_usuario_teams
        suf = uuid.uuid4().hex[:8]
        fantasma = _novo_usuario(f'Merge {suf}', f'mg_f_{suf}@teams.nacomgoya.local')
        real = _novo_usuario(f'Merge Real {suf}', f'mg_r_{suf}@nacomgoya.com.br')
        sessao = _nova_sessao(fantasma.id)
        try:
            out = merge_usuario_teams(fantasma.id, real.id, dry_run=False)
            assert out['tabelas'].get('agent_sessions.user_id') == 1
            _db.session.expire_all()
            assert _db.session.merge(sessao).user_id == real.id
            fresh_fantasma = _db.session.get(Usuario, fantasma.id)
            assert fresh_fantasma.status == 'bloqueado'
            assert 'MERGED' in (fresh_fantasma.observacoes or '')
        finally:
            _cleanup(usuario_ids=[fantasma.id, real.id], sessoes=[sessao])


class TestMergeFantasmaPorNome:
    def test_localiza_fantasma_pelo_email_md5(self, app_ctx):
        from app.teams.services import _merge_usuario_fantasma
        suf = uuid.uuid4().hex[:8]
        nome = f'Fantasma Nome {suf}'
        email_md5 = (
            f"teams_{hashlib.md5(nome.lower().strip().encode('utf-8')).hexdigest()[:12]}"
            f"@teams.nacomgoya.local"
        )
        fantasma = _novo_usuario(nome, email_md5)
        real = _novo_usuario(f'Nome Real {suf}', f'nr_{suf}@nacomgoya.com.br')
        sessao = _nova_sessao(fantasma.id)
        try:
            resumo = _merge_usuario_fantasma(nome, real.id)
            assert '1 conversas' in resumo
            _db.session.expire_all()
            assert _db.session.merge(sessao).user_id == real.id
        finally:
            _cleanup(usuario_ids=[fantasma.id, real.id], sessoes=[sessao])

    def test_sem_fantasma_retorna_vazio(self, app_ctx):
        from app.teams.services import _merge_usuario_fantasma
        assert _merge_usuario_fantasma(f'Inexistente {uuid.uuid4().hex}', 1) == ''
        assert _merge_usuario_fantasma(None, 1) == ''
