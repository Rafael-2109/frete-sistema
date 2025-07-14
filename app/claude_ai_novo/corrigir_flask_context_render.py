#!/usr/bin/env python3
"""
🔧 CORREÇÃO CRÍTICA: Flask Context no Render

PROBLEMA IDENTIFICADO:
1. Sistema antigo (claude_ai) funciona melhor porque:
   - Faz imports diretos dos modelos
   - Acessa db diretamente sem abstrações
   - Executa queries no contexto da requisição Flask

2. Sistema novo (claude_ai_novo) falha porque:
   - Loaders tentam acessar db sem Flask context
   - Arquitetura modular não propaga app context
   - Workers do Gunicorn não compartilham contexto

SOLUÇÃO: Garantir Flask context em todos os Loaders
"""

import os
import sys
from pathlib import Path

def criar_solucao_simples():
    """Cria solução simples e direta para o problema de contexto Flask"""
    
    print("🔧 APLICANDO SOLUÇÃO SIMPLES PARA FLASK CONTEXT...")
    
    # 1. Criar um middleware simples para garantir contexto
    middleware_content = '''#!/usr/bin/env python3
"""
Middleware para garantir Flask context no sistema novo
"""

from flask import current_app, has_app_context
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def ensure_flask_context(func):
    """Decorator que garante Flask context"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if has_app_context():
            # Já tem contexto, executar normalmente
            return func(*args, **kwargs)
        elif current_app:
            # Tem app mas não contexto, criar contexto
            with current_app.app_context():
                return func(*args, **kwargs)
        else:
            # Sem app disponível
            logger.warning(f"⚠️ {func.__name__} executado sem Flask context")
            return func(*args, **kwargs)
    return wrapper

# Solução alternativa: usar o db da aplicação principal
def get_db_from_app():
    """Obtém db da aplicação principal"""
    try:
        if current_app and hasattr(current_app, 'extensions'):
            return current_app.extensions.get('sqlalchemy')
    except:
        pass
    
    # Fallback: importar diretamente
    try:
        from app import db
        return db
    except:
        return None
'''
    
    middleware_path = Path("flask_context_middleware.py")
    middleware_path.write_text(middleware_content, encoding='utf-8')
    print("✅ Middleware criado!")
    
    # 2. Criar versão corrigida do LoaderManager
    loader_fix_content = '''#!/usr/bin/env python3
"""
LoaderManager corrigido com Flask context
"""

import logging
from typing import Dict, Any, Optional
from flask import current_app, has_app_context

logger = logging.getLogger(__name__)

class LoaderManagerFixed:
    """LoaderManager que funciona corretamente no Render"""
    
    def __init__(self, db=None):
        self.db = db
        self._loaders = {}
        
    def load_data(self, domain: str, filters: Dict[str, Any] = None, limit: int = 100) -> Dict[str, Any]:
        """Carrega dados garantindo Flask context"""
        
        # Se tem contexto Flask, usa
        if has_app_context():
            return self._load_with_context(domain, filters, limit)
        
        # Se tem current_app mas não contexto, cria contexto
        elif current_app:
            with current_app.app_context():
                return self._load_with_context(domain, filters, limit)
        
        # Sem Flask disponível, retorna vazio
        else:
            logger.warning(f"❌ LoaderManager: Sem Flask context para domínio {domain}")
            return {"data": [], "total": 0, "error": "Sem Flask context"}
    
    def _load_with_context(self, domain: str, filters: Dict[str, Any], limit: int) -> Dict[str, Any]:
        """Carrega dados com contexto garantido"""
        try:
            # Garantir que tem db
            if not self.db:
                from app import db as app_db
                self.db = app_db
            
            # Obter loader específico
            loader = self._get_loader(domain)
            if loader:
                return loader.load_data(filters, limit)
            
            return {"data": [], "total": 0}
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar dados: {e}")
            return {"data": [], "total": 0, "error": str(e)}
    
    def _get_loader(self, domain: str):
        """Obtém loader específico do domínio"""
        # Implementação simplificada
        if domain not in self._loaders:
            self._create_loader(domain)
        return self._loaders.get(domain)
    
    def _create_loader(self, domain: str):
        """Cria loader para o domínio"""
        # Import dinâmico para evitar circular
        try:
            if domain == "entregas":
                from .loaders.domain.entregas_loader import EntregasLoader
                self._loaders[domain] = EntregasLoader(self.db)
            elif domain == "fretes":
                from .loaders.domain.fretes_loader import FretesLoader
                self._loaders[domain] = FretesLoader(self.db)
            # ... outros domínios
        except Exception as e:
            logger.error(f"❌ Erro ao criar loader para {domain}: {e}")
'''
    
    loader_fix_path = Path("loader_manager_fixed.py")
    loader_fix_path.write_text(loader_fix_content, encoding='utf-8')
    print("✅ LoaderManager corrigido criado!")
    
    # 3. Instruções para aplicar a correção
    print("\n📋 COMO APLICAR A CORREÇÃO:\n")
    
    print("1. No arquivo app/claude_transition.py, adicione após os imports:")
    print("   from app import create_app")
    print("   _flask_app = create_app()")
    print("")
    
    print("2. No método _initialize_system(), modifique para:")
    print("   # Sistema novo com Flask context")
    print("   with _flask_app.app_context():")
    print("       self.claude = OrchestratorManager()")
    print("")
    
    print("3. No método processar_consulta(), adicione:")
    print("   with _flask_app.app_context():")
    print("       return await self.claude.process_query(query, context)")
    print("")
    
    print("✅ SOLUÇÃO CRIADA COM SUCESSO!")
    
    return True

if __name__ == "__main__":
    criar_solucao_simples() 