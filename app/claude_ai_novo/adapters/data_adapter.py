"""
📊 DATA ADAPTER  
Adaptador para conectar com sistema_real_data
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def get_sistema_real_data():
    """
    Adaptador para sistema_real_data - usa data_provider do sistema novo
    """
    try:
        # Importar do data_provider do sistema novo
        from ..data.providers.data_provider import get_sistema_real_data as _get_real_data
        return _get_real_data()
    except ImportError:
        logger.warning("⚠️ Sistema Real Data não disponível - criando mock")
        return MockSistemaRealData()

class MockSistemaRealData:
    """Mock para SistemaRealData quando não disponível"""
    
    def __init__(self):
        logger.info("🔄 MockSistemaRealData inicializado")
        
    def buscar_todos_modelos_reais(self) -> Dict[str, Any]:
        """Retorna modelos mock para teste"""
        return {
            'Pedido': {
                'campos': [
                    {'nome': 'num_pedido', 'tipo': 'VARCHAR'},
                    {'nome': 'cliente', 'tipo': 'VARCHAR'},
                    {'nome': 'valor_total', 'tipo': 'DECIMAL'}
                ]
            },
            'EntregaMonitorada': {
                'campos': [
                    {'nome': 'numero_nf', 'tipo': 'VARCHAR'},
                    {'nome': 'cliente', 'tipo': 'VARCHAR'},
                    {'nome': 'transportadora', 'tipo': 'VARCHAR'}
                ]
            }
        }
        
    def buscar_dados_por_modelo(self, modelo: str) -> Dict[str, Any]:
        """Retorna dados mock por modelo"""
        modelos = self.buscar_todos_modelos_reais()
        return modelos.get(modelo, {})
        
    def executar_consulta_sql(self, sql: str) -> Dict[str, Any]:
        """Mock para consultas SQL"""
        return {
            'success': True,
            'data': [],
            'message': 'Mock SQL execution'
        } 