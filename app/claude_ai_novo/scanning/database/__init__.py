"""
📊 DATABASE SCANNERS MODULE - Módulos Especializados de Leitura de Banco

Este módulo contém scanners especializados para diferentes aspectos do banco:
- database_connection.py: Gestão de conexões
- metadata_scanner.py: Leitura de metadados das tabelas
- data_analyzer.py: Análise de dados reais
- relationship_mapper.py: Mapeamento de relacionamentos
- field_searcher.py: Busca de campos
- auto_mapper.py: Mapeamento automático
"""

# Imports dos módulos especializados
from .database_connection import DatabaseConnection
from .metadata_scanner import MetadataScanner
from .data_analyzer import DataAnalyzer
from .relationship_mapper import RelationshipMapper
from .field_searcher import FieldSearcher
from .auto_mapper import AutoMapper

# Exportações principais
__all__ = [
    'DatabaseConnection',
    'MetadataScanner',
    'DataAnalyzer',
    'RelationshipMapper',
    'FieldSearcher',
    'AutoMapper'
] 