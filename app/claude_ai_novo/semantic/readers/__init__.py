"""
📚 READERS - Leitores de Dados Externos
======================================

Módulo responsável por ler dados de fontes externas
como README e banco de dados.

Readers Disponíveis:
- ReadmeReader    - Leitura do README de mapeamento
- DatabaseReader  - Leitura de dados reais do banco
"""

from .readme_reader import ReadmeReader
from .database_reader import DatabaseReader

__all__ = [
    'ReadmeReader',
    'DatabaseReader'
] 