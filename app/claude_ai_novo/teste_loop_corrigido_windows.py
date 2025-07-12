#!/usr/bin/env python3
"""
🧪 TESTE DEFINITIVO DA CORREÇÃO DO LOOP INFINITO (Windows)
=========================================================

Este script testa se o loop infinito entre IntegrationManager 
e OrchestratorManager foi realmente corrigido.
"""

import asyncio
import sys
import os
import time
import threading
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Flag global para timeout
timeout_occurred = False

def timeout_monitor(duration=10):
    """Monitor de timeout para Windows"""
    global timeout_occurred
    time.sleep(duration)
    if not timeout_occurred:
        timeout_occurred = True
        print("\n❌ TIMEOUT! O teste travou - loop infinito ainda existe!")
        os._exit(1)

async def testar_loop_infinito():
    """Testa se o loop infinito foi corrigido"""
    print("🧪 TESTE DEFINITIVO DO LOOP INFINITO (Windows)")
    print("=" * 50)
    print(f"Início: {datetime.now()}")
    
    # Iniciar thread de timeout
    timeout_thread = threading.Thread(target=timeout_monitor, args=(10,))
    timeout_thread.daemon = True
    timeout_thread.start()
    
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
        
        # Adicionar contador de logs para detectar loops
        log_count = {"integration": 0, "orchestrator": 0}
        
        # Interceptar logs
        import logging
        
        class LogInterceptor(logging.Handler):
            def emit(self, record):
                msg = record.getMessage()
                if "🔄 INTEGRATION:" in msg:
                    log_count["integration"] += 1
                    print(f"   📊 Logs Integration: {log_count['integration']}")
                elif "📞 INTEGRATION:" in msg:
                    log_count["orchestrator"] += 1
                    print(f"   📊 Logs Orchestrator: {log_count['orchestrator']}")
                
                # Detectar loop por excesso de logs
                if log_count["integration"] > 10 or log_count["orchestrator"] > 10:
                    print("\n❌ LOOP DETECTADO! Muitos logs repetidos!")
                    os._exit(1)
        
        # Adicionar interceptor
        logger = logging.getLogger("app.claude_ai_novo")
        interceptor = LogInterceptor()
        logger.addHandler(interceptor)
        
        # Executar teste
        print("\n   🚀 Executando query de teste...")
        start_time = time.time()
        
        try:
            # Usar timeout do asyncio
            result = await asyncio.wait_for(
                manager.process_unified_query("Como estão as entregas do Atacadão?"),
                timeout=5.0
            )
            end_time = time.time()
            
            print(f"\n4️⃣ Resultado do teste:")
            print(f"   Logs Integration: {log_count['integration']}")
            print(f"   Logs Orchestrator: {log_count['orchestrator']}")
            print(f"   Tempo de execução: {end_time - start_time:.2f}s")
            print(f"   Resultado: {result}")
            
            # Verificar se houve loop baseado nos logs
            if log_count["integration"] > 5 or log_count["orchestrator"] > 5:
                print("\n❌ FALHA: Loop infinito detectado!")
                print(f"   Muitos logs repetidos detectados")
                return False
            else:
                print("\n✅ SUCESSO: Nenhum loop infinito detectado!")
                print(f"   Quantidade normal de logs")
                return True
                
        except asyncio.TimeoutError:
            print("\n❌ TIMEOUT! A query travou - possível loop infinito!")
            return False
            
    except Exception as e:
        print(f"\n❌ ERRO durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Marcar que o teste terminou
        global timeout_occurred
        timeout_occurred = True

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

async def testar_chamada_direta():
    """Testa uma chamada direta ao orchestrator"""
    print("\n6️⃣ Testando chamada direta ao orchestrator...")
    
    try:
        from app.claude_ai_novo.orchestrators import get_orchestrator_manager
        orch_manager = get_orchestrator_manager()
        
        # Testar se o orchestrator processa sem loop
        result = await asyncio.wait_for(
            orch_manager.process_query("teste direto"),
            timeout=3.0
        )
        print(f"   ✅ Orchestrator respondeu: {result}")
        return True
        
    except asyncio.TimeoutError:
        print("   ❌ Orchestrator travou!")
        return False
    except Exception as e:
        print(f"   ❌ Erro no orchestrator: {e}")
        return False

async def main():
    """Executa todos os testes"""
    print("🚀 Iniciando teste definitivo do loop infinito\n")
    
    # Verificar arquivos
    files_ok = await verificar_arquivos_corrigidos()
    
    if not files_ok:
        print("\n⚠️ AVISO: Os arquivos não parecem estar corrigidos!")
        print("Execute primeiro: python app/claude_ai_novo/corrigir_loop_infinito_integration.py")
        return
    
    # Testar orchestrator direto
    orch_ok = await testar_chamada_direta()
    
    # Testar loop
    loop_fixed = await testar_loop_infinito()
    
    print("\n" + "=" * 50)
    print("📊 RESULTADO FINAL:")
    print(f"   Arquivos corrigidos: {'✅' if files_ok else '❌'}")
    print(f"   Orchestrator OK: {'✅' if orch_ok else '❌'}")
    print(f"   Loop corrigido: {'✅' if loop_fixed else '❌'}")
    
    if files_ok and orch_ok and loop_fixed:
        print("\n✅ TUDO FUNCIONANDO! O loop infinito foi REALMENTE corrigido!")
    else:
        print("\n❌ AINDA HÁ PROBLEMAS! Revise as correções!")
    print("=" * 50)

if __name__ == "__main__":
    # Para Windows, usar ProactorEventLoop
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main()) 