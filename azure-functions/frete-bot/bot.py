"""
Bot do Microsoft Teams para o Sistema de Frete.

Recebe mensagens via Bot Framework Service, envia para o backend no Render,
e responde no chat do Teams. Suporta flow de confirmacao via Adaptive Cards.

Componentes:
- BotApp: encapsula adapter + bot, expoe process()
- FreteBot: ActivityHandler com logica de mensagens e cards
- Adaptive Cards: confirmacao e erro
"""

import os
import json
import logging
from datetime import datetime

import aiohttp
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    TurnContext,
    ActivityHandler,
    CardFactory,
    MessageFactory,
)
from botbuilder.schema import Activity, ActivityTypes

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# CONFIGURACAO
# ═══════════════════════════════════════════════════════════════

MICROSOFT_APP_ID = os.environ.get("MICROSOFT_APP_ID", "")
MICROSOFT_APP_PASSWORD = os.environ.get("MICROSOFT_APP_PASSWORD", "")
MICROSOFT_APP_TENANT_ID = os.environ.get("MICROSOFT_APP_TENANT_ID", "")

BACKEND_URL = os.environ.get("BACKEND_URL", "https://sistema-fretes.onrender.com")
BACKEND_API_KEY = os.environ.get("BACKEND_API_KEY", "")
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "300"))


# ═══════════════════════════════════════════════════════════════
# ADAPTIVE CARDS
# ═══════════════════════════════════════════════════════════════

def build_confirmation_card(task_id: str, descricao: str, usuario: str) -> dict:
    """
    Adaptive Card v1.4 com botoes Confirmar/Cancelar.

    Usa Action.Submit que envia activity.value com dados do botao.
    Tratado em on_message_activity checando activity.value.
    """
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "msteams": {"width": "Full"},
        "body": [
            {
                "type": "TextBlock",
                "text": "Confirmacao Necessaria",
                "weight": "Bolder",
                "size": "Medium",
                "color": "Warning",
            },
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [
                            {
                                "type": "Image",
                                "url": "https://adaptivecards.io/content/pending.png",
                                "size": "Small",
                            }
                        ],
                    },
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "O agente precisa da sua aprovacao para executar a operacao abaixo:",
                                "wrap": True,
                                "size": "Small",
                                "color": "Light",
                            }
                        ],
                    },
                ],
            },
            {
                "type": "TextBlock",
                "text": descricao,
                "wrap": True,
                "spacing": "Medium",
            },
            {
                "type": "TextBlock",
                "text": f"{usuario} - {agora}",
                "size": "Small",
                "color": "Light",
                "spacing": "Medium",
                "horizontalAlignment": "Right",
            },
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "Confirmar",
                "style": "positive",
                "data": {
                    "action": "confirm",
                    "task_id": task_id,
                },
            },
            {
                "type": "Action.Submit",
                "title": "Cancelar",
                "style": "destructive",
                "data": {
                    "action": "cancel",
                    "task_id": task_id,
                },
            },
        ],
    }


def build_error_card(mensagem: str) -> dict:
    """Adaptive Card para exibir erros."""
    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "Erro",
                "weight": "Bolder",
                "size": "Medium",
                "color": "Attention",
            },
            {
                "type": "TextBlock",
                "text": mensagem,
                "wrap": True,
            },
        ],
    }


# ═══════════════════════════════════════════════════════════════
# BACKEND CLIENT
# ═══════════════════════════════════════════════════════════════

async def call_backend(endpoint: str, payload: dict) -> dict:
    """
    Chama o backend no Render via HTTP POST.

    Args:
        endpoint: Path relativo (ex: /api/teams/bot/message)
        payload: JSON body

    Returns:
        dict: Resposta JSON do backend

    Raises:
        Exception: Se o backend retornar erro ou timeout
    """
    url = f"{BACKEND_URL.rstrip('/')}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": BACKEND_API_KEY,
    }
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

    logger.info(f"[BOT] POST {url}")

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(
                    f"Backend retornou {resp.status}: {text[:300]}"
                )
            return await resp.json()


# ═══════════════════════════════════════════════════════════════
# BOT
# ═══════════════════════════════════════════════════════════════

class FreteBot(ActivityHandler):
    """
    Bot do Teams que faz relay de mensagens para o backend no Render.

    Fluxo de mensagem:
    1. Recebe texto do usuario
    2. Envia typing indicator
    3. Chama backend POST /api/teams/bot/message
    4. Responde com texto OU Adaptive Card de confirmacao

    Fluxo de confirmacao:
    1. Usuario clica Confirmar/Cancelar no card
    2. activity.value contem action e task_id
    3. Confirmar → chama POST /api/teams/bot/execute
    4. Cancelar → responde "Operacao cancelada"
    """

    async def on_message_activity(self, turn_context: TurnContext):
        """Trata mensagens de texto e respostas de Adaptive Cards."""

        # Se activity.value existe, e resposta de card (botao clicado)
        if turn_context.activity.value:
            await self._handle_card_response(turn_context)
            return

        # Mensagem de texto normal
        text = self._remove_bot_mention(turn_context)
        if not text:
            await turn_context.send_activity(
                "Por favor, envie uma mensagem de texto."
            )
            return

        user_name = (
            turn_context.activity.from_property.name or "Usuario"
        )
        user_id = (
            turn_context.activity.from_property.aad_object_id
            or turn_context.activity.from_property.id
            or ""
        )

        logger.info(
            f"[BOT] Mensagem de {user_name} ({user_id}): {text[:100]}"
        )

        # 1. Typing indicator
        await turn_context.send_activity(
            Activity(type=ActivityTypes.typing)
        )

        # 2. Chama o backend
        try:
            result = await call_backend(
                endpoint="/api/teams/bot/message",
                payload={
                    "mensagem": text,
                    "usuario": user_name,
                    "usuario_id": str(user_id),
                },
            )
        except TimeoutError:
            logger.error("[BOT] Timeout ao chamar backend")
            await turn_context.send_activity(
                MessageFactory.attachment(
                    CardFactory.adaptive_card(
                        build_error_card(
                            "Tempo limite excedido. O sistema demorou "
                            "muito para responder. Tente novamente."
                        )
                    )
                )
            )
            return
        except Exception as e:
            logger.error(f"[BOT] Erro ao chamar backend: {e}", exc_info=True)
            await turn_context.send_activity(
                MessageFactory.attachment(
                    CardFactory.adaptive_card(
                        build_error_card(
                            f"Nao consegui conectar ao sistema: {str(e)[:200]}"
                        )
                    )
                )
            )
            return

        # 3. Trata resposta
        if result.get("requer_confirmacao"):
            card = build_confirmation_card(
                task_id=result.get("task_id", ""),
                descricao=result.get("descricao", ""),
                usuario=user_name,
            )
            await turn_context.send_activity(
                MessageFactory.attachment(
                    CardFactory.adaptive_card(card)
                )
            )
        else:
            resposta = result.get("resposta", "Sem resposta do sistema.")
            await turn_context.send_activity(resposta)

    async def _handle_card_response(self, turn_context: TurnContext):
        """
        Trata clique em botoes do Adaptive Card.

        activity.value contem:
        - action: "confirm" ou "cancel"
        - task_id: ID da tarefa pendente
        """
        value = turn_context.activity.value or {}
        action = value.get("action", "")
        task_id = value.get("task_id", "")
        user_name = (
            turn_context.activity.from_property.name or "Usuario"
        )

        logger.info(
            f"[BOT] Card response: action={action}, "
            f"task_id={task_id}, user={user_name}"
        )

        if action == "confirm" and task_id:
            # Typing enquanto executa
            await turn_context.send_activity(
                Activity(type=ActivityTypes.typing)
            )

            try:
                result = await call_backend(
                    endpoint="/api/teams/bot/execute",
                    payload={"task_id": task_id},
                )
                resposta = result.get(
                    "resposta", "Operacao executada com sucesso."
                )
                await turn_context.send_activity(resposta)
            except Exception as e:
                logger.error(
                    f"[BOT] Erro ao executar tarefa: {e}", exc_info=True
                )
                await turn_context.send_activity(
                    MessageFactory.attachment(
                        CardFactory.adaptive_card(
                            build_error_card(
                                f"Erro ao executar operacao: {str(e)[:200]}"
                            )
                        )
                    )
                )

        elif action == "cancel":
            await turn_context.send_activity(
                "Operacao cancelada pelo usuario."
            )

        else:
            logger.warning(
                f"[BOT] Acao desconhecida no card: action={action}"
            )
            await turn_context.send_activity(
                "Acao nao reconhecida. Por favor, envie uma nova mensagem."
            )

    @staticmethod
    def _remove_bot_mention(turn_context: TurnContext) -> str:
        """
        Remove a mencao ao bot do texto da mensagem.

        Em grupos/canais, o Teams envia o texto como:
        "<at>BotName</at> qual o estoque?"
        Este metodo limpa a mencao e retorna so a pergunta.
        Em chats 1:1, retorna o texto original.
        """
        import re

        text = (turn_context.activity.text or "").strip()
        if not text:
            return ""

        # Remove tags <at>...</at> (mencao do bot)
        text = re.sub(r"<at>.*?</at>\s*", "", text).strip()

        return text

    async def on_members_added_activity(self, members_added, turn_context):
        """Mensagem de boas-vindas quando o bot e adicionado."""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    "Ola! Sou o Agente Logistico da Nacom Goya. "
                    "Mencione-me com @bot e sua pergunta para consultar "
                    "pedidos, estoque, entregas e mais."
                )


# ═══════════════════════════════════════════════════════════════
# BOT APP (encapsula adapter + bot)
# ═══════════════════════════════════════════════════════════════

class BotApp:
    """
    Encapsula BotFrameworkAdapter + FreteBot.

    Expoe process() para ser chamado pelo function_app.py.
    """

    def __init__(self):
        self.settings = BotFrameworkAdapterSettings(
            app_id=MICROSOFT_APP_ID,
            app_password=MICROSOFT_APP_PASSWORD,
            channel_auth_tenant=MICROSOFT_APP_TENANT_ID,
        )
        self.adapter = BotFrameworkAdapter(self.settings)
        self.adapter.on_turn_error = self._on_error
        self.bot = FreteBot()

    async def _on_error(self, context: TurnContext, error: Exception):
        """Handler global de erros do adapter."""
        logger.exception(f"[BOT] Erro nao tratado: {error}")
        try:
            await context.send_activity(
                "Ocorreu um erro inesperado. Tente novamente."
            )
        except Exception:
            logger.error("[BOT] Falha ao enviar mensagem de erro")

    async def process(self, auth_header: str, body: str):
        """
        Processa uma activity do Bot Framework.

        Args:
            auth_header: Header Authorization da request
            body: Body JSON como string

        Returns:
            InvokeResponse ou None
        """
        activity = Activity().deserialize(json.loads(body))

        response = await self.adapter.process_activity(
            activity,
            auth_header,
            self.bot.on_turn,
        )

        return response


# Instancia singleton
BOT_APP = BotApp()
