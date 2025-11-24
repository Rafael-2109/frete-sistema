"""
Claude AI Lite - Modulo de IA conversacional modular e escalável.

Arquitetura v2.0:
- core/: Núcleo (orchestrator, classifier, responder)
- capabilities/: Capacidades auto-registráveis por domínio
- prompts/: Prompts centralizados
- memory.py: Memória de conversas
- learning.py: Aprendizado permanente

Domínios disponíveis:
- carteira: pedidos, disponibilidade, gargalos, rotas
- estoque: estoque, rupturas
- acao: criar separações

Uso:
    from app.claude_ai_lite import processar_consulta
    resposta = processar_consulta("Pedido VCD2509030 tem separacao?")

Para adicionar nova capacidade:
    1. Criar arquivo em capabilities/{dominio}/{nome}.py
    2. Herdar de BaseCapability
    3. Definir NOME, DOMINIO, INTENCOES, EXEMPLOS
    4. Implementar executar() e formatar_contexto()
    5. A capacidade será registrada automaticamente
"""

# Importa do novo core (mantém compatibilidade)
from .core import processar_consulta
from .routes import claude_lite_bp
from .routes_admin import claude_lite_admin_bp
from .ia_trainer.routes import bp as ia_trainer_bp

# Exporta também o registry de capacidades para uso externo
from .capabilities import get_capability, get_all_capabilities, find_capability

__all__ = [
    'processar_consulta',
    'claude_lite_bp',
    'claude_lite_admin_bp',
    'ia_trainer_bp',
    'get_capability',
    'get_all_capabilities',
    'find_capability'
]
