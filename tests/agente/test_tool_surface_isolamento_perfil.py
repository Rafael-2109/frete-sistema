"""
ISOLAMENTO DO TOOL SURFACE POR PERFIL (achado CRITICO da revisao adversarial do
cutover do agente lojas).

E1.2 isolou skills (tool `Skill`) e agents (tool `Task`), mas NAO o restante do
tool surface: `allowed_tools` herdava `AgentSettings.tools_enabled` (Write/Edit/
WebSearch/...) e `_register_mcp` registrava TODOS os MCP servers Nacom
(mcp__sql/memory/sessions/resolver/render/routes/...) sem gate por perfil.

Sob o motor (get_client('lojas')), isso exporia SQL arbitrario sobre tabelas
Nacom + memoria/sessoes Nacom ao operador de loja — violando o contrato HORA.

Contrato (paridade com o fork, que rodava com ZERO MCP + allow-list estreita):
  - perfil 'lojas': allowed_tools restrito (Bash/Read/Glob/Grep/Task/Task*),
    SEM Write/Edit/MultiEdit/WebSearch/WebFetch, SEM nenhum mcp__*; mcp_servers={}.
  - perfil 'web': INALTERADO (tool surface completo + MCP servers) — byte-identico.
"""
import pytest


def _allowed(opts):
    return set(getattr(opts, 'allowed_tools', []) or [])


def _mcp(opts):
    return getattr(opts, 'mcp_servers', {}) or {}


# ---------------------------------------------------------------------------
# Perfil 'lojas' — tool surface FECHADO
# ---------------------------------------------------------------------------

def test_lojas_zero_mcp_servers(app):
    from app.agente.sdk.client import get_client
    with app.app_context():
        opts = get_client('lojas')._build_options()
    assert _mcp(opts) == {}, "perfil 'lojas' NAO deve registrar nenhum MCP server Nacom"


def test_lojas_allowed_tools_sem_mcp(app):
    from app.agente.sdk.client import get_client
    with app.app_context():
        opts = get_client('lojas')._build_options()
    mcp_tools = [t for t in _allowed(opts) if t.startswith('mcp__')]
    assert mcp_tools == [], f"perfil 'lojas' nao deve ter mcp__* em allowed_tools: {mcp_tools}"


@pytest.mark.parametrize('tool', ['Write', 'Edit', 'MultiEdit', 'WebSearch', 'WebFetch'])
def test_lojas_sem_tools_perigosas_ou_nacom(app, tool):
    from app.agente.sdk.client import get_client
    with app.app_context():
        opts = get_client('lojas')._build_options()
    assert tool not in _allowed(opts), f"perfil 'lojas' NAO deve expor '{tool}'"


@pytest.mark.parametrize('tool', ['Bash', 'Read', 'Glob', 'Grep', 'Task'])
def test_lojas_tem_tools_de_consulta_da_loja(app, tool):
    from app.agente.sdk.client import get_client
    with app.app_context():
        opts = get_client('lojas')._build_options()
    assert tool in _allowed(opts), f"perfil 'lojas' precisa de '{tool}' (skills consultam via Bash)"


# ---------------------------------------------------------------------------
# Perfil 'web' — INALTERADO (byte-identico)
# ---------------------------------------------------------------------------

def test_web_mantem_mcp_servers(app):
    from app.agente.sdk.client import get_client
    with app.app_context():
        opts = get_client('web')._build_options()
    assert len(_mcp(opts)) > 0, "web deve manter os MCP servers (byte-identico)"
    assert any(t.startswith('mcp__') for t in _allowed(opts))


def test_web_mantem_tool_surface_completo(app):
    from app.agente.sdk.client import get_client
    with app.app_context():
        opts = get_client('web')._build_options()
    allowed = _allowed(opts)
    # web (dominio aberto) mantem WebSearch + Write (restrito a /tmp via can_use_tool)
    assert 'WebSearch' in allowed
    assert 'Write' in allowed
