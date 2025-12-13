"""
MemoryWriter - Persiste memorias aprovadas no banco.

Responsabilidade: Salvar na tabela agent_memories.
Recebe apenas candidatos JA APROVADOS pelo WritePolicy.

Formato de persistencia:
- path: chave unica por usuario
- content: XML estruturado (para compatibilidade com skill existente)
- metadata: JSON com confidence, evidence, timestamps
"""

import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MemoryWriter:
    """
    Persiste memorias aprovadas no banco.
    """

    def __init__(self, app=None):
        self._app = app

    def _get_app(self):
        if self._app:
            return self._app
        from flask import current_app
        return current_app._get_current_object()

    def _candidate_to_xml(self, candidate: 'MemoryCandidate') -> str:
        """Converte candidato para formato XML."""
        lines = [f'<{candidate.memory_type}>']

        # Adiciona campos do value_json
        for key, value in candidate.value_json.items():
            if isinstance(value, (list, dict)):
                continue  # Pula tipos complexos
            lines.append(f'  <{key}>{value}</{key}>')

        # Adiciona metadata
        lines.append(f'  <summary>{candidate.summary}</summary>')
        lines.append(f'  <confidence>{candidate.confidence}</confidence>')
        lines.append(f'  <sensitivity>{candidate.sensitivity.value}</sensitivity>')
        lines.append(f'  <evidence_count>{candidate.evidence_count}</evidence_count>')
        lines.append(f'  <updated_at>{datetime.now(timezone.utc).isoformat()}</updated_at>')

        if candidate.tags:
            lines.append(f'  <tags>{",".join(candidate.tags)}</tags>')

        lines.append(f'</{candidate.memory_type}>')

        return '\n'.join(lines)

    def _persist_sync(
        self,
        user_id: int,
        candidates: List['MemoryCandidate'],
    ) -> List[Dict[str, Any]]:
        """
        Persiste candidatos no banco (sync).

        Returns:
            Lista de memorias salvas
        """
        from ..models import AgentMemory
        from app import db

        app = self._get_app()
        saved = []

        with app.app_context():
            for candidate in candidates:
                try:
                    # Converte para XML
                    content = self._candidate_to_xml(candidate)

                    # Verifica se ja existe
                    existing = AgentMemory.get_by_path(user_id, candidate.path)

                    if existing:
                        # Atualiza existente
                        existing.content = content
                        existing.is_directory = False
                    else:
                        # Cria novo
                        AgentMemory.create_file(user_id, candidate.path, content)

                    saved.append({
                        'path': candidate.path,
                        'type': candidate.memory_type,
                        'action': 'updated' if existing else 'created',
                    })

                except Exception as e:
                    logger.error(
                        f"[MEMORY_WRITER] Erro ao salvar {candidate.path}: {e}"
                    )

            db.session.commit()

        return saved

    async def persist(
        self,
        user_id: int,
        candidates: List['MemoryCandidate'],
    ) -> List[Dict[str, Any]]:
        """
        Persiste candidatos aprovados no banco.

        Args:
            user_id: ID do usuario
            candidates: Lista de candidatos aprovados

        Returns:
            Lista de memorias salvas com status
        """
        if not candidates:
            return []

        # Executa sync em thread separada
        saved = await asyncio.to_thread(
            self._persist_sync,
            user_id,
            candidates,
        )

        logger.info(
            f"[MEMORY_WRITER] user={user_id} "
            f"saved={len(saved)} memories"
        )

        return saved
