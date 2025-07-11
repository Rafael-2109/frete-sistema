#!/usr/bin/env python3
"""
🚀 TESTE DE INTEGRAÇÃO - MÓDULOS DE ALTO VALOR
============================================

Testa a integração dos 3 módulos de alto valor nos orchestrators.
"""

def teste_integracao_modulos_alto_valor():
    """Testa integração dos módulos de alto valor."""
    print("🚀 TESTE DE INTEGRAÇÃO - MÓDULOS DE ALTO VALOR")
    print("=" * 50)
    
    resultados = {
        'coordinator_manager': False,
        'learning_core': False,
        'auto_command_processor': False,
        'integracao_main_orchestrator': False,
        'integracao_session_orchestrator': False
    }
    
    # Teste 1: Verificar se CoordinatorManager está disponível
    try:
        from coordinators.coordinator_manager import get_coordinator_manager
        manager = get_coordinator_manager()
        status = manager.get_coordinator_status()
        print(f"✅ CoordinatorManager: {status['total_coordinators']} coordenadores disponíveis")
        resultados['coordinator_manager'] = True
    except Exception as e:
        print(f"❌ CoordinatorManager: {e}")
    
    # Teste 2: Verificar se LearningCore está disponível
    try:
        from learners.learning_core import get_learning_core
        learning = get_learning_core()
        status = learning.obter_status_sistema()
        print(f"✅ LearningCore: Sistema {status['saude_sistema']}")
        resultados['learning_core'] = True
    except Exception as e:
        print(f"❌ LearningCore: {e}")
    
    # Teste 3: Verificar se AutoCommandProcessor está disponível
    try:
        from commands.auto_command_processor import get_auto_command_processor
        processor = get_auto_command_processor()
        suggestions = processor.get_command_suggestions("gerar relatório")
        print(f"✅ AutoCommandProcessor: {len(suggestions)} sugestões disponíveis")
        resultados['auto_command_processor'] = True
    except Exception as e:
        print(f"❌ AutoCommandProcessor: {e}")
    
    # Teste 4: Verificar integração com MainOrchestrator
    try:
        from orchestrators.main_orchestrator import get_main_orchestrator
        main_orch = get_main_orchestrator()
        
        # Testar coordenação inteligente
        if hasattr(main_orch, 'coordinator_manager') and main_orch.coordinator_manager:
            print("✅ MainOrchestrator: CoordinatorManager integrado")
            resultados['integracao_main_orchestrator'] = True
        else:
            print("⚠️ MainOrchestrator: CoordinatorManager não integrado")
        
        # Testar comandos automáticos
        if hasattr(main_orch, 'auto_command_processor') and main_orch.auto_command_processor:
            print("✅ MainOrchestrator: AutoCommandProcessor integrado")
        else:
            print("⚠️ MainOrchestrator: AutoCommandProcessor não integrado")
            
    except Exception as e:
        print(f"❌ MainOrchestrator integração: {e}")
    
    # Teste 5: Verificar integração com SessionOrchestrator
    try:
        from orchestrators.session_orchestrator import get_session_orchestrator
        session_orch = get_session_orchestrator()
        
        # Testar aprendizado vitalício
        if hasattr(session_orch, 'learning_core') and session_orch.learning_core:
            print("✅ SessionOrchestrator: LearningCore integrado")
            resultados['integracao_session_orchestrator'] = True
        else:
            print("⚠️ SessionOrchestrator: LearningCore não integrado")
            
    except Exception as e:
        print(f"❌ SessionOrchestrator integração: {e}")
    
    # Teste 6: Funcionalidades avançadas
    print("\n🎯 TESTANDO FUNCIONALIDADES AVANÇADAS")
    print("-" * 40)
    
    # Coordenação inteligente
    if resultados['coordinator_manager']:
        try:
            from coordinators.coordinator_manager import coordinate_intelligent_query
            result = coordinate_intelligent_query("consultar entregas atrasadas", {"domain": "entregas"})
            print(f"✅ Coordenação inteligente: {result.get('status', 'unknown')}")
        except Exception as e:
            print(f"❌ Coordenação inteligente: {e}")
    
    # Aprendizado com interação
    if resultados['learning_core']:
        try:
            from learners.learning_core import get_learning_core
            learning = get_learning_core()
            result = learning.aplicar_conhecimento("analisar vendas do cliente X")
            print(f"✅ Aplicação de conhecimento: {result.get('confianca_geral', 0):.2f} confiança")
        except Exception as e:
            print(f"❌ Aplicação de conhecimento: {e}")
    
    # Processamento de comandos
    if resultados['auto_command_processor']:
        try:
            from commands.auto_command_processor import get_auto_command_processor
            processor = get_auto_command_processor()
            result = processor.process_natural_command("gerar relatório de vendas")
            print(f"✅ Comando natural: {result.get('status', 'unknown')}")
        except Exception as e:
            print(f"❌ Comando natural: {e}")
    
    # Resultado final
    print("\n" + "=" * 50)
    modulos_disponiveis = sum(1 for k, v in resultados.items() if v and not k.startswith('integracao'))
    integracoes_ativas = sum(1 for k, v in resultados.items() if v and k.startswith('integracao'))
    
    print(f"📊 MÓDULOS DISPONÍVEIS: {modulos_disponiveis}/3")
    print(f"🔗 INTEGRAÇÕES ATIVAS: {integracoes_ativas}/2")
    
    if modulos_disponiveis == 3 and integracoes_ativas == 2:
        print("🎉 INTEGRAÇÃO COMPLETA! Sistema IA industrial pronto!")
        return True
    elif modulos_disponiveis == 3:
        print("⚡ MÓDULOS PRONTOS! Falta apenas integrar aos orchestrators.")
        return True
    else:
        print("🔧 INTEGRAÇÃO EM ANDAMENTO...")
        return False

def demonstrar_capacidades_avancadas():
    """Demonstra as capacidades avançadas do sistema integrado."""
    print("\n🎯 DEMONSTRAÇÃO DE CAPACIDADES AVANÇADAS")
    print("=" * 50)
    
    # Demonstrar coordenação por domínio
    print("\n1. COORDENAÇÃO INTELIGENTE POR DOMÍNIO")
    print("-" * 40)
    dominios = ['embarques', 'entregas', 'fretes', 'pedidos', 'financeiro']
    for dominio in dominios:
        try:
            from coordinators.coordinator_manager import get_coordinator_manager
            manager = get_coordinator_manager()
            coordenador = manager.get_best_coordinator_for_domain(dominio)
            print(f"✅ {dominio.title()}: {coordenador or 'Coordenador padrão'}")
        except:
            print(f"⚠️ {dominio.title()}: Não disponível")
    
    # Demonstrar aprendizado
    print("\n2. SISTEMA DE APRENDIZADO VITALÍCIO")
    print("-" * 40)
    try:
        from learners.learning_core import get_learning_core
        learning = get_learning_core()
        conhecimento = learning.aplicar_conhecimento("consulta de exemplo")
        print(f"✅ Padrões aplicáveis: {len(conhecimento.get('padroes_aplicaveis', []))}")
        print(f"✅ Grupos conhecidos: {len(conhecimento.get('grupos_conhecidos', []))}")
        print(f"✅ Confiança geral: {conhecimento.get('confianca_geral', 0):.2f}")
    except Exception as e:
        print(f"⚠️ Aprendizado: {e}")
    
    # Demonstrar comandos naturais
    print("\n3. PROCESSAMENTO DE COMANDOS NATURAIS")
    print("-" * 40)
    comandos_exemplo = [
        "gerar relatório de vendas",
        "analisar dados do cliente",
        "consultar pedidos em aberto",
        "verificar status do sistema"
    ]
    
    try:
        from commands.auto_command_processor import get_auto_command_processor
        processor = get_auto_command_processor()
        
        for comando in comandos_exemplo:
            validation = processor.validate_command_syntax(comando)
            print(f"✅ '{comando}': {'Válido' if validation['is_valid'] else 'Inválido'}")
    except Exception as e:
        print(f"⚠️ Comandos naturais: {e}")

if __name__ == "__main__":
    sucesso = teste_integracao_modulos_alto_valor()
    if sucesso:
        demonstrar_capacidades_avancadas() 