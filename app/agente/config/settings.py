"""
Configurações do Claude Agent SDK.

Conforme documentação oficial Anthropic:
- https://platform.claude.com/docs/pt-BR/agent-sdk/skills
- https://platform.claude.com/docs/pt-BR/agent-sdk/cost-tracking

O SDK gerencia sessions automaticamente. Não é necessário configurar Redis/TTL.
"""

import os
from dataclasses import dataclass, field
from typing import ClassVar, List, Optional

from app.agente.config.skills_whitelist import SKILLS_SPED_RESERVED


@dataclass
class AgentSettings:
    """
    Configurações do agente logístico.

    Attributes:
        model: Modelo Claude a ser usado
        api_key: Chave da API Anthropic
        tools_enabled: Lista de tools habilitadas para Skills
        cost_tracking_enabled: Se rastreia custos
        cost_alert_threshold_usd: Alerta se custo exceder (por sessão)
    """

    # Modelo e API
    # Opus 4.8 (28/05/2026): mesma superficie de API que 4.7 (sem breaking change),
    # mesmo preco $5/$25 per MTok, 128K max output, 1M context window nativo,
    # adaptive thinking. Override via env AGENT_MODEL.
    model: str = "claude-opus-4-8"
    api_key: Optional[str] = None

    # Skills exclusivas do subagente auditor-sped-ecd.
    # Alias retrocompat para SKILLS_SPED_RESERVED (fonte única em skills_whitelist.py).
    # Filtradas via `skills=list[str]` no SDK 0.1.77+ — invisíveis no listing do
    # principal E rejeitadas pelo Skill tool (SDK_CHANGELOG.md:160-167).
    SPED_SKILLS_RESERVED: ClassVar[frozenset] = SKILLS_SPED_RESERVED

    # Tools do SDK (ferramentas padrão permitidas)
    # NOTA: Funcionalidades são implementadas via SKILLS, não Custom Tools MCP
    # Skills estão em: .claude/skills/ (gerindo-expedicao, memoria-usuario, etc.)
    # Referência: https://platform.claude.com/docs/pt-BR/agent-sdk/skills
    #
    # 'Skill' NÃO está listada aqui (SDK 0.1.77+ deprecou "Skill" em
    # allowed_tools em favor da option `skills=` em ClaudeAgentOptions).
    # client.py:_build_options() injeta `skills=_discover_skills_from_project()`
    # quando SDK >= 0.1.77 (exclui SPED_SKILLS_RESERVED do listing do principal)
    # ou injeta 'Skill' aqui como fallback para SDK < 0.1.77. Ver _SDK_HAS_OPTIONS_SKILLS.
    tools_enabled: List[str] = field(default_factory=lambda: [
        # Core — operações de arquivo e busca
        'Bash',             # OBRIGATÓRIO - executa scripts das Skills
        'Task',             # Invocar subagentes (.claude/agents/)
        'Read',             # Leitura de arquivos
        'Glob',             # Busca de arquivos
        'Grep',             # Busca em conteúdo
        'Write',            # Escrita de arquivos (RESTRITO a /tmp via can_use_tool)
        'Edit',             # Edição de arquivos (RESTRITO a /tmp via can_use_tool)
        'MultiEdit',        # Edição múltipla (RESTRITO a /tmp via can_use_tool)
        # Task* tools (SDK 0.2.82+: substituiu TodoWrite — ver SDK_CHANGELOG.md)
        'TaskCreate',       # Cria nova tarefa (#N autoincremental)
        'TaskUpdate',       # Atualiza tarefa por taskId (status, subject, etc.)
        'TaskGet',          # Consulta tarefa por taskId
        'TaskList',         # Lista todas tarefas — UI usa como snapshot
        'WebSearch',        # Busca na web
        'WebFetch',         # Fetch e análise de conteúdo web
        # Interação com usuário
        # FONTE: https://platform.claude.com/docs/en/agent-sdk/user-input
        # "If you specify a tools array, include AskUserQuestion in that array."
        'AskUserQuestion',  # Perguntas interativas ao usuário
        # Plan Mode
        'ExitPlanMode',     # Sair do modo planejamento
        'EnterPlanMode',    # Entrar no modo planejamento
        # Background tasks
        'TaskOutput',       # Ler output de Task em background
        'TaskStop',         # Parar Task em background
        'BashOutput',       # Ler output de Bash em background (skills longas)
        'KillBash',         # Parar Bash em background
        # MCP resources
        'ListMcpResources', # Listar resources disponíveis dos MCP servers
        'ReadMcpResource',  # Ler resources de MCP servers
        # Discovery
        'ToolSearch',       # Descobrir e carregar tools deferred antes de usá-las
    ])

    # Custos
    cost_tracking_enabled: bool = True
    cost_alert_threshold_usd: float = 1.0  # Alerta por sessão

    # Preços por modelo (por 1M tokens) — [input, output]
    # Ref: https://www.anthropic.com/pricing
    # Nota: Opus 4.7/4.8 usam novo tokenizer (~0-35% mais tokens por texto vs 4.6) —
    # custo/USD/request pode subir mesmo com preço/token idêntico. Monitorar.
    MODEL_PRICING: dict = field(default_factory=lambda: {
        'claude-opus-4-8': (5.00, 25.00),              # Default atual
        'claude-opus-4-7': (5.00, 25.00),              # Legacy: sessões existentes
        'claude-opus-4-6': (5.00, 25.00),              # Legacy: sessões existentes
        'claude-opus-4-5-20251101': (5.00, 25.00),     # Legacy: sessões antigas
        'claude-sonnet-4-6': (3.00, 15.00),
        'claude-haiku-4-5-20251001': (0.25, 1.25),
    })

    # System prompt
    system_prompt_path: str = "app/agente/prompts/system_prompt.md"

    # Preset operacional (substitui preset claude_code quando USE_CUSTOM_SYSTEM_PROMPT=true)
    operational_preset_path: str = "app/agente/prompts/preset_operacional.md"

    # Briefing institucional da Nacom Goya (cadeia de valor, sistemas, gargalos, vocabulario).
    # Concatenado ao system_prompt estatico via _build_full_system_prompt() — cacheavel.
    # Mesmo arquivo tambem consumido por pattern_analyzer.py (extracao pos-sessao Sonnet).
    empresa_briefing_path: str = "app/agente/config/empresa_briefing.md"

    # Logs
    log_tool_calls: bool = True

    def __post_init__(self):
        """Carrega valores de variáveis de ambiente."""
        self.api_key = os.getenv('ANTHROPIC_API_KEY', self.api_key)
        self.model = os.getenv('AGENT_MODEL', self.model)

        # Validação
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY não configurada. "
                "Defina a variável de ambiente ANTHROPIC_API_KEY."
            )

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: Optional[str] = None,
    ) -> float:
        """
        Calcula custo de uma requisição.

        Args:
            input_tokens: Tokens de entrada
            output_tokens: Tokens de saída
            model: Modelo usado (se None, usa self.model)

        Returns:
            Custo em USD
        """
        model_id = model or self.model
        # Fallback para Opus 4.8 se modelo desconhecido
        input_price, output_price = self.MODEL_PRICING.get(
            model_id,
            self.MODEL_PRICING.get('claude-opus-4-8', (5.00, 25.00)),
        )
        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price
        return round(input_cost + output_cost, 6)


# Cache de settings POR PERFIL de agente. Cada agente_id mapeia para UMA
# instancia — identidade preservada: get_settings() is get_settings('web').
# (Substitui o lru_cache(maxsize=1) global; o default 'web' mantem os ~8
#  callers existentes byte-identicos — todos chamam sem argumento.)
_settings_by_agent: dict = {}


def get_settings(agente_id: str = 'web') -> AgentSettings:
    """
    Obtém configurações do agente por PERFIL (singleton por agente_id).

    Args:
        agente_id: 'web' (default) → AgentSettings (logístico Nacom, comportamento
            histórico); 'lojas' → AgentLojasSettings (perfil isolado HORA, sem
            briefing Nacom). O default preserva os callers sem argumento.

    Returns:
        Instância de AgentSettings (ou subclasse de perfil).

    Raises:
        ValueError: agente_id desconhecido (fail-closed — D3: sem default silencioso).
    """
    agente_id = agente_id or 'web'
    cached = _settings_by_agent.get(agente_id)
    if cached is not None:
        return cached
    if agente_id == 'web':
        settings: AgentSettings = AgentSettings()
    elif agente_id == 'lojas':
        # Import lazy: agente_lojas.config.settings importa ESTE módulo no topo;
        # o lazy quebra o ciclo e mantém o web sem dependência de import-time
        # do perfil (só carrega o perfil lojas quando alguém o pede).
        from app.agente_lojas.config.settings import AgentLojasSettings
        settings = AgentLojasSettings()
    else:
        raise ValueError(
            f"agente_id desconhecido: {agente_id!r} (esperado 'web' ou 'lojas')"
        )
    _settings_by_agent[agente_id] = settings
    return settings


def reload_settings(agente_id: Optional[str] = None) -> AgentSettings:
    """
    Recarrega configurações (limpa cache).

    Args:
        agente_id: se None, limpa TODOS os perfis; caso contrário, limpa só esse.

    Returns:
        Instância recarregada do perfil 'web' (ou do agente_id informado).
    """
    if agente_id is None:
        _settings_by_agent.clear()
        return get_settings()
    _settings_by_agent.pop(agente_id, None)
    return get_settings(agente_id)
