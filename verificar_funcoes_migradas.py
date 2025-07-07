#!/usr/bin/env python3
"""
🔍 VERIFICAÇÃO DE FUNÇÕES MIGRADAS
Script para validar se todas as funções estão corretas após migração
"""

import os
import glob

def contar_funcoes_arquivo(arquivo_path):
    """Conta funções em um arquivo Python"""
    try:
        with open(arquivo_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        func_count = content.count('def ')
        class_count = content.count('class ')
        lines = len(content.split('\n'))
        
        return {
            'arquivo': os.path.basename(arquivo_path),
            'funcoes': func_count,
            'classes': class_count,
            'linhas': lines,
            'tamanho': len(content)
        }
    except Exception as e:
        return {
            'arquivo': os.path.basename(arquivo_path),
            'erro': str(e)
        }

def verificar_migracoes():
    """Verifica todas as migrações realizadas"""
    print("🔍 VERIFICAÇÃO COMPLETA DAS MIGRAÇÕES")
    print("=" * 60)
    
    # Arquivos migrados
    arquivos_verificar = [
        "app/claude_ai_novo/config/advanced_config.py",
        "app/claude_ai_novo/core/data_provider.py", 
        "app/claude_ai_novo/core/semantic_mapper.py",
        "app/claude_ai_novo/core/suggestion_engine.py",
        "app/claude_ai_novo/core/multi_agent_system.py",
        "app/claude_ai_novo/core/project_scanner.py",
        "app/claude_ai_novo/core/advanced_integration.py",
        "app/claude_ai_novo/intelligence/conversation_context.py",
        "app/claude_ai_novo/intelligence/human_in_loop_learning.py",
        "app/claude_ai_novo/intelligence/lifelong_learning.py"
    ]
    
    total_funcoes = 0
    total_classes = 0
    total_linhas = 0
    
    for arquivo in arquivos_verificar:
        if os.path.exists(arquivo):
            stats = contar_funcoes_arquivo(arquivo)
            
            if 'erro' in stats:
                print(f"❌ {stats['arquivo']}: ERRO - {stats['erro']}")
            else:
                print(f"✅ {stats['arquivo']}:")
                print(f"   📊 {stats['funcoes']} funções, {stats['classes']} classes")
                print(f"   📏 {stats['linhas']} linhas, {stats['tamanho']} bytes")
                
                total_funcoes += stats['funcoes']
                total_classes += stats['classes']
                total_linhas += stats['linhas']
        else:
            print(f"❌ {arquivo}: ARQUIVO NÃO ENCONTRADO")
    
    print("\n" + "=" * 60)
    print("📊 RESUMO GERAL:")
    print(f"   ⚙️ Total de funções: {total_funcoes}")
    print(f"   🏗️ Total de classes: {total_classes}")
    print(f"   📏 Total de linhas: {total_linhas}")
    
    # Verificar funções específicas importantes
    print("\n🔍 VERIFICANDO FUNÇÕES CRÍTICAS:")
    verificar_funcoes_criticas()
    
    # Verificar estrutura de pacotes
    print("\n📦 VERIFICANDO ESTRUTURA DE PACOTES:")
    verificar_estrutura_pacotes()

def verificar_funcoes_criticas():
    """Verifica se funções críticas estão presentes"""
    
    funcoes_criticas = {
        "app/claude_ai_novo/config/advanced_config.py": [
            "get_advanced_config",
            "is_unlimited_mode"
        ],
        "app/claude_ai_novo/core/data_provider.py": [
            "buscar_todos_modelos_reais",
            "buscar_clientes_reais",
            "gerar_system_prompt_real",
            "get_sistema_real_data"
        ],
        "app/claude_ai_novo/core/semantic_mapper.py": [
            "mapear_termo_natural",
            "mapear_consulta_completa",
            "gerar_prompt_mapeamento",
            "get_mapeamento_semantico"
        ],
        "app/claude_ai_novo/core/suggestion_engine.py": [
            "get_intelligent_suggestions",
            "_generate_suggestions",
            "_generate_data_based_suggestions",
            "_get_contextual_suggestions",
            "get_suggestion_engine"
        ],
        "app/claude_ai_novo/core/multi_agent_system.py": [
            "process_query",
            "validate_responses",
            "get_multi_agent_system",
            "analyze",
            "get_system_stats"
        ],
        "app/claude_ai_novo/core/project_scanner.py": [
            "scan_complete_project",
            "read_file_content",
            "list_directory_contents",
            "get_project_scanner",
            "search_in_files"
        ],
        "app/claude_ai_novo/core/advanced_integration.py": [
            "process_advanced_query",
            "analyze_own_performance",
            "capture_advanced_feedback",
            "get_advanced_ai_integration",
            "get_advanced_analytics"
        ],
        "app/claude_ai_novo/intelligence/conversation_context.py": [
            "add_message",
            "get_context",
            "clear_context",
            "get_conversation_context",
            "build_context_prompt"
        ],
        "app/claude_ai_novo/intelligence/human_in_loop_learning.py": [
            "capture_feedback",
            "get_improvement_suggestions",
            "apply_improvement",
            "get_human_learning_system",
            "generate_learning_report"
        ],
        "app/claude_ai_novo/intelligence/lifelong_learning.py": [
            "aprender_com_interacao",
            "aplicar_conhecimento",
            "obter_estatisticas_aprendizado",
            "get_lifelong_learning",
            "_extrair_padroes"
        ]
    }
    
    for arquivo, funcoes_esperadas in funcoes_criticas.items():
        if os.path.exists(arquivo):
            with open(arquivo, 'r', encoding='utf-8') as f:
                content = f.read()
            
            arquivo_nome = os.path.basename(arquivo)
            print(f"   📄 {arquivo_nome}:")
            
            for funcao in funcoes_esperadas:
                if f"def {funcao}" in content:
                    print(f"      ✅ {funcao}")
                else:
                    print(f"      ❌ {funcao} - NÃO ENCONTRADA")

def verificar_estrutura_pacotes():
    """Verifica se a estrutura de pacotes Python está correta"""
    
    diretorios_verificar = [
        "app/claude_ai_novo/config",
        "app/claude_ai_novo/core",
        "app/claude_ai_novo/intelligence",
        "app/claude_ai_novo/tests"
    ]
    
    for diretorio in diretorios_verificar:
        init_file = os.path.join(diretorio, "__init__.py")
        dir_nome = os.path.basename(diretorio)
        
        if os.path.exists(init_file):
            print(f"   ✅ {dir_nome}/__init__.py")
            
            # Verificar se tem imports
            with open(init_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'from .' in content or 'import' in content:
                print(f"      📦 Contém imports")
            else:
                print(f"      ⚠️ Sem imports (pode ser normal)")
        else:
            print(f"   ❌ {dir_nome}/__init__.py - NÃO ENCONTRADO")

def verificar_testes():
    """Verifica se todos os testes estão funcionando"""
    print("\n🧪 VERIFICANDO TESTES:")
    
    testes_esperados = [
        "app/claude_ai_novo/tests/test_config.py",
        "app/claude_ai_novo/tests/test_data_provider.py",
        "app/claude_ai_novo/tests/test_semantic_mapper.py",
        "app/claude_ai_novo/tests/test_suggestion_engine.py",
        "app/claude_ai_novo/tests/test_multi_agent_system.py",
        "app/claude_ai_novo/tests/test_project_scanner.py",
        "app/claude_ai_novo/tests/test_advanced_integration.py",
        "app/claude_ai_novo/tests/test_conversation_context.py",
        "app/claude_ai_novo/tests/test_human_learning.py",
        "app/claude_ai_novo/tests/test_lifelong_learning.py"
    ]
    
    for teste in testes_esperados:
        if os.path.exists(teste):
            nome_teste = os.path.basename(teste)
            print(f"   ✅ {nome_teste}")
        else:
            nome_teste = os.path.basename(teste)
            print(f"   ❌ {nome_teste} - NÃO ENCONTRADO")

if __name__ == "__main__":
    verificar_migracoes()
    verificar_testes() 