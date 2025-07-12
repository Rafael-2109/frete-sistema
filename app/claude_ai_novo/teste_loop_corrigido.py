#!/usr/bin/env python3
"""
🧪 TESTE DEFINITIVO DA CORREÇÃO DO LOOP INFINITO
================================================

Este script testa se o loop infinito entre IntegrationManager 
e OrchestratorManager foi realmente corrigido.
"""

import asyncio
import sys
import os
import time
import signal
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Timeout para evitar travamento
def timeout_handler(signum, frame):
    print("\n❌ TIMEOUT! O teste travou - loop infinito ainda existe!")
    sys.exit(1)

async def testar_loop_infinito():
    """Testa se o loop infinito foi corrigido"""
    print("🧪 TESTE DEFINITIVO DO LOOP INFINITO")
    print("=" * 50)
    print(f"Início: {datetime.now()}")
    
    # Configurar timeout de 10 segundos
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(10)
    
    try:
        # 1. Importar e criar IntegrationManager
        print("\n1️⃣ Importando IntegrationManager...")
        from app.claude_ai_novo.integration.integration_manager import IntegrationManager
        manager = IntegrationManager()
        print("✅ IntegrationManager criado")
        
        # 2. Verificar se orchestrator está carregado
        print("\n2️⃣ Verificando orchestrator...")
        print(f"   Orchestrator carregado: {manager.orchestrator_manager is not None}")
        
        # 3. Testar query simples com contador de chamadas
        print("\n3️⃣ Testando query com monitoramento de loops...")
        
        # Adicionar contador de chamadas no manager
        call_count = 0
        original_process = manager.process_unified_query
        
        async def monitored_process(query, context=None):
            nonlocal call_count
            call_count += 1
            print(f"   📞 Chamada #{call_count}: process_unified_query('{query}')")
            
            if call_count > 5:
                print("   ⚠️ ALERTA: Mais de 5 chamadas recursivas detectadas!")
                return {"error": "Loop detectado", "call_count": call_count}
            
            return await original_process(query, context)
        
        # Substituir temporariamente o método
        manager.process_unified_query = monitored_process
        
        # Executar teste
        start_time = time.time()
        result = await manager.process_unified_query("Como estão as entregas do Atacadão?")
        end_time = time.time()
        
        print(f"\n4️⃣ Resultado do teste:")
        print(f"   Total de chamadas: {call_count}")
        print(f"   Tempo de execução: {end_time - start_time:.2f}s")
        print(f"   Resultado: {result}")
        
        # Verificar se houve loop
        if call_count > 2:
            print("\n❌ FALHA: Loop infinito detectado!")
            print(f"   O método foi chamado {call_count} vezes (esperado: 1-2)")
            return False
        else:
            print("\n✅ SUCESSO: Nenhum loop infinito detectado!")
            print(f"   O método foi chamado apenas {call_count} vez(es)")
            return True
            
    except Exception as e:
        print(f"\n❌ ERRO durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cancelar timeout
        signal.alarm(0)

async def verificar_arquivos_corrigidos():
    """Verifica se os arquivos foram realmente modificados"""
    print("\n5️⃣ Verificando arquivos modificados...")
    
    files_to_check = [
        ("orchestrators/orchestrator_manager.py", "integration_operation_direct"),
        ("integration/integration_manager.py", "_from_orchestrator")
    ]
    
    all_correct = True
    
    for file_path, expected_text in files_to_check:
        full_path = f"app/claude_ai_novo/{file_path}"
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if expected_text in content:
                    print(f"   ✅ {file_path}: Correção encontrada")
                else:
                    print(f"   ❌ {file_path}: Correção NÃO encontrada")
                    all_correct = False
        else:
            print(f"   ❌ {file_path}: Arquivo não encontrado")
            all_correct = False
    
    return all_correct

async def main():
    """Executa todos os testes"""
    print("🚀 Iniciando teste definitivo do loop infinito\n")
    
    # Verificar arquivos
    files_ok = await verificar_arquivos_corrigidos()
    
    if not files_ok:
        print("\n⚠️ AVISO: Os arquivos não parecem estar corrigidos!")
        print("Execute primeiro: python app/claude_ai_novo/corrigir_loop_infinito_integration.py")
        return
    
    # Testar loop
    loop_fixed = await testar_loop_infinito()
    
    print("\n" + "=" * 50)
    print("📊 RESULTADO FINAL:")
    if loop_fixed:
        print("✅ O LOOP INFINITO FOI REALMENTE CORRIGIDO!")
        print("✅ O sistema está pronto para uso!")
    else:
        print("❌ O LOOP INFINITO AINDA EXISTE!")
        print("❌ É necessário revisar a correção!")
    print("=" * 50)

if __name__ == "__main__":
    # Para Windows, usar ProactorEventLoop
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main()) 