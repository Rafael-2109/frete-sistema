#!/usr/bin/env python3
"""
🚀 TESTE COM CONTEXTO FLASK: Sistema Novo Claude AI
===================================================

Testa o sistema novo dentro do contexto Flask adequado.
"""

import sys
import os
import traceback

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def inicializar_flask():
    """Inicializa o contexto Flask"""
    try:
        from app import create_app
        app = create_app()
        return app
    except Exception as e:
        print(f"❌ Erro ao inicializar Flask: {e}")
        return None

def teste_sistema_novo_com_flask():
    """Testa sistema novo com contexto Flask ativo"""
    app = inicializar_flask()
    if not app:
        return False
    
    with app.app_context():
        print("🚀 Testando sistema novo com contexto Flask...")
        
        resultados = {}
        
        # Teste 1: Learning Core
        try:
            from app.claude_ai_novo.learners.learning_core import get_lifelong_learning
            learning = get_lifelong_learning()
            resultados['learning_core'] = f"✅ {type(learning).__name__}"
        except Exception as e:
            resultados['learning_core'] = f"❌ {str(e)[:50]}..."
        
        # Teste 2: Orchestrators
        try:
            from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
            orchestrator = get_orchestrator_manager()
            resultados['orchestrator'] = f"✅ {type(orchestrator).__name__}"
        except Exception as e:
            resultados['orchestrator'] = f"❌ {str(e)[:50]}..."
        
        # Teste 3: Security Guard
        try:
            from app.claude_ai_novo.security.security_guard import get_security_guard
            security = get_security_guard()
            resultados['security'] = f"✅ {type(security).__name__}"
        except Exception as e:
            resultados['security'] = f"❌ {str(e)[:50]}..."
        
        # Teste 4: Integration
        try:
            from app.claude_ai_novo.integration.external_api_integration import get_claude_integration
            integration = get_claude_integration()
            resultados['integration'] = f"✅ {type(integration).__name__}"
        except Exception as e:
            resultados['integration'] = f"❌ {str(e)[:50]}..."
        
        # Teste 5: Analyzers
        try:
            from app.claude_ai_novo.analyzers.analyzer_manager import get_analyzer_manager
            analyzer = get_analyzer_manager()
            resultados['analyzer'] = f"✅ {type(analyzer).__name__}"
        except Exception as e:
            resultados['analyzer'] = f"❌ {str(e)[:50]}..."
        
        # Mostrar resultados
        print("\n📊 Resultados dos componentes:")
        for componente, resultado in resultados.items():
            print(f"  {componente}: {resultado}")
        
        sucessos = sum(1 for r in resultados.values() if r.startswith('✅'))
        total = len(resultados)
        
        print(f"\n📈 Taxa de sucesso: {sucessos}/{total} ({sucessos/total*100:.1f}%)")
        
        return sucessos, total, resultados

def teste_funcionalidades_avancadas():
    """Testa funcionalidades mais avançadas"""
    app = inicializar_flask()
    if not app:
        return False
    
    with app.app_context():
        print("\n⚡ Testando funcionalidades avançadas...")
        
        try:
            # Teste Learning Core
            from app.claude_ai_novo.learners.learning_core import get_lifelong_learning
            learning = get_lifelong_learning()
            conhecimento = learning.aplicar_conhecimento("teste")
            print(f"✅ Learning: confiança {conhecimento.get('confianca_geral', 0)}")
            
            # Teste Security Guard
            from app.claude_ai_novo.security.security_guard import get_security_guard
            security = get_security_guard()
            validacao = security.validate_input("SELECT * FROM users")
            print(f"✅ Security: validação {validacao.get('allowed', 'N/A')}")
            
            # Teste Integration
            from app.claude_ai_novo.integration.external_api_integration import get_claude_integration
            integration = get_claude_integration()
            status = integration.get_system_status()
            print(f"✅ Integration: pronto {status.get('system_ready', 'N/A')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro nas funcionalidades: {e}")
            traceback.print_exc()
            return False

def teste_transicao_completa():
    """Testa a transição completa do sistema"""
    app = inicializar_flask()
    if not app:
        return False
    
    with app.app_context():
        print("\n🔄 Testando transição completa...")
        
        try:
            # Importar interface de transição
            from app.claude_transition import get_claude_transition
            transition = get_claude_transition()
            
            print(f"📋 Sistema ativo: {transition.sistema_ativo}")
            
            # Testar mudança para sistema novo
            if transition.sistema_ativo == "antigo":
                print("🔄 Tentando alternar para sistema novo...")
                transition.usar_sistema_novo = True
                transition._inicializar_sistema_novo()
                print(f"📋 Sistema após alteração: {transition.sistema_ativo}")
            
            # Testar consulta
            from app.claude_transition import processar_consulta_transicao
            resultado = processar_consulta_transicao("Teste de transição", {"user_id": "test"})
            print(f"✅ Consulta processada: {len(resultado)} caracteres")
            
            # Verificar se contém erros conhecidos
            if "No module named" in resultado:
                print(f"❌ Erro detectado na resposta: {resultado[:100]}...")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Erro na transição: {e}")
            traceback.print_exc()
            return False

def main():
    """Executa teste completo com contexto Flask"""
    print("🚀 TESTE COM CONTEXTO FLASK: Sistema Novo Claude AI")
    print("=" * 60)
    
    # Verificar se Flask inicializa
    app = inicializar_flask()
    if not app:
        print("❌ ERRO CRÍTICO: Não foi possível inicializar Flask")
        return False
    
    print("✅ Flask inicializado com sucesso")
    
    # Executar testes
    sucessos_componentes, total_componentes, componentes = teste_sistema_novo_com_flask()
    teste_funcionalidades = teste_funcionalidades_avancadas()
    teste_transicao = teste_transicao_completa()
    
    # Análise final
    print("\n" + "=" * 60)
    print("📊 ANÁLISE FINAL:")
    print("=" * 60)
    
    taxa_componentes = sucessos_componentes / total_componentes * 100
    print(f"📦 Componentes funcionais: {sucessos_componentes}/{total_componentes} ({taxa_componentes:.1f}%)")
    print(f"⚡ Funcionalidades avançadas: {'✅' if teste_funcionalidades else '❌'}")
    print(f"🔄 Transição sistema: {'✅' if teste_transicao else '❌'}")
    
    # Identificar problemas específicos
    problemas = []
    for comp, resultado in componentes.items():
        if resultado.startswith('❌'):
            problemas.append(f"{comp}: {resultado[2:]}")
    
    if problemas:
        print(f"\n🔧 PROBLEMAS IDENTIFICADOS:")
        for problema in problemas:
            print(f"  • {problema}")
    
    # Recomendações
    print(f"\n💡 RECOMENDAÇÕES:")
    
    if taxa_componentes == 100 and teste_funcionalidades and teste_transicao:
        print("  🎉 SISTEMA TOTALMENTE FUNCIONAL!")
        print("  ✅ Pronto para migração imediata")
        print("  📝 Execute: transition.usar_sistema_novo = True")
        
    elif taxa_componentes >= 80:
        print("  ⚡ SISTEMA MAJORITARIAMENTE FUNCIONAL")
        print("  🔧 Corrigir problemas específicos identificados")
        print("  📝 Testar novamente após correções")
        
    else:
        print("  ❌ SISTEMA COM PROBLEMAS CRÍTICOS")
        print("  🔧 Necessário corrigir dependências e imports")
        print("  📝 Focar na resolução dos problemas listados")
    
    return taxa_componentes >= 80

if __name__ == "__main__":
    main() 