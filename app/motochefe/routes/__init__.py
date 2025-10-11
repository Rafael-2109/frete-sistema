"""
Blueprint principal do sistema MotoChefe
"""
from flask import Blueprint

# Criar blueprint
# Templates em: app/templates/motochefe/
motochefe_bp = Blueprint('motochefe', __name__, url_prefix='/motochefe')

# Importar rotas depois de criar blueprint para evitar imports circulares
from . import cadastros, produtos, operacional, logistica, vendas, financeiro, extrato, titulos_a_pagar, crossdocking #type: ignore


# ===== CONTEXT PROCESSOR =====
# Injeta contador de pendências no contexto de todos os templates do motochefe

@motochefe_bp.context_processor
def inject_contadores():
    """
    Injeta contadores de pendências para o navbar
    Disponível em todos os templates do motochefe
    """
    from app.motochefe.models import PedidoVendaAuditoria

    count_pendentes = PedidoVendaAuditoria.query\
        .filter_by(confirmado=False, rejeitado=False)\
        .count()

    return dict(count_pendentes_motochefe=count_pendentes)


__all__ = ['motochefe_bp']
