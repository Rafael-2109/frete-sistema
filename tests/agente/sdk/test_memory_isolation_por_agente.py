"""
F2/M3 — teste-contrato de isolamento de memoria por agente.

Prova que `_load_user_memories_for_context(..., agente_id='lojas')` NAO injeta
memoria `agente='web'` (heuristica/perfil Nacom) e vice-versa. Foca no Tier 1
(deterministico — sempre injetado, sem depender de embedding/flags).

Com `agente_id='web'` (default), o comportamento do agente web e PRESERVADO: o
isolamento so "liga" quando 'lojas' e passado explicitamente (F3).
"""
import uuid

import pytest

from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentMemory, AgentSession
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


@pytest.fixture
def seed_session(app, test_user):
    """Cria AgentSession com `agente=` e summary JSONB (resumo_geral)."""
    criados = []

    def _criar(agente, resumo, **kwargs):
        sid = f"iso-{agente}-{uuid.uuid4().hex[:12]}"
        s = AgentSession(session_id=sid, user_id=test_user.id, agente=agente,
                         summary={'resumo_geral': resumo}, **kwargs)
        db.session.add(s)
        db.session.commit()
        criados.append(s.id)
        return s

    yield _criar

    for sid in criados:
        obj = AgentSession.query.get(sid)
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


# ─── M08: _build_session_window (AgentSession por agente) ───
def test_session_window_isola_por_agente(seed_session, test_user):
    seed_session('web', 'RESUMO_SESSAO_WEB_UNICO')
    seed_session('lojas', 'RESUMO_SESSAO_LOJA_UNICO')

    block_web, _ = memory_injection._build_session_window(test_user.id, agente_id='web')
    block_lojas, _ = memory_injection._build_session_window(test_user.id, agente_id='lojas')

    assert 'RESUMO_SESSAO_WEB_UNICO' in (block_web or '')
    assert 'RESUMO_SESSAO_WEB_UNICO' not in (block_lojas or ''), "sessao 'web' vazou p/ janela 'lojas'"
    assert 'RESUMO_SESSAO_LOJA_UNICO' in (block_lojas or '')
    assert 'RESUMO_SESSAO_LOJA_UNICO' not in (block_web or ''), "sessao 'lojas' vazou p/ janela 'web'"


# ─── M09/H01: AgentMemory.get_by_path_for_agent ───
# NOTA: ha UNIQUE(user_id, path) sem agente => mesmo path so existe p/ 1 agente.
# O isolamento de RETRIEVAL e fail-closed: a memoria 'web' existe e o 'lojas'
# NAO a enxerga (None), em vez de pegar a do outro agente via .first().
def test_get_by_path_for_agent_isola(seed_mem, test_user):
    path = '/memories/system/resolved_pendencias.json'
    m_web = seed_mem(path, '["pend_web"]', agente='web')

    achado_web = AgentMemory.get_by_path_for_agent(test_user.id, path, 'web')
    achado_lojas = AgentMemory.get_by_path_for_agent(test_user.id, path, 'lojas')

    assert achado_web is not None and achado_web.id == m_web.id
    assert achado_lojas is None, "lojas enxergou resolved_pendencias do agente 'web'"


# ─── M11/M12: _build_routing_context (armadilhas empresa + dominio) ───
def test_routing_context_armadilhas_isola_por_agente(seed_mem, test_user):
    # paths /geral/ p/ nao casar segmento de dominio; sem sessions => domain=None
    seed_mem('/memories/empresa/armadilhas/geral/aw.xml', 'titulo', agente='web',
             user_id=0, effective_count=10,
             meta={'titulo': 'ARMADILHA_WEB_UNICA', 'do': 'x'})
    seed_mem('/memories/empresa/armadilhas/geral/al.xml', 'titulo', agente='lojas',
             user_id=0, effective_count=10,
             meta={'titulo': 'ARMADILHA_LOJA_UNICA', 'do': 'y'})

    rc_web = memory_injection._build_routing_context(test_user.id, agente_id='web') or ''
    rc_lojas = memory_injection._build_routing_context(test_user.id, agente_id='lojas') or ''

    assert 'ARMADILHA_WEB_UNICA' in rc_web
    assert 'ARMADILHA_WEB_UNICA' not in rc_lojas, "armadilha empresa 'web' vazou p/ 'lojas'"
    assert 'ARMADILHA_LOJA_UNICA' in rc_lojas
    assert 'ARMADILHA_LOJA_UNICA' not in rc_web, "armadilha empresa 'lojas' vazou p/ 'web'"
