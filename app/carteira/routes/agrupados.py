"""
Rotas para visualização agrupada da carteira
"""

from flask import render_template, flash
from flask_login import login_required
from ..services.agrupamento_service import AgrupamentoService
from . import carteira_bp
import logging

logger = logging.getLogger(__name__)


@carteira_bp.route('/agrupados')
@carteira_bp.route('/workspace')  # Rota adicional mais semantica
@login_required
def listar_pedidos_agrupados():
    """
    Lista pedidos agrupados por num_pedido conforme especificacao
    """
    try:
        # FIX E6: Removida verificacao inspect(db.engine) a cada request.
        # As tabelas sao gerenciadas pelo ORM — se nao existissem, a app
        # nao iniciaria. Introspecao de schema e desnecessaria em producao.

        # Usar service para buscar dados agrupados
        agrupamento_service = AgrupamentoService()
        pedidos_enriquecidos = agrupamento_service.obter_pedidos_agrupados()

        logger.info(f"Query agrupamento executada: {len(pedidos_enriquecidos)} pedidos encontrados")

        return render_template('carteira/agrupados_balanceado.html',
                             pedidos=pedidos_enriquecidos,
                             total_pedidos=len(pedidos_enriquecidos))

    except Exception as e:
        logger.error(f"Erro ao listar pedidos agrupados: {str(e)}")
        flash(f'Erro ao carregar pedidos agrupados: {str(e)}', 'error')
        return render_template('carteira/agrupados_balanceado.html', pedidos=None)
