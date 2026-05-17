"""Teste de integracao Fase 1 — subagente auditor-sped-ecd carrega e
invoca parser. NAO testa SDK end-to-end (custo $) — testa estrutura."""
import json
import subprocess
from pathlib import Path

import pytest

from app.agente.config.agent_loader import load_agent_definitions
from app.agente.config.settings import AgentSettings


def test_subagent_loaded():
    """Subagente auditor-sped-ecd carrega via load_agent_definitions()."""
    agents = load_agent_definitions(".claude/agents")
    assert "auditor-sped-ecd" in agents


def test_subagent_has_sped_skills():
    """Subagente declara as 4 skills SPED no frontmatter."""
    agents = load_agent_definitions(".claude/agents")
    a = agents["auditor-sped-ecd"]
    # SDK >= 0.1.49 expoe skills nativamente; se nao tem o campo, pular teste
    if not hasattr(a, "skills") or a.skills is None:
        pytest.skip("SDK < 0.1.49 sem campo skills nativo")
    for sped_skill in AgentSettings.SPED_SKILLS_RESERVED:
        assert sped_skill in a.skills, f"subagente sem skill {sped_skill}"


def test_subagent_has_reused_skills():
    """Subagente declara consultando-sql e descobrindo-odoo-estrutura."""
    agents = load_agent_definitions(".claude/agents")
    a = agents["auditor-sped-ecd"]
    if not hasattr(a, "skills") or a.skills is None:
        pytest.skip("SDK < 0.1.49 sem campo skills nativo")
    for s in ["consultando-sql", "descobrindo-odoo-estrutura"]:
        assert s in a.skills, f"subagente sem skill reuso {s}"


def test_subagent_model_and_effort():
    """Subagente usa Opus com effort xhigh (SDK >= 0.1.74)."""
    agents = load_agent_definitions(".claude/agents")
    a = agents["auditor-sped-ecd"]
    assert a.model == "opus", f"model esperado=opus, encontrado={a.model}"
    # effort pode ser None se SDK < 0.1.74
    if hasattr(a, "effort") and a.effort is not None:
        assert a.effort == "xhigh", f"effort esperado=xhigh, encontrado={a.effort}"


def test_parser_skill_exists_and_executable():
    """Script da skill parseando-sped-ecd existe."""
    script = Path(".claude/skills/parseando-sped-ecd/scripts/parse_sped.py")
    assert script.is_file(), f"{script} nao encontrado"
    content = script.read_text()
    assert content.startswith('"""Parser SPED'), \
        "parse_sped.py deve comecar com docstring 'Parser SPED'"


def test_parser_skill_smoke_run(tmp_path):
    """Smoke: parse de SPED minimo via subprocess nao da erro."""
    sped_minimal = (
        "|0000|LECD|01072024|31122024|TESTE|61724241000178|MG|3106200|"
        "||||||||0|0|0|0|N||||S||\r\n"
        "|9999|1|\r\n"
    )
    sped_path = tmp_path / "smoke.txt"
    sped_path.write_bytes(sped_minimal.encode("latin-1"))
    out_path = tmp_path / "out.json"

    result = subprocess.run(
        ["python",
         ".claude/skills/parseando-sped-ecd/scripts/parse_sped.py",
         str(sped_path), str(out_path)],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, (
        f"parser falhou: stderr={result.stderr}"
    )
    assert out_path.exists(), "JSON de saida nao criado"

    # Validar estrutura JSON
    with open(out_path) as f:
        parsed = json.load(f)
    assert "registros" in parsed
    assert "0000" in parsed["registros"]


def test_principal_does_not_see_sped_skills():
    """Defesa em profundidade: _discover_skills_from_project() filtra SPED."""
    from app.agente.sdk.client import _discover_skills_from_project
    skills = _discover_skills_from_project()
    for sped_skill in AgentSettings.SPED_SKILLS_RESERVED:
        assert sped_skill not in skills, (
            f"Vazamento: {sped_skill} apareceu no listing do principal"
        )
