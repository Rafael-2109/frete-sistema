"""
HookManager - Gerenciador central de hooks do Agent SDK.

ARQUITETURA ROBUSTA (Multi-worker, DB como fonte de verdade):

1. _contexts eh cache local - DB (agent_events) eh fonte de verdade
2. Lock distribuido via pg_advisory_xact_lock (multi-worker safe)
3. Separacao clara: MemoryRetriever (pre) vs PatternDetector (post)
4. working_set estruturado, nao string livre
5. Write Policy explicito: detectar -> avaliar -> persistir
6. Instrumentacao first-class via agent_events
7. asyncio.to_thread() para operacoes sync de DB
8. Scrubbing de dados sensiveis

Uso:
    from app.agente.hooks import get_hook_manager

    manager = get_hook_manager()
    context = await manager.on_session_start(user_id, session_id)
    result = await manager.on_pre_query(user_id, session_id, prompt)
    await manager.on_post_response(user_id, session_id, prompt, response, tools)
"""

import logging
import asyncio
import re
import hashlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS E CONSTANTES
# =============================================================================

class MemoryScope(str, Enum):
    """Escopo da memoria."""
    GLOBAL = "global"      # Aplica a todos os usuarios
    ORG = "org"            # Aplica a organizacao
    USER = "user"          # Especifico do usuario


class MemorySensitivity(str, Enum):
    """Sensibilidade da memoria."""
    LOW = "low"            # Pode ser recuperada livremente
    MEDIUM = "medium"      # Requer contexto relevante
    HIGH = "high"          # APENAS telemetria, NUNCA recuperavel


class EventType(str, Enum):
    """Tipos de eventos para instrumentacao."""
    SESSION_START = "session_start"
    PRE_QUERY = "pre_query"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOOL_ERROR = "tool_error"
    POST_RESPONSE = "post_response"
    FEEDBACK_RECEIVED = "feedback_received"
    SESSION_END = "session_end"
    MEMORY_RETRIEVED = "memory_retrieved"
    MEMORY_CANDIDATE = "memory_candidate"
    MEMORY_SAVED = "memory_saved"


# Limites para injecao de contexto
MAX_MEMORIES_PER_TYPE = 5
MAX_CONTEXT_INJECTION_CHARS = 2000
MAX_RECENT_ENTITIES = 10
MAX_PAYLOAD_LOG_SIZE = 500

# Patterns para scrubbing de dados sensiveis
SENSITIVE_PATTERNS = [
    (re.compile(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b'), '[CNPJ]'),  # CNPJ
    (re.compile(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b'), '[CPF]'),  # CPF
    (re.compile(r'senha["\']?\s*[:=]\s*["\']?[^"\'\s,}]+', re.I), 'senha:[REDACTED]'),
    (re.compile(r'password["\']?\s*[:=]\s*["\']?[^"\'\s,}]+', re.I), 'password:[REDACTED]'),
    (re.compile(r'token["\']?\s*[:=]\s*["\']?[^"\'\s,}]+', re.I), 'token:[REDACTED]'),
    (re.compile(r'api_key["\']?\s*[:=]\s*["\']?[^"\'\s,}]+', re.I), 'api_key:[REDACTED]'),
]


def scrub_sensitive_data(text: str) -> str:
    """Remove dados sensiveis de texto."""
    if not text:
        return text
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def truncate_payload(payload: Any, max_size: int = MAX_PAYLOAD_LOG_SIZE) -> str:
    """Trunca e scrub payload para log."""
    text = str(payload)
    text = scrub_sensitive_data(text)
    if len(text) > max_size:
        return text[:max_size] + '...[truncated]'
    return text


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MemoryCandidate:
    """
    Candidato a memoria detectado (ainda nao aprovado).

    Separacao entre detectar e persistir conforme Write Policy.
    """
    path: str                    # Chave/path da memoria
    value_json: Dict[str, Any]   # Payload estruturado (nao string solta)
    summary: str                 # String curta para embeddings/display
    memory_type: str             # preference, pattern, fact, correction, procedural
    scope: MemoryScope = MemoryScope.USER
    sensitivity: MemorySensitivity = MemorySensitivity.LOW
    confidence: float = 0.5      # 0.0 a 1.0
    evidence: List[str] = field(default_factory=list)
    evidence_count: int = 1
    retention_ttl_days: Optional[int] = None  # None = permanente
    is_pinned: bool = False
    tags: List[str] = field(default_factory=list)
    source_prompt: str = ""
    source_response: str = ""


@dataclass
class WorkingSet:
    """
    Conjunto estruturado de memorias recuperadas.

    Substitui string livre por estrutura deterministica.
    """
    # Perfil do usuario
    profile: Dict[str, Any] = field(default_factory=dict)

    # Memorias semanticas (fatos, preferencias)
    semantic: List[Dict[str, Any]] = field(default_factory=list)

    # Memorias procedurais (padroes de uso, workflows)
    procedural: List[Dict[str, Any]] = field(default_factory=list)

    # Entidades recentes mencionadas
    recent_entities: List[str] = field(default_factory=list)

    # Correcoes aplicaveis
    corrections: List[Dict[str, Any]] = field(default_factory=list)

    # Version para tracking
    version: int = 0

    def render(self, max_chars: int = MAX_CONTEXT_INJECTION_CHARS) -> str:
        """
        Renderiza working_set como string para injecao no prompt.

        Limitado e deterministico.
        """
        parts = []

        # Perfil
        if self.profile:
            name = self.profile.get('name', '')
            role = self.profile.get('role', '')
            if name or role:
                parts.append(f"[Usuario: {name}, {role}]" if role else f"[Usuario: {name}]")

        # Preferencias (filtra apenas LOW e MEDIUM sensitivity)
        prefs = [m for m in self.semantic
                 if m.get('type') == 'preference'
                 and m.get('sensitivity', 'low') != 'high'][:MAX_MEMORIES_PER_TYPE]
        if prefs:
            pref_strs = [p.get('summary', p.get('content', ''))[:100] for p in prefs]
            parts.append(f"[Preferencias: {'; '.join(pref_strs)}]")

        # Padroes procedurais (NUNCA inclui HIGH sensitivity)
        safe_procedural = [p for p in self.procedural
                          if p.get('sensitivity', 'low') != 'high'][:MAX_MEMORIES_PER_TYPE]
        if safe_procedural:
            proc_strs = [p.get('description', '')[:100] for p in safe_procedural]
            parts.append(f"[Padroes observados: {'; '.join(proc_strs)}]")

        # Correcoes
        if self.corrections[:3]:
            corr_strs = [f"{c.get('wrong')} -> {c.get('right')}" for c in self.corrections[:3]]
            parts.append(f"[Correcoes: {'; '.join(corr_strs)}]")

        result = "\n".join(parts)

        # Trunca se necessario
        if len(result) > max_chars:
            result = result[:max_chars - 3] + "..."

        return result

    def to_dict(self) -> Dict[str, Any]:
        """Serializa para JSON."""
        return {
            'profile': self.profile,
            'semantic': self.semantic,
            'procedural': self.procedural,
            'recent_entities': self.recent_entities,
            'corrections': self.corrections,
            'version': self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkingSet':
        """Reconstroi de JSON."""
        return cls(
            profile=data.get('profile', {}),
            semantic=data.get('semantic', []),
            procedural=data.get('procedural', []),
            recent_entities=data.get('recent_entities', []),
            corrections=data.get('corrections', []),
            version=data.get('version', 0),
        )


@dataclass
class HookContext:
    """
    Contexto de uma sessao.

    IMPORTANTE: Este eh cache local. A fonte de verdade eh agent_events no DB.
    """
    user_id: int
    session_id: str

    # Working set estruturado
    working_set: WorkingSet = field(default_factory=WorkingSet)

    # Memorias brutas carregadas do DB
    raw_memories: Dict[str, Any] = field(default_factory=dict)

    # Candidatos a memoria pendentes de aprovacao
    pending_candidates: List[MemoryCandidate] = field(default_factory=list)

    # Historico de queries da sessao (para detectar padroes)
    query_history: List[Dict[str, Any]] = field(default_factory=list)

    # Timestamp de inicio (timezone-aware)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Version para controle de concorrencia
    version: int = 0

    # Flag se memorias foram carregadas
    memories_loaded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serializa contexto para JSON."""
        return {
            'user_id': self.user_id,
            'session_id': self.session_id,
            'working_set': self.working_set.to_dict(),
            'query_count': len(self.query_history),
            'pending_candidates': len(self.pending_candidates),
            'started_at': self.started_at.isoformat(),
            'version': self.version,
            'memories_loaded': self.memories_loaded,
        }


# =============================================================================
# DATABASE LOCK (Multi-worker safe)
# =============================================================================

def _get_session_lock_key(session_id: str) -> int:
    """Gera chave numerica para pg_advisory_lock a partir do session_id."""
    # hashtext do Postgres usa CRC32 internamente
    # Usamos hashlib para compatibilidade
    hash_bytes = hashlib.md5(session_id.encode()).digest()
    # Converte primeiros 4 bytes para int32 (signed)
    lock_key = int.from_bytes(hash_bytes[:4], byteorder='big', signed=False)
    # Postgres advisory lock aceita bigint, mas int32 eh mais seguro
    return lock_key & 0x7FFFFFFF  # Garante positivo


def acquire_session_lock_sync(db_session, session_id: str) -> None:
    """
    Adquire lock distribuido via pg_advisory_xact_lock.

    O lock eh automaticamente liberado no fim da transacao.
    """
    from sqlalchemy import text
    lock_key = _get_session_lock_key(session_id)
    db_session.execute(text(f"SELECT pg_advisory_xact_lock({lock_key})"))


# =============================================================================
# HOOK MANAGER
# =============================================================================

class HookManager:
    """
    Gerenciador central de hooks.

    Arquitetura:
    - _contexts: Cache local (pode perder entre workers/restarts)
    - DB (agent_events): Fonte de verdade (append-only)
    - pg_advisory_xact_lock: Lock distribuido para multi-worker
    - asyncio.Lock: Lock local para single-worker
    - asyncio.to_thread(): Operacoes sync de DB
    """

    def __init__(self, app=None):
        """
        Inicializa o HookManager.

        Args:
            app: Flask app (opcional)
        """
        self._app = app
        self._contexts: Dict[str, HookContext] = {}  # Cache local
        self._locks: Dict[str, asyncio.Lock] = {}    # Locks locais

        # Lazy load dos componentes
        self._memory_retriever = None
        self._pattern_detector = None
        self._write_policy = None
        self._memory_writer = None
        self._event_logger = None
        self._learning_loop = None

        logger.info("[HOOKS] HookManager inicializado (multi-worker safe com pg_advisory_lock)")

    def _get_app(self):
        """Obtem Flask app."""
        if self._app:
            return self._app
        from flask import current_app
        return current_app._get_current_object()

    def _get_local_lock(self, session_id: str) -> asyncio.Lock:
        """Obtem ou cria lock local para sessao."""
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]

    def _ensure_components_loaded(self):
        """Carrega componentes sob demanda."""
        if self._memory_retriever is None:
            from .memory_retriever import MemoryRetriever
            from .pattern_detector import PatternDetector
            from .write_policy import MemoryWritePolicy
            from .memory_writer import MemoryWriter
            from .event_logger import EventLogger
            from .learning_loop import LearningLoop

            self._memory_retriever = MemoryRetriever(self._app)
            self._pattern_detector = PatternDetector(self._app)
            self._write_policy = MemoryWritePolicy(self._app)
            self._memory_writer = MemoryWriter(self._app)
            self._event_logger = EventLogger(self._app)
            self._learning_loop = LearningLoop(self._app)

    def _rebuild_context_from_events_sync(
        self,
        user_id: int,
        session_id: str,
    ) -> HookContext:
        """
        Reconstroi contexto a partir de agent_events (fonte de verdade).

        Executado sync, deve ser chamado via asyncio.to_thread().
        """
        from ..models import AgentEvent

        context = HookContext(
            user_id=user_id,
            session_id=session_id,
        )

        app = self._get_app()

        try:
            with app.app_context():
                # Busca eventos da sessao (mais recentes primeiro, limite razoavel)
                events = AgentEvent.query.filter_by(
                    session_id=session_id
                ).order_by(AgentEvent.created_at.asc()).limit(500).all()

                for event in events:
                    event_type = event.event_type
                    data = event.data or {}

                    # Reconstroi query_history
                    if event_type == 'pre_query':
                        context.query_history.append({
                            'prompt': data.get('prompt_preview', ''),
                            'timestamp': event.created_at.isoformat() if event.created_at else '',
                        })

                    # Reconstroi working_set version
                    if event_type == 'memory_retrieved':
                        context.memories_loaded = True

                    # Incrementa version
                    context.version += 1

                # Se nao encontrou eventos, tenta fallback para AgentSession
                if not events:
                    from ..models import AgentSession
                    session = AgentSession.get_by_session_id(session_id)
                    if session and session.data:
                        messages = session.data.get('messages', [])
                        for msg in messages:
                            if msg.get('role') == 'user':
                                context.query_history.append({
                                    'prompt': msg.get('content', ''),
                                    'timestamp': msg.get('timestamp', ''),
                                })
                        context.version = session.data.get('hook_version', 0)

        except Exception as e:
            logger.error(f"[HOOKS] Erro ao reconstruir contexto: {e}")

        return context

    async def _get_or_rebuild_context(
        self,
        user_id: int,
        session_id: str,
    ) -> HookContext:
        """
        Obtem contexto do cache ou reconstroi do DB via agent_events.

        Garante que mesmo apos restart/troca de worker o contexto existe.
        """
        # Tenta cache primeiro
        if session_id in self._contexts:
            return self._contexts[session_id]

        # Reconstroi do DB usando asyncio.to_thread para nao bloquear
        logger.info(f"[HOOKS] Reconstruindo contexto de agent_events para {session_id[:8]}...")

        context = await asyncio.to_thread(
            self._rebuild_context_from_events_sync,
            user_id,
            session_id,
        )

        # Salva no cache
        self._contexts[session_id] = context
        return context

    def _execute_with_db_lock_sync(
        self,
        session_id: str,
        operation: callable,
        *args,
        **kwargs,
    ) -> Any:
        """
        Executa operacao com lock distribuido no Postgres.

        Sync - deve ser chamado via asyncio.to_thread().
        """
        from app import db

        app = self._get_app()

        with app.app_context():
            # Inicia transacao e adquire lock
            acquire_session_lock_sync(db.session, session_id)

            try:
                result = operation(*args, **kwargs)
                db.session.commit()
                return result
            except Exception as e:
                db.session.rollback()
                raise e

    async def on_session_start(
        self,
        user_id: int,
        session_id: str,
        is_new_session: bool = True,
    ) -> HookContext:
        """
        Hook executado no inicio de uma sessao.

        Carrega memorias via MemoryRetriever e prepara WorkingSet.
        """
        self._ensure_components_loaded()

        # Lock local primeiro (single worker)
        async with self._get_local_lock(session_id):
            logger.info(f"[HOOKS] on_session_start | user={user_id} session={session_id[:8]}...")

            # Obtem ou reconstroi contexto
            context = await self._get_or_rebuild_context(user_id, session_id)

            # Loga evento
            await self._event_logger.log(
                event_type=EventType.SESSION_START,
                user_id=user_id,
                session_id=session_id,
                data={'is_new': is_new_session},
            )

            # Carrega memorias via MemoryRetriever (se ainda nao carregou)
            if not context.memories_loaded:
                retrieval_result = await self._memory_retriever.retrieve(
                    user_id=user_id,
                    prompt="",  # Sessao inicial, sem prompt ainda
                    existing_working_set=None,
                )

                context.working_set = retrieval_result.get('working_set', WorkingSet())
                context.raw_memories = retrieval_result.get('raw_memories', {})
                context.memories_loaded = True

                # Loga memorias recuperadas
                await self._event_logger.log(
                    event_type=EventType.MEMORY_RETRIEVED,
                    user_id=user_id,
                    session_id=session_id,
                    data={
                        'profile': bool(context.working_set.profile),
                        'semantic_count': len(context.working_set.semantic),
                        'procedural_count': len(context.working_set.procedural),
                    },
                )

                logger.info(
                    f"[HOOKS] Memorias carregadas | "
                    f"semantic={len(context.working_set.semantic)} "
                    f"procedural={len(context.working_set.procedural)}"
                )

            return context

    async def on_pre_query(
        self,
        user_id: int,
        session_id: str,
        prompt: str,
    ) -> Dict[str, Any]:
        """
        Hook executado antes de enviar query ao SDK.

        Responsabilidade: APENAS recuperar memorias relevantes.
        NAO detecta padroes aqui (isso eh post-hook).
        """
        self._ensure_components_loaded()

        async with self._get_local_lock(session_id):
            # Garante que sessao foi iniciada
            context = await self._get_or_rebuild_context(user_id, session_id)
            if not context.memories_loaded:
                await self.on_session_start(user_id, session_id, is_new_session=False)
                context = self._contexts[session_id]

            # Registra query no historico
            context.query_history.append({
                'prompt': prompt,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            })
            context.version += 1

            # Recupera memorias relevantes para este prompt especifico
            retrieval_result = await self._memory_retriever.retrieve(
                user_id=user_id,
                prompt=prompt,
                existing_working_set=context.working_set,
            )

            # IMPORTANTE: Atualiza working_set e raw_memories no contexto!
            updated_working_set = retrieval_result.get('working_set', context.working_set)
            context.working_set = updated_working_set
            context.raw_memories = retrieval_result.get('raw_memories', context.raw_memories)

            # Loga evento (com scrubbing)
            await self._event_logger.log(
                event_type=EventType.PRE_QUERY,
                user_id=user_id,
                session_id=session_id,
                data={
                    'prompt_length': len(prompt),
                    'prompt_preview': truncate_payload(prompt, 100),
                    'memories_retrieved': retrieval_result.get('count', 0),
                    'query_number': len(context.query_history),
                },
            )

            # Renderiza contexto para injecao
            context_injection = updated_working_set.render()

            logger.debug(
                f"[HOOKS] on_pre_query | "
                f"prompt_len={len(prompt)} "
                f"injection_len={len(context_injection)}"
            )

            return {
                'enriched_prompt': prompt,  # Nao modifica prompt, apenas adiciona contexto
                'context_injection': context_injection,
                'working_set': updated_working_set.to_dict(),
            }

    async def on_post_response(
        self,
        user_id: int,
        session_id: str,
        user_prompt: str,
        assistant_response: str,
        tools_used: List[str] = None,
        tool_errors: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Hook executado apos resposta do Claude.

        Responsabilidades:
        1. PatternDetector: Detecta padroes -> memory_candidates
        2. MemoryWritePolicy: Avalia candidatos -> approved
        3. MemoryWriter: Persiste aprovados -> saved
        """
        self._ensure_components_loaded()

        async with self._get_local_lock(session_id):
            context = await self._get_or_rebuild_context(user_id, session_id)

            # 1. Detecta padroes (gera candidatos)
            candidates = await self._pattern_detector.analyze(
                user_id=user_id,
                user_prompt=user_prompt,
                assistant_response=assistant_response,
                tools_used=tools_used or [],
                tool_errors=tool_errors or [],
                query_history=context.query_history,
            )

            # Loga candidatos (com scrubbing)
            for candidate in candidates:
                await self._event_logger.log(
                    event_type=EventType.MEMORY_CANDIDATE,
                    user_id=user_id,
                    session_id=session_id,
                    data={
                        'path': candidate.path,
                        'type': candidate.memory_type,
                        'confidence': candidate.confidence,
                        'summary': truncate_payload(candidate.summary, 100),
                    },
                )

            # 2. Avalia candidatos (Write Policy)
            # IMPORTANTE: Write Policy BLOQUEIA candidates com sensitivity=HIGH
            approved = await self._write_policy.evaluate(
                candidates=candidates,
                existing_memories=context.raw_memories,
            )

            # 3. Persiste aprovados
            saved = []
            if approved:
                saved = await self._memory_writer.persist(
                    user_id=user_id,
                    candidates=approved,
                )

                # Loga salvamentos
                for item in saved:
                    await self._event_logger.log(
                        event_type=EventType.MEMORY_SAVED,
                        user_id=user_id,
                        session_id=session_id,
                        data={
                            'path': item.get('path'),
                            'type': item.get('type'),
                        },
                    )

            # Loga evento principal (com scrubbing)
            await self._event_logger.log(
                event_type=EventType.POST_RESPONSE,
                user_id=user_id,
                session_id=session_id,
                data={
                    'response_length': len(assistant_response),
                    'tools_used': tools_used or [],
                    'tool_errors_count': len(tool_errors or []),
                    'candidates_detected': len(candidates),
                    'candidates_approved': len(approved),
                    'memories_saved': len(saved),
                },
            )

            # Verifica se deve pedir feedback
            should_ask_feedback = await self._learning_loop.should_request_feedback(
                user_id=user_id,
                query_count=len(context.query_history),
                response_length=len(assistant_response),
                has_tool_errors=bool(tool_errors),
            )

            logger.info(
                f"[HOOKS] on_post_response | "
                f"candidates={len(candidates)} "
                f"approved={len(approved)} "
                f"saved={len(saved)} "
                f"feedback={should_ask_feedback}"
            )

            return {
                'candidates_detected': len(candidates),
                'candidates_approved': len(approved),
                'memories_saved': saved,
                'feedback_requested': should_ask_feedback,
            }

    async def on_tool_call(
        self,
        user_id: int,
        session_id: str,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> None:
        """Hook para instrumentacao de tool calls."""
        self._ensure_components_loaded()

        await self._event_logger.log(
            event_type=EventType.TOOL_CALL,
            user_id=user_id,
            session_id=session_id,
            data={
                'tool_name': tool_name,
                'tool_input_preview': truncate_payload(tool_input, 200),
            },
        )

    async def on_tool_result(
        self,
        user_id: int,
        session_id: str,
        tool_name: str,
        result: Any,
        is_error: bool = False,
    ) -> None:
        """Hook para instrumentacao de tool results."""
        self._ensure_components_loaded()

        event_type = EventType.TOOL_ERROR if is_error else EventType.TOOL_RESULT

        await self._event_logger.log(
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            data={
                'tool_name': tool_name,
                'result_preview': truncate_payload(result, 200),
                'is_error': is_error,
            },
        )

    async def on_feedback_received(
        self,
        user_id: int,
        session_id: str,
        feedback_type: str,
        feedback_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Hook para processar feedback do usuario.

        O feedback serve como evidence adicional para candidatos pendentes
        e para ajustar confidence de memorias existentes.
        """
        self._ensure_components_loaded()

        # Loga evento
        await self._event_logger.log(
            event_type=EventType.FEEDBACK_RECEIVED,
            user_id=user_id,
            session_id=session_id,
            data={
                'type': feedback_type,
                'data': truncate_payload(feedback_data, 200),
            },
        )

        # Processa feedback via LearningLoop
        result = await self._learning_loop.process_feedback(
            user_id=user_id,
            feedback_type=feedback_type,
            feedback_data=feedback_data,
        )

        logger.info(
            f"[HOOKS] on_feedback_received | "
            f"type={feedback_type} "
            f"processed={result.get('processed', False)}"
        )

        return result

    async def on_session_end(
        self,
        user_id: int,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Hook executado ao final de uma sessao.

        Consolida aprendizados e persiste estado final.
        """
        self._ensure_components_loaded()

        async with self._get_local_lock(session_id):
            # IMPORTANTE: Sempre tenta reconstruir contexto (multi-worker pode nao ter cache)
            context = await self._get_or_rebuild_context(user_id, session_id)

            # Loga evento
            await self._event_logger.log(
                event_type=EventType.SESSION_END,
                user_id=user_id,
                session_id=session_id,
                data={
                    'query_count': len(context.query_history),
                    'pending_candidates': len(context.pending_candidates),
                },
            )

            # Processa candidatos pendentes com threshold mais baixo
            # (final de sessao = mais confianca nos padroes observados)
            if context.pending_candidates:
                approved = await self._write_policy.evaluate(
                    candidates=context.pending_candidates,
                    existing_memories=context.raw_memories,
                    end_of_session=True,  # Threshold mais baixo
                )

                if approved:
                    await self._memory_writer.persist(
                        user_id=user_id,
                        candidates=approved,
                    )

            # Atualiza version no DB (via thread para nao bloquear)
            def save_version_sync():
                from ..models import AgentSession
                from app import db

                app = self._get_app()
                with app.app_context():
                    session = AgentSession.get_by_session_id(session_id)
                    if session:
                        if not session.data:
                            session.data = {}
                        session.data['hook_version'] = context.version
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(session, 'data')
                        db.session.commit()

            try:
                await asyncio.to_thread(save_version_sync)
            except Exception as e:
                logger.error(f"[HOOKS] Erro ao salvar version: {e}")

            # Flush eventos pendentes
            await self._event_logger.flush()

            logger.info(f"[HOOKS] on_session_end | session={session_id[:8]}...")

            return {
                'status': 'completed',
                'query_count': len(context.query_history),
            }

    def cleanup_old_contexts(self, max_age_hours: int = 24):
        """Remove contextos antigos do cache local."""
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        max_age = timedelta(hours=max_age_hours)

        to_remove = []
        for session_id, context in self._contexts.items():
            if now - context.started_at > max_age:
                to_remove.append(session_id)

        for session_id in to_remove:
            del self._contexts[session_id]
            if session_id in self._locks:
                del self._locks[session_id]

        if to_remove:
            logger.info(f"[HOOKS] Limpeza: {len(to_remove)} contextos removidos do cache")


# =============================================================================
# SINGLETON
# =============================================================================

_hook_manager: Optional[HookManager] = None


def get_hook_manager(app=None) -> HookManager:
    """Obtem instancia do HookManager (singleton)."""
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager(app)
    return _hook_manager


def reset_hook_manager():
    """Reseta o singleton do HookManager."""
    global _hook_manager
    _hook_manager = None
