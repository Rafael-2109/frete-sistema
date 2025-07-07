"""
🔌 ADAPTADORES - Conectores para outros módulos
Resolve dependências entre diferentes partes do sistema
"""

from .intelligence_adapter import get_conversation_context, get_db_session
from .data_adapter import get_sistema_real_data

__all__ = [
    'get_conversation_context',
    'get_db_session', 
    'get_sistema_real_data'
] 