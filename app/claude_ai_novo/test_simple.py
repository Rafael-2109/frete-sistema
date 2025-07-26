#!/usr/bin/env python3
"""
Teste simples dos módulos sem dependências do Flask
"""

import sys
import os

# Adicionar diretórios ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.dirname(__file__))

print("🧪 Teste Simples do claude_ai_novo\n")

# Teste 1: Importar função corrigida diretamente
print("1️⃣ Testando generate_api_fallback_response...")
try:
    # Import direto do módulo
    import processors.response_processor as rp
    
    # Testar se a função existe
    if hasattr(rp, 'generate_api_fallback_response'):
        result = rp.generate_api_fallback_response("Erro de teste")
        print(f"   ✅ Função existe e retorna: {result}")
    else:
        print("   ❌ Função não encontrada no módulo")
except Exception as e:
    print(f"   ❌ Erro: {e}")

# Teste 2: Verificar BaseModule
print("\n2️⃣ Testando BaseModule...")
try:
    # Import direto
    import utils.base_classes as bc
    
    # Verificar se BaseModule existe
    if hasattr(bc, 'BaseModule'):
        print("   ✅ BaseModule existe no módulo")
        
        # Testar atributos esperados na definição da classe
        base_module_code = bc.BaseModule.__init__.__code__
        expected_attrs = ['logger', 'components', 'db', 'config', 'initialized', 'redis_cache']
        
        print("   📋 Atributos definidos no __init__:")
        for attr in expected_attrs:
            if attr in base_module_code.co_names or attr in str(base_module_code.co_consts):
                print(f"      ✓ {attr}")
            else:
                print(f"      ? {attr} (verificar manualmente)")
                
    else:
        print("   ❌ BaseModule não encontrada")
except Exception as e:
    print(f"   ❌ Erro: {e}")

# Teste 3: Verificar método process_query no SessionOrchestrator
print("\n3️⃣ Testando SessionOrchestrator.process_query...")
try:
    # Import direto
    import orchestrators.session_orchestrator as so
    
    # Verificar se SessionOrchestrator existe
    if hasattr(so, 'SessionOrchestrator'):
        # Verificar se o método existe
        if hasattr(so.SessionOrchestrator, 'process_query'):
            print("   ✅ Método process_query existe no SessionOrchestrator")
            
            # Verificar se é async
            import inspect
            if inspect.iscoroutinefunction(so.SessionOrchestrator.process_query):
                print("   ✅ Método é async (correto)")
            else:
                print("   ⚠️ Método não é async")
        else:
            print("   ❌ Método process_query não encontrado")
    else:
        print("   ❌ SessionOrchestrator não encontrada")
except Exception as e:
    print(f"   ❌ Erro: {e}")

# Teste 4: Verificar estrutura dos arquivos
print("\n4️⃣ Verificando estrutura dos arquivos...")
files_to_check = [
    "processors/response_processor.py",
    "utils/base_classes.py", 
    "orchestrators/orchestrator_manager.py",
    "orchestrators/session_orchestrator.py"
]

for file in files_to_check:
    full_path = os.path.join(os.path.dirname(__file__), file)
    if os.path.exists(full_path):
        size = os.path.getsize(full_path)
        print(f"   ✅ {file} ({size} bytes)")
    else:
        print(f"   ❌ {file} não encontrado")

print("\n✅ Teste concluído!")
print("\n📝 Resumo das correções aplicadas:")
print("1. Adicionada função generate_api_fallback_response no response_processor.py")
print("2. Criada classe BaseModule com todos os atributos necessários no base_classes.py")
print("3. Adicionado método async process_query no SessionOrchestrator")
print("4. Corrigido loop circular no OrchestratorManager (integration_manager sempre retorna None)")
print("\n⚠️ Nota: Para testar completamente, instale as dependências do Flask.")