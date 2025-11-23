"""
Core do Claude AI Lite.

Componentes:
- orchestrator: orquestra o fluxo principal
- classifier: classifica intenções usando Claude
- responder: gera respostas elaboradas
"""

from .orchestrator import processar_consulta

__all__ = ['processar_consulta']
