"""
Mecanismo de espera para AskUserQuestion — cross-worker via Redis pub/sub.

Permite que o callback can_use_tool() pause ate o frontend enviar a resposta
do usuario via HTTP POST. Funciona em ambiente multi-worker gunicorn.

ARQUITETURA (R-MULTIWORKER, 2026-05-12):

Bug historico: _pending era um dict process-local, mas gunicorn roda 4
workers sem sticky session. Quando AskUserQuestion registrava a pergunta
no worker A, o POST /api/user-answer podia cair em qualquer worker (75%
chance de cair em B/C/D), resultando em 404 silencioso e timeout de 55s.

Solucao: Redis como transporte de wakeup entre workers.
- Storage canonico continua local (_pending no worker A)
- Redis SETEX agent:pq:{sid} marca pergunta como pendente (cross-worker visibility)
- Submit em qualquer worker -> Redis PUBLISH agent:pq:answer:{sid}
- Subscriber thread no worker A recebe -> sinaliza Event LOCAL

Modelo Dual Event (preservado desde Fase 2 Async Migration):
- threading.Event: sync path (legado/Teams, bloqueia thread)
- asyncio.Event: async path (can_use_tool em asyncio.run(), suspende coroutine)

Fluxo cross-worker:
1. can_use_tool intercepta AskUserQuestion (worker A, daemon thread)
2. register_question():
   - Local: cria PendingQuestion com threading.Event + async_event
   - Redis: SETEX agent:pq:{sid} = {tool_input, status:pending} (TTL 130s)
   - Spawn subscriber daemon thread: SUBSCRIBE channels answer/cancel
3. SSE ask_user_question emitido via event_queue (continua local, OK porque
   stream SSE permanece no mesmo worker A)
4. Frontend POST /api/user-answer (cai em qualquer worker B)
5. submit_answer (worker B):
   - Redis EXISTS agent:pq:{sid} -> se nao existe, return False (404 correto)
   - Redis PUBLISH agent:pq:answer:{sid} = answers_json
   - Redis DEL agent:pq:{sid} (idempotencia)
6. Subscriber thread (worker A):
   - Recebe mensagem do pub/sub
   - Grava answer no PendingQuestion local
   - Sinaliza Event + async_event
7. wait_for_answer/async_wait_for_answer (worker A): desbloqueia, retorna

Fallback: Se Redis indisponivel ou feature flag off, comportamento legacy
(memory-only). Funciona dentro do mesmo worker, falha cross-worker.

Compatibilidade: API publica 100% preservada (register/submit/wait/cancel/
get_pending_tool_input). Callsites em permissions.py, chat.py, bot_routes.py
nao precisam mudar.
"""

import asyncio
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Timeout para o usuario responder (segundos).
# CORRECAO 2026-06-06: o SDK NAO impoe timeout no callback can_use_tool — ele e
# awaitado sem fail_after (claude_agent_sdk/_internal/query.py:_handle_control_request);
# so o cancelamento via control_cancel_request do CLI o interrompe. Os "60s" do
# comentario antigo eram, na verdade, do _send_control_request (requests que o SDK
# ENVIA: interrupt/set_model/initialize), NAO desta callback. Logo 55s era curto
# demais (humano lendo pergunta multi-parte + clicando "Enviar" estoura) e gerava
# "agente inerte". Estendido para 180s. SEGURO: o gerador SSE renova o deadline de
# inatividade enquanto a thread esta viva (routes/chat.py emite 'processing'), entao
# a espera longa NAO derruba o stream. Configuravel por env sem deploy.
USER_RESPONSE_TIMEOUT = int(os.getenv("AGENT_ASK_USER_TIMEOUT_WEB", "180"))

# TTL do registro Redis (deve ser > maior timeout possivel entre web e Teams)
_REDIS_TTL_SECONDS = max(
    200,
    USER_RESPONSE_TIMEOUT + 20,
    int(os.getenv("TEAMS_ASK_USER_TIMEOUT", "180")) + 20,
)

# Prefixos Redis (namespaced para evitar colisao)
_REDIS_KEY_PREFIX = "agent:pq:"
_REDIS_CHANNEL_ANSWER_PREFIX = "agent:pq:answer:"
_REDIS_CHANNEL_CANCEL_PREFIX = "agent:pq:cancel:"


@dataclass
class PendingQuestion:
    """Pergunta pendente aguardando resposta do usuario."""
    session_id: str
    tool_input: Dict[str, Any]
    event: threading.Event = field(default_factory=threading.Event)
    async_event: Optional[asyncio.Event] = field(default=None)  # Fase 2: async context
    answer: Optional[Dict[str, str]] = None
    # Loop dono do async_event — usado por submit_answer/cancel_pending para
    # sinalizar via call_soon_threadsafe (cross-thread safe). Sem isso, set()
    # direto da Flask thread quebra com pool persistente (loop em outra thread).
    _loop: Optional[asyncio.AbstractEventLoop] = field(default=None)
    # R-MULTIWORKER: subscriber thread daemon que ouve Redis pub/sub.
    # Setado em register_question quando Redis disponivel.
    _subscriber_thread: Optional[threading.Thread] = field(default=None)
    # Sinalizador interno: pede para subscriber thread terminar (cleanup)
    _stop_subscriber: threading.Event = field(default_factory=threading.Event)
    # Fix code-reviewer (R-MULTIWORKER 2026-05-12 Issue #4): sinalizador
    # de subscribe ativa no Redis. _spawn_subscriber bloqueia ate este
    # evento ser setado (ou timeout), garantindo que SUBSCRIBE ja foi
    # processado pelo Redis ANTES de retornar ao caller. Sem isso, havia
    # janela de 1-5ms onde PUBLISH cross-worker chegava antes da
    # subscricao estar ativa, e a mensagem era perdida.
    _subscriber_ready: threading.Event = field(default_factory=threading.Event)


# Registry local: session_id -> PendingQuestion (storage canonico per-worker)
_pending: Dict[str, PendingQuestion] = {}
_lock = threading.Lock()


# ============================================================================
# Redis helpers (graceful degradation se indisponivel)
# ============================================================================

def _is_redis_enabled() -> bool:
    """Verifica se backing Redis esta habilitado via feature flag."""
    try:
        from ..config.feature_flags import USE_REDIS_PENDING_QUESTIONS
        return bool(USE_REDIS_PENDING_QUESTIONS)
    except Exception:
        return False


def _get_redis_client():
    """Retorna cliente Redis ou None se indisponivel.

    Best-effort: erros sao logados como debug, nunca propagam.
    Cada chamada cria nova conexao (Redis-py faz pooling internamente).
    """
    if not _is_redis_enabled():
        return None
    try:
        import redis
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        return redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
    except Exception as e:
        logger.debug(f"[ASK_USER] Redis indisponivel (fallback memory-only): {e}")
        return None


def _redis_set_pending(session_id: str, tool_input: Dict[str, Any]) -> bool:
    """Marca pergunta como pendente no Redis. Retorna True se OK."""
    r = _get_redis_client()
    if r is None:
        return False
    try:
        key = f"{_REDIS_KEY_PREFIX}{session_id}"
        payload = json.dumps({
            'tool_input': tool_input,
            'status': 'pending',
            'created_at': time.time(),
        }, ensure_ascii=False)
        r.setex(key, _REDIS_TTL_SECONDS, payload)
        return True
    except Exception as e:
        logger.warning(f"[ASK_USER] Redis SETEX falhou: {e}")
        return False


def _redis_get_tool_input(session_id: str) -> Optional[Dict[str, Any]]:
    """Le tool_input do Redis. Retorna None se nao existe ou erro."""
    r = _get_redis_client()
    if r is None:
        return None
    try:
        key = f"{_REDIS_KEY_PREFIX}{session_id}"
        raw = r.get(key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        data = json.loads(raw)
        return data.get('tool_input')
    except Exception as e:
        logger.debug(f"[ASK_USER] Redis GET tool_input falhou: {e}")
        return None


def _redis_publish_answer(session_id: str, answers: Dict[str, str]) -> int:
    """Publica resposta no canal Redis. Retorna numero de subscribers que receberam.

    Se 0 subscribers, significa que nenhum worker tem subscriber ativo
    (provavel: pergunta ja expirou ou worker reciclou).
    """
    r = _get_redis_client()
    if r is None:
        return 0
    try:
        channel = f"{_REDIS_CHANNEL_ANSWER_PREFIX}{session_id}"
        payload = json.dumps(answers, ensure_ascii=False)
        n = r.publish(channel, payload)
        # Cleanup: remove a key (idempotencia — segundo submit nao reencontra)
        try:
            key = f"{_REDIS_KEY_PREFIX}{session_id}"
            r.delete(key)
        except Exception:
            pass
        return int(n)
    except Exception as e:
        logger.warning(f"[ASK_USER] Redis PUBLISH answer falhou: {e}")
        return 0


def _redis_publish_cancel(session_id: str) -> None:
    """Publica cancelamento e remove a key."""
    r = _get_redis_client()
    if r is None:
        return
    try:
        channel = f"{_REDIS_CHANNEL_CANCEL_PREFIX}{session_id}"
        r.publish(channel, b'1')
        key = f"{_REDIS_KEY_PREFIX}{session_id}"
        r.delete(key)
    except Exception as e:
        logger.debug(f"[ASK_USER] Redis PUBLISH cancel falhou: {e}")


def _redis_check_pending(session_id: str) -> bool:
    """Verifica se pergunta esta pendente em algum worker (via Redis)."""
    r = _get_redis_client()
    if r is None:
        return False
    try:
        key = f"{_REDIS_KEY_PREFIX}{session_id}"
        return bool(r.exists(key))
    except Exception as e:
        logger.debug(f"[ASK_USER] Redis EXISTS falhou: {e}")
        return False


# ============================================================================
# Subscriber thread (cross-worker wakeup)
# ============================================================================

def _subscriber_loop(session_id: str, pq: PendingQuestion) -> None:
    """Daemon thread que escuta wakeup via Redis pub/sub para esta sessao.

    Ouve dois canais: answer e cancel. Quando recebe mensagem:
    - answer: grava no pq.answer, sinaliza events, sai
    - cancel: sinaliza events sem answer (vira timeout para waiter), sai

    Auto-encerra apos _REDIS_TTL_SECONDS para evitar vazamento.
    """
    try:
        import redis
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        pubsub = r.pubsub(ignore_subscribe_messages=True)
        answer_channel = f"{_REDIS_CHANNEL_ANSWER_PREFIX}{session_id}"
        cancel_channel = f"{_REDIS_CHANNEL_CANCEL_PREFIX}{session_id}"
        pubsub.subscribe(answer_channel, cancel_channel)
        # Fix code-reviewer (Issue #4): sinaliza que SUBSCRIBE ja foi
        # processado pelo Redis. _spawn_subscriber espera neste event
        # antes de retornar ao caller, garantindo que nao ha janela onde
        # PUBLISH cross-worker chega antes da subscricao estar ativa.
        pq._subscriber_ready.set()
    except Exception as e:
        logger.warning(
            f"[ASK_USER] Subscriber FALHOU em conectar Redis (session={session_id[:8]}...): {e}. "
            "Pergunta funcionara apenas no mesmo worker (degradacao)."
        )
        # Mesmo em erro, sinaliza ready para nao bloquear _spawn_subscriber.
        # Caller continuara — comportamento degrada para memory-only neste worker.
        pq._subscriber_ready.set()
        return

    start = time.time()
    max_duration = _REDIS_TTL_SECONDS + 5  # margem de seguranca

    try:
        while time.time() - start < max_duration:
            # Stop flag (set por cancel_pending local ou cleanup)
            if pq._stop_subscriber.is_set():
                break

            # Verifica se pergunta ainda esta no registry local
            # (waiter pode ter feito timeout e pop)
            with _lock:
                if _pending.get(session_id) is not pq:
                    break

            try:
                msg = pubsub.get_message(timeout=1.0)
            except Exception as e:
                logger.debug(f"[ASK_USER] Subscriber get_message falhou: {e}")
                time.sleep(1.0)
                continue

            if msg is None:
                continue

            channel_raw = msg.get('channel')
            if isinstance(channel_raw, bytes):
                channel_raw = channel_raw.decode('utf-8', errors='replace')
            data = msg.get('data')

            if channel_raw and channel_raw.startswith(_REDIS_CHANNEL_CANCEL_PREFIX):
                logger.info(f"[ASK_USER] Cancelamento via Redis: session={session_id[:8]}...")
                with _lock:
                    # Nao seta answer — waiter vai retornar None (timeout-like)
                    pq.event.set()
                    _signal_async_event(pq)
                break

            if channel_raw and channel_raw.startswith(_REDIS_CHANNEL_ANSWER_PREFIX):
                try:
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    answers = json.loads(data) if data else None
                except Exception as parse_err:
                    logger.warning(
                        f"[ASK_USER] Falha ao parsear answers via Redis: {parse_err}"
                    )
                    answers = None

                if isinstance(answers, dict) and answers:
                    logger.info(
                        f"[ASK_USER] Resposta cross-worker via Redis: "
                        f"session={session_id[:8]}... keys={list(answers.keys())}"
                    )
                    with _lock:
                        pq.answer = answers
                        pq.event.set()
                        _signal_async_event(pq)
                    break
    finally:
        try:
            pubsub.close()
        except Exception:
            pass


def _spawn_subscriber(session_id: str, pq: PendingQuestion) -> None:
    """Spawna daemon thread subscriber para receber wakeup cross-worker.

    Bloqueia ate o subscriber ter feito SUBSCRIBE no Redis (sinalizado via
    pq._subscriber_ready) ou timeout de 1s. Sem essa espera, ha janela onde
    PUBLISH cross-worker pode chegar antes da subscricao estar ativa e a
    mensagem seria perdida (fix code-reviewer Issue #4).
    """
    if not _is_redis_enabled():
        return
    try:
        t = threading.Thread(
            target=_subscriber_loop,
            args=(session_id, pq),
            name=f"ask-user-subscriber-{session_id[:8]}",
            daemon=True,
        )
        t.start()
        pq._subscriber_thread = t
        # Espera o subscriber estabelecer subscricao Redis (max 1s).
        # Em prod local: 1-5ms. Em Render Redis remoto: 10-50ms. Timeout
        # generoso (1s) para evitar falsos negativos em rede degradada.
        if not pq._subscriber_ready.wait(timeout=1.0):
            logger.warning(
                f"[ASK_USER] Subscriber demorou >1s para subscribir Redis: "
                f"session={session_id[:8]}... — continuando, mas race "
                f"window possivel se POST resposta chegar imediatamente"
            )
    except Exception as e:
        logger.warning(f"[ASK_USER] Falha ao spawn subscriber: {e}")


# ============================================================================
# Async event helper (preservado da versao anterior)
# ============================================================================

def _signal_async_event(pq: PendingQuestion) -> None:
    """Sinaliza pq.async_event respeitando a fronteira thread<->asyncio.

    Dois cenarios:

    1. MESMA thread do loop dono (estamos DENTRO do loop que criou o
       async_event): .set() direto eh imediato E thread-safe — eh o uso
       NORMAL de asyncio.Event. call_soon_threadsafe aqui APENAS agendaria
       o set() para depois, sem executa-lo sincronamente; quem checa
       is_set() em seguida (sem ceder controle ao loop via await) veria
       False. Por isso set() direto eh o correto.

    2. OUTRA thread (submit_answer roda na Flask thread; subscriber roda em
       daemon thread) sinalizando um async_event criado no loop daemon
       persistente: .set() direto NAO eh oficialmente thread-safe (missed
       wakeup se GIL drop entre set() e o check interno do asyncio).
       call_soon_threadsafe agenda no loop dono de forma segura.

    Fallback (loop None ou closed): set() direto. Sob CPython GIL eh
    seguro na pratica para o caso comum.
    """
    if not pq.async_event:
        return
    loop = pq._loop
    if loop is not None and not loop.is_closed():
        # Se JA estamos na thread do loop dono, set() direto e' imediato e
        # thread-safe (uso normal de asyncio.Event). call_soon_threadsafe so'
        # e' necessario para sinalizar de OUTRA thread (Flask route / subscriber).
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            pq.async_event.set()
            return
        try:
            loop.call_soon_threadsafe(pq.async_event.set)
            return
        except RuntimeError:
            # Loop ja parou ou em estado invalido — fallback direto
            pass
    pq.async_event.set()


# ============================================================================
# API publica (compativel 100% com versao anterior)
# ============================================================================

def register_question(session_id: str, tool_input: Dict[str, Any]) -> PendingQuestion:
    """Registra pergunta pendente para uma sessao.

    Args:
        session_id: ID da sessao (nosso, nao do SDK)
        tool_input: Input completo da tool AskUserQuestion

    Returns:
        PendingQuestion com Event para sincronizacao
    """
    with _lock:
        # Se ja existe pergunta pendente para esta sessao, cancela a anterior
        # para evitar deadlock (thread anterior ficaria bloqueada ate timeout)
        existing = _pending.get(session_id)
        if existing:
            existing._stop_subscriber.set()
            existing.event.set()
            _signal_async_event(existing)
            logger.warning(
                f"[ASK_USER] Sobrescrevendo pergunta anterior: session={session_id[:8]}..."
            )

        pq = PendingQuestion(session_id=session_id, tool_input=tool_input)
        # Fase 2: Cria asyncio.Event se estamos em async context.
        # Captura o loop corrente para que submit_answer (chamado de outra
        # thread — Flask route) possa sinalizar via call_soon_threadsafe.
        try:
            pq._loop = asyncio.get_running_loop()
            pq.async_event = asyncio.Event()
        except RuntimeError:
            pass  # Nao estamos em async context — sem async_event
        _pending[session_id] = pq

    # R-MULTIWORKER: marca pergunta no Redis e spawna subscriber.
    # Fora do _lock para nao bloquear outros callsites em I/O Redis.
    redis_ok = _redis_set_pending(session_id, tool_input)
    if redis_ok:
        _spawn_subscriber(session_id, pq)
        logger.info(
            f"[ASK_USER] Pergunta registrada (Redis-backed): session={session_id[:8]}..."
        )
    else:
        logger.info(
            f"[ASK_USER] Pergunta registrada (memory-only fallback): "
            f"session={session_id[:8]}..."
        )

    return pq


def get_pending_tool_input(session_id: str) -> Optional[Dict[str, Any]]:
    """Retorna o tool_input da pergunta pendente (para inspecao antes do submit).

    R-MULTIWORKER: tenta local primeiro (rapido), depois Redis (cross-worker).
    Usado por chat.py:api_user_answer para detectar routing questions.
    """
    with _lock:
        pq = _pending.get(session_id)
        if pq:
            return pq.tool_input
    # Fallback cross-worker via Redis
    return _redis_get_tool_input(session_id)


def submit_answer(session_id: str, answers: Dict[str, str]) -> bool:
    """Submete resposta do usuario. Chamado pelo endpoint HTTP.

    R-MULTIWORKER: funciona cross-worker via Redis pub/sub.
    1. Tenta local primeiro (mesmo worker): sinaliza Event diretamente.
    2. Se nao encontrou local, verifica Redis EXISTS e PUBLISH.
    3. O subscriber no worker dono recebe e sinaliza Event LOCAL la.

    Args:
        session_id: ID da sessao
        answers: Dict mapeando question text -> label selecionado

    Returns:
        True se havia pergunta pendente (local ou cross-worker) e foi respondida.
    """
    # Fast path: pergunta esta no mesmo worker
    with _lock:
        pq = _pending.get(session_id)
        if pq is not None:
            pq.answer = answers
            pq.event.set()
            _signal_async_event(pq)
            # Para subscriber thread (evita race com PUBLISH abaixo)
            pq._stop_subscriber.set()
            logger.info(
                f"[ASK_USER] Resposta recebida (local): session={session_id[:8]}... "
                f"answers={list(answers.keys())}"
            )
            # Best-effort: notifica outros workers para limpar suas keys Redis
            # (idempotencia — se outro worker tinha subscriber, ele apenas ignora)
            try:
                _redis_publish_answer(session_id, answers)
            except Exception:
                pass
            return True

    # R-MULTIWORKER: pergunta foi registrada em OUTRO worker.
    # Verifica Redis EXISTS para confirmar antes de publicar (evita 200 falso).
    if not _redis_check_pending(session_id):
        logger.warning(
            f"[ASK_USER] Nenhuma pergunta pendente (local ou Redis): "
            f"session={session_id[:8]}..."
        )
        return False

    n_subs = _redis_publish_answer(session_id, answers)
    if n_subs == 0:
        # Fix code-reviewer (R-MULTIWORKER 2026-05-12): retornar False quando
        # 0 subscribers receberam. Antes retornavamos True (fail-soft), mas
        # isso causava UX confusa: usuario recebe 200 "Resposta enviada", mas
        # o waiter (no worker dono) nunca recebe wakeup → timeout 55s →
        # agente reporta erro de timeout. Melhor retornar False imediatamente
        # → endpoint HTTP retorna 404 → frontend pode mostrar "sessao expirou".
        # Cenarios que disparam n_subs=0: (a) subscriber thread morreu
        # (worker reciclado entre register e submit); (b) pergunta expirou no
        # TTL (130s) entre register e submit; (c) subscriber falhou em
        # conectar Redis (warning logado em _subscriber_loop).
        logger.error(
            f"[ASK_USER] Resposta publicada mas 0 subscribers ouviram: "
            f"session={session_id[:8]}... — retornando False (sessao perdida). "
            f"Worker dono pode ter reciclado ou subscriber falhou ao subscrever."
        )
        return False

    logger.info(
        f"[ASK_USER] Resposta publicada cross-worker via Redis: "
        f"session={session_id[:8]}... subscribers={n_subs} "
        f"answers={list(answers.keys())}"
    )
    return True


def wait_for_answer(
    session_id: str,
    timeout: float = USER_RESPONSE_TIMEOUT,
) -> Optional[Dict[str, str]]:
    """Bloqueia ate o usuario responder ou timeout.

    Chamado dentro do can_use_tool callback (que roda em Thread daemon).
    Usa threading.Event.wait() que e thread-safe — o subscriber thread
    (ou submit_answer local) sinaliza o event.

    Args:
        session_id: ID da sessao
        timeout: Segundos maximos para esperar (default 55s)

    Returns:
        Dict de respostas ou None se timeout
    """
    with _lock:
        pq = _pending.get(session_id)

    if not pq:
        logger.warning(
            f"[ASK_USER] wait_for_answer: nenhum PQ encontrado para "
            f"session={session_id[:8]}..."
        )
        return None

    # Espera (thread-safe, funciona entre threads diferentes incluindo subscriber)
    answered = pq.event.wait(timeout=timeout)

    # Cleanup: remove do registry e para subscriber
    with _lock:
        _pending.pop(session_id, None)
    pq._stop_subscriber.set()

    if answered and pq.answer is not None:
        logger.info(f"[ASK_USER] Resposta coletada: session={session_id[:8]}...")
        return pq.answer

    # Timeout: limpa Redis tambem (best-effort)
    if not answered:
        try:
            r = _get_redis_client()
            if r is not None:
                key = f"{_REDIS_KEY_PREFIX}{session_id}"
                r.delete(key)
        except Exception:
            pass
        logger.warning(
            f"[ASK_USER] Timeout ({timeout}s) sem resposta: session={session_id[:8]}..."
        )
    return None


async def async_wait_for_answer(
    session_id: str,
    timeout: float = USER_RESPONSE_TIMEOUT,
) -> Optional[Dict[str, str]]:
    """Versao async — suspende coroutine sem bloquear thread.

    Usada quando can_use_tool roda em async context nativo
    (Fase 2: can_use_tool ja roda dentro de asyncio.run() na thread daemon).

    Args:
        session_id: ID da sessao
        timeout: Segundos maximos para esperar (default 55s)

    Returns:
        Dict de respostas ou None se timeout
    """
    with _lock:
        pq = _pending.get(session_id)

    if not pq or not pq.async_event:
        logger.warning(
            f"[ASK_USER] async_wait: sem PQ ou sem async_event: "
            f"session={session_id[:8]}..."
        )
        return None

    try:
        await asyncio.wait_for(pq.async_event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(
            f"[ASK_USER] Async timeout ({timeout}s): session={session_id[:8]}..."
        )

    # Cleanup: remove do registry e para subscriber
    with _lock:
        _pending.pop(session_id, None)
    pq._stop_subscriber.set()

    if pq.answer is not None:
        logger.info(
            f"[ASK_USER] Async resposta coletada: session={session_id[:8]}..."
        )
        return pq.answer

    # Timeout: limpa Redis tambem (best-effort)
    try:
        r = _get_redis_client()
        if r is not None:
            key = f"{_REDIS_KEY_PREFIX}{session_id}"
            r.delete(key)
    except Exception:
        pass
    return None


def cancel_pending(session_id: str) -> None:
    """Cancela pergunta pendente (ex: stream interrompido, erro).

    Desbloqueia qualquer thread/coroutine esperando em wait_for_answer()
    ou async_wait_for_answer(), que recebera None (pois answer nao foi setado).

    R-MULTIWORKER: tambem publica cancel no Redis para subscribers em outros
    workers (se houver — caso raro de re-registro cross-worker).

    Args:
        session_id: ID da sessao
    """
    with _lock:
        pq = _pending.pop(session_id, None)
        if pq:
            pq._stop_subscriber.set()
            pq.event.set()
            _signal_async_event(pq)
            logger.info(f"[ASK_USER] Pergunta cancelada: session={session_id[:8]}...")

    # Best-effort cross-worker cleanup (fora do _lock)
    _redis_publish_cancel(session_id)
