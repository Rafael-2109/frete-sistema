#!/usr/bin/env python3
"""
Teste Abrangente de Todos os Módulos - Claude AI Novo
Testa TODOS os módulos do sistema para diagnosticar estado atual
"""

import os
import sys
import importlib
import traceback
from pathlib import Path

# Adicionar paths necessários
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir.parent))
sys.path.insert(0, str(current_dir.parent.parent))

def testar_modulo(module_path, descricao=""):
    """Testa um módulo específico"""
    try:
        if module_path.startswith('.'):
            # Import relativo
            module = importlib.import_module(module_path, package='app.claude_ai_novo')
        else:
            # Import absoluto
            module = importlib.import_module(module_path)
        
        return {
            'status': 'SUCESSO',
            'module': module,
            'error': None,
            'descricao': descricao
        }
    except Exception as e:
        return {
            'status': 'ERRO',
            'module': None,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'descricao': descricao
        }

def main():
    print("=" * 80)
    print("TESTE ABRANGENTE DE TODOS OS MÓDULOS - CLAUDE AI NOVO")
    print("=" * 80)
    
    # Estrutura completa de módulos organizados por responsabilidade
    modulos_teste = {
        '🔧 COORDENADORES': [
            ('app.claude_ai_novo.coordinators.processor_coordinator', 'Coordenador de Processadores'),
            ('app.claude_ai_novo.coordinators.intelligence_coordinator', 'Coordenador de Inteligência'),
        ],
        
        '📊 ANALISADORES': [
            ('app.claude_ai_novo.analyzers.analyzer_manager', 'Gerenciador de Analisadores'),
            ('app.claude_ai_novo.analyzers.intention_analyzer', 'Analisador de Intenções'),
            ('app.claude_ai_novo.analyzers.metacognitive_analyzer', 'Analisador Metacognitivo'),
            ('app.claude_ai_novo.analyzers.structural_analyzer', 'Analisador Estrutural'),
            ('app.claude_ai_novo.analyzers.semantic_analyzer', 'Analisador Semântico'),
            ('app.claude_ai_novo.analyzers.query_analyzer', 'Analisador de Consultas'),
        ],
        
        '⚙️ PROCESSADORES': [
            ('app.claude_ai_novo.processors.context_processor', 'Processador de Contexto'),
            ('app.claude_ai_novo.processors.query_processor', 'Processador de Consultas'),
            ('app.claude_ai_novo.processors.semantic_loop_processor', 'Processador Loop Semântico'),
            ('app.claude_ai_novo.processors.data_processor', 'Processador de Dados'),
            ('app.claude_ai_novo.processors.intelligence_processor', 'Processador de Inteligência'),
        ],
        
        '📥 CARREGADORES': [
            ('app.claude_ai_novo.loaders.context_loader', 'Carregador de Contexto'),
            ('app.claude_ai_novo.loaders.database_loader', 'Carregador de Banco de Dados'),
            ('app.claude_ai_novo.loaders.data_manager', 'Gerenciador de Dados'),
        ],
        
        '🗺️ MAPEADORES': [
            ('app.claude_ai_novo.mappers.field_mapper', 'Mapeador de Campos'),
            ('app.claude_ai_novo.mappers.context_mapper', 'Mapeador de Contexto'),
            ('app.claude_ai_novo.mappers.query_mapper', 'Mapeador de Consultas'),
            ('app.claude_ai_novo.mappers.data_mapper', 'Mapeador de Dados'),
        ],
        
        '🔄 ORQUESTRADORES': [
            ('app.claude_ai_novo.orchestrators.main_orchestrator', 'Orquestrador Principal'),
            ('app.claude_ai_novo.orchestrators.workflow_orchestrator', 'Orquestrador de Fluxo'),
            ('app.claude_ai_novo.orchestrators.integration_orchestrator', 'Orquestrador de Integração'),
        ],
        
        '📚 PROVEDORES': [
            ('app.claude_ai_novo.providers.data_provider', 'Provedor de Dados'),
            ('app.claude_ai_novo.providers.context_provider', 'Provedor de Contexto'),
            ('app.claude_ai_novo.providers.provider_manager', 'Gerenciador de Provedores'),
        ],
        
        '✅ VALIDADORES': [
            ('app.claude_ai_novo.validators.data_validator', 'Validador de Dados'),
            ('app.claude_ai_novo.validators.semantic_validator', 'Validador Semântico'),
            ('app.claude_ai_novo.validators.critic_validator', 'Validador Crítico'),
            ('app.claude_ai_novo.validators.structural_validator', 'Validador de Estrutural'),
        ],
        
        '🧠 MEMORIZADORES': [
            ('app.claude_ai_novo.memorizers.memory_manager', 'Gerenciador de Memória'),
            ('app.claude_ai_novo.memorizers.conversation_memory', 'Memória de Conversa'),
        ],
        
        '🎓 APRENDIZES': [
            ('app.claude_ai_novo.learners.human_in_loop_learning', 'Aprendizado Human-in-Loop'),
            ('app.claude_ai_novo.learners.lifelong_learning', 'Aprendizado Contínuo'),
            ('app.claude_ai_novo.learners.adaptive_learning', 'Aprendizado Adaptativo'),
        ],
        
        '💬 CONVERSADORES': [
            ('app.claude_ai_novo.conversers.conversation_manager', 'Gerenciador de Conversa'),
        ],
        
        '🔍 ESCANEADORES': [
            ('app.claude_ai_novo.scanning.code_scanner', 'Escaneador de Código'),
            ('app.claude_ai_novo.scanning.database_scanner', 'Escaneador de Banco'),
            ('app.claude_ai_novo.scanning.project_scanner', 'Escaneador de Projeto'),
            ('app.claude_ai_novo.scanning.file_scanner', 'Escaneador de Arquivos'),
            
        ],
        
        '💡 SUGESTÕES': [
            ('app.claude_ai_novo.suggestions.suggestion_engine', 'Motor de Sugestões'),
            ('app.claude_ai_novo.suggestions.suggestions_manager', 'Gerenciador de Sugestões'),
        ],
        
        '🛠️ FERRAMENTAS': [
            ('app.claude_ai_novo.tools.tools_manager', 'Gerenciador de Ferramentas'),
        ],
        
        '⚡ ENRIQUECEDORES': [
            ('app.claude_ai_novo.enrichers.semantic_enricher', 'Enriquecedor Semântico'),
            ('app.claude_ai_novo.enrichers.context_enricher', 'Enriquecedor de Contexto'),
        ],
        
        '⚙️ UTILITÁRIOS': [
            ('app.claude_ai_novo.utils.response_utils', 'Utilitários de Resposta'),
            ('app.claude_ai_novo.utils.base_context_manager', 'Gerenciador Base de Contexto'),
            ('app.claude_ai_novo.utils.flask_context_wrapper', 'Wrapper de Contexto Flask'),
        ],
        
        '🔧 CONFIGURAÇÃO': [
            ('app.claude_ai_novo.config.advanced_config', 'Configuração Avançada'),
            ('app.claude_ai_novo.config.system_config', 'Configuração do Sistema'),
        ],
        
        '🔐 SEGURANÇA': [
            ('app.claude_ai_novo.security.security_guard', 'Guarda de Segurança'),
        ],
        
        '🔗 INTEGRAÇÃO': [
            ('app.claude_ai_novo.integration.integration_manager', 'Gerenciador de Integração'),
            ('app.claude_ai_novo.integration.standalone_manager', 'Gerenciador Standalone'),
            ('app.claude_ai_novo.integration.flask_routes', 'Rotas Flask de Integração'),
            ('app.claude_ai_novo.integration.claude.claude_integration', 'Integração Claude'),
            ('app.claude_ai_novo.integration.claude.claude_client', 'Cliente Claude'),
            ('app.claude_ai_novo.integration.advanced.advanced_integration', 'Integração Avançada'),
        ],
        
        '📋 COMANDOS': [
            ('app.claude_ai_novo.commands.base', 'Comandos Base'),
            ('app.claude_ai_novo.commands.cursor_commands', 'Comandos Cursor'),
            ('app.claude_ai_novo.commands.auto_command_processor', 'Processador Auto-Comando'),
        ],
    }
    
    # Estatísticas gerais
    total_modulos = sum(len(modulos) for modulos in modulos_teste.values())
    sucessos = 0
    erros = 0
    resultados_detalhados = {}
    
    print(f"Testando {total_modulos} módulos organizados por responsabilidade...\n")
    
    # Testar cada categoria
    for categoria, modulos in modulos_teste.items():
        print(f"\n{categoria}")
        print("-" * 60)
        
        sucessos_categoria = 0
        erros_categoria = 0
        resultados_categoria = []
        
        for module_path, descricao in modulos:
            resultado = testar_modulo(module_path, descricao)
            resultados_categoria.append(resultado)
            
            if resultado['status'] == 'SUCESSO':
                print(f"✅ {descricao:<35} - SUCESSO")
                sucessos += 1
                sucessos_categoria += 1
            else:
                print(f"❌ {descricao:<35} - ERRO: {resultado['error']}")
                erros += 1
                erros_categoria += 1
        
        # Resumo da categoria
        total_categoria = len(modulos)
        percentual_categoria = (sucessos_categoria / total_categoria) * 100
        print(f"📊 {categoria}: {sucessos_categoria}/{total_categoria} ({percentual_categoria:.1f}%)")
        
        resultados_detalhados[categoria] = {
            'resultados': resultados_categoria,
            'sucessos': sucessos_categoria,
            'erros': erros_categoria,
            'total': total_categoria,
            'percentual': percentual_categoria
        }
    
    # Resumo final
    print("\n" + "=" * 80)
    print("RESUMO FINAL")
    print("=" * 80)
    
    percentual_total = (sucessos / total_modulos) * 100
    print(f"📈 Taxa de Sucesso Geral: {sucessos}/{total_modulos} ({percentual_total:.1f}%)")
    
    # Ranking das categorias
    print("\n🏆 RANKING DAS CATEGORIAS:")
    categorias_ordenadas = sorted(
        resultados_detalhados.items(),
        key=lambda x: x[1]['percentual'],
        reverse=True
    )
    
    for i, (categoria, stats) in enumerate(categorias_ordenadas, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
        print(f"{emoji} {categoria}: {stats['percentual']:.1f}% ({stats['sucessos']}/{stats['total']})")
    
    # Análise de problemas críticos
    print("\n🔍 ANÁLISE DE PROBLEMAS CRÍTICOS:")
    categorias_problema = [cat for cat, stats in resultados_detalhados.items() if stats['percentual'] < 70]
    
    if categorias_problema:
        print("❌ Categorias com problemas críticos (<70%):")
        for categoria in categorias_problema:
            stats = resultados_detalhados[categoria]
            print(f"   • {categoria}: {stats['percentual']:.1f}%")
    else:
        print("✅ Nenhuma categoria com problemas críticos!")
    
    # Diagnóstico de próximos passos
    print(f"\n🎯 DIAGNÓSTICO DE PRÓXIMOS PASSOS:")
    if percentual_total >= 95:
        print("🚀 EXCELENTE! Sistema quase perfeito - foco em otimizações")
    elif percentual_total >= 85:
        print("🎉 MUITO BOM! Sistema estável - foco em funcionalidades avançadas")
    elif percentual_total >= 70:
        print("✅ BOM! Sistema funcional - foco em correções pontuais")
    elif percentual_total >= 50:
        print("⚠️ REGULAR! Sistema parcial - foco em correções estruturais")
    else:
        print("🚨 CRÍTICO! Sistema instável - foco em correções fundamentais")
    
    print("\n" + "=" * 80)
    print("TESTE CONCLUÍDO")
    print("=" * 80)
    
    return {
        'total_modulos': total_modulos,
        'sucessos': sucessos,
        'erros': erros,
        'percentual_total': percentual_total,
        'resultados_detalhados': resultados_detalhados,
        'categorias_problema': categorias_problema
    }

if __name__ == "__main__":
    main() 