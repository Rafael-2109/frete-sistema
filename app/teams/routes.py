"""
Rotas para integração com Microsoft Teams via Workflows.
Recebe mensagens do Teams e retorna Adaptive Cards como resposta.
"""

import logging
import json
from flask import request, jsonify, Response
from app.teams import teams_bp
from app.teams.services import processar_mensagem_teams, criar_card_erro
from app import csrf

logger = logging.getLogger(__name__)


@teams_bp.route('/webhook', methods=['POST'])
@csrf.exempt  # ⚠️ CSRF desabilitado: Webhook externo do Teams Workflow
def webhook_teams():
    """
    Endpoint que recebe mensagens do Teams Workflow.

    Payload esperado do Teams Workflow:
    {
        "mensagem": "texto da mensagem",
        "usuario": "nome do usuário"
    }

    Retorna: Adaptive Card JSON como text/plain para o Power Automate
    tratar como string (o conector "Postar cartão" espera string JSON, não Object)
    """
    logger.info("[TEAMS] Webhook recebido")
    
    try:
        # Tenta parsear o JSON de diferentes formas
        dados = None
        
        # Método 1: request.json (padrão Flask)
        try:
            dados = request.json
        except Exception:
            pass
        
        # Método 2: Parse manual do body
        if not dados:
            try:
                body = request.get_data(as_text=True)
                if body:
                    dados = json.loads(body)
            except Exception:
                pass
        
        # Método 3: Form data
        if not dados:
            dados = {
                'mensagem': request.form.get('mensagem', ''),
                'usuario': request.form.get('usuario', 'Usuário')
            }
        
        dados = dados or {}
        
        mensagem = str(dados.get('mensagem', '')).strip()
        usuario = str(dados.get('usuario', 'Usuário')).strip()
        
        logger.info(f"[TEAMS] Mensagem: '{mensagem[:50]}...' de '{usuario}'")

        if not mensagem:
            logger.warning("[TEAMS] Mensagem vazia")
            resposta = criar_card_erro("Nenhuma mensagem recebida.")
        else:
            # Processa a mensagem e gera resposta
            resposta = processar_mensagem_teams(mensagem, usuario)

        # Log detalhado do tipo e estrutura da resposta
        logger.info(f"[TEAMS] Tipo resposta: {type(resposta).__name__}")
        if isinstance(resposta, dict):
            logger.info(f"[TEAMS] Keys resposta: {list(resposta.keys())}")

        # Garante que a resposta é JSON válido
        try:
            json_str = json.dumps(resposta, ensure_ascii=False, indent=None)
            logger.info(f"[TEAMS] JSON gerado: {len(json_str)} chars")
            logger.debug(f"[TEAMS] JSON primeiros 200 chars: {json_str[:200]}")

            # Validação round-trip: garante que o JSON é parseável
            json.loads(json_str)
            logger.info("[TEAMS] JSON validado com sucesso (round-trip OK)")
        except (TypeError, ValueError) as e:
            logger.error(f"[TEAMS] FALHA ao serializar/validar JSON: {e}")
            logger.error(f"[TEAMS] resposta repr: {repr(resposta)[:500]}")
            resposta = criar_card_erro("Erro interno ao formatar resposta.")
            json_str = json.dumps(resposta, ensure_ascii=False)
        
        # Retorna como text/plain para o Power Automate NÃO parsear como Object.
        # O conector "Postar cartão" do Teams espera receber string JSON, não Object.
        return Response(
            response=json_str,
            status=200,
            mimetype='text/plain',
            headers={
                'Content-Type': 'text/plain; charset=utf-8'
            }
        )

    except Exception as e:
        logger.error(f"[TEAMS] Erro no webhook: {e}", exc_info=True)
        
        # Retorna card de erro de forma segura
        erro_card = criar_card_erro("Erro interno. Tente novamente.")
        
        return Response(
            response=json.dumps(erro_card, ensure_ascii=False),
            status=200,  # 200 para o Teams exibir o card
            mimetype='text/plain',
            headers={
                'Content-Type': 'text/plain; charset=utf-8'
            }
        )


@teams_bp.route('/test-card', methods=['POST'])
@csrf.exempt
def test_card():
    """
    Retorna Adaptive Card estático para validar formato JSON.

    Útil para testar se o Power Automate consegue parsear a resposta
    sem depender do Agent SDK.
    """
    logger.info("[TEAMS] Test card solicitado")

    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "Teste OK - Integracao Teams funcionando",
                "weight": "Bolder",
                "size": "Medium",
                "color": "Accent"
            },
            {
                "type": "TextBlock",
                "text": "Este e um card de teste estatico para validar o formato JSON.",
                "wrap": True,
                "spacing": "Medium"
            }
        ]
    }

    json_str = json.dumps(card, ensure_ascii=False)
    logger.info(f"[TEAMS] Test card: {len(json_str)} chars")

    return Response(
        response=json_str,
        status=200,
        mimetype='text/plain',
        headers={
            'Content-Type': 'text/plain; charset=utf-8'
        }
    )


@teams_bp.route('/health', methods=['GET'])
def health_check():
    """Health check para verificar se o endpoint está funcionando."""
    return jsonify({
        "status": "ok",
        "service": "teams-webhook"
    })