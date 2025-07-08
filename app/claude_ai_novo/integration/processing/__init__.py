"""
⚙️ PROCESSING MODULE - Processamento

Este módulo contém os sistemas de processamento:
- Processador de consultas
- Formatador de respostas
- Pipelines de processamento
"""

from ...processors.query_processor import QueryProcessor
from .response_formatter import ResponseFormatter

__all__ = [
    'QueryProcessor',
    'ResponseFormatter',
]
