"""Compat do Claude Agent SDK — deteccao de capabilities por versao. PURO.

Sem dominio Nacom; importavel de submodulo por ambos os clients (web e
agente_lojas) para nao duplicar a deteccao do campo `skills` (SDK 0.1.77+).
NAO importar `client.py` aqui (evita circular / puxar AgentClient+pool).
"""
import dataclasses

from claude_agent_sdk import ClaudeAgentOptions


def check_skills_option() -> bool:
    """True se ``ClaudeAgentOptions`` tem o campo ``skills`` nativo (SDK 0.1.77+).

    SDK 0.1.77 deprecou ``"Skill"`` em allowed_tools em favor da option
    ``skills: list[str] | Literal["all"] | None``. Quando presente, o SDK
    auto-configura ``"Skill"`` em allowed_tools + setting_sources e filtra o
    listing do model. Fallback (SDK < 0.1.77): ``"Skill"`` injetado manualmente.
    """
    try:
        fields = {f.name for f in dataclasses.fields(ClaudeAgentOptions)}
        return 'skills' in fields
    except Exception:
        return False


# Detectado uma vez no import — zero overhead por request.
SDK_HAS_SKILLS_OPTION = check_skills_option()
