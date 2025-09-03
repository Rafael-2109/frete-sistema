"""
API para dados do dashboard da carteira
"""

from flask import jsonify
from flask_login import login_required
from app.separacao.models import Separacao
from . import carteira_bp
import logging

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/separacoes-programadas')
@login_required
def api_separacoes_programadas():
    """
    API para buscar dados de separações programadas (não sincronizadas)
    Retorna totais e valores por data de expedição
    """
    try:
        # Buscar separações não sincronizadas (inclui PREVISAO, ABERTO, COTADO)
        # MIGRADO: Removido JOIN com Pedido VIEW, usa sincronizado_nf=False
        separacoes = Separacao.query.filter(
            Separacao.sincronizado_nf == False
        ).all()
        
        # Calcular totais
        total_quantidade = 0
        total_valor = 0
        valores_por_data = {}
        
        for separacao in separacoes:
            # Contabilizar totais
            total_quantidade += 1
            valor = float(separacao.valor_saldo or 0)
            total_valor += valor
            
            # Agrupar por data de expedição
            if separacao.expedicao:
                data_str = separacao.expedicao.strftime('%Y-%m-%d')
                if data_str not in valores_por_data:
                    valores_por_data[data_str] = 0
                valores_por_data[data_str] += valor
        
        # Preparar resposta
        return jsonify({
            'success': True,
            'total_quantidade': total_quantidade,
            'total_valor': total_valor,
            'por_data': valores_por_data
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar separações programadas: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'total_quantidade': 0,
            'total_valor': 0,
            'por_data': {}
        }), 500