#!/usr/bin/env python3
"""
Script de Verificação - Qual Sistema Claude AI Está Ativo
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verificar_sistema_ativo():
    """Verifica qual sistema Claude AI está ativo"""
    print("🔍 VERIFICANDO SISTEMA CLAUDE AI ATIVO\n")
    
    # Verificar variável de ambiente
    use_new = os.getenv('USE_NEW_CLAUDE_SYSTEM', 'false')
    print(f"📋 Variável USE_NEW_CLAUDE_SYSTEM: '{use_new}'")
    
    if use_new.lower() == 'true':
        print("✅ Configurado para usar SISTEMA NOVO")
    else:
        print("❌ Configurado para usar SISTEMA ANTIGO")
    
    print("\n" + "="*60)
    
    # Tentar importar sistema de transição
    try:
        from app.claude_transition import get_claude_transition
        transition = get_claude_transition()
        
        print(f"🎯 Sistema Ativo: {transition.sistema_ativo.upper()}")
        
        if transition.sistema_ativo == "novo":
            print("✅ SUCESSO: Sistema Novo está ativo!")
            return verificar_componentes_sistema_novo()
        elif transition.sistema_ativo == "antigo":
            print("⚠️ ATENÇÃO: Sistema Antigo está ativo")
            print("💡 Para ativar sistema novo, configure USE_NEW_CLAUDE_SYSTEM=true")
            return False
        else:
            print("❌ ERRO: Nenhum sistema disponível")
            return False
            
    except Exception as e:
        print(f"❌ ERRO ao verificar transição: {e}")
        return False

def verificar_componentes_sistema_novo():
    """Verifica se componentes do sistema novo estão funcionando"""
    print("\n🔧 VERIFICANDO COMPONENTES DO SISTEMA NOVO:")
    
    componentes = [
        ('MainOrchestrator', 'app.claude_ai_novo.orchestrators.main_orchestrator', 'get_main_orchestrator'),
        ('AnalyzerManager', 'app.claude_ai_novo.analyzers.analyzer_manager', 'get_analyzer_manager'),
        ('SecurityGuard', 'app.claude_ai_novo.security.security_guard', 'get_security_guard'),
        ('ToolsManager', 'app.claude_ai_novo.tools.tools_manager', 'get_tools_manager'),
        ('IntegrationManager', 'app.claude_ai_novo.orchestrators.orchestrator_manager', 'get_orchestrator_manager'),
        ('ResponseProcessor', 'app.claude_ai_novo.processors.response_processor', 'get_responseprocessor'),
    ]
    
    success_count = 0
    total_count = len(componentes)
    
    for nome, modulo, funcao in componentes:
        try:
            mod = __import__(modulo, fromlist=[funcao])
            func = getattr(mod, funcao)
            instance = func()
            
            if instance:
                print(f"✅ {nome}: Funcionando")
                success_count += 1
            else:
                print(f"⚠️ {nome}: Disponível mas não inicializado")
                
        except ImportError as e:
            print(f"❌ {nome}: Módulo não encontrado ({str(e)[:30]}...)")
        except AttributeError as e:
            print(f"❌ {nome}: Função não encontrada ({str(e)[:30]}...)")
        except Exception as e:
            print(f"❌ {nome}: Erro na inicialização ({str(e)[:30]}...)")
    
    print(f"\n📊 RESULTADO: {success_count}/{total_count} componentes funcionando ({success_count/total_count*100:.1f}%)")
    
    if success_count >= total_count * 0.75:  # 75% ou mais
        print("🎉 SISTEMA NOVO FUNCIONANDO CORRETAMENTE!")
        return True
    elif success_count >= total_count * 0.5:  # 50% ou mais
        print("⚠️ Sistema novo parcialmente funcional")
        return True
    else:
        print("❌ Sistema novo com problemas críticos")
        return False

def testar_processamento():
    """Testa processamento de uma consulta simples"""
    print("\n🧪 TESTANDO PROCESSAMENTO DE CONSULTA:")
    
    try:
        from app.claude_transition import processar_consulta_transicao
        
        consulta_teste = "Status do sistema"
        print(f"📝 Consulta teste: '{consulta_teste}'")
        
        resultado = processar_consulta_transicao(consulta_teste)
        
        if resultado and len(resultado) > 10:
            print("✅ Processamento funcionando")
            print(f"📋 Resposta: {resultado[:100]}...")
            return True
        else:
            print(f"⚠️ Resposta vazia ou muito curta: {resultado}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste de processamento: {e}")
        return False

def diagnosticar_problemas():
    """Diagnostica problemas comuns"""
    print("\n🔍 DIAGNÓSTICO DE PROBLEMAS COMUNS:")
    
    problemas = []
    
    # Verificar imports críticos
    try:
        import app.claude_ai_novo
        print("✅ Módulo claude_ai_novo importável")
    except ImportError as e:
        problemas.append(f"claude_ai_novo não importável: {e}")
        print(f"❌ claude_ai_novo não importável: {e}")
    
    # Verificar contexto Flask
    try:
        from flask import current_app
        if current_app:
            print("✅ Contexto Flask disponível")
        else:
            problemas.append("Contexto Flask não disponível")
            print("❌ Contexto Flask não disponível")
    except RuntimeError:
        problemas.append("Não está rodando no contexto Flask")
        print("⚠️ Não está rodando no contexto Flask")
    
    # Verificar banco de dados
    try:
        from app import db
        if db:
            print("✅ Banco de dados disponível")
        else:
            problemas.append("Banco de dados não disponível")
            print("❌ Banco de dados não disponível")
    except Exception as e:
        problemas.append(f"Erro no banco: {e}")
        print(f"❌ Erro no banco: {e}")
    
    if problemas:
        print(f"\n⚠️ {len(problemas)} problema(s) encontrado(s):")
        for i, problema in enumerate(problemas, 1):
            print(f"   {i}. {problema}")
    else:
        print("\n✅ Nenhum problema crítico encontrado")
    
    return len(problemas) == 0

def main():
    """Executa verificação completa"""
    print("🚀 VERIFICAÇÃO COMPLETA DO SISTEMA CLAUDE AI\n")
    
    # Passo 1: Verificar sistema ativo
    sistema_novo_ativo = verificar_sistema_ativo()
    
    # Passo 2: Diagnosticar problemas
    sem_problemas = diagnosticar_problemas()
    
    # Passo 3: Testar processamento
    processamento_ok = testar_processamento()
    
    # Resumo final
    print("\n" + "="*60)
    print("📊 RESUMO FINAL:")
    print(f"{'✅' if sistema_novo_ativo else '❌'} Sistema Novo Ativo: {sistema_novo_ativo}")
    print(f"{'✅' if sem_problemas else '❌'} Sem Problemas Críticos: {sem_problemas}")
    print(f"{'✅' if processamento_ok else '❌'} Processamento Funcionando: {processamento_ok}")
    
    if sistema_novo_ativo and sem_problemas and processamento_ok:
        print("\n🎉 SISTEMA CLAUDE AI NOVO TOTALMENTE FUNCIONAL!")
        print("💡 Suas consultas estão usando a arquitetura modular avançada!")
    elif sistema_novo_ativo:
        print("\n⚠️ Sistema novo ativo mas com alguns problemas")
        print("💡 Consulte os logs para detalhes")
    else:
        print("\n❌ Sistema antigo ainda ativo")
        print("💡 Configure USE_NEW_CLAUDE_SYSTEM=true no Render")
        print("💡 Guia completo em: GUIA_ATIVACAO_SISTEMA_NOVO_RENDER.md")
    
    return sistema_novo_ativo and sem_problemas and processamento_ok

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1) 