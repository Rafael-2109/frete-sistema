"""
EventLogger - Instrumentacao first-class para ML e Analytics.

Grava eventos append-only na tabela agent_events para:
- Dataset de treinamento
- Analytics de uso
- Debugging
- Auditoria

Eventos gravados:
- session_start / session_end
- pre_query / post_response
- tool_call / tool_result / tool_error
- memory_retrieved / memory_candidate / memory_saved
- feedback_received
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class EventLogger:
    """
    Logger de eventos para instrumentacao.

    Grava na tabela agent_events (append-only).
    """

    def __init__(self, app=None):
        """
        Inicializa o EventLogger.

        Args:
            app: Flask app (opcional)
        """
        self._app = app
        self._buffer = []  # Buffer para batch inserts
        self._buffer_size = 10  # Flush a cada N eventos

    def _get_app(self):
        """Obtem Flask app."""
        if self._app:
            return self._app
        from flask import current_app
        return current_app._get_current_object()

    async def log(
        self,
        event_type: str,
        user_id: int,
        session_id: str,
        data: Dict[str, Any] = None,
    ) -> None:
        """
        Loga um evento.

        Args:
            event_type: Tipo do evento (EventType enum value)
            user_id: ID do usuario
            session_id: ID da sessao
            data: Dados adicionais do evento
        """
        event = {
            'event_type': str(event_type.value) if hasattr(event_type, 'value') else str(event_type),
            'user_id': user_id,
            'session_id': session_id,
            'data': data or {},
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

        self._buffer.append(event)

        # Flush se buffer cheio
        if len(self._buffer) >= self._buffer_size:
            await self._flush()

    async def _flush(self) -> None:
        """Persiste buffer de eventos no DB."""
        if not self._buffer:
            return

        events_to_save = self._buffer.copy()
        self._buffer.clear()

        try:
            from ..models import AgentEvent
            from app import db

            app = self._get_app()

            with app.app_context():
                for event in events_to_save:
                    db_event = AgentEvent(
                        event_type=event['event_type'],
                        user_id=event['user_id'],
                        session_id=event['session_id'],
                        data=event['data'],
                    )
                    db.session.add(db_event)

                db.session.commit()
                logger.debug(f"[EVENT_LOGGER] {len(events_to_save)} eventos salvos")

        except Exception as e:
            logger.error(f"[EVENT_LOGGER] Erro ao salvar eventos: {e}")
            # Recoloca no buffer para tentar novamente
            self._buffer.extend(events_to_save)

    async def flush(self) -> None:
        """Flush publico para garantir persistencia."""
        await self._flush()

    def get_events_sync(
        self,
        user_id: int,
        session_id: str = None,
        event_type: str = None,
        limit: int = 100,
    ) -> list:
        """
        Busca eventos (sincrono, para analytics).

        Args:
            user_id: ID do usuario
            session_id: Filtro por sessao (opcional)
            event_type: Filtro por tipo (opcional)
            limit: Limite de resultados

        Returns:
            Lista de eventos
        """
        try:
            from ..models import AgentEvent
            app = self._get_app()

            with app.app_context():
                query = AgentEvent.query.filter_by(user_id=user_id)

                if session_id:
                    query = query.filter_by(session_id=session_id)

                if event_type:
                    query = query.filter_by(event_type=event_type)

                events = query.order_by(AgentEvent.created_at.desc()).limit(limit).all()

                return [e.to_dict() for e in events]

        except Exception as e:
            logger.error(f"[EVENT_LOGGER] Erro ao buscar eventos: {e}")
            return []
