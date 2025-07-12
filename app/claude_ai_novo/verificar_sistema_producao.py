"""
Script para verificar qual sistema Claude AI está sendo usado
"""

import os
import sys

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def verificar_configuracao():
    """Verifica a configuração do sistema"""
    print("=" * 60)
    print("🔍 VERIFICAÇÃO DO SISTEMA CLAUDE AI")
    print("=" * 60)
    
    # Verificar variável de ambiente
    use_new = os.getenv('USE_NEW_CLAUDE_SYSTEM', 'false').lower()
    print(f"\n📌 USE_NEW_CLAUDE_SYSTEM = '{use_new}'")
    
    if use_new == 'true':
        print("✅ Sistema NOVO está configurado para ser usado")
        print("   → app.claude_ai_novo")
        print("   → OrchestratorManager")
    else:
        print("✅ Sistema ANTIGO está configurado para ser usado (padrão)")
        print("   → app.claude_ai")
        print("   → ClaudeRealIntegration")
    
    # Testar importação
    print("\n🧪 Testando importação do sistema configurado...")
    
    try:
        from app.claude_transition import get_transition_manager
        manager = get_transition_manager()
        
        print(f"✅ Sistema ativo: {manager.sistema_ativo}")
        
        # Verificar qual classe foi carregada
        if manager.claude:
            print(f"✅ Classe carregada: {manager.claude.__class__.__name__}")
            print(f"✅ Módulo: {manager.claude.__class__.__module__}")
        else:
            print("❌ Nenhum sistema foi carregado")
            
    except Exception as e:
        print(f"❌ Erro ao testar: {e}")
        import traceback
        traceback.print_exc()

def verificar_loop_no_sistema():
    """Verifica onde o loop pode estar acontecendo"""
    print("\n" + "=" * 60)
    print("🔄 VERIFICAÇÃO DO LOOP INFINITO")
    print("=" * 60)
    
    use_new = os.getenv('USE_NEW_CLAUDE_SYSTEM', 'false').lower()
    
    if use_new == 'true':
        print("\n⚠️  SISTEMA NOVO ATIVO - Loop pode estar em:")
        print("   1. app/claude_ai_novo/orchestrators/session_orchestrator.py")
        print("   2. app/claude_ai_novo/integration/integration_manager.py")
        print("\n💡 SOLUÇÃO: Aplicar correções no sistema NOVO")
        print("   → As correções no sistema antigo NÃO resolverão o problema")
    else:
        print("\n⚠️  SISTEMA ANTIGO ATIVO - Loop pode estar em:")
        print("   1. app/claude_ai/claude_real_integration.py")
        print("   2. app/claude_ai/enhanced_claude_integration.py")
        print("\n💡 SOLUÇÃO: As correções já aplicadas devem funcionar")

def main():
    """Executa todas as verificações"""
    verificar_configuracao()
    verificar_loop_no_sistema()
    
    print("\n" + "=" * 60)
    print("📋 RESUMO")
    print("=" * 60)
    
    use_new = os.getenv('USE_NEW_CLAUDE_SYSTEM', 'false').lower()
    
    if use_new == 'true':
        print("\n🚨 ATENÇÃO: Sistema NOVO está ativo!")
        print("   → Correções devem ser aplicadas em app/claude_ai_novo/")
        print("   → Loop está no SessionOrchestrator do sistema novo")
    else:
        print("\n✅ Sistema ANTIGO está ativo")
        print("   → Correções já aplicadas devem funcionar")
        print("   → Loop foi corrigido no enhanced_claude_integration.py")

if __name__ == "__main__":
    # Simular diferentes valores da variável
    print("\n🧪 TESTE 1: Sem variável definida (padrão)")
    os.environ.pop('USE_NEW_CLAUDE_SYSTEM', None)
    main()
    
    print("\n\n🧪 TESTE 2: Com USE_NEW_CLAUDE_SYSTEM=true")
    os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'true'
    main()
    
    print("\n\n🧪 TESTE 3: Com USE_NEW_CLAUDE_SYSTEM=false")
    os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'false'
    main() 