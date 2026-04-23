"""
Configuracoes do Agente Lojas HORA.

Subclasse fina de `AgentSettings` (do agente logistico) com:
    - system_prompt/preset paths proprios
    - (futuro) whitelist de skills e subagents
    - constante `AGENTE_ID = 'lojas'` usada para filtros de banco
"""
from dataclasses import dataclass
from functools import lru_cache

from app.agente.config.settings import AgentSettings


# Valor que vai para agent_sessions.agente e agent_memories.agente
AGENTE_ID = 'lojas'


@dataclass
class AgentLojasSettings(AgentSettings):
    """Settings do Agente Lojas HORA — herda AgentSettings e troca paths."""

    # Prompts proprios do agente de lojas
    system_prompt_path: str = "app/agente_lojas/prompts/system_prompt.md"
    operational_preset_path: str = "app/agente_lojas/prompts/preset_operacional.md"

    # M0: reusa empresa_briefing do agente principal (sera substituido em M1
    # por briefing dedicado das lojas HORA quando existir dominio para isso).
    empresa_briefing_path: str = "app/agente/config/empresa_briefing.md"

    # M0: sem skills/subagents especificos ainda (padrao vazio). Em M1+
    # sera preenchido pela whitelist importada de skills_whitelist.py.
    # Por enquanto o SDK herda a varredura padrao mas operador tera apenas
    # file I/O + Skill/Bash sem skills de dominio registradas.


@lru_cache(maxsize=1)
def get_lojas_settings() -> AgentLojasSettings:
    """Retorna singleton de AgentLojasSettings (cacheado)."""
    return AgentLojasSettings()


def reload_lojas_settings() -> AgentLojasSettings:
    """Recarrega settings (limpa cache)."""
    get_lojas_settings.cache_clear()
    return get_lojas_settings()
