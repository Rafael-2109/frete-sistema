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

    Retorna: Adaptive Card JSON para ser exibido no Teams
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

        # Garante que a resposta é JSON válido
        try:
            json_str = json.dumps(resposta, ensure_ascii=False, indent=None)
            logger.info(f"[TEAMS] Resposta: {len(json_str)} bytes")
        except (TypeError, ValueError) as e:
            logger.error(f"[TEAMS] Erro ao serializar resposta: {e}")
            resposta = criar_card_erro("Erro interno ao formatar resposta.")
            json_str = json.dumps(resposta, ensure_ascii=False)
        
        # Retorna como Response explícita para garantir Content-Type correto
        return Response(
            response=json_str,
            status=200,
            mimetype='application/json',
            headers={
                'Content-Type': 'application/json; charset=utf-8'
            }
        )

    except Exception as e:
        logger.error(f"[TEAMS] Erro no webhook: {e}", exc_info=True)
        
        # Retorna card de erro de forma segura
        erro_card = criar_card_erro("Erro interno. Tente novamente.")
        
        return Response(
            response=json.dumps(erro_card, ensure_ascii=False),
            status=200,  # 200 para o Teams exibir o card
            mimetype='application/json',
            headers={
                'Content-Type': 'application/json; charset=utf-8'
            }
        )


@teams_bp.route('/health', methods=['GET'])
def health_check():
    """Health check para verificar se o endpoint está funcionando."""
    return jsonify({
        "status": "ok",
        "service": "teams-webhook"
    })