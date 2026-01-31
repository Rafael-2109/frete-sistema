"""
Serviços para integração Teams <-> Agente Claude SDK.

Recebe mensagens do Teams Workflow, envia para o Agente Claude,
e retorna a resposta formatada como Adaptive Card.
"""

import logging
import asyncio
import json
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def processar_mensagem_teams(mensagem: str, usuario: str) -> dict:
    """
    Processa mensagem do Teams enviando para o Agente Claude SDK.

    Args:
        mensagem: Texto da mensagem do usuário
        usuario: Nome do usuário que enviou

    Returns:
        dict: Adaptive Card JSON com a resposta do agente
    """
    logger.info(f"[TEAMS] Processando mensagem de '{usuario}': {mensagem[:100]}...")
    
    if not mensagem or not mensagem.strip():
        logger.warning("[TEAMS] Mensagem vazia recebida")
        return criar_card_erro("Mensagem vazia recebida.")

    try:
        # Obtém resposta do agente Claude
        resposta_texto = _obter_resposta_agente(mensagem, usuario)

        if not resposta_texto:
            logger.warning("[TEAMS] Agente não retornou resposta")
            return criar_card_erro("O agente não retornou uma resposta.")

        logger.info(f"[TEAMS] Resposta obtida: {len(resposta_texto)} caracteres")
        
        # Formata como Adaptive Card
        card = criar_card_resposta(resposta_texto, usuario)
        
        # Valida se o card é JSON serializável
        try:
            json.dumps(card, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.error(f"[TEAMS] Card não é JSON válido: {e}")
            return criar_card_erro("Erro ao formatar resposta.")
        
        return card

    except Exception as e:
        logger.error(f"[TEAMS] Erro ao processar mensagem: {e}", exc_info=True)
        return criar_card_erro(f"Erro ao processar sua solicitação. Tente novamente.")


def _obter_resposta_agente(mensagem: str, usuario: str) -> Optional[str]:
    """
    Obtém resposta do Agente Claude SDK.

    Args:
        mensagem: Mensagem do usuário
        usuario: Nome do usuário

    Returns:
        str: Texto da resposta do agente
    """
    try:
        from app.agente.sdk import get_client
        client = get_client()
    except Exception as e:
        logger.error(f"[TEAMS] Erro ao obter client: {e}")
        return None

    # Contexto especial para Teams: instruir agente a dar resposta direta
    # Inclui diretamente no prompt já que get_response não aceita extra_context
    contexto_teams = """[CONTEXTO: Resposta via Microsoft Teams - Adaptive Card]
REGRAS OBRIGATÓRIAS:
• Você terá APENAS UMA chance de responder
• NÃO diga "vou consultar...", "deixa eu verificar..." - faça silenciosamente
• Responda APENAS com a informação final e completa
• NÃO use tabelas markdown (| col1 | col2 |) - não renderiza
• NÃO use headers (##, ###)
• USE apenas texto simples com quebras de linha
• Para listas use: "• item" em linhas separadas
• Mantenha resposta CONCISA (máximo 2000 caracteres)

PERGUNTA DO USUÁRIO:
"""

    # Combina contexto + mensagem no prompt
    prompt_completo = contexto_teams + mensagem

    # Executa a coroutine de forma síncrona
    try:
        # Tenta usar loop existente ou cria novo
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
        
        # Extrai o texto da resposta
        resposta_texto = _extrair_texto_resposta(response)
        
        return resposta_texto

    except asyncio.TimeoutError:
        logger.error("[TEAMS] Timeout ao aguardar resposta do agente")
        return "Desculpe, a consulta demorou muito. Tente novamente com uma pergunta mais específica."
    
    except Exception as e:
        logger.error(f"[TEAMS] Erro ao obter resposta do agente: {e}", exc_info=True)
        return None


def _extrair_texto_resposta(response) -> Optional[str]:
    """
    Extrai texto da resposta do SDK, tratando diferentes formatos.

    Args:
        response: Objeto de resposta do SDK

    Returns:
        str: Texto extraído e limpo
    """
    texto = None

    # Log do tipo de resposta para debug
    logger.debug(f"[TEAMS] Tipo de response: {type(response).__name__}")
    if hasattr(response, 'text'):
        logger.debug(f"[TEAMS] response.text presente: {bool(response.text)}")
    if hasattr(response, 'content'):
        logger.debug(f"[TEAMS] response.content tipo: {type(response.content).__name__}")

    # Tenta diferentes formas de extrair o texto
    if hasattr(response, 'text') and response.text:
        texto = response.text
        logger.debug(f"[TEAMS] Texto extraído via response.text: {len(texto)} chars")
    elif hasattr(response, 'content') and response.content:
        # Se content é uma lista de blocos
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
            # CRÍTICO: bytes deve ser decode(), NUNCA str() que gera b'...'
            texto = response.content.decode('utf-8', errors='replace')
            logger.warning(f"[TEAMS] response.content era bytes, decodificado: {texto[:100]}")
        elif isinstance(response.content, str):
            texto = response.content
        else:
            texto = str(response.content)
            # Detecta e corrige padrão b'...' gerado por str(bytes)
            if texto.startswith("b'") or texto.startswith('b"'):
                logger.warning(f"[TEAMS] Detectado padrão bytes em str(): {texto[:50]}")
                texto = texto[2:-1]
    elif isinstance(response, str):
        texto = response
    elif isinstance(response, bytes):
        texto = response.decode('utf-8', errors='replace')
    else:
        # Último recurso: converte para string
        texto = str(response)
        # Detecta e corrige padrão b'...' gerado por str(bytes)
        if texto.startswith("b'") or texto.startswith('b"'):
            logger.warning(f"[TEAMS] str(response) gerou padrão bytes: {texto[:50]}")
            texto = texto[2:-1]

    if texto:
        # Limpa e sanitiza o texto
        texto = _sanitizar_texto(texto)

    return texto


def _sanitizar_texto(texto: str) -> str:
    """
    Sanitiza o texto para ser seguro em JSON/Adaptive Card.

    Args:
        texto: Texto bruto

    Returns:
        str: Texto sanitizado
    """
    if not texto:
        return ""

    # Garante que é string
    if isinstance(texto, bytes):
        texto = texto.decode('utf-8', errors='replace')

    # Remove caracteres de controle (exceto newline e tab)
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)

    # Converte aspas curvas para retas (evita problemas JSON no Power Automate)
    texto = texto.replace('\u201c', '"').replace('\u201d', '"')   # " "
    texto = texto.replace('\u2018', "'").replace('\u2019', "'")   # ' '

    # Normaliza quebras de linha
    texto = texto.replace('\r\n', '\n').replace('\r', '\n')

    # Remove múltiplas quebras de linha consecutivas
    texto = re.sub(r'\n{3,}', '\n\n', texto)

    # Limita tamanho (Teams tem limite)
    if len(texto) > 2500:
        texto = texto[:2497] + "..."

    return texto.strip()


def criar_card_resposta(texto: str, usuario: str) -> dict:
    """
    Cria Adaptive Card com a resposta do agente.

    Args:
        texto: Texto da resposta
        usuario: Nome do usuário

    Returns:
        dict: Adaptive Card JSON
    """
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Sanitiza o texto novamente por segurança
    texto = _sanitizar_texto(texto) or "Resposta não disponível."
    usuario = _sanitizar_texto(usuario) or "Usuário"

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "msteams": {
            "width": "Full"
        },
        "body": [
            {
                "type": "TextBlock",
                "text": "🤖 Agente Logístico",
                "weight": "Bolder",
                "size": "Medium",
                "color": "Accent"
            },
            {
                "type": "TextBlock",
                "text": texto,
                "wrap": True,
                "spacing": "Medium"
            },
            {
                "type": "TextBlock",
                "text": f"{usuario} • {agora}",
                "size": "Small",
                "color": "Light",
                "spacing": "Medium",
                "horizontalAlignment": "Right"
            }
        ]
    }


def criar_card_erro(mensagem: str) -> dict:
    """
    Cria Adaptive Card de erro.

    Args:
        mensagem: Mensagem de erro

    Returns:
        dict: Adaptive Card JSON
    """
    mensagem = _sanitizar_texto(mensagem) or "Erro desconhecido"
    
    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "❌ Erro",
                "weight": "Bolder",
                "size": "Medium",
                "color": "Attention"
            },
            {
                "type": "TextBlock",
                "text": mensagem,
                "wrap": True
            }
        ]
    }