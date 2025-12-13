"""
MemoryRetriever - Recupera memorias relevantes do banco.

Responsabilidade: APENAS recuperar memorias (pre-hook).
NAO detecta padroes - isso eh responsabilidade do PatternDetector.

Tipos de memoria recuperados:
- Profile: dados do usuario
- Semantic: fatos, preferencias
- Procedural: padroes de uso, workflows
- Corrections: correcoes de erros

IMPORTANTE: Memorias com sensitivity=HIGH NUNCA sao recuperadas.
"""

import logging
import asyncio
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """
    Recupera memorias do banco para injecao no contexto.

    Carrega da tabela agent_memories e converte para WorkingSet.
    """

    def __init__(self, app=None):
        self._app = app

    def _get_app(self):
        if self._app:
            return self._app
        from flask import current_app
        return current_app._get_current_object()

    def _parse_xml_safely(self, content: str) -> Dict[str, Any]:
        """Parse XML de memoria para dict."""
        try:
            root = ET.fromstring(content)
            result = {}

            for child in root:
                if len(child) == 0:
                    result[child.tag] = child.text or ''
                else:
                    result[child.tag] = {sub.tag: sub.text or '' for sub in child}

            return result
        except Exception as e:
            logger.warning(f"[MEMORY_RETRIEVER] Erro ao parsear XML: {e}")
            return {'raw': content}

    def _retrieve_sync(
        self,
        user_id: int,
        prompt: str = "",
    ) -> Dict[str, Any]:
        """
        Recupera memorias do banco (sync).

        Returns:
            Dict com working_set, raw_memories e count
        """
        from ..models import AgentMemory
        from .manager import WorkingSet, MemorySensitivity

        app = self._get_app()
        working_set = WorkingSet()
        raw_memories = {}
        count = 0

        with app.app_context():
            # Busca todas as memorias do usuario (exceto HIGH sensitivity)
            memories = AgentMemory.query.filter_by(
                user_id=user_id,
                is_directory=False,
            ).all()

            for memory in memories:
                path = memory.path
                content = memory.content or ''
                raw_memories[path] = content

                # Skip se marcado como HIGH sensitivity no conteudo
                if 'sensitivity>high<' in content.lower():
                    continue

                parsed = self._parse_xml_safely(content)
                count += 1

                # Classifica por path
                if '/memories/user' in path:
                    working_set.profile = parsed
                elif '/memories/preferences' in path:
                    working_set.semantic.append({
                        'type': 'preference',
                        'path': path,
                        'content': content,
                        'summary': parsed.get('communication', '')[:100],
                        **parsed,
                    })
                elif '/memories/context/' in path:
                    working_set.semantic.append({
                        'type': 'context',
                        'path': path,
                        'content': content,
                        **parsed,
                    })
                elif '/memories/learned/patterns' in path:
                    # Patterns sao procedurais
                    working_set.procedural.append({
                        'type': 'pattern',
                        'path': path,
                        'description': parsed.get('description', content[:100]),
                        **parsed,
                    })
                elif '/memories/learned/' in path:
                    working_set.semantic.append({
                        'type': 'learned',
                        'path': path,
                        **parsed,
                    })
                elif '/memories/corrections/' in path:
                    working_set.corrections.append({
                        'path': path,
                        **parsed,
                    })

            working_set.version += 1

        return {
            'working_set': working_set,
            'raw_memories': raw_memories,
            'count': count,
        }

    async def retrieve(
        self,
        user_id: int,
        prompt: str = "",
        existing_working_set: Optional['WorkingSet'] = None,
    ) -> Dict[str, Any]:
        """
        Recupera memorias relevantes para o prompt.

        Args:
            user_id: ID do usuario
            prompt: Prompt atual (para relevancia futura)
            existing_working_set: Working set existente para incrementar

        Returns:
            Dict com working_set, raw_memories e count
        """
        # Executa sync em thread separada
        result = await asyncio.to_thread(
            self._retrieve_sync,
            user_id,
            prompt,
        )

        # Se temos working_set existente, mescla
        if existing_working_set:
            # Merge recent_entities
            new_ws = result['working_set']
            new_ws.recent_entities = list(set(
                existing_working_set.recent_entities +
                new_ws.recent_entities
            ))[:10]  # Limite

        logger.debug(
            f"[MEMORY_RETRIEVER] user={user_id} "
            f"retrieved={result['count']} memories"
        )

        return result
