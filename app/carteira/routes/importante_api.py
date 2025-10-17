"""
API para gerenciamento de marcação de pedidos importantes
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import and_
import logging

from app import db
from app.carteira.models import CarteiraPrincipal

logger = logging.getLogger(__name__)

importante_bp = Blueprint("importante", __name__, url_prefix="/api")


@importante_bp.route("/toggle-importante", methods=["POST"])
@login_required
def toggle_importante():
    """
    Toggle do estado importante de um pedido

    Body JSON:
    {
        "num_pedido": "123456"
    }

    Retorna:
    {
        "success": true,
        "importante": true/false,
        "message": "Pedido marcado como importante"
    }
    """
    try:
        data = request.get_json()

        if not data or 'num_pedido' not in data:
            return jsonify({
                "success": False,
                "message": "Campo num_pedido é obrigatório"
            }), 400

        num_pedido = data['num_pedido']

        # Buscar TODOS os itens do pedido na carteira
        itens = CarteiraPrincipal.query.filter(
            and_(
                CarteiraPrincipal.num_pedido == num_pedido,
                CarteiraPrincipal.ativo == True
            )
        ).all()

        if not itens:
            return jsonify({
                "success": False,
                "message": f"Pedido {num_pedido} não encontrado na carteira"
            }), 404

        # Pegar estado atual do primeiro item (todos terão o mesmo)
        estado_atual = itens[0].importante

        # Inverter estado para TODOS os itens do pedido
        novo_estado = not estado_atual

        for item in itens:
            item.importante = novo_estado
            item.updated_by = getattr(current_user, 'nome', None) or getattr(current_user, 'username', None) or 'Sistema'

        db.session.commit()

        mensagem = f"Pedido {num_pedido} marcado como {'importante' if novo_estado else 'normal'}"

        logger.info(f"Toggle importante: {num_pedido} -> {novo_estado} por {item.updated_by}")

        return jsonify({
            "success": True,
            "importante": novo_estado,
            "message": mensagem
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao fazer toggle importante: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Erro ao alterar estado: {str(e)}"
        }), 500


@importante_bp.route("/status-importante/<num_pedido>", methods=["GET"])
@login_required
def status_importante(num_pedido):
    """
    Consulta o estado importante de um pedido

    Retorna:
    {
        "success": true,
        "importante": true/false
    }
    """
    try:
        # Buscar qualquer item do pedido para pegar o estado
        item = CarteiraPrincipal.query.filter(
            and_(
                CarteiraPrincipal.num_pedido == num_pedido,
                CarteiraPrincipal.ativo == True
            )
        ).first()

        if not item:
            return jsonify({
                "success": False,
                "message": f"Pedido {num_pedido} não encontrado"
            }), 404

        return jsonify({
            "success": True,
            "importante": item.importante
        }), 200

    except Exception as e:
        logger.error(f"Erro ao consultar status importante: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Erro ao consultar: {str(e)}"
        }), 500
