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

    def _criar(agente, resumo, tarefas=None, **kwargs):
        sid = f"iso-{agente}-{uuid.uuid4().hex[:12]}"
        summary = {'resumo_geral': resumo, 'tarefas_pendentes': tarefas or []}
        s = AgentSession(session_id=sid, user_id=test_user.id, agente=agente,
                         summary=summary, **kwargs)
        db.session.add(s)
        db.session.commit()
        criados.append(s.id)
        return s

    yield _criar

    for pk in criados:  # criados guarda AgentSession.id (PK int), nao session_id
        obj = AgentSession.query.get(pk)
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
    # path_web e path_lojas distintos (UNIQUE user_id,path) — prova ambos os lados:
    # cada agente acha A SUA e NAO acha a do outro.
    path_web = '/memories/system/resolved_pendencias.json'
    path_lojas = '/memories/system/resolved_pendencias_loja.json'
    m_web = seed_mem(path_web, '["pend_web"]', agente='web')
    m_lojas = seed_mem(path_lojas, '["pend_loja"]', agente='lojas')

    # web acha a sua; nao acha a de lojas (mesmo passando o path da lojas)
    assert AgentMemory.get_by_path_for_agent(test_user.id, path_web, 'web').id == m_web.id
    assert AgentMemory.get_by_path_for_agent(test_user.id, path_lojas, 'web') is None
    # lojas acha a sua; nao acha a do web (mesmo passando o path do web)
    assert AgentMemory.get_by_path_for_agent(test_user.id, path_lojas, 'lojas').id == m_lojas.id
    assert AgentMemory.get_by_path_for_agent(test_user.id, path_web, 'lojas') is None, \
        "lojas enxergou resolved_pendencias do agente 'web'"


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


# ─── R01: _build_user_rules (canal L1 priority=mandatory) ───
def test_user_rules_isola_por_agente(seed_mem, test_user):
    from app.agente.sdk import memory_injection_rules
    seed_mem('/memories/rules/r_web.xml', 'REGRA_NACOM_WEB_UNICA', agente='web',
             priority='mandatory', is_cold=False)
    seed_mem('/memories/rules/r_loja.xml', 'REGRA_LOJA_HORA_UNICA', agente='lojas',
             priority='mandatory', is_cold=False)

    rules_web = memory_injection_rules._build_user_rules(test_user.id, agente_id='web') or ''
    rules_lojas = memory_injection_rules._build_user_rules(test_user.id, agente_id='lojas') or ''

    assert 'REGRA_NACOM_WEB_UNICA' in rules_web
    assert 'REGRA_NACOM_WEB_UNICA' not in rules_lojas, "regra 'web' vazou p/ canal L1 'lojas'"
    assert 'REGRA_LOJA_HORA_UNICA' in rules_lojas
    assert 'REGRA_LOJA_HORA_UNICA' not in rules_web, "regra 'lojas' vazou p/ canal L1 'web'"


# ─── B01-B03: build_intersession_briefing (continuidade por agente) ───
def test_briefing_continuidade_isola_por_agente(seed_session, test_user):
    from app.agente.services import intersession_briefing
    seed_session('web', 'r', tarefas=['CONTINUE_TAREFA_WEB_UNICA'])
    seed_session('lojas', 'r', tarefas=['CONTINUE_TAREFA_LOJA_UNICA'])

    brief_web = intersession_briefing.build_intersession_briefing(
        test_user.id, agente_id='web') or ''
    brief_lojas = intersession_briefing.build_intersession_briefing(
        test_user.id, agente_id='lojas') or ''

    assert 'CONTINUE_TAREFA_WEB_UNICA' in brief_web
    assert 'CONTINUE_TAREFA_WEB_UNICA' not in brief_lojas, "continuidade 'web' vazou p/ briefing 'lojas'"
    assert 'CONTINUE_TAREFA_LOJA_UNICA' in brief_lojas
    assert 'CONTINUE_TAREFA_LOJA_UNICA' not in brief_web, "continuidade 'lojas' vazou p/ briefing 'web'"


# ─── Defesa residual: fontes via PreToolUse hook (M13 + enforce) ───
def test_skill_reminders_isola_por_agente(seed_mem, test_user, monkeypatch):
    monkeypatch.setattr('app.agente.config.feature_flags.AGENT_SKILL_EVAL', True)
    seed_mem('/memories/lembretes_skill/skillweb.xml', 'LEMBRETE', agente='web')
    seed_mem('/memories/lembretes_skill/skillloja.xml', 'LEMBRETE', agente='lojas')

    rem_web = memory_injection.get_skill_reminders_for_session(
        test_user.id, 'sid-web-' + uuid.uuid4().hex[:8], agente_id='web')
    rem_lojas = memory_injection.get_skill_reminders_for_session(
        test_user.id, 'sid-lojas-' + uuid.uuid4().hex[:8], agente_id='lojas')

    assert 'skillweb' in rem_web and 'skillloja' not in rem_web, "lembrete 'lojas' vazou p/ 'web'"
    assert 'skillloja' in rem_lojas and 'skillweb' not in rem_lojas, "lembrete 'web' vazou p/ 'lojas'"


def test_enforce_directives_isola_por_agente(seed_mem, test_user):
    from app.agente.sdk import hooks
    seed_mem('/memories/rules/enf_web.xml', 'ENFORCE_DENY_SUBSTR: TOKEN_WEB_X',
             agente='web', priority='mandatory', is_cold=False)
    seed_mem('/memories/rules/enf_loja.xml', 'ENFORCE_DENY_SUBSTR: TOKEN_LOJA_X',
             agente='lojas', priority='mandatory', is_cold=False)

    tokens_web = {t for t, _ in hooks._load_enforce_directives(test_user.id, agente_id='web')}
    tokens_lojas = {t for t, _ in hooks._load_enforce_directives(test_user.id, agente_id='lojas')}

    assert 'TOKEN_WEB_X' in tokens_web and 'TOKEN_LOJA_X' not in tokens_web
    assert 'TOKEN_LOJA_X' in tokens_lojas and 'TOKEN_WEB_X' not in tokens_lojas, \
        "invariante DENY 'web' vazou p/ enforcement 'lojas'"
