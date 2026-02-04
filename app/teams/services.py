"""
Servicos para integracao Teams Bot <-> Agente Claude SDK.

Recebe mensagens do bot Azure Function, envia para o Agente Claude,
e retorna a resposta como texto puro (cards sao montados na Azure Function).
"""

import logging
import asyncio
import re
from typing import Optional

logger = logging.getLogger(__name__)


def processar_mensagem_bot(mensagem: str, usuario: str) -> str:
    """
    Processa mensagem do bot Teams enviando para o Agente Claude SDK.

    Retorna texto puro (sem Adaptive Card).
    A formatacao como card e responsabilidade da Azure Function.

    Args:
        mensagem: Texto da mensagem do usuario
        usuario: Nome do usuario que enviou

    Returns:
        str: Texto da resposta do agente

    Raises:
        ValueError: Se mensagem estiver vazia
        RuntimeError: Se o agente nao retornar resposta
    """
    logger.info(f"[TEAMS-BOT] Processando mensagem de '{usuario}': {mensagem[:100]}...")

    if not mensagem or not mensagem.strip():
        raise ValueError("Mensagem vazia recebida")

    resposta_texto = _obter_resposta_agente(mensagem, usuario)

    if not resposta_texto:
        raise RuntimeError("O agente nao retornou uma resposta")

    logger.info(f"[TEAMS-BOT] Resposta obtida: {len(resposta_texto)} caracteres")
    return resposta_texto


def _obter_resposta_agente(mensagem: str, usuario: str) -> Optional[str]:
    """
    Obtem resposta do Agente Claude SDK.

    Args:
        mensagem: Mensagem do usuario
        usuario: Nome do usuario

    Returns:
        str: Texto da resposta do agente
    """
    try:
        from app.agente.sdk import get_client
        client = get_client()
    except Exception as e:
        logger.error(f"[TEAMS-BOT] Erro ao obter client: {e}")
        return None

    # Contexto especial para Teams: instruir agente a dar resposta direta
    contexto_teams = """[CONTEXTO: Resposta via Microsoft Teams]
REGRAS OBRIGATORIAS:
- Voce tera APENAS UMA chance de responder
- NAO diga "vou consultar...", "deixa eu verificar..." - faca silenciosamente
- Responda APENAS com a informacao final e completa
- NAO use tabelas markdown (| col1 | col2 |) - nao renderiza no Teams
- NAO use headers (##, ###)
- USE apenas texto simples com quebras de linha
- Para listas use: "- item" em linhas separadas
- Mantenha resposta CONCISA (maximo 2000 caracteres)

PERGUNTA DO USUARIO:
"""

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
            )
        )

        resposta_texto = _extrair_texto_resposta(response)
        return resposta_texto

    except asyncio.TimeoutError:
        logger.error("[TEAMS-BOT] Timeout ao aguardar resposta do agente")
        return "Desculpe, a consulta demorou muito. Tente novamente com uma pergunta mais especifica."

    except Exception as e:
        logger.error(f"[TEAMS-BOT] Erro ao obter resposta do agente: {e}", exc_info=True)
        return None


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
