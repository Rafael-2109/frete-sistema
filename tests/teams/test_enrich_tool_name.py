"""TDD F5: enriquecimento de tool_name no Teams para 'Skill:<nome>'.

Espelha o canal web (chat.py:861-870). Antes, o Teams gravava o bare 'Skill'
em tools_used -> build_skill_windows (avaliador de efetividade de skill) nao
encontrava janelas no Teams (web-only, debito documentado no CLAUDE.md). Com o
enriquecimento, 'Skill:<nome>' casa _skill_from_tools e o avaliador passa a
cobrir o canal Teams.
"""


def test_enrich_skill_com_nome():
    from app.teams.services import _enrich_tool_name
    assert _enrich_tool_name("Skill", {"skill": "cotando-frete"}) == "Skill:cotando-frete"


def test_enrich_skill_sem_nome_mantem_bare():
    from app.teams.services import _enrich_tool_name
    assert _enrich_tool_name("Skill", {"skill": ""}) == "Skill"
    assert _enrich_tool_name("Skill", {}) == "Skill"
    assert _enrich_tool_name("Skill", None) == "Skill"


def test_enrich_agent_subagent_type():
    from app.teams.services import _enrich_tool_name
    assert _enrich_tool_name("Agent", {"subagent_type": "analista-carteira"}) == "Agent:analista-carteira"


def test_enrich_agent_fallback_description():
    from app.teams.services import _enrich_tool_name
    assert _enrich_tool_name("Agent", {"description": "analisar carteira P1"}) == "Agent:analisar carteira P1"


def test_enrich_tool_comum_inalterado():
    from app.teams.services import _enrich_tool_name
    assert _enrich_tool_name("Read", {"file_path": "x"}) == "Read"
    assert _enrich_tool_name("mcp__sql__query", {}) == "mcp__sql__query"
    assert _enrich_tool_name("Bash", None) == "Bash"


def test_enrich_casa_com_skill_effectiveness_prefix():
    """O resultado para Skill DEVE casar com _skill_from_tools (build_skill_windows)."""
    from app.teams.services import _enrich_tool_name
    from app.agente.services.skill_effectiveness_service import _skill_from_tools
    enriched = _enrich_tool_name("Skill", {"skill": "gerindo-expedicao"})
    assert _skill_from_tools([enriched]) == "gerindo-expedicao"
    # bare 'Skill' (comportamento antigo) NAO casa -> prova a regressao corrigida
    assert _skill_from_tools(["Skill"]) is None
