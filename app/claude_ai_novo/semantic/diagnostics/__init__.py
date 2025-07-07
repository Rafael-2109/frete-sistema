"""
📊 DIAGNOSTICS - Diagnósticos e Estatísticas
===========================================

Módulo responsável por gerar estatísticas e diagnósticos
do sistema de mapeamento semântico.

Diagnostics Disponíveis:
- CoverageStats      - Estatísticas de cobertura
- QualityDiagnostics - Diagnósticos de qualidade
"""

from .coverage_stats import CoverageStats
from .quality_diagnostics import QualityDiagnostics

__all__ = [
    'CoverageStats',
    'QualityDiagnostics'
] 