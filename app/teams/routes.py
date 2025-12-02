"""
Rotas para integração com Microsoft Teams via Workflows.
Recebe mensagens do Teams e retorna Adaptive Cards como resposta.
"""

from flask import request, jsonify
from app.teams import teams_bp
from app.teams.services import processar_mensagem_teams


@teams_bp.route('/webhook', methods=['POST'])
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
    try:
        dados = request.json or {}

        mensagem = dados.get('mensagem', '').strip()
        usuario = dados.get('usuario', 'Usuário')

        # Processa a mensagem e gera resposta
        resposta = processar_mensagem_teams(mensagem, usuario)

        return jsonify(resposta), 200

    except Exception as e:
        # Retorna card de erro
        return jsonify({
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "❌ Erro ao processar mensagem",
                    "weight": "Bolder",
                    "size": "Medium",
                    "color": "Attention"
                },
                {
                    "type": "TextBlock",
                    "text": str(e),
                    "wrap": True
                }
            ]
        }), 200  # Retorna 200 mesmo com erro para o Teams exibir o card
