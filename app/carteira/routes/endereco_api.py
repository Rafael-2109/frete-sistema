"""
APIs para modais de endereço/incoterm da carteira agrupada
"""

from flask import jsonify
from flask_login import login_required
from app import db
from app.carteira.models import CarteiraPrincipal
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/pedido/<num_pedido>/endereco')
@login_required
def endereco_pedido(num_pedido):
    """
    API para obter dados de endereço de um pedido
    Usado pelo modal de endereço/incoterm
    """
    try:
        # Buscar dados completos do pedido (primeiro item como referência)
        pedido_info = db.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).first()

        if not pedido_info:
            return jsonify({
                'success': False,
                'error': f'Pedido {num_pedido} não encontrado'
            }), 404

        return jsonify({
            'success': True,
            'num_pedido': pedido_info.num_pedido,
            
            # Dados do cliente
            'raz_social': pedido_info.raz_social_red or pedido_info.raz_social,
            'cnpj_cpf': pedido_info.cnpj_cpf,
            'estado': pedido_info.estado,
            'municipio': pedido_info.municipio,
            'incoterm': getattr(pedido_info, 'incoterm', None) or 'CIF',
            
            # Endereço de entrega
            'empresa_endereco_ent': pedido_info.empresa_endereco_ent,
            'cnpj_endereco_ent': pedido_info.cnpj_endereco_ent,
            'cod_uf': pedido_info.cod_uf,
            'nome_cidade': pedido_info.nome_cidade,
            'bairro_endereco_ent': pedido_info.bairro_endereco_ent,
            'cep_endereco_ent': pedido_info.cep_endereco_ent,
            'rua_endereco_ent': pedido_info.rua_endereco_ent,
            'endereco_ent': pedido_info.endereco_ent,
            'telefone_endereco_ent': pedido_info.telefone_endereco_ent,
            
            # Dados do pedido
            'vendedor': pedido_info.vendedor,
            'equipe_vendas': pedido_info.equipe_vendas,
            # NOTA: Campos rota, sub_rota e expedicao foram REMOVIDOS de CarteiraPrincipal
            # Esses dados agora estão em Separacao (fonte única da verdade para dados operacionais)
            'rota': None,
            'sub_rota': None
        })

    except Exception as e:
        logger.error(f"Erro ao buscar endereço do pedido {num_pedido}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500
