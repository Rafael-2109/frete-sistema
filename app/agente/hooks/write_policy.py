"""
MemoryWritePolicy - Avalia candidatos a memoria antes de persistir.

Responsabilidade: Decidir quais candidatos podem ser salvos.
Separa "detectar" de "persistir" para evitar gravar ruido.

Criterios de aprovacao:
- Confidence minima (threshold)
- Evidence count minimo
- NAO duplica memorias existentes
- BLOQUEIA sensitivity=HIGH de ir para memoria recuperavel
- TTL e retention policy

Modos:
- Normal: threshold padrao (0.7)
- End of session: threshold mais baixo (0.5)
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


# Thresholds
NORMAL_CONFIDENCE_THRESHOLD = 0.7
SESSION_END_CONFIDENCE_THRESHOLD = 0.5
MIN_EVIDENCE_COUNT = 1


class MemoryWritePolicy:
    """
    Avalia candidatos a memoria e decide quais aprovar.
    """

    def __init__(self, app=None):
        self._app = app

    def _get_app(self):
        if self._app:
            return self._app
        from flask import current_app
        return current_app._get_current_object()

    def _is_duplicate(
        self,
        candidate: 'MemoryCandidate',
        existing_memories: Dict[str, Any],
    ) -> bool:
        """Verifica se candidato duplica memoria existente."""
        # Verifica por path exato
        if candidate.path in existing_memories:
            # Permite atualizar se for mesmo tipo
            return False  # Nao eh duplicata, pode atualizar

        # Verifica por summary similar
        for path, content in existing_memories.items():
            if candidate.summary.lower() in content.lower():
                return True

        return False

    def _should_block_sensitivity(
        self,
        candidate: 'MemoryCandidate',
    ) -> bool:
        """
        Verifica se deve bloquear por sensitivity.

        HIGH sensitivity NUNCA pode ir para memoria recuperavel.
        """
        from .manager import MemorySensitivity

        if candidate.sensitivity == MemorySensitivity.HIGH:
            logger.warning(
                f"[WRITE_POLICY] Bloqueando candidate HIGH sensitivity: {candidate.path}"
            )
            return True

        return False

    async def evaluate(
        self,
        candidates: List['MemoryCandidate'],
        existing_memories: Dict[str, Any],
        end_of_session: bool = False,
    ) -> List['MemoryCandidate']:
        """
        Avalia candidatos e retorna os aprovados.

        Args:
            candidates: Lista de candidatos
            existing_memories: Memorias existentes (para dedup)
            end_of_session: Se eh final de sessao (threshold mais baixo)

        Returns:
            Lista de candidatos aprovados
        """
        threshold = SESSION_END_CONFIDENCE_THRESHOLD if end_of_session else NORMAL_CONFIDENCE_THRESHOLD

        approved = []

        for candidate in candidates:
            # 1. Bloqueia HIGH sensitivity
            if self._should_block_sensitivity(candidate):
                continue

            # 2. Verifica confidence
            if candidate.confidence < threshold:
                logger.debug(
                    f"[WRITE_POLICY] Rejeitado (confidence {candidate.confidence} < {threshold}): "
                    f"{candidate.path}"
                )
                continue

            # 3. Verifica evidence count
            if candidate.evidence_count < MIN_EVIDENCE_COUNT:
                logger.debug(
                    f"[WRITE_POLICY] Rejeitado (evidence {candidate.evidence_count} < {MIN_EVIDENCE_COUNT}): "
                    f"{candidate.path}"
                )
                continue

            # 4. Verifica duplicata
            if self._is_duplicate(candidate, existing_memories):
                logger.debug(
                    f"[WRITE_POLICY] Rejeitado (duplicata): {candidate.path}"
                )
                continue

            # Aprovado!
            approved.append(candidate)
            logger.info(
                f"[WRITE_POLICY] Aprovado (confidence={candidate.confidence}): "
                f"{candidate.path}"
            )

        logger.debug(
            f"[WRITE_POLICY] {len(approved)}/{len(candidates)} candidatos aprovados "
            f"(threshold={threshold})"
        )

        return approved
