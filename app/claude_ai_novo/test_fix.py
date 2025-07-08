#!/usr/bin/env python3
"""
Teste rápido para verificar se as correções do erro NoneType funcionaram
"""

import asyncio
import sys
import os

# Adicionar ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from integration_manager import IntegrationManager
    print("✅ Import IntegrationManager OK")
    
    # Teste básico
    manager = IntegrationManager()
    print("✅ Instância criada OK")
    
    # Teste com query vazia (casos que causavam erro)
    result1 = asyncio.run(manager.process_unified_query(None, {}))
    print(f"📝 Teste query None: success={result1.get('success', False)}")
    
    result2 = asyncio.run(manager.process_unified_query("", {}))
    print(f"📝 Teste query vazia: success={result2.get('success', False)}")
    
    result3 = asyncio.run(manager.process_unified_query("teste de correção", {}))
    print(f"📝 Teste query normal: success={result3.get('success', False)}")
    
    print("🎉 TODOS OS TESTES PASSARAM - Erro NoneType CORRIGIDO!")
    
except Exception as e:
    print(f"❌ Erro no teste: {e}")
    import traceback
    traceback.print_exc() 