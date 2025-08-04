"""
Desabilita temporariamente os triggers problemáticos
Este arquivo deve ser importado no início da aplicação
"""

import logging
from sqlalchemy import event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def disable_problematic_triggers():
    """
    Desabilita os triggers que estão causando problemas de transação
    """
    try:
        # Importar os modelos
        from app.carteira.models import PreSeparacaoItem
        from app.estoque.models import MovimentacaoEstoque
        
        # Remover todos os listeners problemáticos de PreSeparacaoItem
        if hasattr(PreSeparacaoItem, '__mapper__'):
            # Limpar eventos after_insert
            if hasattr(PreSeparacaoItem.__mapper__.class_manager, 'events'):
                event.Events._remove(PreSeparacaoItem, 'after_insert')
                event.Events._remove(PreSeparacaoItem, 'after_update')
                event.Events._remove(PreSeparacaoItem, 'after_delete')
                logger.info("✅ Triggers de PreSeparacaoItem desabilitados")
        
        # Também podemos desabilitar temporariamente os triggers do MovimentacaoEstoque
        # se necessário
        
        logger.info("✅ Triggers problemáticos desabilitados com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao desabilitar triggers: {e}")
        return False

# Executar automaticamente ao importar
disable_problematic_triggers()