"""
Configuracoes do Agente Lojas HORA.

Subclasse fina de `AgentSettings` (do agente logistico) com:
    - system_prompt/preset paths proprios
    - (futuro) whitelist de skills e subagents
    - constante `AGENTE_ID = 'lojas'` usada para filtros de banco
"""
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List

from app.agente.config.settings import AgentSettings


# Valor que vai para agent_sessions.agente e agent_memories.agente
AGENTE_ID = 'lojas'


@dataclass
class AgentLojasSettings(AgentSettings):
    """Settings do Agente Lojas HORA — herda AgentSettings e troca paths."""

    # Prompts proprios do agente de lojas
    system_prompt_path: str = "app/agente_lojas/prompts/system_prompt.md"
    operational_preset_path: str = "app/agente_lojas/prompts/preset_operacional.md"

    # Campo HERDADO de AgentSettings mas NAO lido pelo fork: _build_system_prompt()
    # do AgentLojasClient concatena APENAS preset + system_prompt (sem briefing).
    # Mantido VAZIO de proposito — apontar para o briefing Nacom
    # (app/agente/config/empresa_briefing.md) quebraria o contrato de isolamento
    # HORA se alguem "corrigir" _build_system_prompt() para inclui-lo. Em F3 o
    # briefing por perfil entra como config declarativa do perfil de agente.
    empresa_briefing_path: str = ""

    # ISOLAMENTO DO TOOL SURFACE (achado CRITICO da revisao adversarial do cutover):
    # o motor (get_client('lojas')._build_options) usa `allowed_tools = list(
    # settings.tools_enabled)`. Sem este override, o perfil 'lojas' herdaria o
    # conjunto WEB completo (Write/Edit/WebSearch/WebFetch/...) + TODOS os mcp__*
    # Nacom — vazando o dominio logistico ao operador de loja. Aqui restringimos
    # ao conjunto do FORK (ALLOWED_TOOLS_M1) + AskUserQuestion: o operador so
    # consulta via Bash+scripts Python das skills (com filtro <loja_context>),
    # NUNCA SQL livre. 'Skill' entra via option `skills` (allow-list fechada);
    # os mcp_servers sao pulados em _build_options quando agente_id=='lojas'
    # (gate em _register_mcp). NAO incluir: Write/Edit/MultiEdit (em
    # disallowed_tools tambem), WebSearch/WebFetch, mcp__*.
    tools_enabled: List[str] = field(default_factory=lambda: [
        'Bash',           # executa os scripts das skills de loja
        'Read', 'Glob', 'Grep',
        'Task',           # delega ao subagente orientador-loja
        'TaskCreate', 'TaskUpdate', 'TaskGet', 'TaskList',  # UI de tarefas
        'AskUserQuestion',  # perguntas interativas (modal) — seguro, sem dados
    ])

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
