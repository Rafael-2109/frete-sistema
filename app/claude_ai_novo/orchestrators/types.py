"""
🎭 ORCHESTRATOR TYPES - Tipos Compartilhados dos Orquestradores
=============================================================

Tipos e enums compartilhados entre os orquestradores.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional

class OrchestrationMode(Enum):
    """Modos de orquestração disponíveis."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    INTELLIGENT = "intelligent"
    PRIORITY_BASED = "priority_based"
    ADAPTIVE = "adaptive"

class OrchestratorType(Enum):
    """Tipos de orquestradores disponíveis."""
    MAIN = "main"
    SESSION = "session" 
    WORKFLOW = "workflow"

@dataclass
class OrchestrationStep:
    """Definição de um passo de orquestração"""
    name: str
    component: str
    method: str
    parameters: Optional[Dict[str, Any]] = None
    dependencies: Optional[List[str]] = None
    timeout: int = 30

@dataclass
class OrchestrationTask:
    """Task de orquestração com metadados."""
    task_id: str
    orchestrator_type: OrchestratorType
    operation: str
    parameters: Dict[str, Any]
    priority: int = 1
    timeout: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None

class SessionStatus(Enum):
    """Status possíveis de uma sessão."""
    CREATED = "created"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PROCESSING = "processing"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    TERMINATED = "terminated"

class SessionPriority(Enum):
    """Prioridade de uma sessão."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

# Exports
__all__ = [
    'OrchestrationMode',
    'OrchestratorType',
    'OrchestrationStep',
    'OrchestrationTask',
    'SessionStatus',
    'SessionPriority'
] 