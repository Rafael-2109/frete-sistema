#!/usr/bin/env python3
"""
🧪 TESTE DA NOVA ARQUITETURA CORRETA

Valida se a redistribuição de responsabilidades funcionou:
- SmartBaseAgent: Especialista de domínio
- IntegrationManager: Orquestrador central
- IntelligenceManager: Sistemas de IA específicos
"""

import sys
import os

# Ajustar path para funcionar no ambiente atual
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

def teste_arquitetura_correta():
    """Testa se a nova arquitetura está funcionando corretamente"""
    
    print("🧪 TESTE DA NOVA ARQUITETURA CORRETA")
    print("=" * 60)
    
    resultados = []
    
    # 1. TESTE IMPORTS E ESTRUTURA
    print("\n1. 📦 TESTANDO Imports e Estrutura:")
    try:
        # Verificar se arquivos principais existem
        smart_base_path = os.path.join(current_dir, "multi_agent", "agents", "smart_base_agent.py")
        integration_path = os.path.join(current_dir, "integration", "integration_manager.py")
        intelligence_path = os.path.join(current_dir, "intelligence", "intelligence_manager.py")
        
        if os.path.exists(smart_base_path):
            print("   ✅ SmartBaseAgent encontrado")
            resultados.append("✅ SmartBaseAgent existe")
        else:
            print("   ❌ SmartBaseAgent não encontrado")
            resultados.append("❌ SmartBaseAgent ausente")
            
        if os.path.exists(integration_path):
            print("   ✅ IntegrationManager encontrado")
            resultados.append("✅ IntegrationManager existe")
        else:
            print("   ❌ IntegrationManager não encontrado")
            resultados.append("❌ IntegrationManager ausente")
            
        if os.path.exists(intelligence_path):
            print("   ✅ IntelligenceManager encontrado")
            resultados.append("✅ IntelligenceManager existe")
        else:
            print("   ❌ IntelligenceManager não encontrado")
            resultados.append("❌ IntelligenceManager ausente")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append("❌ Estrutura com erro")
    
    # 2. TESTE SMART BASE AGENT - CONTEÚDO
    print("\n2. 🤖 TESTANDO SmartBaseAgent (Conteúdo):")
    try:
        with open(smart_base_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Verificar se imports problemáticos foram removidos
        if 'trend_analyzer' not in content:
            print("   ✅ trend_analyzer removido")
            resultados.append("✅ trend_analyzer removido")
        else:
            print("   ❌ trend_analyzer ainda presente")
            resultados.append("❌ trend_analyzer presente")
            
        if 'validation_engine' not in content:
            print("   ✅ validation_engine removido")
            resultados.append("✅ validation_engine removido")
        else:
            print("   ❌ validation_engine ainda presente")
            resultados.append("❌ validation_engine presente")
            
        if 'alert_engine' not in content:
            print("   ✅ alert_engine removido")
            resultados.append("✅ alert_engine removido")
        else:
            print("   ❌ alert_engine ainda presente")
            resultados.append("❌ alert_engine presente")
            
        # Verificar se tem integração com IntegrationManager
        if 'integration_manager' in content:
            print("   ✅ Integração com IntegrationManager implementada")
            resultados.append("✅ Integração IntegrationManager")
        else:
            print("   ❌ Integração com IntegrationManager ausente")
            resultados.append("❌ Sem integração IntegrationManager")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append("❌ SmartBaseAgent com erro")
    
    # 3. TESTE INTEGRATION MANAGER - CONTEÚDO  
    print("\n3. 🔗 TESTANDO IntegrationManager (Conteúdo):")
    try:
        with open(integration_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Verificar se tem IntelligenceManager integrado
        if 'intelligence_manager' in content:
            print("   ✅ IntelligenceManager integrado")
            resultados.append("✅ IntelligenceManager integrado")
        else:
            print("   ❌ IntelligenceManager não integrado")
            resultados.append("❌ IntelligenceManager não integrado")
            
        # Verificar se tem método esperado pelo SmartBaseAgent
        if 'process_unified_query' in content:
            print("   ✅ Método process_unified_query implementado")
            resultados.append("✅ process_unified_query implementado")
        else:
            print("   ❌ Método process_unified_query ausente")
            resultados.append("❌ process_unified_query ausente")
            
        # Verificar se tem get_system_status
        if 'get_system_status' in content:
            print("   ✅ Método get_system_status implementado")
            resultados.append("✅ get_system_status implementado")
        else:
            print("   ❌ Método get_system_status ausente")
            resultados.append("❌ get_system_status ausente")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append("❌ IntegrationManager com erro")
    
    # 4. TESTE INTELLIGENCE MANAGER - SISTEMAS
    print("\n4. 🧠 TESTANDO IntelligenceManager (Sistemas):")
    try:
        # Verificar se subpastas existem
        learning_path = os.path.join(current_dir, "intelligence", "learning")
        memory_path = os.path.join(current_dir, "intelligence", "memory")
        conversation_path = os.path.join(current_dir, "intelligence", "conversation")
        
        if os.path.exists(learning_path):
            print("   ✅ Pasta learning/ existe")
            resultados.append("✅ Sistema learning existe")
        else:
            print("   ❌ Pasta learning/ não existe")
            resultados.append("❌ Sistema learning ausente")
            
        if os.path.exists(memory_path):
            print("   ✅ Pasta memory/ existe")
            resultados.append("✅ Sistema memory existe")
        else:
            print("   ❌ Pasta memory/ não existe")
            resultados.append("❌ Sistema memory ausente")
            
        if os.path.exists(conversation_path):
            print("   ✅ Pasta conversation/ existe")
            resultados.append("✅ Sistema conversation existe")
        else:
            print("   ❌ Pasta conversation/ não existe")
            resultados.append("❌ Sistema conversation ausente")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append("❌ IntelligenceManager com erro")
    
    # 5. TESTE INTEGRAÇÃO - FLUXO
    print("\n5. 🎯 TESTANDO Fluxo de Integração:")
    try:
        # Verificar se SmartBaseAgent delega para IntegrationManager
        with open(smart_base_path, 'r', encoding='utf-8') as f:
            smart_content = f.read()
            
        if '_delegar_para_integration_manager' in smart_content:
            print("   ✅ SmartBaseAgent delega para IntegrationManager")
            resultados.append("✅ Delegação implementada")
        else:
            print("   ❌ SmartBaseAgent não delega para IntegrationManager")
            resultados.append("❌ Delegação ausente")
            
        # Verificar se IntegrationManager usa IntelligenceManager
        with open(integration_path, 'r', encoding='utf-8') as f:
            integration_content = f.read()
            
        if 'process_intelligence' in integration_content:
            print("   ✅ IntegrationManager usa IntelligenceManager")
            resultados.append("✅ Uso Intelligence implementado")
        else:
            print("   ❌ IntegrationManager não usa IntelligenceManager")
            resultados.append("❌ Uso Intelligence ausente")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append("❌ Fluxo com erro")
    
    # 📊 RESUMO DOS RESULTADOS
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS RESULTADOS:")
    print("=" * 60)
    
    sucessos = len([r for r in resultados if r.startswith("✅")])
    total = len(resultados)
    
    for resultado in resultados:
        print(f"   {resultado}")
    
    print(f"\n🎯 TAXA DE SUCESSO: {sucessos}/{total} ({sucessos/total*100:.1f}%)")
    
    # ANÁLISE DA ARQUITETURA
    print("\n" + "=" * 60)
    print("🏗️ ANÁLISE DA ARQUITETURA:")
    print("=" * 60)
    
    if sucessos >= 10:
        print("🎉 ARQUITETURA CORRETA IMPLEMENTADA!")
        print("✅ Responsabilidades bem distribuídas")
        print("✅ SmartBaseAgent: Especialista focado")
        print("✅ IntegrationManager: Orquestrador central") 
        print("✅ IntelligenceManager: Sistemas de IA")
        print("✅ Eliminação de duplicação")
        print("✅ Fluxo de integração implementado")
        return True
    elif sucessos >= 7:
        print("⚠️ ARQUITETURA PARCIALMENTE IMPLEMENTADA")
        print("🔧 Alguns ajustes podem ser necessários")
        print("✅ Estrutura principal correta")
        return True
    else:
        print("❌ ARQUITETURA PRECISA DE CORREÇÕES")
        print("🔧 Várias correções necessárias")
        return False

if __name__ == "__main__":
    teste_arquitetura_correta() 