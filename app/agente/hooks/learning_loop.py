"""
LearningLoop - Sistema de feedback do usuario.

Responsabilidade: Coletar e processar feedback para ajustar memorias.
O feedback serve como evidence adicional para:
- Aumentar/diminuir confidence de memorias existentes
- Validar candidatos pendentes
- Detectar preferencias implicitas

Tipos de feedback:
- positive: Resposta foi util
- negative: Resposta nao foi util
- correction: Usuario corrigiu algo
- preference: Usuario expressou preferencia
"""

import logging
import asyncio
from typing import Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# Configuracao de quando pedir feedback
FEEDBACK_INTERVAL_QUERIES = 5     # Pede a cada N queries
FEEDBACK_MIN_RESPONSE_LENGTH = 500  # So pede se resposta for longa
FEEDBACK_AFTER_ERROR = True        # Pede apos erro de tool


class LearningLoop:
    """
    Gerencia coleta e processamento de feedback.
    """

    def __init__(self, app=None):
        self._app = app
        self._feedback_counter: Dict[int, int] = {}  # user_id -> count

    def _get_app(self):
        if self._app:
            return self._app
        from flask import current_app
        return current_app._get_current_object()

    async def should_request_feedback(
        self,
        user_id: int,
        query_count: int,
        response_length: int,
        has_tool_errors: bool = False,
    ) -> bool:
        """
        Decide se deve pedir feedback ao usuario.

        Returns:
            True se deve pedir feedback
        """
        # Sempre pede apos erro de tool
        if has_tool_errors and FEEDBACK_AFTER_ERROR:
            return True

        # Pede a cada N queries
        if query_count > 0 and query_count % FEEDBACK_INTERVAL_QUERIES == 0:
            # Mas so se resposta foi longa (indica interacao complexa)
            if response_length >= FEEDBACK_MIN_RESPONSE_LENGTH:
                return True

        return False

    async def process_feedback(
        self,
        user_id: int,
        feedback_type: str,
        feedback_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Processa feedback do usuario.

        Args:
            user_id: ID do usuario
            feedback_type: Tipo do feedback (positive, negative, correction, preference)
            feedback_data: Dados do feedback

        Returns:
            Dict com resultado do processamento
        """
        from .manager import MemoryCandidate, MemoryScope, MemorySensitivity

        result = {
            'processed': False,
            'action': None,
            'memory_path': None,
        }

        try:
            if feedback_type == 'positive':
                # Feedback positivo pode aumentar confidence de memorias usadas
                result['action'] = 'confidence_boost'
                result['processed'] = True

            elif feedback_type == 'negative':
                # Feedback negativo pode diminuir confidence
                result['action'] = 'confidence_decrease'
                result['processed'] = True

            elif feedback_type == 'correction':
                # Correcao gera nova memoria
                from .memory_writer import MemoryWriter

                correction_text = feedback_data.get('correction', '')
                if correction_text:
                    candidate = MemoryCandidate(
                        path=f'/memories/corrections/feedback_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xml',
                        value_json={
                            'correction': correction_text,
                            'context': feedback_data.get('context', ''),
                            'source': 'user_feedback',
                        },
                        summary=f"Correcao do usuario: {correction_text[:100]}",
                        memory_type='correction',
                        scope=MemoryScope.USER,
                        sensitivity=MemorySensitivity.LOW,
                        confidence=0.9,  # Alta confianca - usuario disse explicitamente
                        evidence=[f"Feedback direto: {correction_text[:200]}"],
                    )

                    writer = MemoryWriter(self._app)
                    saved = await writer.persist(user_id, [candidate])

                    result['action'] = 'correction_saved'
                    result['memory_path'] = candidate.path
                    result['processed'] = True

            elif feedback_type == 'preference':
                # Preferencia gera/atualiza memoria
                from .memory_writer import MemoryWriter

                pref_key = feedback_data.get('key', 'general')
                pref_value = feedback_data.get('value', '')

                if pref_value:
                    candidate = MemoryCandidate(
                        path='/memories/preferences.xml',
                        value_json={
                            pref_key: pref_value,
                            'source': 'user_feedback',
                        },
                        summary=f"Preferencia: {pref_key}={pref_value}",
                        memory_type='preference',
                        scope=MemoryScope.USER,
                        sensitivity=MemorySensitivity.LOW,
                        confidence=0.95,  # Muito alta - usuario disse explicitamente
                        evidence=[f"Feedback direto: {pref_key}={pref_value}"],
                    )

                    writer = MemoryWriter(self._app)
                    saved = await writer.persist(user_id, [candidate])

                    result['action'] = 'preference_saved'
                    result['memory_path'] = candidate.path
                    result['processed'] = True

        except Exception as e:
            logger.error(f"[LEARNING_LOOP] Erro ao processar feedback: {e}")
            result['error'] = str(e)

        return result
