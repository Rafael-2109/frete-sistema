"""Entrega proativa de respostas do Teams (Fases C e E2 — plano teams-melhorias).

Problema: a Azure Function entrega a resposta via polling preso ao tempo de
vida da execução (POLL_MAX_ATTEMPTS = 8,5 min; functionTimeout = 10 min).
Tarefas mais longas completavam no backend mas a resposta nunca chegava ao Teams.

Solução (Fase C): quando a task completa e o polling provavelmente já morreu,
o backend POSTa em `{TEAMS_FUNCTION_URL}/api/notify` com o
`conversation_reference` gravado na task; a function entrega via
`adapter.continue_conversation()` (reusa os builders de split/card do bot.py).

Fase E2 (entrega contínua): enquanto a task ainda PROCESSA depois do fim do
polling, o heartbeat do stream chama `notify_function_partial` a cada 60s —
o delta novo de texto (resposta[proactive_partial_chars:]) vira MENSAGEM NOVA
no Teams (proactive não edita mensagem existente). A entrega FINAL envia só o
delta restante. O offset SÓ avança após POST 200 (falha de POST = bloco pode
duplicar no reenvio, mas texto nunca se perde).

Anti-duplicata da entrega FINAL (claim atômico em `teams_tasks.delivered_via`):
- `/bot/status` clama 'polling' ao retornar status final (bot_routes.py);
- `notify_function_delivery` clama 'proactive' ANTES do POST e faz ROLLBACK do
  claim se o POST falhar (o polling, se vivo, volta a poder entregar).
Quem ganhar o claim entrega; o perdedor vê e desiste. Blocos parciais NÃO
clamam — claim é exclusivo da entrega final.
"""
import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

# Janela do polling da function: 340 x 1.5s = 510s (Fase E1). So notificamos
# depois que o polling provavelmente desistiu (+margem). Antes disso o polling
# entrega em <= 1.5s (progressive update in-place) — proactive seria redundante.
POLLING_WINDOW_SECONDS = 520

# Fase E2: tamanho minimo do delta para valer um bloco proativo (mensagem nova
# no Teams). Tambem filtra o status transitorio de tool ("_Consultando..._")
# que o flush parcial grava em resposta antes do primeiro texto real.
PARTIAL_MIN_DELTA_CHARS = 200

# Fase E2: enviado na entrega final quando os blocos ja entregaram 100% do
# texto (delta vazio) — nunca enviar "Sem resposta do sistema." nesse caso.
PARTIAL_FINAL_MARKER = "_(fim da resposta — conteúdo já entregue acima)_"

_NOTIFY_TIMEOUT = 30  # POST a function (continue_conversation e rapido)

# Retry+backoff do POST a function. A Azure Function `frete-bot-func` esta no
# plano Consumption (`sku: Dynamic`, `alwaysOn: false`) e escala a zero: em
# cold-start/reciclagem a 1a conexao do backend pode levar `Connection refused`
# (RST) ate o Azure provisionar a instancia. A lista = intervalos (s) ENTRE
# tentativas; total de POSTs = len(_NOTIFY_BACKOFF) + 1. Dimensionado p/ cobrir
# o cold-start sem segurar o caller demais — o reconciliador (60s) e' a rede de
# seguranca para o resto. Tunavel via env TEAMS_NOTIFY_BACKOFF (CSV de segundos).
_NOTIFY_BACKOFF = [
    float(x) for x in os.environ.get("TEAMS_NOTIFY_BACKOFF", "2,5,10").split(",")
    if x.strip()
]


# URL estavel da Azure Function (mesma do teams-manifest/manifest.json).
# Default no codigo elimina passo de env no go-live; override via env se mudar.
_DEFAULT_FUNCTION_URL = (
    "https://frete-bot-func-d4awggfge3awcqap.brazilsouth-01.azurewebsites.net"
)


def _function_url() -> str:
    """URL base da Azure Function (env TEAMS_FUNCTION_URL sobrepoe o default)."""
    return (os.environ.get("TEAMS_FUNCTION_URL", _DEFAULT_FUNCTION_URL) or "").rstrip("/")


def _post_notify(base_url: str, payload: dict, api_key: str,
                 timeout: int = _NOTIFY_TIMEOUT) -> "requests.Response":
    """POST {base_url}/api/notify com retry+backoff (cold-start Consumption).

    Re-tenta em falha de conexao OU HTTP != 200, dormindo `_NOTIFY_BACKOFF[i]`
    entre tentativas. Em 200 retorna a Response; se TODAS as tentativas
    falharem, levanta a ULTIMA excecao para o caller (que faz rollback do claim
    na entrega final ou nao avanca o offset no bloco parcial).

    A primeira tentativa que esbarra na function fria tambem serve para
    "cutucar" o Azure a iniciar o cold-start; as seguintes (apos o backoff)
    tendem a pegar a instancia ja provisionada.
    """
    url = f"{base_url}/api/notify"
    headers = {"X-API-Key": api_key}
    total = len(_NOTIFY_BACKOFF) + 1
    ultima_exc: Exception | None = None
    for i in range(total):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return resp
            ultima_exc = RuntimeError(f"notify HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:  # ConnectionError, Timeout, etc.
            ultima_exc = e
        if i < total - 1:
            logger.info(
                f"[TEAMS-NOTIFY] tentativa {i + 1}/{total} falhou ({ultima_exc}); "
                f"retry em {_NOTIFY_BACKOFF[i]}s"
            )
            time.sleep(_NOTIFY_BACKOFF[i])
    raise ultima_exc if ultima_exc else RuntimeError("notify falhou sem excecao")


def notify_function_delivery(task_id: str, min_elapsed: int = POLLING_WINDOW_SECONDS) -> dict:
    """Entrega a resposta de uma task final via proactive messaging (best-effort).

    NUNCA levanta — chamado do finally-path de process_teams_task_async.

    Args:
        task_id: TeamsTask em status final (completed|error)
        min_elapsed: segundos minimos desde created_at (polling precisa ter
            morrido; default = janela do polling com margem)

    Returns:
        {"ok": bool, "motivo": str} — motivo em caso de skip/falha.
    """
    try:
        from sqlalchemy import text as sql_text
        from app import db
        from app.teams.models import TeamsTask
        from app.utils.timezone import agora_utc_naive
        from app.agente.config.feature_flags import TEAMS_PROACTIVE_DELIVERY

        if not TEAMS_PROACTIVE_DELIVERY:
            return {"ok": False, "motivo": "flag_off"}

        base_url = _function_url()
        if not base_url:
            return {"ok": False, "motivo": "sem_url"}

        task = db.session.get(TeamsTask, task_id)
        if not task or task.status not in ("completed", "error"):
            return {"ok": False, "motivo": "task_nao_final"}
        if not task.conversation_reference:
            return {"ok": False, "motivo": "sem_reference"}

        elapsed = (agora_utc_naive() - task.created_at).total_seconds() if task.created_at else 0
        if elapsed < min_elapsed:
            return {"ok": False, "motivo": "polling_vivo"}

        # Claim atomico: so notifica quem ganhar (delivered_via IS NULL)
        claimed = db.session.execute(sql_text(
            "UPDATE teams_tasks SET delivered_via = 'proactive' "
            "WHERE id = :id AND delivered_via IS NULL"
        ), {"id": task_id}).rowcount
        db.session.commit()
        if not claimed:
            return {"ok": False, "motivo": "ja_entregue"}

        # Fase E2: se blocos parciais ja entregaram parte da resposta, a final
        # envia apenas o delta restante. Erro IGNORA o offset (texto de erro
        # SUBSTITUI o parcial, nao o continua). Offset alem do len (truncagem
        # da sanitizacao final em 24K) -> delta vazio -> marcador.
        resposta_full = task.resposta or ""
        offset = task.proactive_partial_chars or 0
        if task.status == 'completed' and offset > 0:
            resposta_envio = resposta_full[offset:]
            if not resposta_envio.strip():
                resposta_envio = PARTIAL_FINAL_MARKER
        else:
            resposta_envio = resposta_full

        payload = {
            "tipo": "final",
            "task_id": task_id,
            "status": task.status,
            "resposta": resposta_envio or "Sem resposta do sistema.",
            "resposta_card": task.resposta_card,
            "conversation_reference": task.conversation_reference,
        }
        api_key = os.environ.get("TEAMS_BOT_API_KEY", "")
        try:
            # Retry+backoff absorve o Connection refused transitorio de cold-start
            _post_notify(base_url, payload, api_key)
        except Exception as post_err:
            # Rollback do claim: polling (se vivo) ou o reconciliador (60s) re-entrega
            logger.warning(
                f"[TEAMS-PROACTIVE] POST /api/notify falhou apos retries (claim revertido): {post_err}"
            )
            db.session.execute(sql_text(
                "UPDATE teams_tasks SET delivered_via = NULL "
                "WHERE id = :id AND delivered_via = 'proactive'"
            ), {"id": task_id})
            db.session.commit()
            return {"ok": False, "motivo": f"post_falhou: {post_err}"}

        logger.info(
            f"[TEAMS-PROACTIVE] Resposta entregue via proactive: task={task_id[:8]}... "
            f"elapsed={elapsed:.0f}s len={len(resposta_envio)} offset={offset}"
        )
        return {"ok": True, "motivo": "entregue"}

    except Exception as e:
        logger.error(f"[TEAMS-PROACTIVE] Erro inesperado (ignorado): {e}", exc_info=True)
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
        return {"ok": False, "motivo": f"erro: {e}"}


def notify_function_partial(task_id: str, min_elapsed: int = POLLING_WINDOW_SECONDS) -> dict:
    """Entrega um bloco PARCIAL da resposta via proactive messaging (best-effort).

    Fase E2 (entrega contínua): chamado pelo heartbeat do stream (60s, em
    executor) ENQUANTO a task processa, depois que o polling da function já
    morreu. Envia o delta novo (resposta[proactive_partial_chars:]) como
    mensagem NOVA no Teams. SEM claim — `delivered_via` é exclusivo da
    entrega FINAL (notify_function_delivery).

    Dedup: o offset SÓ avança após POST 200 (CAS sobre o offset lido). Se o
    POST falhar, o próximo tick reenvia o mesmo delta (duplicar bloco raro é
    aceitável; perder texto não é).

    NUNCA levanta.

    Args:
        task_id: TeamsTask em status 'processing'
        min_elapsed: segundos mínimos desde created_at (polling precisa ter
            morrido; antes disso o progressive update in-place já entrega)

    Returns:
        {"ok": bool, "motivo": str} (+ "chars" quando ok)
    """
    try:
        from sqlalchemy import text as sql_text
        from app import db
        from app.teams.models import TeamsTask
        from app.utils.timezone import agora_utc_naive
        from app.agente.config.feature_flags import TEAMS_PROACTIVE_DELIVERY

        if not TEAMS_PROACTIVE_DELIVERY:
            return {"ok": False, "motivo": "flag_off"}

        base_url = _function_url()
        if not base_url:
            return {"ok": False, "motivo": "sem_url"}

        task = db.session.get(TeamsTask, task_id)
        if not task or task.status != 'processing':
            return {"ok": False, "motivo": "task_nao_processing"}
        if task.delivered_via:
            # Final ja foi (ou esta sendo) entregue — nao mandar bloco atrasado
            return {"ok": False, "motivo": "ja_entregue"}
        if not task.conversation_reference:
            return {"ok": False, "motivo": "sem_reference"}

        elapsed = (agora_utc_naive() - task.created_at).total_seconds() if task.created_at else 0
        if elapsed < min_elapsed:
            return {"ok": False, "motivo": "polling_vivo"}

        resposta_atual = task.resposta or ""
        offset = task.proactive_partial_chars or 0
        delta = resposta_atual[offset:]
        if len(delta) < PARTIAL_MIN_DELTA_CHARS:
            return {"ok": False, "motivo": "delta_pequeno"}

        # Cortar em quebra de paragrafo quando possivel — bloco nao termina no
        # meio de frase/tabela; o resto vai no proximo bloco ou na final.
        corte = delta.rfind('\n\n')
        if corte >= PARTIAL_MIN_DELTA_CHARS:
            delta = delta[:corte]

        payload = {
            "tipo": "partial",
            "task_id": task_id,
            "texto_delta": delta,
            "conversation_reference": task.conversation_reference,
        }
        api_key = os.environ.get("TEAMS_BOT_API_KEY", "")
        try:
            # Retry+backoff absorve o refused transitorio de cold-start
            _post_notify(base_url, payload, api_key)
        except Exception as post_err:
            # Nao avanca o offset -> proximo tick (ou a entrega final) reenvia o delta
            return {"ok": False, "motivo": f"post_falhou: {post_err}"}

        # Offset avanca SO apos POST 200. CAS sobre o offset lido: dois envios
        # concorrentes do mesmo delta nunca somam o avanco duas vezes.
        novo_offset = offset + len(delta)
        db.session.execute(sql_text(
            "UPDATE teams_tasks SET proactive_partial_chars = :novo "
            "WHERE id = :id AND proactive_partial_chars = :antigo"
        ), {"novo": novo_offset, "id": task_id, "antigo": offset})
        db.session.commit()

        logger.info(
            f"[TEAMS-PARTIAL] Bloco proativo entregue: task={task_id[:8]}... "
            f"offset {offset}->{novo_offset} elapsed={elapsed:.0f}s"
        )
        return {"ok": True, "motivo": "bloco_entregue", "chars": len(delta)}

    except Exception as e:
        logger.warning(f"[TEAMS-PARTIAL] Falha (ignorada): {e}")
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
        return {"ok": False, "motivo": f"erro: {e}"}


def reconciliar_entregas_pendentes(max_age_min: int = None, limite: int = None) -> dict:
    """Rede de seguranca: re-entrega tasks finais orfas (delivered_via IS NULL).

    Resolve o cold-start do plano Consumption: quando o POST inline a function
    fria falhou (mesmo apos retry), esta varredura periodica (scheduler ~60s)
    re-tenta a entrega — a essa altura a function ja foi 'cutucada'/esquentou.

    Elegibilidade (created_at entre [polling morto] e [teto de idade]):
      - status IN ('completed','error')
      - delivered_via IS NULL  (nem polling nem proactive entregaram)
      - conversation_reference IS NOT NULL  (continue_conversation precisa dela)
      - created_at <= agora - POLLING_WINDOW  (polling da function ja morreu)
      - created_at >= agora - max_age  (resposta ainda relevante; ref nao velha)

    Idempotente: `notify_function_delivery` faz o claim atomico em delivered_via
    (UPDATE ... WHERE delivered_via IS NULL), entao duas execucoes concorrentes
    do reconciliador — ou uma corrida com o polling — nunca entregam em dobro.

    Returns:
        {"candidatas": int, "entregues": int, "falhas": int[, "motivo": str]}
    """
    from datetime import timedelta
    from sqlalchemy import text as sql_text
    from app import db
    from app.utils.timezone import agora_utc_naive
    from app.agente.config.feature_flags import (
        TEAMS_PROACTIVE_DELIVERY,
        TEAMS_RECONCILE_ENABLED,
        TEAMS_RECONCILE_MAX_AGE_MIN,
        TEAMS_RECONCILE_LIMIT,
    )

    out = {"candidatas": 0, "entregues": 0, "falhas": 0}
    if not (TEAMS_PROACTIVE_DELIVERY and TEAMS_RECONCILE_ENABLED):
        out["motivo"] = "flag_off"
        return out
    if not _function_url():
        out["motivo"] = "sem_url"
        return out

    max_age = TEAMS_RECONCILE_MAX_AGE_MIN if max_age_min is None else max_age_min
    lim = TEAMS_RECONCILE_LIMIT if limite is None else limite
    agora = agora_utc_naive()
    janela_polling = agora - timedelta(seconds=POLLING_WINDOW_SECONDS)  # polling morto
    janela_idade = agora - timedelta(minutes=max_age)                  # ref ainda relevante

    try:
        candidatas = db.session.execute(sql_text(
            "SELECT id FROM teams_tasks "
            "WHERE status IN ('completed', 'error') "
            "AND delivered_via IS NULL "
            "AND conversation_reference IS NOT NULL "
            "AND created_at <= :janela_polling AND created_at >= :janela_idade "
            "ORDER BY created_at DESC LIMIT :lim"
        ), {
            "janela_polling": janela_polling,
            "janela_idade": janela_idade,
            "lim": lim,
        }).fetchall()
    except Exception as e:
        logger.error(f"[TEAMS-RECONCILE] query de candidatas falhou: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        out["motivo"] = f"query_erro: {e}"
        return out

    out["candidatas"] = len(candidatas)
    for row in candidatas:
        task_id = row[0]
        try:
            # min_elapsed=0: a candidata ja passou o gate de idade na query acima
            r = notify_function_delivery(task_id, min_elapsed=0)
            if r.get("ok"):
                out["entregues"] += 1
            else:
                out["falhas"] += 1
        except Exception as e:
            logger.warning(f"[TEAMS-RECONCILE] task {str(task_id)[:8]}... falhou: {e}")
            out["falhas"] += 1

    if out["candidatas"]:
        logger.info(
            f"[TEAMS-RECONCILE] candidatas={out['candidatas']} "
            f"entregues={out['entregues']} falhas={out['falhas']}"
        )
    return out
