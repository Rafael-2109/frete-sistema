"""
Rastreador de Custos do Agente.

Implementa rastreamento de custos conforme documentação:
https://platform.claude.com/docs/agent-sdk/cost-tracking

Recursos:
- Deduplica por message.id
- Usa total_cost_usd no result final
- Métricas por sessão e usuário
- Alertas de custo
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


@dataclass
class CostEntry:
    """Entrada de custo individual."""

    message_id: str
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    cost_usd: float
    tool_name: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'message_id': self.message_id,
            'timestamp': self.timestamp.isoformat(),
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'cost_usd': self.cost_usd,
            'tool_name': self.tool_name,
            'session_id': self.session_id,
            'user_id': self.user_id,
        }


@dataclass
class CostSummary:
    """Resumo de custos."""

    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    by_tool: Dict[str, float] = field(default_factory=dict)
    by_user: Dict[int, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_requests': self.total_requests,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_cost_usd': round(self.total_cost_usd, 4),
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'by_tool': {k: round(v, 4) for k, v in self.by_tool.items()},
            'by_user': {k: round(v, 4) for k, v in self.by_user.items()},
        }


class CostTracker:
    """
    Rastreador de custos com deduplicação.

    Implementa o padrão da documentação Anthropic:
    - Deduplica por message.id para evitar contagem dupla
    - Rastreia custos por sessão, usuário e ferramenta
    - Emite alertas quando limites são excedidos

    Uso:
        tracker = CostTracker()

        # Registra custo
        tracker.record_cost(
            message_id="msg_123",
            input_tokens=1000,
            output_tokens=500,
            session_id="session_abc",
            user_id=1
        )

        # Obtém resumo
        summary = tracker.get_summary(user_id=1)
    """

    def __init__(self):
        from ..config import get_settings

        self.settings = get_settings()

        # Armazenamento em memória (pode ser movido para Redis/DB)
        self._entries: List[CostEntry] = []
        self._seen_message_ids: set = set()

        # Acumuladores por sessão
        self._session_costs: Dict[str, float] = defaultdict(float)

        # Acumuladores por usuário
        self._user_costs: Dict[int, float] = defaultdict(float)

        logger.info("[COST_TRACKER] Inicializado")

    def record_cost(
        self,
        message_id: str,
        input_tokens: int,
        output_tokens: int,
        session_id: str = None,
        user_id: int = None,
        tool_name: str = None,
    ) -> Optional[CostEntry]:
        """
        Registra custo de uma requisição.

        Deduplica por message_id para evitar contagem dupla
        em casos de retry ou streaming.

        Args:
            message_id: ID único da mensagem (do response Anthropic)
            input_tokens: Tokens de entrada
            output_tokens: Tokens de saída
            session_id: ID da sessão
            user_id: ID do usuário
            tool_name: Nome da ferramenta (se aplicável)

        Returns:
            CostEntry se registrado, None se duplicado
        """
        # Deduplica
        if message_id in self._seen_message_ids:
            logger.debug(f"[COST_TRACKER] Duplicado ignorado: {message_id}")
            return None

        self._seen_message_ids.add(message_id)

        # Calcula custo
        cost_usd = self.settings.calculate_cost(input_tokens, output_tokens)

        # Cria entrada
        entry = CostEntry(
            message_id=message_id,
            timestamp=agora_utc_naive(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            tool_name=tool_name,
            session_id=session_id,
            user_id=user_id,
        )

        self._entries.append(entry)

        # Atualiza acumuladores
        if session_id:
            self._session_costs[session_id] += cost_usd
            self._check_session_alert(session_id)

        if user_id:
            self._user_costs[user_id] += cost_usd

        logger.info(
            f"[COST_TRACKER] Registrado: ${cost_usd:.4f} "
            f"(in={input_tokens}, out={output_tokens}) "
            f"session={session_id}"
        )

        return entry

    def _check_session_alert(self, session_id: str) -> None:
        """Verifica se sessão excedeu limite de custo."""
        session_cost = self._session_costs.get(session_id, 0)

        if session_cost >= self.settings.cost_alert_threshold_usd:
            logger.warning(
                f"[COST_TRACKER] ALERTA: Sessão {session_id} "
                f"excedeu limite de ${self.settings.cost_alert_threshold_usd:.2f} "
                f"(atual: ${session_cost:.4f})"
            )

    def get_session_cost(self, session_id: str) -> float:
        """Obtém custo total de uma sessão."""
        return self._session_costs.get(session_id, 0.0)

    def get_user_cost(self, user_id: int) -> float:
        """Obtém custo total de um usuário."""
        return self._user_costs.get(user_id, 0.0)

    def get_summary(
        self,
        session_id: str = None,
        user_id: int = None,
        since: datetime = None,
        until: datetime = None,
    ) -> CostSummary:
        """
        Obtém resumo de custos.

        Args:
            session_id: Filtrar por sessão
            user_id: Filtrar por usuário
            since: Data inicial
            until: Data final

        Returns:
            CostSummary com métricas agregadas
        """
        # Filtra entradas
        filtered = self._entries

        if session_id:
            filtered = [e for e in filtered if e.session_id == session_id]

        if user_id:
            filtered = [e for e in filtered if e.user_id == user_id]

        if since:
            filtered = [e for e in filtered if e.timestamp >= since]

        if until:
            filtered = [e for e in filtered if e.timestamp <= until]

        # Agrega
        summary = CostSummary(
            total_requests=len(filtered),
            total_input_tokens=sum(e.input_tokens for e in filtered),
            total_output_tokens=sum(e.output_tokens for e in filtered),
            total_cost_usd=sum(e.cost_usd for e in filtered),
        )

        if filtered:
            summary.period_start = min(e.timestamp for e in filtered)
            summary.period_end = max(e.timestamp for e in filtered)

        # Por ferramenta
        by_tool = defaultdict(float)
        for e in filtered:
            if e.tool_name:
                by_tool[e.tool_name] += e.cost_usd
        summary.by_tool = dict(by_tool)

        # Por usuário
        by_user = defaultdict(float)
        for e in filtered:
            if e.user_id:
                by_user[e.user_id] += e.cost_usd
        summary.by_user = dict(by_user)

        return summary

    def get_daily_summary(self, date: datetime = None) -> CostSummary:
        """Obtém resumo do dia."""
        if date is None:
            date = agora_utc_naive()

        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        return self.get_summary(since=start, until=end)

    def clear_old_entries(self, days: int = 7) -> int:
        """
        Remove entradas antigas.

        Args:
            days: Manter últimos N dias

        Returns:
            Número de entradas removidas
        """
        cutoff = agora_utc_naive() - timedelta(days=days)
        original_count = len(self._entries)

        self._entries = [e for e in self._entries if e.timestamp >= cutoff]

        # Limpa message_ids antigos (mantém set gerenciável)
        if len(self._seen_message_ids) > 10000:
            recent_ids = {e.message_id for e in self._entries}
            self._seen_message_ids = recent_ids

        removed = original_count - len(self._entries)
        if removed > 0:
            logger.info(f"[COST_TRACKER] {removed} entradas antigas removidas")

        return removed


# Singleton do tracker
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """
    Obtém instância do rastreador de custos (singleton).

    Returns:
        Instância de CostTracker
    """
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
