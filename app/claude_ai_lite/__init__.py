"""
Claude AI Lite - Modulo minimo funcional e modular.

Estrutura:
- core.py: Orquestra o fluxo
- claude_client.py: Cliente API Claude
- routes.py: Endpoints Flask
- domains/: Dominios de negocio (carteira, fretes, etc)

Uso:
    from app.claude_ai_lite import processar_consulta
    resposta = processar_consulta("Pedido VCD2509030 tem separacao?")
"""

from .core import processar_consulta

__all__ = ['processar_consulta']
