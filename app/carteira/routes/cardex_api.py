"""
APIs específicas para cardex D0-D28
"""

from flask import jsonify
from flask_login import login_required
# USAR NOVO SISTEMA DE ESTOQUE EM TEMPO REAL
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
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
        # Obter projeção completa usando Sistema de Estoque em Tempo Real
        projecao_completa = ServicoEstoqueTempoReal.get_projecao_completa(cod_produto, dias=28)

        if not projecao_completa:
            return jsonify({
                'success': False,
                'error': f'Produto {cod_produto} não encontrado ou sem movimentações'
            }), 404

        # Converter para formato compatível com cardex
        # A projeção completa já vem com os campos corretos
        resumo_estoque = {
            'estoque_inicial': projecao_completa['estoque_atual'],
            'estoque_atual': projecao_completa['estoque_atual'],
            'menor_estoque_d7': projecao_completa.get('menor_estoque_d7'),
            'dia_ruptura': projecao_completa.get('dia_ruptura'),
            'projecao_29_dias': projecao_completa.get('projecao', []),  # Usar array de projeção
            'status_ruptura': 'CRÍTICO' if projecao_completa.get('dia_ruptura') else 'OK'
        }

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