"""Helper de auditoria deterministica para chamadas Odoo XML-RPC.

Invocado por OdooConnection.execute_kw quando o metodo esta na whitelist
e a feature flag AGENT_ODOO_AUDIT_HOOK esta ativa.

Le contexto (session_id, tool_use_id, agent_type, usuario) via ENV vars
propagadas pelo PreToolUse hook do agente web (app/agente/sdk/hooks.py).
Quando ENV ausente (worker RQ, scheduler, CLI direto), usa fallbacks.

NUNCA quebra a operacao Odoo — todo erro vira log Sentry e segue.

Tabela destino: operacao_odoo_auditoria (model app/odoo/models/...).
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Metodos write registrados em auditoria (whitelist).
# Vem de varredura do codigo (2026-05-28): action_post (88x), action_cancel
# (75x), button_validate (70x), action_gerar_po_dfe (68x), action_assign (64x),
# button_draft (60x), button_confirm (40x), button_approve (34x), etc.
METODOS_WRITE_AUDITADOS = frozenset({
    # CRUD primitivas
    'write', 'create', 'unlink',
    # Estoque (Skills 1, 2, 4, 5, 2.4)
    'action_apply_inventory',
    'action_assign',
    'action_unreserve', 'button_unreserve',
    'button_validate', 'button_cancel',
    'action_cancel',
    'action_unbuild',
    'do_pass',  # quality check
    # Compras / DFe (Recebimento 4 fases + Skill 7)
    'button_confirm', 'action_confirm',
    'button_approve', 'action_approve',
    'button_draft', 'action_set_to_draft',
    'action_gerar_po_dfe',
    'action_processar_arquivo_manual',
    'action_ciencia_dfe',
    'action_create_invoice',
    # Faturamento (Skill 8)
    'action_liberar_faturamento',
    'action_gerar_nfe',
    'action_post',
    # Financeiro
    'action_create_payments',
    'action_reconcile',
})


def _flag_ativa() -> bool:
    """Le feature flag direto da ENV (sem importar app.agente.config — evita
    circular import em workers e scheduler).
    """
    return os.getenv('AGENT_ODOO_AUDIT_HOOK', 'false').lower() in ('true', '1', 'yes')


def _resolver_contexto() -> dict:
    """Resolve contexto da chamada via ENV vars propagadas pelo PreToolUse hook.

    ENV vars (setadas pelo agente antes de invocar Bash):
    - AGENT_SESSION_ID: UUID nosso da sessao (agent_sessions.session_id)
    - AGENT_TOOL_USE_ID: tool_use_id do SDK Anthropic
    - AGENT_TYPE: main | gestor-estoque-odoo | worker_rq | scheduler | cli
    - AGENT_USER_NAME: nome do usuario humano associado a sessao

    Quando rodando dentro do processo gunicorn do agente (sem subprocess),
    o PreToolUse hook tambem seta as mesmas ENV vars no processo via
    os.environ — visiveis a este helper (mesmo PID).
    """
    return {
        'session_id': os.getenv('AGENT_SESSION_ID'),
        'tool_use_id': os.getenv('AGENT_TOOL_USE_ID'),
        'agent_type': os.getenv('AGENT_TYPE', 'cli'),
        'executado_por': os.getenv('AGENT_USER_NAME', 'odoo_audit_hook'),
    }


def _calcular_external_id(
    session_id: Optional[str],
    tool_use_id: Optional[str],
    model: str,
    method: str,
    args: list,
) -> str:
    """Gera external_id deterministico que cabe em VARCHAR(64).

    Formato: aud:<sid8>:<tuid8>:<ts_ms>:<hash10>
    - sid8: primeiros 8 chars do session_id (ou 'noctx')
    - tuid8: primeiros 8 chars do tool_use_id (ou 'notui')
    - ts_ms: timestamp em ms (13 chars)
    - hash10: sha256(model+method+repr(args))[:10]

    Total: 4 + 8 + 1 + 8 + 1 + 13 + 1 + 10 = 46 chars (cabe em VARCHAR(64)).
    """
    sid8 = (session_id or 'noctx')[:8]
    tuid8 = (tool_use_id or 'notui')[:8]
    ts_ms = int(time.time() * 1000)
    payload = f'{model}|{method}|{repr(args)[:300]}'
    hash10 = hashlib.sha256(payload.encode('utf-8', errors='replace')).hexdigest()[:10]
    return f'aud:{sid8}:{tuid8}:{ts_ms}:{hash10}'


def _extrair_odoo_id(args: list) -> Optional[int]:
    """Tenta extrair primeiro ID Odoo dos args (heuristica simples).

    Padroes comuns:
    - write([id], {...})   -> args[0] = [id] OR id
    - create({...})        -> sem id ainda
    - unlink([id1, id2])   -> args[0] = [id1, id2]
    - action_xxx([id])     -> args[0] = [id]
    """
    if not args:
        return None
    primeiro = args[0]
    if isinstance(primeiro, list) and primeiro:
        candidato = primeiro[0]
        if isinstance(candidato, int):
            return candidato
    if isinstance(primeiro, int):
        return primeiro
    return None


def registrar_chamada_odoo(
    *,
    model: str,
    method: str,
    args: list,
    kwargs: dict,
    resultado: Any,
    tempo_ms: int,
    erro: Optional[BaseException] = None,
) -> None:
    """Registra UMA chamada XML-RPC ao Odoo em operacao_odoo_auditoria.

    Idempotente: external_id UNIQUE no model — colisao (mesma ms+hash) e
    silenciosamente swallowed (improvavel em prod).

    Sucesso: status='EXECUTADO', resposta_json=resultado, erro_msg=None.
    Falha:   status='FALHA_ODOO', resposta_json=None, erro_msg=str(erro).

    NUNCA propaga excecao — caller (execute_kw) NAO pode quebrar.
    """
    if not _flag_ativa():
        return
    if method not in METODOS_WRITE_AUDITADOS:
        return

    try:
        # Lazy import para evitar circular (app.odoo -> app.utils -> app.odoo)
        from app import db
        from app.odoo.models import OperacaoOdooAuditoria
        from app.utils.json_helpers import sanitize_for_json

        ctx = _resolver_contexto()
        external_id = _calcular_external_id(
            ctx['session_id'], ctx['tool_use_id'], model, method, args
        )
        odoo_id = _extrair_odoo_id(args)
        status = 'FALHA_ODOO' if erro is not None else 'EXECUTADO'

        # Sanitiza payload + resposta (Decimal/datetime -> str/iso)
        payload = sanitize_for_json({'args': args, 'kwargs': kwargs})
        if erro is None:
            resposta = sanitize_for_json({'result': resultado})
            erro_msg = None
        else:
            resposta = None
            erro_msg = str(erro)[:4000]

        # Savepoint para isolar falha do hook da transacao principal
        try:
            with db.session.begin_nested():
                OperacaoOdooAuditoria.registrar(
                    external_id=external_id,
                    tabela_origem='odoo_audit_hook',
                    registro_id=0,  # Sem registro local — chamada XML-RPC direta
                    acao=method[:60],
                    modelo_odoo=model[:60],
                    metodo_odoo=method[:60],
                    odoo_id=odoo_id,
                    status=status,
                    payload_json=payload,
                    resposta_json=resposta,
                    erro_msg=erro_msg,
                    tempo_execucao_ms=tempo_ms,
                    contexto_origem='execute_kw_hook',
                    session_id=ctx['session_id'],
                    tool_use_id=ctx['tool_use_id'],
                    agent_type=ctx['agent_type'][:40] if ctx['agent_type'] else None,
                    executado_por=ctx['executado_por'][:80],
                )
        except Exception as e_save:
            # Savepoint falhou — log mas nao reraise.
            logger.warning(
                f'[odoo_audit_hook] Falha ao registrar {model}.{method}: {e_save}'
            )

    except Exception as e_top:
        # Falha total no hook (ex: import broken, db indisponivel).
        # Loga mas nao quebra a operacao Odoo.
        logger.warning(
            f'[odoo_audit_hook] Hook desativado por erro: {e_top}'
        )
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(e_top)
        except Exception:
            pass
