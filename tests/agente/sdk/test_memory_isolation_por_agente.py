"""
F2/M3 — teste-contrato de isolamento de memoria por agente.

Prova que `_load_user_memories_for_context(..., agente_id='lojas')` NAO injeta
memoria `agente='web'` (heuristica/perfil Nacom) e vice-versa. Foca no Tier 1
(deterministico — sempre injetado, sem depender de embedding/flags).

Com `agente_id='web'` (default), o comportamento do agente web e PRESERVADO: o
isolamento so "liga" quando 'lojas' e passado explicitamente (F3).
"""
import pytest

from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentMemory
from app.agente.sdk import memory_injection


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def test_user(app):
    email = 'test_iso_agente@test.com'
    user = Usuario.query.filter_by(email=email).first()
    if user:
        return user
    user = Usuario(email=email, nome='Test Iso Agente', perfil='agente', status='ativo')
    user.set_senha('test_password_123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def seed_mem(app, test_user):
    """Cria AgentMemory com `agente=` (create_file nao aceita o campo).

    `user_id=None` => memoria do usuario de teste; `user_id=0` => memoria
    empresa. `**kwargs` permite setar importance_score, meta, priority, etc.
    """
    criados = []

    def _criar(path, content, agente, user_id=None, **kwargs):
        m = AgentMemory(user_id=test_user.id if user_id is None else user_id,
                        path=path, content=content, agente=agente,
                        is_directory=False, **kwargs)
        db.session.add(m)
        db.session.commit()
        criados.append(m.id)
        return m

    yield _criar

    for mid in criados:
        obj = AgentMemory.query.get(mid)
        if obj:
            db.session.delete(obj)
    db.session.commit()


def _ids(user_id, agente_id):
    _main, _tail, ids = memory_injection._load_user_memories_for_context(
        user_id=user_id, agente_id=agente_id,
    )
    return set(ids or [])


def test_sessao_lojas_nao_injeta_memoria_web_tier1(seed_mem, test_user):
    m_web = seed_mem('/memories/user.xml', 'SEGREDO_NACOM_WEB_XYZ', agente='web')
    m_lojas = seed_mem('/memories/preferences.xml', 'DADO_DA_LOJA_XYZ', agente='lojas')

    ids = _ids(test_user.id, 'lojas')
    assert m_web.id not in ids, "id de memoria 'web' vazou p/ sessao 'lojas'"
    assert m_lojas.id in ids


def test_sessao_web_nao_injeta_memoria_lojas_tier1(seed_mem, test_user):
    m_web = seed_mem('/memories/user.xml', 'PERFIL_WEB_NACOM_XYZ', agente='web')
    m_lojas = seed_mem('/memories/preferences.xml', 'PERFIL_LOJA_HORA_XYZ', agente='lojas')

    ids = _ids(test_user.id, 'web')
    assert m_web.id in ids
    assert m_lojas.id not in ids, "id de memoria 'lojas' vazou p/ sessao 'web'"


# ─── M10: operational_directives (memoria empresa user_id=0, nivel 5) ───
def test_directives_empresa_nao_vazam_entre_agentes(seed_mem, test_user, monkeypatch):
    """A FONTE CRITICA: heuristicas/protocolos empresa (user_id=0) injetadas
    como diretiva operacional NAO podem cruzar a fronteira de agente."""
    monkeypatch.setattr(
        'app.agente.config.feature_flags.USE_OPERATIONAL_DIRECTIVES', True
    )
    m_web = seed_mem('/memories/empresa/heuristicas/odoo/dw.xml',
                     'WHEN: x\nDO: y\nnivel=5', agente='web', user_id=0,
                     importance_score=0.95,
                     meta={'nivel': 5, 'do': 'DIRETRIZ_NACOM_WEB', 'titulo': 'TW'})
    m_lojas = seed_mem('/memories/empresa/heuristicas/loja/dl.xml',
                       'WHEN: x\nDO: y\nnivel=5', agente='lojas', user_id=0,
                       importance_score=0.95,
                       meta={'nivel': 5, 'do': 'DIRETRIZ_LOJA', 'titulo': 'TL'})

    _, org_web = memory_injection._build_operational_directives_parts(
        test_user.id, agente_id='web')
    _, org_lojas = memory_injection._build_operational_directives_parts(
        test_user.id, agente_id='lojas')
    blob_web, blob_lojas = '\n'.join(org_web), '\n'.join(org_lojas)

    assert f'id="{m_web.id}"' in blob_web
    assert f'id="{m_web.id}"' not in blob_lojas, "diretiva empresa 'web' vazou p/ 'lojas'"
    assert f'id="{m_lojas.id}"' in blob_lojas
    assert f'id="{m_lojas.id}"' not in blob_web, "diretiva empresa 'lojas' vazou p/ 'web'"
