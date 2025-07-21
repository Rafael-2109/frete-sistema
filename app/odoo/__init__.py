"""
Módulo Odoo - Integração com Sistema ERP Odoo
==============================================

Este módulo organiza todas as integrações com o sistema Odoo ERP,
seguindo uma arquitetura modular por domínios de negócio.

Estrutura:
- routes/: Rotas organizadas por domínio (sincronização integrada)
- services/: Lógica de negócio e integração com Odoo
- validators/: Validações específicas para dados do Odoo
- utils/: Mapeadores de campos e utilitários
- config/: Configurações de conexão e mapeamentos

NOTA: As rotas antigas de carteira e faturamento foram removidas.
Toda funcionalidade foi migrada para app.api.odoo.routes

Autor: Sistema de Fretes
Data: 2025-07-14
"""

# Importar utilitários principais
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils import (
    get_carteira_mapper,
    get_faturamento_mapper,
    get_faturamento_produto_mapper
)

# Importar serviços principais
from app.odoo.services.carteira_service import CarteiraService
from app.odoo.services.faturamento_service import FaturamentoService
from app.odoo.services.sincronizacao_integrada_service import SincronizacaoIntegradaService

# Importar configuração
from app.odoo.config.odoo_config import ODOO_CONFIG

# Funções de conveniência para acesso rápido
def get_carteira_service():
    """Retorna instância do serviço de carteira"""
    return CarteiraService()

def get_faturamento_service():
    """Retorna instância do serviço de faturamento"""
    return FaturamentoService()

def get_sincronizacao_integrada_service():
    """Retorna instância do serviço de sincronização integrada"""
    return SincronizacaoIntegradaService()

# Configuração global do módulo
# (importada de app.odoo.config.odoo_config)

__all__ = [
    'get_carteira_service',
    'get_faturamento_service',
    'get_sincronizacao_integrada_service',
    'get_odoo_connection',
    'get_carteira_mapper',
    'get_faturamento_mapper',
    'get_faturamento_produto_mapper',
    'CarteiraService',
    'FaturamentoService',
    'SincronizacaoIntegradaService',
    'ODOO_CONFIG'
] 