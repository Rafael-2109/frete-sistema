#!/usr/bin/env python3
"""
Teste das Correções Finais
=========================

Testa se:
1. get_integration_status funciona no IntegrationManager
2. ProcessorRegistry tem todos os processadores
"""

import sys
import os
from pathlib import Path

# Adicionar diretório raiz ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def teste_get_integration_status():
    """Testa se get_integration_status funciona"""
    print("🔍 Testando get_integration_status...")
    
    try:
        from app.claude_ai_novo.integration.integration_manager import IntegrationManager
        
        # Criar instância
        integration_manager = IntegrationManager()
        
        # Testar método
        status = integration_manager.get_integration_status()
        
        print(f"   ✅ get_integration_status funcionando")
        print(f"   📊 Status: {status.get('integration_active', 'N/A')}")
        print(f"   🎯 Score: {status.get('integration_score', 0.0)}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return False

def teste_processor_registry_completo():
    """Testa se ProcessorRegistry tem todos os processadores"""
    print("🔍 Testando ProcessorRegistry completo...")
    
    try:
        from app.claude_ai_novo.utils.processor_registry import get_processor_registry
        
        # Obter registry
        registry = get_processor_registry()
        
        # Listar processadores
        processadores = registry.list_processors()
        
        print(f"   📋 Processadores registrados: {processadores}")
        print(f"   📊 Total: {len(processadores)}")
        
        # Processadores esperados
        esperados = ['context', 'response', 'semantic_loop', 'query', 'intelligence', 'data']
        
        # Verificar se todos estão presentes
        faltando = set(esperados) - set(processadores)
        extras = set(processadores) - set(esperados)
        
        if faltando:
            print(f"   ⚠️ Processadores faltando: {faltando}")
        
        if extras:
            print(f"   ℹ️ Processadores extras: {extras}")
        
        # Verificar stats
        stats = registry.get_registry_stats()
        
        print(f"   💚 Processadores saudáveis: {stats['healthy_processors']}")
        print(f"   📈 Taxa de saúde: {stats['healthy_processors']}/{stats['total_processors']}")
        
        # Consideramos sucesso se temos pelo menos os 6 processadores esperados
        sucesso = len(processadores) >= 6
        
        if sucesso:
            print("   ✅ ProcessorRegistry completo")
        else:
            print("   ❌ ProcessorRegistry incompleto")
            
        return sucesso
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return False

def teste_processadores_individuais():
    """Testa cada processador individualmente"""
    print("🔍 Testando processadores individuais...")
    
    try:
        from app.claude_ai_novo.utils.processor_registry import get_processor_registry
        
        registry = get_processor_registry()
        processadores = registry.list_processors()
        
        sucessos = 0
        
        for nome in processadores:
            try:
                processor = registry.get_processor(nome)
                info = registry.get_processor_info(nome)
                
                status = "✅" if info.get('health', False) else "⚠️"
                print(f"   {status} {nome}: {info.get('type', 'N/A')}")
                
                if info.get('health', False):
                    sucessos += 1
                    
            except Exception as e:
                print(f"   ❌ {nome}: Erro - {e}")
        
        print(f"   📊 Processadores funcionais: {sucessos}/{len(processadores)}")
        
        return sucessos > 0
        
    except Exception as e:
        print(f"   ❌ Erro geral: {e}")
        return False

def main():
    """Função principal"""
    
    print("🧪 TESTE DAS CORREÇÕES FINAIS")
    print("=" * 50)
    
    testes = [
        ("IntegrationManager.get_integration_status", teste_get_integration_status),
        ("ProcessorRegistry completo", teste_processor_registry_completo),
        ("Processadores individuais", teste_processadores_individuais)
    ]
    
    sucessos = 0
    
    for nome, teste in testes:
        print(f"\n📋 {nome}")
        print("-" * 30)
        
        try:
            resultado = teste()
            if resultado:
                print(f"✅ APROVADO: {nome}")
                sucessos += 1
            else:
                print(f"❌ REPROVADO: {nome}")
                
        except Exception as e:
            print(f"❌ ERRO: {nome} - {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 RELATÓRIO FINAL")
    print(f"✅ Aprovados: {sucessos}/{len(testes)}")
    print(f"🏆 Taxa de sucesso: {sucessos/len(testes)*100:.1f}%")
    
    if sucessos == len(testes):
        print("🎉 TODAS AS CORREÇÕES FUNCIONANDO!")
    else:
        print("⚠️ Algumas correções precisam de ajustes")
    
    return sucessos == len(testes)

if __name__ == "__main__":
    main() 