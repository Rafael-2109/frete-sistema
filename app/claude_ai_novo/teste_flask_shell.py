#!/usr/bin/env python3
"""
🧪 TESTE FLASK SHELL: Sistema Novo Claude AI
============================================

Execute este script no Flask shell para testar o sistema novo.

Comandos:
flask shell
>>> exec(open('app/claude_ai_novo/teste_flask_shell.py').read())
"""

def testar_sistema_novo_completo():
    """Executa teste completo do sistema novo dentro do Flask"""
    print("🧪 TESTE COMPLETO SISTEMA NOVO - Flask Shell")
    print("=" * 50)
    
    resultados = {}
    
    # Teste 1: Diagnóstico básico
    print("\n📋 1. DIAGNÓSTICO BÁSICO")
    try:
        from app.claude_transition import get_claude_transition
        transition = get_claude_transition()
        print(f"✅ Sistema ativo: {transition.sistema_ativo}")
        resultados['diagnostico_basico'] = True
    except Exception as e:
        print(f"❌ Erro no diagnóstico: {e}")
        resultados['diagnostico_basico'] = False
    
    # Teste 2: Forçar sistema novo
    print("\n🚀 2. FORÇAR SISTEMA NOVO")
    try:
        diagnostico = transition.forcar_sistema_novo()
        print(f"✅ Forçado com sucesso: {diagnostico.get('forced_activation', False)}")
        print(f"📊 Sistema ativo agora: {transition.sistema_ativo}")
        resultados['forcar_sistema'] = diagnostico.get('forced_activation', False)
    except Exception as e:
        print(f"❌ Erro ao forçar: {e}")
        resultados['forcar_sistema'] = False
    
    # Teste 3: Componentes individuais
    print("\n🧩 3. COMPONENTES INDIVIDUAIS")
    componentes = [
        ('Learning Core', 'app.claude_ai_novo.learners.learning_core', 'get_lifelong_learning'),
        ('Security Guard', 'app.claude_ai_novo.security.security_guard', 'get_security_guard'),
        ('Orchestrators', 'app.claude_ai_novo.orchestrators.orchestrator_manager', 'get_orchestrator_manager'),
        ('Integration', 'app.claude_ai_novo.integration.external_api_integration', 'get_claude_integration'),
    ]
    
    componentes_ok = 0
    for nome, modulo, funcao in componentes:
        try:
            mod = __import__(modulo, fromlist=[funcao])
            func = getattr(mod, funcao)
            instance = func()
            print(f"✅ {nome}: {type(instance).__name__}")
            componentes_ok += 1
        except Exception as e:
            print(f"❌ {nome}: {str(e)[:50]}...")
    
    resultados['componentes'] = f"{componentes_ok}/{len(componentes)}"
    
    # Teste 4: Funcionalidades básicas
    print("\n⚡ 4. FUNCIONALIDADES BÁSICAS")
    func_ok = 0
    total_func = 3
    
    # Learning Core
    try:
        from app.claude_ai_novo.learners.learning_core import get_lifelong_learning
        learning = get_lifelong_learning()
        conhecimento = learning.aplicar_conhecimento("teste")
        print(f"✅ Learning: confiança {conhecimento.get('confianca_geral', 0)}")
        func_ok += 1
    except Exception as e:
        print(f"❌ Learning: {str(e)[:50]}...")
    
    # Integration
    try:
        from app.claude_ai_novo.integration.external_api_integration import get_claude_integration
        integration = get_claude_integration()
        status = integration.get_system_status()
        print(f"✅ Integration: pronto {status.get('system_ready', 'N/A')}")
        func_ok += 1
    except Exception as e:
        print(f"❌ Integration: {str(e)[:50]}...")
    
    # Consulta teste
    try:
        from app.claude_transition import processar_consulta_transicao
        resultado = processar_consulta_transicao("teste", {"user_id": 1})
        sem_erro = "No module named" not in resultado
        print(f"✅ Consulta: {len(resultado)} chars, sem erro: {sem_erro}")
        if sem_erro:
            func_ok += 1
    except Exception as e:
        print(f"❌ Consulta: {str(e)[:50]}...")
    
    resultados['funcionalidades'] = f"{func_ok}/{total_func}"
    
    # Relatório final
    print("\n" + "=" * 50)
    print("📊 RELATÓRIO FINAL")
    print("=" * 50)
    
    for teste, resultado in resultados.items():
        print(f"  {teste}: {resultado}")
    
    # Calcular score geral
    score = 0
    if resultados['diagnostico_basico']:
        score += 25
    if resultados['forcar_sistema']:
        score += 25
    
    comp_num, comp_total = map(int, resultados['componentes'].split('/'))
    score += (comp_num / comp_total) * 25
    
    func_num, func_total = map(int, resultados['funcionalidades'].split('/'))
    score += (func_num / func_total) * 25
    
    print(f"\n🎯 SCORE GERAL: {score:.1f}%")
    
    if score >= 90:
        print("🎉 SISTEMA NOVO TOTALMENTE FUNCIONAL!")
        print("✅ Pronto para ativação em produção")
        print("\n💡 PARA ATIVAR:")
        print("   1. Editar app/claude_transition.py linha 17")
        print("   2. Alterar: self.usar_sistema_novo = True")
        print("   3. Fazer deploy/restart")
        
    elif score >= 70:
        print("⚡ SISTEMA MAJORITARIAMENTE FUNCIONAL")
        print("🔧 Algumas correções necessárias")
        print("\n💡 PRÓXIMOS PASSOS:")
        print("   1. Corrigir problemas identificados acima")
        print("   2. Executar teste novamente")
        
    else:
        print("❌ SISTEMA COM PROBLEMAS CRÍTICOS")
        print("🔧 Correções necessárias antes da ativação")
        print("\n💡 FOCAR EM:")
        print("   1. Resolver erros de componentes")
        print("   2. Verificar configurações")
        print("   3. Checar contexto Flask")
    
    return score >= 90

# Executar automaticamente
if __name__ == "__main__":
    testar_sistema_novo_completo()
else:
    # Se importado, executar automaticamente
    print("🧪 Executando teste automático...")
    testar_sistema_novo_completo() 