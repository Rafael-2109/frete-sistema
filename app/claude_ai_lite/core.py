"""
Core do Claude AI Lite - Redirecionador para novo módulo.

Este arquivo mantém compatibilidade com imports existentes,
redirecionando para o novo core em core/orchestrator.py

A arquitetura v2.0 está em:
- core/orchestrator.py: Orquestrador principal
- core/classifier.py: Classificador de intenções
- core/responder.py: Gerador de respostas
"""

# Importa do novo módulo core/
from .core.orchestrator import processar_consulta

# Mantém compatibilidade total
__all__ = ['processar_consulta']
