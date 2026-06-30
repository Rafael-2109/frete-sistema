"""Tools MCP de handoff de sessao (F1): transferir_para + devolver_ao_principal.
Espelha resolver_mcp_tool.py. Registro gated por should_register_handoff()."""
from __future__ import annotations
import logging
from contextlib import nullcontext
from sqlalchemy.orm.attributes import flag_modified

from app.agente.tools._mcp_enhanced import enhanced_tool, create_enhanced_mcp_server

logger = logging.getLogger(__name__)


def should_register_handoff(mode: str, specialist_profile) -> bool:
    """Regra de exposicao da tool de handoff (consumida por client._build_options).

    Registra `transferir_para` SOMENTE:
      - no cliente PRINCIPAL (`specialist_profile is None`) — o ESPECIALISTA usa o
        executor atomico, NAO re-delega (anti multi-spawn, spec F1); e
      - em modo 'on' — 'shadow' e' medicao PURA (o agent_router decide+persiste,
        mas a tool de TROCA nao deve existir onde nada troca). Em 'on' o stream
        TROCA para o especialista (8b ATIVO): o principal expoe transferir_para
        para iniciar o handoff; o especialista expoe so' devolver_ao_principal.
    'off' (default) nunca registra -> behavior-equivalente ao main."""
    return mode == 'on' and specialist_profile is None


def _app_context():
    """Hooks/handlers MCP async do SDK rodam FORA do Flask app_context (thread
    daemon do pool). Sem isto, AgentSession.query / db.session.commit() explodem
    com RuntimeError('Working outside of application context'). Reusa o atual se
    existir, senao cria um. Mesmo padrao de subagent_checkpoint._app_context()."""
    try:
        from flask import current_app as _probe
        _ = _probe.name
        return nullcontext()
    except RuntimeError:
        from app import create_app
        return create_app().app_context()


def _apply_transfer(session_id, especialista, objetivo, entidades, saldo=None) -> dict:
    from app import db
    from app.agente.models import AgentSession
    from app.agente.sdk.handoff_context import build_handoff_context
    with _app_context():
        s = AgentSession.query.filter_by(session_id=session_id).first()
        if not s:
            return {"ok": False, "erro": "sessao_nao_encontrada"}
        ctx = build_handoff_context(objetivo=objetivo, entidades=entidades, saldo=saldo)
        s.set_agente_ativo(especialista)
        _data = s.data or {}
        _data['handoff_context'] = ctx
        s.data = _data
        flag_modified(s, 'data')
        db.session.commit()
        logger.info(f"[HANDOFF] transfer -> {especialista} session={session_id[:12]} "
                    f"tokens={ctx['tokens_estimados']} truncado={ctx['truncado']}")
        return {"ok": True, "especialista": especialista,
                "tokens": ctx["tokens_estimados"]}


def _apply_devolver(session_id) -> dict:
    from app import db
    from app.agente.models import AgentSession
    with _app_context():
        s = AgentSession.query.filter_by(session_id=session_id).first()
        if not s:
            return {"ok": False, "erro": "sessao_nao_encontrada"}
        s.set_agente_ativo('principal')
        _data = s.data or {}
        _data.pop('handoff_context', None)
        # 8b: reseta o flag de injecao p/ um proximo handoff re-injetar o bloco
        # no 1o turno do especialista (hooks.py UserPromptSubmit).
        _data.pop('handoff_context_injected', None)
        s.data = _data
        flag_modified(s, 'data')
        db.session.commit()
        logger.info(f"[HANDOFF] devolver -> principal session={session_id[:12]}")
        return {"ok": True}


@enhanced_tool(
    name="transferir_para",
    description=("Transfere a conducao do assunto para um especialista quente "
                "(piloto: gestor-recebimento), passando um handoff MAGRO "
                "(entidades/saldo/objetivo, NUNCA a conversa). Use quando o "
                "assunto e' recebimento (vincular/conciliar NF x PO) e exige "
                "dialogo continuo no dominio."),
    input_schema={"type": "object", "required": ["especialista", "objetivo"],
                  "additionalProperties": False,
                  "properties": {
                      "especialista": {"type": "string", "enum": ["gestor-recebimento"]},
                      "objetivo": {"type": "string"},
                      "entidades": {"type": "object"},
                      "saldo": {"type": "object"}}},
)
async def transferir_para(args: dict) -> dict:
    from app.agente.config.permissions import get_current_session_id
    sid = get_current_session_id()
    out = _apply_transfer(sid, args["especialista"], args["objetivo"],
                          args.get("entidades") or {}, args.get("saldo"))
    return {"content": [{"type": "text", "text": str(out)}], "structuredContent": out}


@enhanced_tool(
    name="devolver_ao_principal",
    description=("Devolve a conducao ao agente principal quando o assunto sai do "
                "escopo do especialista. Limpa o handoff_context."),
    input_schema={"type": "object", "additionalProperties": False, "properties": {}},
)
async def devolver_ao_principal(args: dict) -> dict:
    from app.agente.config.permissions import get_current_session_id
    out = _apply_devolver(get_current_session_id())
    return {"content": [{"type": "text", "text": str(out)}], "structuredContent": out}


# Server do PRINCIPAL: pode transferir o assunto (e devolver, no-op se ja' principal).
handoff_server = create_enhanced_mcp_server(
    "handoff", version="1.0.0", tools=[transferir_para, devolver_ao_principal])

# Server do ESPECIALISTA (8b): SO' devolver_ao_principal. Nao expoe transferir_para
# ao especialista — ele NAO re-delega (recria o multi-spawn caro); quando o assunto
# sai do escopo, devolve ao principal.
handoff_devolver_server = create_enhanced_mcp_server(
    "handoff", version="1.0.0", tools=[devolver_ao_principal])
