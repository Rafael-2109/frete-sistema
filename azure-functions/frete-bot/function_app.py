"""
Azure Function V2 - Entry point para o Bot do Microsoft Teams.

Endpoint POST /api/messages recebe activities do Bot Framework Service,
valida o token JWT via adapter, e roteia para o FreteBot.
"""

import azure.functions as func
import json
import logging

app = func.FunctionApp()

logger = logging.getLogger(__name__)

# Import do bot com tratamento de erro para nao bloquear registro da function
BOT_APP = None
try:
    from bot import BOT_APP
    logger.info("[FUNC] BOT_APP carregado com sucesso")
except Exception as e:
    logger.exception(f"[FUNC] ERRO ao carregar BOT_APP: {e}")


@app.route(
    route="api/messages",
    methods=["POST"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
async def messages(req: func.HttpRequest) -> func.HttpResponse:
    """
    Endpoint que recebe mensagens do Bot Framework / Teams.

    A autenticacao e feita pelo BotFrameworkAdapter (validacao de JWT),
    por isso o auth_level e ANONYMOUS no nivel do Azure Functions.
    """
    if BOT_APP is None:
        logger.error("[FUNC] BOT_APP nao foi inicializado")
        return func.HttpResponse(
            body=json.dumps({"error": "Bot nao inicializado. Verifique logs."}),
            status_code=500,
            mimetype="application/json",
        )

    try:
        body = req.get_body().decode("utf-8")
        auth_header = req.headers.get("Authorization", "")

        logger.info("[FUNC] POST /api/messages recebido")

        response = await BOT_APP.process(auth_header, body)

        if response:
            return func.HttpResponse(
                body=json.dumps(response.body) if response.body else "",
                status_code=response.status,
                mimetype="application/json",
            )

        return func.HttpResponse(status_code=200)

    except Exception as e:
        logger.exception(f"[FUNC] Erro no endpoint /api/messages: {e}")
        return func.HttpResponse(
            body=json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
