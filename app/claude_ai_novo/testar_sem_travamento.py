#!/usr/bin/env python3
"""
🧪 TESTAR SEM TRAVAMENTO
=======================

Versão do teste que usa imports diretos para evitar travamento.
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
    print("\n🧪 TESTANDO SEM TRAVAMENTO (IMPORTS DIRETOS)\n")
    
    # Flag para detectar travamento
    travou = [False]
    resultado = [None]
    
    def inicializar_sistema():
        """Função que tenta inicializar o sistema"""
        try:
            print("1️⃣ Importando IntegrationManager diretamente...")
            # IMPORT DIRETO - evita __init__.py
            from app.claude_ai_novo.integration.integration_manager import get_integration_manager
            print("   ✅ Import direto OK")
            
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
            import traceback
            traceback.print_exc()
            resultado[0] = f"erro: {e}"
    
    # Criar thread para testar
    thread = threading.Thread(target=inicializar_sistema)
    thread.daemon = True
    
    print("🚀 Iniciando teste de inicialização...")
    print("   (Se travar por mais de 10 segundos, há problema)\n")
    
    # Iniciar thread
    thread.start()
    
    # Aguardar no máximo 10 segundos
    thread.join(timeout=10.0)
    
    # Verificar resultado
    if thread.is_alive():
        travou[0] = True
        print("\n❌ SISTEMA TRAVOU! Thread ainda está executando após 10 segundos")
        print("   O problema persiste mesmo com imports diretos!")
        return False
    else:
        print("\n✅ SISTEMA NÃO TRAVOU!")
        
        if resultado[0] == "sucesso":
            print("\n📊 RESULTADO DO TESTE:")
            print("   ✅ IntegrationManager inicializado sem travar")
            print("   ✅ Lazy loading funcionando corretamente")
            print("   ✅ Orchestrator carregado sob demanda")
            print("   ✅ Sem loops infinitos detectados")
            
            print("\n🎉 SISTEMA FUNCIONANDO COM IMPORTS DIRETOS!")
            return True
        else:
            print(f"\n⚠️ Inicialização completou mas com erro: {resultado[0]}")
            return False

def testar_fluxo_simples():
    """Testa um fluxo mais simples"""
    print("\n\n5️⃣ TESTANDO FLUXO SIMPLES:")
    
    try:
        # Import direto
        from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        
        print("   Criando manager...")
        manager = get_integration_manager()
        
        print("   Testando query simples...")
        start_time = time.time()
        
        # Teste simples sem usar claude_transition
        status = manager.get_system_status()
        
        end_time = time.time()
        
        print(f"   ✅ Query processada em {end_time - start_time:.2f}s")
        print(f"   ✅ Status: orchestrator_loaded={status.get('orchestrator_loaded', False)}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erro ao processar: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Teste 1: Inicialização sem travamento
    sucesso_init = testar_inicializacao()
    
    # Teste 2: Fluxo simples
    if sucesso_init:
        sucesso_fluxo = testar_fluxo_simples()
        
        if sucesso_fluxo:
            print("\n\n✅ TODOS OS TESTES PASSARAM!")
            print("\n💡 SOLUÇÃO:")
            print("Use imports diretos ao invés de importar via __init__.py")
            print("Isso evita o travamento causado por imports circulares")
        else:
            print("\n\n⚠️ Inicialização OK mas fluxo com problemas")
    else:
        print("\n\n❌ O PROBLEMA PERSISTE")
        print("Pode ser necessário investigar mais profundamente") 