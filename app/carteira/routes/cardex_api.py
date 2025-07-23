"""
APIs específicas para cardex D0-D28
"""

from flask import jsonify
from flask_login import login_required
from app.estoque.models import SaldoEstoque
from app.carteira.utils.workspace_utils import (
    converter_projecao_para_cardex,
    calcular_estatisticas_cardex,
    gerar_alertas_reais
)
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/produto/<cod_produto>/cardex')
@login_required
def cardex_produto_real(cod_produto):
    """
    API real para cardex D0-D28 usando SaldoEstoque
    """
    try:
        # Obter resumo completo do produto usando SaldoEstoque
        resumo_estoque = SaldoEstoque.obter_resumo_produto(cod_produto, '')

        if not resumo_estoque:
            return jsonify({
                'success': False,
                'error': f'Produto {cod_produto} não encontrado ou sem movimentações'
            }), 404

        # Converter projeção para formato do cardex
        cardex_dados = converter_projecao_para_cardex(resumo_estoque)

        # Calcular estatísticas
        estatisticas = calcular_estatisticas_cardex(cardex_dados)

        # Gerar alertas baseados em regras reais
        alertas = gerar_alertas_reais(resumo_estoque, cardex_dados)

        return jsonify({
            'success': True,
            'cod_produto': cod_produto,
            'estoque_atual': float(resumo_estoque['estoque_inicial']),
            'cardex': cardex_dados,
            **estatisticas,
            'alertas': alertas
        })

    except Exception as e:
        logger.error(f"Erro ao buscar cardex do produto {cod_produto}: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500