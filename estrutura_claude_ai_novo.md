# ESTRUTURA CLAUDE AI NOVO

## Diretório Principal: claude_ai_novo/

### __init__.py
**Classes:**
- `ClaudeAINovo` - Classe principal do sistema modular integrado
- `IntelligenceResult` - Resultado processado pelos sistemas de inteligência

**Funções:**
- `create_claude_ai_novo()` - Factory function para criar instância do Claude AI
- `get_claude_ai_instance()` - Obtém instância global singleton
- `reset_claude_ai_instance()` - Reseta instância global

**Métodos ClaudeAINovo:**
- `initialize_system()` - Inicializa todo sistema modular
- `process_query()` - Processa consulta usando sistema integrado
- `get_module()` - Obtém acesso direto a módulo específico
- `get_system_status()` - Status completo do sistema
- `processar_consulta()` - Método compatibilidade versão anterior
- `obter_estatisticas()` - Método compatibilidade para estatísticas

### claude_ai_modular.py
**Classes:**
- `ClaudeRealIntegration` - Integração principal com Claude API

**Funções:**
- `processar_consulta_modular()` - Função principal processamento consultas
- `get_nlp_analyzer()` - Retorna analisador NLP avançado
- `processar_com_claude_real()` - Acesso direto ao processador Claude
- `get_claude_integration()` - Acesso direto à integração Claude
- `get_nlp_enhanced_analyzer()` - Acesso direto ao analisador NLP

### routes.py
**Funções:**
- `run_async()` - Executa corrotina síncrona para rotas Flask
- `chat_page()` - Página principal do chat
- `api_query()` - API principal para consultas
- `api_feedback()` - API para feedback do usuário
- `clear_context()` - Limpa contexto conversacional
- `health_check()` - Health check do sistema
- `system_status()` - Status detalhado do sistema

### integration_manager.py
**Classes:**
- `IntegrationManager` - Gerenciador central de integração modular

**Métodos:**
- `initialize_all_modules()` - Inicializa todos módulos em ordem dependência
- `_initialize_base_modules()` - Inicializa módulos base sem dependências
- `_initialize_data_modules()` - Inicializa módulos de dados e banco
- `_initialize_intelligence_modules()` - Inicializa módulos inteligência
- `_initialize_semantic_modules()` - Inicializa módulos semânticos
- `_initialize_multiagent_system()` - Inicializa sistema multi-agente
- `_initialize_interface_modules()` - Inicializa módulos interface
- `_load_module()` - Carrega módulo específico
- `_validate_integration()` - Valida integração completa
- `get_module()` - Obtém módulo específico
- `get_system_status()` - Status do sistema
- `process_unified_query()` - Processa consulta unificada

## Diretório: analyzers/

### __init__.py
**Funções:**
- `get_analyzer_manager()` - Obtém gerenciador de analisadores
- `get_intention_analyzer()` - Obtém analisador de intenção
- `get_nlp_enhanced_analyzer()` - Obtém analisador NLP avançado

### analyzer_manager.py
**Classes:**
- `AnalyzerManager` - Gerenciador principal dos analisadores

**Métodos:**
- `initialize_analyzers()` - Inicializa todos analisadores
- `get_analyzer()` - Obtém analisador específico
- `analyze_with_all()` - Analisa usando todos analisadores
- `get_status()` - Status dos analisadores

### intention_analyzer.py
**Classes:**
- `IntentionAnalyzer` - Analisador de intenção de consultas

**Métodos:**
- `analyze_intention()` - Analisa intenção da consulta
- `_detect_domain()` - Detecta domínio da consulta
- `_extract_entities()` - Extrai entidades da consulta
- `_calculate_confidence()` - Calcula confiança da análise

### nlp_enhanced_analyzer.py
**Classes:**
- `NLPEnhancedAnalyzer` - Analisador NLP avançado com SpaCy e NLTK

**Métodos:**
- `analyze_text()` - Análise completa de texto
- `extract_entities()` - Extração de entidades nomeadas
- `calculate_similarity()` - Calcula similaridade entre textos
- `preprocess_text()` - Pré-processamento de texto

### metacognitive_analyzer.py
**Classes:**
- `MetacognitiveAnalyzer` - Analisador metacognitivo

**Métodos:**
- `analyze_metacognition()` - Análise metacognitiva
- `_assess_confidence()` - Avalia confiança da resposta
- `_analyze_uncertainty()` - Analisa incertezas
- `_suggest_improvements()` - Sugere melhorias

### structural_ai.py
**Classes:**
- `StructuralAI` - IA estrutural para análise de dados

**Métodos:**
- `analyze_structure()` - Analisa estrutura dos dados
- `detect_patterns()` - Detecta padrões nos dados
- `validate_structure()` - Valida estrutura dos dados

### query_analyzer.py
**Classes:**
- `QueryAnalyzer` - Analisador de consultas

**Métodos:**
- `analyze_query()` - Analisa consulta do usuário
- `categorize_query()` - Categoriza tipo de consulta
- `extract_parameters()` - Extrai parâmetros da consulta

## Diretório: commands/

### __init__.py
**Funções:**
- `get_command_manager()` - Obtém gerenciador de comandos
- `register_command()` - Registra novo comando

### base.py
**Classes:**
- `BaseCommand` - Classe base para comandos
- `CommandManager` - Gerenciador de comandos

**Métodos BaseCommand:**
- `execute()` - Executa comando
- `validate()` - Valida parâmetros comando
- `get_help()` - Obtém ajuda do comando

### cursor_commands.py
**Classes:**
- `CursorCommands` - Comandos relacionados ao Cursor

**Métodos:**
- `execute_cursor_command()` - Executa comando Cursor
- `list_cursor_commands()` - Lista comandos disponíveis
- `get_cursor_context()` - Obtém contexto do Cursor

### dev_commands.py
**Classes:**
- `DevCommands` - Comandos de desenvolvimento

**Métodos:**
- `execute_dev_command()` - Executa comando desenvolvimento
- `debug_system()` - Debug do sistema
- `generate_docs()` - Gera documentação

### file_commands.py
**Classes:**
- `FileCommands` - Comandos de arquivo

**Métodos:**
- `read_file()` - Lê arquivo
- `write_file()` - Escreve arquivo
- `list_files()` - Lista arquivos

### excel_orchestrator.py
**Classes:**
- `ExcelOrchestrator` - Orquestrador de comandos Excel

**Métodos:**
- `execute_excel_command()` - Executa comando Excel
- `generate_report()` - Gera relatório Excel
- `process_excel_data()` - Processa dados Excel

### Subdiretório: commands/excel/

#### __init__.py
**Funções:**
- `get_excel_manager()` - Obtém gerenciador Excel

#### pedidos.py
**Classes:**
- `PedidosExcelGenerator` - Gerador Excel para pedidos

**Métodos:**
- `generate_pedidos_excel()` - Gera Excel de pedidos
- `format_pedidos_data()` - Formata dados de pedidos

#### entregas.py
**Classes:**
- `EntregasExcelGenerator` - Gerador Excel para entregas

**Métodos:**
- `generate_entregas_excel()` - Gera Excel de entregas
- `format_entregas_data()` - Formata dados de entregas

#### fretes.py
**Classes:**
- `FretesExcelGenerator` - Gerador Excel para fretes

**Métodos:**
- `generate_fretes_excel()` - Gera Excel de fretes
- `format_fretes_data()` - Formata dados de fretes

#### faturamento.py
**Classes:**
- `FaturamentoExcelGenerator` - Gerador Excel para faturamento

**Métodos:**
- `generate_faturamento_excel()` - Gera Excel de faturamento
- `format_faturamento_data()` - Formata dados de faturamento

## Diretório: config/

### __init__.py
**Funções:**
- `get_config()` - Obtém configuração ativa
- `load_config()` - Carrega configuração

### advanced_config.py
**Classes:**
- `AdvancedConfig` - Configuração avançada do sistema

**Métodos:**
- `load_advanced_settings()` - Carrega configurações avançadas
- `get_setting()` - Obtém configuração específica
- `update_setting()` - Atualiza configuração

### basic_config.py
**Classes:**
- `BasicConfig` - Configuração básica do sistema

**Métodos:**
- `load_basic_settings()` - Carrega configurações básicas
- `get_basic_setting()` - Obtém configuração básica

## Diretório: data/

### __init__.py
**Funções:**
- `get_data_manager()` - Obtém gerenciador de dados
- `get_data_provider()` - Obtém provedor de dados

### data_manager.py
**Classes:**
- `DataManager` - Gerenciador principal de dados

**Métodos:**
- `initialize_data_sources()` - Inicializa fontes de dados
- `get_data_source()` - Obtém fonte de dados específica
- `sync_data()` - Sincroniza dados
- `validate_data()` - Valida dados

### Subdiretório: data/loaders/

#### context_loader.py
**Classes:**
- `ContextLoader` - Carregador de contexto

**Métodos:**
- `load_context()` - Carrega contexto
- `build_context()` - Constrói contexto
- `validate_context()` - Valida contexto

### Subdiretório: data/micro_loaders/

#### agendamentos_loader.py
**Classes:**
- `AgendamentosLoader` - Carregador de agendamentos

**Métodos:**
- `load_agendamentos()` - Carrega agendamentos
- `filter_agendamentos()` - Filtra agendamentos

#### pedidos_loader.py
**Classes:**
- `PedidosLoader` - Carregador de pedidos

**Métodos:**
- `load_pedidos()` - Carrega pedidos
- `filter_pedidos()` - Filtra pedidos

#### entregas_loader.py
**Classes:**
- `EntregasLoader` - Carregador de entregas

**Métodos:**
- `load_entregas()` - Carrega entregas
- `filter_entregas()` - Filtra entregas

#### fretes_loader.py
**Classes:**
- `FretesLoader` - Carregador de fretes

**Métodos:**
- `load_fretes()` - Carrega fretes
- `filter_fretes()` - Filtra fretes

#### embarques_loader.py
**Classes:**
- `EmbarquesLoader` - Carregador de embarques

**Métodos:**
- `load_embarques()` - Carrega embarques
- `filter_embarques()` - Filtra embarques

#### faturamento_loader.py
**Classes:**
- `FaturamentoLoader` - Carregador de faturamento

**Métodos:**
- `load_faturamento()` - Carrega faturamento
- `filter_faturamento()` - Filtra faturamento

### Subdiretório: data/providers/

#### data_provider.py
**Classes:**
- `DataProvider` - Provedor principal de dados

**Métodos:**
- `get_data()` - Obtém dados
- `process_data()` - Processa dados
- `cache_data()` - Cache de dados
- `validate_data()` - Valida dados

## Diretório: intelligence/

### __init__.py
**Funções:**
- `get_intelligence_manager()` - Obtém gerenciador de inteligência

### intelligence_manager.py
**Classes:**
- `IntelligenceManager` - Gerenciador principal de inteligência
- `IntelligenceResult` - Resultado processado pelos sistemas
- `FlaskContextWrapper` - Wrapper para contexto Flask
- `FlaskDatabaseAdapter` - Adapter para operações banco

**Métodos IntelligenceManager:**
- `process_intelligence()` - Processa consulta através sistemas inteligência
- `get_conversation_context()` - Obtém contexto conversacional
- `update_conversation_context()` - Atualiza contexto conversacional
- `capture_human_feedback()` - Captura feedback humano
- `apply_lifelong_learning()` - Aplica aprendizado vitalício
- `get_intelligence_status()` - Status sistemas inteligência
- `health_check()` - Verifica saúde do sistema

### Subdiretório: intelligence/learning/

#### __init__.py
**Funções:**
- `get_learning_core()` - Obtém núcleo de aprendizado

#### learning_core.py
**Classes:**
- `LearningCore` - Núcleo principal de aprendizado

**Métodos:**
- `initialize_learning()` - Inicializa aprendizado
- `learn_from_interaction()` - Aprende de interação
- `update_knowledge()` - Atualiza conhecimento
- `get_learning_stats()` - Estatísticas de aprendizado

#### pattern_learner.py
**Classes:**
- `PatternLearner` - Aprendizado de padrões

**Métodos:**
- `learn_patterns()` - Aprende padrões
- `detect_patterns()` - Detecta padrões
- `classify_patterns()` - Classifica padrões

#### human_in_loop_learning.py
**Classes:**
- `HumanInLoopLearning` - Aprendizado humano-no-loop

**Métodos:**
- `capture_feedback()` - Captura feedback humano
- `process_feedback()` - Processa feedback
- `update_learning()` - Atualiza aprendizado

#### feedback_processor.py
**Classes:**
- `FeedbackProcessor` - Processador de feedback

**Métodos:**
- `process_feedback()` - Processa feedback
- `analyze_feedback()` - Analisa feedback
- `categorize_feedback()` - Categoriza feedback

#### lifelong_learning.py
**Classes:**
- `LifelongLearningSystem` - Sistema aprendizado vitalício

**Métodos:**
- `apply_learning()` - Aplica aprendizado
- `continuous_learning()` - Aprendizado contínuo
- `update_models()` - Atualiza modelos

### Subdiretório: intelligence/memory/

#### __init__.py
**Funções:**
- `get_context_manager()` - Obtém gerenciador de contexto

#### context_manager.py
**Classes:**
- `ContextManager` - Gerenciador de contexto/memória

**Métodos:**
- `manage_context()` - Gerencia contexto
- `store_context()` - Armazena contexto
- `retrieve_context()` - Recupera contexto

### Subdiretório: intelligence/conversation/

#### __init__.py
**Funções:**
- `get_conversation_context()` - Obtém contexto conversacional

#### conversation_context.py
**Classes:**
- `ConversationContext` - Contexto conversacional

**Métodos:**
- `get_context()` - Obtém contexto
- `add_message()` - Adiciona mensagem
- `clear_context()` - Limpa contexto

## Diretório: integration/

### __init__.py
**Funções:**
- `get_integration_manager()` - Obtém gerenciador de integração

### integration_manager.py
**Classes:**
- `IntegrationManager` - Gerenciador de integração

**Métodos:**
- `initialize_integrations()` - Inicializa integrações
- `get_integration()` - Obtém integração específica
- `sync_integrations()` - Sincroniza integrações

### Subdiretório: integration/claude/

#### __init__.py
**Funções:**
- `get_claude_client()` - Obtém cliente Claude
- `get_claude_integration()` - Obtém integração Claude

#### claude_client.py
**Classes:**
- `ClaudeClient` - Cliente para API Claude

**Métodos:**
- `initialize_client()` - Inicializa cliente
- `send_message()` - Envia mensagem
- `get_response()` - Obtém resposta

#### claude_integration.py
**Classes:**
- `ClaudeRealIntegration` - Integração real com Claude

**Métodos:**
- `processar_com_claude_real()` - Processa com Claude real
- `_prepare_context()` - Prepara contexto
- `_process_response()` - Processa resposta

### Subdiretório: integration/processing/

#### __init__.py
**Funções:**
- `get_response_formatter()` - Obtém formatador de resposta

#### response_formatter.py
**Classes:**
- `ResponseFormatter` - Formatador de respostas

**Métodos:**
- `format_response()` - Formata resposta
- `clean_response()` - Limpa resposta
- `validate_response()` - Valida resposta

### Subdiretório: integration/advanced/

#### __init__.py
**Funções:**
- `get_advanced_integration()` - Obtém integração avançada

#### advanced_integration.py
**Classes:**
- `AdvancedIntegration` - Integração avançada

**Métodos:**
- `process_advanced_query()` - Processa consulta avançada
- `apply_advanced_features()` - Aplica recursos avançados
- `get_advanced_response()` - Obtém resposta avançada

## Diretório: multi_agent/

### __init__.py
**Funções:**
- `get_multi_agent_system()` - Obtém sistema multi-agente

### multi_agent_orchestrator.py
**Classes:**
- `MultiAgentOrchestrator` - Orquestrador multi-agente

**Métodos:**
- `orchestrate_agents()` - Orquestra agentes
- `coordinate_responses()` - Coordena respostas
- `validate_consensus()` - Valida consenso

### system.py
**Classes:**
- `MultiAgentSystem` - Sistema multi-agente

**Métodos:**
- `initialize_system()` - Inicializa sistema
- `process_with_agents()` - Processa com agentes
- `get_agent_responses()` - Obtém respostas agentes

### critic_agent.py
**Classes:**
- `CriticAgent` - Agente crítico

**Métodos:**
- `critique_response()` - Critica resposta
- `validate_quality()` - Valida qualidade
- `suggest_improvements()` - Sugere melhorias

### agent_types.py
**Classes:**
- `AgentType` - Tipos de agentes

**Métodos:**
- `get_agent_type()` - Obtém tipo de agente
- `validate_agent_type()` - Valida tipo de agente

### specialist_agents.py
**Classes:**
- `SpecialistAgent` - Agente especialista

**Métodos:**
- `get_specialist()` - Obtém especialista
- `coordinate_specialists()` - Coordena especialistas

### Subdiretório: multi_agent/agents/

#### __init__.py
**Funções:**
- `get_agent()` - Obtém agente específico

#### base_agent.py
**Classes:**
- `BaseAgent` - Agente base

**Métodos:**
- `process_query()` - Processa consulta
- `validate_input()` - Valida entrada
- `format_response()` - Formata resposta

#### smart_base_agent.py
**Classes:**
- `SmartBaseAgent` - Agente base inteligente

**Métodos:**
- `smart_process()` - Processamento inteligente
- `learn_from_context()` - Aprende do contexto
- `adapt_response()` - Adapta resposta

#### entregas_agent.py
**Classes:**
- `EntregasAgent` - Agente de entregas

**Métodos:**
- `process_entregas_query()` - Processa consulta entregas
- `get_entregas_data()` - Obtém dados entregas
- `format_entregas_response()` - Formata resposta entregas

#### fretes_agent.py
**Classes:**
- `FretesAgent` - Agente de fretes

**Métodos:**
- `process_fretes_query()` - Processa consulta fretes
- `get_fretes_data()` - Obtém dados fretes
- `format_fretes_response()` - Formata resposta fretes

#### pedidos_agent.py
**Classes:**
- `PedidosAgent` - Agente de pedidos

**Métodos:**
- `process_pedidos_query()` - Processa consulta pedidos
- `get_pedidos_data()` - Obtém dados pedidos
- `format_pedidos_response()` - Formata resposta pedidos

#### embarques_agent.py
**Classes:**
- `EmbarquesAgent` - Agente de embarques

**Métodos:**
- `process_embarques_query()` - Processa consulta embarques
- `get_embarques_data()` - Obtém dados embarques
- `format_embarques_response()` - Formata resposta embarques

#### financeiro_agent.py
**Classes:**
- `FinanceiroAgent` - Agente financeiro

**Métodos:**
- `process_financeiro_query()` - Processa consulta financeiro
- `get_financeiro_data()` - Obtém dados financeiro
- `format_financeiro_response()` - Formata resposta financeiro

## Diretório: processors/

### __init__.py
**Funções:**
- `get_processor_manager()` - Obtém gerenciador de processadores

### base.py
**Classes:**
- `BaseProcessor` - Processador base
- `ProcessorChain` - Cadeia de processadores

**Métodos BaseProcessor:**
- `process()` - Processa dados
- `validate()` - Valida dados
- `transform()` - Transforma dados

### processor_manager.py
**Classes:**
- `ProcessorManager` - Gerenciador de processadores

**Métodos:**
- `initialize_processors()` - Inicializa processadores
- `get_processor()` - Obtém processador específico
- `chain_processors()` - Encadeia processadores

### processor_registry.py
**Classes:**
- `ProcessorRegistry` - Registro de processadores

**Métodos:**
- `register_processor()` - Registra processador
- `get_registered_processors()` - Obtém processadores registrados
- `validate_processor()` - Valida processador

### processor_coordinator.py
**Classes:**
- `ProcessorCoordinator` - Coordenador de processadores

**Métodos:**
- `coordinate_processing()` - Coordena processamento
- `sync_processors()` - Sincroniza processadores
- `validate_coordination()` - Valida coordenação

### context_processor.py
**Classes:**
- `ContextProcessor` - Processador de contexto

**Métodos:**
- `process_context()` - Processa contexto
- `enrich_context()` - Enriquece contexto
- `validate_context()` - Valida contexto

### response_processor.py
**Classes:**
- `ResponseProcessor` - Processador de respostas

**Métodos:**
- `process_response()` - Processa resposta
- `format_response()` - Formata resposta
- `validate_response()` - Valida resposta

### semantic_loop_processor.py
**Classes:**
- `SemanticLoopProcessor` - Processador loop semântico

**Métodos:**
- `process_semantic_loop()` - Processa loop semântico
- `iterate_semantics()` - Itera semântica
- `validate_semantics()` - Valida semântica

### query_processor.py
**Classes:**
- `QueryProcessor` - Processador de consultas

**Métodos:**
- `process_query()` - Processa consulta
- `parse_query()` - Analisa consulta
- `validate_query()` - Valida consulta

### flask_context_wrapper.py
**Classes:**
- `FlaskContextWrapper` - Wrapper contexto Flask

**Métodos:**
- `wrap_context()` - Envolve contexto
- `get_flask_context()` - Obtém contexto Flask
- `validate_flask_context()` - Valida contexto Flask

## Diretório: scanning/

### __init__.py
**Funções:**
- `get_scanner()` - Obtém scanner específico

### scanner.py
**Classes:**
- `Scanner` - Scanner base

**Métodos:**
- `scan()` - Executa scanning
- `analyze_scan()` - Analisa resultado scan
- `generate_report()` - Gera relatório

### project_scanner.py
**Classes:**
- `ProjectScanner` - Scanner de projeto

**Métodos:**
- `scan_project()` - Escaneia projeto
- `analyze_structure()` - Analisa estrutura
- `generate_project_report()` - Gera relatório projeto

### file_scanner.py
**Classes:**
- `FileScanner` - Scanner de arquivos

**Métodos:**
- `scan_files()` - Escaneia arquivos
- `analyze_files()` - Analisa arquivos
- `generate_file_report()` - Gera relatório arquivos

### code_scanner.py
**Classes:**
- `CodeScanner` - Scanner de código

**Métodos:**
- `scan_code()` - Escaneia código
- `analyze_code()` - Analisa código
- `detect_patterns()` - Detecta padrões

### database_scanner.py
**Classes:**
- `DatabaseScanner` - Scanner de banco de dados

**Métodos:**
- `scan_database()` - Escaneia banco
- `analyze_tables()` - Analisa tabelas
- `map_relationships()` - Mapeia relacionamentos

### structure_scanner.py
**Classes:**
- `StructureScanner` - Scanner de estrutura

**Métodos:**
- `scan_structure()` - Escaneia estrutura
- `analyze_architecture()` - Analisa arquitetura
- `validate_structure()` - Valida estrutura

## Diretório: semantic/

### __init__.py
**Funções:**
- `get_semantic_manager()` - Obtém gerenciador semântico

### semantic_manager.py
**Classes:**
- `SemanticManager` - Gerenciador semântico

**Métodos:**
- `initialize_semantic()` - Inicializa semântica
- `process_semantic()` - Processa semântica
- `get_semantic_data()` - Obtém dados semânticos

### semantic_orchestrator.py
**Classes:**
- `SemanticOrchestrator` - Orquestrador semântico

**Métodos:**
- `orchestrate_semantic()` - Orquestra semântica
- `coordinate_semantic_modules()` - Coordena módulos semânticos
- `validate_semantic_flow()` - Valida fluxo semântico

### semantic_enricher.py
**Classes:**
- `SemanticEnricher` - Enriquecedor semântico

**Métodos:**
- `enrich_content()` - Enriquece conteúdo
- `add_semantic_metadata()` - Adiciona metadados semânticos
- `process_semantic_tags()` - Processa tags semânticas

### semantic_validator.py
**Classes:**
- `SemanticValidator` - Validador semântico

**Métodos:**
- `validate_semantic()` - Valida semântica
- `check_semantic_consistency()` - Verifica consistência semântica
- `repair_semantic_errors()` - Repara erros semânticos

### semantic_diagnostics.py
**Classes:**
- `SemanticDiagnostics` - Diagnósticos semânticos

**Métodos:**
- `diagnose_semantic()` - Diagnostica semântica
- `analyze_semantic_health()` - Analisa saúde semântica
- `generate_diagnostic_report()` - Gera relatório diagnóstico

### Subdiretório: semantic/readers/

#### __init__.py
**Funções:**
- `get_database_reader()` - Obtém leitor de banco

#### database_reader.py
**Classes:**
- `DatabaseReader` - Leitor de banco de dados

**Métodos:**
- `read_database()` - Lê banco de dados
- `extract_metadata()` - Extrai metadados
- `map_relationships()` - Mapeia relacionamentos

#### readme_reader.py
**Classes:**
- `ReadmeReader` - Leitor de README

**Métodos:**
- `read_readme()` - Lê README
- `extract_documentation()` - Extrai documentação
- `parse_markdown()` - Analisa markdown

#### performance_cache.py
**Classes:**
- `PerformanceCache` - Cache de performance

**Métodos:**
- `cache_data()` - Cache dados
- `get_cached_data()` - Obtém dados cache
- `validate_cache()` - Valida cache

#### Subdiretório: semantic/readers/database/

##### __init__.py
**Funções:**
- `get_database_components()` - Obtém componentes banco

##### database_connection.py
**Classes:**
- `DatabaseConnection` - Conexão com banco

**Métodos:**
- `connect()` - Conecta ao banco
- `get_connection()` - Obtém conexão
- `close_connection()` - Fecha conexão

##### metadata_reader.py
**Classes:**
- `MetadataReader` - Leitor de metadados

**Métodos:**
- `read_metadata()` - Lê metadados
- `extract_table_info()` - Extrai info tabelas
- `get_column_info()` - Obtém info colunas

##### data_analyzer.py
**Classes:**
- `DataAnalyzer` - Analisador de dados

**Métodos:**
- `analyze_data()` - Analisa dados
- `detect_patterns()` - Detecta padrões
- `generate_statistics()` - Gera estatísticas

##### auto_mapper.py
**Classes:**
- `AutoMapper` - Mapeador automático

**Métodos:**
- `auto_map()` - Mapeamento automático
- `map_relationships()` - Mapeia relacionamentos
- `validate_mapping()` - Valida mapeamento

##### field_searcher.py
**Classes:**
- `FieldSearcher` - Buscador de campos

**Métodos:**
- `search_fields()` - Busca campos
- `find_matching_fields()` - Encontra campos correspondentes
- `validate_field_matches()` - Valida correspondências

##### relationship_mapper.py
**Classes:**
- `RelationshipMapper` - Mapeador de relacionamentos

**Métodos:**
- `map_relationships()` - Mapeia relacionamentos
- `detect_foreign_keys()` - Detecta chaves estrangeiras
- `validate_relationships()` - Valida relacionamentos

### Subdiretório: semantic/mappers/

#### __init__.py
**Funções:**
- `get_mapper()` - Obtém mapeador específico

#### base_mapper.py
**Classes:**
- `BaseMapper` - Mapeador base

**Métodos:**
- `map_data()` - Mapeia dados
- `validate_mapping()` - Valida mapeamento
- `transform_data()` - Transforma dados

#### pedidos_mapper.py
**Classes:**
- `PedidosMapper` - Mapeador de pedidos

**Métodos:**
- `map_pedidos()` - Mapeia pedidos
- `transform_pedidos_data()` - Transforma dados pedidos
- `validate_pedidos_mapping()` - Valida mapeamento pedidos

#### faturamento_mapper.py
**Classes:**
- `FaturamentoMapper` - Mapeador de faturamento

**Métodos:**
- `map_faturamento()` - Mapeia faturamento
- `transform_faturamento_data()` - Transforma dados faturamento
- `validate_faturamento_mapping()` - Valida mapeamento faturamento

#### embarques_mapper.py
**Classes:**
- `EmbarquesMapper` - Mapeador de embarques

**Métodos:**
- `map_embarques()` - Mapeia embarques
- `transform_embarques_data()` - Transforma dados embarques
- `validate_embarques_mapping()` - Valida mapeamento embarques

#### monitoramento_mapper.py
**Classes:**
- `MonitoramentoMapper` - Mapeador de monitoramento

**Métodos:**
- `map_monitoramento()` - Mapeia monitoramento
- `transform_monitoramento_data()` - Transforma dados monitoramento
- `validate_monitoramento_mapping()` - Valida mapeamento monitoramento

#### transportadoras_mapper.py
**Classes:**
- `TransportadorasMapper` - Mapeador de transportadoras

**Métodos:**
- `map_transportadoras()` - Mapeia transportadoras
- `transform_transportadoras_data()` - Transforma dados transportadoras
- `validate_transportadoras_mapping()` - Valida mapeamento transportadoras

## Diretório: suggestions/

### __init__.py
**Funções:**
- `get_suggestion_engine()` - Obtém motor de sugestões

### engine.py
**Classes:**
- `SuggestionEngine` - Motor de sugestões

**Métodos:**
- `generate_suggestions()` - Gera sugestões
- `rank_suggestions()` - Classifica sugestões
- `validate_suggestions()` - Valida sugestões

### suggestions_manager.py
**Classes:**
- `SuggestionsManager` - Gerenciador de sugestões

**Métodos:**
- `manage_suggestions()` - Gerencia sugestões
- `update_suggestions()` - Atualiza sugestões
- `get_suggestion_stats()` - Estatísticas sugestões

## Diretório: tools/

### __init__.py
**Funções:**
- `get_tools_manager()` - Obtém gerenciador de ferramentas

### tools_manager.py
**Classes:**
- `ToolsManager` - Gerenciador de ferramentas

**Métodos:**
- `initialize_tools()` - Inicializa ferramentas
- `get_tool()` - Obtém ferramenta específica
- `validate_tools()` - Valida ferramentas

## Diretório: utils/

### __init__.py
**Funções:**
- `get_utils_manager()` - Obtém gerenciador de utilitários

### utils_manager.py
**Classes:**
- `UtilsManager` - Gerenciador de utilitários

**Métodos:**
- `initialize_utils()` - Inicializa utilitários
- `get_util()` - Obtém utilitário específico
- `validate_utils()` - Valida utilitários

### validation_utils.py
**Classes:**
- `ValidationUtils` - Utilitários de validação

**Métodos:**
- `validate_data()` - Valida dados
- `validate_structure()` - Valida estrutura
- `validate_format()` - Valida formato

### response_utils.py
**Classes:**
- `ResponseUtils` - Utilitários de resposta

**Métodos:**
- `format_response()` - Formata resposta
- `clean_response()` - Limpa resposta
- `validate_response()` - Valida resposta

## Diretório: knowledge/

### knowledge_manager.py
**Classes:**
- `KnowledgeManager` - Gerenciador de conhecimento

**Métodos:**
- `initialize_knowledge()` - Inicializa conhecimento
- `store_knowledge()` - Armazena conhecimento
- `retrieve_knowledge()` - Recupera conhecimento
- `update_knowledge()` - Atualiza conhecimento

## Diretório: security/

### __init__.py
**Funções:**
- `get_security_manager()` - Obtém gerenciador de segurança

## Diretório: tests/

### __init__.py
**Funções:**
- Funções de teste básicas

### test_advanced_integration.py
**Funções:**
- `test_advanced_integration()` - Testa integração avançada

### test_config.py
**Funções:**
- `test_config()` - Testa configuração

### test_conversation_context.py
**Funções:**
- `test_conversation_context()` - Testa contexto conversacional

### test_data_provider.py
**Funções:**
- `test_data_provider()` - Testa provedor de dados

### test_human_learning.py
**Funções:**
- `test_human_learning()` - Testa aprendizado humano

### test_lifelong_learning.py
**Funções:**
- `test_lifelong_learning()` - Testa aprendizado vitalício

### test_multi_agent_system.py
**Funções:**
- `test_multi_agent_system()` - Testa sistema multi-agente

### test_nlp_enhanced_analyzer.py
**Funções:**
- `test_nlp_enhanced_analyzer()` - Testa analisador NLP

### test_project_scanner.py
**Funções:**
- `test_project_scanner()` - Testa scanner de projeto

### test_suggestion_engine.py
**Funções:**
- `test_suggestion_engine()` - Testa motor de sugestões

## Arquivos de Análise e Configuração

### analisador_arquitetura_real.py
**Funções:**
- `analisar_arquitetura()` - Analisa arquitetura real do sistema
- `gerar_relatorio()` - Gera relatório de arquitetura
- `validar_estrutura()` - Valida estrutura do sistema

### analisador_dependencias_flask.py
**Funções:**
- `analisar_dependencias()` - Analisa dependências Flask
- `mapear_imports()` - Mapeia imports
- `validar_dependencias()` - Valida dependências

### Arquivos de Documentação

- `ARQUITETURA_MODULAR_DOCUMENTADA.md` - Documentação da arquitetura modular
- `RELATORIO_ARQUITETURA_RESUMIDO.md` - Relatório resumido da arquitetura
- `QUANTIFICACAO_SISTEMA_COMPLETA.md` - Quantificação completa do sistema
- `RELATORIO_FINAL_COMMANDS.md` - Relatório final dos commands
- `RELATORIO_ARQUITETURA_COMPLETA.json` - Relatório completo em JSON

### Arquivos de Correção e Análise

- `corrigir_estrutura_imports.py` - Correção de imports
- `analisar_imports_circulares.py` - Análise de imports circulares
- `corrigir_erros_pylance.py` - Correção de erros Pylance
- `diagnosticar_problemas_import.py` - Diagnóstico de problemas imports
- `validar_correcao_processors.py` - Validação correção processors
- `analisar_integracao_necessaria.py` - Análise integração necessária

### Diretórios de Sessão e Logs

- `flask_session/` - Sessões Flask
- `logs/` - Logs do sistema
- `uploads/` - Uploads temporários

## Resumo da Arquitetura

O sistema Claude AI Novo é uma arquitetura modular avançada com:

**28 módulos principais** organizados em:
- **6 agentes especializados** (entregas, fretes, pedidos, embarques, financeiro, crítico)
- **6 módulos de dados** (loaders, providers, micro-loaders)
- **5 módulos de inteligência** (aprendizado, contexto, memória, feedback)
- **4 módulos semânticos** (mappers, readers, validators, diagnostics)
- **3 módulos de processamento** (context, response, semantic loop)
- **2 módulos de interface** (suggestions, tools)
- **1 sistema de integração** central (integration manager)
- **1 sistema de comandos** (commands with excel support)

**Funcionalidades principais:**
- Sistema multi-agente com consenso
- Aprendizado contínuo e humano-no-loop
- Processamento semântico avançado
- Cache inteligente e otimização
- Integração total com Claude 4 Sonnet
- Suporte a Excel e relatórios
- Contexto conversacional persistente
- Validação e diagnósticos automáticos

**Arquitetura de produção:**
- Modularidade total (cada módulo independente)
- Fallbacks para todos os componentes
- Compatibilidade com versões anteriores
- Logs estruturados e monitoramento
- Testes automatizados
- Documentação completa 