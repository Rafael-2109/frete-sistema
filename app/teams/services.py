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
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


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
            aprovado_em=datetime.now(timezone.utc),
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
    data_atual = datetime.now().strftime("%d/%m/%Y")
    dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    dia_semana = dias_semana[datetime.now().weekday()]

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

# TTL de sessão do Teams: após 4h de inatividade, cria nova sessão
TEAMS_SESSION_TTL_HOURS = 4


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

    try:
        # Obter resposta do agente (com can_use_tool para graceful denial de AskUserQuestion)
        resposta_texto, new_sdk_session_id = _obter_resposta_agente(
            mensagem=mensagem,
            usuario=usuario,
            sdk_session_id=sdk_session_id,
            user_id=teams_user_id,
            can_use_tool=agent_can_use_tool,
        )

        # Salvar mensagens e atualizar sdk_session_id
        if session:
            try:
                session.add_user_message(mensagem)
                if resposta_texto:
                    session.add_assistant_message(resposta_texto)
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
                            session.add_assistant_message(resposta_texto)
                        if new_sdk_session_id and new_sdk_session_id != sdk_session_id:
                            session.set_sdk_session_id(new_sdk_session_id)
                        db.session.commit()
                        logger.info("[TEAMS-BOT] Re-apply + commit bem-sucedido")
                    else:
                        logger.error("[TEAMS-BOT] Session nao encontrada no re-fetch")
            except Exception as e:
                logger.error(f"[TEAMS-BOT] Erro ao salvar sessao: {e}", exc_info=True)
                # Nao bloqueia resposta se falhar ao salvar

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
        session_expired = False
        if session and session.updated_at:
            ttl_threshold = datetime.now(timezone.utc) - timedelta(hours=TEAMS_SESSION_TTL_HOURS)
            if session.updated_at < ttl_threshold:
                session_expired = True
                hours_inactive = (datetime.now(timezone.utc) - session.updated_at).total_seconds() / 3600
                logger.info(
                    f"[TEAMS-BOT] Sessao expirada ({hours_inactive:.1f}h inativa), "
                    f"criando nova"
                )

        # Cria nova sessão se não existe ou expirou
        if not session or session_expired:
            # Adiciona timestamp para sessões expiradas (permite histórico)
            if session_expired:
                session_id = f"{base_session_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            else:
                session_id = base_session_id

            from app.agente.config.feature_flags import TEAMS_DEFAULT_MODEL

            session = AgentSession(
                session_id=session_id,
                user_id=user_id,  # User real auto-cadastrado via _get_or_create_teams_user
                title=f"Teams - {usuario}",
                model=TEAMS_DEFAULT_MODEL,
                data={'messages': [], 'total_tokens': 0},
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
) -> Tuple[Optional[str], Optional[str]]:
    """
    Obtem resposta do Agente Claude SDK.

    Args:
        mensagem: Mensagem do usuario
        usuario: Nome do usuario
        sdk_session_id: ID da sessao SDK para resume (opcional)
        user_id: ID real do usuario na tabela usuarios (para memorias)
        can_use_tool: Callback de permissão (para AskUserQuestion no Teams)

    Returns:
        Tuple[resposta_texto, new_sdk_session_id]
    """
    try:
        from app.agente.sdk import get_client
        client = get_client()
    except Exception as e:
        logger.error(f"[TEAMS-BOT] Erro ao obter client: {e}")
        return None, None

    # Contexto especial para Teams: data atual + instruções anti-verbosidade
    contexto_teams = _get_teams_context()
    prompt_completo = contexto_teams + mensagem

    # Modelo padrão para Teams (Sonnet por velocidade)
    from app.agente.config.feature_flags import TEAMS_DEFAULT_MODEL

    # Executa a coroutine de forma sincrona
    try:
        # P1-4: asyncio.get_event_loop() deprecated desde 3.10, quebrará em 3.14+.
        # Criar loop dedicado e fechar no finally.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            response = loop.run_until_complete(
                client.get_response(
                    prompt=prompt_completo,
                    user_name=usuario,
                    sdk_session_id=sdk_session_id,
                    user_id=user_id,
                    model=TEAMS_DEFAULT_MODEL,
                    can_use_tool=can_use_tool,
                )
            )
        finally:
            loop.close()

        resposta_texto = _extrair_texto_resposta(response)

        # Capturar novo sdk_session_id do response
        new_sdk_session_id = getattr(response, 'session_id', None)

        return resposta_texto, new_sdk_session_id

    except asyncio.TimeoutError:
        logger.error("[TEAMS-BOT] Timeout ao aguardar resposta do agente")
        return "Desculpe, a consulta demorou muito. Tente novamente com uma pergunta mais especifica.", None

    except Exception as e:
        logger.error(f"[TEAMS-BOT] Erro ao obter resposta do agente: {e}", exc_info=True)
        # Fix 2b: Retornar mensagem de erro amigavel ao inves de None
        # Evita que o caller receba None e caia em "AgentResponse(text='', ...)" ou RuntimeError
        return "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.", None


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


# ═══════════════════════════════════════════════════════════════
# PROCESSAMENTO ASSÍNCRONO (daemon threads)
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
    Processa uma TeamsTask em daemon thread (background).

    Fix 3: Recebe app como parametro ao inves de criar novo via create_app().
    Isso reutiliza o app context do gunicorn worker e evita problemas com
    inicializacao de hooks/MCP em ambiente headless.

    IMPORTANTE: Esta função roda no MESMO processo gunicorn (daemon thread).
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

            # Fix 3b: Retry na chamada do agente (max 2 tentativas)
            # CLIConnectionError pode ocorrer na 1a tentativa (race condition no subprocess),
            # mas tipicamente funciona na 2a.
            resposta_texto = None
            new_sdk_session_id = None
            max_retries = 2

            for attempt in range(max_retries):
                try:
                    resposta_texto, new_sdk_session_id = _obter_resposta_agente(
                        mensagem=mensagem,
                        usuario=usuario,
                        sdk_session_id=sdk_session_id,
                        user_id=teams_user_id,
                        can_use_tool=agent_can_use_tool,
                    )
                    if resposta_texto:
                        break
                    # Se resposta vazia na 1a tentativa, retry
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"[TEAMS-ASYNC] Tentativa {attempt + 1}: resposta vazia. Retry..."
                        )
                        time.sleep(2)
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

            # Salvar mensagens e sdk_session_id na sessão
            if session:
                try:
                    session.add_user_message(mensagem)
                    if resposta_texto:
                        session.add_assistant_message(resposta_texto)
                    if new_sdk_session_id and new_sdk_session_id != sdk_session_id:
                        session.set_sdk_session_id(new_sdk_session_id)
                except Exception as sess_err:
                    logger.warning(
                        f"[TEAMS-ASYNC] Erro ao salvar sessão (ignorado): {sess_err}"
                    )

            # Atualizar TeamsTask com resultado (retry para SSL dropped)
            task = db.session.get(TeamsTask, task_id)
            if task:
                if resposta_texto:
                    task.status = 'completed'
                    task.resposta = _sanitizar_texto(resposta_texto)
                    task.completed_at = datetime.now(timezone.utc)
                else:
                    task.status = 'error'
                    task.resposta = 'O agente não retornou uma resposta.'
                    task.completed_at = datetime.now(timezone.utc)

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
                                    task.completed_at = datetime.now(timezone.utc)
                                else:
                                    task.status = 'error'
                                    task.resposta = 'O agente não retornou uma resposta.'
                                    task.completed_at = datetime.now(timezone.utc)
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

        except Exception as e:
            logger.error(
                f"[TEAMS-ASYNC] Erro fatal: task={task_id[:8]}... error={e}",
                exc_info=True,
            )
            try:
                task = db.session.get(TeamsTask, task_id)
                if task and task.status not in ('completed', 'error'):
                    task.status = 'error'
                    task.resposta = f'Erro ao processar: {str(e)[:500]}'
                    task.completed_at = datetime.now(timezone.utc)
                    db.session.commit()
            except Exception:
                logger.error("[TEAMS-ASYNC] Erro ao marcar task como error", exc_info=True)
                db.session.rollback()

        finally:
            # Cleanup de contextos
            if teams_session_id:
                cleanup_teams_task_context(teams_session_id)
                cleanup_session_context(teams_session_id)

            try:
                db.session.remove()
            except Exception:
                pass

            logger.debug(f"[TEAMS-ASYNC] Cleanup finalizado: task={task_id[:8]}...")


def cleanup_stale_teams_tasks() -> int:
    """
    Marca tasks stale (pending/processing > 5 min) como timeout.

    Chamado no início de cada bot_message() (lazy cleanup, sem cron extra).

    Returns:
        Número de tasks marcadas como timeout
    """
    try:
        from app.teams.models import TeamsTask
        from app import db

        threshold = datetime.now(timezone.utc) - timedelta(minutes=5)

        # P2-C: Usar updated_at ao invés de created_at para evitar matar tasks legítimas.
        # Uma task criada há 5+ min pode ter mudado para awaiting_user_input há 30s.
        # Com created_at, seria marcada como timeout enquanto o usuário ainda responde.
        stale_tasks = TeamsTask.query.filter(
            TeamsTask.status.in_(['pending', 'processing', 'awaiting_user_input']),
            TeamsTask.updated_at < threshold,
        ).all()

        count = 0
        for task in stale_tasks:
            task.status = 'timeout'
            task.resposta = 'Tempo limite excedido no processamento.'
            task.completed_at = datetime.now(timezone.utc)
            count += 1

        if count > 0:
            db.session.commit()
            logger.warning(f"[TEAMS-CLEANUP] {count} tasks stale marcadas como timeout")

        return count

    except Exception as e:
        logger.error(f"[TEAMS-CLEANUP] Erro no cleanup: {e}", exc_info=True)
        return 0
