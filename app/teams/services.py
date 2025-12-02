"""
Serviços para integração Teams <-> Agente Claude SDK.

Recebe mensagens do Teams Workflow, envia para o Agente Claude,
e retorna a resposta formatada como Adaptive Card.
"""

import logging
import asyncio
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
    if not mensagem or not mensagem.strip():
        return criar_card_erro("Mensagem vazia recebida.")

    try:
        # Obtém resposta do agente Claude
        resposta_texto = _obter_resposta_agente(mensagem, usuario)

        if not resposta_texto:
            return criar_card_erro("O agente não retornou uma resposta.")

        # Formata como Adaptive Card
        return criar_card_resposta(resposta_texto, usuario)

    except Exception as e:
        logger.error(f"[TEAMS] Erro ao processar mensagem: {e}", exc_info=True)
        return criar_card_erro(f"Erro ao processar: {str(e)}")


def _obter_resposta_agente(mensagem: str, usuario: str) -> Optional[str]:
    """
    Obtém resposta do Agente Claude SDK.

    Args:
        mensagem: Mensagem do usuário
        usuario: Nome do usuário

    Returns:
        str: Texto da resposta do agente
    """
    from app.agente.sdk import get_client

    client = get_client()

    # Executa a coroutine de forma síncrona
    # (Flask não é async, então usamos asyncio.run)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        response = loop.run_until_complete(
            client.get_response(
                prompt=mensagem,
                user_name=usuario,
                max_turns=5,  # Limita turnos para resposta rápida
            )
        )
        return response.text

    finally:
        loop.close()


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

    # Trunca texto muito longo (limite do Teams)
    if len(texto) > 3000:
        texto = texto[:2997] + "..."

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
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
                "text": f"_{usuario} • {agora}_",
                "size": "Small",
                "color": "Light",
                "spacing": "Medium",
                "horizontalAlignment": "Right"
            }
        ],
        "actions": [
            {
                "type": "Action.OpenUrl",
                "title": "Abrir Sistema",
                "url": "https://www.sistema-fretes.onrender.com/agente"
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
