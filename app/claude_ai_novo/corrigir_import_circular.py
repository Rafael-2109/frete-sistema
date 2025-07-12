#!/usr/bin/env python3
"""
🔧 CORRIGIR IMPORT CIRCULAR
===========================

O problema: orchestrator_manager.py importa get_integration_manager
e integration_manager.py importa get_orchestrator_manager,
criando um loop circular durante a importação.

Solução: Remover o import desnecessário do orchestrator_manager.py
já que ele tem lazy loading via property.
"""

import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def corrigir_imports():
    """Corrige os imports circulares"""
    
    print("🔧 CORRIGINDO IMPORTS CIRCULARES\n")
    
    # Arquivo a corrigir
    file_path = Path(__file__).parent / "orchestrators" / "orchestrator_manager.py"
    
    # Ler arquivo
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Procurar e remover a linha problemática
    problemas_encontrados = []
    lines_corrigidas = []
    
    for i, line in enumerate(lines):
        # Linha 117: from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        if "from app.claude_ai_novo.integration.integration_manager import get_integration_manager" in line:
            problemas_encontrados.append(f"Linha {i+1}: {line.strip()}")
            # Comentar a linha em vez de removê-la
            lines_corrigidas.append(f"# {line.strip()} # REMOVIDO: Import circular\n")
        else:
            lines_corrigidas.append(line)
    
    if problemas_encontrados:
        print("❌ PROBLEMAS ENCONTRADOS:")
        for p in problemas_encontrados:
            print(f"   {p}")
        
        # Salvar arquivo corrigido
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines_corrigidas)
        
        print("\n✅ Import circular removido!")
        
        # Verificar se o property integration_manager existe
        content = ''.join(lines_corrigidas)
        if "@property" in content and "integration_manager" in content:
            print("✅ Property integration_manager já existe (lazy loading)")
            print("   O import será feito dentro do property quando necessário")
        
        # Verificar outros possíveis imports circulares
        print("\n🔍 Verificando outros possíveis imports circulares...")
        
        # Verificar se session_orchestrator importa integration_manager
        session_path = Path(__file__).parent / "orchestrators" / "session_orchestrator.py"
        
        with open(session_path, 'r', encoding='utf-8') as f:
            session_content = f.read()
        
        if "from app.claude_ai_novo.integration" in session_content:
            print("\n⚠️ SessionOrchestrator também importa IntegrationManager")
            
            # Verificar se é dentro de property (lazy loading)
            if "@property" in session_content and "def integration_manager" in session_content:
                print("   ✅ OK: Import está dentro de property (lazy loading)")
            else:
                print("   ❌ PROBLEMA: Import pode causar loop circular")
        
        print("\n✅ CORREÇÃO APLICADA COM SUCESSO!")
        print("\nO que foi feito:")
        print("1. Removido import circular do orchestrator_manager.py")
        print("2. O orchestrator usa lazy loading via property")
        print("3. Isso quebra o loop circular de importação")
        
        print("\n📝 PRÓXIMOS PASSOS:")
        print("1. Execute o teste novamente")
        print("2. O sistema não deve mais travar")
        
    else:
        print("✅ Arquivo já está corrigido ou import não encontrado")
        
        # Verificar se o import está em outro lugar
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "get_integration_manager" in content:
            print("\n⚠️ get_integration_manager ainda é referenciado no arquivo")
            print("   Mas o import direto foi removido")

if __name__ == "__main__":
    corrigir_imports() 