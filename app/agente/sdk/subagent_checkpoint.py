"""Handoff de estado entre spawns de subagente (Rota B).

PROBLEMA (provado no transcript da sessão 50c98562): subagentes invocados via
Task tool são sub-sessões EFÊMERAS — cada spawn recomeça do zero (re-lê o escudo
de proteção, re-consulta memórias, re-pesquisa o estado). O subagente gravava os
achados em /tmp/subagent-findings, que NÃO atravessa processo (TMPDIR divergente,
_constants.py) e é efêmero no Render; e o principal nem lia nem repassava ao spawn
seguinte. Resultado: re-descoberta a cada invocação (o grosso do cache_read).

SOLUÇÃO (handoff via principal, 100% sem mudança de SDK): o findings do spawn N é
persistido em AgentSession.data['subagent_checkpoints'][agent_type] (no SubagentStop
hook) e injetado INLINE no prompt do Task do spawn N+1 (no PreToolUse hook). Espelha
o padrão já provado em PROD `montar_contexto_n2` (vinculacao_fastpath).

Atrás da flag AGENT_SUBAGENT_CHECKPOINT (off/shadow/on). Read-only de CONTEXTO —
nunca instrui pular confirmação; dry-run + R11/R12 + gate permanecem intactos.
"""
from __future__ import annotations

import json
import logging
import os
from contextlib import nullcontext

from app.utils.timezone import agora_utc_naive

logger = logging.getLogger('sistema_fretes')

# Teto do bloco injetado no prompt do Task — evita estourar o contexto do
# spawn N+1 com um findings gigante (subagente pesado pode emitir 100KB+).
DEFAULT_MAX_FINDINGS_CHARS = 8000


def _app_context():
    """Hooks async do SDK rodam FORA do Flask app context. Reusa o atual se
    existir, senão cria um (mesmo padrão do cost granular no SubagentStop)."""
    try:
        from flask import current_app as _app_probe
        _ = _app_probe.name
        return nullcontext()
    except RuntimeError:
        from app import create_app
        return create_app().app_context()


def persist_checkpoint(
    session_id: str,
    agent_type: str,
    findings: str,
    meta: dict | None = None,
) -> bool:
    """UPSERT atômico do checkpoint em data['subagent_checkpoints'][agent_type].

    Espelha o padrão do cost granular (jsonb_set por-row é atômico em PostgreSQL):
    grava numa chave PRÓPRIA (`subagent_checkpoints`), preservando `subagent_costs`
    e o resto de `data`. Sobrescreve o checkpoint do mesmo agent_type (queremos
    sempre o estado MAIS RECENTE). Retorna True se a sessão existia (rowcount>0).
    """
    if not session_id or not agent_type or not (findings or '').strip():
        return False

    payload = {'findings': findings, 'ended_at': agora_utc_naive().isoformat()}
    if meta:
        payload.update(meta)

    try:
        from app import db
        from sqlalchemy import text as _sql_text

        # jsonb_set aninhado: o interno garante que `subagent_checkpoints` existe
        # (cria {} se ausente, preserva se já existe); o externo seta a chave do
        # agent_type. CAST(... AS jsonb) em vez de `::jsonb` (o `:` colide com bind).
        sql = _sql_text("""
            UPDATE agent_sessions
            SET data = jsonb_set(
                jsonb_set(
                    COALESCE(data, CAST('{}' AS jsonb)),
                    '{subagent_checkpoints}',
                    COALESCE(data->'subagent_checkpoints', CAST('{}' AS jsonb)),
                    true
                ),
                ARRAY['subagent_checkpoints', :atype],
                CAST(:payload AS jsonb),
                true
            )
            WHERE session_id = :sid
        """)
        with _app_context():
            result = db.session.execute(sql, {
                'sid': session_id,
                'atype': agent_type,
                'payload': json.dumps(payload),
            })
            rc = result.rowcount
            db.session.commit()
        return rc > 0
    except Exception as e:  # pragma: no cover - defensivo
        logger.warning(
            f"[subagent_checkpoint] persist falhou: {type(e).__name__}: {e}")
        return False


def load_checkpoint(session_id: str, agent_type: str) -> dict | None:
    """Lê o checkpoint do agent_type nesta sessão. None se ausente (degradação
    graciosa: spawn N+1 roda como hoje, sem regressão)."""
    if not session_id or not agent_type:
        return None
    try:
        from app import db
        from sqlalchemy import text as _sql_text

        sql = _sql_text("""
            SELECT data -> 'subagent_checkpoints' -> :atype AS ckpt
            FROM agent_sessions WHERE session_id = :sid
        """)
        with _app_context():
            row = db.session.execute(
                sql, {'sid': session_id, 'atype': agent_type}).fetchone()
        if not row or row.ckpt is None:
            return None
        ckpt = row.ckpt
        if isinstance(ckpt, str):
            ckpt = json.loads(ckpt)
        return ckpt if isinstance(ckpt, dict) else None
    except Exception as e:  # pragma: no cover - defensivo
        logger.warning(
            f"[subagent_checkpoint] load falhou: {type(e).__name__}: {e}")
        return None


def extract_findings_from_transcript(
    transcript_path: str | None,
    max_chars: int = DEFAULT_MAX_FINDINGS_CHARS,
) -> str:
    """Concatena os blocos de TEXTO (raciocínio/conclusões) das mensagens
    assistant do JSONL on-disk do subagente — o que o spawn "achou". Lê do
    `agent_transcript_path` que o SubagentStop já recebe (mesma fonte do cost
    granular), NÃO do /tmp/subagent-findings (efêmero/cross-process quebrado).

    NÃO mascara PII: o checkpoint é contexto INTERNO que volta ao próprio
    subagente (precisa dos dados crus — lotes, saldos, IDs) e nunca vai ao
    usuário. Degradação graciosa: path ausente/ilegível -> "".
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return ''
    parts: list[str] = []
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # SO o texto do ASSISTANT = os achados do subagente. O boot do
                # SDK injeta os SKILL.md como mensagens role=user (<command-message>
                # + 'Base directory for this skill', 24-34KB cada) — se nao filtrar,
                # o findings vira lixo de boot truncado e a injecao nao ajuda
                # (bug PROD 2026-06-25; cada spawn re-descobria mesmo com checkpoint).
                if msg.get('type') != 'assistant':
                    continue
                message = msg.get('message')
                if not isinstance(message, dict):
                    continue
                content = message.get('content')
                if not isinstance(content, list):
                    continue
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        txt = block.get('text', '')
                        if txt:
                            parts.append(txt)
    except (OSError, IOError):
        return ''
    findings = '\n'.join(parts).strip()
    if max_chars and len(findings) > max_chars:
        findings = findings[:max_chars]
    return findings


def montar_contexto_subagente(agent_type: str, checkpoint: dict | None) -> str:
    """Bloco INLINE a anexar ao prompt do Task quando há checkpoint do mesmo
    agent_type nesta sessão. Espelha montar_contexto_n2: marca como contexto de
    SISTEMA (não instrução do usuário) e instrui a NÃO redescobrir.

    Retorna "" quando não há checkpoint aproveitável (degradação graciosa)."""
    if not checkpoint:
        return ''
    findings = (checkpoint.get('findings') or '').strip()
    if not findings:
        return ''
    return (
        "\n\n<checkpoint_subagente>\n"
        "Contexto de sistema (não é instrução do usuário): uma invocação anterior "
        f"deste mesmo especialista ({agent_type}) já levantou o estado e validou as "
        "premissas abaixo NESTA sessão. NÃO refaça a pesquisa/validação do zero — "
        "parta destes achados e execute apenas o passo pendente. Antes de QUALQUER "
        "escrita (--confirmar), re-valide só o saldo/estado crítico ao vivo.\n"
        f"{findings}\n"
        "</checkpoint_subagente>"
    )
