#!/usr/bin/env python3
"""
🔧 CORRIGIR LOOP INFINITO DE INICIALIZAÇÃO
==========================================

O problema: IntegrationManager e OrchestratorManager estão se chamando
mutuamente durante a inicialização, causando travamento.

Solução: Remover a chamada automática de _ensure_orchestrator_loaded()
do __init__ do IntegrationManager.
"""

import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def corrigir_loop():
    """Corrige o loop infinito de inicialização"""
    
    print("🔧 CORRIGINDO LOOP INFINITO DE INICIALIZAÇÃO\n")
    
    # Arquivo a corrigir
    file_path = Path(__file__).parent / "integration" / "integration_manager.py"
    
    # Ler arquivo
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar se o problema existe
    if "_ensure_orchestrator_loaded()" in content and "def __init__" in content:
        print("❌ PROBLEMA ENCONTRADO: _ensure_orchestrator_loaded() sendo chamado no __init__")
        
        # Remover a chamada automática
        old_code = """        logger.info("🔗 Integration Manager iniciado")
        
        # Inicializar orchestrator automaticamente
        self._ensure_orchestrator_loaded()"""
        
        new_code = """        logger.info("🔗 Integration Manager iniciado")
        
        # NÃO inicializar orchestrator automaticamente para evitar loop circular
        # O orchestrator será carregado sob demanda quando necessário"""
        
        if old_code in content:
            content = content.replace(old_code, new_code)
            print("✅ Removendo chamada automática de _ensure_orchestrator_loaded()")
            
            # Salvar arquivo
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Arquivo corrigido com sucesso!")
            
            # Verificar se há outras chamadas perigosas
            print("\n🔍 Verificando outras possíveis causas de loop...")
            
            # SessionOrchestrator também pode ter problema similar
            session_path = Path(__file__).parent / "orchestrators" / "session_orchestrator.py"
            
            with open(session_path, 'r', encoding='utf-8') as f:
                session_content = f.read()
            
            # Verificar se SessionOrchestrator carrega IntegrationManager no __init__
            if "get_integration_manager()" in session_content and "def __init__" in session_content:
                print("\n⚠️ SessionOrchestrator também pode estar causando loop")
                print("   Verificando se é lazy loading...")
                
                # Verificar se é property (lazy loading)
                if "@property" in session_content and "integration_manager" in session_content:
                    print("   ✅ OK: SessionOrchestrator usa lazy loading (property)")
                else:
                    print("   ❌ PROBLEMA: SessionOrchestrator carrega no __init__")
            
            print("\n✅ CORREÇÃO APLICADA COM SUCESSO!")
            print("\nO que foi feito:")
            print("1. Removida chamada automática de _ensure_orchestrator_loaded() do __init__")
            print("2. O orchestrator agora será carregado sob demanda (lazy loading)")
            print("3. Isso quebra o loop circular de inicialização")
            
            print("\n📝 PRÓXIMOS PASSOS:")
            print("1. Reinicie o servidor Flask")
            print("2. O sistema não deve mais travar na inicialização")
            print("3. O orchestrator será carregado quando necessário")
            
        else:
            print("⚠️ Código esperado não encontrado, arquivo pode já ter sido modificado")
    else:
        print("✅ Arquivo já está corrigido ou tem estrutura diferente")

if __name__ == "__main__":
    corrigir_loop() 