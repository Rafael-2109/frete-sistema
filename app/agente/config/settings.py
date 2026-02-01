"""
Configurações do Claude Agent SDK.

Conforme documentação oficial Anthropic:
- https://platform.claude.com/docs/pt-BR/agent-sdk/skills
- https://platform.claude.com/docs/pt-BR/agent-sdk/cost-tracking

O SDK gerencia sessions automaticamente. Não é necessário configurar Redis/TTL.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from functools import lru_cache


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
    model: str = "claude-opus-4-5-20251101"
    api_key: Optional[str] = None

    # Tools do SDK (ferramentas padrão permitidas)
    # NOTA: Funcionalidades são implementadas via SKILLS, não Custom Tools MCP
    # Skills estão em: .claude/skills/ (gerindo-expedicao, memoria-usuario, etc.)
    # Referência: https://platform.claude.com/docs/pt-BR/agent-sdk/skills
    tools_enabled: List[str] = field(default_factory=lambda: [
        'Skill',    # OBRIGATÓRIO - permite invocar Skills
        'Bash',     # OBRIGATÓRIO - executa scripts das Skills
        'Task',     # Invocar subagentes (.claude/agents/)
        'Read',     # Leitura de arquivos
        'Glob',     # Busca de arquivos
        'Grep',     # Busca em conteúdo
        'Memory',   # Memória persistente do usuário (DatabaseMemoryTool)
        'Write',    # Escrita de arquivos (RESTRITO a /tmp via can_use_tool)
        'Edit',     # Edição de arquivos (RESTRITO a /tmp via can_use_tool)
        'TodoWrite',  # Gerenciamento de tarefas (feedback visual)
        'WebSearch',  # Busca na web
        'WebFetch',  # Busca e salva na web
        'MultiEdit',  # Edição de arquivos (múltiplos arquivos)
    ])

    # Custos
    cost_tracking_enabled: bool = True
    cost_alert_threshold_usd: float = 1.0  # Alerta por sessão

    # Preços por modelo (por 1M tokens) — [input, output]
    # Ref: https://www.anthropic.com/pricing
    MODEL_PRICING: dict = field(default_factory=lambda: {
        'claude-opus-4-5-20251101': (5.00, 25.00),
        'claude-sonnet-4-5-20250514': (1.00, 5.00),
        'claude-haiku-4-5-20251001': (0.25, 1.25),
    })

    # System prompt
    system_prompt_path: str = "app/agente/prompts/system_prompt.md"

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
        # Fallback para Opus se modelo desconhecido
        input_price, output_price = self.MODEL_PRICING.get(
            model_id,
            self.MODEL_PRICING.get('claude-opus-4-5-20251101', (5.00, 25.00)),
        )
        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price
        return round(input_cost + output_cost, 6)


@lru_cache(maxsize=1)
def get_settings() -> AgentSettings:
    """
    Obtém configurações do agente (singleton cacheado).

    Returns:
        Instância de AgentSettings
    """
    return AgentSettings()


def reload_settings() -> AgentSettings:
    """
    Recarrega configurações (limpa cache).

    Returns:
        Nova instância de AgentSettings
    """
    get_settings.cache_clear()
    return get_settings()
