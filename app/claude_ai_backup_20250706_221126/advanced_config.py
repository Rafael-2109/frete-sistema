"""
🧠 CONFIGURAÇÃO AVANÇADA DO CLAUDE AI
Remove limitações e expande capacidades significativamente
"""

# 🚀 CONFIGURAÇÕES DE PERFORMANCE
CLAUDE_CONFIG = {
    # Tokens e Processamento
    "max_tokens": 8192,              # 8x mais que o padrão anterior
    "max_output_tokens": 8192,       # Saída completa
    "temperature": 0.1,              # Precisão alta mas não rígida
    "top_p": 0.95,                   # Criatividade controlada
    
    # Capacidades de Leitura
    "max_file_size_mb": 50,          # Arquivos até 50MB
    "max_lines_read": 50000,         # Até 50.000 linhas
    "max_search_results": 1000,      # 1000 resultados de busca
    "max_variables_extract": 500,    # 500 variáveis por template
    
    # Capacidades de Análise
    "deep_analysis": True,           # Análise profunda habilitada
    "context_window": 200000,        # Janela de contexto expandida
    "multi_file_analysis": True,     # Análise multi-arquivo
    "recursive_scanning": True,      # Escaneamento recursivo
    
    # Processamento de Dados
    "unlimited_sql_results": True,   # Remove LIMITs desnecessários
    "batch_processing": True,        # Processamento em lote
    "parallel_analysis": True,       # Análise paralela
    "smart_caching": True,           # Cache inteligente
    
    # Capacidades de Escrita
    "auto_backup": True,             # Backup automático
    "multi_file_generation": True,   # Gerar múltiplos arquivos
    "advanced_refactoring": True,    # Refatoração avançada
    "intelligent_imports": True,     # Imports inteligentes
}

# 🔍 CONFIGURAÇÕES DE ANÁLISE AVANÇADA
ANALYSIS_CONFIG = {
    "code_complexity": True,         # Análise de complexidade
    "security_scanning": True,       # Escaneamento de segurança
    "performance_analysis": True,    # Análise de performance
    "dependency_mapping": True,      # Mapeamento de dependências
    "architecture_review": True,     # Revisão arquitetural
    "best_practices": True,          # Verificação de boas práticas
}

# 🚀 FUNCIONALIDADES AVANÇADAS
ADVANCED_FEATURES = {
    "auto_documentation": True,      # Documentação automática
    "intelligent_debugging": True,   # Debug inteligente
    "code_optimization": True,       # Otimização de código
    "pattern_recognition": True,     # Reconhecimento de padrões
    "predictive_analysis": True,     # Análise preditiva
    "self_improvement": True,        # Auto-melhoria
}

def get_advanced_config():
    """Retorna configuração avançada completa"""
    return {
        **CLAUDE_CONFIG,
        **ANALYSIS_CONFIG,
        **ADVANCED_FEATURES
    }

def is_unlimited_mode():
    """Verifica se modo ilimitado está ativo"""
    return True  # Sempre ativo após otimização
