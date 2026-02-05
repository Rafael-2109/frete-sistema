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
from datetime import datetime, timedelta
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def _get_teams_user_id(usuario: str) -> int:
    """
    Gera user_id determinístico baseado no nome do usuário do Teams.

    Usa MD5 truncado para 8 hex chars (32 bits) → int positivo.
    Mesmo usuário sempre gera mesmo ID, permitindo memória persistente.

    Args:
        usuario: Nome do usuário do Teams (ex: "Rafael Nascimento")

    Returns:
        int: user_id determinístico (ex: 2938471234)
    """
    normalized = usuario.lower().strip()
    hash_hex = hashlib.md5(normalized.encode('utf-8')).hexdigest()[:8]
    return int(hash_hex, 16)


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
1. RESPOSTA ÚNICA - Você terá APENAS UMA chance de responder
2. SEJA DIRETO - Vá direto ao ponto, sem introduções
3. AÇÃO SILENCIOSA - NUNCA diga "vou consultar...", "deixa eu verificar...", "analisando..."
   Execute as consultas SILENCIOSAMENTE e retorne APENAS o resultado
4. SEM MARKDOWN COMPLEXO - NÃO use tabelas (| col |), headers (##), code blocks
   Use apenas: texto simples, listas com "- item", negrito com *texto*
5. TAMANHO MÁXIMO - 2000 caracteres

PROIBIDO:
❌ "Vou consultar o banco de dados..."
❌ "Deixa eu verificar os pedidos..."
❌ "Analisando os dados disponíveis..."
❌ "Primeiro preciso..."

CORRETO:
✅ "Encontrei 3 pedidos do Atacadão: [lista]"
✅ "O estoque de palmito é 1.500 caixas"
✅ "NF 144533 foi entregue em 15/01/2025"

PERGUNTA DO USUÁRIO:
"""

# TTL de sessão do Teams: após 4h de inatividade, cria nova sessão
TEAMS_SESSION_TTL_HOURS = 4


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

    # Obter ou criar sessao para esta conversa Teams
    session = _get_or_create_teams_session(conversation_id, usuario)

    # Obter sdk_session_id para resume (se existir)
    sdk_session_id = session.get_sdk_session_id() if session else None

    if sdk_session_id:
        logger.info(f"[TEAMS-BOT] Resuming sessao SDK: {sdk_session_id[:20]}...")

    # Obter resposta do agente
    resposta_texto, new_sdk_session_id = _obter_resposta_agente(
        mensagem=mensagem,
        usuario=usuario,
        sdk_session_id=sdk_session_id,
    )

    # Salvar mensagens e atualizar sdk_session_id
    if session:
        try:
            from app import db

            session.add_user_message(mensagem)
            if resposta_texto:
                session.add_assistant_message(resposta_texto)
            if new_sdk_session_id and new_sdk_session_id != sdk_session_id:
                session.set_sdk_session_id(new_sdk_session_id)
                logger.info(f"[TEAMS-BOT] Novo sdk_session_id salvo: {new_sdk_session_id[:20]}...")
            db.session.commit()
        except Exception as e:
            logger.error(f"[TEAMS-BOT] Erro ao salvar sessao: {e}", exc_info=True)
            # Nao bloqueia resposta se falhar ao salvar

    if not resposta_texto:
        raise RuntimeError("O agente nao retornou uma resposta")

    logger.info(f"[TEAMS-BOT] Resposta obtida: {len(resposta_texto)} caracteres")
    return resposta_texto


def _get_or_create_teams_session(
    conversation_id: str,
    usuario: str,
):
    """
    Obtém ou cria AgentSession para uma conversa do Teams.

    Implementa TTL de 4 horas: se a última mensagem foi há mais de 4h,
    cria uma nova sessão para evitar contexto infinito em grupos ativos.

    Args:
        conversation_id: ID da conversa do Teams (ex: 19:xyz@thread.skype)
        usuario: Nome do usuário

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

        # Busca sessão existente
        session = AgentSession.query.filter(
            AgentSession.session_id.like(f"{base_session_id}%")
        ).order_by(AgentSession.updated_at.desc()).first()

        # Verifica se sessão expirou (TTL de 4h)
        session_expired = False
        if session and session.updated_at:
            ttl_threshold = datetime.utcnow() - timedelta(hours=TEAMS_SESSION_TTL_HOURS)
            if session.updated_at < ttl_threshold:
                session_expired = True
                hours_inactive = (datetime.utcnow() - session.updated_at).total_seconds() / 3600
                logger.info(
                    f"[TEAMS-BOT] Sessao expirada ({hours_inactive:.1f}h inativa), "
                    f"criando nova"
                )

        # Cria nova sessão se não existe ou expirou
        if not session or session_expired:
            # Adiciona timestamp para sessões expiradas (permite histórico)
            if session_expired:
                session_id = f"{base_session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            else:
                session_id = base_session_id

            # Gerar user_id determinístico baseado no nome do usuário Teams
            # Isso permite que a memória persista entre sessões para o mesmo usuário
            user_id = _get_teams_user_id(usuario)

            session = AgentSession(
                session_id=session_id,
                user_id=user_id,
                title=f"Teams - {usuario}",
                model="claude-opus-4-6",
                data={'messages': [], 'total_tokens': 0},
            )
            logger.info(f"[TEAMS-BOT] user_id gerado para '{usuario}': {user_id}")
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
) -> Tuple[Optional[str], Optional[str]]:
    """
    Obtem resposta do Agente Claude SDK.

    Args:
        mensagem: Mensagem do usuario
        usuario: Nome do usuario
        sdk_session_id: ID da sessao SDK para resume (opcional)

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

    # Executa a coroutine de forma sincrona
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Loop fechado")
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        response = loop.run_until_complete(
            client.get_response(
                prompt=prompt_completo,
                user_name=usuario,
                sdk_session_id=sdk_session_id,
            )
        )

        resposta_texto = _extrair_texto_resposta(response)

        # Capturar novo sdk_session_id do response
        new_sdk_session_id = getattr(response, 'session_id', None)

        return resposta_texto, new_sdk_session_id

    except asyncio.TimeoutError:
        logger.error("[TEAMS-BOT] Timeout ao aguardar resposta do agente")
        return "Desculpe, a consulta demorou muito. Tente novamente com uma pergunta mais especifica.", None

    except Exception as e:
        logger.error(f"[TEAMS-BOT] Erro ao obter resposta do agente: {e}", exc_info=True)
        return None, None


def _extrair_texto_resposta(response) -> Optional[str]:
    """
    Extrai texto da resposta do SDK, tratando diferentes formatos.

    Args:
        response: Objeto de resposta do SDK

    Returns:
        str: Texto extraido e limpo
    """
    texto = None

    logger.debug(f"[TEAMS-BOT] Tipo de response: {type(response).__name__}")
    if hasattr(response, 'text'):
        logger.debug(f"[TEAMS-BOT] response.text presente: {bool(response.text)}")

    # Tenta diferentes formas de extrair o texto
    if hasattr(response, 'text') and response.text:
        texto = response.text
        logger.debug(f"[TEAMS-BOT] Texto extraido via response.text: {len(texto)} chars")
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
        texto = str(response)
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

    # Limita tamanho (Teams tem limite de card)
    if len(texto) > 2500:
        texto = texto[:2497] + "..."

    return texto.strip()
