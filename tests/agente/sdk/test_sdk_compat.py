"""
F1.2: deteccao compartilhada do campo `skills` (SDK 0.1.77+).

Hoje duplicada identicamente em web (_check_options_skills_field) e fork
(_check_skills_option). Extrai p/ modulo puro consumido por ambos.
"""
import dataclasses

from claude_agent_sdk import ClaudeAgentOptions

from app.agente.sdk.sdk_compat import check_skills_option, SDK_HAS_SKILLS_OPTION


def test_check_skills_option_reflete_presenca_do_campo():
    """Reflete a realidade do SDK instalado — nao acopla a True/False fixo."""
    esperado = 'skills' in {f.name for f in dataclasses.fields(ClaudeAgentOptions)}
    assert check_skills_option() is esperado


def test_sdk_has_skills_option_e_bool_de_modulo():
    assert isinstance(SDK_HAS_SKILLS_OPTION, bool)
    assert SDK_HAS_SKILLS_OPTION is check_skills_option()
