"""
Configurações do Claude AI Lite.

FILOSOFIA:
- Configurações são DIRETRIZES, não regras absolutas
- Claude pode solicitar override em casos justificados
- Valores são defaults que podem ser ajustados por contexto

Criado em: 26/11/2025
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NivelAutonomia(Enum):
    """Nível de autonomia do Claude nas decisões."""
    RESTRITO = "restrito"      # Segue regras à risca
    BALANCEADO = "balanceado"  # Default - equilibra regras e julgamento
    AUTONOMO = "autonomo"      # Mais liberdade para decidir


@dataclass
class ConfigPlanejamento:
    """Configurações do AgentPlanner."""

    # Etapas
    max_etapas_default: int = 5
    max_etapas_complexas: int = 10  # Claude pode solicitar se justificar
    permitir_solicitacao_etapas_extras: bool = True

    # Filtros - SEGURANÇA
    filtro_cliente_obrigatorio: bool = True   # Manter True para segurança
    filtro_pedido_obrigatorio: bool = True    # Manter True para segurança
    permitir_consultas_agregadas_sem_filtro: bool = True  # Ex: "total faturado hoje"

    # Prompt
    usar_diretrizes_flexiveis: bool = True  # Trocar SEMPRE/NUNCA por diretrizes


@dataclass
class ConfigOrquestracao:
    """Configurações do Orchestrator."""

    # Fluxo
    permitir_pular_etapas: bool = True  # Claude decide quais etapas são necessárias
    etapas_obrigatorias: List[str] = field(default_factory=lambda: [
        "extrair_inteligente"  # Esta é sempre necessária
    ])
    etapas_opcionais: List[str] = field(default_factory=lambda: [
        "carregar_conhecimento",
        "buscar_memoria"
    ])

    # Domínios customizáveis
    handlers_customizados: Dict[str, str] = field(default_factory=dict)
    # Exemplo: {"urgente": "processar_urgente", "preview": "processar_preview"}


@dataclass
class ConfigExtracao:
    """Configurações do IntelligentExtractor."""

    # Capabilities
    carregar_capabilities_dinamicamente: bool = True  # Usar ToolRegistry
    permitir_campos_extras_na_resposta: bool = True   # Claude pode adicionar contexto

    # Confiança
    limiar_confianca_minima: float = 0.3  # Abaixo disso, pede clarificação


@dataclass
class ConfigResposta:
    """Configurações do Responder."""

    # Revisão
    revisao_automatica: bool = True
    revisao_condicional: bool = True  # Claude decide se precisa revisar
    limiar_confianca_sem_revisao: float = 0.9  # Acima disso, não revisa

    # Opções
    min_opcoes: int = 2
    max_opcoes: int = 5  # Não mais fixo em 3
    permitir_opcoes_customizadas: bool = True


@dataclass
class ConfigMemoria:
    """Configurações de memória e histórico."""

    # Histórico
    max_mensagens_default: int = 40
    estrategia_historico: str = "recent_and_relevant"  # "recent_only" ou "recent_and_relevant"

    # Tokens
    max_tokens_contexto: int = 8192
    ajustar_por_modelo: bool = True  # Ajusta baseado no modelo Claude usado
    tokens_por_modelo: Dict[str, int] = field(default_factory=lambda: {
        "haiku": 4096,
        "sonnet": 8192,
        "opus": 16384
    })

    # Estimativa
    chars_por_token: int = 4  # 1 token ≈ 4 caracteres


@dataclass
class ConfigFerramentas:
    """Configurações do ToolRegistry."""

    # Cache
    cache_ttl_segundos: int = 300  # 5 minutos
    cache_ttl_dinamico: bool = True  # Ajusta baseado em volatilidade

    # Schema
    schema_dinamico: bool = True  # Usar SQLAlchemy inspect
    schema_cache_ttl: int = 3600  # 1 hora (schema muda pouco)

    # Tipos
    tipos_ferramenta_customizados: Dict[str, Callable] = field(default_factory=dict)
    # Exemplo: {"ml_model": executar_ml_model}


@dataclass
class ConfigLimites:
    """Limites de segurança (NÃO FLEXIBILIZAR SEM MOTIVO)."""

    # Resultados
    max_registros_query: int = 1000  # SEGURANÇA: protege o banco
    max_registros_relatorio: int = 5000  # Para relatórios explícitos

    # Tempo
    timeout_query_segundos: int = 30
    timeout_planejamento_segundos: int = 60


@dataclass
class ConfigClaudeAILite:
    """Configuração master do módulo."""

    nivel_autonomia: NivelAutonomia = NivelAutonomia.BALANCEADO

    planejamento: ConfigPlanejamento = field(default_factory=ConfigPlanejamento)
    orquestracao: ConfigOrquestracao = field(default_factory=ConfigOrquestracao)
    extracao: ConfigExtracao = field(default_factory=ConfigExtracao)
    resposta: ConfigResposta = field(default_factory=ConfigResposta)
    memoria: ConfigMemoria = field(default_factory=ConfigMemoria)
    ferramentas: ConfigFerramentas = field(default_factory=ConfigFerramentas)
    limites: ConfigLimites = field(default_factory=ConfigLimites)

    def __post_init__(self):
        """Log da configuração carregada."""
        logger.info(f"[CONFIG] Claude AI Lite iniciado com autonomia: {self.nivel_autonomia.value}")


# =============================================================================
# SINGLETON E FUNÇÕES DE ACESSO
# =============================================================================

_config: Optional[ConfigClaudeAILite] = None


def get_config() -> ConfigClaudeAILite:
    """Retorna configuração singleton."""
    global _config
    if _config is None:
        _config = ConfigClaudeAILite()
    return _config


def set_config(config: ConfigClaudeAILite):
    """Define configuração customizada."""
    global _config
    _config = config
    logger.info(f"[CONFIG] Configuração atualizada. Autonomia: {config.nivel_autonomia.value}")


def reset_config():
    """Reseta para configuração padrão."""
    global _config
    _config = None
    logger.info("[CONFIG] Configuração resetada para padrão")


# =============================================================================
# HELPERS PARA ACESSO RÁPIDO
# =============================================================================

def get_max_etapas(plano: Dict = None) -> int:
    """
    Retorna máximo de etapas permitidas.

    Pode aumentar se Claude solicitar com justificativa.

    Args:
        plano: Plano retornado pelo Claude (pode conter solicitação de mais etapas)

    Returns:
        Número máximo de etapas permitidas
    """
    config = get_config()
    max_default = config.planejamento.max_etapas_default

    # Se plano solicita mais etapas E config permite
    if plano and config.planejamento.permitir_solicitacao_etapas_extras:
        etapas_solicitadas = plano.get('etapas_necessarias')
        justificativa = plano.get('justificativa_etapas_extras')

        if etapas_solicitadas and justificativa:
            max_complexas = config.planejamento.max_etapas_complexas
            etapas_permitidas = min(etapas_solicitadas, max_complexas)
            logger.info(f"[CONFIG] Claude solicitou {etapas_solicitadas} etapas. "
                       f"Permitido: {etapas_permitidas}. Justificativa: {justificativa[:50]}...")
            return etapas_permitidas

    return max_default


def get_max_historico() -> int:
    """Retorna limite de histórico baseado na config."""
    return get_config().memoria.max_mensagens_default


def get_max_tokens(modelo: str = "sonnet") -> int:
    """
    Retorna limite de tokens baseado no modelo.

    Args:
        modelo: Nome do modelo (haiku, sonnet, opus)

    Returns:
        Número máximo de tokens para contexto
    """
    config = get_config()
    if config.memoria.ajustar_por_modelo:
        return config.memoria.tokens_por_modelo.get(modelo, config.memoria.max_tokens_contexto)
    return config.memoria.max_tokens_contexto


def deve_revisar_resposta(confianca: float = 0.5) -> bool:
    """
    Decide se deve revisar resposta.

    Args:
        confianca: Nível de confiança da resposta (0.0 a 1.0)

    Returns:
        True se deve revisar, False caso contrário
    """
    config = get_config()

    if not config.resposta.revisao_automatica:
        return False

    if config.resposta.revisao_condicional:
        # Alta confiança = não precisa revisar
        return confianca < config.resposta.limiar_confianca_sem_revisao

    return True


def usar_schema_dinamico() -> bool:
    """Retorna se deve usar schema dinâmico."""
    return get_config().ferramentas.schema_dinamico


def usar_capabilities_dinamicas() -> bool:
    """Retorna se deve carregar capabilities dinamicamente."""
    return get_config().extracao.carregar_capabilities_dinamicamente
