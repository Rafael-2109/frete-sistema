#!/usr/bin/env python3
"""
🧪 AVALIAÇÃO LOCAL - ESTRUTURA DO CLAUDE AI
==========================================

Versão SIMPLIFICADA para testar localmente:
- Estrutura dos módulos
- Imports funcionando
- Lógica de dados (sem API)
- Configurações básicas

SEM NECESSIDADE DE:
- ANTHROPIC_API_KEY
- Redis
- Servidor rodando

Autor: Sistema de Avaliação Local
Data: 06/07/2025
"""

import sys
import os
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Adicionar diretório do projeto ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def avaliar_estrutura_local():
    """🧪 Avaliação da estrutura local do Claude AI"""
    
    print("🧪 AVALIAÇÃO LOCAL - ESTRUTURA CLAUDE AI")
    print("=" * 50)
    
    resultados = {
        'timestamp': datetime.now().isoformat(),
        'testes_estrutura': [],
        'imports_funcionando': [],
        'imports_falhando': [],
        'correções_aplicadas': [],
        'problemas_estruturais': []
    }
    
    # 📋 TESTES DE ESTRUTURA
    testes_estrutura = [
        {
            'nome': 'True Free Mode',
            'modulo': 'app.claude_ai.true_free_mode',
            'classe': 'TrueFreeMode',
            'funcoes': ['get_true_free_mode', 'is_truly_autonomous']
        },
        {
            'nome': 'Admin Free Mode',
            'modulo': 'app.claude_ai.admin_free_mode',
            'classe': 'AdminFreeModeManager',
            'funcoes': ['get_admin_free_mode']
        },
        {
            'nome': 'Claude Real Integration',
            'modulo': 'app.claude_ai.claude_real_integration',
            'classe': 'ClaudeRealIntegration',
            'funcoes': ['processar_com_claude_real']
        },
        {
            'nome': 'Conversation Context',
            'modulo': 'app.claude_ai.conversation_context',
            'classe': 'ConversationContextManager',
            'funcoes': ['get_conversation_context']
        },
        {
            'nome': 'Lifelong Learning',
            'modulo': 'app.claude_ai.lifelong_learning',
            'classe': 'LifelongLearning',
            'funcoes': ['get_lifelong_learning']
        }
    ]
    
    # 🧪 EXECUTAR TESTES DE IMPORTS
    for teste in testes_estrutura:
        print(f"\n🔍 TESTANDO: {teste['nome']}")
        print("-" * 30)
        
        resultado_teste = testar_import_modulo(teste)
        resultados['testes_estrutura'].append(resultado_teste)
        
        if resultado_teste['sucesso']:
            resultados['imports_funcionando'].append(teste['nome'])
            print(f"✅ {teste['nome']}: OK")
        else:
            resultados['imports_falhando'].append(f"{teste['nome']}: {resultado_teste['erro']}")
            print(f"❌ {teste['nome']}: {resultado_teste['erro']}")
    
    # 📊 TESTAR CORREÇÕES DE DADOS (SEM API)
    print(f"\n📊 TESTANDO CORREÇÕES DE DADOS...")
    correcoes = testar_correcoes_estrutura()
    resultados['correções_aplicadas'] = correcoes
    
    # 🧠 TESTAR INTEGRAÇÃO AUTONOMIA
    print(f"\n🧠 TESTANDO INTEGRAÇÃO MODO AUTONOMIA...")
    integracao = testar_integracao_autonomia()
    resultados['integracao_autonomia'] = integracao
    
    # 📈 RELATÓRIO ESTRUTURAL
    gerar_relatorio_estrutural(resultados)
    
    return resultados

def testar_import_modulo(teste: Dict[str, Any]) -> Dict[str, Any]:
    """🧪 Testa import de um módulo específico"""
    
    resultado = {
        'nome': teste['nome'],
        'modulo': teste['modulo'],
        'sucesso': False,
        'erro': '',
        'detalhes': {}
    }
    
    try:
        # Testar import do módulo
        modulo = __import__(teste['modulo'], fromlist=[teste['classe']])
        resultado['detalhes']['modulo_importado'] = True
        
        # Testar classe (se especificada)
        if teste['classe']:
            classe = getattr(modulo, teste['classe'], None)
            if classe:
                resultado['detalhes']['classe_encontrada'] = True
            else:
                resultado['detalhes']['classe_encontrada'] = False
                resultado['erro'] = f"Classe {teste['classe']} não encontrada"
        
        # Testar funções
        funcoes_ok = []
        funcoes_erro = []
        
        for funcao in teste['funcoes']:
            if hasattr(modulo, funcao):
                funcoes_ok.append(funcao)
            else:
                funcoes_erro.append(funcao)
        
        resultado['detalhes']['funcoes_ok'] = funcoes_ok
        resultado['detalhes']['funcoes_erro'] = funcoes_erro
        
        # Sucesso se módulo importou e pelo menos uma função existe
        if resultado['detalhes']['modulo_importado'] and len(funcoes_ok) > 0:
            resultado['sucesso'] = True
        elif len(funcoes_erro) > 0:
            resultado['erro'] = f"Funções não encontradas: {', '.join(funcoes_erro)}"
        
    except ImportError as e:
        resultado['erro'] = f"Erro de import: {str(e)}"
    except Exception as e:
        resultado['erro'] = f"Erro geral: {str(e)}"
    
    return resultado

def testar_correcoes_estrutura() -> List[str]:
    """📊 Testa se as correções foram aplicadas na estrutura"""
    
    correcoes = []
    
    try:
        # Testar se arquivo true_free_mode.py existe
        import os
        if os.path.exists('app/claude_ai/true_free_mode.py'):
            correcoes.append("✅ Arquivo true_free_mode.py criado")
            
            # Verificar conteúdo
            with open('app/claude_ai/true_free_mode.py', 'r', encoding='utf-8') as f:
                conteudo = f.read()
                
                if 'LIBERDADE TOTAL + CONSULTA PARA MUDANÇAS' in conteudo:
                    correcoes.append("✅ Filosofia correta implementada")
                
                if 'claude_autonomous_decision' in conteudo:
                    correcoes.append("✅ Sistema de decisão autônoma implementado")
                    
                if 'request_user_permission' in conteudo:
                    correcoes.append("✅ Sistema de permissões implementado")
        
        # Testar se dashboard foi criado
        if os.path.exists('app/templates/claude_ai/true_autonomy_dashboard.html'):
            correcoes.append("✅ Dashboard autonomia verdadeira criado")
        
        # Testar se rotas foram adicionadas
        if os.path.exists('app/claude_ai/routes.py'):
            with open('app/claude_ai/routes.py', 'r', encoding='utf-8') as f:
                conteudo = f.read()
                
                if 'true-free-mode' in conteudo:
                    correcoes.append("✅ Rotas do modo autonomia adicionadas")
                
                if 'enable_true_autonomy' in conteudo:
                    correcoes.append("✅ Função de ativar autonomia implementada")
        
        # Testar integração no claude_real_integration.py
        if os.path.exists('app/claude_ai/claude_real_integration.py'):
            with open('app/claude_ai/claude_real_integration.py', 'r', encoding='utf-8') as f:
                conteudo = f.read()
                
                if 'AUTONOMIA VERDADEIRA' in conteudo:
                    correcoes.append("✅ Integração autonomia verdadeira aplicada")
                
                if 'is_truly_autonomous' in conteudo:
                    correcoes.append("✅ Detecção automática de autonomia implementada")
        
    except Exception as e:
        correcoes.append(f"❌ Erro ao verificar correções: {str(e)}")
    
    return correcoes

def testar_integracao_autonomia() -> Dict[str, Any]:
    """🧠 Testa integração do modo autonomia (sem executar)"""
    
    integracao = {
        'modulo_carregado': False,
        'funcoes_disponiveis': [],
        'classe_funcional': False,
        'problema': ''
    }
    
    try:
        # Tentar importar sem executar
        from app.claude_ai.true_free_mode import get_true_free_mode, is_truly_autonomous
        
        integracao['modulo_carregado'] = True
        integracao['funcoes_disponiveis'] = ['get_true_free_mode', 'is_truly_autonomous']
        
        # Tentar criar instância (sem ativar)
        true_mode = get_true_free_mode()
        
        if true_mode:
            integracao['classe_funcional'] = True
            
            # Testar métodos básicos (sem executar)
            metodos_disponiveis = []
            
            if hasattr(true_mode, 'get_autonomous_dashboard_data'):
                metodos_disponiveis.append('get_autonomous_dashboard_data')
            
            if hasattr(true_mode, 'enable_true_autonomy'):
                metodos_disponiveis.append('enable_true_autonomy')
            
            if hasattr(true_mode, 'claude_autonomous_decision'):
                metodos_disponiveis.append('claude_autonomous_decision')
            
            integracao['metodos_disponiveis'] = metodos_disponiveis
            
            print(f"✅ Modo autonomia: {len(metodos_disponiveis)} métodos disponíveis")
            
        else:
            integracao['problema'] = 'Instância não foi criada'
            
    except ImportError as e:
        integracao['problema'] = f'Erro de import: {str(e)}'
    except Exception as e:
        integracao['problema'] = f'Erro geral: {str(e)}'
    
    return integracao

def gerar_relatorio_estrutural(resultados: Dict[str, Any]):
    """📈 Gera relatório da avaliação estrutural"""
    
    print("\n" + "=" * 50)
    print("📈 RELATÓRIO ESTRUTURAL")
    print("=" * 50)
    
    total_testes = len(resultados['testes_estrutura'])
    imports_ok = len(resultados['imports_funcionando'])
    imports_erro = len(resultados['imports_falhando'])
    
    taxa_sucesso = (imports_ok / total_testes) * 100 if total_testes > 0 else 0
    
    print(f"""
🧪 **TESTES DE ESTRUTURA:**
   • Total testado: {total_testes} módulos
   • Funcionando: {imports_ok}
   • Com problemas: {imports_erro}
   • Taxa de sucesso: {taxa_sucesso:.1f}%
""")
    
    # Módulos funcionando
    if resultados['imports_funcionando']:
        print("✅ **MÓDULOS FUNCIONANDO:**")
        for modulo in resultados['imports_funcionando']:
            print(f"   • {modulo}")
    
    # Módulos com problema
    if resultados['imports_falhando']:
        print("\n❌ **MÓDULOS COM PROBLEMAS:**")
        for problema in resultados['imports_falhando']:
            print(f"   • {problema}")
    
    # Correções aplicadas
    print(f"\n🔧 **CORREÇÕES APLICADAS:**")
    for correcao in resultados['correções_aplicadas']:
        print(f"   {correcao}")
    
    # Integração autonomia
    integracao = resultados.get('integracao_autonomia', {})
    print(f"""
🚀 **INTEGRAÇÃO MODO AUTONOMIA:**
   • Módulo carregado: {'✅ SIM' if integracao.get('modulo_carregado') else '❌ NÃO'}
   • Classe funcional: {'✅ SIM' if integracao.get('classe_funcional') else '❌ NÃO'}""")
    
    if integracao.get('funcoes_disponiveis'):
        print(f"   • Funções: {', '.join(integracao['funcoes_disponiveis'])}")
    
    if integracao.get('metodos_disponiveis'):
        print(f"   • Métodos: {', '.join(integracao['metodos_disponiveis'])}")
    
    if integracao.get('problema'):
        print(f"   • Problema: {integracao['problema']}")
    
    # Recomendações
    print(f"""
🎯 **RECOMENDAÇÕES:**""")
    
    if taxa_sucesso >= 80:
        print("   ✅ Estrutura está bem implementada!")
        print("   💡 Para teste completo, usar o Render (com API key)")
    elif taxa_sucesso >= 60:
        print("   ⚠️ Estrutura funcional, mas alguns problemas")
        print("   🔧 Corrigir imports que falharam")
    else:
        print("   ❌ Problemas estruturais sérios")
        print("   🚨 Revisar implementação dos módulos")
    
    print(f"""
🌐 **PRÓXIMOS PASSOS:**
   1. Para teste completo → usar Render.com
   2. Para teste de API → configurar ANTHROPIC_API_KEY
   3. Para teste Redis → configurar Redis local ou usar Render
   4. Para interface → acessar /claude-ai/true-free-mode/dashboard
""")
    
    print("\n" + "=" * 50)
    print("🏁 AVALIAÇÃO ESTRUTURAL CONCLUÍDA")
    print("=" * 50)

if __name__ == "__main__":
    try:
        print("🔍 Iniciando avaliação estrutural local...")
        resultados = avaliar_estrutura_local()
        print(f"\n🎉 Avaliação estrutural concluída!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Avaliação interrompida pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro na avaliação: {e}")
        traceback.print_exc() 