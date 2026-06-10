"""Entrega proativa de respostas do Teams (Fase C — plano teams-melhorias).

Problema: a Azure Function entrega a resposta via polling preso ao tempo de
vida da execução (POLL_MAX_ATTEMPTS = 5 min; functionTimeout = 10 min). Tarefas
mais longas completavam no backend mas a resposta nunca chegava ao Teams.

Solução: quando a task completa e o polling provavelmente já morreu, o backend
POSTa em `{TEAMS_FUNCTION_URL}/api/notify` com o `conversation_reference`
gravado na task; a function entrega via `adapter.continue_conversation()`
(reusa os builders de split/card existentes no bot.py).

Anti-duplicata (claim atômico em `teams_tasks.delivered_via`):
- `/bot/status` clama 'polling' ao retornar status final (bot_routes.py);
- `notify_function_delivery` clama 'proactive' ANTES do POST e faz ROLLBACK do
  claim se o POST falhar (o polling, se vivo, volta a poder entregar).
Quem ganhar o claim entrega; o perdedor vê e desiste.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

# Janela do polling da function: 200 x 1.5s = 300s. So notificamos depois que
# o polling provavelmente desistiu (com margem). Antes disso o polling entrega
# em <= 1.5s — proactive seria redundante.
POLLING_WINDOW_SECONDS = 270

_NOTIFY_TIMEOUT = 30  # POST a function (continue_conversation e rapido)


# URL estavel da Azure Function (mesma do teams-manifest/manifest.json).
# Default no codigo elimina passo de env no go-live; override via env se mudar.
_DEFAULT_FUNCTION_URL = (
    "https://frete-bot-func-d4awggfge3awcqap.brazilsouth-01.azurewebsites.net"
)


def _function_url() -> str:
    """URL base da Azure Function (env TEAMS_FUNCTION_URL sobrepoe o default)."""
    return (os.environ.get("TEAMS_FUNCTION_URL", _DEFAULT_FUNCTION_URL) or "").rstrip("/")


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

        payload = {
            "task_id": task_id,
            "status": task.status,
            "resposta": task.resposta or "Sem resposta do sistema.",
            "resposta_card": task.resposta_card,
            "conversation_reference": task.conversation_reference,
        }
        api_key = os.environ.get("TEAMS_BOT_API_KEY", "")
        try:
            resp = requests.post(
                f"{base_url}/api/notify",
                json=payload,
                headers={"X-API-Key": api_key},
                timeout=_NOTIFY_TIMEOUT,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"notify HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as post_err:
            # Rollback do claim: polling (se vivo) ou retry futuro pode entregar
            logger.warning(
                f"[TEAMS-PROACTIVE] POST /api/notify falhou (claim revertido): {post_err}"
            )
            db.session.execute(sql_text(
                "UPDATE teams_tasks SET delivered_via = NULL "
                "WHERE id = :id AND delivered_via = 'proactive'"
            ), {"id": task_id})
            db.session.commit()
            return {"ok": False, "motivo": f"post_falhou: {post_err}"}

        logger.info(
            f"[TEAMS-PROACTIVE] Resposta entregue via proactive: task={task_id[:8]}... "
            f"elapsed={elapsed:.0f}s len={len(task.resposta or '')}"
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
