"""Registry do FALANTE do turno por sessão (Fase B teams-melhorias 2026-06-10).

Problema: os hooks do SDK (`build_hooks`) vivem em CLOSURE criada no turno que
CONECTOU o client do pool — `client_pool.get_or_create_client` reusa o client
SEM reaplicar hooks (fast path). Em conversa de GRUPO do Teams (vários falantes
na mesma sessão), o `<session_context><usuario>` e as MEMÓRIAS injetadas pelo
hook UserPromptSubmit ficavam congelados no 1º falante.

Solução: registry module-level keyed por `our_session_id` (mesmo pattern do
`resume_state` mutável). O client seta a cada turno (`stream_response`/
`get_response`); os hooks resolvem via `resolve_turn_user` com FALLBACK para os
valores da closure — comportamento do web 1:1 fica inalterado quando o registry
não tem entrada.

ContextVar NÃO serve aqui: o hook roda no event loop do daemon thread do pool,
fora do contexto da thread Flask que recebeu a mensagem.

Decisão Rafael (2026-06-10): memórias injetadas em grupo = do falante do turno.
"""
import threading
from typing import Optional, Tuple

_registry: dict = {}
_lock = threading.Lock()


def set_turn_user(session_id: Optional[str], user_id: Optional[int], user_name: str) -> None:
    """Registra o falante do turno atual da sessão (sobrescreve o anterior)."""
    if not session_id:
        return
    with _lock:
        _registry[session_id] = (user_id, user_name)


def get_turn_user(session_id: Optional[str]) -> Optional[Tuple[Optional[int], str]]:
    """Retorna (user_id, user_name) do turno atual, ou None se não registrado."""
    if not session_id:
        return None
    with _lock:
        return _registry.get(session_id)


def clear_turn_user(session_id: Optional[str]) -> None:
    """Remove o registro da sessão (chamado quando o client sai do pool)."""
    if not session_id:
        return
    with _lock:
        _registry.pop(session_id, None)


def resolve_turn_user(
    session_id: Optional[str],
    fallback_user_id: Optional[int],
    fallback_user_name: str,
) -> Tuple[Optional[int], str]:
    """Resolve o falante do turno com fallback para a closure (defense in depth)."""
    registrado = get_turn_user(session_id)
    if registrado is not None:
        return registrado
    return (fallback_user_id, fallback_user_name)
