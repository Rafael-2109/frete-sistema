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
from typing import List, Optional, Tuple

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
    """
    resposta_texto: Optional[str]
    sdk_session_id: Optional[str]
    input_tokens: int = 0
    output_tokens: int = 0
    tools_used: List[str] = field(default_factory=list)
    cost_usd: float = 0.0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

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


def _get_or_create_teams_user(usuario: str) -> Optional[int]:
    """
    Obtém ou auto-cadastra usuário do Teams como Usuario real no banco.

    Cria um usuário "oculto" com email determinístico @teams.nacomgoya.local
    e senha aleatória. Isso permite que a FK de AgentMemory/AgentSession
    funcione corretamente, habilitando memórias persistentes no Teams.

    O usuário é criado com status='ativo' e perfil='logistica'.
    Não consegue fazer login no sistema web (não sabe a senha).
    Facilmente identificável pelo email @teams.nacomgoya.local.

    Args:
        usuario: Nome do usuário do Teams (ex: "Rafael Nascimento")

    Returns:
        int: user_id real na tabela usuarios, ou None se falhar
    """
    if not usuario or not usuario.strip():
        return None

    try:
        from app.auth.models import Usuario
        from app import db

        # Gera email determinístico baseado no nome normalizado
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
4. TAMANHO IDEAL - Até 3000 caracteres (respostas longas serão divididas automaticamente)
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

    # Configurar session context para permissions.py (AskUserQuestion)
    teams_session_id = session.session_id if session else None
    if teams_session_id:
        from app.agente.config.permissions import set_current_session_id, cleanup_session_context, can_use_tool as agent_can_use_tool
        set_current_session_id(teams_session_id)
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
        # C1: Smart model routing
        selected_model = _select_model_for_message(mensagem)
        logger.info(
            f"[TEAMS-BOT] Model routing: {selected_model} "
            f"para msg ({len(mensagem.split())} palavras)"
        )

        # Obter resposta do agente (com can_use_tool para graceful denial de AskUserQuestion)
        _sync_result = _obter_resposta_agente(
            mensagem=mensagem,
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
                session.add_user_message(mensagem)
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
                        session.add_user_message(mensagem)
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
    # Construimos XML com ultimas 10 msgs do JSONB `data['messages']` para o
    # hook UserPromptSubmit (client.py) injetar como `additionalContext` quando
    # resume falhar. Espelha pattern de chat.py:341-360 no path web.
    resume_messages_fallback = None
    if session:
        try:
            messages = session.get_messages() or []
            if messages and len(messages) > 1:
                recent = messages[-10:]
                parts = ['<conversation_history_fallback reason="resume_failed">']
                for msg in recent:
                    role = msg.get('role', 'unknown')
                    content = (msg.get('content', '') or '')[:2000]
                    if content:
                        parts.append(f'<msg role="{role}">{content}</msg>')
                parts.append('</conversation_history_fallback>')
                resume_messages_fallback = '\n'.join(parts)
                logger.debug(
                    f"[TEAMS-BOT] Fallback XML preparado: "
                    f"{len(messages)} msgs, {len(resume_messages_fallback)} chars"
                )
        except Exception as fb_err:
            logger.debug(f"[TEAMS-BOT] Fallback XML falhou (ignorado): {fb_err}")

    # Contexto especial para Teams: data atual + instruções anti-verbosidade
    contexto_teams = _get_teams_context()
    prompt_completo = contexto_teams + mensagem

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

    # Limita tamanho (Teams suporta ~28KB, mas cards ficam legíveis até ~4000)
    if len(texto) > 3800:
        # Tenta cortar em quebra de parágrafo para manter legibilidade
        corte = texto[:3700].rfind('\n\n')
        if corte > 2000:
            texto = texto[:corte] + '\n\n_(resposta truncada)_'
        else:
            # Fallback: cortar na última quebra de linha
            corte = texto[:3700].rfind('\n')
            if corte > 2000:
                texto = texto[:corte] + '\n\n_(resposta truncada)_'
            else:
                texto = texto[:3700] + '\n\n_(resposta truncada)_'

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
    # contexto das ultimas 10 msgs via `additionalContext`.
    resume_messages_fallback = None
    if session:
        try:
            messages = session.get_messages() or []
            if messages and len(messages) > 1:
                recent = messages[-10:]
                parts = ['<conversation_history_fallback reason="resume_failed">']
                for msg in recent:
                    role = msg.get('role', 'unknown')
                    content = (msg.get('content', '') or '')[:2000]
                    if content:
                        parts.append(f'<msg role="{role}">{content}</msg>')
                parts.append('</conversation_history_fallback>')
                resume_messages_fallback = '\n'.join(parts)
                logger.debug(
                    f"[TEAMS-STREAM] Fallback XML preparado: "
                    f"{len(messages)} msgs, {len(resume_messages_fallback)} chars"
                )
        except Exception as fb_err:
            logger.debug(f"[TEAMS-STREAM] Fallback XML falhou (ignorado): {fb_err}")

    # Contexto especial para Teams
    contexto_teams = _get_teams_context()
    prompt_completo = contexto_teams + mensagem

    # Pool key para path persistente (ClaudeSDKClient por sessão)
    our_session_id = session.session_id if session else None

    # Timeout por inatividade: mata quando não há atividade real.
    # Cada chunk/tool_call recebido renova o deadline.
    # Sem teto absoluto — operações longas (subagentes Odoo, bulk) são legítimas.
    INACTIVITY_TIMEOUT = 240   # 4 min sem atividade = timeout

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
                    tool_name = event.content if isinstance(event.content, str) else str(event.content)
                    if tool_name and tool_name not in tools_used:
                        tools_used.append(tool_name)

                    # A1: Status visual durante tool calls (quando texto ainda não gerado)
                    if TEAMS_TOOL_STATUS_FEEDBACK and not full_text:
                        tool_label = _tool_display_name(tool_name)
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

            # Se full_text vazio mas houve errors, montar texto sintetico
            if not full_text and errors:
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
            )

        # Deadline renewal integrado em _stream_with_flush (per-chunk timeout).
        # Wrapper direto sem asyncio.wait_for externo.
        async def _stream_with_timeout():
            return await _stream_with_flush()

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
    """
    with app.app_context():
        from app.teams.models import TeamsTask
        from app import db
        from app.agente.config.permissions import (
            set_current_session_id,
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

            # Obter/criar sessão
            session = _get_or_create_teams_session(
                conversation_id, usuario, user_id=teams_user_id
            )
            sdk_session_id = session.get_sdk_session_id() if session else None
            teams_session_id = session.session_id if session else f"teams_async_{task_id}"

            # Configurar context para permissions.py
            set_current_session_id(teams_session_id)
            set_teams_task_context(teams_session_id, task_id)

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
            agent_result: Optional[StreamResult] = None
            for attempt in range(max_retries):
                try:
                    if TEAMS_PROGRESSIVE_STREAMING:
                        agent_result = _obter_resposta_agente_streaming(
                            mensagem=mensagem,
                            usuario=usuario,
                            task_id=task_id,
                            sdk_session_id=sdk_session_id,
                            user_id=teams_user_id,
                            can_use_tool=agent_can_use_tool,
                            session=session,
                            app=app,
                            model=selected_model,
                        )
                    else:
                        agent_result = _obter_resposta_agente(
                            mensagem=mensagem,
                            usuario=usuario,
                            sdk_session_id=sdk_session_id,
                            user_id=teams_user_id,
                            can_use_tool=agent_can_use_tool,
                            session=session,
                            model=selected_model,
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

                    session.add_user_message(mensagem)
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
                    from app.agente.routes import _track_memory_effectiveness
                    _client = _get_client()
                    injected_ids = getattr(_client, '_last_injected_memory_ids', [])
                    _track_memory_effectiveness(teams_user_id, resposta_texto, injected_ids)
                    _client._last_injected_memory_ids = []
            except Exception as eff_err:
                logger.warning(f"[TEAMS-ASYNC] Memory effectiveness tracking falhou: {eff_err}")

            # Atualizar TeamsTask com resultado (retry para SSL dropped)
            # no_autoflush previne flush automático de dirty objects ao fazer get()
            with db.session.no_autoflush:
                task = db.session.get(TeamsTask, task_id)
            if task:
                if resposta_texto:
                    task.status = 'completed'
                    task.resposta = _sanitizar_texto(resposta_texto)
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
                f"resposta_len={len(resposta_texto) if resposta_texto else 0}"
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

        # Processar na mesma thread (non-daemon), mesma sessao
        process_teams_task_async(
            app=app,
            task_id=queued_task.id,
            mensagem=queued_task.mensagem,
            usuario=queued_task.user_name,
            conversation_id=conversation_id,
            teams_user_id=queued_task.user_id,
        )

    except Exception as e:
        logger.warning(
            f"[TEAMS-QUEUE] Erro ao processar fila (ignorado): {e}",
            exc_info=True,
        )


def cleanup_stale_teams_tasks() -> int:
    """
    Marca tasks stale como timeout.

    - pending/processing/awaiting_user_input: > 5 min sem update
    - queued: > 10 min sem update (threshold maior porque aguarda task ativa)

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

        threshold = agora_utc_naive() - timedelta(minutes=5)
        queued_threshold = agora_utc_naive() - timedelta(minutes=10)

        # P2-C: Usar updated_at ao invés de created_at para evitar matar tasks legítimas.
        # Uma task criada há 5+ min pode ter mudado para awaiting_user_input há 30s.
        # Com created_at, seria marcada como timeout enquanto o usuário ainda responde.
        # Tasks queued usam threshold maior (10 min) porque aguardam task ativa terminar.
        stale_tasks = TeamsTask.query.filter(
            db.or_(
                db.and_(
                    TeamsTask.status.in_(['pending', 'processing', 'awaiting_user_input']),
                    TeamsTask.updated_at < threshold,
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
