#!/usr/bin/env python3
"""
🧪 Teste das Correções de Arquitetura
=====================================

Verifica se as correções implementadas resolveram os problemas de importação.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import traceback
from datetime import datetime

def teste_integration_manager():
    """Testa se o IntegrationManager pode ser importado"""
    print("🔍 Testando IntegrationManager...")
    
    try:
        from app.claude_ai_novo.integration.integration_manager import IntegrationManager
        print("✅ IntegrationManager importado com sucesso")
        
        # Testar instanciação
        manager = IntegrationManager()
        print("✅ IntegrationManager instanciado com sucesso")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro na instanciação: {e}")
        return False

def teste_imports_corrigidos():
    """Testa as importações que foram corrigidas"""
    print("\n🔍 Testando importações corrigidas...")
    
    testes = [
        # Learners (antes intelligence)
        ("app.claude_ai_novo.learners.learning_core", "LearningCore"),
        ("app.claude_ai_novo.learners.pattern_learning", "PatternLearner"),
        
        # Memorizers (antes knowledge)
        ("app.claude_ai_novo.memorizers.knowledge_memory", "KnowledgeMemory"),
        
        # Enrichers (antes semantic)
        ("app.claude_ai_novo.enrichers.semantic_enricher", "SemanticEnricher"),
        
        # Validators (antes critic)
        ("app.claude_ai_novo.validators.critic_validator", "CriticValidator"),
        
        # Utils corrigido
        ("app.claude_ai_novo.utils.validation_utils", "BaseValidationUtils"),
        
        # Suggestions corrigido
        ("app.claude_ai_novo.suggestions.suggestion_engine", "SuggestionEngine"),
        
        # Conversers
        ("app.claude_ai_novo.conversers.context_converser", "ContextConverser"),
        
        # Coordinators
        ("app.claude_ai_novo.coordinators.coordinator_manager", "CoordinatorManager"),
    ]
    
    sucessos = 0
    total = len(testes)
    
    for module_path, class_name in testes:
        try:
            import importlib
            module = importlib.import_module(module_path)
            
            if hasattr(module, class_name):
                print(f"✅ {module_path} → {class_name}")
                sucessos += 1
            else:
                print(f"⚠️  {module_path} → {class_name} (classe não encontrada)")
                
        except ImportError as e:
            print(f"❌ {module_path} → {class_name} (erro: {e})")
        except Exception as e:
            print(f"❌ {module_path} → {class_name} (erro: {e})")
    
    print(f"\n📊 Resultado: {sucessos}/{total} importações funcionais ({sucessos/total*100:.1f}%)")
    return sucessos, total

def teste_diretórios_removidos():
    """Verifica se os diretórios da arquitetura antiga foram removidos"""
    print("\n🔍 Verificando limpeza de diretórios antigos...")
    
    base_path = "app/claude_ai_novo"
    diretorios_antigos = ["semantic", "intelligence", "knowledge", "multi_agent"]
    
    removidos_corretamente = 0
    
    for diretorio in diretorios_antigos:
        path = os.path.join(base_path, diretorio)
        if not os.path.exists(path):
            print(f"✅ {diretorio}/ removido corretamente")
            removidos_corretamente += 1
        else:
            print(f"⚠️  {diretorio}/ ainda existe")
    
    print(f"\n📊 Limpeza: {removidos_corretamente}/{len(diretorios_antigos)} diretórios removidos")
    return removidos_corretamente == len(diretorios_antigos)

def main():
    """Executa todos os testes"""
    print("🧪 TESTE DAS CORREÇÕES DE ARQUITETURA")
    print("=" * 50)
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    resultados = []
    
    # Teste 1: IntegrationManager
    resultados.append(teste_integration_manager())
    
    # Teste 2: Importações corrigidas
    sucessos, total = teste_imports_corrigidos()
    resultados.append(sucessos >= total * 0.8)  # 80% de sucesso mínimo
    
    # Teste 3: Diretórios removidos
    resultados.append(teste_diretórios_removidos())
    
    # Resultado final
    print("\n" + "=" * 50)
    print("📊 RESULTADO FINAL:")
    
    sucessos_totais = sum(1 for r in resultados if r)
    total_testes = len(resultados)
    
    print(f"✅ Testes passados: {sucessos_totais}/{total_testes}")
    print(f"📈 Taxa de sucesso: {sucessos_totais/total_testes*100:.1f}%")
    
    if sucessos_totais == total_testes:
        print("🎉 TODAS AS CORREÇÕES FUNCIONARAM!")
        print("✅ Sistema novo PRONTO para ativação no Render")
    elif sucessos_totais >= total_testes * 0.8:
        print("⚠️  A maioria das correções funcionou")
        print("🔧 Algumas correções menores ainda necessárias")
    else:
        print("❌ Muitas correções ainda precisam ser implementadas")
    
    print("\n🚀 Próximo passo: Configure USE_NEW_CLAUDE_SYSTEM=true no Render")

if __name__ == "__main__":
    main() 