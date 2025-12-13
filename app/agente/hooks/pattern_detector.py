"""
PatternDetector - Detecta padroes e preferencias nas interacoes.

Responsabilidade: Analisa interacoes e gera candidatos a memoria.
NAO persiste - isso eh responsabilidade do MemoryWriter apos WritePolicy.

Padroes detectados:
- Preferencias de comunicacao ("seja mais direto")
- Correcoes ("nao eh assim, eh X")
- Padroes de uso (sempre pergunta sobre X primeiro)
- Fatos sobre o usuario (cargo, clientes)

Deteccao eh baseada em:
- Keywords no prompt
- Frequencia de queries similares
- Feedback do usuario
"""

import logging
import re
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# Patterns para detectar tipos de informacao
PREFERENCE_PATTERNS = [
    (re.compile(r'prefiro?\s+(respostas?\s+)?(curtas?|diretas?|resumidas?)', re.I),
     'communication', 'direto e objetivo'),
    (re.compile(r'prefiro?\s+(respostas?\s+)?(longas?|detalhadas?|completas?)', re.I),
     'communication', 'detalhado'),
    (re.compile(r'(pode|quero)\s+(ser\s+)?(mais\s+)?(direto|resumido|curto)', re.I),
     'communication', 'direto e objetivo'),
    (re.compile(r'(pode|quero)\s+(ser\s+)?(mais\s+)?(detalhado|completo)', re.I),
     'communication', 'detalhado'),
    (re.compile(r'n[aã]o\s+(precis[ao]|quero)\s+(de\s+)?(tanto\s+)?detalhe', re.I),
     'communication', 'direto e objetivo'),
]

CORRECTION_PATTERNS = [
    (re.compile(r'n[aã]o\s+[eé]\s+assim', re.I), 'correction'),
    (re.compile(r'n[aã]o\s+[eé]\s+isso', re.I), 'correction'),
    (re.compile(r'est[aá]\s+errado', re.I), 'correction'),
    (re.compile(r'o\s+correto\s+[eé]', re.I), 'correction'),
    (re.compile(r'aqui\s+(chamamos|usamos|dizemos)', re.I), 'correction'),
    (re.compile(r'esse\s+campo\s+se\s+chama', re.I), 'correction'),
]

FACT_PATTERNS = [
    (re.compile(r'(sou|eu\s+sou)\s+(o\s+)?(gerente|dono|diretor|analista|coordenador)', re.I), 'role'),
    (re.compile(r'meu\s+nome\s+[eé]', re.I), 'name'),
    (re.compile(r'trabalho\s+(com|no|na|em)', re.I), 'work'),
    (re.compile(r'cuido\s+(de|do|da|dos|das)', re.I), 'responsibility'),
]


class PatternDetector:
    """
    Detecta padroes nas interacoes e gera candidatos a memoria.
    """

    def __init__(self, app=None):
        self._app = app

    def _get_app(self):
        if self._app:
            return self._app
        from flask import current_app
        return current_app._get_current_object()

    def _detect_preferences(
        self,
        prompt: str,
    ) -> List['MemoryCandidate']:
        """Detecta preferencias de comunicacao."""
        from .manager import MemoryCandidate, MemoryScope, MemorySensitivity

        candidates = []

        for pattern, pref_type, value in PREFERENCE_PATTERNS:
            if pattern.search(prompt):
                candidates.append(MemoryCandidate(
                    path=f'/memories/preferences.xml',
                    value_json={
                        'type': pref_type,
                        'value': value,
                        'detected_at': datetime.now(timezone.utc).isoformat(),
                    },
                    summary=f"Preferencia: {value}",
                    memory_type='preference',
                    scope=MemoryScope.USER,
                    sensitivity=MemorySensitivity.LOW,
                    confidence=0.8,  # Alta confianca - usuario disse explicitamente
                    evidence=[prompt[:200]],
                    source_prompt=prompt[:500],
                ))
                break  # Uma preferencia por vez

        return candidates

    def _detect_corrections(
        self,
        prompt: str,
        response: str,
    ) -> List['MemoryCandidate']:
        """Detecta correcoes do usuario."""
        from .manager import MemoryCandidate, MemoryScope, MemorySensitivity

        candidates = []

        for pattern, _ in CORRECTION_PATTERNS:
            if pattern.search(prompt):
                candidates.append(MemoryCandidate(
                    path=f'/memories/corrections/correction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xml',
                    value_json={
                        'context': prompt[:300],
                        'detected_at': datetime.now(timezone.utc).isoformat(),
                    },
                    summary=f"Correcao: {prompt[:100]}",
                    memory_type='correction',
                    scope=MemoryScope.USER,
                    sensitivity=MemorySensitivity.LOW,
                    confidence=0.7,
                    evidence=[prompt[:200]],
                    source_prompt=prompt[:500],
                    source_response=response[:500],
                ))
                break

        return candidates

    def _detect_facts(
        self,
        prompt: str,
    ) -> List['MemoryCandidate']:
        """Detecta fatos sobre o usuario."""
        from .manager import MemoryCandidate, MemoryScope, MemorySensitivity

        candidates = []

        for pattern, fact_type in FACT_PATTERNS:
            match = pattern.search(prompt)
            if match:
                candidates.append(MemoryCandidate(
                    path=f'/memories/context/{fact_type}.xml',
                    value_json={
                        'type': fact_type,
                        'context': prompt[:300],
                        'detected_at': datetime.now(timezone.utc).isoformat(),
                    },
                    summary=f"Fato ({fact_type}): {prompt[:100]}",
                    memory_type='fact',
                    scope=MemoryScope.USER,
                    sensitivity=MemorySensitivity.MEDIUM,  # Dados pessoais
                    confidence=0.6,
                    evidence=[prompt[:200]],
                    source_prompt=prompt[:500],
                ))

        return candidates

    def _detect_procedural_patterns(
        self,
        query_history: List[Dict[str, Any]],
        tools_used: List[str],
    ) -> List['MemoryCandidate']:
        """Detecta padroes procedurais de uso."""
        from .manager import MemoryCandidate, MemoryScope, MemorySensitivity

        candidates = []

        # Detecta se usuario sempre pergunta sobre mesmo assunto primeiro
        if len(query_history) >= 3:
            first_queries = [q['prompt'].lower() for q in query_history[:3]]

            # Verifica keywords comuns
            common_keywords = {}
            for query in first_queries:
                words = set(re.findall(r'\b\w{4,}\b', query))
                for word in words:
                    common_keywords[word] = common_keywords.get(word, 0) + 1

            # Se uma keyword aparece em 2+ das primeiras queries
            for word, count in common_keywords.items():
                if count >= 2 and word not in ['voce', 'como', 'qual', 'quero', 'preciso']:
                    candidates.append(MemoryCandidate(
                        path=f'/memories/learned/patterns.xml',
                        value_json={
                            'pattern_type': 'frequent_topic',
                            'keyword': word,
                            'frequency': count,
                            'detected_at': datetime.now(timezone.utc).isoformat(),
                        },
                        summary=f"Usuario frequentemente pergunta sobre: {word}",
                        memory_type='procedural',
                        scope=MemoryScope.USER,
                        sensitivity=MemorySensitivity.LOW,
                        confidence=0.5,  # Menor confianca - precisa mais evidencia
                        evidence=[q['prompt'][:100] for q in query_history[:3]],
                        evidence_count=count,
                    ))
                    break  # Um padrao por vez

        return candidates

    async def analyze(
        self,
        user_id: int,
        user_prompt: str,
        assistant_response: str,
        tools_used: List[str],
        tool_errors: List[Dict[str, Any]],
        query_history: List[Dict[str, Any]],
    ) -> List['MemoryCandidate']:
        """
        Analisa interacao e detecta padroes.

        Returns:
            Lista de candidatos a memoria
        """
        candidates = []

        # Detecta preferencias
        candidates.extend(self._detect_preferences(user_prompt))

        # Detecta correcoes
        candidates.extend(self._detect_corrections(user_prompt, assistant_response))

        # Detecta fatos
        candidates.extend(self._detect_facts(user_prompt))

        # Detecta padroes procedurais
        candidates.extend(self._detect_procedural_patterns(query_history, tools_used))

        logger.debug(
            f"[PATTERN_DETECTOR] user={user_id} "
            f"candidates={len(candidates)}"
        )

        return candidates
