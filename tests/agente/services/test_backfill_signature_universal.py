"""Backfill UNIVERSAL de error_signature — passivo historico do loop corretivo.

Generaliza o backfill hardcoded do Marcus (user 18): varre /memories/corrections/ VIVAS
(nao cold, nao directory) SEM error_signature de QUALQUER usuario e gera a assinatura via
helper. NAO funde clusters — apenas adiciona a assinatura. Idempotente, dry-run-first.

gerar_fn e' SEMPRE injetado (mock deterministico) -> sem custo de API.
"""
import importlib.util
import os

import pytest

from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentMemory


def _load_backfill():
    path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', '..', '..', 'scripts', 'backfill_signature_universal.py'))
    spec = importlib.util.spec_from_file_location('backfill_signature_universal', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def test_user(app):
    user = Usuario.query.filter_by(email='test_backfill_sig@test.com').first()
    if user:
        return user
    user = Usuario(email='test_backfill_sig@test.com', nome='Test Backfill Sig',
                   perfil='agente', status='ativo')
    user.set_senha('test_password_123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def outro_user(app):
    user = Usuario.query.filter_by(email='test_backfill_sig2@test.com').first()
    if user:
        return user
    user = Usuario(email='test_backfill_sig2@test.com', nome='Test Backfill Sig 2',
                   perfil='agente', status='ativo')
    user.set_senha('test_password_123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def cleanup(app, test_user):
    ids = []
    yield ids, test_user.id
    try:
        db.session.rollback()
    except Exception:
        pass
    for mid in ids:
        m = AgentMemory.query.get(mid)
        if m:
            db.session.delete(m)
    db.session.commit()


def _correcao(user_id, path, content='[correcao] agente errou no escopo\nDO: confirmar antes',
              *, is_cold=False, error_signature=None):
    mem = AgentMemory.create_file(user_id, path, content)
    mem.is_cold = is_cold
    mem.error_signature = error_signature
    db.session.commit()
    return mem


_GERAR_FIXO = lambda desc, presc: 'sig_gerada'  # noqa: E731 (mock deterministico, sem LLM)


def test_dry_run_nao_escreve(app, cleanup):
    ids, user_id = cleanup
    bf = _load_backfill()
    mem = _correcao(user_id, '/memories/corrections/bf_dry.xml')
    ids.append(mem.id)

    stats = bf.backfill_signatures(user_id=user_id, dry_run=True, gerar_fn=_GERAR_FIXO)

    db.session.refresh(mem)
    assert mem.error_signature is None          # dry-run nao escreve
    assert stats['candidatas'] == 1
    assert stats['assinadas'] == 1              # SERIA assinada


def test_confirmar_grava_signature(app, cleanup):
    ids, user_id = cleanup
    bf = _load_backfill()
    mem = _correcao(user_id, '/memories/corrections/bf_write.xml')
    ids.append(mem.id)

    stats = bf.backfill_signatures(user_id=user_id, dry_run=False, gerar_fn=_GERAR_FIXO)

    db.session.refresh(mem)
    assert mem.error_signature == 'sig_gerada'
    assert stats['assinadas'] == 1


def test_idempotente_pula_ja_assinada(app, cleanup):
    """Correcao que JA tem error_signature nao e candidata (nao sobrescreve)."""
    ids, user_id = cleanup
    bf = _load_backfill()
    mem = _correcao(user_id, '/memories/corrections/bf_idem.xml', error_signature='existente')
    ids.append(mem.id)

    stats = bf.backfill_signatures(user_id=user_id, dry_run=False,
                                   gerar_fn=lambda d, p: 'NAO_DEVE_USAR')

    db.session.refresh(mem)
    assert mem.error_signature == 'existente'   # intacta
    assert stats['candidatas'] == 0


def test_ignora_cold(app, cleanup):
    """Correcao arquivada (is_cold) nao e tocada pelo backfill."""
    ids, user_id = cleanup
    bf = _load_backfill()
    mem = _correcao(user_id, '/memories/corrections/bf_cold.xml', is_cold=True)
    ids.append(mem.id)

    stats = bf.backfill_signatures(user_id=user_id, dry_run=False, gerar_fn=_GERAR_FIXO)

    db.session.refresh(mem)
    assert mem.error_signature is None
    assert stats['candidatas'] == 0


def test_ignora_fora_de_corrections(app, cleanup):
    """So /memories/corrections/ — preferences/expertise/contexto nao sao tocados."""
    ids, user_id = cleanup
    bf = _load_backfill()
    mem = _correcao(user_id, '/memories/learned/expertise_x.xml')
    ids.append(mem.id)

    stats = bf.backfill_signatures(user_id=user_id, dry_run=False, gerar_fn=_GERAR_FIXO)

    db.session.refresh(mem)
    assert mem.error_signature is None
    assert stats['candidatas'] == 0


def test_filtra_por_user_id(app, cleanup, outro_user):
    """user_id filtra: backfill de um usuario nao toca correcoes de outro."""
    ids, user_id = cleanup
    bf = _load_backfill()
    minha = _correcao(user_id, '/memories/corrections/bf_minha.xml')
    ids.append(minha.id)
    alheia = _correcao(outro_user.id, '/memories/corrections/bf_alheia.xml')
    ids.append(alheia.id)

    stats = bf.backfill_signatures(user_id=user_id, dry_run=False, gerar_fn=_GERAR_FIXO)

    db.session.refresh(minha)
    db.session.refresh(alheia)
    assert minha.error_signature == 'sig_gerada'
    assert alheia.error_signature is None       # nao tocada
    assert stats['candidatas'] == 1


def test_assinatura_vazia_nao_grava(app, cleanup):
    """Se o gerador retorna vazio, nao grava e conta como sem_assinatura (nao quebra)."""
    ids, user_id = cleanup
    bf = _load_backfill()
    mem = _correcao(user_id, '/memories/corrections/bf_vazia.xml')
    ids.append(mem.id)

    stats = bf.backfill_signatures(user_id=user_id, dry_run=False, gerar_fn=lambda d, p: '')

    db.session.refresh(mem)
    assert mem.error_signature is None
    assert stats['candidatas'] == 1
    assert stats['assinadas'] == 0
    assert stats['sem_assinatura'] == 1
