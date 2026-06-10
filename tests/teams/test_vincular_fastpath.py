"""Fast-path 'vincular CODIGO' — pareamento Teams <-> Web (Task A5).

Cobre:
  - regex should_intercept_vincular (anti-colisao com fast-path NF x PO da
    Gabriella: "vincular pedido X na nota Y" NAO pode ser interceptado;
    digitos puros tambem nao — codigo de pareamento comeca com letra)
  - executar_vincular_fastpath: codigo valido vincula + marca used;
    expirado/ja usado/inexistente -> resposta deterministica de erro;
    sem aad_id -> orienta retry.
"""
import hashlib
import uuid
from datetime import timedelta

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


def _novo_codigo(user_id, codigo, minutos=10, used=False):
    from app.auth.models import TeamsVinculoCodigo
    from app.utils.timezone import agora_utc_naive
    vc = TeamsVinculoCodigo(
        user_id=user_id,
        codigo_hash=hashlib.sha256(codigo.upper().encode()).hexdigest(),
        expires_at=agora_utc_naive() + timedelta(minutes=minutos),
        used_at=agora_utc_naive() if used else None,
    )
    _db.session.add(vc)
    _db.session.commit()
    return vc


def _cleanup(usuario_ids=(), codigos=()):
    from app.auth.models import Usuario
    try:
        _db.session.rollback()
        for vc in codigos:
            obj = _db.session.merge(vc)
            _db.session.delete(obj)
        for uid in usuario_ids:
            u = _db.session.get(Usuario, uid)
            if u:
                _db.session.delete(u)
        _db.session.commit()
    except Exception:
        _db.session.rollback()


class TestShouldInterceptVincular:
    def test_casa_codigo_valido(self, app_ctx):
        from app.agente.sdk.vincular_teams_fastpath import should_intercept_vincular
        assert should_intercept_vincular('vincular ABC123')
        assert should_intercept_vincular('  VINCULAR ab12cd  ')

    def test_nao_casa_frase_nf_po(self, app_ctx):
        """Anti-colisao com o fast-path NF x PO (Gabriella)."""
        from app.agente.sdk.vincular_teams_fastpath import should_intercept_vincular
        assert not should_intercept_vincular('vincular o pedido 123 na nota 456')
        assert not should_intercept_vincular('vincular pedido PD123 na NF 99887')

    def test_nao_casa_digitos_puros_nem_tamanho_errado(self, app_ctx):
        from app.agente.sdk.vincular_teams_fastpath import should_intercept_vincular
        assert not should_intercept_vincular('vincular 123456')   # pode ser num. de pedido
        assert not should_intercept_vincular('vincular ABC1234')  # 7 chars
        assert not should_intercept_vincular('vincular AB12')     # 4 chars
        assert not should_intercept_vincular('')
        assert not should_intercept_vincular(None)


class TestExecutarVincularFastpath:
    def test_codigo_valido_vincula_e_marca_used(self, app_ctx):
        from app.auth.models import Usuario, TeamsVinculoCodigo
        from app.agente.sdk.vincular_teams_fastpath import executar_vincular_fastpath
        suf = uuid.uuid4().hex[:8].upper()
        codigo = f'A{suf[:5]}'
        u = _novo_usuario(f'Pareamento {suf}', f'par_{suf}@nacomgoya.com.br')
        vc = _novo_codigo(u.id, codigo)
        try:
            out = executar_vincular_fastpath(
                f'vincular {codigo}', aad_id=f'aad-{suf}',
                email=None, nome=f'Pareamento {suf}', fallback_user_id=None,
            )
            assert out['ok'] is True
            assert u.nome in out['resposta']
            _db.session.expire_all()
            fresh = _db.session.get(Usuario, u.id)
            assert fresh.teams_user_id == f'aad-{suf}'
            assert fresh.teams_vinculo_origem == 'codigo'
            fresh_vc = _db.session.get(TeamsVinculoCodigo, vc.id)
            assert fresh_vc.used_at is not None
        finally:
            _cleanup(usuario_ids=[u.id], codigos=[vc])

    def test_codigo_expirado_ou_usado_responde_erro(self, app_ctx):
        from app.auth.models import Usuario
        from app.agente.sdk.vincular_teams_fastpath import executar_vincular_fastpath
        suf = uuid.uuid4().hex[:8].upper()
        u = _novo_usuario(f'Expirado {suf}', f'exp_{suf}@nacomgoya.com.br')
        vc_exp = _novo_codigo(u.id, f'B{suf[:5]}', minutos=-1)
        vc_used = _novo_codigo(u.id, f'C{suf[:5]}', used=True)
        try:
            out1 = executar_vincular_fastpath(
                f'vincular B{suf[:5]}', aad_id='aad-x', email=None,
                nome='X', fallback_user_id=None,
            )
            out2 = executar_vincular_fastpath(
                f'vincular C{suf[:5]}', aad_id='aad-x', email=None,
                nome='X', fallback_user_id=None,
            )
            assert out1['ok'] and 'inválido ou expirado' in out1['resposta']
            assert out2['ok'] and 'inválido ou expirado' in out2['resposta']
            _db.session.expire_all()
            fresh = _db.session.get(Usuario, u.id)
            assert fresh.teams_user_id is None  # nada gravado
        finally:
            _cleanup(usuario_ids=[u.id], codigos=[vc_exp, vc_used])

    def test_sem_aad_id_orienta_retry(self, app_ctx):
        from app.agente.sdk.vincular_teams_fastpath import executar_vincular_fastpath
        suf = uuid.uuid4().hex[:8].upper()
        u = _novo_usuario(f'SemAad {suf}', f'semaad_{suf}@nacomgoya.com.br')
        vc = _novo_codigo(u.id, f'D{suf[:5]}')
        try:
            out = executar_vincular_fastpath(
                f'vincular D{suf[:5]}', aad_id='', email=None,
                nome='X', fallback_user_id=None,
            )
            assert out['ok'] is True
            assert 'identificar' in out['resposta']
        finally:
            _cleanup(usuario_ids=[u.id], codigos=[vc])
