# 🔍 RELATÓRIO DE DEPENDÊNCIAS AUSENTES

**Data**: 2025-07-25 22:09:42

**Arquivos analisados**: 162

**Total de problemas**: 118

## 📊 PROBLEMAS POR TIPO

### FALLBACK INCOMPLETO (74 ocorrências)

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:0**
  - Variáveis importadas sem fallback: get_claude_client, db
  - Variáveis: get_claude_client, db

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/__init__.py:0**
  - Variáveis importadas sem fallback: NLPEnhancedAnalyzer, get_semantic_analyzer, get_structural_analyzer, IntentionAnalyzer, get_diagnostics_analyzer, MetacognitiveAnalyzer, StructuralAnalyzer, DiagnosticsAnalyzer, get_performance_analyzer, SemanticAnalyzer, AnalyzerManager, QueryAnalyzer, PerformanceAnalyzer, is_flask_available
  - Variáveis: NLPEnhancedAnalyzer, get_semantic_analyzer, get_structural_analyzer, IntentionAnalyzer, get_diagnostics_analyzer, MetacognitiveAnalyzer, StructuralAnalyzer, DiagnosticsAnalyzer, get_performance_analyzer, SemanticAnalyzer, AnalyzerManager, QueryAnalyzer, PerformanceAnalyzer, is_flask_available

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:0**
  - Variáveis importadas sem fallback: get_semantic_validator, get_scanning_manager
  - Variáveis: get_semantic_validator, get_scanning_manager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:0**
  - Variáveis importadas sem fallback: process, STOP_WORDS, stopwords, fuzz
  - Variáveis: process, STOP_WORDS, stopwords, fuzz

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:0**
  - Variáveis importadas sem fallback: get_db
  - Variáveis: get_db

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:0**
  - Variáveis importadas sem fallback: UF_LIST
  - Variáveis: UF_LIST

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:0**
  - Variáveis importadas sem fallback: get_excel_entregas, CursorCommands, DevCommands, BaseCommand, ExcelEntregas, get_dev_commands, FileCommands, get_file_commands, create_excel_summary, ExcelFretes, get_excel_faturamento, ExcelFaturamento, ExcelOrchestrator, ExcelPedidos, get_excel_orchestrator, detect_command_type, get_cursor_commands, get_excel_fretes, get_excel_pedidos, format_response_advanced
  - Variáveis: get_excel_entregas, CursorCommands, DevCommands, BaseCommand, ExcelEntregas, get_dev_commands, FileCommands, get_file_commands, create_excel_summary, ExcelFretes, get_excel_faturamento, ExcelFaturamento, ExcelOrchestrator, ExcelPedidos, get_excel_orchestrator, detect_command_type, get_cursor_commands, get_excel_fretes, get_excel_pedidos, format_response_advanced

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/__init__.py:0**
  - Variáveis importadas sem fallback: ExcelFaturamento, ExcelPedidos, ExcelEntregas, get_excel_pedidos, get_excel_fretes, get_excel_entregas, ExcelFretes, get_excel_faturamento
  - Variáveis: ExcelFaturamento, ExcelPedidos, ExcelEntregas, get_excel_pedidos, get_excel_fretes, get_excel_entregas, ExcelFretes, get_excel_faturamento

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:0**
  - Variáveis importadas sem fallback: and_, Workbook, Pedido, Alignment, Font, PatternFill, get_column_letter, or_, EntregaMonitorada, Side, Border, AgendamentoEntrega, func
  - Variáveis: and_, Workbook, Pedido, Alignment, Font, PatternFill, get_column_letter, or_, EntregaMonitorada, Side, Border, AgendamentoEntrega, func

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:0**
  - Variáveis importadas sem fallback: and_, Workbook, Font, PatternFill, get_column_letter, or_, Side, Alignment, RelatorioFaturamentoImportado, Border, func
  - Variáveis: and_, Workbook, Font, PatternFill, get_column_letter, or_, Side, Alignment, RelatorioFaturamentoImportado, Border, func

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:0**
  - Variáveis importadas sem fallback: and_, Workbook, Alignment, Embarque, Font, PatternFill, DespesaExtra, get_column_letter, or_, Transportadora, Side, Border, Frete, func
  - Variáveis: and_, Workbook, Alignment, Embarque, Font, PatternFill, DespesaExtra, get_column_letter, or_, Transportadora, Side, Border, Frete, func

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:0**
  - Variáveis importadas sem fallback: Workbook, Font, PatternFill, get_column_letter, Side, Alignment, Border
  - Variáveis: Workbook, Font, PatternFill, get_column_letter, Side, Alignment, Border

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:0**
  - Variáveis importadas sem fallback: Workbook, get_excel_pedidos, get_excel_fretes, PatternFill, Font, get_excel_entregas, get_excel_faturamento
  - Variáveis: Workbook, get_excel_pedidos, get_excel_fretes, PatternFill, Font, get_excel_entregas, get_excel_faturamento

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/__init__.py:0**
  - Variáveis importadas sem fallback: get_advanced_config, SystemConfig, get_system_config, AdvancedConfig
  - Variáveis: get_advanced_config, SystemConfig, get_system_config, AdvancedConfig

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/__init__.py:0**
  - Variáveis importadas sem fallback: ConversationContext, ConversationManager
  - Variáveis: ConversationContext, ConversationManager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:0**
  - Variáveis importadas sem fallback: Mock
  - Variáveis: Mock

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:0**
  - Variáveis importadas sem fallback: get_all_agent_types, create_entregas_agent, create_pedidos_agent, create_embarques_agent, create_financeiro_agent, get_intelligence_coordinator, get_coordinator_manager, create_fretes_agent, ProcessorCoordinator
  - Variáveis: get_all_agent_types, create_entregas_agent, create_pedidos_agent, create_embarques_agent, create_financeiro_agent, get_intelligence_coordinator, get_coordinator_manager, create_fretes_agent, ProcessorCoordinator

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:0**
  - Variáveis importadas sem fallback: SpecialistAgent, get_intelligence_coordinator, AgentType, ProcessorCoordinator
  - Variáveis: SpecialistAgent, get_intelligence_coordinator, AgentType, ProcessorCoordinator

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:0**
  - Variáveis importadas sem fallback: get_integration_manager
  - Variáveis: get_integration_manager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:0**
  - Variáveis importadas sem fallback: get_adaptive_learning, get_analyzer_manager, get_intelligence_processor
  - Variáveis: get_adaptive_learning, get_analyzer_manager, get_intelligence_processor

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/__init__.py:0**
  - Variáveis importadas sem fallback: ContextEnricher, EnricherManager, SemanticEnricher
  - Variáveis: ContextEnricher, EnricherManager, SemanticEnricher

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/enricher_manager.py:0**
  - Variáveis importadas sem fallback: ContextEnricher, SemanticEnricher
  - Variáveis: ContextEnricher, SemanticEnricher

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:0**
  - Variáveis importadas sem fallback: get_scanning_manager
  - Variáveis: get_scanning_manager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/__init__.py:0**
  - Variáveis importadas sem fallback: get_external_api_integration, get_standalone_integration, get_flask_routes, get_web_integration_adapter, get_standalone_adapter, get_integration_manager, create_standalone_system, get_claude_client, ClaudeAPIClient, StandaloneIntegration, WebFlaskRoutes, ExternalAPIIntegration, create_claude_client, create_integration_routes, WebIntegrationAdapter, is_flask_available, IntegrationManager
  - Variáveis: get_external_api_integration, get_standalone_integration, get_flask_routes, get_web_integration_adapter, get_standalone_adapter, get_integration_manager, create_standalone_system, get_claude_client, ClaudeAPIClient, StandaloneIntegration, WebFlaskRoutes, ExternalAPIIntegration, create_claude_client, create_integration_routes, WebIntegrationAdapter, is_flask_available, IntegrationManager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:0**
  - Variáveis importadas sem fallback: IntegrationManager
  - Variáveis: IntegrationManager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/integration_manager.py:0**
  - Variáveis importadas sem fallback: get_orchestrator_manager
  - Variáveis: get_orchestrator_manager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:0**
  - Variáveis importadas sem fallback: get_external_api_integration, IntegrationManager
  - Variáveis: get_external_api_integration, IntegrationManager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:0**
  - Variáveis importadas sem fallback: get_feedback_processor, get_external_api_integration, get_contextprocessor, IntegrationManager
  - Variáveis: get_feedback_processor, get_external_api_integration, get_contextprocessor, IntegrationManager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/__init__.py:0**
  - Variáveis importadas sem fallback: AdaptiveLearning, HumanInLoopLearning, PatternLearner, LearningCore, FeedbackProcessor, LifelongLearningSystem
  - Variáveis: AdaptiveLearning, HumanInLoopLearning, PatternLearner, LearningCore, FeedbackProcessor, LifelongLearningSystem

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:0**
  - Variáveis importadas sem fallback: text, get_db
  - Variáveis: text, get_db

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:0**
  - Variáveis importadas sem fallback: text, get_db
  - Variáveis: text, get_db

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/__init__.py:0**
  - Variáveis importadas sem fallback: get_fretes_loader, get_faturamento_loader, get_loader_manager, DatabaseLoader, ContextLoader, get_agendamentos_loader, get_embarques_loader, get_entregas_loader, get_datamanager, get_pedidos_loader
  - Variáveis: get_fretes_loader, get_faturamento_loader, get_loader_manager, DatabaseLoader, ContextLoader, get_agendamentos_loader, get_embarques_loader, get_entregas_loader, get_datamanager, get_pedidos_loader

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:0**
  - Variáveis importadas sem fallback: create_engine, sessionmaker
  - Variáveis: create_engine, sessionmaker

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:0**
  - Variáveis importadas sem fallback: get_app, current_app, create_app, EntregaMonitorada, db, text, datetime, timedelta
  - Variáveis: get_app, current_app, create_app, EntregaMonitorada, db, text, datetime, timedelta

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:0**
  - Variáveis importadas sem fallback: get_fretes_loader, get_faturamento_loader, get_agendamentos_loader, get_embarques_loader, get_entregas_loader, get_pedidos_loader
  - Variáveis: get_fretes_loader, get_faturamento_loader, get_agendamentos_loader, get_embarques_loader, get_entregas_loader, get_pedidos_loader

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/__init__.py:0**
  - Variáveis importadas sem fallback: get_context_mapper, get_field_mapper, get_semantic_mapper, get_mapper_manager, get_query_mapper, is_flask_available
  - Variáveis: get_context_mapper, get_field_mapper, get_semantic_mapper, get_mapper_manager, get_query_mapper, is_flask_available

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:0**
  - Variáveis importadas sem fallback: fuzz
  - Variáveis: fuzz

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:0**
  - Variáveis importadas sem fallback: get_database_manager
  - Variáveis: get_database_manager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/__init__.py:0**
  - Variáveis importadas sem fallback: SystemMemory, KnowledgeMemory, ContextMemory, SessionMemory, ConversationMemory, MemoryManager
  - Variáveis: SystemMemory, KnowledgeMemory, ContextMemory, SessionMemory, ConversationMemory, MemoryManager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:0**
  - Variáveis importadas sem fallback: get_current_user, Mock
  - Variáveis: get_current_user, Mock

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:0**
  - Variáveis importadas sem fallback: current_app, text, get_db
  - Variáveis: current_app, text, get_db

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:0**
  - Variáveis importadas sem fallback: Mock
  - Variáveis: Mock

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/__init__.py:0**
  - Variáveis importadas sem fallback: WorkflowOrchestrator, get_orchestration_status, get_session_orchestrator, orchestrate_system_operation, SessionOrchestrator, MainOrchestrator, get_orchestrator_manager, OrchestratorManager
  - Variáveis: WorkflowOrchestrator, get_orchestration_status, get_session_orchestrator, orchestrate_system_operation, SessionOrchestrator, MainOrchestrator, get_orchestrator_manager, OrchestratorManager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:0**
  - Variáveis importadas sem fallback: get_suggestions_manager, get_processormanager, get_context_enricher, get_enricher_manager, get_analyzer_manager, get_auto_command_processor, get_context_processor, get_semantic_enricher, get_loader_manager, get_validator_manager, BaseCommand, get_memory_manager, get_mapper_manager, get_responseprocessor, get_coordinator_manager, get_toolsmanager, get_learning_core, get_conversation_manager, get_provider_manager, get_security_guard, get_scanning_manager
  - Variáveis: get_suggestions_manager, get_processormanager, get_context_enricher, get_enricher_manager, get_analyzer_manager, get_auto_command_processor, get_context_processor, get_semantic_enricher, get_loader_manager, get_validator_manager, BaseCommand, get_memory_manager, get_mapper_manager, get_responseprocessor, get_coordinator_manager, get_toolsmanager, get_learning_core, get_conversation_manager, get_provider_manager, get_security_guard, get_scanning_manager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:0**
  - Variáveis importadas sem fallback: WorkflowOrchestrator, get_session_orchestrator, SessionOrchestrator, SessionPriority, MainOrchestrator, get_security_guard
  - Variáveis: WorkflowOrchestrator, get_session_orchestrator, SessionOrchestrator, SessionPriority, MainOrchestrator, get_security_guard

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:0**
  - Variáveis importadas sem fallback: get_learning_core, ResponseProcessor, get_conversation_manager, get_security_guard, get_main_orchestrator
  - Variáveis: get_learning_core, ResponseProcessor, get_conversation_manager, get_security_guard, get_main_orchestrator

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/__init__.py:0**
  - Variáveis importadas sem fallback: BaseProcessor, get_context_processor, get_intelligence_processor, get_query_processor, ContextProcessor, get_data_processor, IntelligenceProcessor, QueryProcessor, DataProcessor
  - Variáveis: BaseProcessor, get_context_processor, get_intelligence_processor, get_query_processor, ContextProcessor, get_data_processor, IntelligenceProcessor, QueryProcessor, DataProcessor

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:0**
  - Variáveis importadas sem fallback: ClaudeAIConfig, AdvancedConfig, get_model, get_db
  - Variáveis: ClaudeAIConfig, AdvancedConfig, get_model, get_db

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:0**
  - Variáveis importadas sem fallback: ClaudeAIConfig, get_data_provider, get_responseutils, AdvancedConfig, datetime, timedelta
  - Variáveis: ClaudeAIConfig, get_data_provider, get_responseutils, AdvancedConfig, datetime, timedelta

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/__init__.py:0**
  - Variáveis importadas sem fallback: provide_data, is_flask_available, ProviderRequest, get_data_provider, get_context_provider, provide_context, get_provider_manager
  - Variáveis: provide_data, is_flask_available, ProviderRequest, get_data_provider, get_context_provider, provide_context, get_provider_manager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:0**
  - Variáveis importadas sem fallback: get_current_user, get_db, get_loader_manager, get_model, Mock, intelligent_cache, PendenciaFinanceiraNF
  - Variáveis: get_current_user, get_db, get_loader_manager, get_model, Mock, intelligent_cache, PendenciaFinanceiraNF

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:0**
  - Variáveis importadas sem fallback: ContextProvider, get_data_provider
  - Variáveis: ContextProvider, get_data_provider

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/__init__.py:0**
  - Variáveis importadas sem fallback: DatabaseScanner, ReadmeScanner, StructureScanner, FileScanner, ProjectScanner, ScanningManager, CodeScanner, DatabaseManager, is_flask_available
  - Variáveis: DatabaseScanner, ReadmeScanner, StructureScanner, FileScanner, ProjectScanner, ScanningManager, CodeScanner, DatabaseManager, is_flask_available

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:0**
  - Variáveis importadas sem fallback: DatabaseConnection, MetadataScanner
  - Variáveis: DatabaseConnection, MetadataScanner

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:0**
  - Variáveis importadas sem fallback: urlparse, quote, urlunparse, get_db
  - Variáveis: urlparse, quote, urlunparse, get_db

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:0**
  - Variáveis importadas sem fallback: DatabaseManager
  - Variáveis: DatabaseManager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/__init__.py:0**
  - Variáveis importadas sem fallback: get_security_guard, is_flask_available
  - Variáveis: get_security_guard, is_flask_available

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:0**
  - Variáveis importadas sem fallback: get_current_user, Mock, has_request_context
  - Variáveis: get_current_user, Mock, has_request_context

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/__init__.py:0**
  - Variáveis importadas sem fallback: SuggestionsEngine, get_suggestions_manager, SuggestionsManager, get_suggestions_engine
  - Variáveis: SuggestionsEngine, get_suggestions_manager, SuggestionsManager, get_suggestions_engine

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:0**
  - Variáveis importadas sem fallback: DataAnalyzer
  - Variáveis: DataAnalyzer

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:0**
  - Variáveis importadas sem fallback: get_main_orchestrator
  - Variáveis: get_main_orchestrator

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:0**
  - Variáveis importadas sem fallback: get_session_orchestrator, get_main_orchestrator
  - Variáveis: get_session_orchestrator, get_main_orchestrator

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/__init__.py:0**
  - Variáveis importadas sem fallback: AgentResponse, FlaskContextWrapper, ValidationResult, get_validation_utils, ResponseUtils, get_config, ExternalAPIIntegration, ScannersCache, FlaskFallback, get_datamanager, ProcessorRegistry, get_current_user, get_db, AgentType, BaseOrchestrator, BaseValidationUtils, get_model, get_flask_fallback, is_flask_available, UtilsManager, BaseProcessor, BaseContextManager, get_app, OperationRecord, get_utilsmanager, DataManager
  - Variáveis: AgentResponse, FlaskContextWrapper, ValidationResult, get_validation_utils, ResponseUtils, get_config, ExternalAPIIntegration, ScannersCache, FlaskFallback, get_datamanager, ProcessorRegistry, get_current_user, get_db, AgentType, BaseOrchestrator, BaseValidationUtils, get_model, get_flask_fallback, is_flask_available, UtilsManager, BaseProcessor, BaseContextManager, get_app, OperationRecord, get_utilsmanager, DataManager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:0**
  - Variáveis importadas sem fallback: ClaudeAIConfig, GrupoEmpresarialDetector, AdvancedConfig, current_app
  - Variáveis: ClaudeAIConfig, GrupoEmpresarialDetector, AdvancedConfig, current_app

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/data_manager.py:0**
  - Variáveis importadas sem fallback: DataProvider
  - Variáveis: DataProvider

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_context_wrapper.py:0**
  - Variáveis importadas sem fallback: request, current_app, db
  - Variáveis: request, current_app, db

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:0**
  - Variáveis importadas sem fallback: EmbarqueItem, current_app, Flask, Pedido, Embarque, Usuario, current_user, create_app, Transportadora, EntregaMonitorada, db, RelatorioFaturamentoImportado, Frete
  - Variáveis: EmbarqueItem, current_app, Flask, Pedido, Embarque, Usuario, current_user, create_app, Transportadora, EntregaMonitorada, db, RelatorioFaturamentoImportado, Frete

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/legacy_compatibility.py:0**
  - Variáveis importadas sem fallback: processar_com_claude_real, get_external_api_integration, get_nlp_enhanced_analyzer, ExternalAPIIntegration
  - Variáveis: processar_com_claude_real, get_external_api_integration, get_nlp_enhanced_analyzer, ExternalAPIIntegration

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:0**
  - Variáveis importadas sem fallback: ReadmeScanner, DatabaseScanner
  - Variáveis: ReadmeScanner, DatabaseScanner

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/utils_manager.py:0**
  - Variáveis importadas sem fallback: FlaskContextWrapper
  - Variáveis: FlaskContextWrapper

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/__init__.py:0**
  - Variáveis importadas sem fallback: CriticAgent, ValidatorManager, ValidationUtils, StructuralAI, SemanticValidator
  - Variáveis: CriticAgent, ValidatorManager, ValidationUtils, StructuralAI, SemanticValidator

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:0**
  - Variáveis importadas sem fallback: get_current_user, get_claude_integration, get_db, get_model, Mock, intelligent_cache, PendenciaFinanceiraNF
  - Variáveis: get_current_user, get_claude_integration, get_db, get_model, Mock, intelligent_cache, PendenciaFinanceiraNF

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:0**
  - Variáveis importadas sem fallback: get_scanning_manager
  - Variáveis: get_scanning_manager

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:0**
  - Variáveis importadas sem fallback: StructuralAI, CriticAgent, ValidationUtils, SemanticValidator
  - Variáveis: StructuralAI, CriticAgent, ValidationUtils, SemanticValidator

### REDIS SEM VERIFICACAO (44 ocorrências)

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:214**
  - Uso de intelligent_cache.get sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:216**
  - Uso de redis_cache.get sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:214**
  - Uso de intelligent_cache.get sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:216**
  - Uso de redis_cache.get sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:227**
  - Uso de intelligent_cache.set sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:230**
  - Uso de intelligent_cache.set sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:227**
  - Uso de intelligent_cache.set sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:230**
  - Uso de intelligent_cache.set sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:233**
  - Uso de redis_cache.set sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:227**
  - Uso de intelligent_cache.set sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:230**
  - Uso de intelligent_cache.set sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:227**
  - Uso de intelligent_cache.set sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:230**
  - Uso de intelligent_cache.set sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:233**
  - Uso de redis_cache.set sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:276**
  - Uso de redis_cache._gerar_chave sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:285**
  - Uso de redis_cache.get sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:358**
  - Uso de redis_cache.cache_entregas_cliente sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:364**
  - Uso de entregas_cache.get sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:358**
  - Uso de redis_cache.cache_entregas_cliente sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:364**
  - Uso de entregas_cache.get sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:429**
  - Uso de redis_cache.cache_entregas_cliente sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:435**
  - Uso de entregas_cache.get sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:444**
  - Uso de redis_cache.cache_entregas_cliente sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:471**
  - Uso de redis_cache.cache_estatisticas_cliente sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:478**
  - Uso de redis_cache.cache_estatisticas_cliente sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:509**
  - Uso de redis_cache.set sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:358**
  - Uso de redis_cache.cache_entregas_cliente sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:364**
  - Uso de entregas_cache.get sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:358**
  - Uso de redis_cache.cache_entregas_cliente sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:364**
  - Uso de entregas_cache.get sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:429**
  - Uso de redis_cache.cache_entregas_cliente sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:435**
  - Uso de entregas_cache.get sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:444**
  - Uso de redis_cache.cache_entregas_cliente sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:471**
  - Uso de redis_cache.cache_estatisticas_cliente sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:478**
  - Uso de redis_cache.cache_estatisticas_cliente sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:509**
  - Uso de redis_cache.set sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:68**
  - Uso de redis_cache.set sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:68**
  - Uso de redis_cache.set sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:98**
  - Uso de redis_cache.get sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:98**
  - Uso de redis_cache.get sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:195**
  - Uso de redis_cache.delete sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:195**
  - Uso de redis_cache.delete sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:324**
  - Uso de cache_obj.set sem verificar disponibilidade

- **/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:324**
  - Uso de cache_obj.set sem verificar disponibilidade


## 🔧 RECOMENDAÇÕES

1. **Imports condicionais**: Sempre adicionar fallback no bloco except
2. **Redis/Cache**: Verificar disponibilidade antes de usar
3. **Modelos SQLAlchemy**: Garantir contexto Flask ou usar with app.app_context()
4. **Fallbacks**: Definir valores padrão para todas as dependências opcionais
