"""Identidade unificada Teams <-> Web — Fase A do plano teams-melhorias.

Task A2: Usuario.find_by_teams_aad_id + modelo TeamsVinculoCodigo.
Task A3: hierarquia de resolucao em _get_or_create_teams_user
         (AAD ID vinculado -> auto-match por email -> fallback fantasma MD5 do nome).

NOTA de isolamento: _get_or_create_teams_user COMMITA internamente (gotcha
"commit em service fura savepoint"), entao estes testes criam dados com
sufixo uuid e limpam explicitamente no teardown (try/finally + delete).
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


def _novo_usuario(nome, email, status='ativo', teams_user_id=None,
                  teams_vinculo_origem=None):
    from app.auth.models import Usuario
    u = Usuario(
        nome=nome,
        email=email,
        perfil='logistica',
        status=status,
        teams_user_id=teams_user_id,
        teams_vinculo_origem=teams_vinculo_origem,
    )
    u.set_senha(uuid.uuid4().hex)
    _db.session.add(u)
    _db.session.commit()
    return u


def _cleanup_usuarios(ids):
    from app.auth.models import Usuario
    try:
        _db.session.rollback()
        for uid in ids:
            u = _db.session.get(Usuario, uid)
            if u:
                _db.session.delete(u)
        _db.session.commit()
    except Exception:
        _db.session.rollback()


# ═══════════════════════════════════════════════════════════════
# Task A2 — find_by_teams_aad_id + TeamsVinculoCodigo
# ═══════════════════════════════════════════════════════════════

class TestFindByTeamsAadId:
    def test_acha_usuario_ativo_por_aad_id(self, app_ctx):
        from app.auth.models import Usuario
        suf = uuid.uuid4().hex[:8]
        aad = f'aad-{suf}'
        u = _novo_usuario(f'Teste A2 {suf}', f'a2_{suf}@teste.local',
                          teams_user_id=aad, teams_vinculo_origem='codigo')
        try:
            achado = Usuario.find_by_teams_aad_id(aad)
            assert achado is not None
            assert achado.id == u.id
        finally:
            _cleanup_usuarios([u.id])

    def test_ignora_usuario_inativo(self, app_ctx):
        from app.auth.models import Usuario
        suf = uuid.uuid4().hex[:8]
        aad = f'aad-{suf}'
        u = _novo_usuario(f'Teste A2 {suf}', f'a2i_{suf}@teste.local',
                          status='bloqueado', teams_user_id=aad)
        try:
            assert Usuario.find_by_teams_aad_id(aad) is None
        finally:
            _cleanup_usuarios([u.id])

    def test_none_sem_match_ou_sem_aad(self, app_ctx):
        from app.auth.models import Usuario
        assert Usuario.find_by_teams_aad_id(None) is None
        assert Usuario.find_by_teams_aad_id('') is None
        assert Usuario.find_by_teams_aad_id(f'inexistente-{uuid.uuid4().hex}') is None


class TestTeamsVinculoCodigoModel:
    def test_cria_e_consulta_codigo(self, app_ctx):
        from datetime import timedelta
        from app.auth.models import TeamsVinculoCodigo
        from app.utils.timezone import agora_utc_naive
        suf = uuid.uuid4().hex[:8]
        u = _novo_usuario(f'Teste Cod {suf}', f'cod_{suf}@teste.local')
        vc = TeamsVinculoCodigo(
            user_id=u.id,
            codigo_hash='a' * 64,
            expires_at=agora_utc_naive() + timedelta(minutes=10),
        )
        _db.session.add(vc)
        _db.session.commit()
        try:
            achado = TeamsVinculoCodigo.query.filter_by(codigo_hash='a' * 64).first()
            assert achado is not None
            assert achado.user_id == u.id
            assert achado.used_at is None
        finally:
            _db.session.delete(vc)
            _db.session.commit()
            _cleanup_usuarios([u.id])


# ═══════════════════════════════════════════════════════════════
# Task A3 — hierarquia de resolucao em _get_or_create_teams_user
# ═══════════════════════════════════════════════════════════════

class TestHierarquiaResolucao:
    def test_aad_vinculado_resolve_direto(self, app_ctx):
        from app.teams.services import _get_or_create_teams_user
        suf = uuid.uuid4().hex[:8]
        aad = f'aad-{suf}'
        u = _novo_usuario(f'Vinculado {suf}', f'vinc_{suf}@teste.local',
                          teams_user_id=aad, teams_vinculo_origem='codigo')
        try:
            assert _get_or_create_teams_user(f'Vinculado {suf}', aad_id=aad) == u.id
        finally:
            _cleanup_usuarios([u.id])

    def test_email_match_grava_vinculo_automatico(self, app_ctx):
        from app.auth.models import Usuario
        from app.teams.services import _get_or_create_teams_user
        suf = uuid.uuid4().hex[:8]
        aad = f'aad-{suf}'
        email = f'email_{suf}@nacomgoya.com.br'
        u = _novo_usuario(f'PorEmail {suf}', email)
        try:
            # E-mail com caixa diferente deve casar (case-insensitive)
            resolved = _get_or_create_teams_user(
                f'PorEmail {suf}', aad_id=aad, email=email.upper(),
            )
            assert resolved == u.id
            _db.session.expire_all()
            fresh = _db.session.get(Usuario, u.id)
            assert fresh.teams_user_id == aad
            assert fresh.teams_vinculo_origem == 'email'
        finally:
            _cleanup_usuarios([u.id])

    def test_email_nao_sobrescreve_vinculo_existente(self, app_ctx):
        """Usuario ja vinculado a OUTRO aad nao e re-vinculado por email."""
        from app.auth.models import Usuario
        from app.teams.services import _get_or_create_teams_user
        suf = uuid.uuid4().hex[:8]
        email = f'fixo_{suf}@nacomgoya.com.br'
        u = _novo_usuario(f'Fixo {suf}', email,
                          teams_user_id=f'aad-original-{suf}',
                          teams_vinculo_origem='codigo')
        try:
            resolved = _get_or_create_teams_user(
                f'Fixo {suf}', aad_id=f'aad-outro-{suf}', email=email,
            )
            assert resolved == u.id
            _db.session.expire_all()
            fresh = _db.session.get(Usuario, u.id)
            assert fresh.teams_user_id == f'aad-original-{suf}'
            assert fresh.teams_vinculo_origem == 'codigo'
        finally:
            _cleanup_usuarios([u.id])

    def test_fallback_fantasma_por_nome_inalterado(self, app_ctx):
        """Sem aad/email: comportamento legacy (fantasma MD5 do nome) preservado."""
        import hashlib
        from app.auth.models import Usuario
        from app.teams.services import _get_or_create_teams_user
        suf = uuid.uuid4().hex[:8]
        nome = f'Fantasma Legacy {suf}'
        esperado_email = (
            f"teams_{hashlib.md5(nome.lower().strip().encode('utf-8')).hexdigest()[:12]}"
            f"@teams.nacomgoya.local"
        )
        uid = _get_or_create_teams_user(nome)
        try:
            assert uid is not None
            u = _db.session.get(Usuario, uid)
            assert u.email == esperado_email
        finally:
            _cleanup_usuarios([uid])
