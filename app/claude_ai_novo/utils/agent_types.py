"""
🤖 AGENT TYPES - Tipos e Enums dos Agentes Multi-Agent

Define tipos básicos e enumerações usadas pelo sistema multi-agente.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


class AgentType(Enum):
    """Tipos de agentes especializados"""
    ENTREGAS = "entregas"
    FRETES = "fretes" 
    PEDIDOS = "pedidos"
    EMBARQUES = "embarques"
    FINANCEIRO = "financeiro"
    CRITIC = "critic"
    VALIDATOR = "validator"


@dataclass
class AgentResponse:
    """Resposta padronizada de um agente"""
    agent: str
    relevance: float
    response: Optional[str]
    confidence: float
    timestamp: str
    reasoning: str
    error: Optional[str] = None


@dataclass
class ValidationResult:
    """Resultado de validação cruzada"""
    validation_score: float
    inconsistencies: List[str]
    recommendations: List[str]
    approval: bool
    cross_validation: Dict[str, Any]


@dataclass
class OperationRecord:
    """Registro de operação do sistema multi-agente"""
    operation_id: str
    query: str
    timestamp: str
    duration_seconds: float
    agent_responses: List[Dict[str, Any]]
    validation: ValidationResult
    final_response: str
    success: bool


# Exportações principais
__all__ = [
    'AgentType',
    'AgentResponse', 
    'ValidationResult',
    'OperationRecord'
] 