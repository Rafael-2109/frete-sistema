"""MOTOR UNICO — ETAPA 1.2: AgentClient parametrizado por perfil de agente.

Invariantes (web byte-identico atras de default 'web'):
- get_client() is get_client('web') (singleton por agente_id);
- get_client('lojas') -> perfil isolado HORA (AgentLojasSettings, briefing vazio);
- _discover_skills_from_project: 'web'=deny-list, 'lojas'=allow-list fechada;
- _build_options agents=: 'lojas' so expoe SUBAGENTS_PERMITIDOS.
"""


# ---------------------------------------------------------------------------
# E1.2a — __init__(settings, agente_id) + get_client(agente_id) dict _clients
# ---------------------------------------------------------------------------

def test_get_client_default_e_web_sao_a_mesma_instancia():
    from app.agente.sdk.client import get_client, reset_client
    reset_client()
    c1 = get_client()
    c2 = get_client('web')
    assert c1 is c2
    assert c1.agente_id == 'web'


def test_get_client_lojas_perfil_isolado():
    from app.agente.sdk.client import get_client
    c = get_client('lojas')
    assert c.agente_id == 'lojas'
    assert c.settings.__class__.__name__ == 'AgentLojasSettings'
    assert c.settings.empresa_briefing_path == ''
    # guard: briefing vazio NAO injeta o bloco Nacom (isolamento HORA)
    assert c.empresa_briefing == ''


def test_get_client_web_e_lojas_sao_distintos():
    from app.agente.sdk.client import get_client
    assert get_client('web') is not get_client('lojas')


def test_reset_client_por_agente():
    from app.agente.sdk.client import get_client, reset_client
    web1 = get_client('web')
    reset_client('lojas')           # limpa so lojas
    assert get_client('web') is web1  # web preservado
    reset_client()                  # limpa todos
    assert get_client('web') is not web1


# ---------------------------------------------------------------------------
# E1.2b — _discover_skills_from_project(agente_id)
# ---------------------------------------------------------------------------

def test_discover_skills_web_e_deny_list():
    from app.agente.sdk.client import _discover_skills_from_project
    from app.agente.config.skills_whitelist import SKILLS_DELEGADAS_SUBAGENTE
    skills = set(_discover_skills_from_project('web'))
    # deny-list: nenhuma skill delegada a subagente aparece
    assert not (skills & set(SKILLS_DELEGADAS_SUBAGENTE))
    # web e dominio ABERTO: tem MUITAS skills
    assert len(skills) > 10


def test_discover_skills_lojas_e_allow_list_fechada():
    from app.agente.sdk.client import _discover_skills_from_project
    from app.agente_lojas.config.skills_whitelist import SKILLS_PERMITIDAS
    skills = set(_discover_skills_from_project('lojas'))
    # allow-list: subconjunto estrito de SKILLS_PERMITIDAS (so as que existem no disco)
    assert skills <= set(SKILLS_PERMITIDAS)
    # NAO vaza skill Nacom para o operador de loja
    assert 'gerindo-expedicao' not in skills
    assert 'rastreando-odoo' not in skills
    # contem ao menos uma skill HORA real
    assert 'consultando-estoque-loja' in skills


def test_discover_skills_default_e_web():
    from app.agente.sdk.client import _discover_skills_from_project
    assert _discover_skills_from_project() == _discover_skills_from_project('web')


# ---------------------------------------------------------------------------
# E1.2c — _build_options agents= filtrado por SUBAGENTS_PERMITIDOS (lojas)
# ---------------------------------------------------------------------------

def test_build_options_lojas_filtra_agents_para_permitidos(app):
    from app.agente.sdk.client import get_client
    from app.agente_lojas.config.skills_whitelist import SUBAGENTS_PERMITIDOS
    with app.app_context():
        opts = get_client('lojas')._build_options()
    agents = getattr(opts, 'agents', None) or {}
    assert set(agents.keys()) <= set(SUBAGENTS_PERMITIDOS)
    # subagentes Nacom NAO vazam para o operador de loja
    assert 'analista-carteira' not in agents
    assert 'especialista-odoo' not in agents


def test_build_options_web_expoe_catalogo_completo(app):
    from app.agente.sdk.client import get_client
    with app.app_context():
        opts = get_client('web')._build_options()
    agents = getattr(opts, 'agents', None) or {}
    # web (dominio aberto) carrega o catalogo completo de subagentes
    assert len(agents) > 1
