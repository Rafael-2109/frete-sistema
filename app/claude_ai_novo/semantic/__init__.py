"""
🧠 MÓDULO SEMÂNTICO - Claude AI Novo
====================================

Módulo responsável pelo mapeamento semântico entre linguagem natural 
e campos do banco de dados do sistema de fretes.

Arquitetura Modular:
- mappers/      - Mapeamentos por modelo de dados
- validators/   - Validações de contexto de negócio  
- relationships/ - Relacionamentos entre modelos
- readers/      - Leitores de dados (README, banco)
- diagnostics/  - Estatísticas e diagnósticos

Uso:
    from app.claude_ai_novo.semantic import get_semantic_manager
    
    manager = get_semantic_manager()
    resultados = manager.mapear_termo_natural("número do pedido")
"""

from .semantic_manager import SemanticManager

# Instância global (singleton)
_semantic_manager = None

def get_semantic_manager() -> SemanticManager:
    """
    Retorna instância singleton do SemanticManager
    
    Returns:
        SemanticManager: Instância do gerenciador semântico
    """
    global _semantic_manager
    
    if _semantic_manager is None:
        _semantic_manager = SemanticManager()
        
    return _semantic_manager

# Compatibilidade com versão anterior
def get_mapeamento_semantico():
    """Compatibilidade com versão anterior"""
    return get_semantic_manager()

__all__ = [
    'SemanticManager',
    'get_semantic_manager', 
    'get_mapeamento_semantico'
] 