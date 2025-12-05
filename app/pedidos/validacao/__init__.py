"""
Módulo de validação de preços para pedidos de redes de atacarejo
"""

from .models import TabelaRede, RegiaoTabelaRede
from .validador_precos import (
    ValidadorPrecos,
    ResultadoValidacao,
    ResultadoValidacaoPreco,
    validar_precos_documento,
    validar_documento_completo
)

__all__ = [
    'TabelaRede',
    'RegiaoTabelaRede',
    'ValidadorPrecos',
    'ResultadoValidacao',
    'ResultadoValidacaoPreco',
    'validar_precos_documento',
    'validar_documento_completo'
]
