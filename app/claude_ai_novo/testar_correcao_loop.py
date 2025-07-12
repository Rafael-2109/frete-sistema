#!/usr/bin/env python3
"""
🧪 TESTAR CORREÇÃO DO LOOP INFINITO
===================================

Verifica se o sistema não trava mais durante a inicialização.
"""

import os
import sys
import time
import threading
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

# Configurar variáveis de ambiente
os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'true'

def testar_inicializacao():
    """Testa se a inicialização funciona sem travar"""
    print("\n🧪 TESTANDO CORREÇÃO DO LOOP INFINITO\n")
    
    # Flag para detectar travamento
    travou = [False]
    resultado = [None]
    
    def inicializar_sistema():
        """Função que tenta inicializar o sistema"""
        try:
            print("1️⃣ Importando IntegrationManager...")
            from app.claude_ai_novo.integration.integration_manager import get_integration_manager
            print("   ✅ Import OK")
            
            print("\n2️⃣ Criando instância do IntegrationManager...")
            start_time = time.time()
            manager = get_integration_manager()
            end_time = time.time()
            print(f"   ✅ Instância criada em {end_time - start_time:.2f}s")
            
            print("\n3️⃣ Verificando status...")
            status = manager.get_system_status()
            print(f"   ✅ Status obtido: orchestrator_loaded={status.get('orchestrator_loaded', False)}")
            
            print("\n4️⃣ Testando lazy loading do orchestrator...")
            # Isso deve carregar o orchestrator sob demanda
            manager._ensure_orchestrator_loaded()
            print(f"   ✅ Orchestrator carregado: {manager.orchestrator_manager is not None}")
            
            resultado[0] = "sucesso"
            
        except Exception as e:
            print(f"\n❌ Erro durante inicialização: {e}")
            resultado[0] = f"erro: {e}"
    
    # Criar thread para testar
    thread = threading.Thread(target=inicializar_sistema)
    thread.daemon = True
    
    print("🚀 Iniciando teste de inicialização...")
    print("   (Se travar por mais de 5 segundos, há problema)\n")
    
    # Iniciar thread
    thread.start()
    
    # Aguardar no máximo 5 segundos
    thread.join(timeout=5.0)
    
    # Verificar resultado
    if thread.is_alive():
        travou[0] = True
        print("\n❌ SISTEMA TRAVOU! Thread ainda está executando após 5 segundos")
        print("   O loop infinito ainda existe!")
        return False
    else:
        print("\n✅ SISTEMA NÃO TRAVOU!")
        
        if resultado[0] == "sucesso":
            print("\n📊 RESULTADO DO TESTE:")
            print("   ✅ IntegrationManager inicializado sem travar")
            print("   ✅ Lazy loading funcionando corretamente")
            print("   ✅ Orchestrator carregado sob demanda")
            print("   ✅ Sem loops infinitos detectados")
            
            print("\n🎉 CORREÇÃO FUNCIONOU PERFEITAMENTE!")
            return True
        else:
            print(f"\n⚠️ Inicialização completou mas com erro: {resultado[0]}")
            return False

def testar_fluxo_completo():
    """Testa o fluxo completo de uma query"""
    print("\n\n5️⃣ TESTANDO FLUXO COMPLETO DE QUERY:")
    
    try:
        from app.claude_transition import processar_consulta_transicao
        
        print("   Processando query de teste...")
        start_time = time.time()
        
        # Usar timeout para evitar travamento
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Query travou por mais de 10 segundos")
        
        # Configurar timeout (apenas em sistemas Unix)
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)  # 10 segundos de timeout
        
        resultado = processar_consulta_transicao("teste rápido")
        
        # Cancelar alarm se configurado
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)
        
        end_time = time.time()
        
        print(f"   ✅ Query processada em {end_time - start_time:.2f}s")
        print(f"   ✅ Resposta: {str(resultado)[:100]}...")
        
        return True
        
    except TimeoutError:
        print("   ❌ Query travou (timeout de 10 segundos)")
        return False
    except Exception as e:
        print(f"   ❌ Erro ao processar query: {e}")
        return False

if __name__ == "__main__":
    # Teste 1: Inicialização sem travamento
    sucesso_init = testar_inicializacao()
    
    # Teste 2: Fluxo completo (apenas se inicialização passou)
    if sucesso_init:
        sucesso_fluxo = testar_fluxo_completo()
        
        if sucesso_fluxo:
            print("\n\n✅ TODOS OS TESTES PASSARAM!")
            print("O sistema está funcionando sem loops infinitos!")
        else:
            print("\n\n⚠️ Inicialização OK mas fluxo completo com problemas")
    else:
        print("\n\n❌ CORREÇÃO NECESSITA MAIS AJUSTES")
        print("O sistema ainda está travando durante a inicialização") 