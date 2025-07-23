"""
Rotas para visualização agrupada da carteira
"""

from flask import render_template, flash
from flask_login import login_required
from sqlalchemy import func, and_, inspect
from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from ..services.agrupamento_service import AgrupamentoService
from . import carteira_bp
import logging

logger = logging.getLogger(__name__)


@carteira_bp.route('/agrupados')
@carteira_bp.route('/workspace')  # Rota adicional mais semântica
@login_required
def listar_pedidos_agrupados():
    """
    Lista pedidos agrupados por num_pedido conforme especificação
    """
    try:
        # Verificar se sistema está inicializado
        if not _verificar_sistema_inicializado():
            flash('Sistema de carteira ainda não foi inicializado', 'warning')
            return render_template('carteira/agrupados_balanceado.html', pedidos=None)
        
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


def _verificar_sistema_inicializado():
    """Verifica se as tabelas necessárias existem"""
    inspector = inspect(db.engine)
    tabelas_necessarias = ['carteira_principal', 'cadastro_palletizacao']
    
    for tabela in tabelas_necessarias:
        if not inspector.has_table(tabela):
            logger.warning(f'Tabela {tabela} não encontrada')
            return False
    
    return True