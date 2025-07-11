#!/usr/bin/env python3
"""
🔬 TESTE RÁPIDO: Sistema Novo Claude AI
======================================

Testa componentes específicos do sistema novo para identificar problemas.
"""

import sys
import os
import traceback

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def teste_imports_basicos():
    """Testa imports básicos do sistema novo"""
    print("📦 Testando imports básicos...")
    
    try:
        # Teste 1: Learning Core
        from app.claude_ai_novo.learners.learning_core import get_lifelong_learning
        print("✅ Learning Core importado")
        
        # Teste 2: Orchestrators
        from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
        print("✅ Orchestrator Manager importado")
        
        # Teste 3: Security Guard
        from app.claude_ai_novo.security.security_guard import get_security_guard
        print("✅ Security Guard importado")
        
        # Teste 4: Integration
        from app.claude_ai_novo.integration.external_api_integration import get_claude_integration
        print("✅ External API Integration importado")
        
        # Teste 5: Analyzers
        from app.claude_ai_novo.analyzers.analyzer_manager import get_analyzer_manager
        print("✅ Analyzer Manager importado")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro nos imports: {e}")
        traceback.print_exc()
        return False

def teste_inicializacao_componentes():
    """Testa inicialização dos componentes"""
    print("\n🚀 Testando inicialização dos componentes...")
    
    resultados = {}
    
    # Learning Core
    try:
        from app.claude_ai_novo.learners.learning_core import get_lifelong_learning
        learning = get_lifelong_learning()
        resultados['learning_core'] = f"✅ {type(learning).__name__}"
    except Exception as e:
        resultados['learning_core'] = f"❌ {e}"
    
    # Orchestrators
    try:
        from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
        orchestrator = get_orchestrator_manager()
        resultados['orchestrator'] = f"✅ {type(orchestrator).__name__}"
    except Exception as e:
        resultados['orchestrator'] = f"❌ {e}"
    
    # Security Guard
    try:
        from app.claude_ai_novo.security.security_guard import get_security_guard
        security = get_security_guard()
        resultados['security'] = f"✅ {type(security).__name__}"
    except Exception as e:
        resultados['security'] = f"❌ {e}"
    
    # Integration
    try:
        from app.claude_ai_novo.integration.external_api_integration import get_claude_integration
        integration = get_claude_integration()
        resultados['integration'] = f"✅ {type(integration).__name__}"
    except Exception as e:
        resultados['integration'] = f"❌ {e}"
    
    # Analyzers
    try:
        from app.claude_ai_novo.analyzers.analyzer_manager import get_analyzer_manager
        analyzer = get_analyzer_manager()
        resultados['analyzer'] = f"✅ {type(analyzer).__name__}"
    except Exception as e:
        resultados['analyzer'] = f"❌ {e}"
    
    # Mostrar resultados
    for componente, resultado in resultados.items():
        print(f"  {componente}: {resultado}")
    
    sucessos = sum(1 for r in resultados.values() if r.startswith('✅'))
    total = len(resultados)
    
    print(f"\n📊 Componentes funcionais: {sucessos}/{total} ({sucessos/total*100:.1f}%)")
    
    return sucessos == total

def teste_funcionalidades_basicas():
    """Testa funcionalidades básicas dos componentes"""
    print("\n⚡ Testando funcionalidades básicas...")
    
    try:
        # Learning Core - aplicar conhecimento
        from app.claude_ai_novo.learners.learning_core import get_lifelong_learning
        learning = get_lifelong_learning()
        conhecimento = learning.aplicar_conhecimento("teste")
        print(f"✅ Learning aplicou conhecimento: confiança {conhecimento.get('confianca_geral', 0)}")
        
        # Security Guard - validar entrada
        from app.claude_ai_novo.security.security_guard import get_security_guard
        security = get_security_guard()
        validacao = security.validate_input("SELECT * FROM users")
        print(f"✅ Security validou entrada: {validacao.get('allowed', 'N/A')}")
        
        # Orchestrator - status
        from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
        orchestrator = get_orchestrator_manager()
        status = orchestrator.get_system_status()
        print(f"✅ Orchestrator status: {status.get('total_orchestrators', 0)} orchestrators")
        
        # Integration - status
        from app.claude_ai_novo.integration.external_api_integration import get_claude_integration
        integration = get_claude_integration()
        int_status = integration.get_system_status()
        print(f"✅ Integration status: {int_status.get('system_ready', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro nas funcionalidades: {e}")
        traceback.print_exc()
        return False

def teste_problemas_conhecidos():
    """Testa problemas conhecidos específicos"""
    print("\n🔍 Verificando problemas conhecidos...")
    
    problemas = []
    
    # Problema 1: Módulo intelligence
    try:
        from app.claude_ai_novo.intelligence.learning_core import get_lifelong_learning
        print("❌ PROBLEMA: Tentou importar de intelligence (caminho incorreto)")
        problemas.append("Import de intelligence ainda sendo usado")
    except ImportError:
        print("✅ Import correto sendo usado (learners, não intelligence)")
    
    # Problema 2: Dependências circulares
    try:
        from app.claude_ai_novo.integration.integration_manager import IntegrationManager
        from app.claude_ai_novo.orchestrators.main_orchestrator import MainOrchestrator
        print("✅ Imports principais funcionam")
    except Exception as e:
        print(f"⚠️ Possível dependência circular: {e}")
        problemas.append("Dependência circular")
    
    # Problema 3: Configurações
    try:
        from app.claude_ai_novo.config.advanced_config import get_advanced_config_instance
        config = get_advanced_config_instance()
        print("✅ Configurações carregadas")
    except Exception as e:
        print(f"⚠️ Problema nas configurações: {e}")
        problemas.append("Configurações")
    
    if problemas:
        print(f"\n❌ Problemas identificados: {', '.join(problemas)}")
        return False
    else:
        print("\n✅ Nenhum problema conhecido detectado")
        return True

def main():
    """Executa teste rápido completo"""
    print("🔬 TESTE RÁPIDO: Sistema Novo Claude AI")
    print("=" * 50)
    
    testes = [
        ("Imports Básicos", teste_imports_basicos),
        ("Inicialização Componentes", teste_inicializacao_componentes),
        ("Funcionalidades Básicas", teste_funcionalidades_basicas),
        ("Problemas Conhecidos", teste_problemas_conhecidos)
    ]
    
    sucessos = 0
    for nome, teste_func in testes:
        print(f"\n📋 {nome}")
        print("-" * 30)
        
        if teste_func():
            sucessos += 1
            print(f"🎯 ✅ SUCESSO")
        else:
            print(f"🎯 ❌ FALHA")
    
    taxa_sucesso = sucessos / len(testes) * 100
    print(f"\n{'='*50}")
    print(f"📊 RESULTADO FINAL: {sucessos}/{len(testes)} ({taxa_sucesso:.1f}%)")
    
    if taxa_sucesso == 100:
        print("🎉 SISTEMA NOVO TOTALMENTE FUNCIONAL!")
        print("✅ Pronto para migração")
    elif taxa_sucesso >= 75:
        print("⚡ SISTEMA MAJORITARIAMENTE FUNCIONAL")
        print("🔧 Pequenos ajustes necessários")
    else:
        print("❌ SISTEMA COM PROBLEMAS CRÍTICOS")
        print("🔧 Correções necessárias antes da migração")
    
    return taxa_sucesso

if __name__ == "__main__":
    main() 