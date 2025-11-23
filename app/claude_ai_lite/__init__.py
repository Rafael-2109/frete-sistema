"""
Claude AI Lite - Modulo minimo funcional e modular.

Estrutura:
- core.py: Orquestra o fluxo
- claude_client.py: Cliente API Claude
- routes.py: Endpoints Flask
- routes_admin.py: Endpoints de administração (memória/aprendizados)
- memory.py: Serviço de memória de conversas
- learning.py: Serviço de aprendizado
- models.py: Modelos de dados (histórico, aprendizados)
- domains/: Dominios de negocio (carteira, fretes, etc)

Uso:
    from app.claude_ai_lite import processar_consulta
    resposta = processar_consulta("Pedido VCD2509030 tem separacao?")
"""

from .core import processar_consulta
from .routes import claude_lite_bp
from .routes_admin import claude_lite_admin_bp

__all__ = ['processar_consulta', 'claude_lite_bp', 'claude_lite_admin_bp']
