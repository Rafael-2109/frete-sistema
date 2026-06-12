"""Testes do filtro de superficie do agent_loader (T2.1 arquitetura-conhecimento).

`surface: dev` no frontmatter = agent disponivel SO no Claude Code dev
(Task tool le o .md direto); ausente ou outro valor = carregado no loader
web (default retrocompativel). Sem DB — chama load_agent_definitions direto
(mesmo padrao de tests/agente/test_sped_audit_integration.py).
"""
import pytest

pytest.importorskip("claude_agent_sdk")

from app.agente.config.agent_loader import load_agent_definitions

AGENTS_DEV_ONLY_T21 = [
    "controlador-custo-frete",
    "gestor-devolucoes",
    "gestor-ssw",
    "desenvolvedor-integracao-odoo",
]


def _write_agent(tmp_path, filename, name, extra_frontmatter=""):
    """Cria um .md sintetico com frontmatter minimo (name + description)."""
    content = (
        "---\n"
        f"name: {name}\n"
        f"description: Agent sintetico de teste ({name})\n"
        f"{extra_frontmatter}"
        "---\n\n"
        f"# {name}\n\nCorpo de teste.\n"
    )
    (tmp_path / filename).write_text(content, encoding="utf-8")


def test_surface_dev_nao_carrega(tmp_path):
    """(a) Agent com surface: dev NAO entra no loader web."""
    _write_agent(tmp_path, "dev-only.md", "agent-dev-only",
                 extra_frontmatter="surface: dev\n")
    agents = load_agent_definitions(str(tmp_path))
    assert "agent-dev-only" not in agents


def test_sem_surface_carrega(tmp_path):
    """(b) Agent SEM campo surface E carregado (retrocompat)."""
    _write_agent(tmp_path, "sem-surface.md", "agent-sem-surface")
    agents = load_agent_definitions(str(tmp_path))
    assert "agent-sem-surface" in agents


def test_surface_web_carrega(tmp_path):
    """(c) Agent com surface diferente de 'dev' E carregado."""
    _write_agent(tmp_path, "surface-web.md", "agent-surface-web",
                 extra_frontmatter="surface: web\n")
    _write_agent(tmp_path, "surface-outro.md", "agent-surface-outro",
                 extra_frontmatter="surface: qualquer-coisa\n")
    agents = load_agent_definitions(str(tmp_path))
    assert "agent-surface-web" in agents
    assert "agent-surface-outro" in agents


def test_integracao_agents_reais():
    """(d) Loader real: 4 agents dev-only T2.1 ausentes; web seguem presentes."""
    agents = load_agent_definitions(".claude/agents")
    assert agents, ".claude/agents nao carregou nenhum agent"
    for nome in AGENTS_DEV_ONLY_T21:
        assert nome not in agents, (
            f"{nome} deveria estar FORA do loader web (surface: dev, T2.1)"
        )
    for nome in ["gestor-recebimento", "gestor-estoque-odoo"]:
        assert nome in agents, f"{nome} deveria continuar no loader web"
