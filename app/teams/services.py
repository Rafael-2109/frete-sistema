"""
Servicos para integracao Teams Bot <-> Agente Claude SDK.

Recebe mensagens do bot Azure Function, envia para o Agente Claude,
e retorna a resposta como texto puro (cards sao montados na Azure Function).

Suporta sessoes persistentes por conversation_id do Teams.
"""

import logging
import asyncio
import re
import hashlib
import time
import uuid
from dataclasses import dataclass, field
from datetime import timedelta

from app.utils.timezone import agora_utc_naive
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# StreamResult — valor de retorno tipado de _obter_resposta_agente*
# ═══════════════════════════════════════════════════════════════════════
# Fase 4 extensao (2026-04-21): substitui tupla de 6 campos por dataclass
# imutavel com campos nomeados. Permite adicionar cache_read_tokens /
# cache_creation_tokens sem quebrar call sites (que usam acesso por nome).
#
# Backward compat: metodos `__iter__` para suportar unpacking posicional
# legacy (se algum call site ainda fizer `a, b, c, d, e, f = result`).
# Mas o padrao novo e acessar via atributo (stream.input_tokens, etc.).
@dataclass(frozen=True)
class StreamResult:
    """Resultado de uma chamada _obter_resposta_agente* (sync ou streaming).

    Campos:
        resposta_texto: texto final retornado ao usuario (pode ser None em erro)
        sdk_session_id: novo sdk_session_id emitido pelo SDK (para resume)
        input_tokens: tokens de input uncached
        output_tokens: tokens de output
        tools_used: lista de nomes de tools invocadas (granularidade via stream)
        cost_usd: custo reportado pelo SDK (ResultMessage.total_cost_usd)
        cache_read_tokens: tokens servidos do cache (Fase 4 observabilidade)
        cache_creation_tokens: tokens escritos no cache
        resposta_card: card Adaptive estruturado (Fase 1 MVP, 2026-04-22) —
            quando presente, a Azure Function renderiza via build_<template>_card
            em vez de enviar texto puro. Formato: {"template": str, "data": dict}.
    """
    resposta_texto: Optional[str]
    sdk_session_id: Optional[str]
    input_tokens: int = 0
    output_tokens: int = 0
    tools_used: List[str] = field(default_factory=list)
    cost_usd: float = 0.0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    resposta_card: Optional[Dict[str, Any]] = None
    # Fix code-reviewer (R-CLI-CRASH 2026-05-12): flag explicita propagada
    # quando o CLI subprocess crashou tentando --resume sessao ausente do
    # session_store (client.py:2238 CASO 1). Antes, o retry funcionava por
    # acidente (texto vazio + falta de event 'error' → check `not resposta_texto`
    # disparava retry). Agora a flag torna o caso auditavel e protege contra
    # regressao futura: se algum handler entre client.py e services.py
    # adicionar texto sintetico, o retry continua sendo forcado.
    recoverable_resume_failure: bool = False

    def __iter__(self):
        # Backward compat: permite unpacking posicional antigo de 6 campos.
        # Codigo novo DEVE usar acesso por atributo.
        yield self.resposta_texto
        yield self.sdk_session_id
        yield self.input_tokens
        yield self.output_tokens
        yield self.tools_used
        yield self.cost_usd


def _error_stream_result(
    resposta_texto: Optional[str] = None,
    sdk_session_id: Optional[str] = None,
) -> StreamResult:
    """Helper para paths de erro/timeout. Zero tokens e custo."""
    return StreamResult(
        resposta_texto=resposta_texto,
        sdk_session_id=sdk_session_id,
        input_tokens=0,
        output_tokens=0,
        tools_used=[],
        cost_usd=0.0,
        cache_read_tokens=0,
        cache_creation_tokens=0,
    )


def _get_or_create_teams_user(
    usuario: str,
    aad_id: Optional[str] = None,
    email: Optional[str] = None,
) -> Optional[int]:
    """
    Resolve o usuário do Teams para um Usuario real no banco (hierarquia Fase A).

    Hierarquia de resolução (plano 2026-06-10-teams-melhorias):
    1. ``aad_id`` vinculado (``Usuario.find_by_teams_aad_id``) — vínculo
       confirmado por código de pareamento, e-mail ou admin. Fonte mais forte.
    2. Auto-match por e-mail corporativo (case-insensitive) — conveniência de
       1ª linha; grava o vínculo (``teams_vinculo_origem='email'``) se o
       usuário ainda não tem ``teams_user_id`` (nunca sobrescreve vínculo).
    3. Fallback legacy: auto-cadastro de usuário "fantasma" com e-mail
       determinístico ``teams_{md5(nome)}@teams.nacomgoya.local``
       (comportamento original — preservado para quem não vinculou).

    Args:
        usuario: Nome do usuário do Teams (ex: "Rafael Nascimento")
        aad_id: Azure AD object ID (activity.from_property.aad_object_id)
        email: e-mail corporativo via TeamsInfo.get_member (pode faltar)

    Returns:
        int: user_id real na tabela usuarios, ou None se falhar
    """
    if not usuario or not usuario.strip():
        return None

    try:
        from sqlalchemy import func as sa_func
        from app.auth.models import Usuario
        from app import db

        # 1) Vínculo confirmado por AAD object ID
        vinculado = Usuario.find_by_teams_aad_id(aad_id)
        if vinculado:
            return vinculado.id

        # 2) Auto-match por e-mail corporativo (o mesmo que aparece no "Contato")
        if email and email.strip():
            por_email = Usuario.query.filter(
                sa_func.lower(Usuario.email) == email.strip().lower(),
                Usuario.status == 'ativo',
            ).first()
            if por_email:
                if aad_id and not por_email.teams_user_id:
                    por_email.teams_user_id = str(aad_id)
                    por_email.teams_vinculo_origem = 'email'
                    db.session.commit()
                    logger.info(
                        f"[TEAMS-BOT] Vínculo automático por e-mail: "
                        f"user_id={por_email.id} email={email} aad={str(aad_id)[:12]}..."
                    )
                return por_email.id

        # 3) Fallback legacy: fantasma com email determinístico pelo nome
        normalized = usuario.lower().strip()
        hash_hex = hashlib.md5(normalized.encode('utf-8')).hexdigest()[:12]
        teams_email = f"teams_{hash_hex}@teams.nacomgoya.local"

        # Busca usuário existente pelo email
        existing = Usuario.query.filter_by(email=teams_email).first()
        if existing:
            return existing.id

        # Auto-cadastra novo usuário
        new_user = Usuario(
            nome=usuario.strip(),
            email=teams_email,
            perfil='logistica',
            status='ativo',
            empresa='Nacom Goya (Teams)',
            cargo='Usuário Teams',
            sistema_logistica=True,
            sistema_motochefe=False,
            aprovado_em=agora_utc_naive(),
            aprovado_por='sistema-teams-bot',
            observacoes='Auto-cadastrado via Teams Bot',
        )
        new_user.set_senha(uuid.uuid4().hex)  # Senha aleatória — ninguém precisa saber
        db.session.add(new_user)
        db.session.commit()

        logger.info(
            f"[TEAMS-BOT] Usuário auto-cadastrado: "
            f"id={new_user.id} nome='{usuario}' email='{teams_email}'"
        )
        return new_user.id

    except Exception as e:
        logger.error(f"[TEAMS-BOT] Erro ao obter/criar usuário Teams: {e}", exc_info=True)
        return None


def _merge_linha_a_linha(
    table_name: str, column_name: str, fantasma_id: int, real_id: int,
) -> tuple:
    """Fallback do merge quando o UPDATE em massa colide com UNIQUE.

    Reaponta linha a linha via ctid (independe da PK da tabela); linhas que
    violam constraint ficam no fantasma e são contadas como colisão.

    Returns:
        (migradas, colisoes)
    """
    from sqlalchemy import text as sql_text
    from app import db

    migradas = 0
    colisoes = 0
    try:
        ctids = [r[0] for r in db.session.execute(sql_text(
            f'SELECT ctid FROM "{table_name}" WHERE "{column_name}" = :fid'
        ), {'fid': fantasma_id}).fetchall()]
    except Exception:
        db.session.rollback()
        return (0, 0)

    for ctid in ctids:
        try:
            db.session.execute(sql_text(
                f'UPDATE "{table_name}" SET "{column_name}" = :rid '
                f'WHERE ctid = :ctid AND "{column_name}" = :fid'
            ), {'rid': real_id, 'ctid': ctid, 'fid': fantasma_id})
            db.session.commit()
            migradas += 1
        except Exception:
            db.session.rollback()
            colisoes += 1
    return (migradas, colisoes)


def merge_usuario_teams(fantasma_id: int, real_id: int, dry_run: bool = True) -> dict:
    """Reaponta TODAS as FKs de `usuarios(id)` do usuário fantasma para o real.

    Descobre as FKs dinamicamente via information_schema (cobre agent_sessions,
    agent_memories, agent_step, teams_tasks, agent_invocation_metrics, etc. sem
    lista hardcoded). Colisões UNIQUE são capturadas POR TABELA (loga e segue).

    Args:
        fantasma_id: id do usuário @teams.nacomgoya.local
        real_id: id do usuário web verdadeiro
        dry_run: True = apenas conta linhas afetadas, sem UPDATE

    Returns:
        {"tabelas": {tabela.coluna: linhas}, "erros": [str], "dry_run": bool}
    """
    from sqlalchemy import text as sql_text
    from app import db

    resultado = {"tabelas": {}, "erros": [], "colisoes": {}, "dry_run": dry_run}
    fks = db.session.execute(sql_text("""
        SELECT tc.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND ccu.table_name = 'usuarios' AND ccu.column_name = 'id'
    """)).fetchall()

    # Complemento: tabelas do dominio do agente SEM FK formal (agent_sessions,
    # agent_step, agent_session_costs, etc. — user_id e' Integer sem ForeignKey
    # no modelo). Escopo restrito por prefixo para nao reapontar user_id de
    # outros dominios (ex.: ids de usuario Odoo).
    sem_fk = db.session.execute(sql_text("""
        SELECT c.table_name, c.column_name
        FROM information_schema.columns c
        WHERE c.column_name IN ('user_id', 'created_by')
          AND (c.table_name LIKE 'agent%' OR c.table_name LIKE 'teams%'
               OR c.table_name LIKE 'claude%')
    """)).fetchall()

    alvos = sorted({(t, c) for t, c in list(fks) + list(sem_fk)})

    for table_name, column_name in alvos:
        chave = f"{table_name}.{column_name}"
        try:
            if dry_run:
                count = db.session.execute(sql_text(
                    f'SELECT COUNT(*) FROM "{table_name}" WHERE "{column_name}" = :fid'
                ), {'fid': fantasma_id}).scalar() or 0
            else:
                count = db.session.execute(sql_text(
                    f'UPDATE "{table_name}" SET "{column_name}" = :rid '
                    f'WHERE "{column_name}" = :fid'
                ), {'rid': real_id, 'fid': fantasma_id}).rowcount
                db.session.commit()
            if count:
                resultado["tabelas"][chave] = count
        except Exception as tbl_err:
            db.session.rollback()
            # Bug PROD 2026-06-11 (caso Rafael): UNIQUE (ex.: agent_memories
            # uq_user_memory_path) derruba o UPDATE em massa e a tabela INTEIRA
            # ficava para tras ('0 memorias' com 19 existentes). Fallback linha
            # a linha via ctid: nao-colidentes migram; colisoes sao CONTADAS.
            migradas, colisoes = _merge_linha_a_linha(
                table_name, column_name, fantasma_id, real_id,
            )
            if migradas:
                resultado["tabelas"][chave] = migradas
            if colisoes:
                resultado["colisoes"][chave] = colisoes
                logger.warning(
                    f"[TEAMS-MERGE] {chave}: {colisoes} linha(s) colidiram "
                    f"(ficam no fantasma); {migradas} migraram. Causa: {tbl_err}"
                )
            if not migradas and not colisoes:
                resultado["erros"].append(f"{chave}: {tbl_err}")
                logger.warning(f"[TEAMS-MERGE] {chave} falhou (segue): {tbl_err}")

    if not dry_run:
        try:
            from app.auth.models import Usuario
            fantasma = db.session.get(Usuario, fantasma_id)
            if fantasma:
                fantasma.status = 'bloqueado'
                fantasma.observacoes = (
                    f"{fantasma.observacoes or ''} | MERGED -> user {real_id} "
                    f"em {agora_utc_naive().strftime('%d/%m/%Y %H:%M')}"
                ).strip(' |')
                db.session.commit()
        except Exception as blk_err:
            db.session.rollback()
            resultado["erros"].append(f"bloqueio fantasma: {blk_err}")

    return resultado


def _merge_usuario_fantasma(nome: Optional[str], real_id: int) -> str:
    """Localiza o usuário fantasma pelo nome (e-mail MD5 determinístico) e migra
    o histórico para o usuário real. Best-effort — chamado pelo fast-path
    'vincular CODIGO' logo após gravar o vínculo (Task A5/A7).

    Returns:
        Resumo curto para a resposta ao usuário ("" se nada a migrar).
    """
    if not nome or not str(nome).strip():
        return ""
    try:
        from app.auth.models import Usuario

        normalized = str(nome).lower().strip()
        hash_hex = hashlib.md5(normalized.encode('utf-8')).hexdigest()[:12]
        teams_email = f"teams_{hash_hex}@teams.nacomgoya.local"
        fantasma = Usuario.query.filter_by(email=teams_email).first()
        if not fantasma or fantasma.id == real_id:
            return ""

        resultado = merge_usuario_teams(fantasma.id, real_id, dry_run=False)
        sessoes = resultado["tabelas"].get("agent_sessions.user_id", 0)
        memorias = resultado["tabelas"].get("agent_memories.user_id", 0)
        colisoes_mem = resultado.get("colisoes", {}).get("agent_memories.user_id", 0)
        logger.info(
            f"[TEAMS-MERGE] Fantasma {fantasma.id} -> real {real_id}: "
            f"{resultado['tabelas']} colisoes={resultado.get('colisoes')} "
            f"erros={len(resultado['erros'])}"
        )
        if sessoes or memorias or colisoes_mem:
            resumo = (
                f"Migrei seu histórico do Teams ({sessoes} conversas, "
                f"{memorias} memórias)."
            )
            if colisoes_mem:
                resumo += (
                    f" {colisoes_mem} memórias não migraram por já existirem "
                    f"no seu perfil web (mantive as do web)."
                )
            return resumo
        return ""
    except Exception as e:
        logger.warning(f"[TEAMS-MERGE] Merge best-effort falhou (ignorado): {e}")
        return ""


def _get_teams_context() -> str:
    """
    Gera contexto específico para Teams com data atual e instruções anti-verbosidade.

    Returns:
        str: Contexto formatado para prefixar a mensagem do usuário
    """
    data_atual = agora_utc_naive().strftime("%d/%m/%Y")
    dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    dia_semana = dias_semana[agora_utc_naive().weekday()]

    return f"""[CONTEXTO: Resposta via Microsoft Teams]

DATA ATUAL: {dia_semana}, {data_atual}

REGRAS OBRIGATÓRIAS:
1. SEJA DIRETO - Vá direto ao ponto, sem introduções
2. AÇÃO SILENCIOSA - NUNCA diga "vou consultar...", "deixa eu verificar...", "analisando..."
   Execute as consultas SILENCIOSAMENTE e retorne APENAS o resultado
3. SEM MARKDOWN COMPLEXO - NÃO use tabelas (| col |), headers (##), code blocks
   Use apenas: texto simples, listas com "- item", negrito com *texto*
4. TAMANHO IDEAL - Até 3000 caracteres. Se precisar de mais, pode: respostas
   longas são divididas em múltiplas mensagens automaticamente (limite ~24000)
5. PERGUNTAS INTERATIVAS - Se precisar de mais informações do usuário, use AskUserQuestion normalmente. O sistema apresentará as opções via Adaptive Card no Teams.

PROIBIDO:
- "Vou consultar o banco de dados..."
- "Deixa eu verificar os pedidos..."
- "Analisando os dados disponíveis..."
- "Primeiro preciso..."

CORRETO:
- "Encontrei 3 pedidos do Atacadão: [lista]"
- "O estoque de palmito é 1.500 caixas"
- "NF 144533 foi entregue em 15/01/2025"

PERGUNTA DO USUÁRIO:
"""


_RESET_CONVERSA_RE = re.compile(
    r'^\s*(nova|resetar|reiniciar)\s+(conversa|sess[aã]o)\s*[.!]?\s*$',
    re.IGNORECASE,
)


def _should_reset_conversa(mensagem: Optional[str]) -> bool:
    """True se a mensagem é EXATAMENTE um pedido de reset de contexto (Fase D).

    Conservador: qualquer palavra a mais ("nova conversa sobre X") NÃO intercepta.
    """
    if not mensagem or not str(mensagem).strip():
        return False
    return bool(_RESET_CONVERSA_RE.match(str(mensagem).strip()))


def _executar_reset_conversa(conversation_id: str) -> dict:
    """Expira a sessão ativa da conversa SEM esperar o TTL de 2h (Fase D).

    Empurra updated_at da AgentSession mais recente da conversa para o passado
    (> TTL) — a próxima mensagem cria sessão nova via _get_or_create_teams_session.
    NUNCA levanta.
    """
    try:
        from sqlalchemy import text as sql_text
        from app import db

        base_session_id = f"teams_{conversation_id}"
        if len(base_session_id) > 250:
            conv_hash = hashlib.md5(conversation_id.encode()).hexdigest()[:20]
            base_session_id = f"teams_{conv_hash}"

        db.session.execute(sql_text(
            "UPDATE agent_sessions SET updated_at = updated_at - interval '1 day' "
            "WHERE session_id LIKE :pattern"
        ), {'pattern': f'{base_session_id}%'})
        db.session.commit()
        return {
            "ok": True,
            "resposta": "Contexto reiniciado — sua próxima mensagem começa uma conversa nova.",
        }
    except Exception as e:
        logger.warning(f"[TEAMS-RESET] Falhou (ignorado): {e}")
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
        return {"ok": False, "resposta": None}


def _montar_prompt_teams(mensagem: str, usuario: str, conversation_type: str = "personal") -> str:
    """Monta o prompt do turno: contexto Teams + etiqueta de falante (grupos).

    Fase B (falante do turno): em conversa de GRUPO ('groupChat'/'channel'),
    prefixa ``[Mensagem de: <nome>]`` para o agente saber QUEM está falando —
    a sessão é por conversa, com vários falantes. Em 'personal' não polui.
    """
    contexto = _get_teams_context()
    if conversation_type in ("groupChat", "channel") and usuario:
        return f"{contexto}[Mensagem de: {usuario}]\n{mensagem}"
    return contexto + mensagem


def _construir_fallback_xml(session) -> Optional[str]:
    """Constrói o fallback XML de resume (últimas 10 msgs do JSONB).

    Usado pelos paths sync e streaming (era duplicado inline nos dois).
    O hook UserPromptSubmit injeta como additionalContext quando o resume do
    SDK falha. Fase B: inclui ``author`` quando presente (grupos).
    """
    if not session:
        return None
    try:
        messages = session.get_messages() or []
        if not messages or len(messages) <= 1:
            return None
        recent = messages[-10:]
        parts = ['<conversation_history_fallback reason="resume_failed">']
        for msg in recent:
            role = msg.get('role', 'unknown')
            content = (msg.get('content', '') or '')[:2000]
            if not content:
                continue
            author = msg.get('author')
            if author:
                parts.append(f'<msg role="{role}" author="{author}">{content}</msg>')
            else:
                parts.append(f'<msg role="{role}">{content}</msg>')
        parts.append('</conversation_history_fallback>')
        xml = '\n'.join(parts)
        logger.debug(
            f"[TEAMS-BOT] Fallback XML preparado: {len(messages)} msgs, {len(xml)} chars"
        )
        return xml
    except Exception as fb_err:
        logger.debug(f"[TEAMS-BOT] Fallback XML falhou (ignorado): {fb_err}")
        return None


def _enrich_tool_name(tool_name: Any, tool_input: Any) -> str:
    """Enriquece o nome de Skill/Agent com o alvo invocado (espelha o canal
    web em ``chat.py:861-870``).

    Por que: o avaliador de efetividade de skill (``build_skill_windows`` ->
    ``_skill_from_tools``) casa ``"Skill:<nome>"`` em ``msg["tools_used"]``. O
    Teams gravava o bare ``"Skill"`` (sem o nome) -> zero janelas de avaliacao no
    canal Teams (debito documentado em ``app/agente/CLAUDE.md``). Enriquecer aqui
    liga o avaliador no Teams sem tocar o canal web.

    Tools comuns (Read, Bash, mcp__*) passam inalteradas.
    """
    if not isinstance(tool_name, str):
        tool_name = str(tool_name)
    if not isinstance(tool_input, dict):
        return tool_name
    if tool_name == 'Skill':
        skill = (tool_input.get('skill') or '').strip()
        return f"Skill:{skill}" if skill else tool_name
    if tool_name == 'Agent':
        agent_type = (tool_input.get('subagent_type') or '').strip()
        if agent_type:
            return f"Agent:{agent_type}"
        desc = (tool_input.get('description') or '')[:50].strip()
        return f"Agent:{desc}" if desc else tool_name
    return tool_name


# TTL de sessão do Teams: após N horas de inatividade, cria nova sessão.
# Fase 2 (2026-04-21): extraido para env var (default 2h). Reduz cache
# creation em sessoes longas abandonadas e retomadas horas depois.
# Para rollback ao comportamento antigo: TEAMS_SESSION_TTL_HOURS=4
from app.agente.config.feature_flags import ( # noqa: E402
    TEAMS_SESSION_TTL_HOURS as _TEAMS_SESSION_TTL_HOURS,
)
TEAMS_SESSION_TTL_HOURS = _TEAMS_SESSION_TTL_HOURS


# ═══════════════════════════════════════════════════════════════
# HELPERS UX — Model routing e feedback visual
# ═══════════════════════════════════════════════════════════════

_TOOL_DISPLAY_NAMES = {
    'mcp__sql__consultar_sql': 'Consultando dados...',
    'ToolSearch': 'Preparando ferramentas...',
    'Bash': 'Executando operação...',
    'Skill': 'Executando skill...',
    'mcp__render__query_render_postgres': 'Consultando banco...',
}


def _tool_display_name(tool_name: str) -> str:
    """Retorna label amigável para exibir durante tool call."""
    if not tool_name:
        return 'Processando...'
    for key, label in _TOOL_DISPLAY_NAMES.items():
        if key in tool_name:
            return label
    if 'mcp__' in tool_name:
        return 'Consultando dados...'
    return 'Processando...'


def _select_model_for_message(mensagem: str) -> str:
    """Seleciona modelo com base em padroes de intent da mensagem.

    Fase 1 (2026-04-21): delega a app.agente.sdk.model_router.select_model,
    compartilhado entre Teams e Web. Patterns evolvem em um local unico.

    Mantém compatibilidade com v2 anterior: quando SMART_MODEL_ROUTING=false,
    retorna TEAMS_DEFAULT_MODEL. Caso contrario, roteia baseado em patterns
    observados em producao (padrao_nf_po, saudacoes, follow-ups, etc.).
    """
    from app.agente.config.feature_flags import (
        TEAMS_SMART_MODEL_ROUTING, TEAMS_DEFAULT_MODEL, TEAMS_FAST_MODEL,
    )
    if not TEAMS_SMART_MODEL_ROUTING:
        return TEAMS_DEFAULT_MODEL

    from app.agente.sdk.model_router import select_model
    chosen, _reason = select_model(
        mensagem or "",
        default_model=TEAMS_DEFAULT_MODEL,
        fast_model=TEAMS_FAST_MODEL,
    )
    return chosen


def _gravar_agent_step_teams(session, user_id, model, sync_result):
    """Onda 0 / S0a — grava agent_step (channel='teams') no PRIMARY (INV-1; INV-3 caminho proprio Teams).

    Best-effort (INV-6): falha NAO quebra a persistencia da resposta nem o turno.
    Idempotente via step_uid UNIQUE — chamado nos 2 pontos de persistencia (primario
    + fallback de re-fetch pos-SSL-drop) sem duplicar. Derivar turn_seq DEPOIS de
    add_user_message+add_assistant_message (mesma semantica do canal web).
    """
    try:
        # Simetria com o canal web (chat.py _save_messages_to_db grava o passo com
        # base na mensagem do usuario, mesmo sem texto final — turno so-tools ou
        # erro): mantem o dataset de agent_step consistente entre canais p/ o
        # flywheel (Onda 1). O call site sempre roda add_user_message antes.
        if session is None:
            return
        from app.agente.models import AgentStep
        _msgs = (session.data or {}).get('messages', [])
        _turn_seq = sum(1 for m in _msgs if m.get('role') == 'user')
        AgentStep.insert_step(
            step_uid=f"{session.session_id}:{_turn_seq}",
            session_id=session.session_id,
            user_id=user_id,
            channel='teams',
            model=model,
            input_tokens=getattr(sync_result, 'input_tokens', 0) or 0,
            output_tokens=getattr(sync_result, 'output_tokens', 0) or 0,
            tools_used=getattr(sync_result, 'tools_used', None) or None,
        )
        # Onda 1 / E1 — captura frustração no outcome_signal (flag OFF por default)
        from app.agente.config.feature_flags import USE_AGENT_QUALITY_SPINE
        if USE_AGENT_QUALITY_SPINE:
            from app.agente.services.sentiment_detector import get_last_frustration_score
            _fscore = get_last_frustration_score(session.session_id)
            if _fscore is not None:
                AgentStep.update_outcome(
                    f"{session.session_id}:{_turn_seq}",
                    {'frustration_score': _fscore},
                )
    except Exception as e:
        logger.warning(f"[TEAMS-BOT] agent_step nao gravado (best-effort): {e}")


def _commit_with_retry(log_prefix: str = "[TEAMS]") -> bool:
    """
    Commit com retry para conexoes PostgreSQL stale (SSL dropped pelo Render).

    P1-1: Apos db.session.close(), objetos ficam detached. Em vez de commitar
    transacao vazia, fazemos apenas o commit inicial e logamos warning no retry
    (o caller deve re-fetch objetos se necessario).

    Args:
        log_prefix: Prefixo para mensagens de log

    Returns:
        True se commit bem-sucedido, False se falhou
    """
    from app import db

    try:
        db.session.commit()
        return True
    except Exception as commit_err:
        err_str = str(commit_err).lower()
        if 'ssl' in err_str or 'connection' in err_str or 'closed' in err_str:
            logger.warning(
                f"{log_prefix} Conexão perdida no commit, reconectando: {commit_err}"
            )
            db.session.rollback()
            db.session.close()  # Devolve conexão stale ao pool, obtém fresh
            # P1-1: Apos close(), objetos estao detached — commit commitaria transacao vazia.
            # Retorna False para sinalizar ao caller que precisa re-fetch e re-apply.
            logger.warning(
                f"{log_prefix} Conexão resetada. Objetos detached — caller deve re-fetch."
            )
            return False
        else:
            raise  # Erro não relacionado a conexão — propaga


def processar_mensagem_bot(
    mensagem: str,
    usuario: str,
    conversation_id: str = None,
) -> str:
    """
    Processa mensagem do bot Teams enviando para o Agente Claude SDK.

    Mantém sessão persistente por conversation_id do Teams.

    Args:
        mensagem: Texto da mensagem do usuario
        usuario: Nome do usuario que enviou
        conversation_id: ID da conversa do Teams para sessao persistente

    Returns:
        str: Texto da resposta do agente

    Raises:
        ValueError: Se mensagem estiver vazia
        RuntimeError: Se o agente nao retornar resposta
    """
    logger.info(
        f"[TEAMS-BOT] Processando mensagem de '{usuario}' "
        f"conv={conversation_id[:30] if conversation_id else 'N/A'}...: "
        f"{mensagem[:100]}..."
    )

    if not mensagem or not mensagem.strip():
        raise ValueError("Mensagem vazia recebida")

    # Obter ou criar usuário real no banco para o usuário do Teams
    teams_user_id = _get_or_create_teams_user(usuario)

    # Obter ou criar sessao para esta conversa Teams
    session = _get_or_create_teams_session(conversation_id, usuario, user_id=teams_user_id)

    # Obter sdk_session_id para resume (se existir)
    sdk_session_id = session.get_sdk_session_id() if session else None

    if sdk_session_id:
        logger.info(f"[TEAMS-BOT] Resuming sessao SDK: {sdk_session_id[:20]}...")

    # Configurar session context para permissions.py (AskUserQuestion + gating Estoque)
    teams_session_id = session.session_id if session else None
    if teams_session_id:
        from app.agente.config.permissions import (
            set_current_session_id,
            set_current_user_id as set_perm_user_id,
            cleanup_session_context,
            can_use_tool as agent_can_use_tool,
        )
        set_current_session_id(teams_session_id)
        # Restricao Estoque (2026-05-26): registra user_id para can_use_tool
        # avaliar gating de skills WRITE de ajuste/Indisponivel.
        if teams_user_id:
            set_perm_user_id(teams_user_id)
    else:
        from app.agente.config.permissions import can_use_tool as agent_can_use_tool

    # C4: Configurar user_id nos ContextVars de MCP tools (Memory + Session)
    # Sem isso, tools falham com RuntimeError("user_id não definido") se
    # _build_options() não for chamado (ex: path persistente re-ativado).
    if teams_user_id:
        try:
            from app.agente.tools.memory_mcp_tool import set_current_user_id as set_memory_user_id
            set_memory_user_id(teams_user_id)
        except ImportError:
            pass
        try:
            from app.agente.tools.session_search_tool import set_current_user_id as set_session_user_id
            set_session_user_id(teams_user_id)
        except ImportError:
            pass

    try:
        # FASE 3 fast-path (plano 2026-06-08): vincular/desvincular pedido X na
        # nota Y (Gabriella) resolvido por roteamento DETERMINISTICO (regex N0 +
        # Haiku N1) reusando validar_dfe/consolidar_pos/reverter_consolidacao,
        # SEM o subagente gestor-recebimento (Opus xhigh). ANTES do baseline.
        # Anomalia (status!=aprovado, PO diverge, NF ambigua) ou None -> baseline/
        # LLM abaixo (N2). Ver R-EXEC-6 e sdk/vinculacao_fastpath.py.
        _vinc_resposta = None
        # Mensagem ao LLM pode ganhar <diagnostico_fastpath> (anomalia do
        # fast-path); persistencia continua com `mensagem` original.
        mensagem_llm = mensagem
        try:
            from app.agente.config.feature_flags import AGENT_VINCULACAO_FASTPATH
            from app.agente.sdk.vinculacao_fastpath import (
                executar_vinculacao_fastpath, montar_contexto_n2,
            )
            if AGENT_VINCULACAO_FASTPATH:
                _vinc = executar_vinculacao_fastpath(
                    mensagem, session_id=teams_session_id, user_id=teams_user_id,
                )
                if _vinc and _vinc.get("ok"):
                    _vinc_resposta = _vinc["resposta"]
                    logger.info(f"[TEAMS-BOT] vinculacao fast-path (sem subagente) user={teams_user_id}")
                elif _vinc:
                    _ctx_n2 = montar_contexto_n2(_vinc)
                    if _ctx_n2:
                        mensagem_llm = mensagem + _ctx_n2
                        logger.info(
                            "[TEAMS-BOT] vinculacao fast-path anomalia -> "
                            "diagnostico anexado ao prompt (N2)"
                        )
        except Exception as _ve:
            logger.warning(f"[TEAMS-BOT] fast-path vinculacao ignorado (-> LLM): {_ve}")

        # FASE 1 fast-path (plano docs/superpowers/plans/2026-06-06-reducao-custo-
        # agente-fast-path): "atualizar baseline" trivial e resolvido DETERMINISTI-
        # CAMENTE, sem LLM. SO o caminho feliz e interceptado; qualquer variacao
        # (data passada, formato, CarVia, pergunta) ou falha de execucao (ok=False)
        # CAI no fluxo normal do LLM abaixo. Ver R-EXEC-6 e sdk/baseline_fastpath.py.
        _fp_resposta = None
        try:
            from app.agente.config.feature_flags import AGENT_BASELINE_FASTPATH
            from app.agente.sdk.baseline_fastpath import (
                should_intercept_baseline, executar_baseline_fastpath,
            )
            if AGENT_BASELINE_FASTPATH and should_intercept_baseline(mensagem):
                _fp = executar_baseline_fastpath(
                    session_id=teams_session_id, user_id=teams_user_id,
                )
                if _fp.get("ok"):
                    _fp_resposta = _fp["resposta"]
                    logger.info(f"[TEAMS-BOT] baseline fast-path (sem LLM) user={teams_user_id}")
                else:
                    logger.info("[TEAMS-BOT] baseline fast-path falhou -> fluxo LLM")
        except Exception as _fp_err:
            logger.warning(f"[TEAMS-BOT] fast-path baseline ignorado (-> LLM): {_fp_err}")

        if _vinc_resposta is not None:
            # FASE 3: pula o LLM E o subagente; REUSA a persistencia/cleanup abaixo
            # (StreamResult sintetico: 0 tokens, mantem o sdk_session_id atual).
            selected_model = 'fastpath-vinculacao'
            _sync_result = _error_stream_result(
                resposta_texto=_vinc_resposta, sdk_session_id=sdk_session_id,
            )
        elif _fp_resposta is not None:
            # Pula o LLM e REUSA a persistencia/post-session/cleanup abaixo
            # (StreamResult sintetico: 0 tokens, mantem o sdk_session_id atual).
            selected_model = 'fastpath-baseline'
            _sync_result = _error_stream_result(
                resposta_texto=_fp_resposta, sdk_session_id=sdk_session_id,
            )
        else:
            # C1: Smart model routing
            selected_model = _select_model_for_message(mensagem)
            logger.info(
                f"[TEAMS-BOT] Model routing: {selected_model} "
                f"para msg ({len(mensagem.split())} palavras)"
            )

            # Obter resposta do agente (com can_use_tool para graceful denial de AskUserQuestion)
            _sync_result = _obter_resposta_agente(
                mensagem=mensagem_llm,
                usuario=usuario,
                sdk_session_id=sdk_session_id,
                user_id=teams_user_id,
                can_use_tool=agent_can_use_tool,
                session=session,
                model=selected_model,
            )
        resposta_texto = _sync_result.resposta_texto
        new_sdk_session_id = _sync_result.sdk_session_id

        # Salvar mensagens e atualizar sdk_session_id
        if session:
            try:
                session.add_user_message(mensagem, author=usuario)
                if resposta_texto:
                    # Fase 4 (2026-04-21): persiste cache tokens por msg
                    session.add_assistant_message(
                        content=resposta_texto,
                        input_tokens=_sync_result.input_tokens,
                        output_tokens=_sync_result.output_tokens,
                        tools_used=_sync_result.tools_used if _sync_result.tools_used else None,
                        cache_read_tokens=_sync_result.cache_read_tokens,
                        cache_creation_tokens=_sync_result.cache_creation_tokens,
                    )
                if new_sdk_session_id and new_sdk_session_id != sdk_session_id:
                    session.set_sdk_session_id(new_sdk_session_id)
                    logger.info(f"[TEAMS-BOT] Novo sdk_session_id salvo: {new_sdk_session_id[:20]}...")

                # Onda 0 / S0a-teams: grava agent_step (best-effort, idempotente via step_uid)
                _gravar_agent_step_teams(session, teams_user_id, selected_model, _sync_result)

                # Commit com retry — conexão PostgreSQL pode cair durante requests longas (30-40s)
                # O agente processa tools enquanto a conexão fica idle → SSL dropped pelo Render.
                # P1-A: Se commit falhar (SSL dropped), re-fetch session e re-apply mensagens.
                commit_ok = _commit_with_retry("[TEAMS-BOT]")
                if not commit_ok:
                    logger.warning("[TEAMS-BOT] Commit falhou — re-fetching session para re-apply")
                    from app import db
                    from app.agente.models import AgentSession
                    session = AgentSession.query.filter_by(
                        session_id=teams_session_id
                    ).first()
                    if session:
                        session.add_user_message(mensagem, author=usuario)
                        if resposta_texto:
                            session.add_assistant_message(
                                content=resposta_texto,
                                input_tokens=_sync_result.input_tokens,
                                output_tokens=_sync_result.output_tokens,
                                tools_used=_sync_result.tools_used if _sync_result.tools_used else None,
                                cache_read_tokens=_sync_result.cache_read_tokens,
                                cache_creation_tokens=_sync_result.cache_creation_tokens,
                            )
                        if new_sdk_session_id and new_sdk_session_id != sdk_session_id:
                            session.set_sdk_session_id(new_sdk_session_id)
                        # Onda 0 / S0a-teams: grava agent_step no fallback (best-effort, idempotente)
                        _gravar_agent_step_teams(session, teams_user_id, selected_model, _sync_result)
                        db.session.commit()
                        logger.info("[TEAMS-BOT] Re-apply + commit bem-sucedido")
                    else:
                        logger.error("[TEAMS-BOT] Session nao encontrada no re-fetch")
            except Exception as e:
                logger.error(f"[TEAMS-BOT] Erro ao salvar sessao: {e}", exc_info=True)
                # Nao bloqueia resposta se falhar ao salvar

            # C2: Post-session processing (summarization, patterns, extraction, embedding)
            # Roda em non-daemon thread — daemon=True morria com reciclagem gunicorn,
            # impedindo toda a cadeia de aprendizado (summary → extração → memórias).
            # Fix: daemon=False garante conclusão (coerente com R1 do Teams CLAUDE.md).
            try:
                from flask import current_app
                _app = current_app._get_current_object()

                from threading import Thread
                from app.agente.routes import run_post_session_processing

                def _teams_post_session():
                    try:
                        with _app.app_context():
                            # Re-fetch session para evitar detached instance
                            from app.agente.models import AgentSession
                            fresh_session = AgentSession.query.filter_by(
                                session_id=teams_session_id
                            ).first()
                            if fresh_session:
                                logger.info(
                                    f"[TEAMS-BOT] Post-session iniciando "
                                    f"(user={teams_user_id}, session={teams_session_id[:8]}..., " # type: ignore
                                    f"msg_count={fresh_session.message_count}, "
                                    f"has_summary={fresh_session.summary is not None})"
                                )
                                run_post_session_processing(
                                    app=_app,
                                    session=fresh_session,
                                    session_id=teams_session_id,
                                    user_id=teams_user_id,
                                    user_message=mensagem,
                                    assistant_message=resposta_texto,
                                )
                                logger.info(
                                    f"[TEAMS-BOT] Post-session concluído "
                                    f"(user={teams_user_id}, session={teams_session_id[:8]}...)" # type: ignore
                                )
                            else:
                                logger.warning(
                                    f"[TEAMS-BOT] Post-session: session {teams_session_id[:8]}... " # type: ignore
                                    f"não encontrada no re-fetch"
                                )
                    except Exception as ps_err:
                        logger.warning(
                            f"[TEAMS-BOT] Post-session processing falhou (ignorado): {ps_err}",
                            exc_info=True,
                        )
                    finally:
                        try:
                            with _app.app_context():
                                from app import db
                                db.session.remove()
                        except Exception:
                            pass

                Thread(
                    target=_teams_post_session,
                    daemon=False,
                    name=f"teams-post-session-{teams_user_id}",
                ).start()
                logger.info(f"[TEAMS-BOT] Post-session processing disparado em background (non-daemon)")
            except Exception as ps_setup_err:
                logger.warning(f"[TEAMS-BOT] Erro ao disparar post-session (ignorado): {ps_setup_err}")

        if not resposta_texto:
            raise RuntimeError("O agente nao retornou uma resposta")

        logger.info(f"[TEAMS-BOT] Resposta obtida: {len(resposta_texto)} caracteres")
        return resposta_texto

    finally:
        # P0-2: Cleanup de _stream_context para evitar memory leak no path sincrono
        if teams_session_id:
            try:
                cleanup_session_context(teams_session_id)
            except Exception:
                pass  # Cleanup nao pode bloquear a resposta

        # Cleanup user_id cross-thread dos MCP tools (espelha finally do async path)
        try:
            from app.agente.tools.memory_mcp_tool import clear_current_user_id as clear_memory_uid
            clear_memory_uid()
        except (ImportError, Exception):
            pass
        try:
            from app.agente.tools.session_search_tool import clear_current_user_id as clear_session_uid
            clear_session_uid()
        except (ImportError, Exception):
            pass
        try:
            from app.agente.tools.text_to_sql_tool import clear_current_user_id as clear_sql_uid
            clear_sql_uid()
        except (ImportError, Exception):
            pass
        # Restricao Estoque (2026-05-26): cleanup user_id do permissions ContextVar
        try:
            from app.agente.config.permissions import clear_current_user_id as clear_perm_uid
            clear_perm_uid()
        except (ImportError, Exception):
            pass


def _get_or_create_teams_session(
    conversation_id: str,
    usuario: str,
    user_id: int = None,
):
    """
    Obtém ou cria AgentSession para uma conversa do Teams.

    Implementa TTL de 4 horas: se a última mensagem foi há mais de 4h,
    cria uma nova sessão para evitar contexto infinito em grupos ativos.

    Args:
        conversation_id: ID da conversa do Teams (ex: 19:xyz@thread.skype)
        usuario: Nome do usuário
        user_id: ID real do usuário na tabela usuarios (auto-cadastrado)

    Returns:
        AgentSession ou None se conversation_id não fornecido
    """
    if not conversation_id:
        logger.warning("[TEAMS-BOT] conversation_id nao fornecido — sessao nao persistente")
        return None

    try:
        from app.agente.models import AgentSession
        from app import db

        # Prefixo para identificar sessoes do Teams
        base_session_id = f"teams_{conversation_id}"

        # Garantir que session_id caiba no campo VARCHAR(255)
        if len(base_session_id) > 250:
            conv_hash = hashlib.md5(conversation_id.encode()).hexdigest()[:20]
            base_session_id = f"teams_{conv_hash}"

        # Busca sessão existente
        session = AgentSession.query.filter(
            AgentSession.session_id.like(f"{base_session_id}%")
        ).order_by(AgentSession.updated_at.desc()).first()

        # Verifica se sessão expirou (TTL de 4h)
        # Usa agora_utc_naive() (padrão do projeto) para comparação safe naive vs naive.
        # Try/except captura TypeError (comparação naive/aware) e AttributeError (campo None).
        session_expired = False
        if session and session.updated_at:
            try:
                ttl_threshold = agora_utc_naive() - timedelta(hours=TEAMS_SESSION_TTL_HOURS)
                # Forçar naive para dados legados que podem ter tzinfo
                updated_naive = session.updated_at.replace(tzinfo=None) if session.updated_at.tzinfo else session.updated_at
                if updated_naive < ttl_threshold:
                    session_expired = True
                    hours_inactive = (agora_utc_naive() - updated_naive).total_seconds() / 3600
                    logger.info(
                        f"[TEAMS-BOT] Sessao expirada ({hours_inactive:.1f}h inativa), "
                        f"criando nova"
                    )
            except (TypeError, AttributeError) as tz_err:
                logger.warning(f"[TEAMS-BOT] Erro ao verificar TTL, criando nova sessão: {tz_err}")
                session_expired = True

        # Cria nova sessão se não existe ou expirou
        if not session or session_expired:
            # Adiciona timestamp para sessões expiradas (permite histórico)
            if session_expired:
                session_id = f"{base_session_id}_{agora_utc_naive().strftime('%Y%m%d_%H%M%S')}"
            else:
                session_id = base_session_id

            from app.agente.config.feature_flags import TEAMS_DEFAULT_MODEL

            session = AgentSession(
                session_id=session_id,
                user_id=user_id,  # User real auto-cadastrado via _get_or_create_teams_user
                title=f"Teams - {usuario}",
                model=TEAMS_DEFAULT_MODEL,
                data={'messages': [], 'total_tokens': 0, 'channel': 'teams'},
            )
            db.session.add(session)
            db.session.commit()
            logger.info(f"[TEAMS-BOT] Nova sessao criada: {session_id[:50]}...")
        else:
            logger.info(
                f"[TEAMS-BOT] Sessao existente: {session.session_id[:50]}... "
                f"({session.message_count or 0} msgs)"
            )

        return session

    except Exception as e:
        logger.error(f"[TEAMS-BOT] Erro ao obter/criar sessao: {e}", exc_info=True)
        return None


def _obter_resposta_agente(
    mensagem: str,
    usuario: str,
    sdk_session_id: str = None,
    user_id: int = None,
    can_use_tool=None,
    session=None,
    model: str = None,
    conversation_type: str = "personal",
) -> StreamResult:
    """
    Obtem resposta do Agente Claude SDK (path sync, non-streaming).

    Args:
        mensagem: Mensagem do usuario
        usuario: Nome do usuario
        sdk_session_id: ID da sessao SDK para resume (opcional)
        user_id: ID real do usuario na tabela usuarios (para memorias)
        can_use_tool: Callback de permissão (para AskUserQuestion no Teams)
        session: AgentSession para backup/restore de transcript (Bug Teams #1)
        conversation_type: 'personal' | 'groupChat' | 'channel' (Fase B)

    Returns:
        StreamResult (dataclass imutavel) com campos nomeados.
        Compativel com unpacking posicional legacy de 6 elementos via __iter__.
    """
    try:
        from app.agente.sdk import get_client
        client = get_client()
    except Exception as e:
        logger.error(f"[TEAMS-BOT] Erro ao obter client: {e}")
        return _error_stream_result()

    # Fase B (SDK 0.1.64 SessionStore): restore_session_transcript removido.
    # SDK materializa JSONL de resume a partir de claude_session_store via
    # materialize_resume_session (automatico quando session_store setado em options).

    # FIX P1 (FaseB.1 review): Teams perdeu fallback XML ao remover
    # session_persistence. Se uma session Teams pre-existente nao foi migrada
    # (migration script pode ter pulado linhas), o SDK materialize retorna None
    # e subprocess spawna sem --resume — contexto perdido silenciosamente.
    # XML com ultimas 10 msgs do JSONB para o hook UserPromptSubmit injetar
    # como `additionalContext` quando resume falhar (helper compartilhado).
    resume_messages_fallback = _construir_fallback_xml(session)

    # Contexto Teams + etiqueta de falante quando grupo (Fase B)
    prompt_completo = _montar_prompt_teams(mensagem, usuario, conversation_type)

    # Modelo: usar override se fornecido, senão padrão
    if not model:
        from app.agente.config.feature_flags import TEAMS_DEFAULT_MODEL
        model = TEAMS_DEFAULT_MODEL

    # Pool key para path persistente (ClaudeSDKClient por sessão)
    our_session_id = session.session_id if session else None

    # wait_for(240s) garante que a thread SEMPRE termina em tempo finito,
    # mesmo se o SDK travar. Sem isso, uma thread non-daemon bloquearia
    # o shutdown do worker indefinidamente.
    MAX_TEAMS_RESPONSE_SECONDS = 240  # 4 min (Sonnet tipicamente 30-120s)

    try:
        async def _get_response_with_timeout():
            return await asyncio.wait_for(
                client.get_response(
                    prompt=prompt_completo,
                    user_name=usuario,
                    effort_level="medium",
                    sdk_session_id=sdk_session_id,
                    user_id=user_id,
                    model=model,
                    can_use_tool=can_use_tool,
                    our_session_id=our_session_id,
                    resume_messages_fallback=resume_messages_fallback,
                ),
                timeout=MAX_TEAMS_RESPONSE_SECONDS,
            )

        # ClaudeSDKClient persistente (v3) — daemon thread pool.
        # v2 (asyncio.run) desligado em 2026-03-27.
        from app.agente.sdk.client_pool import submit_coroutine
        future = submit_coroutine(_get_response_with_timeout())
        response = future.result(timeout=MAX_TEAMS_RESPONSE_SECONDS + 10)

        resposta_texto = _extrair_texto_resposta(response)
        new_sdk_session_id = getattr(response, 'session_id', None)

        # GAP 1/2: Extrair tokens e custo do response (non-streaming)
        ns_input_tokens = getattr(response, 'input_tokens', 0) or 0
        ns_output_tokens = getattr(response, 'output_tokens', 0) or 0
        ns_cost_usd = getattr(response, 'total_cost_usd', 0) or 0.0
        # Fase 4 (2026-04-21): cache tokens do SDK ResultMessage.usage
        ns_cache_read = getattr(response, 'cache_read_tokens', 0) or 0
        ns_cache_creation = getattr(response, 'cache_creation_tokens', 0) or 0
        # Non-streaming não tem granularidade de tool_call events
        ns_tools_used: List[str] = []

        # Fase B: backup_session_transcript removido — SDK TranscriptMirrorBatcher
        # persiste entries automaticamente em claude_session_store durante o stream.

        return StreamResult(
            resposta_texto=resposta_texto,
            sdk_session_id=new_sdk_session_id,
            input_tokens=ns_input_tokens,
            output_tokens=ns_output_tokens,
            tools_used=ns_tools_used,
            cost_usd=ns_cost_usd,
            cache_read_tokens=ns_cache_read,
            cache_creation_tokens=ns_cache_creation,
        )

    except asyncio.TimeoutError:
        future.cancel()  # Evita "Task was destroyed but it is pending"
        logger.error("[TEAMS-BOT] Timeout ao aguardar resposta do agente")
        return _error_stream_result(
            resposta_texto="Desculpe, a consulta demorou muito. Tente novamente com uma pergunta mais especifica.",
        )

    except Exception as e:
        future.cancel()  # Evita "Task was destroyed but it is pending"
        logger.error(f"[TEAMS-BOT] Erro ao obter resposta do agente: {e}", exc_info=True)
        return _error_stream_result(
            resposta_texto="Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.",
        )


def _extrair_texto_resposta(response) -> Optional[str]:
    """
    Extrai texto da resposta do SDK, tratando diferentes formatos.

    Fix 2: Trata AgentResponse com text vazio ANTES de cair no fallback str(response),
    evitando que "AgentResponse(text='', ...)" seja exibido ao usuario.

    Args:
        response: Objeto de resposta do SDK

    Returns:
        str: Texto extraido e limpo, ou None se vazio/erro
    """
    texto = None

    logger.debug(f"[TEAMS-BOT] Tipo de response: {type(response).__name__}")
    if hasattr(response, 'text'):
        logger.debug(f"[TEAMS-BOT] response.text presente: {bool(response.text)}")

    # Fix 2: Tratar AgentResponse (ou qualquer objeto com .text) ANTES do fallback
    # Se tem atributo .text, usa ele — mesmo que vazio (retorna None, não str(response))
    if hasattr(response, 'text'):
        if response.text:
            texto = response.text
            logger.debug(f"[TEAMS-BOT] Texto extraido via response.text: {len(texto)} chars")
        else:
            # response.text vazio — agente nao gerou texto (erro, CLIConnectionError, etc.)
            # Retorna None para que _obter_resposta_agente trate corretamente
            logger.warning(
                "[TEAMS-BOT] response.text vazio — agente nao gerou texto. "
                f"type={type(response).__name__}"
            )
            return None

    elif hasattr(response, 'content') and response.content:
        if isinstance(response.content, list):
            partes = []
            for bloco in response.content:
                if hasattr(bloco, 'text'):
                    partes.append(bloco.text)
                elif isinstance(bloco, dict) and 'text' in bloco:
                    partes.append(bloco['text'])
                elif isinstance(bloco, bytes):
                    partes.append(bloco.decode('utf-8', errors='replace'))
                elif isinstance(bloco, str):
                    partes.append(bloco)
                else:
                    partes.append(str(bloco))
            texto = '\n'.join(partes)
        elif isinstance(response.content, bytes):
            texto = response.content.decode('utf-8', errors='replace')
            logger.warning(f"[TEAMS-BOT] response.content era bytes, decodificado: {texto[:100]}")
        elif isinstance(response.content, str):
            texto = response.content
        else:
            texto = str(response.content)
            if texto.startswith("b'") or texto.startswith('b"'):
                logger.warning(f"[TEAMS-BOT] Detectado padrao bytes em str(): {texto[:50]}")
                texto = texto[2:-1]
    elif isinstance(response, str):
        texto = response
    elif isinstance(response, bytes):
        texto = response.decode('utf-8', errors='replace')
    else:
        # Fallback: converte para string mas NUNCA para objetos com __repr__
        # que geram "ClassName(field='', ...)"
        texto = str(response)
        # Detectar repr() de dataclass/namedtuple (ex: "AgentResponse(text='', ...)")
        type_name = type(response).__name__
        if texto.startswith(f"{type_name}("):
            logger.warning(
                f"[TEAMS-BOT] str(response) gerou repr() de {type_name} — ignorando"
            )
            return None
        if texto.startswith("b'") or texto.startswith('b"'):
            logger.warning(f"[TEAMS-BOT] str(response) gerou padrao bytes: {texto[:50]}")
            texto = texto[2:-1]

    if texto:
        texto = _sanitizar_texto(texto)

    return texto


def _sanitizar_texto(texto: str) -> str:
    """
    Sanitiza o texto para ser seguro em JSON e exibicao no Teams.

    Args:
        texto: Texto bruto

    Returns:
        str: Texto sanitizado
    """
    if not texto:
        return ""

    if isinstance(texto, bytes):
        texto = texto.decode('utf-8', errors='replace')

    # Remove caracteres de controle (exceto newline e tab)
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)

    # Converte aspas curvas para retas
    texto = texto.replace('\u201c', '"').replace('\u201d', '"')
    texto = texto.replace('\u2018', "'").replace('\u2019', "'")

    # Normaliza quebras de linha
    texto = texto.replace('\r\n', '\n').replace('\r', '\n')

    # Remove multiplas quebras de linha consecutivas
    texto = re.sub(r'\n{3,}', '\n\n', texto)

    # Teto DEFENSIVO (Fase D 2026-06-10): era 3800 e cortava respostas que a
    # function JA sabe dividir (_send_split_response, blocos de 3.5K). Teams
    # aceita ~28KB por mensagem; 24K da margem e a function splita em ~7 msgs.
    if len(texto) > 24000:
        corte = texto[:23800].rfind('\n\n')
        if corte > 16000:
            texto = texto[:corte] + '\n\n_(resposta truncada)_'
        else:
            corte = texto[:23800].rfind('\n')
            if corte > 16000:
                texto = texto[:corte] + '\n\n_(resposta truncada)_'
            else:
                texto = texto[:23800] + '\n\n_(resposta truncada)_'

    return texto.strip()


def _sanitizar_texto_parcial(texto: str) -> str:
    """
    Sanitiza texto parcial (streaming em progresso) para persistencia no DB.

    Igual a _sanitizar_texto() mas SEM truncagem a 3800 chars — o texto
    ainda esta crescendo e sera substituido pela versao final.

    Args:
        texto: Texto bruto parcial

    Returns:
        str: Texto sanitizado sem truncagem
    """
    if not texto:
        return ""

    if isinstance(texto, bytes):
        texto = texto.decode('utf-8', errors='replace')

    # Remove caracteres de controle (exceto newline e tab)
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)

    # Converte aspas curvas para retas
    texto = texto.replace('\u201c', '"').replace('\u201d', '"')
    texto = texto.replace('\u2018', "'").replace('\u2019', "'")

    # Normaliza quebras de linha
    texto = texto.replace('\r\n', '\n').replace('\r', '\n')

    # Remove multiplas quebras de linha consecutivas
    texto = re.sub(r'\n{3,}', '\n\n', texto)

    return texto.strip()


def _flush_partial_to_db(task_id: str, partial_text: str) -> None:
    """
    Persiste texto parcial em TeamsTask.resposta via raw SQL UPDATE.

    Usa raw SQL para evitar contaminacao da sessao ORM principal.
    O commit final em process_teams_task_async sobrescreve com texto
    definitivo via ORM.

    Args:
        task_id: ID da TeamsTask
        partial_text: Texto parcial acumulado ate o momento
    """
    from app import db
    from sqlalchemy import text as sql_text

    sanitized = _sanitizar_texto_parcial(partial_text)
    if not sanitized:
        return

    try:
        db.session.execute(
            sql_text(
                "UPDATE teams_tasks SET resposta = :resposta, updated_at = :now "
                "WHERE id = :task_id AND status = 'processing'"
            ),
            {'resposta': sanitized, 'task_id': task_id, 'now': agora_utc_naive()},
        )
        db.session.commit()
    except Exception as e:
        logger.warning(f"[TEAMS-STREAM] Erro ao flush parcial (ignorado): {e}")
        try:
            db.session.rollback()
        except Exception:
            pass


def _cleanup_orphan_claude_processes():
    """Kill orphan claude CLI subprocesses spawned by this worker.

    Chamado nos paths de erro/timeout de _obter_resposta_agente_streaming().
    Após CancelledError (DC-8) ou timeout, o subprocess claude pode ficar
    órfão consumindo CPU. Esta função encontra e mata esses processos.

    Usa pgrep para encontrar filhos diretos do PID atual com 'claude' no comando.
    Falha silenciosamente se pgrep não disponível ou sem processos.
    """
    try:
        import subprocess as sp
        import os
        import signal
        result = sp.run(
            ['pgrep', '-P', str(os.getpid()), '-f', 'claude'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid_str in pids:
                try:
                    pid = int(pid_str.strip())
                    os.kill(pid, signal.SIGTERM)
                    logger.warning(
                        f"[TEAMS-STREAM] Killed orphan claude process: pid={pid}"
                    )
                except (ValueError, ProcessLookupError, PermissionError):
                    pass
    except Exception as e:
        logger.debug(f"[TEAMS-STREAM] Orphan cleanup skipped: {e}")


def _obter_resposta_agente_streaming(
    mensagem: str,
    usuario: str,
    task_id: str,
    sdk_session_id: str = None,
    user_id: int = None,
    can_use_tool=None,
    session=None,
    app=None,
    model: str = None,
    conversation_type: str = "personal",
) -> StreamResult:
    """
    Obtem resposta do Agente Claude SDK com flush parcial progressivo ao DB.

    Mesmo contrato que _obter_resposta_agente() mas:
    - Itera sobre stream_response() em vez de get_response()
    - A cada TEAMS_STREAM_FLUSH_INTERVAL segundos, persiste texto parcial no DB
    - Flush imediato antes de tool_call (texto fica visivel enquanto tool executa)

    Args:
        mensagem: Mensagem do usuario
        usuario: Nome do usuario
        task_id: ID da TeamsTask (para flush parcial)
        sdk_session_id: ID da sessao SDK para resume (opcional)
        user_id: ID real do usuario na tabela usuarios (para memorias)
        can_use_tool: Callback de permissao (para AskUserQuestion no Teams)
        session: AgentSession para backup/restore de transcript (Bug Teams #1)
        conversation_type: 'personal' | 'groupChat' | 'channel' (Fase B)

    Returns:
        Tuple[resposta_texto, new_sdk_session_id, input_tokens, output_tokens, tools_used, cost_usd]
    """
    from app.agente.config.feature_flags import (
        TEAMS_STREAM_FLUSH_INTERVAL,
        TEAMS_TOOL_STATUS_FEEDBACK,
    )
    if not model:
        from app.agente.config.feature_flags import TEAMS_DEFAULT_MODEL
        model = TEAMS_DEFAULT_MODEL

    try:
        from app.agente.sdk import get_client
        client = get_client()
    except Exception as e:
        logger.error(f"[TEAMS-STREAM] Erro ao obter client: {e}")
        return _error_stream_result()

    # Fase B (SDK 0.1.64 SessionStore): restore_session_transcript removido.
    # SDK materializa JSONL de resume a partir de claude_session_store.

    # FIX P1 (FaseB.1 review): fallback XML defense in depth — se session
    # Teams pre-existente nao foi migrada, hook UserPromptSubmit injeta
    # contexto das ultimas 10 msgs via `additionalContext` (helper compartilhado).
    resume_messages_fallback = _construir_fallback_xml(session)

    # Contexto Teams + etiqueta de falante quando grupo (Fase B)
    prompt_completo = _montar_prompt_teams(mensagem, usuario, conversation_type)

    # Pool key para path persistente (ClaudeSDKClient por sessão)
    our_session_id = session.session_id if session else None

    # Timeout por inatividade: mata quando não há atividade real.
    # Cada chunk/tool_call recebido renova o deadline.
    # Sem teto absoluto — operações longas (subagentes Odoo, bulk) são legítimas.
    # Fase C: configurável via env (botão de rollback sem deploy).
    import os as _os
    INACTIVITY_TIMEOUT = int(_os.environ.get("TEAMS_INACTIVITY_TIMEOUT", "300"))

    try:
        async def _stream_with_flush():
            full_text = ""
            result_session_id = sdk_session_id
            errors = []
            tools_used = []
            tool_status_shown = False
            input_tokens = 0
            output_tokens = 0
            cost_usd = 0.0
            cache_read_tokens = 0
            cache_creation_tokens = 0
            recoverable_resume_failure = False  # R-CLI-CRASH 2026-05-12
            last_flush_time = time.monotonic()
            last_activity = time.monotonic()  # Renewal: atualizado a cada chunk
            stream_start = time.monotonic()   # Para log de elapsed time

            # Helper: flush com app_context para daemon thread.
            # No daemon thread, não há Flask app_context — wrapping necessário.
            # _safe_flush é sync (sem await), portanto atômico no event loop.
            _needs_app_ctx = False
            try:
                from flask import current_app
                _ = current_app.name
            except RuntimeError:
                _needs_app_ctx = True

            def _safe_flush(text):
                if not _needs_app_ctx:
                    _flush_partial_to_db(task_id, text)
                elif app:
                    with app.app_context():
                        _flush_partial_to_db(task_id, text)
                else:
                    logger.warning(
                        "[TEAMS-STREAM] Flush ignorado: sem app_context disponível"
                    )

            # Timeout por inatividade: cada chunk renova o deadline.
            # Se nenhum chunk chegar em INACTIVITY_TIMEOUT, dispara TimeoutError.
            stream_iter = client.stream_response(
                prompt=prompt_completo,
                user_name=usuario,
                model=model,
                effort_level="medium",
                sdk_session_id=sdk_session_id,
                can_use_tool=can_use_tool,
                user_id=user_id,
                our_session_id=our_session_id,
                resume_messages_fallback=resume_messages_fallback,
            ).__aiter__()

            while True:
                # Timeout por inatividade apenas — sem teto absoluto.
                # Operações com subagentes (Odoo XML-RPC, bulk) podem
                # levar 15-30 min legitimamente. Matar por wall-clock
                # desperdiça trabalho ativo (DC-9).
                now_mono = time.monotonic()
                chunk_timeout = INACTIVITY_TIMEOUT - (now_mono - last_activity)

                if chunk_timeout <= 0:
                    elapsed = now_mono - stream_start
                    inact = now_mono - last_activity
                    logger.warning(
                        f"[TEAMS-STREAM] Inactivity timeout "
                        f"- elapsed={elapsed:.0f}s "
                        f"inactivity={inact:.0f}s"
                    )
                    raise asyncio.TimeoutError(
                        f"Inactivity timeout ({inact:.0f}s)"
                    )

                try:
                    event = await asyncio.wait_for(
                        stream_iter.__anext__(),
                        timeout=chunk_timeout,
                    )
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    elapsed = time.monotonic() - stream_start
                    inact = time.monotonic() - last_activity
                    logger.warning(
                        f"[TEAMS-STREAM] Chunk timeout "
                        f"(elapsed={elapsed:.0f}s, "
                        f"inactivity={inact:.0f}s)"
                    )
                    raise

                # Renewal: cada chunk recebido renova deadline de inatividade
                last_activity = time.monotonic()

                if event.type == 'init':
                    result_session_id = event.content.get('session_id')

                elif event.type == 'text':
                    # D1: Se tinha status de tool, texto real substitui
                    if tool_status_shown and not full_text:
                        tool_status_shown = False
                    full_text += event.content

                    # Flush periodico ao DB
                    now = time.monotonic()
                    if now - last_flush_time >= TEAMS_STREAM_FLUSH_INTERVAL:
                        _safe_flush(full_text)
                        last_flush_time = now
                        logger.debug(
                            f"[TEAMS-STREAM] Flush parcial: "
                            f"task={task_id[:8]}... chars={len(full_text)}"
                        )

                elif event.type == 'tool_call':
                    # GAP 1: Rastrear tools usadas
                    raw_tool_name = event.content if isinstance(event.content, str) else str(event.content)
                    # F5: enriquecer Skill/Agent com o alvo invocado (espelha o
                    # canal web em chat.py:861) para o avaliador de efetividade de
                    # skill encontrar janelas no Teams (build_skill_windows casa
                    # 'Skill:<nome>'). Tools comuns passam inalteradas.
                    _tool_input = (event.metadata or {}).get('input') if getattr(event, 'metadata', None) else None
                    tool_name = _enrich_tool_name(raw_tool_name, _tool_input)
                    if tool_name and tool_name not in tools_used:
                        tools_used.append(tool_name)

                    # A1: Status visual durante tool calls (quando texto ainda não gerado)
                    if TEAMS_TOOL_STATUS_FEEDBACK and not full_text:
                        tool_label = _tool_display_name(raw_tool_name)
                        _safe_flush(f"_{tool_label}_")
                        tool_status_shown = True
                        logger.debug(
                            f"[TEAMS-STREAM] Tool status: "
                            f"task={task_id[:8]}... tool={tool_name}"
                        )
                    elif full_text:
                        _safe_flush(full_text)
                        logger.debug(
                            f"[TEAMS-STREAM] Flush pre-tool: "
                            f"task={task_id[:8]}... tool={event.content}"
                        )
                    last_flush_time = time.monotonic()

                elif event.type == 'error':
                    error_content = event.content if isinstance(event.content, str) else str(event.content)
                    errors.append(error_content)
                    logger.warning(
                        f"[TEAMS-STREAM] Error event: {error_content[:200]}"
                    )

                elif event.type == 'done':
                    done_session_id = event.content.get('session_id')
                    if done_session_id:
                        result_session_id = done_session_id
                    # GAP 1/2: Extrair tokens e custo do done event
                    input_tokens = event.content.get('input_tokens', 0) or 0
                    output_tokens = event.content.get('output_tokens', 0) or 0
                    cost_usd = event.content.get('total_cost_usd', 0.0) or 0.0
                    # Fase 4 (2026-04-21): cache tokens para observabilidade
                    cache_read_tokens = event.content.get('cache_read_tokens', 0) or 0
                    cache_creation_tokens = event.content.get('cache_creation_tokens', 0) or 0
                    # Fix code-reviewer (R-CLI-CRASH 2026-05-12): capturar flag
                    # explicita de recuperacao. Quando CLI crashou tentando
                    # --resume sessao ausente, client.py emite done com
                    # recoverable_resume_failure=True (sem event 'error').
                    # Caller forca retry na proxima iteracao.
                    if event.content.get('recoverable_resume_failure'):
                        recoverable_resume_failure = True
                        logger.warning(
                            f"[TEAMS-STREAM] recoverable_resume_failure detectado — "
                            f"forcando retry sem --resume na proxima tentativa"
                        )

            # Se full_text vazio mas houve errors, montar texto sintetico
            # EXCETO se o crash foi resume-related (caso 1 de client.py:2238) —
            # nesse caso o retry sem --resume eh esperado funcionar; texto sintetico
            # bypassaria o retry com mensagem confusa ao usuario.
            if not full_text and errors and not recoverable_resume_failure:
                full_text = (
                    "Desculpe, ocorreu um erro ao processar sua mensagem. "
                    "Tente novamente."
                )
                logger.warning(
                    f"[TEAMS-STREAM] text vazio com {len(errors)} errors. "
                    f"Errors: {'; '.join(errors[:3])}"
                )

            return StreamResult(
                resposta_texto=full_text,
                sdk_session_id=result_session_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                tools_used=tools_used,
                cost_usd=cost_usd,
                cache_read_tokens=cache_read_tokens,
                cache_creation_tokens=cache_creation_tokens,
                recoverable_resume_failure=recoverable_resume_failure,
            )

        # Deadline renewal integrado em _stream_with_flush (per-chunk timeout).
        # Wrapper direto sem asyncio.wait_for externo.
        # Fase C: heartbeat de 60s renova teams_tasks.updated_at enquanto a
        # coroutine esta viva — desacopla "thread viva" de "texto novo". Sem
        # isso, um tool call longo sem flush deixava updated_at parado e o
        # cleanup lazy (15 min) podia matar task legitima. Cancel no finally
        # cobre TODOS os exits, inclusive CancelledError (R7).
        def _heartbeat_update():
            from sqlalchemy import text as _hb_sql
            from app import db as _hb_db
            try:
                _hb_db.session.execute(_hb_sql(
                    "UPDATE teams_tasks SET updated_at = :now "
                    "WHERE id = :id AND status = 'processing'"
                ), {'now': agora_utc_naive(), 'id': task_id})
                _hb_db.session.commit()
            except Exception as hb_err:
                # Best-effort: heartbeat NUNCA derruba o stream (mesmo padrao
                # de sessao do _flush_partial_to_db — scoped session da thread
                # do event loop, sem remove() por operacao).
                logger.debug(f"[TEAMS-HEARTBEAT] Ignorado: {hb_err}")
                try:
                    _hb_db.session.rollback()
                except Exception:
                    pass

        # Fase E2: blocos proativos pos-polling — depois que o polling da
        # function morre (~8,5 min), cada tick do heartbeat verifica se ha
        # delta novo de resposta e o entrega como mensagem nova no Teams
        # (notify_function_partial decide: flag, elapsed, delta minimo).
        # Roda em EXECUTOR: requests e sincrono (timeout 30s) e bloquearia o
        # event loop COMPARTILHADO do pool — congelaria todos os streams.
        def _proactive_partial_check():
            try:
                from app.teams.proactive import notify_function_partial
                from app import db as _pp_db
                if app:
                    with app.app_context():
                        notify_function_partial(task_id)
                        # Sessao scoped da thread do executor (reusada por
                        # outros usos) — remove() devolve a conexao ao pool.
                        _pp_db.session.remove()
                else:
                    notify_function_partial(task_id)
            except Exception as pp_err:
                # Best-effort: bloco parcial NUNCA derruba o stream
                logger.debug(f"[TEAMS-PARTIAL] Check ignorado: {pp_err}")

        async def _heartbeat_loop():
            loop = asyncio.get_running_loop()
            while True:
                await asyncio.sleep(60)
                if app:
                    with app.app_context():
                        _heartbeat_update()
                else:
                    _heartbeat_update()
                await loop.run_in_executor(None, _proactive_partial_check)

        async def _stream_with_timeout():
            heartbeat_task = asyncio.create_task(_heartbeat_loop())
            try:
                return await _stream_with_flush()
            finally:
                heartbeat_task.cancel()

        # ClaudeSDKClient persistente (v3) — daemon thread pool.
        # v2 (asyncio.run) desligado em 2026-03-27.
        from app.agente.sdk.client_pool import submit_coroutine
        future = submit_coroutine(_stream_with_timeout())
        # Timeout da thread: safety net contra coroutine que nunca retorna.
        # Generoso (1h) porque o timeout real é por inatividade (240s) dentro da coroutine.
        THREAD_SAFETY_TIMEOUT = 3600
        stream_result: StreamResult = future.result(timeout=THREAD_SAFETY_TIMEOUT)

        # Extrair e sanitizar resposta (retorna novo StreamResult — dataclass e frozen)
        if stream_result.resposta_texto:
            stream_result = StreamResult(
                resposta_texto=_sanitizar_texto(stream_result.resposta_texto),
                sdk_session_id=stream_result.sdk_session_id,
                input_tokens=stream_result.input_tokens,
                output_tokens=stream_result.output_tokens,
                tools_used=stream_result.tools_used,
                cost_usd=stream_result.cost_usd,
                cache_read_tokens=stream_result.cache_read_tokens,
                cache_creation_tokens=stream_result.cache_creation_tokens,
                resposta_card=stream_result.resposta_card,
            )

        # Fase B: backup_session_transcript removido — SDK TranscriptMirrorBatcher
        # persiste entries automaticamente em claude_session_store.

        return stream_result

    except asyncio.TimeoutError:
        future.cancel()  # Evita "Task was destroyed but it is pending"
        logger.error("[TEAMS-STREAM] Timeout ao aguardar resposta do agente")
        _cleanup_orphan_claude_processes()
        return _error_stream_result(
            resposta_texto=(
                "Desculpe, a consulta demorou muito. "
                "Tente novamente com uma pergunta mais especifica."
            ),
        )

    except Exception as e:
        future.cancel()  # Evita "Task was destroyed but it is pending"
        logger.error(
            f"[TEAMS-STREAM] Erro ao obter resposta do agente: {e}",
            exc_info=True,
        )
        _cleanup_orphan_claude_processes()
        return _error_stream_result(
            resposta_texto=(
                "Desculpe, ocorreu um erro ao processar sua mensagem. "
                "Tente novamente."
            ),
        )


# ═══════════════════════════════════════════════════════════════
# PROCESSAMENTO ASSÍNCRONO (non-daemon threads)
# ═══════════════════════════════════════════════════════════════

def process_teams_task_async(
    app,
    task_id: str,
    mensagem: str,
    usuario: str,
    conversation_id: str,
    teams_user_id: Optional[int],
    usuario_aad_id: str = "",
    usuario_email: str = "",
    conversation_type: str = "personal",
) -> None:
    """
    Processa uma TeamsTask em thread non-daemon (background).

    Non-daemon garante que a thread sobrevive à reciclagem do worker
    (max_requests) — Python espera threads non-daemon terminarem antes
    de sair. O timeout de 240s em _obter_resposta_agente garante que
    a thread sempre termina em tempo finito.

    Fix 3: Recebe app como parametro ao inves de criar novo via create_app().
    Isso reutiliza o app context do gunicorn worker e evita problemas com
    inicializacao de hooks/MCP em ambiente headless.

    IMPORTANTE: Esta função roda no MESMO processo gunicorn (thread).
    Isso permite que pending_questions.py (threading.Event) funcione
    para AskUserQuestion cross-thread.

    Args:
        app: Flask app instance (do gunicorn worker)
        task_id: ID da TeamsTask
        mensagem: Texto da mensagem do usuário
        usuario: Nome do usuário
        conversation_id: ID da conversa do Teams
        teams_user_id: ID real do usuário na tabela usuarios
        usuario_aad_id: AAD object ID do falante (Fase A — fast-path vincular)
        usuario_email: e-mail corporativo do falante (Fase A)
        conversation_type: 'personal' | 'groupChat' | 'channel' (Fase B)
    """
    with app.app_context():
        from app.teams.models import TeamsTask
        from app import db
        from app.agente.config.permissions import (
            set_current_session_id,
            set_current_user_id as set_perm_user_id,
            clear_current_user_id as clear_perm_user_id,
            set_teams_task_context,
            cleanup_teams_task_context,
            cleanup_session_context,
            can_use_tool as agent_can_use_tool,
        )

        teams_session_id = None

        try:
            # Atualizar status para processing
            task = db.session.get(TeamsTask, task_id)
            if not task:
                logger.error(f"[TEAMS-ASYNC] Task {task_id} não encontrada")
                return

            task.status = 'processing'
            db.session.commit()

            logger.info(
                f"[TEAMS-ASYNC] Iniciando processamento: task={task_id[:8]}... "
                f"user={usuario} msg={mensagem[:80]}..."
            )

            # ── Fase A: fast-path 'vincular CODIGO' (meta-comando de pareamento).
            # ANTES de criar sessão: não polui o contexto da conversa nem chama
            # LLM. executar_* NUNCA levanta; o try cobre import/flag.
            try:
                from app.agente.config.feature_flags import AGENT_TEAMS_VINCULO_FASTPATH
                from app.agente.sdk.vincular_teams_fastpath import (
                    should_intercept_vincular, executar_vincular_fastpath,
                )
                if AGENT_TEAMS_VINCULO_FASTPATH and should_intercept_vincular(mensagem):
                    _v = executar_vincular_fastpath(
                        mensagem,
                        aad_id=usuario_aad_id,
                        email=usuario_email,
                        nome=usuario,
                        fallback_user_id=teams_user_id,
                    )
                    if _v.get("ok") and _v.get("resposta"):
                        task.status = 'completed'
                        task.resposta = _sanitizar_texto(_v["resposta"])
                        task.completed_at = agora_utc_naive()
                        if not _commit_with_retry("[TEAMS-VINCULO]"):
                            task = db.session.get(TeamsTask, task_id)
                            if task:
                                task.status = 'completed'
                                task.resposta = _sanitizar_texto(_v["resposta"])
                                task.completed_at = agora_utc_naive()
                                db.session.commit()
                        logger.info(
                            f"[TEAMS-VINCULO] fast-path respondido sem LLM: "
                            f"task={task_id[:8]}..."
                        )
                        _process_queued_task(app, conversation_id, task_id)
                        return
            except Exception as _vt_err:
                logger.warning(
                    f"[TEAMS-ASYNC] fast-path vincular ignorado (-> fluxo normal): {_vt_err}"
                )

            # ── Fase D: fast-path 'nova conversa' (reset de contexto sem
            # esperar o TTL de 2h). ANTES de _get_or_create_teams_session —
            # senao a propria mensagem renovaria o TTL da sessao antiga.
            try:
                if _should_reset_conversa(mensagem):
                    _r = _executar_reset_conversa(conversation_id)
                    if _r.get("ok") and _r.get("resposta"):
                        task.status = 'completed'
                        task.resposta = _sanitizar_texto(_r["resposta"])
                        task.completed_at = agora_utc_naive()
                        if not _commit_with_retry("[TEAMS-RESET]"):
                            task = db.session.get(TeamsTask, task_id)
                            if task:
                                task.status = 'completed'
                                task.resposta = _sanitizar_texto(_r["resposta"])
                                task.completed_at = agora_utc_naive()
                                db.session.commit()
                        logger.info(f"[TEAMS-RESET] Contexto reiniciado: conv={conversation_id[:30]}...")
                        _process_queued_task(app, conversation_id, task_id)
                        return
            except Exception as _rs_err:
                logger.warning(
                    f"[TEAMS-ASYNC] fast-path reset ignorado (-> fluxo normal): {_rs_err}"
                )

            # Obter/criar sessão
            session = _get_or_create_teams_session(
                conversation_id, usuario, user_id=teams_user_id
            )
            sdk_session_id = session.get_sdk_session_id() if session else None
            teams_session_id = session.session_id if session else f"teams_async_{task_id}"

            # Configurar context para permissions.py
            set_current_session_id(teams_session_id)
            set_teams_task_context(teams_session_id, task_id)
            # Restricao Estoque (2026-05-26): registra user_id para can_use_tool
            # avaliar gating de skills WRITE de ajuste/Indisponivel.
            if teams_user_id:
                set_perm_user_id(teams_user_id)

            # Configurar user_id nos ContextVars de MCP tools
            # (espelha app/agente/routes.py:310-312 e bot_routes.py:197-211)
            if teams_user_id:
                try:
                    from app.agente.tools.memory_mcp_tool import set_current_user_id as set_memory_user_id
                    set_memory_user_id(teams_user_id)
                except ImportError:
                    pass
                try:
                    from app.agente.tools.session_search_tool import set_current_user_id as set_session_user_id
                    set_session_user_id(teams_user_id)
                except ImportError:
                    pass
                try:
                    from app.agente.tools.text_to_sql_tool import set_current_user_id as set_sql_user_id
                    set_sql_user_id(teams_user_id)
                except ImportError:
                    pass

            # Fix 3b: Retry na chamada do agente (max 2 tentativas)
            resposta_texto = None
            new_sdk_session_id = None
            max_retries = 2

            from app.agente.config.feature_flags import TEAMS_PROGRESSIVE_STREAMING

            # GAP 1: Variáveis para captura de tokens/tools/cost
            input_tokens = 0
            output_tokens = 0
            tools_used: List[str] = []
            cost_usd = 0.0
            # Fase 4 (2026-04-21): cache tokens inicializados aqui para evitar
            # UnboundLocalError caso todas as tentativas do retry loop falhem
            # antes de atingir o bloco que os atribui (linhas 1464-1465).
            cache_read_tokens = 0
            cache_creation_tokens = 0

            # ── Fast-paths determinísticos (Fase A — corrige gap: antes só
            # existiam no path SYNC processar_mensagem_bot, morto desde que
            # TEAMS_ASYNC_MODE=true virou default). Ordem: vinculação NF×PO
            # (Gabriella) -> baseline (Marcus). Resposta de fast-path REUSA a
            # persistência abaixo (add_user/assistant_message + task completed)
            # via agent_result sintético com 0 tokens.
            agent_result: Optional[StreamResult] = None
            selected_model = None
            # Mensagem enviada ao LLM: pode ganhar o bloco <diagnostico_fastpath>
            # quando o fast-path abortou com anomalia (a persistencia e o model
            # routing continuam usando `mensagem` original).
            mensagem_llm = mensagem
            try:
                from app.agente.config.feature_flags import AGENT_VINCULACAO_FASTPATH
                from app.agente.sdk.vinculacao_fastpath import (
                    executar_vinculacao_fastpath, montar_contexto_n2,
                )
                if AGENT_VINCULACAO_FASTPATH:
                    _vinc = executar_vinculacao_fastpath(
                        mensagem, session_id=teams_session_id, user_id=teams_user_id,
                    )
                    if _vinc and _vinc.get("ok"):
                        agent_result = _error_stream_result(
                            resposta_texto=_vinc["resposta"],
                            sdk_session_id=sdk_session_id,
                        )
                        selected_model = 'fastpath-vinculacao'
                        logger.info(
                            f"[TEAMS-ASYNC] vinculacao fast-path (sem subagente) "
                            f"user={teams_user_id}"
                        )
                    elif _vinc:
                        # Anomalia diagnosticada: anexa ao prompt do N2 para o
                        # gestor-recebimento nao redescobrir do zero.
                        _ctx_n2 = montar_contexto_n2(_vinc)
                        if _ctx_n2:
                            mensagem_llm = mensagem + _ctx_n2
                            logger.info(
                                "[TEAMS-ASYNC] vinculacao fast-path anomalia -> "
                                "diagnostico anexado ao prompt (N2)"
                            )
            except Exception as _ve:
                logger.warning(f"[TEAMS-ASYNC] fast-path vinculacao ignorado (-> LLM): {_ve}")

            if agent_result is None:
                try:
                    from app.agente.config.feature_flags import AGENT_BASELINE_FASTPATH
                    from app.agente.sdk.baseline_fastpath import (
                        should_intercept_baseline, executar_baseline_fastpath,
                    )
                    if AGENT_BASELINE_FASTPATH and should_intercept_baseline(mensagem):
                        _fp = executar_baseline_fastpath(
                            session_id=teams_session_id, user_id=teams_user_id,
                        )
                        if _fp.get("ok"):
                            agent_result = _error_stream_result(
                                resposta_texto=_fp["resposta"],
                                sdk_session_id=sdk_session_id,
                            )
                            selected_model = 'fastpath-baseline'
                            logger.info(
                                f"[TEAMS-ASYNC] baseline fast-path (sem LLM) "
                                f"user={teams_user_id}"
                            )
                        else:
                            logger.info("[TEAMS-ASYNC] baseline fast-path falhou -> fluxo LLM")
                except Exception as _fp_err:
                    logger.warning(f"[TEAMS-ASYNC] fast-path baseline ignorado (-> LLM): {_fp_err}")

            if agent_result is not None:
                # Fast-path resolveu: pula o retry loop do LLM
                resposta_texto = agent_result.resposta_texto
                new_sdk_session_id = agent_result.sdk_session_id
                max_retries = 0
            else:
                # C1: Smart model routing
                selected_model = _select_model_for_message(mensagem)
                logger.info(
                    f"[TEAMS-ASYNC] Model routing: {selected_model} "
                    f"para msg ({len(mensagem.split())} palavras)"
                )

            # Prefixos de erro retornados por _obter_resposta_agente_*
            # NÃO devem ser aceitos como resposta válida pelo retry loop.
            _ERROR_PREFIXES = ("Desculpe, ocorreu um erro", "Desculpe, a consulta demorou")

            # Inicializado como None — agent_result e reatribuido em cada tentativa.
            # Retry loop preserva `agent_result` da ultima tentativa bem-sucedida
            # OU mantem erro da ultima tentativa se todas falharam.
            # (max_retries=0 quando fast-path já produziu agent_result acima.)
            for attempt in range(max_retries):
                try:
                    if TEAMS_PROGRESSIVE_STREAMING:
                        agent_result = _obter_resposta_agente_streaming(
                            mensagem=mensagem_llm,
                            usuario=usuario,
                            task_id=task_id,
                            sdk_session_id=sdk_session_id,
                            user_id=teams_user_id,
                            can_use_tool=agent_can_use_tool,
                            session=session,
                            app=app,
                            model=selected_model,
                            conversation_type=conversation_type,
                        )
                    else:
                        agent_result = _obter_resposta_agente(
                            mensagem=mensagem_llm,
                            usuario=usuario,
                            sdk_session_id=sdk_session_id,
                            user_id=teams_user_id,
                            can_use_tool=agent_can_use_tool,
                            session=session,
                            model=selected_model,
                            conversation_type=conversation_type,
                        )
                    resposta_texto = agent_result.resposta_texto
                    new_sdk_session_id = agent_result.sdk_session_id
                    input_tokens = agent_result.input_tokens
                    output_tokens = agent_result.output_tokens
                    tools_used = agent_result.tools_used
                    cost_usd = agent_result.cost_usd
                    cache_read_tokens = agent_result.cache_read_tokens
                    cache_creation_tokens = agent_result.cache_creation_tokens
                    # Fix: mensagens de erro são truthy mas NÃO são respostas válidas.
                    # Sem esta checagem, "Desculpe, ocorreu um erro..." bypassa o retry.
                    is_error_response = (
                        resposta_texto
                        and resposta_texto.startswith(_ERROR_PREFIXES)
                    )
                    if resposta_texto and not is_error_response:
                        break
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"[TEAMS-ASYNC] Tentativa {attempt + 1}: "
                            f"{'resposta é erro interno' if is_error_response else 'resposta vazia'}. "
                            f"Retry..."
                        )
                        resposta_texto = None  # Limpar para retry
                        time.sleep(2)
                    elif is_error_response:
                        # Última tentativa e ainda é erro — manter a mensagem de erro
                        logger.error(
                            f"[TEAMS-ASYNC] Todas as {max_retries} tentativas "
                            f"retornaram erro: {resposta_texto[:100] if resposta_texto else 'N/A'}"
                        )
                except Exception as agent_err:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"[TEAMS-ASYNC] Tentativa {attempt + 1} falhou: {agent_err}. Retry..."
                        )
                        time.sleep(2)
                    else:
                        logger.error(
                            f"[TEAMS-ASYNC] Todas as {max_retries} tentativas falharam: {agent_err}",
                            exc_info=True,
                        )
                        resposta_texto = (
                            "Desculpe, ocorreu um erro ao processar sua mensagem. "
                            "Tente novamente."
                        )

            # GAP 1/2/6: Salvar mensagens com tokens/tools/cost + model
            # Fase 4 (2026-04-21): inclui cache_read_tokens + cache_creation_tokens
            if session:
                try:
                    # Defense-in-depth: se agent_result None (nao deveria acontecer
                    # pois retry loop sempre produz resultado), cria fallback zerado.
                    if agent_result is None:
                        agent_result = _error_stream_result(resposta_texto=resposta_texto)

                    # Fase B: registra o FALANTE (grupos tem varios na mesma sessao)
                    session.add_user_message(mensagem, author=usuario)
                    if resposta_texto:
                        session.add_assistant_message(
                            content=resposta_texto,
                            input_tokens=agent_result.input_tokens,
                            output_tokens=agent_result.output_tokens,
                            tools_used=agent_result.tools_used if agent_result.tools_used else None,
                            cache_read_tokens=agent_result.cache_read_tokens,
                            cache_creation_tokens=agent_result.cache_creation_tokens,
                        )
                    if new_sdk_session_id and new_sdk_session_id != sdk_session_id:
                        # Defense-in-depth: só salvar se for UUID válido
                        try:
                            import uuid as _uuid
                            _uuid.UUID(new_sdk_session_id)
                            session.set_sdk_session_id(new_sdk_session_id)
                        except (ValueError, AttributeError):
                            logger.warning(
                                f"[TEAMS-ASYNC] sdk_session_id inválido (não UUID), "
                                f"descartado: {new_sdk_session_id[:20]}..."
                            )

                    # GAP 2: Custo — SDK prioritário, fallback cálculo local
                    from app.agente.routes import _calculate_cost
                    sdk_cost = agent_result.cost_usd
                    calc_cost = _calculate_cost(
                        selected_model, agent_result.input_tokens, agent_result.output_tokens
                    )
                    final_cost = sdk_cost if sdk_cost and sdk_cost > 0 else calc_cost
                    session.total_cost_usd = float(session.total_cost_usd or 0) + final_cost

                    # GAP 6: Model (registra modelo efetivamente usado)
                    session.model = selected_model

                    logger.info(
                        f"[TEAMS-ASYNC] Custo sessão {teams_session_id[:8]}: "
                        f"sdk_cost={sdk_cost}, calc_cost={calc_cost:.6f}, "
                        f"final={final_cost:.6f}, "
                        f"tokens=(in={agent_result.input_tokens},out={agent_result.output_tokens},"
                        f"cache_r={agent_result.cache_read_tokens},cache_w={agent_result.cache_creation_tokens}), "
                        f"tools={agent_result.tools_used}"
                    )
                except Exception as sess_err:
                    logger.warning(
                        f"[TEAMS-ASYNC] Erro ao salvar sessão (ignorado): {sess_err}"
                    )

            # Fix: Commitar mudanças da sessão para limpar dirty state ANTES
            # de buscar TeamsTask. Sem isso, autoflush dispara ao fazer
            # db.session.get() e falha se a sessão tiver objetos dirty/invalid.
            try:
                db.session.commit()
            except Exception as flush_err:
                logger.warning(
                    f"[TEAMS-ASYNC] Erro ao commitar sessão antes de buscar task: {flush_err}"
                )
                db.session.rollback()

            # =================================================================
            # GAP 3: Post-session processing COMPLETO (unificado com Web)
            # Substitui CAPDo inline por run_post_session_processing() que
            # executa: sumarização, pattern learning, behavioral profile,
            # knowledge extraction (CAPDo) e embedding generation.
            # Re-fetch session para evitar objeto stale após commit (linha 1241).
            # =================================================================
            if session and resposta_texto:
                try:
                    from app.agente.routes import run_post_session_processing
                    from app.agente.models import AgentSession

                    # Re-fetch: commit anterior pode ter expirado o objeto ORM
                    fresh_session = AgentSession.query.filter_by(
                        session_id=teams_session_id
                    ).first()
                    if fresh_session:
                        logger.info(
                            f"[TEAMS-ASYNC] Post-session iniciando "
                            f"(user={teams_user_id}, session={teams_session_id[:8]}..., "
                            f"msg_count={fresh_session.message_count}, "
                            f"has_summary={fresh_session.summary is not None})"
                        )
                        run_post_session_processing(
                            app=app,
                            session=fresh_session,
                            session_id=teams_session_id,
                            user_id=teams_user_id,
                            user_message=mensagem,
                            assistant_message=resposta_texto,
                        )
                        logger.info(
                            f"[TEAMS-ASYNC] Post-session processing concluído "
                            f"(user={teams_user_id}, session={teams_session_id[:8]}...)"
                        )
                    else:
                        logger.warning(
                            f"[TEAMS-ASYNC] Post-session: session {teams_session_id[:8]}... "
                            f"não encontrada no re-fetch"
                        )
                except Exception as post_err:
                    logger.warning(
                        f"[TEAMS-ASYNC] Post-session processing falhou (ignorado): {post_err}",
                        exc_info=True,
                    )

            # =================================================================
            # GAP 4: Memory effectiveness tracking (espelho de routes.py:1181-1191)
            # =================================================================
            try:
                if resposta_texto and teams_user_id:
                    from app.agente.sdk import get_client as _get_client
                    from app.agente.routes import (
                        _track_memory_effectiveness,
                        _track_outcome_by_recurrence,
                    )
                    _client = _get_client()
                    injected_ids = getattr(_client, '_last_injected_memory_ids', [])
                    _track_memory_effectiveness(teams_user_id, resposta_texto, injected_ids)
                    # Fase 3.3: medicao por OUTCOME (helpful) — ANTES de zerar injected_ids
                    _track_outcome_by_recurrence(teams_user_id, injected_ids)
                    _client._last_injected_memory_ids = []
            except Exception as eff_err:
                logger.warning(f"[TEAMS-ASYNC] Memory effectiveness tracking falhou: {eff_err}")

            # Buscar card estruturado pendente (Fase 1 MVP cards ricos).
            # Se o agente chamou render_teams_card durante o turno, o card
            # estara disponivel aqui e sera persistido em task.resposta_card.
            # sanitize_for_json aplica-se porque `data` pode conter Decimal
            # (cod_produto, valores monetarios) vindos de queries SQL ou APIs
            # Odoo que o LLM repassa sem conversao — regra CLAUDE.md 2026-04-14.
            pending_card = None
            try:
                from app.agente.config.permissions import pop_pending_teams_card
                from app.utils.json_helpers import sanitize_for_json
                raw_card = pop_pending_teams_card(teams_session_id) if teams_session_id else None
                if raw_card:
                    pending_card = sanitize_for_json(raw_card)
                    logger.info(
                        f"[TEAMS-ASYNC] Card estruturado encontrado: "
                        f"template={pending_card.get('template')} "
                        f"task={task_id[:8]}..."
                    )
            except Exception as card_err:
                logger.warning(
                    f"[TEAMS-ASYNC] Erro ao buscar pending card (ignorado): {card_err}"
                )

            # Atualizar TeamsTask com resultado (retry para SSL dropped)
            # no_autoflush previne flush automático de dirty objects ao fazer get()
            with db.session.no_autoflush:
                task = db.session.get(TeamsTask, task_id)
            if task:
                if resposta_texto:
                    task.status = 'completed'
                    task.resposta = _sanitizar_texto(resposta_texto)
                    task.resposta_card = pending_card
                    task.completed_at = agora_utc_naive()
                else:
                    task.status = 'error'
                    task.resposta = 'O agente não retornou uma resposta.'
                    task.completed_at = agora_utc_naive()

                try:
                    db.session.commit()
                except Exception as commit_err:
                    err_str = str(commit_err).lower()
                    if 'ssl' in err_str or 'connection' in err_str or 'closed' in err_str:
                        logger.warning(
                            f"[TEAMS-ASYNC] Conexão perdida no commit, reconectando: {commit_err}"
                        )
                        db.session.rollback()
                        db.session.close()
                        # P1-1: Após close(), objetos ficam detached — commit commitaria
                        # transação vazia. Re-fetch task e re-apply mudanças.
                        try:
                            task = db.session.get(TeamsTask, task_id)
                            if task:
                                if resposta_texto:
                                    task.status = 'completed'
                                    task.resposta = _sanitizar_texto(resposta_texto)
                                    task.resposta_card = pending_card
                                    task.completed_at = agora_utc_naive()
                                else:
                                    task.status = 'error'
                                    task.resposta = 'O agente não retornou uma resposta.'
                                    task.completed_at = agora_utc_naive()
                                db.session.commit()
                                logger.info("[TEAMS-ASYNC] Retry commit bem-sucedido (re-fetched)")
                            else:
                                logger.error(f"[TEAMS-ASYNC] Task {task_id} não encontrada no retry")
                        except Exception as retry_err:
                            logger.error(f"[TEAMS-ASYNC] Retry commit falhou: {retry_err}")
                            db.session.rollback()
                    else:
                        raise

            logger.info(
                f"[TEAMS-ASYNC] Task completada: task={task_id[:8]}... "
                f"status={task.status if task else 'N/A'} "
                f"resposta_len={len(resposta_texto) if resposta_texto else 0} "
                f"card={pending_card.get('template') if pending_card else 'none'}"
            )

            # Fase C (proactive): se o polling da function provavelmente ja
            # morreu (task antiga), entrega a resposta via continue_conversation.
            # Best-effort + claim atomico anti-duplicata (ver proactive.py).
            try:
                from app.teams.proactive import notify_function_delivery
                notify_function_delivery(task_id)
            except Exception as proactive_err:
                logger.warning(
                    f"[TEAMS-ASYNC] Proactive delivery falhou (ignorado): {proactive_err}"
                )

            # Verificar fila de mensagens pendentes para esta conversa
            _process_queued_task(app, conversation_id, task_id)

        except Exception as e:
            logger.error(
                f"[TEAMS-ASYNC] Erro fatal: task={task_id[:8]}... error={e}",
                exc_info=True,
            )
            try:
                # Fix: rollback dirty state antes de buscar task para evitar
                # autoflush failure que impede task de chegar a status terminal
                db.session.rollback()
                # no_autoflush previne flush automático de dirty objects ao fazer get()
                with db.session.no_autoflush:
                    task = db.session.get(TeamsTask, task_id)
                if task and task.status not in ('completed', 'error'):
                    task.status = 'error'
                    task.resposta = f'Erro ao processar: {str(e)[:500]}'
                    task.completed_at = agora_utc_naive()
                    db.session.commit()
            except Exception:
                logger.error("[TEAMS-ASYNC] Erro ao marcar task como error", exc_info=True)
                db.session.rollback()

            # Fase C (proactive): entrega o ERRO tambem se o polling ja morreu
            try:
                from app.teams.proactive import notify_function_delivery
                notify_function_delivery(task_id)
            except Exception:
                pass

            # Mesmo com erro, processar mensagem queued (usuario ja enviou)
            _process_queued_task(app, conversation_id, task_id)

        finally:
            # Cleanup de contextos
            if teams_session_id:
                cleanup_teams_task_context(teams_session_id)
                cleanup_session_context(teams_session_id)

            # Cleanup user_id cross-thread dos MCP tools
            # Remove entrada do dict keyed por thread ID para evitar stale entries
            # que causariam cross-user data leak em invocações concorrentes.
            try:
                from app.agente.tools.memory_mcp_tool import clear_current_user_id as clear_memory_uid
                clear_memory_uid()
            except (ImportError, Exception):
                pass
            try:
                from app.agente.tools.session_search_tool import clear_current_user_id as clear_session_uid
                clear_session_uid()
            except (ImportError, Exception):
                pass
            try:
                from app.agente.tools.text_to_sql_tool import clear_current_user_id as clear_sql_uid
                clear_sql_uid()
            except (ImportError, Exception):
                pass
            # Restricao Estoque (2026-05-26): cleanup user_id do permissions ContextVar
            try:
                clear_perm_user_id()
            except Exception:
                pass

            try:
                db.session.remove()
            except Exception:
                pass

            logger.debug(f"[TEAMS-ASYNC] Cleanup finalizado: task={task_id[:8]}...")


def _process_queued_task(app, conversation_id: str, finished_task_id: str) -> None:
    """
    Verifica se ha mensagem queued para a conversa e processa.

    Chamado apos conclusao (sucesso ou erro) de uma task.
    Processa a mensagem queued NA MESMA THREAD para manter contexto
    e reutilizar a sessao Teams (TTL 4h).

    NOTA: Chamada recursiva via process_teams_task_async() — nao e
    recursao infinita porque a task queued muda para 'processing'
    antes da chamada, saindo do filtro de concorrencia.
    """
    try:
        from app.teams.models import TeamsTask
        from app import db

        with db.session.no_autoflush:
            queued_task = TeamsTask.query.filter(
                TeamsTask.conversation_id == conversation_id,
                TeamsTask.status == 'queued',
            ).order_by(TeamsTask.created_at.asc()).first()

        if not queued_task:
            return

        logger.info(
            f"[TEAMS-QUEUE] Mensagem queued encontrada: "
            f"task={queued_task.id[:8]}... msg={queued_task.mensagem[:80]}... "
            f"(apos task={finished_task_id[:8]}...)"
        )

        # Atualizar status para processing antes de chamar
        # R2: _commit_with_retry obrigatorio em thread longa (SSL drop risk)
        queued_task.status = 'processing'
        if not _commit_with_retry("[TEAMS-QUEUE]"):
            # SSL dropped — re-fetch e re-apply
            queued_task = db.session.get(TeamsTask, queued_task.id)
            if not queued_task:
                logger.error("[TEAMS-QUEUE] Task queued perdida apos SSL drop")
                return
            queued_task.status = 'processing'
            _commit_with_retry("[TEAMS-QUEUE-RETRY]")

        # Processar na mesma thread (non-daemon), mesma sessao.
        # Fase B: TeamsTask nao guarda conversation_type — heuristica pelo
        # formato do conversation_id ('19:...' = groupChat/channel; pessoal
        # comeca com 'a:'). Mantem a etiqueta de falante em msgs enfileiradas.
        _conv_type = 'groupChat' if (conversation_id or '').startswith('19:') else 'personal'
        process_teams_task_async(
            app=app,
            task_id=queued_task.id,
            mensagem=queued_task.mensagem,
            usuario=queued_task.user_name,
            conversation_id=conversation_id,
            teams_user_id=queued_task.user_id,
            conversation_type=_conv_type,
        )

    except Exception as e:
        logger.warning(
            f"[TEAMS-QUEUE] Erro ao processar fila (ignorado): {e}",
            exc_info=True,
        )


def cleanup_stale_teams_tasks() -> int:
    """
    Marca tasks stale como timeout.

    Thresholds (Fase C — eram 5/5/10 min; com o heartbeat de 60s renovando
    updated_at, um gap de 15 min significa thread realmente morta):
    - pending/processing: > 15 min sem update
    - awaiting_user_input: > 30 min sem update (usuario pode demorar no card)
    - queued: > 15 min sem update

    Chamado no início de cada bot_message() (lazy cleanup, sem cron extra).

    Returns:
        Número de tasks marcadas como timeout
    """
    try:
        from app.teams.models import TeamsTask
        from app import db

        # Fix PYTHON-FLASK-C: rollback dirty session left over from a previous
        # request in the same Flask thread. Without this, any DB query fails
        # with PendingRollbackError if a prior error left the session dirty.
        try:
            db.session.rollback()
        except Exception:
            pass

        # Fase C: thresholds maiores (eram 5/5/10). O heartbeat de 60s renova
        # updated_at de tasks processing — gap de 15 min = thread morta de fato.
        # awaiting_user_input ganha 30 min (usuario pode demorar no card).
        processing_threshold = agora_utc_naive() - timedelta(minutes=15)
        awaiting_threshold = agora_utc_naive() - timedelta(minutes=30)
        queued_threshold = agora_utc_naive() - timedelta(minutes=15)

        # P2-C: Usar updated_at ao invés de created_at para evitar matar tasks legítimas.
        # Uma task criada há 15+ min pode ter mudado para awaiting_user_input há 30s.
        # Com created_at, seria marcada como timeout enquanto o usuário ainda responde.
        stale_tasks = TeamsTask.query.filter(
            db.or_(
                db.and_(
                    TeamsTask.status.in_(['pending', 'processing']),
                    TeamsTask.updated_at < processing_threshold,
                ),
                db.and_(
                    TeamsTask.status == 'awaiting_user_input',
                    TeamsTask.updated_at < awaiting_threshold,
                ),
                db.and_(
                    TeamsTask.status == 'queued',
                    TeamsTask.updated_at < queued_threshold,
                ),
            ),
        ).all()

        count = 0
        for task in stale_tasks:
            task.status = 'timeout'
            task.resposta = 'Tempo limite excedido no processamento.'
            task.completed_at = agora_utc_naive()
            count += 1

        if count > 0:
            db.session.commit()
            logger.warning(f"[TEAMS-CLEANUP] {count} tasks stale marcadas como timeout")

        return count

    except Exception as e:
        logger.error(f"[TEAMS-CLEANUP] Erro no cleanup: {e}", exc_info=True)
        return 0
