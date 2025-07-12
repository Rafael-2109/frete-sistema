# 🔍 RELATÓRIO DE ATRIBUTOS INEXISTENTES

**Data**: 2025-07-12T18:11:53.050249
**Arquivos analisados**: 175
**Total de acessos**: 12702
**Classes definidas**: 196
**Atributos suspeitos**: 6939

## 📋 ATRIBUTOS POTENCIALMENTE INEXISTENTES

### 🔍 Objeto: `AgentType`

#### `AgentType.FRETES` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:125 (em CoordinatorManager._load_specialist_coordinator)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/specialist_agents.py:46 (em SpecialistAgent.__new__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/fretes_agent.py:22 (em FretesAgent.__init__)
```

#### `AgentType.ENTREGAS` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/specialist_agents.py:45 (em SpecialistAgent.__new__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:21 (em EntregasAgent.__init__)
```

#### `AgentType.PEDIDOS` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/specialist_agents.py:47 (em SpecialistAgent.__new__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/pedidos_agent.py:22 (em PedidosAgent.__init__)
```

#### `AgentType.EMBARQUES` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/specialist_agents.py:48 (em SpecialistAgent.__new__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/embarques_agent.py:22 (em EmbarquesAgent.__init__)
```

#### `AgentType.FINANCEIRO` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/specialist_agents.py:49 (em SpecialistAgent.__new__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/financeiro_agent.py:22 (em FinanceiroAgent.__init__)
```

### 🔍 Objeto: `ClaudeAIConfig`

#### `ClaudeAIConfig.get_claude_params` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:285 (em ClaudeAIMetrics.get_ai_technical_metrics)
```

#### `ClaudeAIConfig.REQUEST_TIMEOUT_SECONDS` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:301 (em ClaudeAIMetrics.get_ai_technical_metrics)
```

#### `ClaudeAIConfig.MAX_CONCURRENT_REQUESTS` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:302 (em ClaudeAIMetrics.get_ai_technical_metrics)
```

#### `ClaudeAIConfig.CACHE_TTL_SECONDS` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:304 (em ClaudeAIMetrics.get_ai_technical_metrics)
```

#### `ClaudeAIConfig.get_anthropic_api_key` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:318 (em ClaudeAIMetrics.get_ai_technical_metrics)
```

### 🔍 Objeto: `ClaudeAPIClient`

#### `ClaudeAPIClient.from_environment` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:214 (em ExternalAPIIntegration._initialize_clients)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:463 (em module.get_claude_client)
```

#### `ClaudeAPIClient.from_mode` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:480 (em module.create_claude_client)
```

### 🔍 Objeto: `Embarque`

#### `Embarque.data_embarque` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:164 (em DataProvider._get_embarques_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:166 (em DataProvider._get_embarques_data)
```

#### `Embarque.status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:162 (em DataProvider._get_embarques_data)
```

### 🔍 Objeto: `EntregaMonitorada`

#### `EntregaMonitorada.cliente` (13 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:191 (em ContextLoader._carregar_entregas_banco)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:484 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:486 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:487 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:545 (em ContextLoader._carregar_todos_clientes_sistema)
  ... e mais 8 ocorrências
```

#### `EntregaMonitorada.data_embarque` (10 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:149 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:150 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:186 (em ContextLoader._carregar_entregas_banco)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:194 (em ContextLoader._carregar_entregas_banco)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:547 (em ContextLoader._carregar_todos_clientes_sistema)
  ... e mais 5 ocorrências
```

#### `EntregaMonitorada.cliente.ilike` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:191 (em ContextLoader._carregar_entregas_banco)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:70 (em AgendamentosLoader._build_agendamentos_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:108 (em DataProvider._get_entregas_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:147 (em ValidationUtils._calcular_estatisticas_especificas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:153 (em ValidationUtils._calcular_estatisticas_especificas)
  ... e mais 3 ocorrências
```

#### `EntregaMonitorada.data_entrega_prevista` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:141 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:153 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:154 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:160 (em ExcelEntregas._buscar_dados_entregas)
```

#### `EntregaMonitorada.entregue` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:133 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:135 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:140 (em ExcelEntregas._buscar_dados_entregas)
```

#### `EntregaMonitorada.status_finalizacao` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:110 (em DataProvider._get_entregas_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:166 (em ValidationUtils._calcular_estatisticas_especificas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:167 (em ValidationUtils._calcular_estatisticas_especificas)
```

#### `EntregaMonitorada.nome_cliente.ilike` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:121 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:281 (em ContextProcessor._carregar_dados_entregas)
```

#### `EntregaMonitorada.nome_cliente` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:121 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:281 (em ContextProcessor._carregar_dados_entregas)
```

#### `EntregaMonitorada.uf_destino` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:128 (em ExcelEntregas._buscar_dados_entregas)
```

#### `EntregaMonitorada.data_entrega_prevista.desc` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:160 (em ExcelEntregas._buscar_dados_entregas)
```

#### `EntregaMonitorada.id.desc` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:160 (em ExcelEntregas._buscar_dados_entregas)
```

#### `EntregaMonitorada.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:160 (em ExcelEntregas._buscar_dados_entregas)
```

#### `EntregaMonitorada.data_embarque.desc` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:194 (em ContextLoader._carregar_entregas_banco)
```

#### `EntregaMonitorada.data_embarque.is_` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:135 (em ValidationUtils._calcular_estatisticas_especificas)
```

#### `EntregaMonitorada.vendedor` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:163 (em ValidationUtils._calcular_estatisticas_especificas)
```

#### `EntregaMonitorada.status_finalizacao.in_` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:167 (em ValidationUtils._calcular_estatisticas_especificas)
```

### 🔍 Objeto: `FeedbackSeverity`

#### `FeedbackSeverity.CRITICAL` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:101 (em HumanInLoopLearning.capture_feedback)
```

### 🔍 Objeto: `FeedbackType`

#### `FeedbackType.NEGATIVE` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:147 (em HumanInLoopLearning._analyze_feedback_patterns)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:398 (em HumanInLoopLearning._calculate_satisfaction_score)
```

#### `FeedbackType.CORRECTION` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:147 (em HumanInLoopLearning._analyze_feedback_patterns)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:397 (em HumanInLoopLearning._calculate_satisfaction_score)
```

#### `FeedbackType.POSITIVE` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:395 (em HumanInLoopLearning._calculate_satisfaction_score)
```

#### `FeedbackType.IMPROVEMENT` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:396 (em HumanInLoopLearning._calculate_satisfaction_score)
```

#### `FeedbackType.BUG_REPORT` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:399 (em HumanInLoopLearning._calculate_satisfaction_score)
```

### 🔍 Objeto: `FieldType`

#### `FieldType.STRING` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:147 (em FieldMapper.create_pedidos_mapping)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:148 (em FieldMapper.create_pedidos_mapping)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:151 (em FieldMapper.create_pedidos_mapping)
```

#### `FieldType.FLOAT` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:149 (em FieldMapper.create_pedidos_mapping)
```

#### `FieldType.DATE` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:150 (em FieldMapper.create_pedidos_mapping)
```

### 🔍 Objeto: `Frete`

#### `Frete.data_embarque` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:142 (em ExcelFretes._buscar_dados_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:143 (em ExcelFretes._buscar_dados_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:151 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.data_cotacao` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:319 (em ContextProcessor._carregar_dados_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:241 (em DataProvider._get_fretes_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:243 (em DataProvider._get_fretes_data)
```

#### `Frete.nome_cliente.ilike` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:123 (em ExcelFretes._buscar_dados_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:314 (em ContextProcessor._carregar_dados_fretes)
```

#### `Frete.nome_cliente` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:123 (em ExcelFretes._buscar_dados_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:314 (em ContextProcessor._carregar_dados_fretes)
```

#### `Frete.numero_cte` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:135 (em ExcelFretes._buscar_dados_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:137 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.razao_social_cliente.ilike` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:124 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.razao_social_cliente` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:124 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.uf_destino` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:130 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.numero_cte.is_` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:135 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.numero_cte.isnot` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:137 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.valor_cotado` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:148 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.data_embarque.desc` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:151 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.id.desc` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:151 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:151 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.transportadora.ilike` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:237 (em DataProvider._get_fretes_data)
```

#### `Frete.transportadora` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:237 (em DataProvider._get_fretes_data)
```

#### `Frete.status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:239 (em DataProvider._get_fretes_data)
```

### 🔍 Objeto: `IMPORT_FIXES`

#### `IMPORT_FIXES.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:155 (em ImportFixer._find_fix)
```

### 🔍 Objeto: `OrchestrationMode`

#### `OrchestrationMode.INTELLIGENT` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:105 (em module.teste_sistema_basico)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:183 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:229 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:803 (em module.top-level)
```

#### `OrchestrationMode.SEQUENTIAL` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:794 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:817 (em MainOrchestrator.top-level)
```

#### `OrchestrationMode.PARALLEL` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:819 (em MainOrchestrator.top-level)
```

#### `OrchestrationMode.ADAPTIVE` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:821 (em MainOrchestrator.top-level)
```

### 🔍 Objeto: `OrchestratorType`

#### `OrchestratorType.MAIN` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:127 (em OrchestratorManager._initialize_orchestrators)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:450 (em OrchestratorManager._detect_appropriate_orchestrator)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:452 (em OrchestratorManager._detect_appropriate_orchestrator)
```

#### `OrchestratorType.SESSION` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:134 (em OrchestratorManager._initialize_orchestrators)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:433 (em OrchestratorManager._detect_appropriate_orchestrator)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:478 (em OrchestratorManager.top-level)
```

#### `OrchestratorType.WORKFLOW` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:141 (em OrchestratorManager._initialize_orchestrators)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:434 (em OrchestratorManager._detect_appropriate_orchestrator)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:480 (em OrchestratorManager.top-level)
```

### 🔍 Objeto: `Path()`

#### `Path().parent` (17 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:271 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:230 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:316 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:14 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:22 (em module.top-level)
  ... e mais 12 ocorrências
```

#### `Path().parent.parent` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:22 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_status_completo.py:11 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:29 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:381 (em module.get_code_scanner)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:381 (em module.get_file_scanner)
  ... e mais 3 ocorrências
```

#### `Path().parts` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:154 (em module.contar_linhas_codigo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:189 (em module.verificar_modulos_especiais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:54 (em module.categorizar_todos_modulos)
```

#### `Path().parent.parent.parent` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:22 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_status_completo.py:11 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:29 (em module.top-level)
```

#### `Path().resolve` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:23 (em DetectorModulosOrfaos.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:23 (em module.top-level)
```

#### `Path().exists` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:384 (em module.main)
```

#### `Path().relative_to` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:236 (em UninitializedVariableFinder.generate_report)
```

#### `Path().resolve().parent.parent.parent` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:23 (em module.top-level)
```

#### `Path().resolve().parent.parent` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:23 (em module.top-level)
```

#### `Path().resolve().parent` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:23 (em module.top-level)
```

#### `Path().parent.parent.parent.parent` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:29 (em module.top-level)
```

### 🔍 Objeto: `Pedido`

#### `Pedido.data_pedido` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:184 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:185 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:190 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:191 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:198 (em ExcelPedidos._buscar_dados_pedidos)
  ... e mais 3 ocorrências
```

#### `Pedido.nf_cd` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:145 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:151 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:159 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:164 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:171 (em ExcelPedidos._buscar_dados_pedidos)
  ... e mais 1 ocorrências
```

#### `Pedido.raz_social_red` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:132 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:492 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:494 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:495 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:347 (em ContextProcessor._carregar_dados_pedidos)
```

#### `Pedido.nf` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:149 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:150 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:158 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:158 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.data_embarque` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:157 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:163 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:170 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.raz_social_red.ilike` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:132 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:347 (em ContextProcessor._carregar_dados_pedidos)
```

#### `Pedido.data_embarque.isnot` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:157 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:163 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.cotacao_id` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:169 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:176 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.nome_cliente.ilike` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:122 (em ExcelEntregas._buscar_dados_entregas)
```

#### `Pedido.nome_cliente` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:122 (em ExcelEntregas._buscar_dados_entregas)
```

#### `Pedido.cnpj_cpf.ilike` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:133 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.cnpj_cpf` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:133 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.cod_uf` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:139 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.nf.isnot` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:149 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.nf.is_` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:158 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.cotacao_id.isnot` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:169 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.data_embarque.is_` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:170 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.cotacao_id.is_` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:176 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.valor_saldo_total` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:195 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.data_pedido.desc` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:198 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.id.desc` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:198 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:198 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.cliente.ilike` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:135 (em DataProvider._get_pedidos_data)
```

#### `Pedido.cliente` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:135 (em DataProvider._get_pedidos_data)
```

#### `Pedido.status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:137 (em DataProvider._get_pedidos_data)
```

### 🔍 Objeto: `PendenciaFinanceiraNF`

#### `PendenciaFinanceiraNF.nome_cliente.ilike` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:380 (em ContextProcessor._carregar_dados_financeiro)
```

#### `PendenciaFinanceiraNF.nome_cliente` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:380 (em ContextProcessor._carregar_dados_financeiro)
```

### 🔍 Objeto: `QueryType`

#### `QueryType.SQL` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:53 (em QueryMapper._setup_default_mappings)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:60 (em QueryMapper._setup_default_mappings)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:79 (em QueryMapper.map_query)
```

#### `QueryType.NATURAL_LANGUAGE` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:52 (em QueryMapper._setup_default_mappings)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:59 (em QueryMapper._setup_default_mappings)
```

### 🔍 Objeto: `RelatorioFaturamentoImportado`

#### `RelatorioFaturamentoImportado.nome_cliente` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:119 (em ExcelFaturamento._buscar_dados_faturamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:475 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:478 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:479 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:187 (em DataProvider._get_faturamento_data)
```

#### `RelatorioFaturamentoImportado.data_fatura` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:124 (em ExcelFaturamento._buscar_dados_faturamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:125 (em ExcelFaturamento._buscar_dados_faturamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:133 (em ExcelFaturamento._buscar_dados_faturamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:189 (em DataProvider._get_faturamento_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:191 (em DataProvider._get_faturamento_data)
```

#### `RelatorioFaturamentoImportado.nome_cliente.ilike` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:119 (em ExcelFaturamento._buscar_dados_faturamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:187 (em DataProvider._get_faturamento_data)
```

#### `RelatorioFaturamentoImportado.valor_total` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:130 (em ExcelFaturamento._buscar_dados_faturamento)
```

#### `RelatorioFaturamentoImportado.data_fatura.desc` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:133 (em ExcelFaturamento._buscar_dados_faturamento)
```

#### `RelatorioFaturamentoImportado.id.desc` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:133 (em ExcelFaturamento._buscar_dados_faturamento)
```

#### `RelatorioFaturamentoImportado.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:133 (em ExcelFaturamento._buscar_dados_faturamento)
```

#### `RelatorioFaturamentoImportado.cnpj_cliente` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:476 (em ContextLoader._carregar_todos_clientes_sistema)
```

### 🔍 Objeto: `SessionPriority`

#### `SessionPriority.NORMAL` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:505 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:93 (em SessionContext.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:219 (em SessionOrchestrator.create_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:1092 (em module.create_ai_session)
```

#### `SessionPriority.HIGH` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:499 (em OrchestratorManager.top-level)
```

#### `SessionPriority.LOW` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:501 (em OrchestratorManager.top-level)
```

#### `SessionPriority.CRITICAL` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:503 (em OrchestratorManager.top-level)
```

### 🔍 Objeto: `SessionStatus`

#### `SessionStatus.ACTIVE` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:108 (em SessionContext.is_active)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:314 (em SessionOrchestrator.initialize_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:386 (em SessionOrchestrator.execute_session_workflow)
```

#### `SessionStatus.PROCESSING` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:108 (em SessionContext.is_active)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:362 (em SessionOrchestrator.execute_session_workflow)
```

#### `SessionStatus.FAILED` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:331 (em SessionOrchestrator.initialize_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:403 (em SessionOrchestrator.execute_session_workflow)
```

#### `SessionStatus.CREATED` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:92 (em SessionContext.top-level)
```

#### `SessionStatus.WAITING_INPUT` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:108 (em SessionContext.is_active)
```

#### `SessionStatus.INITIALIZING` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:303 (em SessionOrchestrator.initialize_session)
```

#### `SessionStatus.COMPLETED` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:553 (em SessionOrchestrator.complete_session)
```

#### `SessionStatus.TERMINATED` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:601 (em SessionOrchestrator.terminate_session)
```

### 🔍 Objeto: `Transportadora`

#### `Transportadora.razao_social.ilike` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:212 (em DataProvider._get_transportadoras_data)
```

#### `Transportadora.razao_social` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:212 (em DataProvider._get_transportadoras_data)
```

#### `Transportadora.cidade.ilike` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:214 (em DataProvider._get_transportadoras_data)
```

#### `Transportadora.cidade` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:214 (em DataProvider._get_transportadoras_data)
```

#### `Transportadora.uf` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:216 (em DataProvider._get_transportadoras_data)
```

### 🔍 Objeto: `__all__`

#### `__all__.extend` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:328 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:335 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:338 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:341 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:344 (em module.top-level)
  ... e mais 2 ocorrências
```

### 🔍 Objeto: `__import__()`

#### `__import__().datetime.now` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:347 (em module.export_config)
```

#### `__import__().datetime` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:347 (em module.export_config)
```

### 🔍 Objeto: `_cache_store`

#### `_cache_store.keys` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/performance_cache.py:54 (em module.cached_result)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/performance_cache.py:119 (em module.get_cache_stats)
```

#### `_cache_store.values` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/performance_cache.py:120 (em module.get_cache_stats)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/performance_cache.py:121 (em module.get_cache_stats)
```

### 🔍 Objeto: `_claude_ai_instance`

#### `_claude_ai_instance.initialize_system` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:336 (em module.get_claude_ai_instance)
```

### 🔍 Objeto: `_commands_registry`

#### `_commands_registry.discover_commands` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:165 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:240 (em module.get_available_commands)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:316 (em module.reset_commands_cache)
```

#### `_commands_registry.get_available_commands` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:241 (em module.get_available_commands)
```

#### `_commands_registry.get_status_report` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:290 (em module.get_commands_info)
```

### 🔍 Objeto: `_components`

#### `_components.get` (28 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/__init__.py:35 (em module.get_conversation_manager)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/__init__.py:49 (em module.get_conversation_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/__init__.py:34 (em module.get_semantic_enricher)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/__init__.py:48 (em module.get_context_enricher)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/__init__.py:63 (em module.get_learning_core)
  ... e mais 23 ocorrências
```

#### `_components.keys` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/__init__.py:165 (em module.get_system_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/__init__.py:190 (em module.diagnose_orchestrator_module)
```

### 🔍 Objeto: `_field_mapper`

#### `_field_mapper.create_pedidos_mapping` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:170 (em module.get_field_mapper)
```

### 🔍 Objeto: `_global_instances`

#### `_global_instances.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/__init__.py:293 (em module.get_global_instance)
```

### 🔍 Objeto: `acao`

#### `acao.action_type` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:156 (em FeedbackProcessor.processar_feedback_completo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:297 (em FeedbackProcessor.aplicar_acao_corretiva)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:300 (em FeedbackProcessor.aplicar_acao_corretiva)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:303 (em FeedbackProcessor.aplicar_acao_corretiva)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:306 (em FeedbackProcessor.aplicar_acao_corretiva)
  ... e mais 2 ocorrências
```

#### `acao.description` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:158 (em FeedbackProcessor.processar_feedback_completo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:479 (em FeedbackProcessor._aplicar_update_mapping)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:485 (em FeedbackProcessor._aplicar_improve_search)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:491 (em FeedbackProcessor._aplicar_enhance_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:497 (em FeedbackProcessor._aplicar_adjust_parameters)
```

#### `acao.confidence` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:152 (em FeedbackProcessor.processar_feedback_completo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:159 (em FeedbackProcessor.processar_feedback_completo)
```

#### `acao.target_component` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:157 (em FeedbackProcessor.processar_feedback_completo)
```

### 🔍 Objeto: `acoes`

#### `acoes.append` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:299 (em DetectorModulosOrfaos.sugerir_acoes_corretivas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:406 (em FeedbackProcessor._gerar_acoes_correcao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:421 (em FeedbackProcessor._gerar_acoes_melhoria)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:436 (em FeedbackProcessor._gerar_acoes_clarificacao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:450 (em FeedbackProcessor._gerar_acoes_mapeamento)
  ... e mais 1 ocorrências
```

#### `acoes.extend` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:265 (em FeedbackProcessor.extrair_acoes_corretivas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:268 (em FeedbackProcessor.extrair_acoes_corretivas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:271 (em FeedbackProcessor.extrair_acoes_corretivas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:275 (em FeedbackProcessor.extrair_acoes_corretivas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:278 (em FeedbackProcessor.extrair_acoes_corretivas)
  ... e mais 1 ocorrências
```

#### `acoes.sort` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:304 (em DetectorModulosOrfaos.sugerir_acoes_corretivas)
```

### 🔍 Objeto: `active_list`

#### `active_list.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:281 (em ConversationManager.get_active_conversations)
```

### 🔍 Objeto: `active_sessions`

#### `active_sessions.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:222 (em ContextMemory.get_active_sessions)
```

### 🔍 Objeto: `adaptations`

#### `adaptations.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:411 (em AdaptiveLearning._apply_adaptations)
```

### 🔍 Objeto: `adjustments`

#### `adjustments.append` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:518 (em AdaptiveLearning._handle_negative_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:522 (em AdaptiveLearning._handle_negative_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:533 (em AdaptiveLearning._handle_positive_feedback)
```

### 🔍 Objeto: `advanced_config`

#### `advanced_config.get` (10 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:168 (em module.get_config)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:292 (em ClaudeAIMetrics.get_ai_technical_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:295 (em ClaudeAIMetrics.get_ai_technical_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:296 (em ClaudeAIMetrics.get_ai_technical_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:309 (em ClaudeAIMetrics.get_ai_technical_metrics)
  ... e mais 5 ocorrências
```

#### `advanced_config.set` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:220 (em module.set_config)
```

### 🔍 Objeto: `agent`

#### `agent.agent_type` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:155 (em ValidadorSistemaReal._test_domain_agents)
```

#### `agent.process_query` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:261 (em CoordinatorManager._process_with_coordinator)
```

### 🔍 Objeto: `agent_classes`

#### `agent_classes.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/specialist_agents.py:52 (em SpecialistAgent.__new__)
```

### 🔍 Objeto: `agent_name`

#### `agent_name.value` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:80 (em SmartBaseAgent._conectar_integration_manager)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:90 (em SmartBaseAgent._conectar_integration_manager)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:99 (em SmartBaseAgent._conectar_integration_manager)
```

### 🔍 Objeto: `aggregations`

#### `aggregations.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:267 (em DataProcessor.aggregate_data)
```

### 🔍 Objeto: `ai_response`

#### `ai_response.lower` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:211 (em ConversationContext.extract_metadata)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:219 (em ConversationContext.extract_metadata)
```

### 🔍 Objeto: `alias`

#### `alias.asname` (10 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:30 (em MethodCallVisitor.visit_Import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:30 (em MethodCallVisitor.visit_Import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:37 (em MethodCallVisitor.visit_ImportFrom)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:37 (em MethodCallVisitor.visit_ImportFrom)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:29 (em VariableTracker.visit_Import)
  ... e mais 5 ocorrências
```

#### `alias.name` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:30 (em MethodCallVisitor.visit_Import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:37 (em MethodCallVisitor.visit_ImportFrom)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:29 (em VariableTracker.visit_Import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:36 (em VariableTracker.visit_ImportFrom)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:107 (em ImportChecker.extract_imports)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `all_content`

#### `all_content.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:292 (em ConversationContext.get_context_summary)
```

### 🔍 Objeto: `all_defined_methods`

#### `all_defined_methods.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:148 (em module.find_undefined_methods)
```

### 🔍 Objeto: `all_inconsistencies`

#### `all_inconsistencies.extend` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:91 (em CriticAgent.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:92 (em CriticAgent.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:93 (em CriticAgent.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:94 (em CriticAgent.top-level)
```

### 🔍 Objeto: `all_insights`

#### `all_insights.extend` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:680 (em IntelligenceCoordinator._create_simple_consensus)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:682 (em IntelligenceCoordinator._create_simple_consensus)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:859 (em IntelligenceCoordinator._combine_all_insights)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:623 (em IntelligenceProcessor._comprehensive_synthesis)
```

### 🔍 Objeto: `all_method_calls`

#### `all_method_calls.extend` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:147 (em module.find_undefined_methods)
```

### 🔍 Objeto: `all_suggestions`

#### `all_suggestions.extend` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:122 (em SuggestionsManager.generate_suggestions)
```

### 🔍 Objeto: `analise`

#### `analise.get` (72 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:291 (em SemanticEnricher._sugestoes_qualidade_banco)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:292 (em SemanticEnricher._sugestoes_qualidade_banco)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:293 (em SemanticEnricher._sugestoes_qualidade_banco)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:305 (em SemanticEnricher._sugestoes_qualidade_banco)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:306 (em SemanticEnricher._sugestoes_qualidade_banco)
  ... e mais 67 ocorrências
```

#### `analise.confianca` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:410 (em FeedbackProcessor._gerar_acoes_correcao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:425 (em FeedbackProcessor._gerar_acoes_melhoria)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:440 (em FeedbackProcessor._gerar_acoes_clarificacao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:454 (em FeedbackProcessor._gerar_acoes_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:468 (em FeedbackProcessor._gerar_acoes_busca)
  ... e mais 1 ocorrências
```

#### `analise.tipo` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:264 (em FeedbackProcessor.extrair_acoes_corretivas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:267 (em FeedbackProcessor.extrair_acoes_corretivas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:270 (em FeedbackProcessor.extrair_acoes_corretivas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:506 (em FeedbackProcessor._salvar_feedback_analise)
```

#### `analise.categoria` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:274 (em FeedbackProcessor.extrair_acoes_corretivas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:277 (em FeedbackProcessor.extrair_acoes_corretivas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:405 (em FeedbackProcessor._gerar_acoes_correcao)
```

#### `analise.acoes_sugeridas` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:405 (em FeedbackProcessor._gerar_acoes_correcao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:424 (em FeedbackProcessor._gerar_acoes_melhoria)
```

### 🔍 Objeto: `analise_completa`

#### `analise_completa.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:94 (em DataAnalyzer.analisar_dados_reais)
```

### 🔍 Objeto: `analise_dados`

#### `analise_dados.get` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:415 (em AutoMapper._melhorar_termos_com_analise)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:441 (em AutoMapper._melhorar_termos_com_analise)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:472 (em AutoMapper._ajustar_confianca_com_analise)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:479 (em AutoMapper._ajustar_confianca_com_analise)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:484 (em AutoMapper._ajustar_confianca_com_analise)
```

### 🔍 Objeto: `analysis`

#### `analysis.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:193 (em ClassDuplicateFinder.generate_report)
```

### 🔍 Objeto: `analysis1`

#### `analysis1.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:363 (em SemanticAnalyzer._calculate_similarity)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:370 (em SemanticAnalyzer._calculate_similarity)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:377 (em SemanticAnalyzer._calculate_similarity)
```

### 🔍 Objeto: `analysis2`

#### `analysis2.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:364 (em SemanticAnalyzer._calculate_similarity)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:371 (em SemanticAnalyzer._calculate_similarity)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:377 (em SemanticAnalyzer._calculate_similarity)
```

### 🔍 Objeto: `analyzer`

#### `analyzer.detect_anomalies` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:644 (em module.detect_system_anomalies)
```

#### `analyzer.analyze` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/__init__.py:139 (em module.analyze_query_intention)
```

#### `analyzer.analyze_structure` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/__init__.py:144 (em module.analyze_text_structure)
```

#### `analyzer.analyze_query` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/__init__.py:149 (em module.analyze_semantic_meaning)
```

### 🔍 Objeto: `anomalies`

#### `anomalies.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:577 (em PerformanceAnalyzer._detect_statistical_anomalies)
```

### 🔍 Objeto: `anthropic`

#### `anthropic.Anthropic` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:73 (em ClaudeAPIClient.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:113 (em ResponseProcessor._init_anthropic_client)
```

### 🔍 Objeto: `api_tasks`

#### `api_tasks.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:299 (em CursorMonitor.top-level)
```

### 🔍 Objeto: `app`

#### `app.app_context` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:89 (em DatabaseConnection._try_flask_connection)
```

### 🔍 Objeto: `aprendizado`

#### `aprendizado.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:443 (em SessionOrchestrator._execute_learning_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:444 (em SessionOrchestrator._execute_learning_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:448 (em SessionOrchestrator._execute_learning_workflow)
```

### 🔍 Objeto: `aprendizados`

#### `aprendizados.get` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:357 (em LearningCore._calcular_score_aprendizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:360 (em LearningCore._calcular_score_aprendizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:363 (em LearningCore._calcular_score_aprendizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:366 (em LearningCore._calcular_score_aprendizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:369 (em LearningCore._calcular_score_aprendizado)
```

### 🔍 Objeto: `architectural_compliance`

#### `architectural_compliance.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/__init__.py:236 (em module.validate_integration_architecture)
```

### 🔍 Objeto: `architecture_data`

#### `architecture_data.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:103 (em StructuralAnalyzer.validate_architecture)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:107 (em StructuralAnalyzer.validate_architecture)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:111 (em StructuralAnalyzer.validate_architecture)
```

### 🔍 Objeto: `arg`

#### `arg.arg` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:44 (em VariableTracker.visit_FunctionDef)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:45 (em VariableTracker.visit_FunctionDef)
```

### 🔍 Objeto: `argparse`

#### `argparse.ArgumentParser` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:360 (em module.main)
```

### 🔍 Objeto: `args`

#### `args.url` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:366 (em module.main)
```

#### `args.interval` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:367 (em module.main)
```

### 🔍 Objeto: `arquivo`

#### `arquivo.name` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:74 (em DetectorModulosOrfaos._analisar_pasta)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:78 (em DetectorModulosOrfaos._analisar_pasta)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:81 (em DetectorModulosOrfaos._analisar_pasta)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:132 (em DetectorModulosOrfaos.analisar_imports_sistema)
```

#### `arquivo.is_file` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:73 (em DetectorModulosOrfaos._analisar_pasta)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:132 (em DetectorModulosOrfaos.analisar_imports_sistema)
```

#### `arquivo.name.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:81 (em DetectorModulosOrfaos._analisar_pasta)
```

#### `arquivo.relative_to` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:136 (em DetectorModulosOrfaos.analisar_imports_sistema)
```

#### `arquivo.replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:175 (em TesteIntegracaoCompleta.testar_modulo)
```

### 🔍 Objeto: `arquivos_grandes`

#### `arquivos_grandes.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:200 (em module.verificar_modulos_especiais)
```

### 🔍 Objeto: `arquivos_importantes`

#### `arquivos_importantes.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:205 (em module.verificar_modulos_especiais)
```

### 🔍 Objeto: `arquivos_py_local`

#### `arquivos_py_local.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:66 (em module.contar_arquivos_detalhado)
```

### 🔍 Objeto: `assign_node`

#### `assign_node.targets` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:149 (em CodeScanner._parse_form_field)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:244 (em StructureScanner._parse_model_assignment)
```

#### `assign_node.value` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:152 (em CodeScanner._parse_form_field)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:247 (em StructureScanner._parse_model_assignment)
```

### 🔍 Objeto: `ast`

#### `ast.Name` (17 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:68 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:71 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:82 (em MethodCallVisitor._get_object_name)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:55 (em VariableTracker.visit_ClassDef)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:62 (em VariableTracker.visit_Assign)
  ... e mais 12 ocorrências
```

#### `ast.ClassDef` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:106 (em DetectorModulosOrfaos._extrair_definicoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:52 (em ClassDuplicateFinder.scan_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:60 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:104 (em CodeScanner._parse_forms_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:136 (em CodeScanner._is_flask_form)
  ... e mais 3 ocorrências
```

#### `ast.Attribute` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:70 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:84 (em MethodCallVisitor._get_object_name)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:142 (em CodeScanner._is_flask_form)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:172 (em CodeScanner._extract_form_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:198 (em CodeScanner._extract_validators)
  ... e mais 3 ocorrências
```

#### `ast.Constant` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:210 (em CodeScanner._extract_dict_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:212 (em CodeScanner._extract_dict_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:235 (em CodeScanner._extract_simple_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:236 (em StructureScanner._extract_table_name)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:296 (em StructureScanner._extract_field_info)
  ... e mais 3 ocorrências
```

#### `ast.parse` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:104 (em DetectorModulosOrfaos._extrair_definicoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:48 (em ClassDuplicateFinder.scan_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:99 (em module.analyze_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:110 (em UninitializedVariableFinder.scan_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:64 (em ImportChecker.check_file)
  ... e mais 2 ocorrências
```

#### `ast.Assign` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:53 (em VariableTracker.visit_ClassDef)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:120 (em CodeScanner._parse_forms_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:147 (em CodeScanner._parse_form_field)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:200 (em StructureScanner._parse_models_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:233 (em StructureScanner._extract_table_name)
  ... e mais 1 ocorrências
```

#### `ast.FunctionDef` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:108 (em DetectorModulosOrfaos._extrair_definicoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:76 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:49 (em MethodCallVisitor.visit_ClassDef)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:122 (em CodeScanner._parse_forms_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:202 (em StructureScanner._parse_models_file)
```

#### `ast.Call` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:88 (em MethodCallVisitor._get_object_name)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:168 (em CodeScanner._extract_form_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:195 (em CodeScanner._extract_validators)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:271 (em StructureScanner._extract_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:327 (em StructureScanner._extract_column_type)
```

#### `ast.Str` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:237 (em CodeScanner._extract_simple_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:238 (em StructureScanner._extract_table_name)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:298 (em StructureScanner._extract_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:350 (em StructureScanner._extract_string_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:361 (em StructureScanner._extract_value)
```

#### `ast.walk` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:105 (em DetectorModulosOrfaos._extrair_definicoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:51 (em ClassDuplicateFinder.scan_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:102 (em ImportChecker.extract_imports)
```

#### `ast.NodeVisitor` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:16 (em MethodCallVisitor.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:15 (em VariableTracker.top-level)
```

#### `ast.Load` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:66 (em MethodCallVisitor.visit_Attribute)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:69 (em VariableTracker.visit_Name)
```

#### `ast.List` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:193 (em CodeScanner._extract_validators)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:222 (em CodeScanner._extract_choices)
```

#### `ast.Num` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:239 (em CodeScanner._extract_simple_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:363 (em StructureScanner._extract_value)
```

#### `ast.NameConstant` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:339 (em StructureScanner._extract_boolean_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:365 (em StructureScanner._extract_value)
```

#### `ast.get_docstring` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:63 (em ClassDuplicateFinder.extract_class_info)
```

#### `ast.Store` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:72 (em VariableTracker.visit_Name)
```

#### `ast.AST` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:98 (em ImportChecker.extract_imports)
```

#### `ast.Import` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:103 (em ImportChecker.extract_imports)
```

#### `ast.ImportFrom` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:112 (em ImportChecker.extract_imports)
```

#### `ast.Dict` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:208 (em CodeScanner._extract_dict_value)
```

#### `ast.Tuple` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:224 (em CodeScanner._extract_choices)
```

### 🔍 Objeto: `asyncio`

#### `asyncio.run` (9 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:398 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:102 (em ProcessorCoordinator._execute_chain_step)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:197 (em ProcessorCoordinator._execute_single_processor)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:513 (em module.processar_com_claude_real)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:127 (em StandaloneIntegration.initialize_system)
  ... e mais 4 ocorrências
```

#### `asyncio.get_event_loop` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:219 (em ClaudeAINovo.process_query_sync)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:330 (em module.get_claude_ai_instance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:507 (em module.processar_com_claude_real)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:124 (em StandaloneIntegration.initialize_system)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:194 (em StandaloneIntegration.process_query)
  ... e mais 3 ocorrências
```

#### `asyncio.to_thread` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:297 (em CursorMonitor.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:311 (em CursorMonitor.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:312 (em CursorMonitor.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:316 (em CursorMonitor.top-level)
```

#### `asyncio.new_event_loop` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:221 (em ClaudeAINovo.process_query_sync)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:332 (em module.get_claude_ai_instance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:262 (em WebIntegrationAdapter._run_async)
```

#### `asyncio.set_event_loop` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:222 (em ClaudeAINovo.process_query_sync)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:333 (em module.get_claude_ai_instance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:263 (em WebIntegrationAdapter._run_async)
```

#### `asyncio.iscoroutinefunction` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:100 (em ProcessorCoordinator._execute_chain_step)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:196 (em ProcessorCoordinator._execute_single_processor)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:933 (em MainOrchestrator.top-level)
```

#### `asyncio.gather` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:301 (em CursorMonitor.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:884 (em MainOrchestrator.top-level)
```

#### `asyncio.sleep` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:326 (em CursorMonitor.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:334 (em CursorMonitor.top-level)
```

#### `asyncio.create_task` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:296 (em CursorMonitor.top-level)
```

### 🔍 Objeto: `atrasos`

#### `atrasos.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:111 (em ValidationUtils._calcular_metricas_prazo)
```

### 🔍 Objeto: `attr`

#### `attr.startswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:197 (em DeepValidator._test_class_exists)
```

### 🔍 Objeto: `available_scores`

#### `available_scores.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:445 (em OrchestratorManager._detect_appropriate_orchestrator)
```

### 🔍 Objeto: `base`

#### `base.value` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:71 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:71 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:223 (em StructureScanner._is_sqlalchemy_model)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:223 (em StructureScanner._is_sqlalchemy_model)
```

#### `base.attr` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:71 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:71 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:143 (em CodeScanner._is_flask_form)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:223 (em StructureScanner._is_sqlalchemy_model)
```

#### `base.id` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:69 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:140 (em CodeScanner._is_flask_form)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:226 (em StructureScanner._is_sqlalchemy_model)
```

#### `base.value.id` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:71 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:223 (em StructureScanner._is_sqlalchemy_model)
```

#### `base.replace().lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:237 (em BaseCommand._generate_cache_key)
```

#### `base.replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:237 (em BaseCommand._generate_cache_key)
```

### 🔍 Objeto: `base_cmd`

#### `base_cmd._format_currency` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:365 (em module.create_excel_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:366 (em module.create_excel_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:367 (em module.create_excel_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:368 (em module.create_excel_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:374 (em module.create_excel_summary)
  ... e mais 1 ocorrências
```

#### `base_cmd._format_weight` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:375 (em module.create_excel_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:377 (em module.create_excel_summary)
```

#### `base_cmd._create_summary_stats` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:348 (em module.create_excel_summary)
```

#### `base_cmd._format_percentage` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:385 (em module.create_excel_summary)
```

### 🔍 Objeto: `base_dir`

#### `base_dir.rglob` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:139 (em module.find_undefined_methods)
```

### 🔍 Objeto: `base_status`

#### `base_status.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:158 (em ClaudeAINovo.get_system_status)
```

### 🔍 Objeto: `bases`

#### `bases.append` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:69 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:71 (em ClassDuplicateFinder.extract_class_info)
```

### 🔍 Objeto: `basic_config`

#### `basic_config.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:291 (em ClaudeAIMetrics.get_ai_technical_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:294 (em ClaudeAIMetrics.get_ai_technical_metrics)
```

### 🔍 Objeto: `basic_context`

#### `basic_context.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:527 (em WebFlaskRoutes._build_user_context)
```

### 🔍 Objeto: `batch_result`

#### `batch_result.get().get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:167 (em DataProcessor.batch_process)
```

#### `batch_result.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:167 (em DataProcessor.batch_process)
```

### 🔍 Objeto: `best_orchestrator`

#### `best_orchestrator.value` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:446 (em OrchestratorManager._detect_appropriate_orchestrator)
```

### 🔍 Objeto: `blocks`

#### `blocks.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:151 (em FileScanner._extract_template_blocks)
```

### 🔍 Objeto: `bp`

#### `bp.route` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:327 (em WebFlaskRoutes.chat_page)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:333 (em WebFlaskRoutes.api_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:387 (em WebFlaskRoutes.api_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:420 (em WebFlaskRoutes.clear_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:445 (em WebFlaskRoutes.health_check)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `business_logic`

#### `business_logic.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:94 (em CriticAgent.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:103 (em CriticAgent.top-level)
```

### 🔍 Objeto: `by_file`

#### `by_file.items` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:95 (em ImportFixer.fix_imports)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:280 (em ImportChecker.print_report)
```

### 🔍 Objeto: `by_module`

#### `by_module.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:302 (em ImportChecker.print_report)
```

### 🔍 Objeto: `by_priority`

#### `by_priority.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:716 (em SessionOrchestrator.get_session_stats)
```

### 🔍 Objeto: `by_status`

#### `by_status.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:712 (em SessionOrchestrator.get_session_stats)
```

### 🔍 Objeto: `by_type`

#### `by_type.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:196 (em ImportFixer._print_report)
```

### 🔍 Objeto: `by_variable`

#### `by_variable.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:223 (em UninitializedVariableFinder.generate_report)
```

### 🔍 Objeto: `c`

#### `c.get` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:276 (em ProcessorCoordinator.get_coordinator_stats)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:277 (em ProcessorCoordinator.get_coordinator_stats)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:278 (em ProcessorCoordinator.get_coordinator_stats)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:156 (em BaseMapper.gerar_estatisticas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:270 (em SystemMemory.get_system_overview)
```

#### `c.strip` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:233 (em KnowledgeMemory.buscar_grupos_aplicaveis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:233 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `c.get().get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:270 (em SystemMemory.get_system_overview)
```

### 🔍 Objeto: `cache`

#### `cache.get_cached_result` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:260 (em module.cached_result)
```

#### `cache.set_cached_result` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:268 (em module.cached_result)
```

### 🔍 Objeto: `cache_entry`

#### `cache_entry.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/context_provider.py:415 (em ContextProvider._get_cached_context)
```

### 🔍 Objeto: `cache_obj`

#### `cache_obj.set` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_classes.py:324 (em BaseProcessor._safe_cache_set)
```

### 🔍 Objeto: `campo`

#### `campo.get` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:168 (em MapperManager._calcular_confianca_integrada)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:171 (em MapperManager._calcular_confianca_integrada)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:194 (em MapperManager._agrupar_por_mapper)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:149 (em DatabaseManager.buscar_campos_por_tipo)
```

#### `campo.lower` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:406 (em SemanticValidator._calcular_similaridade_termo_campo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:414 (em SemanticValidator._calcular_similaridade_termo_campo)
```

#### `campo.endswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:178 (em SemanticValidator._validacoes_gerais)
```

#### `campo.lower().split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:414 (em SemanticValidator._calcular_similaridade_termo_campo)
```

### 🔍 Objeto: `campo_comp`

#### `campo_comp.get` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:467 (em FieldSearcher._calcular_similaridade_campos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:470 (em FieldSearcher._calcular_similaridade_campos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:475 (em FieldSearcher._calcular_similaridade_campos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:507 (em FieldSearcher._analisar_fatores_similaridade)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:510 (em FieldSearcher._analisar_fatores_similaridade)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `campo_ref`

#### `campo_ref.get` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:467 (em FieldSearcher._calcular_similaridade_campos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:470 (em FieldSearcher._calcular_similaridade_campos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:474 (em FieldSearcher._calcular_similaridade_campos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:507 (em FieldSearcher._analisar_fatores_similaridade)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:510 (em FieldSearcher._analisar_fatores_similaridade)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `campos_baixa_confianca`

#### `campos_baixa_confianca.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:511 (em AutoMapper._gerar_sugestoes_melhoria)
```

### 🔍 Objeto: `campos_detectados`

#### `campos_detectados.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:76 (em MapperManager.analisar_consulta_semantica)
```

#### `campos_detectados.extend` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:86 (em MapperManager.analisar_consulta_semantica)
```

### 🔍 Objeto: `campos_encontrados`

#### `campos_encontrados.append` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:99 (em FieldSearcher.buscar_campos_por_tipo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:179 (em FieldSearcher.buscar_campos_por_nome)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:314 (em FieldSearcher.buscar_campos_por_caracteristica)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:367 (em FieldSearcher.buscar_campos_por_tamanho)
```

#### `campos_encontrados.sort` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:102 (em FieldSearcher.buscar_campos_por_tipo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:182 (em FieldSearcher.buscar_campos_por_nome)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:370 (em FieldSearcher.buscar_campos_por_tamanho)
```

### 🔍 Objeto: `campos_por_tabela`

#### `campos_por_tabela.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:305 (em MetadataReader.obter_estatisticas_tabelas)
```

### 🔍 Objeto: `campos_similares`

#### `campos_similares.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:428 (em FieldSearcher.buscar_campos_similares)
```

#### `campos_similares.sort` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:431 (em FieldSearcher.buscar_campos_similares)
```

### 🔍 Objeto: `candidate`

#### `candidate.exists` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:443 (em SystemConfig._get_default_config_path)
```

### 🔍 Objeto: `categorias`

#### `categorias.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:384 (em AutoMapper._identificar_categoria_semantica)
```

### 🔍 Objeto: `category_patterns`

#### `category_patterns.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:354 (em FeedbackProcessor._classificar_categoria)
```

### 🔍 Objeto: `cell`

#### `cell.value` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:444 (em ExcelEntregas._auto_ajustar_colunas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:445 (em ExcelEntregas._auto_ajustar_colunas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:299 (em ExcelFaturamento._auto_ajustar_colunas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:300 (em ExcelFaturamento._auto_ajustar_colunas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:410 (em ExcelFretes._auto_ajustar_colunas)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `chain_info`

#### `chain_info.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:259 (em ProcessorCoordinator.cleanup_completed_chains)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:260 (em ProcessorCoordinator.cleanup_completed_chains)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:260 (em ProcessorCoordinator.cleanup_completed_chains)
```

### 🔍 Objeto: `chains`

#### `chains.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:135 (em ProcessorManager.get_processor_chain)
```

### 🔍 Objeto: `chains_to_remove`

#### `chains_to_remove.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:262 (em ProcessorCoordinator.cleanup_completed_chains)
```

### 🔍 Objeto: `check_name`

#### `check_name.upper` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:232 (em CursorMonitor.display_status)
```

### 🔍 Objeto: `checker`

#### `checker.check_directory` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:328 (em module.main)
```

#### `checker.print_report` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:331 (em module.main)
```

#### `checker.save_report` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:335 (em module.main)
```

### 🔍 Objeto: `checks`

#### `checks.append` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:83 (em module.check_anti_loop_protection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:86 (em module.check_anti_loop_protection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:90 (em module.check_anti_loop_protection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:93 (em module.check_anti_loop_protection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:107 (em module.check_anti_loop_protection)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `choices`

#### `choices.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:227 (em CodeScanner._extract_choices)
```

### 🔍 Objeto: `choices_node`

#### `choices_node.elts` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:223 (em CodeScanner._extract_choices)
```

### 🔍 Objeto: `chr()`

#### `chr().join` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:125 (em CursorCommands._ativar_cursor_mode)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/response_utils.py:108 (em ResponseUtils._formatar_resultado_cursor)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/response_utils.py:146 (em ResponseUtils._formatar_status_cursor)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/response_utils.py:149 (em ResponseUtils._formatar_status_cursor)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/response_utils.py:152 (em ResponseUtils._formatar_status_cursor)
```

### 🔍 Objeto: `ck`

#### `ck.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:241 (em MetadataReader._obter_constraints_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:242 (em MetadataReader._obter_constraints_tabela)
```

### 🔍 Objeto: `class_node`

#### `class_node.bases` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:138 (em CodeScanner._is_flask_form)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:221 (em StructureScanner._is_sqlalchemy_model)
```

#### `class_node.body` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:232 (em StructureScanner._extract_table_name)
```

### 🔍 Objeto: `classes`

#### `classes.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:107 (em DetectorModulosOrfaos._extrair_definicoes)
```

#### `classes.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:162 (em StructuralAnalyzer.detect_patterns)
```

#### `classes.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:265 (em StructuralAnalyzer._calculate_complexity)
```

### 🔍 Objeto: `classification`

#### `classification.upper` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:260 (em CursorMonitor.display_status)
```

### 🔍 Objeto: `claude_ai`

#### `claude_ai.initialize_system` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:287 (em module.top-level)
```

### 🔍 Objeto: `claude_data`

#### `claude_data.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:242 (em CursorMonitor.display_status)
```

### 🔍 Objeto: `claude_instance`

#### `claude_instance.__class__.__name__` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/__init__.py:350 (em module.top-level)
```

#### `claude_instance.__class__` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/__init__.py:350 (em module.top-level)
```

### 🔍 Objeto: `claude_metrics`

#### `claude_metrics.record_query` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:420 (em module.record_query_metric)
```

### 🔍 Objeto: `cleanup_results`

#### `cleanup_results.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:291 (em MemoryManager.cleanup_expired_data)
```

### 🔍 Objeto: `cliente`

#### `cliente.lower` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:211 (em ConversationContext.extract_metadata)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:211 (em ConversationContext.extract_metadata)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:292 (em ConversationContext.get_context_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:460 (em PatternLearner._extrair_termos_cliente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:401 (em KnowledgeMemory._extrair_termos_cliente)
```

#### `cliente.title` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:97 (em BaseCommand._extract_client_from_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/base.py:53 (em ProcessorBase._extract_filters)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:469 (em SuggestionsEngine._get_contextual_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:473 (em SuggestionsEngine._get_contextual_suggestions)
```

### 🔍 Objeto: `cliente_lower`

#### `cliente_lower.split` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:467 (em PatternLearner._extrair_termos_cliente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:408 (em KnowledgeMemory._extrair_termos_cliente)
```

#### `cliente_lower.startswith` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:477 (em PatternLearner._extrair_termos_cliente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:417 (em KnowledgeMemory._extrair_termos_cliente)
```

### 🔍 Objeto: `clientes_mencionados`

#### `clientes_mencionados.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:293 (em ConversationContext.get_context_summary)
```

### 🔍 Objeto: `clientes_stats`

#### `clientes_stats.items` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:117 (em FaturamentoLoader._format_faturamento_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:154 (em FretesLoader._format_fretes_results)
```

### 🔍 Objeto: `cls`

#### `cls._instance` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:35 (em ScannersCache.__new__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:37 (em ScannersCache.__new__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:39 (em ScannersCache.__new__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:40 (em ScannersCache.__new__)
```

#### `cls.ANTHROPIC_API_KEY` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/basic_config.py:46 (em ClaudeAIConfig.get_anthropic_api_key)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/basic_config.py:69 (em ClaudeAIConfig.validate)
```

#### `cls.CLAUDE_MODEL` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/basic_config.py:52 (em ClaudeAIConfig.get_claude_params)
```

#### `cls.MAX_TOKENS` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/basic_config.py:53 (em ClaudeAIConfig.get_claude_params)
```

#### `cls.TEMPERATURE` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/basic_config.py:54 (em ClaudeAIConfig.get_claude_params)
```

#### `cls._lock` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:36 (em ScannersCache.__new__)
```

### 🔍 Objeto: `cluster`

#### `cluster.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:324 (em RelationshipMapper._explorar_cluster)
```

### 🔍 Objeto: `clusters`

#### `clusters.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:286 (em RelationshipMapper._identificar_clusters)
```

#### `clusters.sort` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:294 (em RelationshipMapper._identificar_clusters)
```

### 🔍 Objeto: `col`

#### `col.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:124 (em StructureScanner._discover_models_via_database)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:124 (em StructureScanner._discover_models_via_database)
```

### 🔍 Objeto: `coluna`

#### `coluna.get` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:101 (em MetadataReader.obter_campos_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:102 (em MetadataReader.obter_campos_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:103 (em MetadataReader.obter_campos_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:105 (em MetadataReader.obter_campos_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:106 (em MetadataReader.obter_campos_tabela)
```

### 🔍 Objeto: `combined`

#### `combined.extend` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:576 (em DataProcessor._combine_processed_data)
```

#### `combined.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:582 (em DataProcessor._combine_processed_data)
```

#### `combined.encode` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:317 (em SecurityGuard.generate_token)
```

### 🔍 Objeto: `command`

#### `command.get` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:372 (em AutoCommandProcessor._validate_security)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:380 (em AutoCommandProcessor._validate_security)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:399 (em AutoCommandProcessor._execute_command)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:486 (em AutoCommandProcessor._validate_command_syntax)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:487 (em AutoCommandProcessor._validate_command_syntax)
```

#### `command.get().get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:372 (em AutoCommandProcessor._validate_security)
```

#### `command.get().lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:380 (em AutoCommandProcessor._validate_security)
```

### 🔍 Objeto: `command_result`

#### `command_result.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:560 (em MainOrchestrator._execute_natural_commands)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:563 (em MainOrchestrator._execute_natural_commands)
```

### 🔍 Objeto: `common`

#### `common.extend` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:389 (em SemanticAnalyzer._find_common_entities)
```

### 🔍 Objeto: `common_issues`

#### `common_issues.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:375 (em HumanInLoopLearning._analyze_trends)
```

#### `common_issues.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:378 (em HumanInLoopLearning._analyze_trends)
```

### 🔍 Objeto: `comp`

#### `comp.analyze_intention` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:327 (em TesteIntegracaoCompleta.testar_fallbacks_mocks)
```

#### `comp.generate_intelligent_suggestions` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:331 (em TesteIntegracaoCompleta.testar_fallbacks_mocks)
```

#### `comp.manage_conversation` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:335 (em TesteIntegracaoCompleta.testar_fallbacks_mocks)
```

### 🔍 Objeto: `component_data`

#### `component_data.get().get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:300 (em SystemMemory.get_component_status)
```

#### `component_data.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:300 (em SystemMemory.get_component_status)
```

### 🔍 Objeto: `component_info`

#### `component_info.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:590 (em IntelligenceCoordinator._component_supports_operation)
```

### 🔍 Objeto: `component_instance`

#### `component_instance.analyze` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:547 (em IntelligenceCoordinator._execute_component_operation)
```

#### `component_instance.synthesize` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:549 (em IntelligenceCoordinator._execute_component_operation)
```

#### `component_instance.predict` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:551 (em IntelligenceCoordinator._execute_component_operation)
```

#### `component_instance.optimize` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:553 (em IntelligenceCoordinator._execute_component_operation)
```

#### `component_instance.process` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:555 (em IntelligenceCoordinator._execute_component_operation)
```

#### `component_instance.process_intelligence` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:557 (em IntelligenceCoordinator._execute_component_operation)
```

### 🔍 Objeto: `components`

#### `components.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/__init__.py:225 (em module.validate_integration_architecture)
```

#### `components.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:243 (em CursorMonitor.display_status)
```

### 🔍 Objeto: `compressed`

#### `compressed.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:278 (em ContextMemory._compress_context)
```

### 🔍 Objeto: `conditions`

#### `conditions.append` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:148 (em DatabaseLoader.load_table_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:221 (em SessionMemory.search_sessions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:224 (em SessionMemory.search_sessions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:227 (em SessionMemory.search_sessions)
```

### 🔍 Objeto: `confiancas`

#### `confiancas.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:291 (em IntentionAnalyzer.get_performance_stats)
```

### 🔍 Objeto: `confidences`

#### `confidences.append` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:334 (em AnalyzerManager._calculate_combined_confidence)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:336 (em AnalyzerManager._calculate_combined_confidence)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:130 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:671 (em IntelligenceCoordinator._create_simple_consensus)
```

### 🔍 Objeto: `config`

#### `config.get` (11 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:123 (em IntentionAnalyzer._detectar_intencoes_multiplas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:149 (em ProcessorCoordinator.execute_parallel_processors)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:175 (em ProcessorCoordinator._execute_single_processor)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:176 (em ProcessorCoordinator._execute_single_processor)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:177 (em ProcessorCoordinator._execute_single_processor)
  ... e mais 6 ocorrências
```

#### `config.get_anthropic_api_key` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:108 (em ValidadorSistemaReal._test_anthropic_config)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:110 (em ResponseProcessor._init_anthropic_client)
```

#### `config.get_claude_params` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:90 (em ClaudeAPIClient.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:114 (em ClaudeAPIClient.from_mode)
```

#### `config.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:644 (em SystemConfig._validate_profile_config)
```

### 🔍 Objeto: `config_data`

#### `config_data.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:104 (em SystemMemory.retrieve_system_config)
```

### 🔍 Objeto: `config_params`

#### `config_params.get` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:83 (em ClaudeAPIClient.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:84 (em ClaudeAPIClient.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:85 (em ClaudeAPIClient.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:86 (em ClaudeAPIClient.__init__)
```

### 🔍 Objeto: `conhecimento`

#### `conhecimento.get` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:387 (em LearningCore._gerar_recomendacoes_aplicacao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:397 (em LearningCore._gerar_recomendacoes_aplicacao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:398 (em LearningCore._gerar_recomendacoes_aplicacao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:399 (em LearningCore._gerar_recomendacoes_aplicacao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:524 (em SessionOrchestrator.apply_learned_knowledge)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `conn`

#### `conn.execute` (11 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:71 (em DatabaseLoader._initialize_connection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:112 (em DatabaseLoader.load_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:235 (em DatabaseConnection.test_connection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:123 (em DataAnalyzer._analisar_estatisticas_basicas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:169 (em DataAnalyzer._obter_exemplos_valores)
  ... e mais 6 ocorrências
```

#### `conn.execute().fetchone` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:123 (em DataAnalyzer._analisar_estatisticas_basicas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:242 (em DataAnalyzer._analisar_comprimento_valores)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:309 (em DataAnalyzer._verificar_padrao_numerico)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:340 (em DataAnalyzer._verificar_padrao_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:371 (em DataAnalyzer._verificar_padrao_email)
  ... e mais 1 ocorrências
```

#### `conn.execute().fetchall` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:169 (em DataAnalyzer._obter_exemplos_valores)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:201 (em DataAnalyzer._analisar_distribuicao)
```

### 🔍 Objeto: `connection_count`

#### `connection_count.items` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:300 (em DatabaseScanner._analyze_relationships)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:307 (em DatabaseScanner._analyze_relationships)
```

#### `connection_count.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:314 (em DatabaseScanner._analyze_relationships)
```

### 🔍 Objeto: `consistencia`

#### `consistencia.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:306 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
```

### 🔍 Objeto: `consistency_check`

#### `consistency_check.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:329 (em ValidatorManager.validate_consistency)
```

### 🔍 Objeto: `consulta`

#### `consulta.lower` (28 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:62 (em IntentionAnalyzer._detectar_intencoes_multiplas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:140 (em IntentionAnalyzer._analisar_contexto_intencao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:203 (em IntentionAnalyzer._detectar_urgencia)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:225 (em IntentionAnalyzer._calcular_complexidade_intencao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:226 (em IntentionAnalyzer._calcular_complexidade_intencao)
  ... e mais 23 ocorrências
```

#### `consulta.split` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:222 (em IntentionAnalyzer._calcular_complexidade_intencao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:249 (em IntentionAnalyzer._deve_usar_sistema_avancado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:140 (em MapperManager._extrair_termos_compostos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/data_manager.py:339 (em DataManager.get_best_loader)
```

#### `consulta.strip` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:76 (em BaseCommand._validate_input)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:85 (em BaseCommand._sanitize_input)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:216 (em PatternLearner._extrair_padroes_linguisticos)
```

#### `consulta.replace().strip` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:229 (em CursorCommands._buscar_codigo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:268 (em CursorCommands._cursor_chat)
```

#### `consulta.replace` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:229 (em CursorCommands._buscar_codigo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:268 (em CursorCommands._cursor_chat)
```

#### `consulta.strip().endswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:216 (em PatternLearner._extrair_padroes_linguisticos)
```

#### `consulta.lower().strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:59 (em MapperManager.analisar_consulta_semantica)
```

### 🔍 Objeto: `consulta_lower`

#### `consulta_lower.split` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:473 (em PatternLearner._extrair_termos_cliente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:67 (em MapperManager.analisar_consulta_semantica)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:96 (em MapperManager.analisar_consulta_semantica)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:414 (em KnowledgeMemory._extrair_termos_cliente)
```

#### `consulta_lower.index` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:186 (em ExcelOrchestrator._detectar_tipo_excel)
```

### 🔍 Objeto: `contagem`

#### `contagem.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:195 (em MapperManager._agrupar_por_mapper)
```

### 🔍 Objeto: `content`

#### `content.split` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:80 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:189 (em UninitializedVariableFinder._get_line_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:261 (em CodeScanner._parse_routes_file)
```

#### `content.encode` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:711 (em IntelligenceCoordinator._generate_cache_key)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/context_provider.py:404 (em ContextProvider._generate_cache_key)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:491 (em SuggestionsManager._generate_cache_key)
```

#### `content.lower` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:88 (em module.check_anti_loop_protection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:88 (em module.check_anti_loop_protection)
```

#### `content.rstrip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:251 (em ImportFixer._add_get_function)
```

### 🔍 Objeto: `conteudo`

#### `conteudo.splitlines` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:88 (em DetectorModulosOrfaos._analisar_pasta)
```

### 🔍 Objeto: `context`

#### `context.get` (21 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:352 (em SemanticAnalyzer._enhance_with_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:426 (em AutoCommandProcessor._handle_query_command)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:435 (em AutoCommandProcessor._handle_report_command)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:444 (em AutoCommandProcessor._handle_analyze_command)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:351 (em ConversationManager.get_conversation_summary)
  ... e mais 16 ocorrências
```

#### `context.update` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:862 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:892 (em MainOrchestrator.top-level)
```

#### `context.copy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:271 (em ContextMemory._compress_context)
```

#### `context.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:177 (em BaseValidationUtils.validate_context)
```

### 🔍 Objeto: `context_history`

#### `context_history.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:71 (em ConversationContext.add_message)
```

### 🔍 Objeto: `context_lines`

#### `context_lines.append` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:177 (em ConversationContext.build_context_prompt)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:179 (em ConversationContext.build_context_prompt)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:180 (em ConversationContext.build_context_prompt)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:181 (em ConversationContext.build_context_prompt)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:182 (em ConversationContext.build_context_prompt)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `context_module`

#### `context_module.clear_context` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:428 (em WebFlaskRoutes.clear_context)
```

### 🔍 Objeto: `context_processor`

#### `context_processor.carregar_contexto_inteligente` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:523 (em WebFlaskRoutes._build_user_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:46 (em ProcessorManager.process_context)
```

### 🔍 Objeto: `context_result`

#### `context_result.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:218 (em ProviderManager._provide_data_with_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:250 (em ProviderManager._provide_context_with_data)
```

### 🔍 Objeto: `contexto`

#### `contexto.append` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:261 (em NLPEnhancedAnalyzer._detectar_negacoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:262 (em NLPEnhancedAnalyzer._detectar_negacoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:264 (em NLPEnhancedAnalyzer._detectar_negacoes)
```

#### `contexto.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:246 (em IntentionAnalyzer._deve_usar_sistema_avancado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:248 (em IntentionAnalyzer._deve_usar_sistema_avancado)
```

### 🔍 Objeto: `contextual_suggestions`

#### `contextual_suggestions.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:467 (em SuggestionsEngine._get_contextual_suggestions)
```

### 🔍 Objeto: `conversation_context`

#### `conversation_context.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:461 (em SuggestionsEngine._get_contextual_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:546 (em SuggestionsEngine._generate_cache_key)
```

#### `conversation_context.get().lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:461 (em SuggestionsEngine._get_contextual_suggestions)
```

### 🔍 Objeto: `conversation_result`

#### `conversation_result.get` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:486 (em SessionOrchestrator._execute_conversation_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:487 (em SessionOrchestrator._execute_conversation_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:488 (em SessionOrchestrator._execute_conversation_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:492 (em SessionOrchestrator._execute_conversation_workflow)
```

### 🔍 Objeto: `conversational`

#### `conversational.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:254 (em ContextEnricher._calculate_context_score)
```

### 🔍 Objeto: `coordination_result`

#### `coordination_result.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:523 (em MainOrchestrator._execute_intelligent_coordination)
```

### 🔍 Objeto: `coordinator`

#### `coordinator.coordinate_intelligent_response` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:271 (em CoordinatorManager._process_with_coordinator)
```

#### `coordinator.process_query` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:274 (em CoordinatorManager._process_with_coordinator)
```

#### `coordinator.coordinate_specialists` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:277 (em CoordinatorManager._process_with_coordinator)
```

#### `coordinator.process` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:280 (em CoordinatorManager._process_with_coordinator)
```

#### `coordinator.coordinate_intelligence_operation` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:219 (em module.coordinate_intelligence)
```

#### `coordinator.coordinate_processors` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:236 (em module.coordinate_processors)
```

### 🔍 Objeto: `coordinator_name`

#### `coordinator_name.startswith` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:257 (em CoordinatorManager._process_with_coordinator)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:295 (em CoordinatorManager._update_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:329 (em CoordinatorManager.reload_coordinator)
```

### 🔍 Objeto: `criteria`

#### `criteria.items` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:219 (em SessionMemory.search_sessions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:597 (em DataProcessor._apply_filters)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:681 (em IntelligenceProcessor._evaluate_option)
```

#### `criteria.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:228 (em IntelligenceProcessor.make_intelligent_decision)
```

### 🔍 Objeto: `criterios`

#### `criterios.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:256 (em IntentionAnalyzer._deve_usar_sistema_avancado)
```

### 🔍 Objeto: `current_app`

#### `current_app.app_context` (13 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:265 (em LearningCore._atualizar_metricas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:312 (em LearningCore._salvar_historico_aprendizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:260 (em PatternLearner._salvar_padrao_otimizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:339 (em PatternLearner.buscar_padroes_aplicaveis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:47 (em KnowledgeMemory.aprender_mapeamento_cliente)
  ... e mais 8 ocorrências
```

#### `current_app.config` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_context_wrapper.py:26 (em FlaskContextWrapper._init_flask_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_context_wrapper.py:41 (em FlaskContextWrapper.get_app_config)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:265 (em FlaskFallback.get_config)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/utils_manager.py:42 (em FlaskContextWrapper._init_flask_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/utils_manager.py:52 (em FlaskContextWrapper._get_app_config)
```

#### `current_app.name` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_context_wrapper.py:76 (em FlaskContextWrapper.get_flask_context_info)
```

#### `current_app.debug` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_context_wrapper.py:77 (em FlaskContextWrapper.get_flask_context_info)
```

#### `current_app.config.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:265 (em FlaskFallback.get_config)
```

### 🔍 Objeto: `current_dir`

#### `current_dir.parent` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:16 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:17 (em module.top-level)
```

#### `current_dir.parent.parent` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:17 (em module.top-level)
```

### 🔍 Objeto: `current_results`

#### `current_results.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:310 (em AnalyzerManager._should_use_nlp_analysis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:315 (em AnalyzerManager._should_use_nlp_analysis)
```

### 🔍 Objeto: `current_user`

#### `current_user.id` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:401 (em WebFlaskRoutes.api_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:428 (em WebFlaskRoutes.clear_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:503 (em WebFlaskRoutes._build_user_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:519 (em WebFlaskRoutes._build_user_context)
```

#### `current_user.nome` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:504 (em WebFlaskRoutes._build_user_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:87 (em ValidationUtils._obter_filtros_usuario)
```

#### `current_user.vendedor` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:159 (em ContextLoader._obter_filtros_usuario)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:85 (em ValidationUtils._obter_filtros_usuario)
```

#### `current_user.is_authenticated` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:378 (em SecurityGuard._is_user_authenticated)
```

#### `current_user.perfil` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:393 (em SecurityGuard._is_user_admin)
```

### 🔍 Objeto: `d`

#### `d.startswith` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:45 (em ImportChecker.check_directory)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:300 (em FileScanner.search_in_files)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:54 (em StructureScanner.discover_project_structure)
```

#### `d.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:411 (em ContextProcessor._carregar_dados_geral)
```

#### `d.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:206 (em StructureScanner._parse_models_file)
```

### 🔍 Objeto: `dados`

#### `dados.get` (24 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:247 (em SemanticEnricher._sugestoes_readme_vs_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:248 (em SemanticEnricher._sugestoes_readme_vs_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:287 (em SemanticEnricher._sugestoes_qualidade_banco)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:328 (em SemanticEnricher._sugestoes_campos_similares)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:358 (em SemanticEnricher._sugestoes_otimizacao)
  ... e mais 19 ocorrências
```

#### `dados.get().get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:446 (em SemanticEnricher._calcular_estatisticas_batch)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:449 (em SemanticEnricher._calcular_estatisticas_batch)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:452 (em SemanticEnricher._calcular_estatisticas_batch)
```

### 🔍 Objeto: `dados_agendamentos`

#### `dados_agendamentos.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:109 (em EntregasAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:110 (em EntregasAgent._resumir_dados_reais)
```

### 🔍 Objeto: `dados_completos`

#### `dados_completos.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:408 (em ContextLoader._carregar_contexto_inteligente)
```

### 🔍 Objeto: `dados_cotacoes`

#### `dados_cotacoes.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/pedidos_agent.py:56 (em PedidosAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/pedidos_agent.py:57 (em PedidosAgent._resumir_dados_reais)
```

### 🔍 Objeto: `dados_embarques`

#### `dados_embarques.get` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/embarques_agent.py:39 (em EmbarquesAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/embarques_agent.py:40 (em EmbarquesAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/embarques_agent.py:41 (em EmbarquesAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/embarques_agent.py:42 (em EmbarquesAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:283 (em ContextLoader._carregar_contexto_inteligente)
  ... e mais 2 ocorrências
```

### 🔍 Objeto: `dados_entregas`

#### `dados_entregas.get` (11 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:91 (em EntregasAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:92 (em EntregasAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:93 (em EntregasAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:94 (em EntregasAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:95 (em EntregasAgent._resumir_dados_reais)
  ... e mais 6 ocorrências
```

### 🔍 Objeto: `dados_faturamento`

#### `dados_faturamento.get` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/financeiro_agent.py:39 (em FinanceiroAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/financeiro_agent.py:40 (em FinanceiroAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/financeiro_agent.py:41 (em FinanceiroAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:289 (em ContextLoader._carregar_contexto_inteligente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:290 (em ContextLoader._carregar_contexto_inteligente)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `dados_financeiro`

#### `dados_financeiro.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:295 (em ContextLoader._carregar_contexto_inteligente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:296 (em ContextLoader._carregar_contexto_inteligente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:367 (em ContextLoader._carregar_contexto_inteligente)
```

### 🔍 Objeto: `dados_fretes`

#### `dados_fretes.get` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/fretes_agent.py:39 (em FretesAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/fretes_agent.py:40 (em FretesAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/fretes_agent.py:41 (em FretesAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/fretes_agent.py:42 (em FretesAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:271 (em ContextLoader._carregar_contexto_inteligente)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `dados_geral`

#### `dados_geral.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:411 (em ContextProcessor._carregar_dados_geral)
```

### 🔍 Objeto: `dados_json`

#### `dados_json.append` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:124 (em AgendamentosLoader._format_agendamentos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:143 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:131 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:125 (em FaturamentoLoader._format_faturamento_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:162 (em FretesLoader._format_fretes_results)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `dados_pedidos`

#### `dados_pedidos.get` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/pedidos_agent.py:39 (em PedidosAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/pedidos_agent.py:40 (em PedidosAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/pedidos_agent.py:41 (em PedidosAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/pedidos_agent.py:42 (em PedidosAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:265 (em ContextLoader._carregar_contexto_inteligente)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `dados_pendencias`

#### `dados_pendencias.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/financeiro_agent.py:55 (em FinanceiroAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/financeiro_agent.py:56 (em FinanceiroAgent._resumir_dados_reais)
```

### 🔍 Objeto: `dados_reais`

#### `dados_reais.get` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/embarques_agent.py:29 (em EmbarquesAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:81 (em EntregasAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/financeiro_agent.py:29 (em FinanceiroAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/fretes_agent.py:29 (em FretesAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/pedidos_agent.py:29 (em PedidosAgent._resumir_dados_reais)
```

### 🔍 Objeto: `dados_transportadoras`

#### `dados_transportadoras.get` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:117 (em EntregasAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:118 (em EntregasAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/fretes_agent.py:56 (em FretesAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/fretes_agent.py:57 (em FretesAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:277 (em ContextLoader._carregar_contexto_inteligente)
  ... e mais 2 ocorrências
```

### 🔍 Objeto: `dados_volumes`

#### `dados_volumes.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/embarques_agent.py:56 (em EmbarquesAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/embarques_agent.py:57 (em EmbarquesAgent._resumir_dados_reais)
```

### 🔍 Objeto: `daily_data`

#### `daily_data.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:366 (em PerformanceAnalyzer.detect_anomalies)
```

#### `daily_data.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:399 (em PerformanceAnalyzer._analyze_trends)
```

### 🔍 Objeto: `data`

#### `data.get` (34 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:78 (em ImportFixer.fix_imports)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:339 (em WebFlaskRoutes.api_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:393 (em WebFlaskRoutes.api_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:394 (em WebFlaskRoutes.api_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:395 (em WebFlaskRoutes.api_feedback)
  ... e mais 29 ocorrências
```

#### `data.values` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:198 (em StructuralAnalyzer._count_nested_levels)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:206 (em StructuralAnalyzer._analyze_data_types)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:225 (em StructuralAnalyzer._detect_structural_issues)
```

#### `data.strip` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_classes.py:259 (em BaseProcessor._validate_input)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:72 (em BaseValidationUtils._basic_validation)
```

#### `data.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:220 (em StructuralAnalyzer._detect_structural_issues)
```

#### `data.strftime` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:270 (em BaseCommand._format_date_br)
```

#### `data.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:663 (em SystemConfig._flatten_dict)
```

#### `data.get().strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:339 (em WebFlaskRoutes.api_query)
```

### 🔍 Objeto: `data_consistency`

#### `data_consistency.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:92 (em CriticAgent.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:101 (em CriticAgent.top-level)
```

### 🔍 Objeto: `data_context`

#### `data_context.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/structural_validator.py:109 (em StructuralAI._validate_data_relationships)
```

### 🔍 Objeto: `data_dict`

#### `data_dict.items` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:382 (em DataProcessor._clean_dict)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:471 (em DataProcessor._normalize_dict)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:561 (em DataProcessor._transform_dict_schema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:377 (em IntelligenceProcessor._normalize_dict_for_intelligence)
```

### 🔍 Objeto: `data_manager`

#### `data_manager.load_data` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/__init__.py:200 (em module.load_data)
```

### 🔍 Objeto: `data_provider`

#### `data_provider.get_data_by_domain` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:52 (em module._carregar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:69 (em module._carregar_dados_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:85 (em module._carregar_dados_transportadoras)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:101 (em module._carregar_dados_embarques)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:118 (em module._carregar_dados_faturamento)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `data_result`

#### `data_result.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:217 (em ProviderManager._provide_data_with_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:251 (em ProviderManager._provide_context_with_data)
```

### 🔍 Objeto: `database_data`

#### `database_data.get` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:288 (em SemanticEnricher._sugestoes_qualidade_banco)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:329 (em SemanticEnricher._sugestoes_campos_similares)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:366 (em SemanticEnricher._sugestoes_otimizacao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:378 (em SemanticEnricher._sugestoes_otimizacao)
```

### 🔍 Objeto: `database_reader`

#### `database_reader.obter_estatisticas_gerais` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:220 (em DiagnosticsAnalyzer.gerar_relatorio_enriquecido)
```

#### `database_reader.buscar_campos_por_nome` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:154 (em SemanticEnricher._enriquecer_via_banco)
```

#### `database_reader.analisar_dados_reais` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:170 (em SemanticEnricher._enriquecer_via_banco)
```

#### `database_reader.listar_tabelas` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:226 (em SemanticValidator.validar_consistencia_readme_banco)
```

#### `database_reader.obter_campos_tabela` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:297 (em SemanticValidator._validar_campos_modelo_tabela)
```

### 🔍 Objeto: `database_url`

#### `database_url.startswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:116 (em DatabaseConnection._try_direct_connection)
```

#### `database_url.replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:117 (em DatabaseConnection._try_direct_connection)
```

### 🔍 Objeto: `date_consistency`

#### `date_consistency.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:91 (em CriticAgent.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:100 (em CriticAgent.top-level)
```

### 🔍 Objeto: `date_obj`

#### `date_obj.strftime` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_classes.py:386 (em BaseProcessor._format_date_br)
```

### 🔍 Objeto: `datetime`

#### `datetime.now().isoformat` (285 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:320 (em DetectorModulosOrfaos.gerar_relatorio_completo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:248 (em ClassDuplicateFinder.save_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:185 (em module.find_undefined_methods)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:297 (em UninitializedVariableFinder.save_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:118 (em module.generate_report)
  ... e mais 280 ocorrências
```

#### `datetime.now().strftime` (37 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:168 (em ImportFixer._create_backup)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:342 (em DetectorModulosOrfaos.salvar_relatorio)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:172 (em ClassDuplicateFinder.generate_report)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:198 (em UninitializedVariableFinder.generate_report)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:141 (em module.generate_report)
  ... e mais 32 ocorrências
```

#### `datetime.now().date` (17 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:119 (em BaseCommand._extract_filters_advanced)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:120 (em BaseCommand._extract_filters_advanced)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:123 (em BaseCommand._extract_filters_advanced)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:124 (em BaseCommand._extract_filters_advanced)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:127 (em BaseCommand._extract_filters_advanced)
  ... e mais 12 ocorrências
```

#### `datetime.now().timestamp` (17 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:324 (em SystemConfig.register_config_watcher)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:91 (em IntelligenceCoordinator.coordinate_intelligence_operation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:25 (em ProcessorCoordinator.execute_processor_chain)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:134 (em ProcessorCoordinator.execute_parallel_processors)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:436 (em ContextLoader._carregar_contexto_inteligente)
  ... e mais 12 ocorrências
```

#### `datetime.now().hour` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:401 (em SuggestionsManager._analyze_context)
```

#### `datetime.now().weekday` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:402 (em SuggestionsManager._analyze_context)
```

### 🔍 Objeto: `db`

#### `db.session.execute` (33 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:278 (em LearningCore._atualizar_metricas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:316 (em LearningCore._salvar_historico_aprendizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:265 (em PatternLearner._salvar_padrao_otimizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:279 (em PatternLearner._salvar_padrao_otimizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:295 (em PatternLearner._salvar_padrao_otimizado)
  ... e mais 28 ocorrências
```

#### `db.session.query` (21 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:114 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:114 (em ExcelFaturamento._buscar_dados_faturamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:116 (em ExcelFretes._buscar_dados_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:124 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:183 (em ContextLoader._carregar_entregas_banco)
  ... e mais 16 ocorrências
```

#### `db.session.execute().scalar` (11 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:302 (em KnowledgeMemory.obter_estatisticas_aprendizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:307 (em KnowledgeMemory.obter_estatisticas_aprendizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:312 (em KnowledgeMemory.obter_estatisticas_aprendizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:317 (em KnowledgeMemory.obter_estatisticas_aprendizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:322 (em KnowledgeMemory.obter_estatisticas_aprendizado)
  ... e mais 6 ocorrências
```

#### `db.session.execute().fetchall` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:343 (em PatternLearner.buscar_padroes_aplicaveis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:203 (em KnowledgeMemory.buscar_grupos_aplicaveis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:258 (em KnowledgeMemory.buscar_mapeamentos_aplicaveis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:148 (em DatabaseScanner._get_postgresql_statistics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:169 (em DatabaseScanner._get_postgresql_statistics)
  ... e mais 2 ocorrências
```

#### `db.session.commit` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:290 (em LearningCore._atualizar_metricas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:332 (em LearningCore._salvar_historico_aprendizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:315 (em PatternLearner._salvar_padrao_otimizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:96 (em KnowledgeMemory.aprender_mapeamento_cliente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:165 (em KnowledgeMemory.descobrir_grupo_empresarial)
```

#### `db.session.rollback` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:297 (em LearningCore._atualizar_metricas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:339 (em LearningCore._salvar_historico_aprendizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:322 (em PatternLearner._salvar_padrao_otimizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:109 (em KnowledgeMemory.aprender_mapeamento_cliente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:183 (em KnowledgeMemory.descobrir_grupo_empresarial)
```

#### `db.session.query().filter` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:474 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:483 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:491 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:544 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:132 (em ValidationUtils._calcular_estatisticas_especificas)
```

#### `db.session.execute().fetchone` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:102 (em DatabaseScanner._get_database_version)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:105 (em DatabaseScanner._get_database_version)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:108 (em DatabaseScanner._get_database_version)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:353 (em DatabaseScanner._get_postgresql_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:375 (em DatabaseScanner._get_mysql_performance)
```

#### `db.session.query().filter().distinct` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:474 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:483 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:491 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:544 (em ContextLoader._carregar_todos_clientes_sistema)
```

#### `db.engine.dialect.name` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:50 (em DatabaseScanner.discover_database_schema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:99 (em DatabaseScanner._get_database_version)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:129 (em DatabaseScanner._get_table_statistics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:327 (em DatabaseScanner._get_performance_info)
```

#### `db.engine.dialect` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:50 (em DatabaseScanner.discover_database_schema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:99 (em DatabaseScanner._get_database_version)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:129 (em DatabaseScanner._get_table_statistics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:327 (em DatabaseScanner._get_performance_info)
```

#### `db.engine.pool` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:331 (em DatabaseScanner._get_performance_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:332 (em DatabaseScanner._get_performance_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:333 (em DatabaseScanner._get_performance_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:334 (em DatabaseScanner._get_performance_info)
```

#### `db.session.query().join` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:114 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:116 (em ExcelFretes._buscar_dados_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:124 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `db.session.execute().first` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:265 (em PatternLearner._salvar_padrao_otimizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:57 (em KnowledgeMemory.aprender_mapeamento_cliente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:138 (em KnowledgeMemory.descobrir_grupo_empresarial)
```

#### `db.session.query().filter().distinct().all` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:474 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:483 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:491 (em ContextLoader._carregar_todos_clientes_sistema)
```

#### `db.session.query().filter().distinct().count` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:544 (em ContextLoader._carregar_todos_clientes_sistema)
```

#### `db.engine.driver` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:51 (em DatabaseScanner.discover_database_schema)
```

### 🔍 Objeto: `db_conn`

#### `db_conn.get_inspector` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:443 (em DataAnalyzer.analisar_tabela_completa)
```

### 🔍 Objeto: `db_status`

#### `db_status.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:298 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:299 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
```

### 🔍 Objeto: `dependencies`

#### `dependencies.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_classes.py:244 (em BaseProcessor._check_dependencies)
```

### 🔍 Objeto: `detected`

#### `detected.append` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:160 (em StructuralAnalyzer.detect_patterns)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:166 (em StructuralAnalyzer.detect_patterns)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:171 (em StructuralAnalyzer.detect_patterns)
```

### 🔍 Objeto: `detected_commands`

#### `detected_commands.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:312 (em AutoCommandProcessor._detect_commands)
```

### 🔍 Objeto: `detected_domains`

#### `detected_domains.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:221 (em ContextEnricher._enrich_domain_context)
```

### 🔍 Objeto: `detector`

#### `detector.gerar_relatorio_completo` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:391 (em module.main)
```

#### `detector.salvar_relatorio` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:394 (em module.main)
```

#### `detector.detectar_grupo_na_consulta` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:526 (em ContextLoader._carregar_todos_clientes_sistema)
```

### 🔍 Objeto: `detector_grupos`

#### `detector_grupos.detectar_grupo_na_consulta` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:136 (em QueryAnalyzer._extract_entities)
```

### 🔍 Objeto: `df`

#### `df.columns` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:268 (em DataProcessor.aggregate_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:283 (em DataProcessor.aggregate_data)
```

#### `df.groupby().agg().reset_index` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:284 (em DataProcessor.aggregate_data)
```

#### `df.groupby().agg` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:284 (em DataProcessor.aggregate_data)
```

#### `df.groupby` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:284 (em DataProcessor.aggregate_data)
```

#### `df.agg().to_frame().T` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:287 (em DataProcessor.aggregate_data)
```

#### `df.agg().to_frame` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:287 (em DataProcessor.aggregate_data)
```

#### `df.agg` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:287 (em DataProcessor.aggregate_data)
```

### 🔍 Objeto: `diagnostico`

#### `diagnostico.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:173 (em DiagnosticsAnalyzer._determinar_status_geral)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:174 (em DiagnosticsAnalyzer._determinar_status_geral)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:293 (em ScanningManager.executar_diagnostico_completo)
```

### 🔍 Objeto: `dict_node`

#### `dict_node.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:209 (em CodeScanner._extract_dict_value)
```

#### `dict_node.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:209 (em CodeScanner._extract_dict_value)
```

### 🔍 Objeto: `dir_name`

#### `dir_name.startswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:77 (em module.contar_arquivos_detalhado)
```

### 🔍 Objeto: `dir_path`

#### `dir_path.exists` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:103 (em ValidadorSistemaCompleto._testar_estrutura_diretorios)
```

### 🔍 Objeto: `directory`

#### `directory.rglob` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:35 (em ClassDuplicateFinder.scan_directory)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:97 (em UninitializedVariableFinder.scan_directory)
```

### 🔍 Objeto: `dirs`

#### `dirs.copy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:61 (em StructureScanner.discover_project_structure)
```

### 🔍 Objeto: `distribuicao`

#### `distribuicao.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:442 (em AutoMapper._melhorar_termos_com_analise)
```

### 🔍 Objeto: `doc`

#### `doc.ents` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:242 (em NLPEnhancedAnalyzer._extrair_entidades_spacy)
```

### 🔍 Objeto: `domain`

#### `domain.lower` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:107 (em LoaderManager.load_data_by_domain)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/__init__.py:101 (em module.get_best_mapper_for_domain)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/__init__.py:32 (em module.get_domain_mapper)
```

#### `domain.title` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:149 (em CoordinatorManager._load_domain_agents)
```

#### `domain.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:259 (em ContextEnricher._calculate_context_score)
```

#### `domain.lower().strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:107 (em LoaderManager.load_data_by_domain)
```

### 🔍 Objeto: `domain_data`

#### `domain_data.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:181 (em LoaderManager.load_multiple_domains)
```

### 🔍 Objeto: `domain_keywords`

#### `domain_keywords.items` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:123 (em QueryAnalyzer._detect_domains)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:229 (em CoordinatorManager._select_best_coordinator)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:219 (em ContextEnricher._enrich_domain_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:222 (em LoaderManager.get_best_loader_for_query)
```

### 🔍 Objeto: `domain_knowledge`

#### `domain_knowledge.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:220 (em SmartBaseAgent.top-level)
```

### 🔍 Objeto: `domain_loaders`

#### `domain_loaders.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/__init__.py:98 (em module.get_domain_loaders)
```

### 🔍 Objeto: `domain_mappers`

#### `domain_mappers.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/__init__.py:101 (em module.get_best_mapper_for_domain)
```

### 🔍 Objeto: `domain_scores`

#### `domain_scores.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:238 (em LoaderManager.get_best_loader_for_query)
```

### 🔍 Objeto: `domains`

#### `domains.items` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:114 (em MetacognitiveAnalyzer._assess_domain_coverage)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:180 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `domains.append` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:125 (em QueryAnalyzer._detect_domains)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:252 (em SemanticAnalyzer._identify_domains)
```

### 🔍 Objeto: `dominios`

#### `dominios.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:253 (em ContextProcessor._detectar_dominio)
```

### 🔍 Objeto: `duration`

#### `duration.seconds` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:188 (em ConversationMemory._calculate_duration)
```

### 🔍 Objeto: `durations`

#### `durations.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:720 (em SessionOrchestrator.get_session_stats)
```

### 🔍 Objeto: `e`

#### `e.data_entrega_prevista` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:204 (em ContextLoader._carregar_entregas_banco)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:204 (em ContextLoader._carregar_entregas_banco)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:102 (em ValidationUtils._calcular_metricas_prazo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:103 (em ValidationUtils._calcular_metricas_prazo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:109 (em ValidationUtils._calcular_metricas_prazo)
  ... e mais 2 ocorrências
```

#### `e.data_hora_entrega_realizada` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:99 (em ValidationUtils._calcular_metricas_prazo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:102 (em ValidationUtils._calcular_metricas_prazo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:103 (em ValidationUtils._calcular_metricas_prazo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:109 (em ValidationUtils._calcular_metricas_prazo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:110 (em ValidationUtils._calcular_metricas_prazo)
```

#### `e.lead_time` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:119 (em ValidationUtils._calcular_metricas_prazo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:119 (em ValidationUtils._calcular_metricas_prazo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:119 (em ValidationUtils._calcular_metricas_prazo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:119 (em ValidationUtils._calcular_metricas_prazo)
```

#### `e.data_hora_entrega_realizada.date` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:103 (em ValidationUtils._calcular_metricas_prazo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:109 (em ValidationUtils._calcular_metricas_prazo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:110 (em ValidationUtils._calcular_metricas_prazo)
```

#### `e.data_embarque` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:203 (em ContextLoader._carregar_entregas_banco)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:203 (em ContextLoader._carregar_entregas_banco)
```

#### `e.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:200 (em ContextLoader._carregar_entregas_banco)
```

#### `e.cliente` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:201 (em ContextLoader._carregar_entregas_banco)
```

#### `e.numero_nf` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:202 (em ContextLoader._carregar_entregas_banco)
```

#### `e.data_embarque.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:203 (em ContextLoader._carregar_entregas_banco)
```

#### `e.data_entrega_prevista.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:204 (em ContextLoader._carregar_entregas_banco)
```

#### `e.entregue` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:205 (em ContextLoader._carregar_entregas_banco)
```

### 🔍 Objeto: `elt`

#### `elt.func` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:196 (em CodeScanner._extract_validators)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:197 (em CodeScanner._extract_validators)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:198 (em CodeScanner._extract_validators)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:199 (em CodeScanner._extract_validators)
```

#### `elt.elts` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:224 (em CodeScanner._extract_choices)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:225 (em CodeScanner._extract_choices)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:226 (em CodeScanner._extract_choices)
```

#### `elt.func.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:197 (em CodeScanner._extract_validators)
```

#### `elt.func.attr` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:199 (em CodeScanner._extract_validators)
```

### 🔍 Objeto: `embarque`

#### `embarque.data_embarque` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:288 (em DataProvider._serialize_embarque)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:288 (em DataProvider._serialize_embarque)
```

#### `embarque.valor_total` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:291 (em DataProvider._serialize_embarque)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:291 (em DataProvider._serialize_embarque)
```

#### `embarque.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:286 (em DataProvider._serialize_embarque)
```

#### `embarque.numero` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:287 (em DataProvider._serialize_embarque)
```

#### `embarque.data_embarque.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:288 (em DataProvider._serialize_embarque)
```

#### `embarque.destino` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:289 (em DataProvider._serialize_embarque)
```

#### `embarque.status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:290 (em DataProvider._serialize_embarque)
```

### 🔍 Objeto: `end_date`

#### `end_date.replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:263 (em BaseValidationUtils.validate_date_range)
```

### 🔍 Objeto: `end_time`

#### `end_time.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:575 (em IntelligenceCoordinator._execute_component_operation)
```

### 🔍 Objeto: `engine`

#### `engine.generate_suggestions` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/__init__.py:101 (em module.generate_suggestions)
```

### 🔍 Objeto: `enriched`

#### `enriched.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:484 (em SuggestionsManager._enrich_suggestions)
```

### 🔍 Objeto: `enriched_context`

#### `enriched_context.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:58 (em ContextEnricher.enrich_context)
```

#### `enriched_context.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:242 (em ContextEnricher._calculate_context_score)
```

### 🔍 Objeto: `enrichments`

#### `enrichments.get` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:245 (em ContextEnricher._calculate_context_score)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:249 (em ContextEnricher._calculate_context_score)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:253 (em ContextEnricher._calculate_context_score)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:258 (em ContextEnricher._calculate_context_score)
```

### 🔍 Objeto: `enriquecimentos`

#### `enriquecimentos.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:445 (em SemanticEnricher._calcular_estatisticas_batch)
```

### 🔍 Objeto: `ent`

#### `ent.text` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:244 (em NLPEnhancedAnalyzer._extrair_entidades_spacy)
```

#### `ent.label_` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:245 (em NLPEnhancedAnalyzer._extrair_entidades_spacy)
```

#### `ent.start_char` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:246 (em NLPEnhancedAnalyzer._extrair_entidades_spacy)
```

#### `ent.end_char` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:247 (em NLPEnhancedAnalyzer._extrair_entidades_spacy)
```

### 🔍 Objeto: `entidades`

#### `entidades.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:243 (em NLPEnhancedAnalyzer._extrair_entidades_spacy)
```

### 🔍 Objeto: `entities`

#### `entities.append` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:139 (em QueryAnalyzer._extract_entities)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:144 (em QueryAnalyzer._extract_entities)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:153 (em QueryAnalyzer._extract_entities)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:166 (em QueryAnalyzer._extract_entities)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:171 (em QueryAnalyzer._extract_entities)
  ... e mais 2 ocorrências
```

#### `entities.extend` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/context_provider.py:495 (em ContextProvider._extract_simple_entities)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/context_provider.py:499 (em ContextProvider._extract_simple_entities)
```

### 🔍 Objeto: `entity_keywords`

#### `entity_keywords.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:149 (em ContextEnricher._enrich_semantic_context)
```

### 🔍 Objeto: `entrega`

#### `entrega.data_entrega_prevista` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:266 (em DataProvider._serialize_entrega)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:266 (em DataProvider._serialize_entrega)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:63 (em ValidationUtils._verificar_prazo_entrega)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:66 (em ValidationUtils._verificar_prazo_entrega)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:69 (em ValidationUtils._calcular_dias_atraso)
  ... e mais 2 ocorrências
```

#### `entrega.data_hora_entrega_realizada` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:267 (em DataProvider._serialize_entrega)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:267 (em DataProvider._serialize_entrega)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:63 (em ValidationUtils._verificar_prazo_entrega)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:66 (em ValidationUtils._verificar_prazo_entrega)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:69 (em ValidationUtils._calcular_dias_atraso)
  ... e mais 2 ocorrências
```

#### `entrega.numero_nf` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:131 (em AgendamentosLoader._format_agendamentos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:424 (em ContextProcessor._serialize_entrega)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:262 (em DataProvider._serialize_entrega)
```

#### `entrega.data_embarque` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:426 (em ContextProcessor._serialize_entrega)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:265 (em DataProvider._serialize_entrega)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:265 (em DataProvider._serialize_entrega)
```

#### `entrega.data_hora_entrega_realizada.date` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:66 (em ValidationUtils._verificar_prazo_entrega)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:72 (em ValidationUtils._calcular_dias_atraso)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:73 (em ValidationUtils._calcular_dias_atraso)
```

#### `entrega.cliente` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:130 (em AgendamentosLoader._format_agendamentos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:261 (em DataProvider._serialize_entrega)
```

#### `entrega.destino` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:132 (em AgendamentosLoader._format_agendamentos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:263 (em DataProvider._serialize_entrega)
```

#### `entrega.id` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:423 (em ContextProcessor._serialize_entrega)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:260 (em DataProvider._serialize_entrega)
```

#### `entrega.status_finalizacao` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:427 (em ContextProcessor._serialize_entrega)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:264 (em DataProvider._serialize_entrega)
```

#### `entrega.nome_cliente` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:425 (em ContextProcessor._serialize_entrega)
```

#### `entrega.entregue` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:428 (em ContextProcessor._serialize_entrega)
```

#### `entrega.data_embarque.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:265 (em DataProvider._serialize_entrega)
```

#### `entrega.data_entrega_prevista.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:266 (em DataProvider._serialize_entrega)
```

#### `entrega.data_hora_entrega_realizada.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:267 (em DataProvider._serialize_entrega)
```

#### `entrega.vendedor` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:268 (em DataProvider._serialize_entrega)
```

### 🔍 Objeto: `entregas_cache`

#### `entregas_cache.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:307 (em ContextLoader._carregar_contexto_inteligente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:378 (em ContextLoader._carregar_contexto_inteligente)
```

### 🔍 Objeto: `errors`

#### `errors.append` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:480 (em AutoCommandProcessor._validate_command_syntax)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:483 (em AutoCommandProcessor._validate_command_syntax)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:487 (em AutoCommandProcessor._validate_command_syntax)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:201 (em TestLoopPrevention.make_request)
```

### 🔍 Objeto: `erros`

#### `erros.append` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:179 (em BaseMapper.validar_mapeamentos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:182 (em BaseMapper.validar_mapeamentos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:184 (em BaseMapper.validar_mapeamentos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:186 (em BaseMapper.validar_mapeamentos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:189 (em BaseMapper.validar_mapeamentos)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `esqueleto`

#### `esqueleto.gerar_excel_faturamento` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:157 (em ExcelOrchestrator._processar_excel_interno)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:227 (em ExcelOrchestrator._tentar_fallback_esqueletos)
```

#### `esqueleto.gerar_excel_fretes` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:159 (em ExcelOrchestrator._processar_excel_interno)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:221 (em ExcelOrchestrator._tentar_fallback_esqueletos)
```

#### `esqueleto.gerar_excel_pedidos` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:161 (em ExcelOrchestrator._processar_excel_interno)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:223 (em ExcelOrchestrator._tentar_fallback_esqueletos)
```

#### `esqueleto.gerar_excel_entregas` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:163 (em ExcelOrchestrator._processar_excel_interno)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:225 (em ExcelOrchestrator._tentar_fallback_esqueletos)
```

### 🔍 Objeto: `estado`

#### `estado.upper` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:184 (em QueryAnalyzer._extract_entities)
```

#### `estado.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:147 (em BaseCommand._extract_filters_advanced)
```

### 🔍 Objeto: `estatisticas`

#### `estatisticas.get` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:144 (em DiagnosticsAnalyzer._avaliar_qualidade_geral)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:149 (em DiagnosticsAnalyzer._avaliar_qualidade_geral)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:151 (em DiagnosticsAnalyzer._avaliar_qualidade_geral)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:429 (em LearningCore._avaliar_saude_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:434 (em LearningCore._avaliar_saude_sistema)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `etapa_config`

#### `etapa_config.get` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:180 (em WorkflowOrchestrator._executar_etapas_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:202 (em WorkflowOrchestrator._executar_etapas_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:211 (em WorkflowOrchestrator._executar_etapas_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:235 (em WorkflowOrchestrator._executar_etapa)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:236 (em WorkflowOrchestrator._executar_etapa)
```

### 🔍 Objeto: `etapas_concluidas`

#### `etapas_concluidas.add` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:193 (em WorkflowOrchestrator._executar_etapas_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:207 (em WorkflowOrchestrator._executar_etapas_workflow)
```

### 🔍 Objeto: `existe`

#### `existe.id` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:287 (em PatternLearner._salvar_padrao_otimizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:290 (em PatternLearner._salvar_padrao_otimizado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:77 (em KnowledgeMemory.aprender_mapeamento_cliente)
```

#### `existe.confidence` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:276 (em PatternLearner._salvar_padrao_otimizado)
```

#### `existe.usage_count` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:277 (em PatternLearner._salvar_padrao_otimizado)
```

### 🔍 Objeto: `existing_pattern`

#### `existing_pattern.examples.extend` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:199 (em HumanInLoopLearning._create_learning_pattern)
```

#### `existing_pattern.examples` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:199 (em HumanInLoopLearning._create_learning_pattern)
```

#### `existing_pattern.confidence_score` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:200 (em HumanInLoopLearning._create_learning_pattern)
```

#### `existing_pattern.frequency` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:201 (em HumanInLoopLearning._create_learning_pattern)
```

### 🔍 Objeto: `expansions`

#### `expansions.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:215 (em SemanticLoopProcessor._expand_unmapped_terms)
```

### 🔍 Objeto: `expired_keys`

#### `expired_keys.append` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:913 (em IntelligenceCoordinator._optimize_ai_cache)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:350 (em SystemMemory.cleanup_expired_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:725 (em SuggestionsManager._optimize_cache)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:166 (em ScannersCache._cleanup_expired_cache)
```

### 🔍 Objeto: `expired_sessions`

#### `expired_sessions.append` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:312 (em ConversationManager.cleanup_expired_conversations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:245 (em ContextMemory.cleanup_expired_contexts)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:674 (em SessionOrchestrator.cleanup_expired_sessions)
```

### 🔍 Objeto: `external_api`

#### `external_api.process_query` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:188 (em StandaloneIntegration.process_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:110 (em WebIntegrationAdapter.process_query_sync)
```

#### `external_api.initialize_complete_system` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:118 (em StandaloneIntegration.initialize_system)
```

#### `external_api.get_system_status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:221 (em WebIntegrationAdapter.get_system_status)
```

#### `external_api.claude_client` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:273 (em WebIntegrationAdapter.claude_client)
```

### 🔍 Objeto: `f`

#### `f.read` (19 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:172 (em ImportFixer._create_backup)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:243 (em ImportFixer._add_get_function)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:87 (em DetectorModulosOrfaos._analisar_pasta)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:155 (em DetectorModulosOrfaos._extrair_imports)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:46 (em ClassDuplicateFinder.scan_file)
  ... e mais 14 ocorrências
```

#### `f.endswith` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:58 (em ImportFixer._find_latest_error_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:62 (em StructureScanner.discover_project_structure)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:63 (em StructureScanner.discover_project_structure)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:64 (em StructureScanner.discover_project_structure)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:65 (em StructureScanner.discover_project_structure)
  ... e mais 1 ocorrências
```

#### `f.feedback_text` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:146 (em HumanInLoopLearning._analyze_feedback_patterns)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:154 (em HumanInLoopLearning._analyze_feedback_patterns)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:160 (em HumanInLoopLearning._analyze_feedback_patterns)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:168 (em HumanInLoopLearning._analyze_feedback_patterns)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:174 (em HumanInLoopLearning._analyze_feedback_patterns)
  ... e mais 1 ocorrências
```

#### `f.write` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:175 (em ImportFixer._create_backup)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:259 (em ImportFixer._add_get_function)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:244 (em ClassDuplicateFinder.save_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:242 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:293 (em UninitializedVariableFinder.save_results)
```

#### `f.readlines` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:162 (em module.contar_linhas_codigo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:197 (em module.verificar_modulos_especiais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:113 (em ImportFixer._fix_file)
```

#### `f.feedback_text.lower` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:146 (em HumanInLoopLearning._analyze_feedback_patterns)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:160 (em HumanInLoopLearning._analyze_feedback_patterns)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:174 (em HumanInLoopLearning._analyze_feedback_patterns)
```

#### `f.startswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:58 (em ImportFixer._find_latest_error_file)
```

#### `f.writelines` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:146 (em ImportFixer._fix_file)
```

#### `f.feedback_type` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:147 (em HumanInLoopLearning._analyze_feedback_patterns)
```

#### `f.feedback_id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:275 (em HumanInLoopLearning.apply_improvement)
```

#### `f.timestamp` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:288 (em HumanInLoopLearning.generate_learning_report)
```

### 🔍 Objeto: `factories`

#### `factories.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:106 (em SpecialistCoordinator.get_agent)
```

### 🔍 Objeto: `fallback`

#### `fallback.value` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:457 (em OrchestratorManager._detect_appropriate_orchestrator)
```

#### `fallback.is_flask_available` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/__init__.py:133 (em module.initialize_flask_fallback)
```

### 🔍 Objeto: `fatores`

#### `fatores.append` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:499 (em FieldSearcher._analisar_fatores_similaridade)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:503 (em FieldSearcher._analisar_fatores_similaridade)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:505 (em FieldSearcher._analisar_fatores_similaridade)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:508 (em FieldSearcher._analisar_fatores_similaridade)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:511 (em FieldSearcher._analisar_fatores_similaridade)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `faturamento`

#### `faturamento.data_fatura` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:300 (em DataProvider._serialize_faturamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:300 (em DataProvider._serialize_faturamento)
```

#### `faturamento.valor_total` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:301 (em DataProvider._serialize_faturamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:301 (em DataProvider._serialize_faturamento)
```

#### `faturamento.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:297 (em DataProvider._serialize_faturamento)
```

#### `faturamento.numero_nf` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:298 (em DataProvider._serialize_faturamento)
```

#### `faturamento.nome_cliente` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:299 (em DataProvider._serialize_faturamento)
```

#### `faturamento.data_fatura.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:300 (em DataProvider._serialize_faturamento)
```

#### `faturamento.origem` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:302 (em DataProvider._serialize_faturamento)
```

#### `faturamento.incoterm` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:303 (em DataProvider._serialize_faturamento)
```

### 🔍 Objeto: `feedback`

#### `feedback.get` (10 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:563 (em WebFlaskRoutes._record_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:212 (em AdaptiveLearning.update_learning_from_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:218 (em AdaptiveLearning.update_learning_from_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:219 (em AdaptiveLearning.update_learning_from_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:516 (em AdaptiveLearning._handle_negative_feedback)
  ... e mais 5 ocorrências
```

#### `feedback.feedback_text` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:124 (em HumanInLoopLearning._process_critical_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:133 (em HumanInLoopLearning._process_critical_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:372 (em HumanInLoopLearning._analyze_trends)
```

#### `feedback.severity` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:101 (em HumanInLoopLearning.capture_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:307 (em HumanInLoopLearning.generate_learning_report)
```

#### `feedback.feedback_id` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:118 (em HumanInLoopLearning._process_critical_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:123 (em HumanInLoopLearning._process_critical_feedback)
```

#### `feedback.timestamp` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:126 (em HumanInLoopLearning._process_critical_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:357 (em HumanInLoopLearning._analyze_trends)
```

#### `feedback.feedback_type` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:303 (em HumanInLoopLearning.generate_learning_report)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:406 (em HumanInLoopLearning._calculate_satisfaction_score)
```

#### `feedback.suggested_improvement` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:125 (em HumanInLoopLearning._process_critical_feedback)
```

#### `feedback.timestamp.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:126 (em HumanInLoopLearning._process_critical_feedback)
```

#### `feedback.context` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:127 (em HumanInLoopLearning._process_critical_feedback)
```

#### `feedback.feedback_type.value` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:303 (em HumanInLoopLearning.generate_learning_report)
```

#### `feedback.severity.value` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:307 (em HumanInLoopLearning.generate_learning_report)
```

#### `feedback.user_id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:311 (em HumanInLoopLearning.generate_learning_report)
```

#### `feedback.timestamp.strftime` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:357 (em HumanInLoopLearning._analyze_trends)
```

#### `feedback.feedback_text.lower().split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:372 (em HumanInLoopLearning._analyze_trends)
```

#### `feedback.feedback_text.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:372 (em HumanInLoopLearning._analyze_trends)
```

### 🔍 Objeto: `feedback_processor`

#### `feedback_processor.processar_feedback_completo` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:558 (em WebFlaskRoutes._record_feedback)
```

### 🔍 Objeto: `field_info`

#### `field_info.get` (13 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:154 (em CodeScanner._parse_form_field)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:154 (em CodeScanner._parse_form_field)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:157 (em CodeScanner._parse_form_field)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:158 (em CodeScanner._parse_form_field)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:159 (em CodeScanner._parse_form_field)
  ... e mais 8 ocorrências
```

### 🔍 Objeto: `field_mapper`

#### `field_mapper.map_fields` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/__init__.py:84 (em module.map_query_fields)
```

### 🔍 Objeto: `field_mapping`

#### `field_mapping.source_field` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:91 (em FieldMapper.add_mapping)
```

#### `field_mapping.target_field` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:91 (em FieldMapper.add_mapping)
```

### 🔍 Objeto: `fila`

#### `fila.pop` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:383 (em RelationshipMapper.obter_caminho_relacionamentos)
```

#### `fila.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:404 (em RelationshipMapper.obter_caminho_relacionamentos)
```

### 🔍 Objeto: `file`

#### `file.endswith` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:65 (em module.contar_arquivos_detalhado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:158 (em module.contar_linhas_codigo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:193 (em module.verificar_modulos_especiais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:58 (em module.categorizar_todos_modulos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:48 (em ImportChecker.check_directory)
  ... e mais 2 ocorrências
```

#### `file.startswith` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:69 (em module.contar_arquivos_detalhado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:48 (em ImportChecker.check_directory)
```

#### `file.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:203 (em module.verificar_modulos_especiais)
```

### 🔍 Objeto: `file_errors`

#### `file_errors.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:78 (em ImportChecker.check_file)
```

### 🔍 Objeto: `file_module`

#### `file_module.split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:158 (em ImportChecker.check_import)
```

### 🔍 Objeto: `file_path`

#### `file_path.relative_to` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:57 (em FileScanner.discover_all_templates)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:315 (em FileScanner.search_in_files)
```

#### `file_path.stat().st_size` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:61 (em FileScanner.discover_all_templates)
```

#### `file_path.stat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:61 (em FileScanner.discover_all_templates)
```

### 🔍 Objeto: `file_types`

#### `file_types.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:261 (em FileScanner.list_directory_contents)
```

### 🔍 Objeto: `filepath`

#### `filepath.relative_to` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:86 (em ClassDuplicateFinder.extract_class_info)
```

### 🔍 Objeto: `files`

#### `files.sort` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:63 (em ImportFixer._find_latest_error_file)
```

### 🔍 Objeto: `filtered_data`

#### `filtered_data.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:331 (em DataProcessor.filter_data)
```

### 🔍 Objeto: `filtered_queue`

#### `filtered_queue.sort` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:251 (em HumanInLoopLearning.get_improvement_suggestions)
```

### 🔍 Objeto: `filters`

#### `filters.get` (52 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:56 (em AgendamentosLoader._build_agendamentos_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:66 (em AgendamentosLoader._build_agendamentos_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:74 (em AgendamentosLoader._build_agendamentos_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:142 (em AgendamentosLoader._format_agendamentos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:143 (em AgendamentosLoader._format_agendamentos_results)
  ... e mais 47 ocorrências
```

#### `filters.items` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:147 (em DatabaseLoader.load_table_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:589 (em DataProcessor._apply_filters)
```

#### `filters.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/__init__.py:194 (em module.load_data)
```

### 🔍 Objeto: `filtros`

#### `filtros.get` (42 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:168 (em BaseCommand._log_command)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:169 (em BaseCommand._log_command)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:171 (em CursorCommands._analisar_codigo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:155 (em DevCommands._construir_contexto_projeto)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:333 (em DevCommands._template_modulo_fallback)
  ... e mais 37 ocorrências
```

#### `filtros.items` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:235 (em BaseCommand._generate_cache_key)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:358 (em module.create_excel_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:304 (em ExcelOrchestrator._gerar_excel_geral_multi)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:98 (em ExcelEntregas._gerar_excel_entregas_interno)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:98 (em ExcelFaturamento._gerar_excel_faturamento_interno)
  ... e mais 2 ocorrências
```

#### `filtros.get().lower().replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:333 (em DevCommands._template_modulo_fallback)
```

#### `filtros.get().lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:333 (em DevCommands._template_modulo_fallback)
```

### 🔍 Objeto: `filtros_usuario`

#### `filtros_usuario.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:162 (em ValidationUtils._calcular_estatisticas_especificas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:177 (em ValidationUtils._calcular_estatisticas_especificas)
```

### 🔍 Objeto: `finder`

#### `finder.stats` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:279 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:279 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:324 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:325 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:326 (em module.main)
  ... e mais 2 ocorrências
```

#### `finder.duplicates` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:284 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:285 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:289 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:294 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:295 (em module.main)
```

#### `finder.root_path.absolute` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:276 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:321 (em module.main)
```

#### `finder.root_path` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:276 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:321 (em module.main)
```

#### `finder.scan_directory` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:277 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:322 (em module.main)
```

#### `finder.save_results` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:301 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:336 (em module.main)
```

#### `finder.find_duplicates` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:282 (em module.main)
```

#### `finder.duplicates.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:289 (em module.main)
```

#### `finder.uninitialized_vars` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:329 (em module.main)
```

### 🔍 Objeto: `first_arg`

#### `first_arg.value` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:297 (em StructureScanner._extract_field_info)
```

#### `first_arg.s` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:299 (em StructureScanner._extract_field_info)
```

### 🔍 Objeto: `fixer`

#### `fixer.fix_imports` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:272 (em module.main)
```

#### `fixer.create_fix_functions` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:275 (em module.main)
```

### 🔍 Objeto: `fk`

#### `fk.get` (13 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:289 (em DatabaseScanner._analyze_relationships)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:294 (em DatabaseScanner._analyze_relationships)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:295 (em DatabaseScanner._analyze_relationships)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:223 (em MetadataReader._obter_constraints_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:224 (em MetadataReader._obter_constraints_tabela)
  ... e mais 8 ocorrências
```

### 🔍 Objeto: `flask`

#### `flask.request.headers.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:808 (em SessionOrchestrator._get_user_agent)
```

#### `flask.request.headers` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:808 (em SessionOrchestrator._get_user_agent)
```

#### `flask.request` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:808 (em SessionOrchestrator._get_user_agent)
```

### 🔍 Objeto: `flask_fallback`

#### `flask_fallback.is_flask_available` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/__init__.py:260 (em module.top-level)
```

### 🔍 Objeto: `flask_status`

#### `flask_status.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:201 (em CursorMonitor.display_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:202 (em CursorMonitor.display_status)
```

#### `flask_status.get().upper` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:202 (em CursorMonitor.display_status)
```

### 🔍 Objeto: `flattened`

#### `flattened.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:667 (em SystemConfig._flatten_dict)
```

### 🔍 Objeto: `fnmatch`

#### `fnmatch.fnmatch` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:725 (em SystemConfig._key_matches_pattern)
```

### 🔍 Objeto: `focused_insights`

#### `focused_insights.extend` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:636 (em IntelligenceProcessor._focused_synthesis)
```

### 🔍 Objeto: `folder_stats`

#### `folder_stats.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:225 (em ClassDuplicateFinder.generate_report)
```

### 🔍 Objeto: `forms`

#### `forms.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:54 (em CodeScanner.discover_all_forms)
```

### 🔍 Objeto: `forms_file`

#### `forms_file.exists` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:53 (em CodeScanner.discover_all_forms)
```

### 🔍 Objeto: `frete`

#### `frete.id` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:203 (em ExcelFretes._criar_aba_fretes_principal)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:435 (em ContextProcessor._serialize_frete)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:320 (em DataProvider._serialize_frete)
```

#### `frete.valor_cotado` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:437 (em ContextProcessor._serialize_frete)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:322 (em DataProvider._serialize_frete)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:322 (em DataProvider._serialize_frete)
```

#### `frete.valor_considerado` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:438 (em ContextProcessor._serialize_frete)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:323 (em DataProvider._serialize_frete)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:323 (em DataProvider._serialize_frete)
```

#### `frete.data_cotacao` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:439 (em ContextProcessor._serialize_frete)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:325 (em DataProvider._serialize_frete)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:325 (em DataProvider._serialize_frete)
```

#### `frete.nome_cliente` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:436 (em ContextProcessor._serialize_frete)
```

#### `frete.status_aprovacao` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:440 (em ContextProcessor._serialize_frete)
```

#### `frete.transportadora` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:321 (em DataProvider._serialize_frete)
```

#### `frete.status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:324 (em DataProvider._serialize_frete)
```

#### `frete.data_cotacao.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:325 (em DataProvider._serialize_frete)
```

### 🔍 Objeto: `full_path`

#### `full_path.exists` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:190 (em FileScanner.read_file_content)
```

#### `full_path.stat().st_size` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:198 (em FileScanner.read_file_content)
```

#### `full_path.stat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:198 (em FileScanner.read_file_content)
```

### 🔍 Objeto: `func`

#### `func.__name__` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/performance_cache.py:89 (em module.wrapper)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/performance_cache.py:91 (em module.wrapper)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/performance_cache.py:93 (em module.wrapper)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/performance_cache.py:99 (em module.wrapper)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:293 (em module.wrapper)
  ... e mais 2 ocorrências
```

### 🔍 Objeto: `func_code`

#### `func_code.strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:251 (em ImportFixer._add_get_function)
```

### 🔍 Objeto: `funcoes`

#### `funcoes.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:109 (em DetectorModulosOrfaos._extrair_definicoes)
```

### 🔍 Objeto: `future`

#### `future.result` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:215 (em IntelligenceCoordinator.coordinate_multi_ai_synthesis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:441 (em IntelligenceCoordinator._execute_parallel_intelligence)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:512 (em IntelligenceCoordinator._execute_hybrid_intelligence)
```

### 🔍 Objeto: `futures`

#### `futures.append` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:210 (em IntelligenceCoordinator.coordinate_multi_ai_synthesis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:436 (em IntelligenceCoordinator._execute_parallel_intelligence)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:508 (em IntelligenceCoordinator._execute_hybrid_intelligence)
```

### 🔍 Objeto: `fuzz`

#### `fuzz.ratio` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:196 (em NLPEnhancedAnalyzer._aplicar_correcoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:106 (em BaseMapper.buscar_mapeamento_fuzzy)
```

#### `fuzz.partial_ratio` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:285 (em NLPEnhancedAnalyzer._calcular_similaridades)
```

### 🔍 Objeto: `get_cache()`

#### `get_cache().get_readme_scanner` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:234 (em module.cached_readme_scanner)
```

#### `get_cache().get_database_scanner` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:243 (em module.cached_database_scanner)
```

### 🔍 Objeto: `get_commands_status()`

#### `get_commands_status().values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:365 (em module.top-level)
```

### 🔍 Objeto: `get_flask_fallback()`

#### `get_flask_fallback().get_app` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:289 (em module.get_app)
```

#### `get_flask_fallback().get_model` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:293 (em module.get_model)
```

#### `get_flask_fallback().get_db` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:297 (em module.get_db)
```

#### `get_flask_fallback().get_current_user` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:301 (em module.get_current_user)
```

#### `get_flask_fallback().is_flask_available` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:305 (em module.is_flask_available)
```

#### `get_flask_fallback().get_config` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:309 (em module.get_config)
```

### 🔍 Objeto: `get_performance_analyzer()`

#### `get_performance_analyzer().analyze_ai_performance` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:631 (em module.analyze_system_performance)
```

### 🔍 Objeto: `get_security_guard()`

#### `get_security_guard().validate_user_access` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:456 (em module.validate_user_access)
```

#### `get_security_guard().validate_input` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:460 (em module.validate_input)
```

#### `get_security_guard().sanitize_input` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:464 (em module.sanitize_input)
```

### 🔍 Objeto: `get_session_memory()`

#### `get_session_memory().store_session` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:404 (em module.store_session_data)
```

#### `get_session_memory().get_session` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:416 (em module.get_session_data)
```

### 🔍 Objeto: `get_session_orchestrator()`

#### `get_session_orchestrator().create_session` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:1107 (em module.create_ai_session)
```

#### `get_session_orchestrator().complete_session` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:1120 (em module.complete_ai_session)
```

### 🔍 Objeto: `get_validation_utils()`

#### `get_validation_utils().validate` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:459 (em module.validate_data)
```

#### `get_validation_utils().validate_query` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:463 (em module.validate_query)
```

#### `get_validation_utils().validate_context` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:467 (em module.validate_context)
```

#### `get_validation_utils().sanitize_input` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:471 (em module.sanitize_input)
```

### 🔍 Objeto: `grafo_relacionamentos`

#### `grafo_relacionamentos.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:224 (em DatabaseManager.obter_estatisticas_gerais)
```

### 🔍 Objeto: `grau_entrada`

#### `grau_entrada.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:264 (em RelationshipMapper._calcular_estatisticas_grafo)
```

### 🔍 Objeto: `grau_saida`

#### `grau_saida.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:265 (em RelationshipMapper._calcular_estatisticas_grafo)
```

### 🔍 Objeto: `grouped`

#### `grouped.to_dict` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:290 (em DataProcessor.aggregate_data)
```

### 🔍 Objeto: `grupo`

#### `grupo.cnpjs_str` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:226 (em KnowledgeMemory.buscar_grupos_aplicaveis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:226 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `grupo.palavras_str` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:227 (em KnowledgeMemory.buscar_grupos_aplicaveis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:227 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `grupo.cnpjs_str.split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:226 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `grupo.palavras_str.split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:227 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `grupo.nome_grupo` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:230 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `grupo.tipo_negocio` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:231 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `grupo.filtro_sql` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:232 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

### 🔍 Objeto: `grupo_detectado`

#### `grupo_detectado.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:142 (em QueryAnalyzer._extract_entities)
```

### 🔍 Objeto: `grupo_info`

#### `grupo_info.get` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:129 (em KnowledgeMemory.descobrir_grupo_empresarial)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:155 (em KnowledgeMemory.descobrir_grupo_empresarial)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:156 (em KnowledgeMemory.descobrir_grupo_empresarial)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:157 (em KnowledgeMemory.descobrir_grupo_empresarial)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:158 (em KnowledgeMemory.descobrir_grupo_empresarial)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `grupos_aplicaveis`

#### `grupos_aplicaveis.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:229 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

### 🔍 Objeto: `grupos_detectados`

#### `grupos_detectados.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:566 (em ContextLoader._carregar_todos_clientes_sistema)
```

### 🔍 Objeto: `grupos_tipos`

#### `grupos_tipos.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:136 (em FieldSearcher._obter_tipos_similares)
```

### 🔍 Objeto: `guard`

#### `guard.validate_user_access` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/__init__.py:84 (em module.secure_validate)
```

#### `guard.validate_input` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/__init__.py:90 (em module.secure_validate)
```

#### `guard.sanitize_input` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/__init__.py:91 (em module.secure_validate)
```

#### `guard.get_security_info` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/__init__.py:98 (em module.get_security_status)
```

### 🔍 Objeto: `hashlib`

#### `hashlib.md5().hexdigest` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:711 (em IntelligenceCoordinator._generate_cache_key)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/context_provider.py:404 (em ContextProvider._generate_cache_key)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:491 (em SuggestionsManager._generate_cache_key)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_classes.py:373 (em BaseProcessor._generate_cache_key)
```

#### `hashlib.md5` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:711 (em IntelligenceCoordinator._generate_cache_key)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/context_provider.py:404 (em ContextProvider._generate_cache_key)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:491 (em SuggestionsManager._generate_cache_key)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_classes.py:373 (em BaseProcessor._generate_cache_key)
```

#### `hashlib.sha256().hexdigest` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:317 (em SecurityGuard.generate_token)
```

#### `hashlib.sha256` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:317 (em SecurityGuard.generate_token)
```

### 🔍 Objeto: `health`

#### `health.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/__init__.py:200 (em module.top-level)
```

### 🔍 Objeto: `hour_counts`

#### `hour_counts.most_common` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:366 (em AdaptiveLearning._detect_time_pattern)
```

### 🔍 Objeto: `hourly_distribution`

#### `hourly_distribution.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:179 (em PerformanceAnalyzer.analyze_ai_performance)
```

### 🔍 Objeto: `hours`

#### `hours.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:358 (em AdaptiveLearning._detect_time_pattern)
```

### 🔍 Objeto: `i`

#### `i.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:321 (em HumanInLoopLearning.generate_learning_report)
```

### 🔍 Objeto: `imp`

#### `imp.get` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:190 (em ImportChecker.check_import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:191 (em ImportChecker.check_import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:201 (em ImportChecker.check_import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:202 (em ImportChecker.check_import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:212 (em ImportChecker.check_import)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `import_configs`

#### `import_configs.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:395 (em SystemConfig.import_config)
```

### 🔍 Objeto: `import_stmt`

#### `import_stmt.replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:157 (em ImportFixer._find_fix)
```

### 🔍 Objeto: `import_str`

#### `import_str.split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:176 (em DetectorModulosOrfaos._marcar_modulo_usado)
```

### 🔍 Objeto: `importlib`

#### `importlib.import_module` (9 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:24 (em module.testar_modulo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:27 (em module.testar_modulo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:178 (em DeepValidator._test_module_import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:191 (em DeepValidator._test_class_exists)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:144 (em ValidadorSistemaCompleto._testar_imports_principais)
  ... e mais 4 ocorrências
```

### 🔍 Objeto: `imports`

#### `imports.append` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:105 (em ImportChecker.extract_imports)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:124 (em ImportChecker.extract_imports)
```

#### `imports.extend` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:166 (em DetectorModulosOrfaos._extrair_imports)
```

### 🔍 Objeto: `improvements`

#### `improvements.append` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:180 (em MetacognitiveAnalyzer._suggest_self_improvements)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:183 (em MetacognitiveAnalyzer._suggest_self_improvements)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:186 (em MetacognitiveAnalyzer._suggest_self_improvements)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:191 (em MetacognitiveAnalyzer._suggest_self_improvements)
```

### 🔍 Objeto: `inc`

#### `inc.lower` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:333 (em CriticAgent._generate_recommendations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:336 (em CriticAgent._generate_recommendations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:336 (em CriticAgent._generate_recommendations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:339 (em CriticAgent._generate_recommendations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:339 (em CriticAgent._generate_recommendations)
```

### 🔍 Objeto: `includes`

#### `includes.extend` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:168 (em FileScanner._extract_template_includes)
```

### 🔍 Objeto: `inconsistencias`

#### `inconsistencias.append` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:305 (em SemanticValidator._validar_campos_modelo_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:310 (em SemanticValidator._validar_campos_modelo_tabela)
```

### 🔍 Objeto: `inconsistencies`

#### `inconsistencies.append` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:144 (em CriticAgent._validate_date_consistency)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:149 (em CriticAgent._validate_date_consistency)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:175 (em CriticAgent._validate_data_consistency)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:191 (em CriticAgent._validate_data_consistency)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:249 (em CriticAgent._validate_numerical_consistency)
```

#### `inconsistencies.extend` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:289 (em CriticAgent._validate_business_logic)
```

### 🔍 Objeto: `inconsistency`

#### `inconsistency.lower` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:195 (em SemanticLoopProcessor.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:198 (em SemanticLoopProcessor.top-level)
```

### 🔍 Objeto: `indice`

#### `indice.get` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:176 (em MetadataReader._obter_indices_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:177 (em MetadataReader._obter_indices_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:178 (em MetadataReader._obter_indices_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:179 (em MetadataReader._obter_indices_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:180 (em MetadataReader._obter_indices_tabela)
```

### 🔍 Objeto: `indices_info`

#### `indices_info.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:182 (em MetadataReader._obter_indices_tabela)
```

### 🔍 Objeto: `individual_results`

#### `individual_results.append` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:216 (em IntelligenceCoordinator.coordinate_multi_ai_synthesis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:224 (em IntelligenceCoordinator.coordinate_multi_ai_synthesis)
```

### 🔍 Objeto: `info_campo`

#### `info_campo.get` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:159 (em AutoMapper._mapear_campo_automatico)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:160 (em AutoMapper._mapear_campo_automatico)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:510 (em AutoMapper._gerar_sugestoes_melhoria)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:96 (em FieldSearcher.buscar_campos_por_tipo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:305 (em FieldSearcher.buscar_campos_por_caracteristica)
  ... e mais 2 ocorrências
```

### 🔍 Objeto: `info_tabela`

#### `info_tabela.get` (9 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:87 (em FieldSearcher.buscar_campos_por_tipo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:165 (em FieldSearcher.buscar_campos_por_nome)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:304 (em FieldSearcher.buscar_campos_por_caracteristica)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:349 (em FieldSearcher.buscar_campos_por_tamanho)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:411 (em FieldSearcher.buscar_campos_similares)
  ... e mais 4 ocorrências
```

#### `info_tabela.get().items` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:87 (em FieldSearcher.buscar_campos_por_tipo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:165 (em FieldSearcher.buscar_campos_por_nome)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:304 (em FieldSearcher.buscar_campos_por_caracteristica)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:349 (em FieldSearcher.buscar_campos_por_tamanho)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:411 (em FieldSearcher.buscar_campos_similares)
```

#### `info_tabela.get().values` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:266 (em MetadataReader.obter_tipos_campo_disponiveis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:295 (em MetadataReader.obter_estatisticas_tabelas)
```

#### `info_tabela.get().keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:298 (em SemanticValidator._validar_campos_modelo_tabela)
```

### 🔍 Objeto: `info_tabela_ref`

#### `info_tabela_ref.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:399 (em FieldSearcher.buscar_campos_similares)
```

### 🔍 Objeto: `init_file`

#### `init_file.exists` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:106 (em ValidadorSistemaCompleto._testar_estrutura_diretorios)
```

### 🔍 Objeto: `init_principal`

#### `init_principal.exists` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:125 (em DetectorModulosOrfaos.analisar_imports_sistema)
```

### 🔍 Objeto: `init_result`

#### `init_result.get` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:266 (em ExternalAPIIntegration.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:325 (em ExternalAPIIntegration.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:129 (em StandaloneIntegration.initialize_system)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:182 (em StandaloneIntegration.process_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:183 (em StandaloneIntegration.process_query)
```

### 🔍 Objeto: `initial_data`

#### `initial_data.copy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:811 (em MainOrchestrator.top-level)
```

### 🔍 Objeto: `initialization_result`

#### `initialization_result.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:337 (em module.get_claude_ai_instance)
```

### 🔍 Objeto: `input()`

#### `input().strip` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:277 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:283 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:292 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:301 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:305 (em module.main)
```

### 🔍 Objeto: `input_data`

#### `input_data.strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:400 (em BaseValidationUtils.sanitize_input)
```

### 🔍 Objeto: `insights`

#### `insights.append` (19 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:479 (em PerformanceAnalyzer._generate_insights)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:481 (em PerformanceAnalyzer._generate_insights)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:483 (em PerformanceAnalyzer._generate_insights)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:487 (em PerformanceAnalyzer._generate_insights)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:489 (em PerformanceAnalyzer._generate_insights)
  ... e mais 14 ocorrências
```

### 🔍 Objeto: `inspect`

#### `inspect.iscoroutinefunction` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:240 (em ValidadorSistemaReal.test_async_issues)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:309 (em ValidadorSistemaReal.top-level)
```

### 🔍 Objeto: `inspector`

#### `inspector.get_table_names` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:56 (em DatabaseScanner.discover_database_schema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:107 (em StructureScanner._discover_models_via_database)
```

#### `inspector.get_columns` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:62 (em DatabaseScanner.discover_database_schema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:111 (em StructureScanner._discover_models_via_database)
```

#### `inspector.get_pk_constraint` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:63 (em DatabaseScanner.discover_database_schema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:114 (em StructureScanner._discover_models_via_database)
```

#### `inspector.get_foreign_keys` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:64 (em DatabaseScanner.discover_database_schema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:112 (em StructureScanner._discover_models_via_database)
```

#### `inspector.get_indexes` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:65 (em DatabaseScanner.discover_database_schema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:113 (em StructureScanner._discover_models_via_database)
```

#### `inspector.get_unique_constraints` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:66 (em DatabaseScanner.discover_database_schema)
```

#### `inspector.get_check_constraints` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:121 (em DatabaseScanner._get_check_constraints)
```

### 🔍 Objeto: `instance`

#### `instance.is_excel_fretes_command` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:228 (em DeepValidator._test_excel_fretes)
```

#### `instance.is_excel_pedidos_command` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:255 (em DeepValidator._test_excel_pedidos)
```

#### `instance.is_excel_entregas_command` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:280 (em DeepValidator._test_excel_entregas)
```

#### `instance.is_excel_faturamento_command` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:305 (em DeepValidator._test_excel_faturamento)
```

### 🔍 Objeto: `integracao`

#### `integracao.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:283 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:305 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
```

### 🔍 Objeto: `integrados`

#### `integrados.append` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:124 (em module.verificar_integracao_modulos_funcionais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:134 (em module.verificar_integracao_modulos_funcionais)
```

### 🔍 Objeto: `integration`

#### `integration.process_query` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:494 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:509 (em module.processar_com_claude_real)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:514 (em module.processar_com_claude_real)
```

#### `integration.initialize_system` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:349 (em module.create_standalone_system)
```

### 🔍 Objeto: `integration_manager`

#### `integration_manager.get_integration_status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:201 (em ValidadorSistemaCompleto._testar_componentes_criticos)
```

### 🔍 Objeto: `integration_results`

#### `integration_results.values` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:41 (em module.teste_integracao_completa)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:53 (em module.teste_integracao_completa)
```

### 🔍 Objeto: `integration_system`

#### `integration_system.__class__.__name__` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/__init__.py:343 (em module.top-level)
```

#### `integration_system.__class__` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/__init__.py:343 (em module.top-level)
```

### 🔍 Objeto: `intelligent_cache`

#### `intelligent_cache.set` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:219 (em BaseCommand._set_cached_result)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:222 (em BaseCommand._set_cached_result)
```

#### `intelligent_cache.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:206 (em BaseCommand._get_cached_result)
```

### 🔍 Objeto: `intelligent_context`

#### `intelligent_context.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:530 (em WebFlaskRoutes._build_user_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:532 (em WebFlaskRoutes._build_user_context)
```

### 🔍 Objeto: `intencoes`

#### `intencoes.values` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:29 (em IntentionAnalyzer.analyze_intention)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:223 (em IntentionAnalyzer._calcular_complexidade_intencao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:224 (em IntentionAnalyzer._calcular_complexidade_intencao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:244 (em IntentionAnalyzer._deve_usar_sistema_avancado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:245 (em IntentionAnalyzer._deve_usar_sistema_avancado)
```

#### `intencoes.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:28 (em IntentionAnalyzer.analyze_intention)
```

#### `intencoes.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:438 (em PatternLearner._detectar_intencao_avancada)
```

### 🔍 Objeto: `intencoes_count`

#### `intencoes_count.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:290 (em IntentionAnalyzer.get_performance_stats)
```

#### `intencoes_count.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:297 (em IntentionAnalyzer.get_performance_stats)
```

### 🔍 Objeto: `intencoes_scores`

#### `intencoes_scores.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:130 (em IntentionAnalyzer._detectar_intencoes_multiplas)
```

### 🔍 Objeto: `intent_patterns`

#### `intent_patterns.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:338 (em SemanticAnalyzer._classify_intents)
```

### 🔍 Objeto: `intention_analysis`

#### `intention_analysis.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:316 (em AnalyzerManager._should_use_nlp_analysis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:364 (em AnalyzerManager._generate_combined_insights)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:365 (em AnalyzerManager._generate_combined_insights)
```

### 🔍 Objeto: `intents`

#### `intents.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:341 (em SemanticAnalyzer._classify_intents)
```

### 🔍 Objeto: `interaction`

#### `interaction.get().get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:382 (em AdaptiveLearning._detect_query_pattern)
```

#### `interaction.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:382 (em AdaptiveLearning._detect_query_pattern)
```

### 🔍 Objeto: `interaction_data`

#### `interaction_data.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:311 (em AdaptiveLearning._extract_preferences)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:317 (em AdaptiveLearning._extract_preferences)
```

### 🔍 Objeto: `interpretacao`

#### `interpretacao.get` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:112 (em LearningCore.aprender_com_interacao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:119 (em LearningCore.aprender_com_interacao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:286 (em LearningCore._atualizar_metricas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:105 (em PatternLearner._extrair_padroes_periodo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:135 (em PatternLearner._extrair_padroes_dominio)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `issues`

#### `issues.append` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:217 (em StructuralAnalyzer._detect_structural_issues)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:222 (em StructuralAnalyzer._detect_structural_issues)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:227 (em StructuralAnalyzer._detect_structural_issues)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/structural_validator.py:96 (em StructuralAI._validate_temporal_consistency)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/structural_validator.py:110 (em StructuralAI._validate_data_relationships)
```

### 🔍 Objeto: `item`

#### `item.name` (11 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:45 (em DetectorModulosOrfaos.mapear_todas_pastas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:46 (em DetectorModulosOrfaos.mapear_todas_pastas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:77 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:50 (em MethodCallVisitor.visit_ClassDef)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:51 (em MethodCallVisitor.visit_ClassDef)
  ... e mais 6 ocorrências
```

#### `item.value` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:236 (em StructureScanner._extract_table_name)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:237 (em StructureScanner._extract_table_name)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:238 (em StructureScanner._extract_table_name)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:239 (em StructureScanner._extract_table_name)
```

#### `item.is_dir` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:45 (em DetectorModulosOrfaos.mapear_todas_pastas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:241 (em FileScanner.list_directory_contents)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:244 (em FileScanner.list_directory_contents)
```

#### `item.targets` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:54 (em VariableTracker.visit_ClassDef)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:234 (em StructureScanner._extract_table_name)
```

#### `item.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:261 (em HumanInLoopLearning.apply_improvement)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:262 (em HumanInLoopLearning.apply_improvement)
```

#### `item.cliente` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:154 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:154 (em EmbarquesLoader._format_embarques_results)
```

#### `item.name.startswith` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:125 (em CodeScanner._parse_forms_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:241 (em FileScanner.list_directory_contents)
```

#### `item.stat` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:247 (em FileScanner.list_directory_contents)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:254 (em FileScanner.list_directory_contents)
```

#### `item.suffix` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:253 (em FileScanner.list_directory_contents)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:260 (em FileScanner.list_directory_contents)
```

#### `item.peso_total` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:140 (em EmbarquesLoader._format_embarques_results)
```

#### `item.valor_total` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:141 (em EmbarquesLoader._format_embarques_results)
```

#### `item.iterdir` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:244 (em FileScanner.list_directory_contents)
```

#### `item.is_file` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:246 (em FileScanner.list_directory_contents)
```

#### `item.stat().st_size` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:247 (em FileScanner.list_directory_contents)
```

#### `item.stat().st_mtime` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:254 (em FileScanner.list_directory_contents)
```

#### `item.decorator_list` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:207 (em StructureScanner._parse_models_file)
```

#### `item.value.value` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:237 (em StructureScanner._extract_table_name)
```

#### `item.value.s` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:239 (em StructureScanner._extract_table_name)
```

### 🔍 Objeto: `json`

#### `json.dumps` (15 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:365 (em SystemConfig.export_config)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:345 (em module.export_config)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:132 (em BaseSpecialistAgent.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:135 (em BaseSpecialistAgent.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:378 (em ExternalAPIIntegration.top-level)
  ... e mais 10 ocorrências
```

#### `json.dump` (10 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:345 (em DetectorModulosOrfaos.salvar_relatorio)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:259 (em ClassDuplicateFinder.save_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:237 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:304 (em UninitializedVariableFinder.save_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:145 (em module.generate_report)
  ... e mais 5 ocorrências
```

#### `json.load` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:69 (em ImportFixer.load_errors)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:540 (em SystemConfig._load_profile_config)
```

#### `json.loads` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:385 (em SystemConfig.import_config)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:360 (em PatternLearner.buscar_padroes_aplicaveis)
```

#### `json.JSONDecodeError` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:364 (em PatternLearner.buscar_padroes_aplicaveis)
```

### 🔍 Objeto: `key`

#### `key.lower` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:611 (em SystemConfig._validate_config_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:614 (em SystemConfig._validate_config_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:617 (em SystemConfig._validate_config_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:620 (em SystemConfig._validate_config_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:473 (em DataProcessor._normalize_dict)
  ... e mais 1 ocorrências
```

#### `key.strip` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:383 (em DataProcessor._clean_dict)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:385 (em DataProcessor._clean_dict)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:387 (em DataProcessor._clean_dict)
```

#### `key.startswith` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/basic_config.py:63 (em ClaudeAIConfig.to_dict)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:727 (em SystemConfig._key_matches_pattern)
```

#### `key.split` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:582 (em SystemConfig._get_nested_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:595 (em SystemConfig._set_nested_value)
```

#### `key.lower().replace` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:473 (em DataProcessor._normalize_dict)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:379 (em IntelligenceProcessor._normalize_dict_for_intelligence)
```

#### `key.lower().replace().replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:473 (em DataProcessor._normalize_dict)
```

#### `key.value` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:211 (em CodeScanner._extract_dict_value)
```

### 🔍 Objeto: `key_data`

#### `key_data.encode` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_classes.py:373 (em BaseProcessor._generate_cache_key)
```

### 🔍 Objeto: `keyword`

#### `keyword.arg` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:177 (em CodeScanner._extract_form_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:179 (em CodeScanner._extract_form_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:181 (em CodeScanner._extract_form_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:284 (em StructureScanner._extract_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:286 (em StructureScanner._extract_field_info)
  ... e mais 3 ocorrências
```

#### `keyword.value` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:178 (em CodeScanner._extract_form_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:180 (em CodeScanner._extract_form_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:182 (em CodeScanner._extract_form_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:285 (em StructureScanner._extract_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:287 (em StructureScanner._extract_field_info)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `keywords`

#### `keywords.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:281 (em SemanticAnalyzer._extract_keywords)
```

### 🔍 Objeto: `keywords_entregas`

#### `keywords_entregas.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:69 (em EntregasAgent._calculate_relevance)
```

### 🔍 Objeto: `kwargs`

#### `kwargs.get` (35 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1086 (em EnrichersWrapper.enrich_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1266 (em MockComponent.execute_tool)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1273 (em MockComponent.register_tool)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1281 (em MockComponent.validate_tool)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1299 (em MockComponent._sanitize_input)
  ... e mais 30 ocorrências
```

#### `kwargs.items` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:710 (em IntelligenceCoordinator._generate_cache_key)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/context_provider.py:403 (em ContextProvider._generate_cache_key)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:391 (em module.provide_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:402 (em module.provide_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:490 (em SuggestionsManager._generate_cache_key)
```

#### `kwargs.copy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/__init__.py:192 (em module.load_data)
```

### 🔍 Objeto: `l`

#### `l.strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:379 (em ResponseProcessor._validar_resposta_final)
```

### 🔍 Objeto: `learning_module`

#### `learning_module.record_feedback` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:581 (em WebFlaskRoutes._record_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:596 (em WebFlaskRoutes._record_feedback)
```

### 🔍 Objeto: `learning_system`

#### `learning_system.capture_feedback` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:425 (em module.capture_user_feedback)
```

#### `learning_system.generate_learning_report` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:431 (em module.get_learning_insights)
```

### 🔍 Objeto: `level`

#### `level.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_classes.py:286 (em BaseProcessor._log_operation)
```

### 🔍 Objeto: `line`

#### `line.split` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:285 (em CodeScanner._extract_blueprint_name)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:346 (em CodeScanner._extract_function_info)
```

#### `line.strip` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:298 (em CodeScanner._extract_routes_from_lines)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:317 (em FileScanner.search_in_files)
```

#### `line.startswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:345 (em CodeScanner._extract_function_info)
```

### 🔍 Objeto: `linha`

#### `linha.strip` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:379 (em ResponseProcessor._validar_resposta_final)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:379 (em ResponseProcessor._validar_resposta_final)
```

### 🔍 Objeto: `linhas_unicas`

#### `linhas_unicas.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:380 (em ResponseProcessor._validar_resposta_final)
```

### 🔍 Objeto: `loader`

#### `loader.load_pedidos_data` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:123 (em LoaderManager.load_data_by_domain)
```

#### `loader.load_entregas_data` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:125 (em LoaderManager.load_data_by_domain)
```

#### `loader.load_fretes_data` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:127 (em LoaderManager.load_data_by_domain)
```

#### `loader.load_embarques_data` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:129 (em LoaderManager.load_data_by_domain)
```

#### `loader.load_faturamento_data` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:131 (em LoaderManager.load_data_by_domain)
```

#### `loader.load_agendamentos_data` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:133 (em LoaderManager.load_data_by_domain)
```

#### `loader.load_context` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/__init__.py:156 (em module.load_context)
```

#### `loader.load_database` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/__init__.py:172 (em module.load_database)
```

### 🔍 Objeto: `logging`

#### `logging.getLogger` (154 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:17 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:38 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:101 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:112 (em AnalyzerManager.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:19 (em module.top-level)
  ... e mais 149 ocorrências
```

#### `logging.warning` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:24 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:27 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:34 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:50 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:32 (em module.top-level)
  ... e mais 1 ocorrências
```

#### `logging.INFO` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:16 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:370 (em module.top-level)
```

#### `logging.basicConfig` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:16 (em module.top-level)
```

#### `logging.Logger` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_classes.py:98 (em module.top-level)
```

### 🔍 Objeto: `loop`

#### `loop.run_until_complete` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:224 (em ClaudeAINovo.process_query_sync)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:336 (em module.get_claude_ai_instance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:508 (em module.processar_com_claude_real)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:125 (em StandaloneIntegration.initialize_system)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:195 (em StandaloneIntegration.process_query)
  ... e mais 3 ocorrências
```

#### `loop.is_running` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:198 (em ValidatorManager.validate_agent_responses)
```

#### `loop.create_task` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:200 (em ValidatorManager.validate_agent_responses)
```

### 🔍 Objeto: `m`

#### `m.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:147 (em ConversationMemory.get_conversation_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:148 (em ConversationMemory.get_conversation_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:257 (em ProjectScanner._calculate_quality_metrics)
```

#### `m.strip().strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:332 (em CodeScanner._extract_route_methods)
```

#### `m.strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:332 (em CodeScanner._extract_route_methods)
```

#### `m.get().startswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:257 (em ProjectScanner._calculate_quality_metrics)
```

### 🔍 Objeto: `main_orch`

#### `main_orch.components` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:84 (em module.teste_sistema_basico)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:321 (em TesteIntegracaoCompleta.testar_fallbacks_mocks)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:322 (em TesteIntegracaoCompleta.testar_fallbacks_mocks)
```

#### `main_orch.execute_workflow` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:177 (em module.teste_funcionalidades_avancadas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:221 (em module.teste_funcionalidades_avancadas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:255 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `main_orch.workflows` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:84 (em module.teste_sistema_basico)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:239 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `main_orch.coordinator_manager` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:129 (em module.teste_modulos_alto_valor)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:228 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `main_orch.auto_command_processor` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:155 (em module.teste_modulos_alto_valor)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:229 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `main_orch.security_guard` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:230 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `main_orch.suggestions_manager` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:231 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

### 🔍 Objeto: `manager`

#### `manager.get_status` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:677 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:279 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tools/tools_manager.py:202 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/data_manager.py:420 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/utils_manager.py:303 (em module.top-level)
```

#### `manager.health_check` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:678 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:280 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tools/tools_manager.py:203 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/data_manager.py:421 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/utils_manager.py:304 (em module.top-level)
```

#### `manager.provide` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:393 (em module.provide_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:404 (em module.provide_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/__init__.py:114 (em module.provide_integrated_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/__init__.py:139 (em module.provide_integrated_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/__init__.py:165 (em module.provide_mixed_intelligence)
```

#### `manager.orchestrate_operation` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:102 (em module.teste_sistema_basico)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:805 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/__init__.py:132 (em module.top-level)
```

#### `manager.claude` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:40 (em module.verificar_configuracao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:41 (em module.verificar_configuracao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:42 (em module.verificar_configuracao)
```

#### `manager.process_unified_query` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:133 (em ClaudeAINovo.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:349 (em ExternalAPIIntegration.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:128 (em WebIntegrationAdapter.process_query_sync)
```

#### `manager.get_system_status` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:156 (em ClaudeAINovo.get_system_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:269 (em ExternalAPIIntegration.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:214 (em WebIntegrationAdapter.get_system_status)
```

#### `manager.load_data_by_domain` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:319 (em module.load_domain_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/__init__.py:195 (em module.load_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/__init__.py:217 (em module.load_domain_data)
```

#### `manager.process_query` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:240 (em ValidadorSistemaReal.test_async_issues)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:272 (em ValidadorSistemaReal.top-level)
```

#### `manager.claude.__class__` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:41 (em module.verificar_configuracao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:42 (em module.verificar_configuracao)
```

#### `manager.initialize_all_modules` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:94 (em ClaudeAINovo.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:265 (em ExternalAPIIntegration.top-level)
```

#### `manager.get_module` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:146 (em ClaudeAINovo.get_module)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:186 (em WebIntegrationAdapter.get_module)
```

#### `manager.coordinate_query` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:371 (em module.coordinate_intelligent_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:174 (em module.coordinate_smart_query)
```

#### `manager.domain_agents.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:384 (em module.get_domain_agent)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:189 (em module.get_domain_agent)
```

#### `manager.domain_agents` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:384 (em module.get_domain_agent)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:189 (em module.get_domain_agent)
```

#### `manager.get_coordinator_status` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:394 (em module.get_coordination_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:201 (em module.get_coordination_status)
```

#### `manager.get_best_loader_for_query` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:329 (em module.get_best_loader)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/__init__.py:191 (em module.load_data)
```

#### `manager.get_memory_health` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/__init__.py:172 (em module.get_memory_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/__init__.py:199 (em module.top-level)
```

#### `manager.get_orchestrator_status` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:821 (em module.get_orchestration_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/__init__.py:160 (em module.get_system_status)
```

#### `manager.get_scanner_status` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/__init__.py:172 (em module.get_scanning_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/__init__.py:198 (em module.top-level)
```

#### `manager.get_validation_status` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/__init__.py:151 (em module.get_validation_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/__init__.py:177 (em module.top-level)
```

#### `manager.orchestrators` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:79 (em module.teste_sistema_basico)
```

#### `manager.sistema_ativo` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:37 (em module.verificar_configuracao)
```

#### `manager.claude.__class__.__name__` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:41 (em module.verificar_configuracao)
```

#### `manager.claude.__class__.__module__` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:42 (em module.verificar_configuracao)
```

#### `manager.get_integration_status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_status_completo.py:29 (em module.verificar_status)
```

#### `manager.modules.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:175 (em ClaudeAINovo.get_available_modules)
```

#### `manager.modules` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:175 (em ClaudeAINovo.get_available_modules)
```

#### `manager.initialize_diagnostics_analyzer` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:670 (em module.get_analyzer_manager)
```

#### `manager.get_available_modules` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:241 (em WebIntegrationAdapter.get_available_modules)
```

#### `manager.load_multiple_domains` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:324 (em module.load_multiple_data)
```

#### `manager.store_conversation_context` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/__init__.py:150 (em module.memorize_context)
```

#### `manager.retrieve_conversation_context` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/__init__.py:161 (em module.recall_context)
```

#### `manager.get_processor_chain` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:284 (em module.top-level)
```

#### `manager.get_detailed_health_report` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:288 (em module.top-level)
```

#### `manager.get_best_provider_for_query` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/__init__.py:170 (em module.get_best_provider_recommendation)
```

#### `manager.get_provider_status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/__init__.py:175 (em module.get_all_providers_status)
```

#### `manager.scan_complete_project` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/__init__.py:150 (em module.scan_project)
```

#### `manager.generate_suggestions` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/__init__.py:96 (em module.generate_suggestions)
```

#### `manager.register_suggestion_engine` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/__init__.py:137 (em module.register_suggestion_engine)
```

#### `manager.submit_feedback` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/__init__.py:162 (em module.submit_suggestion_feedback)
```

#### `manager.get_suggestion_recommendations` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/__init__.py:185 (em module.get_suggestion_recommendations)
```

#### `manager.optimize_suggestion_performance` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/__init__.py:233 (em module.optimize_suggestions_performance)
```

#### `manager.validate_context` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/__init__.py:129 (em module.validate_context)
```

#### `manager.validate_data_structure` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/__init__.py:140 (em module.validate_data_structure)
```

### 🔍 Objeto: `manager_status`

#### `manager_status.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:216 (em WebIntegrationAdapter.get_system_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:455 (em WebFlaskRoutes.health_check)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:456 (em WebFlaskRoutes.health_check)
```

### 🔍 Objeto: `mapa`

#### `mapa.campo_sistema` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:275 (em KnowledgeMemory.buscar_mapeamentos_aplicaveis)
```

#### `mapa.modelo` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:276 (em KnowledgeMemory.buscar_mapeamentos_aplicaveis)
```

#### `mapa.frequencia` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:277 (em KnowledgeMemory.buscar_mapeamentos_aplicaveis)
```

#### `mapa.termos` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:278 (em KnowledgeMemory.buscar_mapeamentos_aplicaveis)
```

### 🔍 Objeto: `mapeamento`

#### `mapeamento.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:279 (em SemanticValidator._mapear_modelo_para_tabela)
```

### 🔍 Objeto: `mapeamento_atual`

#### `mapeamento_atual.get` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:251 (em SemanticEnricher._sugestoes_readme_vs_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:268 (em SemanticEnricher._sugestoes_readme_vs_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:370 (em SemanticEnricher._sugestoes_otimizacao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:371 (em SemanticEnricher._sugestoes_otimizacao)
```

### 🔍 Objeto: `mapeamento_campo`

#### `mapeamento_campo.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:114 (em AutoMapper.gerar_mapeamento_automatico)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:118 (em AutoMapper.gerar_mapeamento_automatico)
```

### 🔍 Objeto: `mapeamentos`

#### `mapeamentos.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:151 (em MetadataReader._normalizar_tipo_sqlalchemy)
```

### 🔍 Objeto: `mapeamentos_aplicaveis`

#### `mapeamentos_aplicaveis.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:274 (em KnowledgeMemory.buscar_mapeamentos_aplicaveis)
```

### 🔍 Objeto: `mapeamentos_criados`

#### `mapeamentos_criados.append` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:79 (em KnowledgeMemory.aprender_mapeamento_cliente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:94 (em KnowledgeMemory.aprender_mapeamento_cliente)
```

### 🔍 Objeto: `mapper`

#### `mapper.mapeamentos` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:198 (em SemanticEnricher._obter_mapeamento_atual)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:199 (em SemanticEnricher._obter_mapeamento_atual)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:172 (em SemanticValidator._validacoes_gerais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:184 (em SemanticValidator._validacoes_gerais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:185 (em SemanticValidator._validacoes_gerais)
  ... e mais 1 ocorrências
```

#### `mapper.gerar_estatisticas` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:60 (em DiagnosticsAnalyzer.gerar_estatisticas_completas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:244 (em MapperManager.obter_estatisticas_mappers)
```

#### `mapper.modelo_nome` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:203 (em SemanticEnricher._obter_mapeamento_atual)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:302 (em SemanticValidator._validar_campos_modelo_tabela)
```

#### `mapper.validar_mapeamentos` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:106 (em DiagnosticsAnalyzer.diagnosticar_qualidade)
```

#### `mapper.buscar_mapeamento` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:72 (em MapperManager.analisar_consulta_semantica)
```

#### `mapper.buscar_mapeamento_fuzzy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:118 (em MapperManager._buscar_fuzzy_integrado)
```

#### `mapper.modelo_nome.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:302 (em SemanticValidator._validar_campos_modelo_tabela)
```

#### `mapper.mapeamentos.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:303 (em SemanticValidator._validar_campos_modelo_tabela)
```

### 🔍 Objeto: `mappers`

#### `mappers.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/__init__.py:32 (em module.get_domain_mapper)
```

#### `mappers.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/__init__.py:34 (em module.get_domain_mapper)
```

### 🔍 Objeto: `mappers_consultados`

#### `mappers_consultados.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:79 (em MapperManager.analisar_consulta_semantica)
```

### 🔍 Objeto: `mapping`

#### `mapping.transform_function` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/context_mapper.py:96 (em ContextMapper.map_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/context_mapper.py:97 (em ContextMapper.map_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:126 (em FieldMapper.map_fields)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:127 (em FieldMapper.map_fields)
```

#### `mapping.source_field` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:114 (em FieldMapper.map_fields)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:122 (em FieldMapper.map_fields)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:131 (em FieldMapper.map_fields)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:138 (em FieldMapper.map_fields)
```

#### `mapping.target_key` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/context_mapper.py:100 (em ContextMapper.map_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/context_mapper.py:103 (em ContextMapper.map_context)
```

#### `mapping.default_value` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:117 (em FieldMapper.map_fields)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:118 (em FieldMapper.map_fields)
```

#### `mapping.validation_function` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:130 (em FieldMapper.map_fields)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:130 (em FieldMapper.map_fields)
```

#### `mapping.pattern` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:98 (em QueryMapper.map_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:100 (em QueryMapper.map_query)
```

#### `mapping.source_keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/context_mapper.py:91 (em ContextMapper.map_context)
```

#### `mapping.required` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:121 (em FieldMapper.map_fields)
```

#### `mapping.target_field` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:135 (em FieldMapper.map_fields)
```

#### `mapping.target_type` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:96 (em QueryMapper.map_query)
```

#### `mapping.template` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:103 (em QueryMapper.map_query)
```

#### `mapping.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:166 (em ValidatorManager.validate_critical_rules)
```

### 🔍 Objeto: `mapping_result`

#### `mapping_result.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:129 (em SemanticLoopProcessor.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:130 (em SemanticLoopProcessor.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:131 (em SemanticLoopProcessor.top-level)
```

### 🔍 Objeto: `match`

#### `match.group` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:102 (em BaseCommand._extract_client_from_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:318 (em CodeScanner._extract_url_pattern)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:331 (em CodeScanner._extract_route_methods)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:132 (em FileScanner._extract_template_extends)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:114 (em ReadmeScanner.buscar_termos_naturais)
  ... e mais 2 ocorrências
```

#### `match.strip` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:340 (em FeedbackProcessor._extrair_acoes_sugeridas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:340 (em FeedbackProcessor._extrair_acoes_sugeridas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:105 (em FileScanner._extract_template_variables)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:149 (em FileScanner._extract_template_blocks)
```

#### `match.split` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:97 (em FileScanner._extract_template_variables)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:113 (em FileScanner._extract_template_variables)
```

#### `match.start` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:342 (em FileScanner._extract_match_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:225 (em ReadmeScanner._extrair_secao_modelo)
```

#### `match.group().title` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:102 (em BaseCommand._extract_client_from_query)
```

#### `match.end` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:343 (em FileScanner._extract_match_context)
```

#### `match.lower().replace().capitalize` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:367 (em ReadmeScanner.listar_modelos_disponiveis)
```

#### `match.lower().replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:367 (em ReadmeScanner.listar_modelos_disponiveis)
```

#### `match.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:367 (em ReadmeScanner.listar_modelos_disponiveis)
```

### 🔍 Objeto: `match_contexto`

#### `match_contexto.group().strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:334 (em ReadmeScanner.obter_informacoes_campo)
```

#### `match_contexto.group` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:334 (em ReadmeScanner.obter_informacoes_campo)
```

### 🔍 Objeto: `match_obs`

#### `match_obs.group().strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:340 (em ReadmeScanner.obter_informacoes_campo)
```

#### `match_obs.group` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:340 (em ReadmeScanner.obter_informacoes_campo)
```

### 🔍 Objeto: `match_proximo`

#### `match_proximo.start` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:240 (em ReadmeScanner._extrair_secao_modelo)
```

### 🔍 Objeto: `match_significado`

#### `match_significado.group().strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:328 (em ReadmeScanner.obter_informacoes_campo)
```

#### `match_significado.group` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:328 (em ReadmeScanner.obter_informacoes_campo)
```

### 🔍 Objeto: `match_termos`

#### `match_termos.group` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:322 (em ReadmeScanner.obter_informacoes_campo)
```

### 🔍 Objeto: `matches_por_mapper`

#### `matches_por_mapper.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:216 (em MapperManager.detectar_dominio_principal)
```

#### `matches_por_mapper.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:217 (em MapperManager.detectar_dominio_principal)
```

#### `matches_por_mapper.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:222 (em MapperManager.detectar_dominio_principal)
```

### 🔍 Objeto: `melhorias`

#### `melhorias.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:155 (em FeedbackProcessor.processar_feedback_completo)
```

### 🔍 Objeto: `mentioned_dates`

#### `mentioned_dates.extend` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:136 (em CriticAgent._validate_date_consistency)
```

### 🔍 Objeto: `mes`

#### `mes.capitalize` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:220 (em ConversationContext.extract_metadata)
```

### 🔍 Objeto: `message`

#### `message.to_dict` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:71 (em ConversationContext.add_message)
```

### 🔍 Objeto: `metadata`

#### `metadata.get` (11 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:174 (em AutoCommandProcessor.get_command_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:175 (em AutoCommandProcessor.get_command_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_formatter.py:23 (em ResponseFormatter.format_standard_response)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_formatter.py:26 (em ResponseFormatter.format_standard_response)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:47 (em module.format_response_advanced)
  ... e mais 6 ocorrências
```

### 🔍 Objeto: `metadata_reader`

#### `metadata_reader.obter_campos_tabela` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:446 (em DataAnalyzer.analisar_tabela_completa)
```

### 🔍 Objeto: `method`

#### `method.startswith` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:279 (em ProcessorRegistry.validate_all_processors)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:134 (em ValidatorManager.validate_data_structure)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:366 (em ValidatorManager.get_validation_status)
```

### 🔍 Objeto: `method_name`

#### `method_name.startswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:164 (em module.find_undefined_methods)
```

#### `method_name.endswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:164 (em module.find_undefined_methods)
```

### 🔍 Objeto: `methods`

#### `methods.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:77 (em ClassDuplicateFinder.extract_class_info)
```

### 🔍 Objeto: `methods_count`

#### `methods_count.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:360 (em CodeScanner._analyze_route_methods)
```

### 🔍 Objeto: `methods_str`

#### `methods_str.split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:332 (em CodeScanner._extract_route_methods)
```

### 🔍 Objeto: `mock_db`

#### `mock_db.session` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:204 (em FlaskFallback._create_mock_db)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:205 (em FlaskFallback._create_mock_db)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:206 (em FlaskFallback._create_mock_db)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:207 (em FlaskFallback._create_mock_db)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:208 (em FlaskFallback._create_mock_db)
```

### 🔍 Objeto: `mock_query`

#### `mock_query.all` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:94 (em FlaskFallback._create_mock_model)
```

#### `mock_query.first` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:95 (em FlaskFallback._create_mock_model)
```

#### `mock_query.count` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:96 (em FlaskFallback._create_mock_model)
```

#### `mock_query.filter` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:97 (em FlaskFallback._create_mock_model)
```

#### `mock_query.filter_by` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:98 (em FlaskFallback._create_mock_model)
```

#### `mock_query.order_by` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:99 (em FlaskFallback._create_mock_model)
```

#### `mock_query.limit` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:100 (em FlaskFallback._create_mock_model)
```

#### `mock_query.offset` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:101 (em FlaskFallback._create_mock_model)
```

#### `mock_query.join` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:102 (em FlaskFallback._create_mock_model)
```

### 🔍 Objeto: `mode`

#### `mode.value` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:827 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:839 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:298 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:317 (em OrchestratorManager.top-level)
```

#### `mode.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:800 (em module.top-level)
```

### 🔍 Objeto: `model_info`

#### `model_info.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:240 (em ProjectScanner._calculate_quality_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:240 (em ProjectScanner._calculate_quality_metrics)
```

### 🔍 Objeto: `model_name`

#### `model_name.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:90 (em FlaskFallback._create_mock_model)
```

### 🔍 Objeto: `modelo`

#### `modelo.lower` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:195 (em SemanticEnricher._obter_mapeamento_atual)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:171 (em SemanticValidator._validacoes_gerais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:279 (em SemanticValidator._mapear_modelo_para_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:302 (em SemanticValidator._validar_campos_modelo_tabela)
```

### 🔍 Objeto: `modelos`

#### `modelos.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:369 (em ReadmeScanner.listar_modelos_disponiveis)
```

### 🔍 Objeto: `models`

#### `models.update` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:87 (em StructureScanner.discover_all_models)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:90 (em StructureScanner.discover_all_models)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:156 (em StructureScanner._discover_models_via_files)
```

#### `models.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:181 (em PerformanceAnalyzer.analyze_ai_performance)
```

### 🔍 Objeto: `models_file`

#### `models_file.exists` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:155 (em StructureScanner._discover_models_via_files)
```

### 🔍 Objeto: `module_dir`

#### `module_dir.name` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:51 (em CodeScanner.discover_all_forms)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:54 (em CodeScanner.discover_all_forms)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:74 (em CodeScanner.discover_all_routes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:77 (em CodeScanner.discover_all_routes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:153 (em StructureScanner._discover_models_via_files)
  ... e mais 1 ocorrências
```

#### `module_dir.is_dir` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:51 (em CodeScanner.discover_all_forms)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:74 (em CodeScanner.discover_all_routes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:153 (em StructureScanner._discover_models_via_files)
```

#### `module_dir.name.startswith` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:51 (em CodeScanner.discover_all_forms)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:74 (em CodeScanner.discover_all_routes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:153 (em StructureScanner._discover_models_via_files)
```

### 🔍 Objeto: `module_name`

#### `module_name.lstrip` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:166 (em ImportChecker.check_import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:167 (em ImportChecker.check_import)
```

#### `module_name.startswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:101 (em CommandsRegistry._try_import_command)
```

### 🔍 Objeto: `module_path`

#### `module_path.startswith` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:22 (em module.testar_modulo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:173 (em DeepValidator._test_module_import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:186 (em DeepValidator._test_class_exists)
```

### 🔍 Objeto: `modulo`

#### `modulo.replace().replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:121 (em module.verificar_integracao_modulos_funcionais)
```

#### `modulo.replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:121 (em module.verificar_integracao_modulos_funcionais)
```

### 🔍 Objeto: `modulo_orfao`

#### `modulo_orfao.lower` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:229 (em DetectorModulosOrfaos.analisar_impacto_orfaos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:229 (em DetectorModulosOrfaos.analisar_impacto_orfaos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:231 (em DetectorModulosOrfaos.analisar_impacto_orfaos)
```

### 🔍 Objeto: `modulos_esquecidos`

#### `modulos_esquecidos.values` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_modulos_esquecidos.py:101 (em module.teste_modulos_esquecidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_modulos_esquecidos.py:102 (em module.teste_modulos_esquecidos)
```

#### `modulos_esquecidos.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_modulos_esquecidos.py:109 (em module.teste_modulos_esquecidos)
```

### 🔍 Objeto: `modulos_teste`

#### `modulos_teste.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:174 (em module.main)
```

#### `modulos_teste.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:182 (em module.main)
```

### 🔍 Objeto: `monitor`

#### `monitor.start` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:369 (em module.main)
```

### 🔍 Objeto: `msg`

#### `msg.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:165 (em ConversationContext.build_context_prompt)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:166 (em ConversationContext.build_context_prompt)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:169 (em ConversationContext.build_context_prompt)
```

### 🔍 Objeto: `name`

#### `name.split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:30 (em VariableTracker.visit_Import)
```

### 🔍 Objeto: `negacoes_encontradas`

#### `negacoes_encontradas.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:266 (em NLPEnhancedAnalyzer._detectar_negacoes)
```

### 🔍 Objeto: `new_line`

#### `new_line.rstrip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:128 (em ImportFixer._fix_file)
```

### 🔍 Objeto: `nltk`

#### `nltk.download` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:41 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:42 (em module.top-level)
```

### 🔍 Objeto: `node`

#### `node.name` (14 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:107 (em DetectorModulosOrfaos._extrair_definicoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:109 (em DetectorModulosOrfaos._extrair_definicoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:54 (em ClassDuplicateFinder.scan_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:44 (em MethodCallVisitor.visit_ClassDef)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:45 (em MethodCallVisitor.visit_ClassDef)
  ... e mais 9 ocorrências
```

#### `node.lineno` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:83 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:87 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:74 (em MethodCallVisitor.visit_Attribute)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:64 (em VariableTracker.visit_Assign)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:71 (em VariableTracker.visit_Name)
  ... e mais 2 ocorrências
```

#### `node.names` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:29 (em MethodCallVisitor.visit_Import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:36 (em MethodCallVisitor.visit_ImportFrom)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:28 (em VariableTracker.visit_Import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:35 (em VariableTracker.visit_ImportFrom)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:104 (em ImportChecker.extract_imports)
  ... e mais 1 ocorrências
```

#### `node.body` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:75 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:48 (em MethodCallVisitor.visit_ClassDef)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:52 (em VariableTracker.visit_ClassDef)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:119 (em CodeScanner._parse_forms_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:199 (em StructureScanner._parse_models_file)
```

#### `node.ctx` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:66 (em MethodCallVisitor.visit_Attribute)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:69 (em VariableTracker.visit_Name)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:72 (em VariableTracker.visit_Name)
```

#### `node.attr` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:73 (em MethodCallVisitor.visit_Attribute)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:76 (em MethodCallVisitor.visit_Attribute)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:87 (em MethodCallVisitor._get_object_name)
```

#### `node.id` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:83 (em MethodCallVisitor._get_object_name)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:71 (em VariableTracker.visit_Name)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:74 (em VariableTracker.visit_Name)
```

#### `node.end_lineno` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:82 (em ClassDuplicateFinder.extract_class_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:83 (em ClassDuplicateFinder.extract_class_info)
```

#### `node.value` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:68 (em MethodCallVisitor.visit_Attribute)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:85 (em MethodCallVisitor._get_object_name)
```

#### `node.bases` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:67 (em ClassDuplicateFinder.extract_class_info)
```

#### `node.func` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:89 (em MethodCallVisitor._get_object_name)
```

#### `node.args.args` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:43 (em VariableTracker.visit_FunctionDef)
```

#### `node.args` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:43 (em VariableTracker.visit_FunctionDef)
```

#### `node.targets` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:61 (em VariableTracker.visit_Assign)
```

#### `node.module` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:113 (em ImportChecker.extract_imports)
```

#### `node.level` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:114 (em ImportChecker.extract_imports)
```

### 🔍 Objeto: `nome_campo`

#### `nome_campo.lower` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:231 (em AutoMapper._gerar_termos_automaticos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:332 (em AutoMapper._calcular_confianca_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:367 (em AutoMapper._identificar_categoria_semantica)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:206 (em FieldSearcher._calcular_score_match_nome)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:246 (em FieldSearcher._determinar_tipo_match)
```

#### `nome_campo.replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:226 (em AutoMapper._gerar_termos_automaticos)
```

### 🔍 Objeto: `nome_lower`

#### `nome_lower.startswith` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:213 (em FieldSearcher._calcular_score_match_nome)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:221 (em FieldSearcher._calcular_score_match_nome)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:251 (em FieldSearcher._determinar_tipo_match)
```

#### `nome_lower.endswith` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:216 (em FieldSearcher._calcular_score_match_nome)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:223 (em FieldSearcher._calcular_score_match_nome)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:253 (em FieldSearcher._determinar_tipo_match)
```

### 🔍 Objeto: `nome_modelo`

#### `nome_modelo.upper` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:215 (em ReadmeScanner._extrair_secao_modelo)
```

#### `nome_modelo.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:218 (em ReadmeScanner._extrair_secao_modelo)
```

#### `nome_modelo.endswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:204 (em AutoMapper._gerar_nome_modelo)
```

### 🔍 Objeto: `nome_modulo`

#### `nome_modulo.title` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:351 (em DevCommands._template_modulo_fallback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:359 (em DevCommands._template_modulo_fallback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:376 (em DevCommands._template_modulo_fallback)
```

### 🔍 Objeto: `nome_padrao`

#### `nome_padrao.lower` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:160 (em FieldSearcher.buscar_campos_por_nome)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:207 (em FieldSearcher._calcular_score_match_nome)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:247 (em FieldSearcher._determinar_tipo_match)
```

### 🔍 Objeto: `nome_tabela`

#### `nome_tabela.replace().split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:200 (em AutoMapper._gerar_nome_modelo)
```

#### `nome_tabela.replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:200 (em AutoMapper._gerar_nome_modelo)
```

### 🔍 Objeto: `numerical_consistency`

#### `numerical_consistency.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:93 (em CriticAgent.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:102 (em CriticAgent.top-level)
```

### 🔍 Objeto: `numerical_data`

#### `numerical_data.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:223 (em CriticAgent._validate_numerical_consistency)
```

### 🔍 Objeto: `operation`

#### `operation.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:565 (em OrchestratorManager._is_integration_operation)
```

### 🔍 Objeto: `operation_mapping`

#### `operation_mapping.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:600 (em IntelligenceCoordinator._component_supports_operation)
```

### 🔍 Objeto: `operation_type`

#### `operation_type.lower` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:357 (em OrchestratorManager._validate_operation_security)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:363 (em OrchestratorManager._validate_operation_security)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:363 (em OrchestratorManager._validate_operation_security)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:427 (em OrchestratorManager._detect_appropriate_orchestrator)
```

### 🔍 Objeto: `option_evaluations`

#### `option_evaluations.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:242 (em IntelligenceProcessor.make_intelligent_decision)
```

#### `option_evaluations.sort` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:245 (em IntelligenceProcessor.make_intelligent_decision)
```

### 🔍 Objeto: `orch_instance`

#### `orch_instance.health_check` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:674 (em OrchestratorManager.get_orchestrator_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:710 (em OrchestratorManager.health_check)
```

#### `orch_instance.get_status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:671 (em OrchestratorManager.get_orchestrator_status)
```

### 🔍 Objeto: `orch_type`

#### `orch_type.value` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:675 (em OrchestratorManager.get_orchestrator_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:680 (em OrchestratorManager.get_orchestrator_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:683 (em OrchestratorManager.get_orchestrator_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:686 (em OrchestratorManager.get_orchestrator_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:687 (em OrchestratorManager.get_orchestrator_status)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `orchestrator`

#### `orchestrator.create_session` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:510 (em OrchestratorManager.top-level)
```

#### `orchestrator.complete_session` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:517 (em OrchestratorManager.top-level)
```

#### `orchestrator.execute_session_workflow` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:522 (em OrchestratorManager.top-level)
```

#### `orchestrator.process_query` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:535 (em OrchestratorManager.top-level)
```

### 🔍 Objeto: `orchestrator_manager`

#### `orchestrator_manager.health_check` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:671 (em ValidadorSistemaCompleto._testar_health_checks)
```

### 🔍 Objeto: `orchestrators_real`

#### `orchestrators_real.append` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:163 (em ClaudeAIMetrics.get_orchestrator_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:169 (em ClaudeAIMetrics.get_orchestrator_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:178 (em ClaudeAIMetrics.get_orchestrator_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:184 (em ClaudeAIMetrics.get_orchestrator_metrics)
```

### 🔍 Objeto: `original_response`

#### `original_response.copy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:161 (em AdaptiveLearning.adapt_response)
```

### 🔍 Objeto: `os`

#### `os.path` (68 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:15 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:15 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:15 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:51 (em ImportFixer.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:51 (em ImportFixer.__init__)
  ... e mais 63 ocorrências
```

#### `os.getenv` (40 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_ativo.py:15 (em module.verificar_sistema_ativo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:18 (em module.verificar_configuracao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:57 (em module.verificar_loop_no_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:80 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_status_completo.py:20 (em module.verificar_status)
  ... e mais 35 ocorrências
```

#### `os.path.dirname` (27 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:15 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:51 (em ImportFixer.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:222 (em ClassDuplicateFinder.generate_report)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:14 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:72 (em module.check_anti_loop_protection)
  ... e mais 22 ocorrências
```

#### `os.path.join` (17 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:15 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:64 (em ImportFixer._find_latest_error_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:89 (em ImportFixer.fix_imports)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:235 (em ImportFixer._add_get_function)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:14 (em module.top-level)
  ... e mais 12 ocorrências
```

#### `os.getenv().lower` (12 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:18 (em module.verificar_configuracao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:57 (em module.verificar_loop_no_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:80 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:452 (em SystemConfig._detect_active_profile)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:457 (em SystemConfig._detect_active_profile)
  ... e mais 7 ocorrências
```

#### `os.environ` (12 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:94 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:98 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:102 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:126 (em ClaudeAIConfig.get_anthropic_api_key)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/integration_manager.py:335 (em IntegrationManager.get_system_status)
  ... e mais 7 ocorrências
```

#### `os.path.abspath` (11 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:15 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:51 (em ImportFixer.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:14 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:15 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:9 (em module.top-level)
  ... e mais 6 ocorrências
```

#### `os.environ.get` (9 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:126 (em ClaudeAIConfig.get_anthropic_api_key)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/integration_manager.py:335 (em IntegrationManager.get_system_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/integration_manager.py:336 (em IntegrationManager.get_system_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:34 (em StandaloneContextManager._load_config)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:35 (em StandaloneContextManager._load_config)
  ... e mais 4 ocorrências
```

#### `os.walk` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:39 (em module.contar_arquivos_detalhado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:152 (em module.contar_linhas_codigo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:188 (em module.verificar_modulos_especiais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:52 (em module.categorizar_todos_modulos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:43 (em ImportChecker.check_directory)
  ... e mais 3 ocorrências
```

#### `os.path.relpath` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:103 (em ImportFixer._fix_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:57 (em ImportChecker.check_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:185 (em ImportChecker.check_import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:196 (em ImportChecker.check_import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:207 (em ImportChecker.check_import)
  ... e mais 1 ocorrências
```

#### `os.path.exists` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:237 (em ImportFixer._add_get_function)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:76 (em module.check_anti_loop_protection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:101 (em module.check_anti_loop_protection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:59 (em ReadmeScanner._localizar_readme)
```

#### `os.name` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:70 (em CursorMonitor.clear_screen)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:121 (em CursorMonitor.get_system_stats)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:131 (em CursorMonitor.check_flask_process)
```

#### `os.getcwd` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:52 (em ReadmeScanner._localizar_readme)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:78 (em SecurityGuard._is_production_mode)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:79 (em SecurityGuard._is_production_mode)
```

#### `os.environ.get().lower` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:34 (em StandaloneContextManager._load_config)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:35 (em StandaloneContextManager._load_config)
```

#### `os.listdir` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:58 (em ImportFixer._find_latest_error_file)
```

#### `os.path.split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:226 (em ImportChecker.filepath_to_module)
```

#### `os.environ.pop` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:94 (em module.top-level)
```

#### `os.system` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:70 (em CursorMonitor.clear_screen)
```

#### `os.path.isabs` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:187 (em FileScanner.read_file_content)
```

#### `os.sys.version` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:219 (em ProjectScanner._generate_scan_metadata)
```

#### `os.sys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:219 (em ProjectScanner._generate_scan_metadata)
```

#### `os.path.normpath` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:58 (em ReadmeScanner._localizar_readme)
```

#### `os.getenv().startswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:71 (em SecurityGuard._is_production_mode)
```

### 🔍 Objeto: `outliers`

#### `outliers.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:569 (em PerformanceAnalyzer.detect_outliers)
```

### 🔍 Objeto: `output`

#### `output.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:537 (em IntelligenceProcessor._learn_from_processing)
```

#### `output.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:636 (em IntelligenceProcessor._focused_synthesis)
```

### 🔍 Objeto: `outros_arquivos_local`

#### `outros_arquivos_local.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:70 (em module.contar_arquivos_detalhado)
```

### 🔍 Objeto: `overview`

#### `overview.get` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/response_utils.py:133 (em ResponseUtils._formatar_analise_projeto)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/response_utils.py:134 (em ResponseUtils._formatar_analise_projeto)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/response_utils.py:135 (em ResponseUtils._formatar_analise_projeto)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/response_utils.py:136 (em ResponseUtils._formatar_analise_projeto)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/response_utils.py:138 (em ResponseUtils._formatar_analise_projeto)
```

### 🔍 Objeto: `p`

#### `p.pattern_type` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:194 (em HumanInLoopLearning._create_learning_pattern)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:337 (em HumanInLoopLearning.generate_learning_report)
```

#### `p.strip` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:234 (em KnowledgeMemory.buscar_grupos_aplicaveis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:234 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `p.created_at` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:315 (em HumanInLoopLearning.generate_learning_report)
```

#### `p.description` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:338 (em HumanInLoopLearning.generate_learning_report)
```

#### `p.frequency` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:339 (em HumanInLoopLearning.generate_learning_report)
```

#### `p.confidence_score` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:340 (em HumanInLoopLearning.generate_learning_report)
```

#### `p.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:188 (em LearningCore.aplicar_conhecimento)
```

### 🔍 Objeto: `padrao`

#### `padrao.interpretation` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:359 (em PatternLearner.buscar_padroes_aplicaveis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:360 (em PatternLearner.buscar_padroes_aplicaveis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:363 (em PatternLearner.buscar_padroes_aplicaveis)
```

#### `padrao.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:306 (em PatternLearner._salvar_padrao_otimizado)
```

#### `padrao.pattern_type` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:369 (em PatternLearner.buscar_padroes_aplicaveis)
```

#### `padrao.pattern_text` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:370 (em PatternLearner.buscar_padroes_aplicaveis)
```

#### `padrao.confidence` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:372 (em PatternLearner.buscar_padroes_aplicaveis)
```

#### `padrao.usage_count` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:373 (em PatternLearner.buscar_padroes_aplicaveis)
```

### 🔍 Objeto: `padrao_novo`

#### `padrao_novo.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:311 (em PatternLearner._salvar_padrao_otimizado)
```

#### `padrao_novo.confidence` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:312 (em PatternLearner._salvar_padrao_otimizado)
```

### 🔍 Objeto: `padroes`

#### `padroes.append` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:117 (em PatternLearner._extrair_padroes_periodo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:140 (em PatternLearner._extrair_padroes_dominio)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:161 (em PatternLearner._extrair_padroes_intencao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:184 (em PatternLearner._extrair_padroes_entidades)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:198 (em PatternLearner._extrair_padroes_entidades)
  ... e mais 2 ocorrências
```

#### `padroes.extend` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:85 (em PatternLearner._extrair_padroes_multipos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:88 (em PatternLearner._extrair_padroes_multipos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:91 (em PatternLearner._extrair_padroes_multipos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:94 (em PatternLearner._extrair_padroes_multipos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:97 (em PatternLearner._extrair_padroes_multipos)
```

#### `padroes.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:485 (em AutoMapper._ajustar_confianca_com_analise)
```

### 🔍 Objeto: `padroes_aplicaveis`

#### `padroes_aplicaveis.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:368 (em PatternLearner.buscar_padroes_aplicaveis)
```

### 🔍 Objeto: `padroes_detectados`

#### `padroes_detectados.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:62 (em PatternLearner.extrair_e_salvar_padroes)
```

### 🔍 Objeto: `padroes_intencao`

#### `padroes_intencao.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:114 (em IntentionAnalyzer._detectar_intencoes_multiplas)
```

### 🔍 Objeto: `palavra`

#### `palavra.capitalize` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:201 (em AutoMapper._gerar_nome_modelo)
```

### 🔍 Objeto: `palavras_chave`

#### `palavras_chave.append` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:306 (em NLPEnhancedAnalyzer._extrair_palavras_chave)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:311 (em NLPEnhancedAnalyzer._extrair_palavras_chave)
```

### 🔍 Objeto: `palavras_corrigidas`

#### `palavras_corrigidas.append` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:199 (em NLPEnhancedAnalyzer._aplicar_correcoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:203 (em NLPEnhancedAnalyzer._aplicar_correcoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:205 (em NLPEnhancedAnalyzer._aplicar_correcoes)
```

### 🔍 Objeto: `palavras_relevantes`

#### `palavras_relevantes.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:398 (em PatternLearner._extrair_palavras_chave_dominio)
```

### 🔍 Objeto: `palavras_termo`

#### `palavras_termo.intersection` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:416 (em SemanticValidator._calcular_similaridade_termo_campo)
```

### 🔍 Objeto: `palavras_unicas`

#### `palavras_unicas.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:318 (em NLPEnhancedAnalyzer._extrair_palavras_chave)
```

### 🔍 Objeto: `parameters`

#### `parameters.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1170 (em MainOrchestrator._resolve_parameters)
```

### 🔍 Objeto: `params`

#### `params.get` (11 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:493 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:511 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:513 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:514 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:518 (em OrchestratorManager.top-level)
  ... e mais 6 ocorrências
```

#### `params.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:163 (em QueryMapper._apply_template)
```

### 🔍 Objeto: `parent_parts`

#### `parent_parts.pop` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:163 (em ImportChecker.check_import)
```

#### `parent_parts.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:167 (em ImportChecker.check_import)
```

### 🔍 Objeto: `parsed_values`

#### `parsed_values.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:238 (em CriticAgent._validate_numerical_consistency)
```

### 🔍 Objeto: `parser`

#### `parser.add_argument` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:361 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:362 (em module.main)
```

#### `parser.parse_args` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:364 (em module.main)
```

### 🔍 Objeto: `part`

#### `part.startswith` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:43 (em module.contar_arquivos_detalhado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:154 (em module.contar_linhas_codigo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:189 (em module.verificar_modulos_especiais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:54 (em module.categorizar_todos_modulos)
```

### 🔍 Objeto: `partial_text`

#### `partial_text.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:161 (em AutoCommandProcessor.get_command_suggestions)
```

### 🔍 Objeto: `parts`

#### `parts.insert` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:228 (em ImportChecker.filepath_to_module)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:234 (em ImportChecker.filepath_to_module)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:235 (em ImportChecker.filepath_to_module)
```

### 🔍 Objeto: `pasta_path`

#### `pasta_path.rglob` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:72 (em DetectorModulosOrfaos._analisar_pasta)
```

### 🔍 Objeto: `patch`

#### `patch.object` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:125 (em TestLoopPrevention.test_circular_reference_detection)
```

### 🔍 Objeto: `path`

#### `path.suffix` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:238 (em BaseValidationUtils.validate_file_path)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:238 (em BaseValidationUtils.validate_file_path)
```

#### `path.is_absolute` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:232 (em BaseValidationUtils.validate_file_path)
```

#### `path.exists` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:232 (em BaseValidationUtils.validate_file_path)
```

#### `path.suffix.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:238 (em BaseValidationUtils.validate_file_path)
```

### 🔍 Objeto: `pattern`

#### `pattern.lower` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:170 (em AutoCommandProcessor.get_command_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:305 (em AutoCommandProcessor._detect_commands)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:460 (em AutoCommandProcessor._calculate_detection_confidence)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:464 (em AutoCommandProcessor._calculate_detection_confidence)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:123 (em QueryMapper._pattern_matches)
```

#### `pattern.confidence_score` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:219 (em HumanInLoopLearning._create_learning_pattern)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:226 (em HumanInLoopLearning._add_to_improvement_queue)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:231 (em HumanInLoopLearning._add_to_improvement_queue)
```

#### `pattern.lower().split` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:170 (em AutoCommandProcessor.get_command_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:464 (em AutoCommandProcessor._calculate_detection_confidence)
```

#### `pattern.pattern_id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:227 (em HumanInLoopLearning._add_to_improvement_queue)
```

#### `pattern.description` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:229 (em HumanInLoopLearning._add_to_improvement_queue)
```

#### `pattern.improvement_suggestion` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:230 (em HumanInLoopLearning._add_to_improvement_queue)
```

#### `pattern.frequency` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:232 (em HumanInLoopLearning._add_to_improvement_queue)
```

#### `pattern.examples` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:233 (em HumanInLoopLearning._add_to_improvement_queue)
```

#### `pattern.pattern_type` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:238 (em HumanInLoopLearning._add_to_improvement_queue)
```

#### `pattern.lower().replace().replace().split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:123 (em QueryMapper._pattern_matches)
```

#### `pattern.lower().replace().replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:123 (em QueryMapper._pattern_matches)
```

#### `pattern.lower().replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:123 (em QueryMapper._pattern_matches)
```

### 🔍 Objeto: `pattern_count`

#### `pattern_count.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:253 (em UninitializedVariableFinder.generate_report)
```

### 🔍 Objeto: `patterns`

#### `patterns.append` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:203 (em QueryAnalyzer._detect_temporal_patterns)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:344 (em AdaptiveLearning._detect_patterns)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:349 (em AdaptiveLearning._detect_patterns)
```

### 🔍 Objeto: `pd`

#### `pd.DataFrame` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:59 (em DataProcessor.process_data)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:263 (em DataProcessor.aggregate_data)
```

### 🔍 Objeto: `pedido`

#### `pedido.data_pedido` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:450 (em ContextProcessor._serialize_pedido)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:277 (em DataProvider._serialize_pedido)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:277 (em DataProvider._serialize_pedido)
```

#### `pedido.id` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:447 (em ContextProcessor._serialize_pedido)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:274 (em DataProvider._serialize_pedido)
```

#### `pedido.num_pedido` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:448 (em ContextProcessor._serialize_pedido)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:275 (em DataProvider._serialize_pedido)
```

#### `pedido.valor_total` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:278 (em DataProvider._serialize_pedido)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:278 (em DataProvider._serialize_pedido)
```

#### `pedido.raz_social_red` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:449 (em ContextProcessor._serialize_pedido)
```

#### `pedido.valor_saldo_total` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:451 (em ContextProcessor._serialize_pedido)
```

#### `pedido.status_calculado` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:452 (em ContextProcessor._serialize_pedido)
```

#### `pedido.cliente` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:276 (em DataProvider._serialize_pedido)
```

#### `pedido.data_pedido.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:277 (em DataProvider._serialize_pedido)
```

#### `pedido.status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:279 (em DataProvider._serialize_pedido)
```

#### `pedido.vendedor` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:280 (em DataProvider._serialize_pedido)
```

### 🔍 Objeto: `pendencia`

#### `pendencia.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:459 (em ContextProcessor._serialize_pendencia)
```

#### `pendencia.numero_nf` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:460 (em ContextProcessor._serialize_pendencia)
```

#### `pendencia.nome_cliente` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:461 (em ContextProcessor._serialize_pendencia)
```

#### `pendencia.descricao` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:462 (em ContextProcessor._serialize_pendencia)
```

#### `pendencia.data_criacao` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:463 (em ContextProcessor._serialize_pendencia)
```

#### `pendencia.resolvida` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:464 (em ContextProcessor._serialize_pendencia)
```

### 🔍 Objeto: `pending_steps`

#### `pending_steps.remove` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:889 (em MainOrchestrator.top-level)
```

### 🔍 Objeto: `performance_info`

#### `performance_info.update` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:339 (em DatabaseScanner._get_performance_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:341 (em DatabaseScanner._get_performance_info)
```

### 🔍 Objeto: `pilha`

#### `pilha.pop` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:318 (em RelationshipMapper._explorar_cluster)
```

#### `pilha.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:338 (em RelationshipMapper._explorar_cluster)
```

### 🔍 Objeto: `pk`

#### `pk.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:215 (em MetadataReader._obter_constraints_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:216 (em MetadataReader._obter_constraints_tabela)
```

### 🔍 Objeto: `pk_constraint`

#### `pk_constraint.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:125 (em StructureScanner._discover_models_via_database)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:136 (em StructureScanner._discover_models_via_database)
```

### 🔍 Objeto: `possiveis_orfaos`

#### `possiveis_orfaos.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:136 (em module.verificar_integracao_modulos_funcionais)
```

### 🔍 Objeto: `predictions`

#### `predictions.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:764 (em IntelligenceProcessor._make_trend_predictions)
```

### 🔍 Objeto: `preference_data`

#### `preference_data.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:460 (em AdaptiveLearning._generate_preference_recommendations)
```

### 🔍 Objeto: `preferences`

#### `preferences.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:128 (em AdaptiveLearning.get_personalized_recommendations)
```

### 🔍 Objeto: `primeiro_exemplo`

#### `primeiro_exemplo.isdigit` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:425 (em AutoMapper._melhorar_termos_com_analise)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:429 (em AutoMapper._melhorar_termos_com_analise)
```

#### `primeiro_exemplo.replace().replace().replace().isdigit` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:421 (em AutoMapper._melhorar_termos_com_analise)
```

#### `primeiro_exemplo.replace().replace().replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:421 (em AutoMapper._melhorar_termos_com_analise)
```

#### `primeiro_exemplo.replace().replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:421 (em AutoMapper._melhorar_termos_com_analise)
```

#### `primeiro_exemplo.replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:421 (em AutoMapper._melhorar_termos_com_analise)
```

#### `primeiro_exemplo.startswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:437 (em AutoMapper._melhorar_termos_com_analise)
```

### 🔍 Objeto: `priority`

#### `priority.value` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:259 (em SessionOrchestrator.create_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:275 (em SessionOrchestrator.create_session)
```

### 🔍 Objeto: `priority_filter`

#### `priority_filter.upper` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:245 (em HumanInLoopLearning.get_improvement_suggestions)
```

### 🔍 Objeto: `priority_order`

#### `priority_order.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:251 (em HumanInLoopLearning.get_improvement_suggestions)
```

### 🔍 Objeto: `priority_value`

#### `priority_value.upper` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:498 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:500 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:502 (em OrchestratorManager.top-level)
```

### 🔍 Objeto: `problem`

#### `problem.startswith` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/__init__.py:254 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/__init__.py:256 (em module.top-level)
```

### 🔍 Objeto: `problemas`

#### `problemas.append` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_ativo.py:129 (em module.diagnosticar_problemas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_ativo.py:138 (em module.diagnosticar_problemas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_ativo.py:141 (em module.diagnosticar_problemas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_ativo.py:150 (em module.diagnosticar_problemas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_ativo.py:153 (em module.diagnosticar_problemas)
```

### 🔍 Objeto: `process`

#### `process.extractOne` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:193 (em NLPEnhancedAnalyzer._aplicar_correcoes)
```

### 🔍 Objeto: `processed_data_list`

#### `processed_data_list.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:172 (em DataProcessor.batch_process)
```

### 🔍 Objeto: `processing_times`

#### `processing_times.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:145 (em PerformanceAnalyzer.analyze_ai_performance)
```

### 🔍 Objeto: `processor`

#### `processor.gerar_resposta_otimizada` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:767 (em SessionOrchestrator._execute_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:966 (em SessionOrchestrator._process_deliveries_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:1038 (em SessionOrchestrator._process_general_inquiry)
```

#### `processor.client` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:208 (em ValidadorSistemaReal._test_response_processor)
```

#### `processor.process_data` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/__init__.py:171 (em module.process_data)
```

#### `processor.process_query` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/__init__.py:199 (em module.process_query)
```

#### `processor.process_context` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/__init__.py:227 (em module.process_context)
```

#### `processor.process_intelligence` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/__init__.py:255 (em module.process_intelligence)
```

#### `processor.synthesize_multi_source_intelligence` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/__init__.py:282 (em module.synthesize_multi_source_intelligence)
```

#### `processor.batch_process` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/__init__.py:310 (em module.batch_process_data)
```

#### `processor.get_status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:198 (em ProcessorRegistry.get_processor_info)
```

#### `processor.health_check` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:210 (em ProcessorRegistry._check_processor_health)
```

#### `processor.initialized` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:214 (em ProcessorRegistry._check_processor_health)
```

### 🔍 Objeto: `profile`

#### `profile.get` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:124 (em AdaptiveLearning.get_personalized_recommendations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:125 (em AdaptiveLearning.get_personalized_recommendations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:171 (em AdaptiveLearning.adapt_response)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:308 (em AdaptiveLearning._extract_preferences)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:427 (em AdaptiveLearning._calculate_learning_confidence)
  ... e mais 1 ocorrências
```

#### `profile.setdefault` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:517 (em AdaptiveLearning._handle_negative_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:521 (em AdaptiveLearning._handle_negative_feedback)
```

#### `profile.get().get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:532 (em AdaptiveLearning._handle_positive_feedback)
```

### 🔍 Objeto: `profile_path`

#### `profile_path.exists` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:537 (em SystemConfig._load_profile_config)
```

#### `profile_path.parent.mkdir` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:564 (em SystemConfig._save_profile_config)
```

#### `profile_path.parent` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:564 (em SystemConfig._save_profile_config)
```

### 🔍 Objeto: `provider`

#### `provider.gerar_system_prompt_real` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/data_manager.py:197 (em DataManager.provide_data)
```

#### `provider.gerar_relatorio_dados_sistema` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/data_manager.py:199 (em DataManager.provide_data)
```

#### `provider.buscar_clientes_reais` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/data_manager.py:201 (em DataManager.provide_data)
```

#### `provider.buscar_transportadoras_reais` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/data_manager.py:203 (em DataManager.provide_data)
```

#### `provider.buscar_todos_modelos_reais` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/data_manager.py:205 (em DataManager.provide_data)
```

#### `provider.validar_cliente_existe` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/data_manager.py:283 (em DataManager.validate_client)
```

#### `provider.sugerir_cliente_similar` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/data_manager.py:293 (em DataManager.validate_client)
```

### 🔍 Objeto: `psutil`

#### `psutil.disk_usage().percent` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:121 (em CursorMonitor.get_system_stats)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:121 (em CursorMonitor.get_system_stats)
```

#### `psutil.disk_usage` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:121 (em CursorMonitor.get_system_stats)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:121 (em CursorMonitor.get_system_stats)
```

#### `psutil.cpu_percent` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:119 (em CursorMonitor.get_system_stats)
```

#### `psutil.virtual_memory().percent` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:120 (em CursorMonitor.get_system_stats)
```

#### `psutil.virtual_memory` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:120 (em CursorMonitor.get_system_stats)
```

#### `psutil.boot_time` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:122 (em CursorMonitor.get_system_stats)
```

### 🔍 Objeto: `py_file`

#### `py_file.name` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:37 (em ClassDuplicateFinder.scan_directory)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:99 (em UninitializedVariableFinder.scan_directory)
```

### 🔍 Objeto: `qualidade`

#### `qualidade.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:176 (em ResponseProcessor.gerar_resposta_otimizada)
```

### 🔍 Objeto: `query`

#### `query.filter` (75 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:119 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:128 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:133 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:135 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:138 (em ExcelEntregas._buscar_dados_entregas)
  ... e mais 70 ocorrências
```

#### `query.lower` (34 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:569 (em AnalyzerManager.get_best_analyzer)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:53 (em MetacognitiveAnalyzer._assess_query_complexity)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:56 (em MetacognitiveAnalyzer._assess_query_complexity)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:56 (em MetacognitiveAnalyzer._assess_query_complexity)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:111 (em MetacognitiveAnalyzer._assess_domain_coverage)
  ... e mais 29 ocorrências
```

#### `query.limit().all` (20 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:163 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:136 (em ExcelFaturamento._buscar_dados_faturamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:154 (em ExcelFretes._buscar_dados_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:201 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:88 (em AgendamentosLoader._execute_query)
  ... e mais 15 ocorrências
```

#### `query.limit` (20 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:163 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:136 (em ExcelFaturamento._buscar_dados_faturamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:154 (em ExcelFretes._buscar_dados_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:201 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:88 (em AgendamentosLoader._execute_query)
  ... e mais 15 ocorrências
```

#### `query.split` (12 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:306 (em AnalyzerManager._should_use_nlp_analysis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:585 (em AnalyzerManager.get_best_analyzer)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:48 (em IntentionAnalyzer.analyze_intention)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:52 (em MetacognitiveAnalyzer._assess_query_complexity)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:55 (em MetacognitiveAnalyzer._assess_query_complexity)
  ... e mais 7 ocorrências
```

#### `query.order_by` (11 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:160 (em ExcelEntregas._buscar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:133 (em ExcelFaturamento._buscar_dados_faturamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:151 (em ExcelFretes._buscar_dados_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:198 (em ExcelPedidos._buscar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:194 (em ContextLoader._carregar_entregas_banco)
  ... e mais 6 ocorrências
```

#### `query.count` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:293 (em ContextProcessor._carregar_dados_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:326 (em ContextProcessor._carregar_dados_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:359 (em ContextProcessor._carregar_dados_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:387 (em ContextProcessor._carregar_dados_financeiro)
```

#### `query.join().filter` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:69 (em AgendamentosLoader._build_agendamentos_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:73 (em EmbarquesLoader._build_embarques_query)
```

#### `query.join` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:69 (em AgendamentosLoader._build_agendamentos_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:73 (em EmbarquesLoader._build_embarques_query)
```

#### `query.lower().split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:163 (em QueryAnalyzer._extract_entities)
```

#### `query.order_by().limit().all` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:194 (em ContextLoader._carregar_entregas_banco)
```

#### `query.order_by().limit` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:194 (em ContextLoader._carregar_entregas_banco)
```

#### `query.lower().strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:91 (em QueryMapper.map_query)
```

#### `query.replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:217 (em SemanticLoopProcessor._expand_unmapped_terms)
```

#### `query.strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:131 (em BaseValidationUtils.validate_query)
```

### 🔍 Objeto: `query_base`

#### `query_base.filter` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:146 (em ValidationUtils._calcular_estatisticas_especificas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:151 (em ValidationUtils._calcular_estatisticas_especificas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:160 (em ValidationUtils._calcular_estatisticas_especificas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:163 (em ValidationUtils._calcular_estatisticas_especificas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:166 (em ValidationUtils._calcular_estatisticas_especificas)
  ... e mais 1 ocorrências
```

#### `query_base.filter().count` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:166 (em ValidationUtils._calcular_estatisticas_especificas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:167 (em ValidationUtils._calcular_estatisticas_especificas)
```

#### `query_base.count` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/data_validator.py:165 (em ValidationUtils._calcular_estatisticas_especificas)
```

### 🔍 Objeto: `query_mapper`

#### `query_mapper.analisar_consulta_semantica` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/__init__.py:89 (em module.analyze_query_mapping)
```

### 🔍 Objeto: `query_processor`

#### `query_processor.process_query` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:101 (em ProcessorManager.process_query)
```

### 🔍 Objeto: `query_types`

#### `query_types.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:383 (em AdaptiveLearning._detect_query_pattern)
```

### 🔍 Objeto: `r`

#### `r.transportadora` (9 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:123 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:123 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:148 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:148 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:144 (em EntregasLoader._format_entregas_results)
  ... e mais 4 ocorrências
```

#### `r.data_agendamento` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:106 (em AgendamentosLoader._format_agendamentos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:106 (em AgendamentosLoader._format_agendamentos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:107 (em AgendamentosLoader._format_agendamentos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:107 (em AgendamentosLoader._format_agendamentos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:108 (em AgendamentosLoader._format_agendamentos_results)
  ... e mais 3 ocorrências
```

#### `r.data_criacao` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:127 (em AgendamentosLoader._format_agendamentos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:127 (em AgendamentosLoader._format_agendamentos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:145 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:145 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:166 (em FretesLoader._format_fretes_results)
  ... e mais 3 ocorrências
```

#### `r.data_embarque` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:109 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:131 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:146 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:146 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:135 (em EntregasLoader._format_entregas_results)
  ... e mais 3 ocorrências
```

#### `r.get` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:737 (em IntelligenceCoordinator._calculate_performance_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:738 (em IntelligenceCoordinator._calculate_performance_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:864 (em IntelligenceCoordinator._calculate_overall_confidence)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:160 (em ProcessorCoordinator.execute_parallel_processors)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:220 (em ProcessorManager.reload_processors)
  ... e mais 2 ocorrências
```

#### `r.data_entrega_prevista` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:107 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:107 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:125 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:125 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:136 (em EntregasLoader._format_entregas_results)
  ... e mais 1 ocorrências
```

#### `r.cliente` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:112 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:133 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:141 (em FretesLoader._format_fretes_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:164 (em FretesLoader._format_fretes_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:104 (em PedidosLoader._format_pedidos_results)
  ... e mais 1 ocorrências
```

#### `r.valor_total` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:99 (em FaturamentoLoader._format_faturamento_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:112 (em FaturamentoLoader._format_faturamento_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:129 (em FaturamentoLoader._format_faturamento_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:98 (em PedidosLoader._format_pedidos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:112 (em PedidosLoader._format_pedidos_results)
  ... e mais 1 ocorrências
```

#### `r.entregue` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:101 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:107 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:121 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:137 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:139 (em EntregasLoader._format_entregas_results)
```

#### `r.peso_total` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:142 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:173 (em FretesLoader._format_fretes_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:99 (em PedidosLoader._format_pedidos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:113 (em PedidosLoader._format_pedidos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:123 (em PedidosLoader._format_pedidos_results)
```

#### `r.data_criacao.strftime` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:127 (em AgendamentosLoader._format_agendamentos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:145 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:166 (em FretesLoader._format_fretes_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:121 (em PedidosLoader._format_pedidos_results)
```

#### `r.status` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:115 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:147 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:119 (em FretesLoader._format_fretes_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:168 (em FretesLoader._format_fretes_results)
```

#### `r.transportadora.razao_social` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:123 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:148 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:127 (em FretesLoader._format_fretes_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:169 (em FretesLoader._format_fretes_results)
```

#### `r.itens` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:140 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:141 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:153 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:154 (em EmbarquesLoader._format_embarques_results)
```

#### `r.valor_cotado` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:113 (em FretesLoader._format_fretes_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:135 (em FretesLoader._format_fretes_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:149 (em FretesLoader._format_fretes_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:170 (em FretesLoader._format_fretes_results)
```

#### `r.valor_considerado` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:114 (em FretesLoader._format_fretes_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:136 (em FretesLoader._format_fretes_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:150 (em FretesLoader._format_fretes_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:171 (em FretesLoader._format_fretes_results)
```

#### `r.created_at` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:191 (em SessionMemory.get_sessions_by_user)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:191 (em SessionMemory.get_sessions_by_user)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:245 (em SessionMemory.search_sessions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:245 (em SessionMemory.search_sessions)
```

#### `r.updated_at` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:192 (em SessionMemory.get_sessions_by_user)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:192 (em SessionMemory.get_sessions_by_user)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:246 (em SessionMemory.search_sessions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:246 (em SessionMemory.search_sessions)
```

#### `r.numero_embarque` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:144 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:143 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:175 (em FretesLoader._format_fretes_results)
```

#### `r.data_embarque.strftime` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:146 (em EmbarquesLoader._format_embarques_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:135 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:167 (em FretesLoader._format_fretes_results)
```

#### `r.destino` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:134 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:165 (em FretesLoader._format_fretes_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:126 (em PedidosLoader._format_pedidos_results)
```

#### `r.observacoes` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:129 (em AgendamentosLoader._format_agendamentos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:127 (em PedidosLoader._format_pedidos_results)
```

#### `r.numero_nf` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:132 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:126 (em FaturamentoLoader._format_faturamento_results)
```

#### `r.data_entrega_real` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:138 (em EntregasLoader._format_entregas_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:138 (em EntregasLoader._format_entregas_results)
```

#### `r.nome_cliente` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:105 (em FaturamentoLoader._format_faturamento_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:127 (em FaturamentoLoader._format_faturamento_results)
```

#### `r.cnpj_cliente` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:110 (em FaturamentoLoader._format_faturamento_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:128 (em FaturamentoLoader._format_faturamento_results)
```

#### `r.data_fatura` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:130 (em FaturamentoLoader._format_faturamento_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:130 (em FaturamentoLoader._format_faturamento_results)
```

#### `r.data_expedicao` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:125 (em PedidosLoader._format_pedidos_results)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:125 (em PedidosLoader._format_pedidos_results)
```

#### `r.session_id` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:190 (em SessionMemory.get_sessions_by_user)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:244 (em SessionMemory.search_sessions)
```

#### `r.created_at.isoformat` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:191 (em SessionMemory.get_sessions_by_user)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:245 (em SessionMemory.search_sessions)
```

#### `r.updated_at.isoformat` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:192 (em SessionMemory.get_sessions_by_user)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:246 (em SessionMemory.search_sessions)
```

#### `r.user_id` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:193 (em SessionMemory.get_sessions_by_user)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:247 (em SessionMemory.search_sessions)
```

#### `r.metadata_jsonb` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:194 (em SessionMemory.get_sessions_by_user)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:248 (em SessionMemory.search_sessions)
```

#### `r.entrega_monitorada` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:122 (em AgendamentosLoader._format_agendamentos_results)
```

#### `r.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:125 (em AgendamentosLoader._format_agendamentos_results)
```

#### `r.data_agendamento.strftime` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:126 (em AgendamentosLoader._format_agendamentos_results)
```

#### `r.entrega_id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:133 (em AgendamentosLoader._format_agendamentos_results)
```

#### `r.placa_veiculo` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:149 (em EmbarquesLoader._format_embarques_results)
```

#### `r.motorista` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:150 (em EmbarquesLoader._format_embarques_results)
```

#### `r.data_entrega_prevista.strftime` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:136 (em EntregasLoader._format_entregas_results)
```

#### `r.data_entrega_real.strftime` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:138 (em EntregasLoader._format_entregas_results)
```

#### `r.lead_time` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:140 (em EntregasLoader._format_entregas_results)
```

#### `r.valor_nf` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:141 (em EntregasLoader._format_entregas_results)
```

#### `r.data_fatura.strftime` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:130 (em FaturamentoLoader._format_faturamento_results)
```

#### `r.origem` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:131 (em FaturamentoLoader._format_faturamento_results)
```

#### `r.incoterm` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:132 (em FaturamentoLoader._format_faturamento_results)
```

#### `r.numero_frete` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:163 (em FretesLoader._format_fretes_results)
```

#### `r.valor_pago` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:172 (em FretesLoader._format_fretes_results)
```

#### `r.cte_numero` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:174 (em FretesLoader._format_fretes_results)
```

#### `r.num_pedido` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:119 (em PedidosLoader._format_pedidos_results)
```

#### `r.data_expedicao.strftime` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:125 (em PedidosLoader._format_pedidos_results)
```

### 🔍 Objeto: `re`

#### `re.findall` (26 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:112 (em DetectorModulosOrfaos._extrair_definicoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:113 (em DetectorModulosOrfaos._extrair_definicoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:165 (em DetectorModulosOrfaos._extrair_imports)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:182 (em IntentionAnalyzer._detectar_especificidade)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:239 (em SemanticAnalyzer._extract_entities)
  ... e mais 21 ocorrências
```

#### `re.search` (24 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:64 (em module.categorizar_todos_modulos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:66 (em module.categorizar_todos_modulos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:68 (em module.categorizar_todos_modulos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:100 (em BaseCommand._extract_client_from_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:152 (em BaseCommand._extract_filters_advanced)
  ... e mais 19 ocorrências
```

#### `re.IGNORECASE` (18 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:64 (em module.categorizar_todos_modulos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:66 (em module.categorizar_todos_modulos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:68 (em module.categorizar_todos_modulos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:239 (em SemanticAnalyzer._extract_entities)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:313 (em FileScanner.search_in_files)
  ... e mais 13 ocorrências
```

#### `re.sub` (9 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:227 (em NLPEnhancedAnalyzer._tokenizar_basico)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:83 (em BaseCommand._sanitize_input)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:283 (em SecurityGuard.sanitize_input)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:286 (em SecurityGuard.sanitize_input)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:289 (em SecurityGuard.sanitize_input)
  ... e mais 4 ocorrências
```

#### `re.DOTALL` (9 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:111 (em ReadmeScanner.buscar_termos_naturais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:268 (em ReadmeScanner._buscar_campo_na_secao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:313 (em ReadmeScanner.obter_informacoes_campo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:320 (em ReadmeScanner.obter_informacoes_campo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:326 (em ReadmeScanner.obter_informacoes_campo)
  ... e mais 4 ocorrências
```

#### `re.escape` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:110 (em ReadmeScanner.buscar_termos_naturais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:129 (em ReadmeScanner.buscar_termos_naturais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:215 (em ReadmeScanner._extrair_secao_modelo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:216 (em ReadmeScanner._extrair_secao_modelo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:217 (em ReadmeScanner._extrair_secao_modelo)
  ... e mais 3 ocorrências
```

#### `re.MULTILINE` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:112 (em DetectorModulosOrfaos._extrair_definicoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:113 (em DetectorModulosOrfaos._extrair_definicoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:165 (em DetectorModulosOrfaos._extrair_imports)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:237 (em ReadmeScanner._extrair_secao_modelo)
```

#### `re.match` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:342 (em SecurityGuard.validate_token)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:100 (em BaseValidationUtils._validate_with_rules)
```

#### `re.sub().replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:236 (em CriticAgent._validate_numerical_consistency)
```

### 🔍 Objeto: `readers`

#### `readers.get` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:204 (em DiagnosticsAnalyzer.gerar_relatorio_enriquecido)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:205 (em DiagnosticsAnalyzer.gerar_relatorio_enriquecido)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:246 (em DiagnosticsAnalyzer._avaliar_integracao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:247 (em DiagnosticsAnalyzer._avaliar_integracao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:71 (em SemanticEnricher.enriquecer_mapeamento_com_readers)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `readme_data`

#### `readme_data.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:250 (em SemanticEnricher._sugestoes_readme_vs_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:363 (em SemanticEnricher._sugestoes_otimizacao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:378 (em SemanticEnricher._sugestoes_otimizacao)
```

### 🔍 Objeto: `readme_reader`

#### `readme_reader.validar_estrutura_readme` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:211 (em DiagnosticsAnalyzer.gerar_relatorio_enriquecido)
```

#### `readme_reader.buscar_termos_naturais` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:120 (em SemanticEnricher._enriquecer_via_readme)
```

#### `readme_reader.obter_informacoes_campo` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:127 (em SemanticEnricher._enriquecer_via_readme)
```

#### `readme_reader.listar_modelos_disponiveis` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:223 (em SemanticValidator.validar_consistencia_readme_banco)
```

### 🔍 Objeto: `readme_status`

#### `readme_status.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:290 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:291 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
```

### 🔍 Objeto: `ready_steps`

#### `ready_steps.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:877 (em MainOrchestrator.top-level)
```

### 🔍 Objeto: `reasoning`

#### `reasoning.append` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:713 (em IntelligenceProcessor._generate_decision_reasoning)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:716 (em IntelligenceProcessor._generate_decision_reasoning)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:719 (em IntelligenceProcessor._generate_decision_reasoning)
```

### 🔍 Objeto: `recomendacoes`

#### `recomendacoes.append` (22 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:789 (em ValidadorSistemaCompleto._gerar_recomendacoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:793 (em ValidadorSistemaCompleto._gerar_recomendacoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:797 (em ValidadorSistemaCompleto._gerar_recomendacoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:799 (em ValidadorSistemaCompleto._gerar_recomendacoes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:801 (em ValidadorSistemaCompleto._gerar_recomendacoes)
  ... e mais 17 ocorrências
```

### 🔍 Objeto: `recommendations`

#### `recommendations.append` (18 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:237 (em StructuralAnalyzer._generate_recommendations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:239 (em StructuralAnalyzer._generate_recommendations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:241 (em StructuralAnalyzer._generate_recommendations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:461 (em AdaptiveLearning._generate_preference_recommendations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:475 (em AdaptiveLearning._generate_pattern_recommendations)
  ... e mais 13 ocorrências
```

#### `recommendations.extend` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:129 (em AdaptiveLearning.get_personalized_recommendations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:135 (em AdaptiveLearning.get_personalized_recommendations)
```

### 🔍 Objeto: `redis_cache`

#### `redis_cache.set` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:225 (em BaseCommand._set_cached_result)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:452 (em ContextLoader._carregar_contexto_inteligente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:68 (em ContextMemory.store_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:71 (em SystemMemory.store_system_config)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:150 (em SystemMemory.store_component_state)
  ... e mais 1 ocorrências
```

#### `redis_cache.get` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:208 (em BaseCommand._get_cached_result)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:228 (em ContextLoader._carregar_contexto_inteligente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:98 (em ContextMemory.retrieve_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:101 (em SystemMemory.retrieve_system_config)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:180 (em SystemMemory.retrieve_component_state)
```

#### `redis_cache.cache_entregas_cliente` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:301 (em ContextLoader._carregar_contexto_inteligente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:372 (em ContextLoader._carregar_contexto_inteligente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:387 (em ContextLoader._carregar_contexto_inteligente)
```

#### `redis_cache.cache_estatisticas_cliente` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:414 (em ContextLoader._carregar_contexto_inteligente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:421 (em ContextLoader._carregar_contexto_inteligente)
```

#### `redis_cache._gerar_chave` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:219 (em ContextLoader._carregar_contexto_inteligente)
```

#### `redis_cache.delete` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:195 (em ContextMemory.clear_context)
```

### 🔍 Objeto: `reference_date`

#### `reference_date.isoformat` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/context_provider.py:177 (em ContextProvider.provide_temporal_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/context_provider.py:180 (em ContextProvider.provide_temporal_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/context_provider.py:200 (em ContextProvider.provide_temporal_context)
```

### 🔍 Objeto: `registry`

#### `registry.list_processors` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:226 (em ValidadorSistemaCompleto._testar_componentes_criticos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:333 (em ValidadorSistemaCompleto._testar_processor_registry)
```

#### `registry.get_registry_stats` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:703 (em ValidadorSistemaCompleto._testar_fallbacks)
```

### 🔍 Objeto: `regra`

#### `regra.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:99 (em SemanticValidator.validar_contexto_negocio)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:102 (em SemanticValidator.validar_contexto_negocio)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:122 (em SemanticValidator.validar_contexto_negocio)
```

### 🔍 Objeto: `rel_path`

#### `rel_path.parts` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:62 (em FileScanner.discover_all_templates)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:62 (em FileScanner.discover_all_templates)
```

### 🔍 Objeto: `relacionamentos`

#### `relacionamentos.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:84 (em RelationshipMapper.obter_relacionamentos)
```

#### `relacionamentos.extend` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:88 (em RelationshipMapper.obter_relacionamentos)
```

### 🔍 Objeto: `relacionamentos_entrada`

#### `relacionamentos_entrada.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:136 (em RelationshipMapper._buscar_relacionamentos_entrada)
```

### 🔍 Objeto: `relatorio`

#### `relatorio.get` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:282 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:289 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:297 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:311 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:317 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
```

### 🔍 Objeto: `relevant_responses`

#### `relevant_responses.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:313 (em CriticAgent._check_business_rule)
```

### 🔍 Objeto: `report`

#### `report.append` (91 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:171 (em ClassDuplicateFinder.generate_report)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:172 (em ClassDuplicateFinder.generate_report)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:173 (em ClassDuplicateFinder.generate_report)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:176 (em ClassDuplicateFinder.generate_report)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:177 (em ClassDuplicateFinder.generate_report)
  ... e mais 86 ocorrências
```

### 🔍 Objeto: `request`

#### `request.query.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:117 (em ProviderManager._detect_provision_type)
```

### 🔍 Objeto: `request_data`

#### `request_data.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:292 (em StandaloneIntegration.process_request)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:293 (em StandaloneIntegration.process_request)
```

### 🔍 Objeto: `requests`

#### `requests.exceptions` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:95 (em CursorMonitor.check_url)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:101 (em CursorMonitor.check_url)
```

#### `requests.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:85 (em CursorMonitor.check_url)
```

#### `requests.exceptions.ConnectionError` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:95 (em CursorMonitor.check_url)
```

#### `requests.exceptions.Timeout` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:101 (em CursorMonitor.check_url)
```

### 🔍 Objeto: `response`

#### `response.headers.get().startswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:93 (em CursorMonitor.check_url)
```

#### `response.headers.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:93 (em CursorMonitor.check_url)
```

#### `response.get().lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:311 (em CriticAgent._check_business_rule)
```

### 🔍 Objeto: `response_processor`

#### `response_processor.gerar_resposta_otimizada` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:65 (em ProcessorManager.process_response)
```

### 🔍 Objeto: `response_result`

#### `response_result.get` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:351 (em WebFlaskRoutes.api_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:352 (em WebFlaskRoutes.api_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:359 (em WebFlaskRoutes.api_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:365 (em WebFlaskRoutes.api_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:366 (em WebFlaskRoutes.api_query)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `response_text`

#### `response_text.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:239 (em TestLoopPrevention.test_anti_loop_response_quality)
```

### 🔍 Objeto: `resposta`

#### `resposta.lower` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:277 (em ResponseProcessor._avaliar_qualidade_resposta)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:277 (em ResponseProcessor._avaliar_qualidade_resposta)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:283 (em ResponseProcessor._avaliar_qualidade_resposta)
```

#### `resposta.split` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:288 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:376 (em ResponseProcessor._validar_resposta_final)
```

#### `resposta.count` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:288 (em ResponseProcessor._avaliar_qualidade_resposta)
```

#### `resposta.strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:372 (em ResponseProcessor._validar_resposta_final)
```

### 🔍 Objeto: `result`

#### `result.get` (49 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:97 (em module.teste_sistema_basico)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:107 (em module.teste_sistema_basico)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:183 (em module.teste_funcionalidades_avancadas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:183 (em module.teste_funcionalidades_avancadas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:205 (em module.teste_funcionalidades_avancadas)
  ... e mais 44 ocorrências
```

#### `result.stdout` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:138 (em CursorMonitor.check_flask_process)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:139 (em CursorMonitor.check_flask_process)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:163 (em CursorMonitor.run_validator)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:174 (em CursorMonitor.run_validator)
```

#### `result.get().get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:858 (em IntelligenceCoordinator._combine_all_insights)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:547 (em DataProcessor._update_global_stats)
```

#### `result.created_at` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:151 (em SessionMemory.get_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:151 (em SessionMemory.get_session)
```

#### `result.updated_at` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:152 (em SessionMemory.get_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:152 (em SessionMemory.get_session)
```

#### `result.rowcount` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:278 (em SessionMemory.cleanup_old_sessions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:364 (em SessionMemory.update_session_metadata)
```

#### `result.returncode` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:138 (em CursorMonitor.check_flask_process)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:161 (em CursorMonitor.run_validator)
```

#### `result.stdout.split` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:139 (em CursorMonitor.check_flask_process)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:163 (em CursorMonitor.run_validator)
```

#### `result.append` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:272 (em SuggestionsEngine._generate_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:275 (em SuggestionsEngine._generate_suggestions)
```

#### `result.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:112 (em IntelligenceCoordinator.coordinate_intelligence_operation)
```

#### `result.get().get().get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:858 (em IntelligenceCoordinator._combine_all_insights)
```

#### `result.first` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:309 (em PatternLearner._salvar_padrao_otimizado)
```

#### `result.fetchall` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:113 (em DatabaseLoader.load_data)
```

#### `result.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:116 (em DatabaseLoader.load_data)
```

#### `result.replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:164 (em QueryMapper._apply_template)
```

#### `result.scalar` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:164 (em KnowledgeMemory.descobrir_grupo_empresarial)
```

#### `result.session_id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:150 (em SessionMemory.get_session)
```

#### `result.created_at.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:151 (em SessionMemory.get_session)
```

#### `result.updated_at.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:152 (em SessionMemory.get_session)
```

#### `result.user_id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:153 (em SessionMemory.get_session)
```

#### `result.metadata_jsonb` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:154 (em SessionMemory.get_session)
```

#### `result.total_sessions` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:318 (em SessionMemory.get_session_stats)
```

#### `result.unique_users` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:319 (em SessionMemory.get_session_stats)
```

#### `result.avg_confidence` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:320 (em SessionMemory.get_session_stats)
```

#### `result.fretes_sessions` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:322 (em SessionMemory.get_session_stats)
```

#### `result.entregas_sessions` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:323 (em SessionMemory.get_session_stats)
```

#### `result.pedidos_sessions` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:324 (em SessionMemory.get_session_stats)
```

#### `result.stdout.strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:138 (em CursorMonitor.check_flask_process)
```

#### `result.stderr` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:176 (em CursorMonitor.run_validator)
```

#### `result.wasSuccessful` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:262 (em module.run_pre_commit_tests)
```

#### `result.errors` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:268 (em module.run_pre_commit_tests)
```

#### `result.failures` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:269 (em module.run_pre_commit_tests)
```

### 🔍 Objeto: `resultado`

#### `resultado.get` (13 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:728 (em ValidadorSistemaCompleto._processar_resultado_teste)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:145 (em CursorCommands._ativar_cursor_mode)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:110 (em ClaudeAIMetrics.get_system_health_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:111 (em ClaudeAIMetrics.get_system_health_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:112 (em ClaudeAIMetrics.get_system_health_metrics)
  ... e mais 8 ocorrências
```

#### `resultado.update` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:185 (em SmartBaseAgent.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:134 (em SemanticValidator.validar_contexto_negocio)
```

#### `resultado.get().get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:111 (em ClaudeAIMetrics.get_system_health_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:112 (em ClaudeAIMetrics.get_system_health_metrics)
```

#### `resultado.entidades_nomeadas` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:163 (em NLPEnhancedAnalyzer.analyze_text)
```

#### `resultado.palavras_chave` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:164 (em NLPEnhancedAnalyzer.analyze_text)
```

#### `resultado.sentimento` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:165 (em NLPEnhancedAnalyzer.analyze_text)
```

#### `resultado.tokens_limpos` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:167 (em NLPEnhancedAnalyzer.analyze_text)
```

#### `resultado.correcoes_sugeridas` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:168 (em NLPEnhancedAnalyzer.analyze_text)
```

#### `resultado.similaridades` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:169 (em NLPEnhancedAnalyzer.analyze_text)
```

#### `resultado.tempo_verbal` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:170 (em NLPEnhancedAnalyzer.analyze_text)
```

#### `resultado.split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:303 (em DevCommands._processar_com_claude)
```

### 🔍 Objeto: `resultado_batch`

#### `resultado_batch.get` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:435 (em SemanticEnricher._calcular_estatisticas_batch)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:458 (em SemanticEnricher._calcular_estatisticas_batch)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:459 (em SemanticEnricher._calcular_estatisticas_batch)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:475 (em SemanticEnricher._gerar_sugestoes_batch)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:478 (em SemanticEnricher._gerar_sugestoes_batch)
```

### 🔍 Objeto: `resultado_etapa`

#### `resultado_etapa.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:203 (em WorkflowOrchestrator._executar_etapas_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:204 (em WorkflowOrchestrator._executar_etapas_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:206 (em WorkflowOrchestrator._executar_etapas_workflow)
```

### 🔍 Objeto: `resultado_grupo`

#### `resultado_grupo.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:533 (em ContextLoader._carregar_todos_clientes_sistema)
```

### 🔍 Objeto: `resultado_validacao`

#### `resultado_validacao.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:434 (em SemanticValidator._gerar_recomendacoes_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:435 (em SemanticValidator._gerar_recomendacoes_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:443 (em SemanticValidator._gerar_recomendacoes_mapeamento)
```

### 🔍 Objeto: `resultados`

#### `resultados.append` (62 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:107 (em ValidadorSistemaCompleto._testar_estrutura_diretorios)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:113 (em ValidadorSistemaCompleto._testar_estrutura_diretorios)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:119 (em ValidadorSistemaCompleto._testar_estrutura_diretorios)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:145 (em ValidadorSistemaCompleto._testar_imports_principais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:151 (em ValidadorSistemaCompleto._testar_imports_principais)
  ... e mais 57 ocorrências
```

#### `resultados.sort` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:123 (em BaseMapper.buscar_mapeamento_fuzzy)
```

### 🔍 Objeto: `resultados_categoria`

#### `resultados_categoria.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:192 (em module.main)
```

### 🔍 Objeto: `resultados_detalhados`

#### `resultados_detalhados.items` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:227 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:238 (em module.main)
```

### 🔍 Objeto: `resultados_fuzzy`

#### `resultados_fuzzy.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:122 (em MapperManager._buscar_fuzzy_integrado)
```

### 🔍 Objeto: `results`

#### `results.get` (15 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:332 (em AnalyzerManager._calculate_combined_confidence)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:359 (em AnalyzerManager._generate_combined_insights)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:360 (em AnalyzerManager._generate_combined_insights)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:372 (em AnalyzerManager._generate_combined_insights)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:375 (em AnalyzerManager._generate_combined_insights)
  ... e mais 10 ocorrências
```

#### `results.append` (13 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:163 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:175 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:183 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:178 (em ProductionSimulator.run_production_tests)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:443 (em IntelligenceCoordinator._execute_parallel_intelligence)
  ... e mais 8 ocorrências
```

#### `results.get().get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:749 (em IntelligenceCoordinator._validate_intelligence_quality)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:752 (em IntelligenceCoordinator._validate_intelligence_quality)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:240 (em CursorMonitor.display_status)
```

#### `results.values` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:137 (em StandaloneIntegration.initialize_system)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:220 (em ProcessorManager.reload_processors)
```

#### `results.get().items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:218 (em CursorMonitor.display_status)
```

#### `results.get().get().get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:240 (em CursorMonitor.display_status)
```

### 🔍 Objeto: `root_path`

#### `root_path.parts` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:43 (em module.contar_arquivos_detalhado)
```

#### `root_path.parent` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:51 (em module.contar_arquivos_detalhado)
```

#### `root_path.name` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:52 (em module.contar_arquivos_detalhado)
```

#### `root_path.relative_to().parts` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:55 (em module.contar_arquivos_detalhado)
```

#### `root_path.relative_to` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:55 (em module.contar_arquivos_detalhado)
```

### 🔍 Objeto: `route`

#### `route.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:359 (em CodeScanner._analyze_route_methods)
```

### 🔍 Objeto: `route_info`

#### `route_info.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:182 (em ProjectScanner._generate_scan_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:245 (em ProjectScanner._calculate_quality_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:288 (em ProjectScanner._generate_recommendations)
```

#### `route_info.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:306 (em CodeScanner._extract_routes_from_lines)
```

### 🔍 Objeto: `routes`

#### `routes.get_blueprint` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:644 (em module.create_integration_routes)
```

#### `routes.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:77 (em CodeScanner.discover_all_routes)
```

#### `routes.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:308 (em CodeScanner._extract_routes_from_lines)
```

### 🔍 Objeto: `routes_file`

#### `routes_file.exists` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:76 (em CodeScanner.discover_all_routes)
```

### 🔍 Objeto: `row`

#### `row.created_at` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:165 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:166 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:167 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.confidence` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:129 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:130 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.domain` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:135 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:136 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.complexity` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:139 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:140 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.processing_time` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:144 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:145 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.model_used` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:150 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:151 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.tokens_used` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:155 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:156 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.success` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:161 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:161 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.session_count` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:283 (em PerformanceAnalyzer.analyze_user_behavior)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:288 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.active_days` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:283 (em PerformanceAnalyzer.analyze_user_behavior)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:293 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.avg_confidence` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:289 (em PerformanceAnalyzer.analyze_user_behavior)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:369 (em PerformanceAnalyzer.detect_anomalies)
```

#### `row.first_session` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:291 (em PerformanceAnalyzer.analyze_user_behavior)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:291 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.last_session` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:292 (em PerformanceAnalyzer.analyze_user_behavior)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:292 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.created_at.hour` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:166 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.created_at.date().isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:167 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.created_at.date` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:167 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.user_id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:287 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.domains_used` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:290 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.first_session.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:291 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.last_session.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:292 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.date.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:367 (em PerformanceAnalyzer.detect_anomalies)
```

#### `row.date` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:367 (em PerformanceAnalyzer.detect_anomalies)
```

#### `row.daily_sessions` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:368 (em PerformanceAnalyzer.detect_anomalies)
```

#### `row.avg_processing_time` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:370 (em PerformanceAnalyzer.detect_anomalies)
```

#### `row.failures` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:371 (em PerformanceAnalyzer.detect_anomalies)
```

### 🔍 Objeto: `rule_config`

#### `rule_config.get` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:336 (em BaseValidationUtils._validate_single_rule)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:337 (em BaseValidationUtils._validate_single_rule)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:346 (em BaseValidationUtils._validate_single_rule)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:357 (em BaseValidationUtils._validate_single_rule)
```

### 🔍 Objeto: `rule_result`

#### `rule_result.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:312 (em BaseValidationUtils.validate_business_rules)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:315 (em BaseValidationUtils.validate_business_rules)
```

### 🔍 Objeto: `rules`

#### `rules.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:305 (em BaseValidationUtils.validate_business_rules)
```

### 🔍 Objeto: `runner`

#### `runner.run` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:258 (em module.run_pre_commit_tests)
```

### 🔍 Objeto: `s`

#### `s.user_profiles` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:238 (em SuggestionsEngine._generate_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:238 (em SuggestionsEngine._generate_suggestions)
```

#### `s.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:137 (em SuggestionsManager.generate_suggestions)
```

#### `s.to_dict` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:272 (em SuggestionsEngine._generate_suggestions)
```

### 🔍 Objeto: `sa`

#### `sa.text` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:71 (em DatabaseLoader._initialize_connection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:112 (em DatabaseLoader.load_data)
```

### 🔍 Objeto: `sanitized`

#### `sanitized.strip` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/security/security_guard.py:295 (em SecurityGuard.sanitize_input)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_classes.py:274 (em BaseProcessor._sanitize_input)
```

### 🔍 Objeto: `saude`

#### `saude.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:312 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
```

### 🔍 Objeto: `scanner`

#### `scanner.esta_disponivel` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:71 (em ScannersCache.get_readme_scanner)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:97 (em ScannersCache.get_database_scanner)
```

#### `scanner.scan_complete_database` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/__init__.py:161 (em module.scan_database)
```

### 🔍 Objeto: `scanner_status`

#### `scanner_status.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:294 (em ScanningManager.executar_diagnostico_completo)
```

### 🔍 Objeto: `scenarios`

#### `scenarios.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:245 (em ProductionSimulator.test_specific_scenario)
```

### 🔍 Objeto: `schema_mapping`

#### `schema_mapping.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:232 (em DataProcessor.transform_schema)
```

#### `schema_mapping.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:233 (em DataProcessor.transform_schema)
```

#### `schema_mapping.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:556 (em DataProcessor._transform_dict_schema)
```

### 🔍 Objeto: `scores`

#### `scores.items` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:439 (em OrchestratorManager._detect_appropriate_orchestrator)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:262 (em ContextProcessor._detectar_dominio)
```

#### `scores.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:193 (em ExcelOrchestrator._detectar_tipo_excel)
```

#### `scores.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:259 (em ContextProcessor._detectar_dominio)
```

### 🔍 Objeto: `scores_positivos`

#### `scores_positivos.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:132 (em IntentionAnalyzer._detectar_intencoes_multiplas)
```

### 🔍 Objeto: `section_data`

#### `section_data.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:648 (em SystemConfig._validate_profile_config)
```

### 🔍 Objeto: `self`

#### `self.logger.error` (196 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:184 (em AnalyzerManager._initialize_components)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:295 (em AnalyzerManager.analyze_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:403 (em AnalyzerManager.initialize_diagnostics_analyzer)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:435 (em AnalyzerManager.analyze_diagnostics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:453 (em AnalyzerManager.analyze_intention)
  ... e mais 191 ocorrências
```

#### `self.logger.info` (97 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:181 (em AnalyzerManager._initialize_components)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:290 (em AnalyzerManager.analyze_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:399 (em AnalyzerManager.initialize_diagnostics_analyzer)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:30 (em SemanticAnalyzer.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:28 (em StructuralAnalyzer.__init__)
  ... e mais 92 ocorrências
```

#### `self.logger.warning` (81 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:129 (em AnalyzerManager._initialize_components)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:137 (em AnalyzerManager._initialize_components)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:145 (em AnalyzerManager._initialize_components)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:153 (em AnalyzerManager._initialize_components)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:161 (em AnalyzerManager._initialize_components)
  ... e mais 76 ocorrências
```

#### `self.logger.debug` (56 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:127 (em AnalyzerManager._initialize_components)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:135 (em AnalyzerManager._initialize_components)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:143 (em AnalyzerManager._initialize_components)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:151 (em AnalyzerManager._initialize_components)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:159 (em AnalyzerManager._initialize_components)
  ... e mais 51 ocorrências
```

#### `self.components.get` (42 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:215 (em AnalyzerManager.analyze_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:226 (em AnalyzerManager.analyze_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:237 (em AnalyzerManager.analyze_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:250 (em AnalyzerManager.analyze_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:261 (em AnalyzerManager.analyze_query)
  ... e mais 37 ocorrências
```

#### `self.agent_type.value` (23 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:32 (em BaseSpecialistAgent.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:67 (em BaseSpecialistAgent.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:70 (em BaseSpecialistAgent.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:77 (em BaseSpecialistAgent.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:82 (em BaseSpecialistAgent.top-level)
  ... e mais 18 ocorrências
```

#### `self.db.session` (20 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:62 (em PerformanceAnalyzer._ensure_table_exists)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:105 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:269 (em PerformanceAnalyzer.analyze_user_behavior)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:354 (em PerformanceAnalyzer.detect_anomalies)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:235 (em ExternalAPIIntegration._get_integration_manager)
  ... e mais 15 ocorrências
```

#### `self.db.session.execute` (12 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:62 (em PerformanceAnalyzer._ensure_table_exists)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:105 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:269 (em PerformanceAnalyzer.analyze_user_behavior)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:354 (em PerformanceAnalyzer.detect_anomalies)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:61 (em SessionMemory._ensure_table_exists)
  ... e mais 7 ocorrências
```

#### `self.integration_manager.process_unified_query` (9 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:81 (em ProductionSimulator.simulate_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:104 (em ProductionSimulator.run_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:179 (em SmartBaseAgent.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:47 (em TestLoopPrevention.test_direct_loop_detection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:68 (em TestLoopPrevention.test_direct_loop_detection)
  ... e mais 4 ocorrências
```

#### `self.__class__.__name__` (9 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:50 (em BaseCommand.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:197 (em BaseMapper.__str__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_classes.py:169 (em BaseOrchestrator.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_classes.py:173 (em BaseOrchestrator.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_classes.py:187 (em BaseOrchestrator.get_status)
  ... e mais 4 ocorrências
```

#### `self.db_engine.connect` (9 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:234 (em DatabaseConnection.test_connection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:122 (em DataAnalyzer._analisar_estatisticas_basicas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:168 (em DataAnalyzer._obter_exemplos_valores)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:200 (em DataAnalyzer._analisar_distribuicao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:241 (em DataAnalyzer._analisar_comprimento_valores)
  ... e mais 4 ocorrências
```

#### `self.security_guard.validate_user_access` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:426 (em MainOrchestrator._validate_workflow_security)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:442 (em MainOrchestrator._validate_workflow_security)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:448 (em MainOrchestrator._validate_workflow_security)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:342 (em OrchestratorManager._validate_operation_security)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:358 (em OrchestratorManager._validate_operation_security)
  ... e mais 3 ocorrências
```

#### `self.metadata_reader.obter_campos_tabela` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:103 (em DatabaseManager.obter_campos_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:83 (em AutoMapper.gerar_mapeamento_automatico)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:85 (em FieldSearcher.buscar_campos_por_tipo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:163 (em FieldSearcher.buscar_campos_por_nome)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:302 (em FieldSearcher.buscar_campos_por_caracteristica)
  ... e mais 3 ocorrências
```

#### `self.inspector.get_table_names` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:79 (em FieldSearcher.buscar_campos_por_tipo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:159 (em FieldSearcher.buscar_campos_por_nome)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:299 (em FieldSearcher.buscar_campos_por_caracteristica)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:344 (em FieldSearcher.buscar_campos_por_tamanho)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:406 (em FieldSearcher.buscar_campos_similares)
  ... e mais 3 ocorrências
```

#### `self.model.data_criacao` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:61 (em AgendamentosLoader._build_agendamentos_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:64 (em EmbarquesLoader._build_embarques_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:86 (em EmbarquesLoader._build_embarques_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:67 (em FretesLoader._build_fretes_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:90 (em FretesLoader._build_fretes_query)
  ... e mais 2 ocorrências
```

#### `self.validators.get` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:97 (em ValidatorManager.validate_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:127 (em ValidatorManager.validate_data_structure)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:159 (em ValidatorManager.validate_critical_rules)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:191 (em ValidatorManager.validate_agent_responses)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:252 (em ValidatorManager.validate_structural_integrity)
  ... e mais 2 ocorrências
```

#### `self.components.items` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:606 (em AnalyzerManager.get_best_analyzer)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:634 (em AnalyzerManager.health_check)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tools/tools_manager.py:167 (em ToolsManager.health_check)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/data_manager.py:354 (em DataManager.get_best_loader)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/data_manager.py:383 (em DataManager.health_check)
  ... e mais 1 ocorrências
```

#### `self.registry.get_processor` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:88 (em ProcessorCoordinator._execute_chain_step)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:183 (em ProcessorCoordinator._execute_single_processor)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:39 (em ProcessorManager.process_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:58 (em ProcessorManager.process_response)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:75 (em ProcessorManager.process_semantic_loop)
  ... e mais 1 ocorrências
```

#### `self.model.query` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:53 (em AgendamentosLoader._build_agendamentos_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:54 (em EmbarquesLoader._build_embarques_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:53 (em EntregasLoader._build_entregas_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:53 (em FaturamentoLoader._build_faturamento_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:56 (em FretesLoader._build_fretes_query)
  ... e mais 1 ocorrências
```

#### `self.connection.get_inspector` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:61 (em DatabaseManager.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:63 (em DatabaseManager.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:65 (em DatabaseManager.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:76 (em DatabaseManager.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:351 (em DatabaseManager.recarregar_conexao)
  ... e mais 1 ocorrências
```

#### `self.project_scanner.file_scanner` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:110 (em ScanningManager.read_file_content)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:114 (em ScanningManager.list_directory_contents)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:119 (em ScanningManager.search_in_files)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:231 (em ScanningManager.discover_all_templates)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:253 (em ScanningManager.get_modulos_especializados)
  ... e mais 1 ocorrências
```

#### `self.components.keys` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:622 (em AnalyzerManager.get_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tools/tools_manager.py:155 (em ToolsManager.get_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_classes.py:190 (em BaseOrchestrator.get_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/data_manager.py:370 (em DataManager.get_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/utils_manager.py:256 (em UtilsManager.get_status)
```

#### `self.db.session.execute().fetchall` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:105 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:269 (em PerformanceAnalyzer.analyze_user_behavior)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:354 (em PerformanceAnalyzer.detect_anomalies)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:183 (em SessionMemory.get_sessions_by_user)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:240 (em SessionMemory.search_sessions)
```

#### `self.system_config.get_config` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/advanced_config.py:69 (em AdvancedConfig.get_temperature)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/advanced_config.py:79 (em AdvancedConfig.get_claude_params)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/advanced_config.py:80 (em AdvancedConfig.get_claude_params)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/advanced_config.py:82 (em AdvancedConfig.get_claude_params)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/advanced_config.py:83 (em AdvancedConfig.get_claude_params)
```

#### `self.redis_cache.disponivel` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:78 (em ConversationContext.add_message)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:112 (em ConversationContext.get_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:248 (em ConversationContext.clear_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:302 (em ConversationContext.get_context_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:222 (em SuggestionsEngine._is_redis_available)
```

#### `self.context_memory.store_context` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:78 (em ConversationManager.start_conversation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:255 (em ConversationManager.end_conversation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:51 (em ConversationMemory.start_conversation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:72 (em ConversationMemory.end_conversation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:53 (em MemoryManager.store_conversation_context)
```

#### `self.context_memory.add_message` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:128 (em ConversationManager.add_user_message)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:175 (em ConversationManager.add_assistant_message)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:99 (em ConversationMemory.add_user_message)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:125 (em ConversationMemory.add_assistant_message)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:152 (em MemoryManager.add_conversation_message)
```

#### `self.context_memory.retrieve_context` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:205 (em ConversationManager.get_conversation_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:250 (em ConversationManager.end_conversation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:68 (em ConversationMemory.end_conversation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:142 (em ConversationMemory.get_conversation_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:69 (em MemoryManager.retrieve_conversation_context)
```

#### `self.ai_components.items` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:426 (em IntelligenceCoordinator._execute_parallel_intelligence)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:455 (em IntelligenceCoordinator._execute_sequential_intelligence)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:477 (em IntelligenceCoordinator._execute_hybrid_intelligence)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:482 (em IntelligenceCoordinator._execute_hybrid_intelligence)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:607 (em IntelligenceCoordinator._select_best_component)
```

#### `self.logger_estruturado.error` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/embarques_agent.py:63 (em EmbarquesAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:124 (em EntregasAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/financeiro_agent.py:62 (em FinanceiroAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/fretes_agent.py:63 (em FretesAgent._resumir_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/pedidos_agent.py:63 (em PedidosAgent._resumir_dados_reais)
```

#### `self.user_profiles.get` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:118 (em AdaptiveLearning.get_personalized_recommendations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:165 (em AdaptiveLearning.adapt_response)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:222 (em AdaptiveLearning.update_learning_from_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:255 (em AdaptiveLearning.get_user_profile)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:426 (em AdaptiveLearning._calculate_learning_confidence)
```

#### `self.model.data_embarque` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:61 (em EmbarquesLoader._build_embarques_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:63 (em EmbarquesLoader._build_embarques_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:60 (em EntregasLoader._build_entregas_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:78 (em EntregasLoader._build_entregas_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:68 (em FretesLoader._build_fretes_query)
```

#### `self.project_scanner.structure_scanner` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:215 (em ScanningManager.discover_project_structure)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:219 (em ScanningManager.discover_all_models)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:251 (em ScanningManager.get_modulos_especializados)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:331 (em ScanningManager._discover_project_structure)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:335 (em ScanningManager._discover_all_models)
```

#### `self.project_scanner.code_scanner` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:223 (em ScanningManager.discover_all_forms)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:227 (em ScanningManager.discover_all_routes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:252 (em ScanningManager.get_modulos_especializados)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:339 (em ScanningManager._discover_all_forms)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:343 (em ScanningManager._discover_all_routes)
```

#### `self.defined_vars.add` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:45 (em VariableTracker.visit_FunctionDef)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:50 (em VariableTracker.visit_ClassDef)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:63 (em VariableTracker.visit_Assign)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:74 (em VariableTracker.visit_Name)
```

#### `self.orchestrator_manager.process_query` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:82 (em ProductionSimulator.simulate_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/integration_manager.py:298 (em IntegrationManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:48 (em TestLoopPrevention.test_direct_loop_detection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:133 (em TestLoopPrevention.test_circular_reference_detection)
```

#### `self.orchestrator.mappers` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:48 (em DiagnosticsAnalyzer.gerar_estatisticas_completas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:58 (em DiagnosticsAnalyzer.gerar_estatisticas_completas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:104 (em DiagnosticsAnalyzer.diagnosticar_qualidade)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:301 (em SemanticValidator._validar_campos_modelo_tabela)
```

#### `self.db.session.execute().fetchone` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:62 (em PerformanceAnalyzer._ensure_table_exists)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:61 (em SessionMemory._ensure_table_exists)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:146 (em SessionMemory.get_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:314 (em SessionMemory.get_session_stats)
```

#### `self.client.messages.create` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:288 (em DevCommands._processar_com_claude)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:123 (em ClaudeAPIClient.send_message)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:209 (em ResponseProcessor._gerar_resposta_inicial)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:354 (em ResponseProcessor._melhorar_resposta)
```

#### `self.client.messages` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:288 (em DevCommands._processar_com_claude)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:123 (em ClaudeAPIClient.send_message)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:209 (em ResponseProcessor._gerar_resposta_inicial)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/response_processor.py:354 (em ResponseProcessor._melhorar_resposta)
```

#### `self.esqueletos.keys` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:368 (em ExcelOrchestrator._fallback_tipo_indisponivel)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:377 (em ExcelOrchestrator._fallback_tipo_indisponivel)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:385 (em ExcelOrchestrator._fallback_tipo_indisponivel)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:410 (em ExcelOrchestrator.get_status_esqueletos)
```

#### `self.model.status` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:77 (em AgendamentosLoader._build_agendamentos_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:80 (em EmbarquesLoader._build_embarques_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:83 (em EmbarquesLoader._build_embarques_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:80 (em FretesLoader._build_fretes_query)
```

#### `self.db.session.rollback` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:122 (em SessionMemory.store_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:126 (em SessionMemory.store_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:284 (em SessionMemory.cleanup_old_sessions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:373 (em SessionMemory.update_session_metadata)
```

#### `self.status.total_requests` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:267 (em CursorMonitor.display_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:269 (em CursorMonitor.display_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:269 (em CursorMonitor.display_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:315 (em CursorMonitor.top-level)
```

#### `self.security_guard.validate_input` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:431 (em MainOrchestrator._validate_workflow_security)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:454 (em MainOrchestrator._validate_workflow_security)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:347 (em OrchestratorManager._validate_operation_security)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:837 (em SessionOrchestrator._validate_session_security)
```

#### `self.session_memory.update_session_metadata` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:324 (em SessionOrchestrator.initialize_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:396 (em SessionOrchestrator.execute_session_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:568 (em SessionOrchestrator.complete_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:612 (em SessionOrchestrator.terminate_session)
```

#### `self.connection.get_engine` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:62 (em DatabaseManager.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:74 (em DatabaseManager.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:352 (em DatabaseManager.recarregar_conexao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:366 (em DatabaseManager.recarregar_conexao)
```

#### `self.connection.is_connected` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:197 (em DatabaseManager.esta_disponivel)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:208 (em DatabaseManager.obter_estatisticas_gerais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:374 (em DatabaseManager.recarregar_conexao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:389 (em DatabaseManager.obter_info_modulos)
```

#### `self.defined_methods.add` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:51 (em MethodCallVisitor.visit_ClassDef)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:59 (em MethodCallVisitor.visit_FunctionDef)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:61 (em MethodCallVisitor.visit_FunctionDef)
```

#### `self.orchestrator.mappers.items` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:58 (em DiagnosticsAnalyzer.gerar_estatisticas_completas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:104 (em DiagnosticsAnalyzer.diagnosticar_qualidade)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:301 (em SemanticValidator._validar_campos_modelo_tabela)
```

#### `self.orchestrator.obter_readers` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:203 (em DiagnosticsAnalyzer.gerar_relatorio_enriquecido)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:70 (em SemanticEnricher.enriquecer_mapeamento_com_readers)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:210 (em SemanticValidator.validar_consistencia_readme_banco)
```

#### `self.thread_pool.submit` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:205 (em IntelligenceCoordinator.coordinate_multi_ai_synthesis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:428 (em IntelligenceCoordinator._execute_parallel_intelligence)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:504 (em IntelligenceCoordinator._execute_hybrid_intelligence)
```

#### `self.active_chains.values` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:276 (em ProcessorCoordinator.get_coordinator_stats)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:277 (em ProcessorCoordinator.get_coordinator_stats)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:278 (em ProcessorCoordinator.get_coordinator_stats)
```

#### `self.knowledge_base.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:165 (em BaseSpecialistAgent._calculate_confidence)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:176 (em BaseSpecialistAgent.get_agent_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:177 (em BaseSpecialistAgent.get_agent_info)
```

#### `self.web_adapter.get_module` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:426 (em WebFlaskRoutes.clear_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:577 (em WebFlaskRoutes._record_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:593 (em WebFlaskRoutes._record_feedback)
```

#### `self.model.data_criacao.desc` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:86 (em EmbarquesLoader._build_embarques_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:90 (em FretesLoader._build_fretes_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:75 (em PedidosLoader._build_pedidos_query)
```

#### `self.model.cliente.ilike` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:68 (em EntregasLoader._build_entregas_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:75 (em FretesLoader._build_fretes_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:63 (em PedidosLoader._build_pedidos_query)
```

#### `self.model.cliente` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:68 (em EntregasLoader._build_entregas_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:75 (em FretesLoader._build_fretes_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:63 (em PedidosLoader._build_pedidos_query)
```

#### `self.mappers.items` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:64 (em MapperManager.analisar_consulta_semantica)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:115 (em MapperManager._buscar_fuzzy_integrado)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:242 (em MapperManager.obter_estatisticas_mappers)
```

#### `self.mapeamentos.items` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:66 (em BaseMapper.buscar_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:104 (em BaseMapper.buscar_mapeamento_fuzzy)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:176 (em BaseMapper.validar_mapeamentos)
```

#### `self.mapeamentos.values` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:143 (em BaseMapper.listar_termos_naturais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:155 (em BaseMapper.gerar_estatisticas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:156 (em BaseMapper.gerar_estatisticas)
```

#### `self.local_cache.items` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:220 (em ContextMemory.get_active_sessions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:243 (em ContextMemory.cleanup_expired_contexts)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:348 (em SystemMemory.cleanup_expired_data)
```

#### `self.db.session.commit` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:116 (em SessionMemory.store_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:276 (em SessionMemory.cleanup_old_sessions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:362 (em SessionMemory.update_session_metadata)
```

#### `self.registry.list_processors` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:170 (em ProcessorManager.get_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:210 (em ProcessorManager.reload_processors)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:241 (em ProcessorManager.__str__)
```

#### `self.app_path.iterdir` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:50 (em CodeScanner.discover_all_forms)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:73 (em CodeScanner.discover_all_routes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:152 (em StructureScanner._discover_models_via_files)
```

#### `self.tabelas_cache.clear` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:331 (em DatabaseManager.limpar_cache)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:44 (em MetadataReader.set_inspector)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:312 (em MetadataReader.limpar_cache)
```

#### `self.discovered_routes.values` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:183 (em ProjectScanner._generate_scan_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:246 (em ProjectScanner._calculate_quality_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:289 (em ProjectScanner._generate_recommendations)
```

#### `self.project_scanner.get_scanner_status` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:240 (em ScanningManager.get_scanner_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:266 (em ScanningManager.executar_diagnostico_completo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:267 (em ScanningManager.executar_diagnostico_completo)
```

#### `self.mapping_cache.clear` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:49 (em AutoMapper.set_metadata_reader)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:59 (em AutoMapper.set_data_analyzer)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:573 (em AutoMapper.limpar_cache)
```

#### `self.search_cache.clear` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:46 (em FieldSearcher.set_inspector)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:56 (em FieldSearcher.set_metadata_reader)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:524 (em FieldSearcher.limpar_cache)
```

#### `self.inspector.get_foreign_keys` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:220 (em MetadataReader._obter_constraints_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:70 (em RelationshipMapper.obter_relacionamentos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:121 (em RelationshipMapper._buscar_relacionamentos_entrada)
```

#### `self.mock_models.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:164 (em FlaskFallback.get_model)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:168 (em FlaskFallback.get_model)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:170 (em FlaskFallback.get_model)
```

#### `self.backups_created.append` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:109 (em ImportFixer._fix_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:255 (em ImportFixer._add_get_function)
```

#### `self.duplicates.items` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:112 (em ClassDuplicateFinder.analyze_duplicates)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:220 (em ClassDuplicateFinder.generate_report)
```

#### `self.root_path.absolute` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:173 (em ClassDuplicateFinder.generate_report)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:199 (em UninitializedVariableFinder.generate_report)
```

#### `self.imported_names.add` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:31 (em MethodCallVisitor.visit_Import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:38 (em MethodCallVisitor.visit_ImportFrom)
```

#### `self.imports.add` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:30 (em VariableTracker.visit_Import)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:37 (em VariableTracker.visit_ImportFrom)
```

#### `self.uninitialized_vars.items` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:218 (em UninitializedVariableFinder.generate_report)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:249 (em UninitializedVariableFinder.generate_report)
```

#### `self.orchestrator.verificar_saude_sistema` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:229 (em DiagnosticsAnalyzer.gerar_relatorio_enriquecido)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:333 (em DiagnosticsAnalyzer.gerar_relatorio_resumido)
```

#### `self.output_dir.mkdir` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:55 (em BaseCommand.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:63 (em BaseCommand.__init__)
```

#### `self.prioridades.keys` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:199 (em ExcelOrchestrator._detectar_tipo_excel)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:211 (em ExcelOrchestrator._tentar_fallback_esqueletos)
```

#### `self.status.items` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:141 (em CommandsRegistry.get_available_commands)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:148 (em CommandsRegistry.get_status_report)
```

#### `self.system_config.active_profile` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/advanced_config.py:95 (em AdvancedConfig.get_config)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/advanced_config.py:103 (em AdvancedConfig.get_config)
```

#### `self.profiles.keys` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:191 (em SystemConfig.switch_profile)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:423 (em SystemConfig.get_system_status)
```

#### `self.default_configurations.copy` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:531 (em SystemConfig._load_initial_configurations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:552 (em SystemConfig._load_profile_config)
```

#### `self.change_history.append` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:684 (em SystemConfig._record_config_change)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:699 (em SystemConfig._record_profile_switch)
```

#### `self.redis_cache.set` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:80 (em ConversationContext.add_message)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:201 (em SuggestionsEngine.get_intelligent_suggestions)
```

#### `self.redis_cache.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:114 (em ConversationContext.get_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:188 (em SuggestionsEngine.get_intelligent_suggestions)
```

#### `self.conversation_memory.start_conversation` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:74 (em ConversationManager.start_conversation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:186 (em MemoryManager.start_conversation)
```

#### `self.context_memory.get_conversation_history` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:225 (em ConversationManager.get_conversation_history)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:169 (em MemoryManager.get_conversation_history)
```

#### `self.conversation_memory.end_conversation` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:246 (em ConversationManager.end_conversation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:202 (em MemoryManager.end_conversation)
```

#### `self.active_conversations.items` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:278 (em ConversationManager.get_active_conversations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:309 (em ConversationManager.cleanup_expired_conversations)
```

#### `self.context_memory.cleanup_expired_contexts` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:321 (em ConversationManager.cleanup_expired_conversations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:279 (em MemoryManager.cleanup_expired_data)
```

#### `self.conversation_memory.get_conversation_summary` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:344 (em ConversationManager.get_conversation_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:218 (em MemoryManager.get_conversation_summary)
```

#### `self.coordination_metrics.copy` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:363 (em IntelligenceCoordinator.get_intelligence_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:893 (em IntelligenceCoordinator._analyze_current_performance)
```

#### `self.config.copy` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:364 (em IntelligenceCoordinator.get_intelligence_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/context_provider.py:380 (em ContextProvider._enrich_context)
```

#### `self.active_chains.items` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:249 (em ProcessorCoordinator.get_active_chains)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:258 (em ProcessorCoordinator.cleanup_completed_chains)
```

#### `self.registry.get_registry_stats` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:279 (em ProcessorCoordinator.get_coordinator_stats)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:167 (em ProcessorManager.get_status)
```

#### `self.agent_types.keys` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:116 (em SpecialistCoordinator.get_all_agents)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:120 (em SpecialistCoordinator.get_available_domains)
```

#### `self.agent_type.value.title` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:32 (em BaseSpecialistAgent.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:215 (em SmartBaseAgent.top-level)
```

#### `self.integration_manager.get_system_status` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:73 (em SmartBaseAgent._conectar_integration_manager)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:429 (em ExternalAPIIntegration.get_system_status)
```

#### `self.orchestrator.obter_mapper` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:196 (em SemanticEnricher._obter_mapeamento_atual)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:171 (em SemanticValidator._validacoes_gerais)
```

#### `self.claude_client.validate_connection` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:215 (em ExternalAPIIntegration._initialize_clients)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:394 (em ExternalAPIIntegration._validate_claude_connection)
```

#### `self.claude_client.send_message` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:384 (em ExternalAPIIntegration.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/query_processor.py:51 (em QueryProcessor._process_with_claude)
```

#### `self.config.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:45 (em StandaloneContextManager.get_config)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:227 (em StandaloneIntegration.get_status)
```

#### `self.web_adapter.get_system_status` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:450 (em WebFlaskRoutes.health_check)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:483 (em WebFlaskRoutes.system_status)
```

#### `self.web_adapter._run_async` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:580 (em WebFlaskRoutes._record_feedback)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:595 (em WebFlaskRoutes._record_feedback)
```

#### `self.knowledge_memory.aprender_mapeamento_cliente` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:113 (em LearningCore.aprender_com_interacao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:119 (em MemoryManager.learn_client_mapping)
```

#### `self.knowledge_memory.descobrir_grupo_empresarial` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:120 (em LearningCore.aprender_com_interacao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:135 (em MemoryManager.discover_business_group)
```

#### `self.knowledge_memory.obter_estatisticas_aprendizado` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:235 (em LearningCore.obter_status_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:258 (em MemoryManager.get_system_overview)
```

#### `self.learning_core.aprender_com_interacao` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/lifelong_learning.py:65 (em LifelongLearningSystem.aprender_com_interacao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:433 (em SessionOrchestrator._execute_learning_workflow)
```

#### `self.learning_core.aplicar_conhecimento` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/lifelong_learning.py:81 (em LifelongLearningSystem.aplicar_conhecimento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:519 (em SessionOrchestrator.apply_learned_knowledge)
```

#### `self.config.username` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:60 (em DatabaseLoader._initialize_connection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:206 (em DatabaseLoader.get_connection_info)
```

#### `self.config.host` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:60 (em DatabaseLoader._initialize_connection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:203 (em DatabaseLoader.get_connection_info)
```

#### `self.config.port` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:60 (em DatabaseLoader._initialize_connection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:204 (em DatabaseLoader.get_connection_info)
```

#### `self.config.database` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:60 (em DatabaseLoader._initialize_connection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:205 (em DatabaseLoader.get_connection_info)
```

#### `self._engine.connect` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:70 (em DatabaseLoader._initialize_connection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:111 (em DatabaseLoader.load_data)
```

#### `self._loaders.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:89 (em LoaderManager._get_loader)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:275 (em LoaderManager.get_loader_status)
```

#### `self.model.data_agendamento` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:60 (em AgendamentosLoader._build_agendamentos_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:80 (em AgendamentosLoader._build_agendamentos_query)
```

#### `self.model.entregue` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:73 (em EntregasLoader._build_entregas_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:75 (em EntregasLoader._build_entregas_query)
```

#### `self.model.data_fatura` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:58 (em FaturamentoLoader._build_faturamento_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:77 (em FaturamentoLoader._build_faturamento_query)
```

#### `self.model.nome_cliente.ilike` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:63 (em FaturamentoLoader._build_faturamento_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:71 (em FaturamentoLoader._build_faturamento_query)
```

#### `self.model.nome_cliente` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:63 (em FaturamentoLoader._build_faturamento_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:71 (em FaturamentoLoader._build_faturamento_query)
```

#### `self.status.errors_count` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:268 (em CursorMonitor.display_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:269 (em CursorMonitor.display_status)
```

#### `self.status.last_error` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:271 (em CursorMonitor.display_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:272 (em CursorMonitor.display_status)
```

#### `self.coordinator_manager.coordinate_query` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:517 (em MainOrchestrator._execute_intelligent_coordination)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:564 (em MainOrchestrator._execute_natural_commands)
```

#### `self.execution_history.append` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:825 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:837 (em MainOrchestrator.top-level)
```

#### `self.orchestrators.items` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:668 (em OrchestratorManager.get_orchestrator_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:707 (em OrchestratorManager.health_check)
```

#### `self.active_sessions.pop` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:575 (em SessionOrchestrator.complete_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:619 (em SessionOrchestrator.terminate_session)
```

#### `self.active_sessions.values` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:655 (em SessionOrchestrator.get_user_sessions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:709 (em SessionOrchestrator.get_session_stats)
```

#### `self._ultimo_contexto_carregado.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:111 (em ContextProcessor._build_contexto_por_intencao)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/context_processor.py:144 (em ContextProcessor._descrever_contexto_carregado)
```

#### `self.flask_wrapper.health_check` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:182 (em ProcessorManager.health_check)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:195 (em ProcessorManager.get_detailed_health_report)
```

#### `self.registry.health_check` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:183 (em ProcessorManager.health_check)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:196 (em ProcessorManager.get_detailed_health_report)
```

#### `self.coordinator.health_check` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:184 (em ProcessorManager.health_check)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:197 (em ProcessorManager.get_detailed_health_report)
```

#### `self.data_provider.get_data_by_domain` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:152 (em ProviderManager._provide_data_only)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:282 (em ProviderManager._provide_mixed)
```

#### `self.context_provider.get_context` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:176 (em ProviderManager._provide_context_only)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:272 (em ProviderManager._provide_mixed)
```

#### `self.connection.get_session` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:75 (em DatabaseManager.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:367 (em DatabaseManager.recarregar_conexao)
```

#### `self.data_analyzer.analisar_dados_reais` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:117 (em DatabaseManager.analisar_dados_reais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:170 (em AutoMapper._mapear_campo_automatico)
```

#### `self.relationship_mapper.obter_relacionamentos` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:129 (em DatabaseManager.obter_relacionamentos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:254 (em DatabaseManager.analisar_tabela_completa)
```

#### `self.auto_mapper.gerar_mapeamento_automatico` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:188 (em DatabaseManager.gerar_mapeamento_automatico)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:258 (em DatabaseManager.analisar_tabela_completa)
```

#### `self.relationship_mapper.mapear_grafo_relacionamentos` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:219 (em DatabaseManager.obter_estatisticas_gerais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:274 (em DatabaseManager.mapear_grafo_relacionamentos)
```

#### `self.metadata_reader.is_available` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:226 (em DatabaseManager.obter_estatisticas_gerais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:394 (em DatabaseManager.obter_info_modulos)
```

#### `self.data_analyzer.is_available` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:227 (em DatabaseManager.obter_estatisticas_gerais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:398 (em DatabaseManager.obter_info_modulos)
```

#### `self.relationship_mapper.is_available` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:228 (em DatabaseManager.obter_estatisticas_gerais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:402 (em DatabaseManager.obter_info_modulos)
```

#### `self.field_searcher.is_available` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:229 (em DatabaseManager.obter_estatisticas_gerais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:406 (em DatabaseManager.obter_info_modulos)
```

#### `self.auto_mapper.is_available` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:230 (em DatabaseManager.obter_estatisticas_gerais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:410 (em DatabaseManager.obter_info_modulos)
```

#### `self.connection.connection_method` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:390 (em DatabaseManager.obter_info_modulos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:433 (em DatabaseManager.__str__)
```

#### `self.structure_scanner.discover_project_structure` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:101 (em ProjectScanner.scan_complete_project)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:152 (em ProjectScanner.scan_project_light)
```

#### `self.structure_scanner.discover_all_models` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:104 (em ProjectScanner.scan_complete_project)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:153 (em ProjectScanner.scan_project_light)
```

#### `self.file_scanner.discover_all_templates` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:113 (em ProjectScanner.scan_complete_project)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:154 (em ProjectScanner.scan_project_light)
```

#### `self.database_schema.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:185 (em ProjectScanner._generate_scan_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:298 (em ProjectScanner._generate_recommendations)
```

#### `self.discovered_models.values` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:239 (em ProjectScanner._calculate_quality_metrics)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:256 (em ProjectScanner._calculate_quality_metrics)
```

#### `self.project_scanner.scan_project_light` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:211 (em ScanningManager.scan_project_light)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:268 (em ScanningManager.executar_diagnostico_completo)
```

#### `self.project_scanner.structure_scanner.discover_project_structure` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:215 (em ScanningManager.discover_project_structure)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:331 (em ScanningManager._discover_project_structure)
```

#### `self.project_scanner.structure_scanner.discover_all_models` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:219 (em ScanningManager.discover_all_models)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:335 (em ScanningManager._discover_all_models)
```

#### `self.project_scanner.code_scanner.discover_all_forms` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:223 (em ScanningManager.discover_all_forms)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:339 (em ScanningManager._discover_all_forms)
```

#### `self.project_scanner.code_scanner.discover_all_routes` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:227 (em ScanningManager.discover_all_routes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:343 (em ScanningManager._discover_all_routes)
```

#### `self.project_scanner.file_scanner.discover_all_templates` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:231 (em ScanningManager.discover_all_templates)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:347 (em ScanningManager._discover_all_templates)
```

#### `self.analysis_cache.clear` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:46 (em DataAnalyzer.set_engine)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:471 (em DataAnalyzer.limpar_cache)
```

#### `self.relationships_cache.clear` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:45 (em RelationshipMapper.set_inspector)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:412 (em RelationshipMapper.limpar_cache)
```

#### `self.suggestion_engines.items` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:114 (em SuggestionsManager.generate_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:698 (em SuggestionsManager._optimize_engines)
```

#### `self.mock_app.config.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:267 (em FlaskFallback.get_config)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:269 (em FlaskFallback.get_config)
```

#### `self.mock_app.config` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:267 (em FlaskFallback.get_config)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:269 (em FlaskFallback.get_config)
```

#### `self._scanners_pool.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:83 (em ScannersCache.get_readme_scanner)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:109 (em ScannersCache.get_database_scanner)
```

#### `self.processors.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:163 (em ProcessorRegistry.get_processor)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:182 (em ProcessorRegistry.get_processor_info)
```

#### `self.processors.keys` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:177 (em ProcessorRegistry.list_processors)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:262 (em ProcessorRegistry.get_registry_stats)
```

#### `self.processors.values` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:260 (em ProcessorRegistry.get_registry_stats)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:261 (em ProcessorRegistry.get_registry_stats)
```

#### `self.fixes_applied.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:132 (em ImportFixer._fix_file)
```

#### `self.base_path.iterdir` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:44 (em DetectorModulosOrfaos.mapear_todas_pastas)
```

#### `self.pastas_encontradas.add` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:47 (em DetectorModulosOrfaos.mapear_todas_pastas)
```

#### `self.base_path.rglob` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:131 (em DetectorModulosOrfaos.analisar_imports_sistema)
```

#### `self.modulos_usados.add` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:180 (em DetectorModulosOrfaos._marcar_modulo_usado)
```

#### `self.classes_map.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:97 (em ClassDuplicateFinder.find_duplicates)
```

#### `self.method_calls.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:71 (em MethodCallVisitor.visit_Attribute)
```

#### `self.function_params.add` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:44 (em VariableTracker.visit_FunctionDef)
```

#### `self.class_attributes.add` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:56 (em VariableTracker.visit_ClassDef)
```

#### `self.assignments.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:64 (em VariableTracker.visit_Assign)
```

#### `self.used_vars.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:71 (em VariableTracker.visit_Name)
```

#### `self.call_stack.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:41 (em ProductionSimulator.track_call)
```

#### `self.resultados.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:386 (em TesteIntegracaoCompleta.gerar_relatorio_final)
```

#### `self.checked_modules.add` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:147 (em ImportChecker.check_import)
```

#### `self.initialization_result.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/__init__.py:97 (em ClaudeAINovo.top-level)
```

#### `self.components.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:181 (em AnalyzerManager._initialize_components)
```

#### `self._historico_performance.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:266 (em IntentionAnalyzer._salvar_performance)
```

#### `self.self_performance_history.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:44 (em MetacognitiveAnalyzer.analyze_own_performance)
```

#### `self.correcoes_comuns.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:180 (em NLPEnhancedAnalyzer._aplicar_correcoes)
```

#### `self.correcoes_comuns.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:195 (em NLPEnhancedAnalyzer._aplicar_correcoes)
```

#### `self.sinonimos.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:309 (em NLPEnhancedAnalyzer._extrair_palavras_chave)
```

#### `self.entity_patterns.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:238 (em SemanticAnalyzer._extract_entities)
```

#### `self.domain_keywords.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:249 (em SemanticAnalyzer._identify_domains)
```

#### `self.domain_keywords.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:278 (em SemanticAnalyzer._extract_keywords)
```

#### `self.command_registry.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:164 (em AutoCommandProcessor.get_command_suggestions)
```

#### `self.command_patterns.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:304 (em AutoCommandProcessor._detect_commands)
```

#### `self.command_history.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:501 (em AutoCommandProcessor._record_command_execution)
```

#### `self.cursor_mode.activated` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:85 (em CursorCommands._processar_comando_cursor_interno)
```

#### `self.cursor_mode.activate_cursor_mode` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:107 (em CursorCommands._ativar_cursor_mode)
```

#### `self.patterns_deteccao.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:180 (em ExcelOrchestrator._detectar_tipo_excel)
```

#### `self.system_config.get_profile_config` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/advanced_config.py:95 (em AdvancedConfig.get_config)
```

#### `self.profiles.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:191 (em SystemConfig.switch_profile)
```

#### `self.configurations.get().copy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:231 (em SystemConfig.reload_config)
```

#### `self.configurations.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:231 (em SystemConfig.reload_config)
```

#### `self._flatten_dict().items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:281 (em SystemConfig.validate_configuration)
```

#### `self.configurations.copy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:355 (em SystemConfig.export_config)
```

#### `self.configurations.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:424 (em SystemConfig.get_system_status)
```

#### `self.metrics.copy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:426 (em SystemConfig.get_system_status)
```

#### `self.config_watchers.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:703 (em SystemConfig._notify_config_watchers)
```

#### `self.redis_cache.delete` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:250 (em ConversationContext.clear_context)
```

#### `self.conversation_memory.add_user_message` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:132 (em ConversationManager.add_user_message)
```

#### `self.conversation_memory.add_assistant_message` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:179 (em ConversationManager.add_assistant_message)
```

#### `self.coordinators.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:304 (em CoordinatorManager.get_coordinator_status)
```

#### `self.domain_agents.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:305 (em CoordinatorManager.get_coordinator_status)
```

#### `self.ai_cache.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:910 (em IntelligenceCoordinator._optimize_ai_cache)
```

#### `self.agent_type.value.upper` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:127 (em BaseSpecialistAgent.top-level)
```

#### `self.claude_client.messages.create` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:141 (em BaseSpecialistAgent.top-level)
```

#### `self.claude_client.messages` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:141 (em BaseSpecialistAgent.top-level)
```

#### `self.logger_estruturado.info` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:243 (em SmartBaseAgent._log_consulta_estruturada)
```

#### `self.claude_client.client` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:233 (em ExternalAPIIntegration._get_integration_manager)
```

#### `self.db.engine` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:234 (em ExternalAPIIntegration._get_integration_manager)
```

#### `self.claude_client.get_current_config` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:417 (em ExternalAPIIntegration.get_system_status)
```

#### `self.config.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:226 (em StandaloneIntegration.get_status)
```

#### `self._external_api_integration.get_system_status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:234 (em StandaloneIntegration.get_status)
```

#### `self._integration_manager.get_system_status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:238 (em StandaloneIntegration.get_status)
```

#### `self.web_adapter.process_query_sync` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:348 (em WebFlaskRoutes.api_query)
```

#### `self.web_adapter.processar_consulta_sync` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:372 (em WebFlaskRoutes.api_query)
```

#### `self.web_adapter.claude_client` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:466 (em WebFlaskRoutes.health_check)
```

#### `self.web_adapter.db_engine` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:467 (em WebFlaskRoutes.health_check)
```

#### `self.web_adapter.get_available_modules` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:488 (em WebFlaskRoutes.system_status)
```

#### `self.web_adapter.initialization_result` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:489 (em WebFlaskRoutes.system_status)
```

#### `self.interaction_history.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:282 (em AdaptiveLearning._record_interaction)
```

#### `self.feedback_patterns.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:191 (em FeedbackProcessor.analisar_feedback)
```

#### `self.sentiment_patterns.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:321 (em FeedbackProcessor._detectar_sentimento)
```

#### `self.feedback_storage.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:98 (em HumanInLoopLearning.capture_feedback)
```

#### `self.improvement_queue.insert` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:130 (em HumanInLoopLearning._process_critical_feedback)
```

#### `self.learning_patterns.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:215 (em HumanInLoopLearning._create_learning_pattern)
```

#### `self.improvement_queue.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:237 (em HumanInLoopLearning._add_to_improvement_queue)
```

#### `self.pattern_learner.extrair_e_salvar_padroes` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:108 (em LearningCore.aprender_com_interacao)
```

#### `self.feedback_processor.processar_feedback_completo` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:126 (em LearningCore.aprender_com_interacao)
```

#### `self.pattern_learner.buscar_padroes_aplicaveis` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:175 (em LearningCore.aplicar_conhecimento)
```

#### `self.knowledge_memory.buscar_grupos_aplicaveis` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:179 (em LearningCore.aplicar_conhecimento)
```

#### `self.knowledge_memory.buscar_mapeamentos_aplicaveis` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/learning_core.py:180 (em LearningCore.aplicar_conhecimento)
```

#### `self.learning_core.apply_learning` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/lifelong_learning.py:99 (em LifelongLearningSystem.apply_learning)
```

#### `self.learning_core.obter_estatisticas_aprendizado` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/lifelong_learning.py:113 (em LifelongLearningSystem.obter_estatisticas_aprendizado)
```

#### `self.config.password` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:60 (em DatabaseLoader._initialize_connection)
```

#### `self._session.close` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:213 (em DatabaseLoader.close)
```

#### `self._engine.dispose` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:217 (em DatabaseLoader.close)
```

#### `self._loader_mapping.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:110 (em LoaderManager.load_data_by_domain)
```

#### `self._loader_mapping.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:257 (em LoaderManager.get_available_domains)
```

#### `self._loader_mapping.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:274 (em LoaderManager.get_loader_status)
```

#### `self.model.data_agendamento.desc` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:80 (em AgendamentosLoader._build_agendamentos_query)
```

#### `self.model.data_embarque.is_` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:63 (em EmbarquesLoader._build_embarques_query)
```

#### `self.item_model.cliente.ilike` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:74 (em EmbarquesLoader._build_embarques_query)
```

#### `self.item_model.cliente` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:74 (em EmbarquesLoader._build_embarques_query)
```

#### `self.model.data_entrega_prevista` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:61 (em EntregasLoader._build_entregas_query)
```

#### `self.model.data_embarque.desc` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:78 (em EntregasLoader._build_entregas_query)
```

#### `self.model.cnpj_cliente.ilike` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:72 (em FaturamentoLoader._build_faturamento_query)
```

#### `self.model.cnpj_cliente` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:72 (em FaturamentoLoader._build_faturamento_query)
```

#### `self.model.data_fatura.desc` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:77 (em FaturamentoLoader._build_faturamento_query)
```

#### `self.model.query.join` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:56 (em FretesLoader._build_fretes_query)
```

#### `self.model.transportadora_id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:58 (em FretesLoader._build_fretes_query)
```

#### `self.transportadora_model.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:58 (em FretesLoader._build_fretes_query)
```

#### `self.transportadora_model.razao_social.ilike` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:86 (em FretesLoader._build_fretes_query)
```

#### `self.transportadora_model.razao_social` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:86 (em FretesLoader._build_fretes_query)
```

#### `self.model.status_calculado` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:69 (em PedidosLoader._build_pedidos_query)
```

#### `self.transformers.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:58 (em FieldMapper._setup_default_transformers)
```

#### `self.validators.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:71 (em FieldMapper._setup_default_validators)
```

#### `self.mappers.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:235 (em MapperManager.obter_estatisticas_mappers)
```

#### `self.mappings.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:94 (em QueryMapper.map_query)
```

#### `self.mapeamentos.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:133 (em BaseMapper.listar_todos_campos)
```

#### `self.system_memory.store_system_config` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:86 (em MemoryManager.store_system_configuration)
```

#### `self.system_memory.retrieve_system_config` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:102 (em MemoryManager.retrieve_system_configuration)
```

#### `self.system_memory.store_performance_metric` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:236 (em MemoryManager.record_performance_metric)
```

#### `self.context_memory.get_memory_stats` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:255 (em MemoryManager.get_system_overview)
```

#### `self.system_memory.get_system_overview` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:257 (em MemoryManager.get_system_overview)
```

#### `self.system_memory.cleanup_expired_data` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:283 (em MemoryManager.cleanup_expired_data)
```

#### `self.context_memory.clear_context` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:311 (em MemoryManager.clear_all_context)
```

#### `self.context_memory.get_active_sessions` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:324 (em MemoryManager.get_active_sessions)
```

#### `self.urls.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:295 (em CursorMonitor.top-level)
```

#### `self.response_times.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:73 (em ClaudeAIMetrics.record_query)
```

#### `self.metrics_buffer.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:88 (em ClaudeAIMetrics.record_query)
```

#### `self.query_types.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:241 (em ClaudeAIMetrics.get_usage_metrics)
```

#### `self.last_reset.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:258 (em ClaudeAIMetrics.get_usage_metrics)
```

#### `self.model_config.copy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:263 (em ClaudeAIMetrics.get_model_config)
```

#### `self.metrics_buffer.clear` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:397 (em ClaudeAIMetrics.reset_metrics)
```

#### `self.query_types.clear` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:398 (em ClaudeAIMetrics.reset_metrics)
```

#### `self.response_times.clear` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:399 (em ClaudeAIMetrics.reset_metrics)
```

#### `self.auto_command_processor.process_natural_command` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:554 (em MainOrchestrator._execute_natural_commands)
```

#### `self.suggestions_manager.generate_intelligent_suggestions` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:601 (em MainOrchestrator._execute_intelligent_suggestions)
```

#### `self.base_command._validate_input` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:648 (em MainOrchestrator._execute_basic_commands)
```

#### `self.base_command._extract_filters_advanced` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:657 (em MainOrchestrator._execute_basic_commands)
```

#### `self.base_command._sanitize_input` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:661 (em MainOrchestrator._execute_basic_commands)
```

#### `self.base_command.__class__.__name__` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:668 (em MainOrchestrator._execute_basic_commands)
```

#### `self.base_command.__class__` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:668 (em MainOrchestrator._execute_basic_commands)
```

#### `self.response_processor.gerar_resposta_otimizada` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:721 (em MainOrchestrator._execute_response_processing)
```

#### `self.semantic.enrich` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1088 (em EnrichersWrapper.enrich_data)
```

#### `self.context.enrich` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1090 (em EnrichersWrapper.enrich_data)
```

#### `self.component_type.title` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1248 (em MockComponent.get_security_info)
```

#### `self.active_tasks.pop` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:322 (em OrchestratorManager.top-level)
```

#### `self.security_guard.sanitize_input` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:390 (em OrchestratorManager._log_security_audit)
```

#### `self.security_guard.generate_token` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:398 (em OrchestratorManager._log_security_audit)
```

#### `self.orchestrators.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:456 (em OrchestratorManager._detect_appropriate_orchestrator)
```

#### `self.orchestrators.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:473 (em OrchestratorManager.top-level)
```

#### `self.operation_history.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:633 (em OrchestratorManager._record_operation)
```

#### `self.operation_history.clear` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:747 (em OrchestratorManager.clear_history)
```

#### `self.sessions.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:58 (em MockSessionMemory.get_session)
```

#### `self.session_memory.store_session` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:270 (em SessionOrchestrator.create_session)
```

#### `self.conversation_manager.manage_conversation` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:476 (em SessionOrchestrator._execute_conversation_workflow)
```

#### `self.active_sessions.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:639 (em SessionOrchestrator.get_session)
```

#### `self.active_sessions.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:672 (em SessionOrchestrator.cleanup_expired_sessions)
```

#### `self.cleanup_handlers.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:741 (em SessionOrchestrator.register_cleanup_handler)
```

#### `self.workflows_ativos.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:317 (em WorkflowOrchestrator.obter_status_workflow)
```

#### `self.workflows_ativos.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:326 (em WorkflowOrchestrator.listar_workflows_ativos)
```

#### `self.workflows_ativos.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:353 (em WorkflowOrchestrator.limpar_workflows_concluidos)
```

#### `self.workflows_ativos.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:374 (em WorkflowOrchestrator.obter_estatisticas)
```

#### `self.templates_workflow.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:381 (em WorkflowOrchestrator.obter_estatisticas)
```

#### `self.executores.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:382 (em WorkflowOrchestrator.obter_estatisticas)
```

#### `self.coordinator.execute_processor_chain` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:152 (em ProcessorManager.execute_processing_chain)
```

#### `self.flask_wrapper.get_status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:166 (em ProcessorManager.get_status)
```

#### `self.coordinator.get_coordinator_stats` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:168 (em ProcessorManager.get_status)
```

#### `self.registry.validate_all_processors` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:199 (em ProcessorManager.get_detailed_health_report)
```

#### `self.flask_wrapper.get_flask_context_info` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:200 (em ProcessorManager.get_detailed_health_report)
```

#### `self.coordinator.get_active_chains` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:201 (em ProcessorManager.get_detailed_health_report)
```

#### `self.registry.reload_processor` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:212 (em ProcessorManager.reload_processors)
```

#### `self.coordinator.cleanup_completed_chains` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:231 (em ProcessorManager.cleanup_resources)
```

#### `self.context_manager.enrich_query` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/query_processor.py:24 (em QueryProcessor.process_query)
```

#### `self.learning_system.get_relevant_knowledge` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/query_processor.py:27 (em QueryProcessor.process_query)
```

#### `self.learning_system.record_interaction` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/query_processor.py:33 (em QueryProcessor.process_query)
```

#### `self.context_cache.clear` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/context_provider.py:267 (em ContextProvider.clear_context_cache)
```

#### `self.context_cache.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/context_provider.py:271 (em ContextProvider.clear_context_cache)
```

#### `self.context_sources.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/context_provider.py:344 (em ContextProvider._collect_complete_context)
```

#### `self.request_stats.copy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:354 (em ProviderManager.get_provider_status)
```

#### `self.providers_cache.clear` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:361 (em ProviderManager.clear_cache)
```

#### `self.context_provider.clear_context_cache` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:363 (em ProviderManager.clear_cache)
```

#### `self.metadata_reader.listar_tabelas` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:91 (em DatabaseManager.listar_tabelas)
```

#### `self.field_searcher.buscar_campos_por_tipo` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:141 (em DatabaseManager.buscar_campos_por_tipo)
```

#### `self.field_searcher.buscar_campos_por_nome` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:164 (em DatabaseManager.buscar_campos_por_nome)
```

#### `self.metadata_reader.obter_estatisticas_tabelas` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:213 (em DatabaseManager.obter_estatisticas_gerais)
```

#### `self.connection.get_connection_info` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:216 (em DatabaseManager.obter_estatisticas_gerais)
```

#### `self.data_analyzer.analisar_tabela_completa` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:251 (em DatabaseManager.analisar_tabela_completa)
```

#### `self.field_searcher.buscar_campos_similares` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:289 (em DatabaseManager.buscar_campos_similares)
```

#### `self.auto_mapper.gerar_mapeamento_multiplas_tabelas` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:303 (em DatabaseManager.gerar_mapeamento_multiplas_tabelas)
```

#### `self.relationship_mapper.obter_caminho_relacionamentos` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:316 (em DatabaseManager.obter_caminho_relacionamentos)
```

#### `self.metadata_reader.limpar_cache` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:324 (em DatabaseManager.limpar_cache)
```

#### `self.data_analyzer.limpar_cache` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:325 (em DatabaseManager.limpar_cache)
```

#### `self.relationship_mapper.limpar_cache` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:326 (em DatabaseManager.limpar_cache)
```

#### `self.field_searcher.limpar_cache` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:327 (em DatabaseManager.limpar_cache)
```

#### `self.auto_mapper.limpar_cache` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:328 (em DatabaseManager.limpar_cache)
```

#### `self.modelos_cache.clear` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:332 (em DatabaseManager.limpar_cache)
```

#### `self.connection.close_connection` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:345 (em DatabaseManager.recarregar_conexao)
```

#### `self.connection._establish_connection` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:348 (em DatabaseManager.recarregar_conexao)
```

#### `self.metadata_reader.set_inspector` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:355 (em DatabaseManager.recarregar_conexao)
```

#### `self.relationship_mapper.set_inspector` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:356 (em DatabaseManager.recarregar_conexao)
```

#### `self.field_searcher.set_inspector` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:357 (em DatabaseManager.recarregar_conexao)
```

#### `self.data_analyzer.set_engine` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:360 (em DatabaseManager.recarregar_conexao)
```

#### `self.field_searcher.set_metadata_reader` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:361 (em DatabaseManager.recarregar_conexao)
```

#### `self.auto_mapper.set_metadata_reader` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:362 (em DatabaseManager.recarregar_conexao)
```

#### `self.auto_mapper.set_data_analyzer` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:363 (em DatabaseManager.recarregar_conexao)
```

#### `self.connection.is_inspector_available` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:391 (em DatabaseManager.obter_info_modulos)
```

#### `self.metadata_reader.tabelas_cache` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:395 (em DatabaseManager.obter_info_modulos)
```

#### `self.data_analyzer.analysis_cache` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:399 (em DatabaseManager.obter_info_modulos)
```

#### `self.relationship_mapper.relationships_cache` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:403 (em DatabaseManager.obter_info_modulos)
```

#### `self.field_searcher.search_cache` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:407 (em DatabaseManager.obter_info_modulos)
```

#### `self.auto_mapper.mapping_cache` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:411 (em DatabaseManager.obter_info_modulos)
```

#### `self.metadata_reader._normalizar_tipo_sqlalchemy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:419 (em DatabaseManager._normalizar_tipo_sqlalchemy)
```

#### `self.field_searcher._calcular_score_match_nome` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:423 (em DatabaseManager._calcular_score_match)
```

#### `self.auto_mapper._gerar_termos_automaticos` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:428 (em DatabaseManager._gerar_termos_automaticos)
```

#### `self.code_scanner.discover_all_forms` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:107 (em ProjectScanner.scan_complete_project)
```

#### `self.code_scanner.discover_all_routes` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:110 (em ProjectScanner.scan_complete_project)
```

#### `self.database_scanner.discover_database_schema` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:116 (em ProjectScanner.scan_complete_project)
```

#### `self.project_structure.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:177 (em ProjectScanner._generate_scan_summary)
```

#### `self.project_structure.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:178 (em ProjectScanner._generate_scan_summary)
```

#### `self.discovered_templates.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:250 (em ProjectScanner._calculate_quality_metrics)
```

#### `self.project_scanner.scan_complete_project` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:90 (em ScanningManager.scan_complete_project)
```

#### `self.project_scanner.file_scanner.read_file_content` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:110 (em ScanningManager.read_file_content)
```

#### `self.project_scanner.file_scanner.list_directory_contents` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:114 (em ScanningManager.list_directory_contents)
```

#### `self.project_scanner.file_scanner.search_in_files` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:119 (em ScanningManager.search_in_files)
```

#### `self.database_manager.listar_tabelas` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:132 (em ScanningManager.scan_database)
```

#### `self.database_manager.obter_campos_tabela` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:144 (em ScanningManager.scan_database)
```

#### `self.database_manager.analisar_tabela_completa` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:156 (em ScanningManager.scan_database)
```

#### `self.database_manager.obter_estatisticas_gerais` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:164 (em ScanningManager.scan_database)
```

#### `self.database_manager.buscar_campos_por_tipo` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:175 (em ScanningManager.scan_database)
```

#### `self.database_manager.buscar_campos_por_nome` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:177 (em ScanningManager.scan_database)
```

#### `self.project_scanner.get_scanner_status().get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:266 (em ScanningManager.executar_diagnostico_completo)
```

#### `self._project_scanner.reset_scanner_data` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:312 (em ScanningManager.reset_scanner)
```

#### `self.project_scanner._generate_scan_summary` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:351 (em ScanningManager._generate_scan_summary)
```

#### `self.term_patterns.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:232 (em AutoMapper._gerar_termos_automaticos)
```

#### `self.term_patterns.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:333 (em AutoMapper._calcular_confianca_mapeamento)
```

#### `self.db_session.close` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:263 (em DatabaseConnection.close_connection)
```

#### `self.db_engine.dispose` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:267 (em DatabaseConnection.close_connection)
```

#### `self.inspector.get_columns` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:85 (em MetadataReader.obter_campos_tabela)
```

#### `self.inspector.get_indexes` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:171 (em MetadataReader._obter_indices_tabela)
```

#### `self.inspector.get_pk_constraint` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:212 (em MetadataReader._obter_constraints_tabela)
```

#### `self.inspector.get_unique_constraints` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:230 (em MetadataReader._obter_constraints_tabela)
```

#### `self.inspector.get_check_constraints` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:238 (em MetadataReader._obter_constraints_tabela)
```

#### `self.suggestion_engines.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:207 (em SuggestionsManager.register_suggestion_engine)
```

#### `self.suggestions_cache.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:720 (em SuggestionsManager._optimize_cache)
```

#### `self.feedback_history.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:769 (em SuggestionsManager._cleanup_old_data)
```

#### `self.cache.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_classes.py:308 (em BaseProcessor._get_cached_result)
```

#### `self._config.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_context_manager.py:39 (em BaseContextManager._get_config)
```

#### `self._config.copy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_context_manager.py:67 (em BaseContextManager.get_config_dict)
```

#### `self._config.clear` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_context_manager.py:80 (em BaseContextManager.clear_config)
```

#### `self._config.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/base_context_manager.py:89 (em BaseContextManager.update_config)
```

#### `self._cache_timestamps.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:126 (em ScannersCache.get_cached_result)
```

#### `self._results_cache.pop` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:156 (em ScannersCache._remove_from_cache)
```

#### `self._cache_timestamps.pop` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:157 (em ScannersCache._remove_from_cache)
```

#### `self._cache_timestamps.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:164 (em ScannersCache._cleanup_expired_cache)
```

#### `self._results_cache.clear` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:196 (em ScannersCache.clear_cache)
```

#### `self._cache_timestamps.clear` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:197 (em ScannersCache.clear_cache)
```

#### `self.processor_types.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:173 (em ProcessorRegistry.get_processor_type)
```

#### `self.flask_wrapper.is_flask_available` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:263 (em ProcessorRegistry.get_registry_stats)
```

#### `self.processors.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:273 (em ProcessorRegistry.validate_all_processors)
```

#### `self.orchestrator.mapear_termo_natural` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:341 (em SemanticValidator.validar_mapeamento_completo)
```

#### `self.validators.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:317 (em ValidatorManager.validate_consistency)
```

#### `self.validators.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:362 (em ValidatorManager.get_validation_status)
```

### 🔍 Objeto: `semantic`

#### `semantic.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:250 (em ContextEnricher._calculate_context_score)
```

### 🔍 Objeto: `semantic_analysis`

#### `semantic_analysis.get` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:311 (em AnalyzerManager._should_use_nlp_analysis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:320 (em AnalyzerManager._should_use_nlp_analysis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:362 (em AnalyzerManager._generate_combined_insights)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:363 (em AnalyzerManager._generate_combined_insights)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:162 (em SemanticLoopProcessor.top-level)
  ... e mais 2 ocorrências
```

### 🔍 Objeto: `semantic_mapper`

#### `semantic_mapper.analisar_consulta_semantica` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:126 (em SemanticLoopProcessor.top-level)
```

### 🔍 Objeto: `semantic_processor`

#### `semantic_processor.process_semantic_loop` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:83 (em ProcessorManager.process_semantic_loop)
```

### 🔍 Objeto: `semantic_validator`

#### `semantic_validator.validar_consistencia_readme_banco` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:325 (em ValidatorManager.validate_consistency)
```

### 🔍 Objeto: `session`

#### `session.metadata` (12 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:317 (em SessionOrchestrator.initialize_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:324 (em SessionOrchestrator.initialize_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:389 (em SessionOrchestrator.execute_session_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:396 (em SessionOrchestrator.execute_session_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:442 (em SessionOrchestrator._execute_learning_workflow)
  ... e mais 7 ocorrências
```

#### `session.metadata.update` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:317 (em SessionOrchestrator.initialize_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:389 (em SessionOrchestrator.execute_session_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:442 (em SessionOrchestrator._execute_learning_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:485 (em SessionOrchestrator._execute_conversation_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:522 (em SessionOrchestrator.apply_learned_knowledge)
  ... e mais 2 ocorrências
```

#### `session.session_id` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:448 (em SessionOrchestrator._execute_learning_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:452 (em SessionOrchestrator._execute_learning_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:477 (em SessionOrchestrator._execute_conversation_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:492 (em SessionOrchestrator._execute_conversation_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:496 (em SessionOrchestrator._execute_conversation_workflow)
```

#### `session.update_activity` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:304 (em SessionOrchestrator.initialize_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:363 (em SessionOrchestrator.execute_session_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:554 (em SessionOrchestrator.complete_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:602 (em SessionOrchestrator.terminate_session)
```

#### `session.user_id` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:438 (em SessionOrchestrator._execute_learning_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:481 (em SessionOrchestrator._execute_conversation_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:656 (em SessionOrchestrator.get_user_sessions)
```

#### `session.components` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:308 (em SessionOrchestrator.initialize_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:319 (em SessionOrchestrator.initialize_session)
```

#### `session.error_history.append` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:332 (em SessionOrchestrator.initialize_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:404 (em SessionOrchestrator.execute_session_workflow)
```

#### `session.error_history` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:332 (em SessionOrchestrator.initialize_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:404 (em SessionOrchestrator.execute_session_workflow)
```

#### `session.is_active` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:357 (em SessionOrchestrator.execute_session_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:657 (em SessionOrchestrator.get_user_sessions)
```

#### `session.status.value` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:358 (em SessionOrchestrator.execute_session_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:711 (em SessionOrchestrator.get_session_stats)
```

#### `session.status` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:358 (em SessionOrchestrator.execute_session_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:711 (em SessionOrchestrator.get_session_stats)
```

#### `session.workflow_state` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:379 (em SessionOrchestrator.execute_session_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:392 (em SessionOrchestrator.execute_session_workflow)
```

#### `session.created_at` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:563 (em SessionOrchestrator.complete_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:719 (em SessionOrchestrator.get_session_stats)
```

#### `session.components.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:308 (em SessionOrchestrator.initialize_session)
```

#### `session.is_expired` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:673 (em SessionOrchestrator.cleanup_expired_sessions)
```

#### `session.priority.value` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:715 (em SessionOrchestrator.get_session_stats)
```

#### `session.priority` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:715 (em SessionOrchestrator.get_session_stats)
```

### 🔍 Objeto: `session_context`

#### `session_context.metadata` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:256 (em SessionOrchestrator.create_session)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:270 (em SessionOrchestrator.create_session)
```

#### `session_context.metadata.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:256 (em SessionOrchestrator.create_session)
```

### 🔍 Objeto: `session_orch`

#### `session_orch.create_session` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:89 (em module.teste_sistema_basico)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:197 (em module.teste_funcionalidades_avancadas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:281 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `session_orch.complete_session` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:90 (em module.teste_sistema_basico)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:211 (em module.teste_funcionalidades_avancadas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:290 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `session_orch.learning_core` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:142 (em module.teste_modulos_alto_valor)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:272 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_status_completo.py:42 (em module.verificar_status)
```

#### `session_orch.execute_session_workflow` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:199 (em module.teste_funcionalidades_avancadas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:286 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `session_orch.security_guard` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:273 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_status_completo.py:43 (em module.verificar_status)
```

#### `session_orch.conversation_manager` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:274 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `session_orch.integration_manager` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_status_completo.py:41 (em module.verificar_status)
```

### 🔍 Objeto: `sessions`

#### `sessions.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:658 (em SessionOrchestrator.get_user_sessions)
```

### 🔍 Objeto: `set`

#### `set.intersection` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:138 (em ClassDuplicateFinder.calculate_similarity)
```

#### `set.union` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:139 (em ClassDuplicateFinder.calculate_similarity)
```

### 🔍 Objeto: `signal`

#### `signal.signal` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:346 (em CursorMonitor.start)
```

#### `signal.SIGINT` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:346 (em CursorMonitor.start)
```

### 🔍 Objeto: `simulator`

#### `simulator.simulate_query` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:53 (em module.run_loop_detection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:285 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:334 (em module.top-level)
```

#### `simulator.run_production_tests` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:280 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:327 (em module.top-level)
```

#### `simulator.test_specific_scenario` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:293 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:343 (em module.top-level)
```

#### `simulator.max_depth` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:297 (em module.main)
```

#### `simulator.timeout_seconds` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:298 (em module.main)
```

### 🔍 Objeto: `sistema`

#### `sistema.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:318 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
```

### 🔍 Objeto: `source_data`

#### `source_data.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:114 (em FieldMapper.map_fields)
```

### 🔍 Objeto: `source_results`

#### `source_results.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:176 (em IntelligenceProcessor.synthesize_multi_source_intelligence)
```

### 🔍 Objeto: `sources_used`

#### `sources_used.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:123 (em SuggestionsManager.generate_suggestions)
```

### 🔍 Objeto: `spacy`

#### `spacy.load` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:20 (em module.top-level)
```

#### `spacy.blank` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:23 (em module.top-level)
```

### 🔍 Objeto: `specific_results`

#### `specific_results.get` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:136 (em DeepValidator._test_individual_module)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:137 (em DeepValidator._test_individual_module)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:138 (em DeepValidator._test_individual_module)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:141 (em DeepValidator._test_individual_module)
```

### 🔍 Objeto: `start_date`

#### `start_date.replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:260 (em BaseValidationUtils.validate_date_range)
```

### 🔍 Objeto: `state`

#### `state.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:141 (em SystemMemory.store_component_state)
```

### 🔍 Objeto: `state_data`

#### `state_data.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:183 (em SystemMemory.retrieve_component_state)
```

### 🔍 Objeto: `statistics`

#### `statistics.mean` (10 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:173 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:174 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:175 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:300 (em PerformanceAnalyzer.analyze_user_behavior)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:404 (em PerformanceAnalyzer._analyze_trends)
  ... e mais 5 ocorrências
```

#### `statistics.stdev` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:193 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:563 (em PerformanceAnalyzer.detect_outliers)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:581 (em PerformanceAnalyzer._detect_statistical_anomalies)
```

#### `statistics.median` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:192 (em PerformanceAnalyzer.analyze_ai_performance)
```

### 🔍 Objeto: `stats`

#### `stats.get` (10 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:704 (em ValidadorSistemaCompleto._testar_fallbacks)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:300 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:335 (em module.format_response_advanced)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:477 (em SemanticEnricher._gerar_sugestoes_batch)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:485 (em SemanticEnricher._gerar_sugestoes_batch)
  ... e mais 5 ocorrências
```

#### `stats.update` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:289 (em BaseCommand._create_summary_stats)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:300 (em BaseCommand._create_summary_stats)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:309 (em BaseCommand._create_summary_stats)
```

#### `stats.get().get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:476 (em KnowledgeMemory.get_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:477 (em KnowledgeMemory.get_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:478 (em KnowledgeMemory.get_status)
```

### 🔍 Objeto: `status`

#### `status.get` (12 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:205 (em ValidadorSistemaCompleto._testar_componentes_criticos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_status_completo.py:30 (em module.verificar_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_status_completo.py:31 (em module.verificar_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_status_completo.py:32 (em module.verificar_status)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:74 (em SmartBaseAgent._conectar_integration_manager)
  ... e mais 7 ocorrências
```

#### `status.values` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:281 (em module.get_commands_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/__init__.py:169 (em module.validate_flask_dependencies)
```

#### `status.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/__init__.py:372 (em module.top-level)
```

#### `status.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/integration_manager.py:372 (em IntegrationManager.get_integration_status)
```

### 🔍 Objeto: `status_count`

#### `status_count.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:318 (em ExcelPedidos._criar_aba_analise_vendas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:378 (em ExcelPedidos._criar_resumo_pedidos)
```

#### `status_count.items` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:320 (em ExcelPedidos._criar_aba_analise_vendas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:402 (em ExcelPedidos._criar_resumo_pedidos)
```

### 🔍 Objeto: `status_counts`

#### `status_counts.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:376 (em WorkflowOrchestrator.obter_estatisticas)
```

### 🔍 Objeto: `status_data`

#### `status_data.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:356 (em ExcelPedidos._criar_aba_status_agendamentos)
```

### 🔍 Objeto: `status_pastas`

#### `status_pastas.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificacao_integracao_real_183_modulos.py:170 (em module.analisar_modulos_por_pasta)
```

### 🔍 Objeto: `step`

#### `step.component` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:918 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:920 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:922 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:924 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:941 (em MainOrchestrator.top-level)
```

#### `step.dependencies` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:852 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:853 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:876 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:876 (em MainOrchestrator.top-level)
```

#### `step.name` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:859 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:888 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:938 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:944 (em MainOrchestrator.top-level)
```

#### `step.method` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:931 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:932 (em MainOrchestrator.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:941 (em MainOrchestrator.top-level)
```

#### `step.parameters` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:927 (em MainOrchestrator.top-level)
```

### 🔍 Objeto: `step_config`

#### `step_config.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:80 (em ProcessorCoordinator._execute_chain_step)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:81 (em ProcessorCoordinator._execute_chain_step)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:82 (em ProcessorCoordinator._execute_chain_step)
```

### 🔍 Objeto: `step_result`

#### `step_result.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:44 (em ProcessorCoordinator.execute_processor_chain)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:47 (em ProcessorCoordinator.execute_processor_chain)
```

### 🔍 Objeto: `stopwords`

#### `stopwords.words` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:43 (em module.top-level)
```

### 🔍 Objeto: `str()`

#### `str().lower` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:161 (em PerformanceAnalyzer.analyze_ai_performance)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:64 (em FieldMapper._setup_default_transformers)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:428 (em OrchestratorManager._detect_appropriate_orchestrator)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:99 (em DatabaseScanner._get_database_version)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:129 (em DatabaseScanner._get_table_statistics)
  ... e mais 3 ocorrências
```

#### `str().strip` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/system_config.py:626 (em SystemConfig._validate_config_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:65 (em FieldMapper._setup_default_transformers)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:72 (em FieldMapper._setup_default_validators)
```

#### `str().upper` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:63 (em FieldMapper._setup_default_transformers)
```

#### `str().replace().replace().isdigit` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:73 (em FieldMapper._setup_default_validators)
```

#### `str().replace().replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:73 (em FieldMapper._setup_default_validators)
```

#### `str().replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:73 (em FieldMapper._setup_default_validators)
```

#### `str().startswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:194 (em FileScanner.read_file_content)
```

#### `str().split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:606 (em SuggestionsManager._assess_query_complexity)
```

### 🔍 Objeto: `strengths`

#### `strengths.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:685 (em IntelligenceProcessor._evaluate_option)
```

### 🔍 Objeto: `structural_analysis`

#### `structural_analysis.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:384 (em AnalyzerManager._generate_combined_insights)
```

### 🔍 Objeto: `structure`

#### `structure.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:258 (em ValidatorManager.validate_structural_integrity)
```

### 🔍 Objeto: `subdirs_validos`

#### `subdirs_validos.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:78 (em module.contar_arquivos_detalhado)
```

### 🔍 Objeto: `subprocess`

#### `subprocess.check_output().strip` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:126 (em module.generate_report)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:132 (em module.generate_report)
```

#### `subprocess.check_output` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:126 (em module.generate_report)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:132 (em module.generate_report)
```

#### `subprocess.run` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:136 (em CursorMonitor.check_flask_process)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:153 (em CursorMonitor.run_validator)
```

#### `subprocess.TimeoutExpired` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:178 (em CursorMonitor.run_validator)
```

### 🔍 Objeto: `sugestoes`

#### `sugestoes.append` (19 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:257 (em SemanticEnricher._sugestoes_readme_vs_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:264 (em SemanticEnricher._sugestoes_readme_vs_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:269 (em SemanticEnricher._sugestoes_readme_vs_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:296 (em SemanticEnricher._sugestoes_qualidade_banco)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:300 (em SemanticEnricher._sugestoes_qualidade_banco)
  ... e mais 14 ocorrências
```

#### `sugestoes.extend` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:222 (em SemanticEnricher._gerar_sugestoes_melhoria)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:225 (em SemanticEnricher._gerar_sugestoes_melhoria)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:228 (em SemanticEnricher._gerar_sugestoes_melhoria)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:231 (em SemanticEnricher._gerar_sugestoes_melhoria)
```

### 🔍 Objeto: `suggestion`

#### `suggestion.get` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:127 (em SuggestionsManager.generate_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:128 (em SuggestionsManager.generate_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:438 (em SuggestionsManager._prioritize_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:632 (em SuggestionsManager._categorize_suggestion)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:636 (em SuggestionsManager._generate_explanation)
  ... e mais 1 ocorrências
```

#### `suggestion.copy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:463 (em SuggestionsManager._enrich_suggestions)
```

### 🔍 Objeto: `suggestions`

#### `suggestions.extend` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/pedidos_mapper.py:189 (em PedidosMapper.get_semantic_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/pedidos_mapper.py:197 (em PedidosMapper.get_semantic_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/pedidos_mapper.py:204 (em PedidosMapper.get_semantic_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:549 (em SuggestionsManager._contextual_suggestions_engine)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:564 (em SuggestionsManager._contextual_suggestions_engine)
  ... e mais 2 ocorrências
```

#### `suggestions.append` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:171 (em AutoCommandProcessor.get_command_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:333 (em SuggestionsEngine._generate_data_based_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:344 (em SuggestionsEngine._generate_data_based_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:355 (em SuggestionsEngine._generate_data_based_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:417 (em SuggestionsEngine._generate_data_based_suggestions)
```

#### `suggestions.sort` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:181 (em AutoCommandProcessor.get_command_suggestions)
```

### 🔍 Objeto: `suggestions_result`

#### `suggestions_result.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:608 (em MainOrchestrator._execute_intelligent_suggestions)
```

### 🔍 Objeto: `suitable_components`

#### `suitable_components.sort` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:615 (em IntelligenceCoordinator._select_best_component)
```

### 🔍 Objeto: `super()`

#### `super().__init__` (35 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:111 (em AnalyzerManager.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:30 (em AutoCommandProcessor.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:18 (em CursorCommands.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:19 (em DevCommands.__init__)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:43 (em ExcelOrchestrator.__init__)
  ... e mais 30 ocorrências
```

#### `super().to_dict` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/advanced_config.py:94 (em AdvancedConfig.get_config)
```

#### `super().analyze` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:163 (em SmartBaseAgent.top-level)
```

#### `super()._get_cached_result` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/base.py:89 (em ProcessorBase._get_cached_result)
```

#### `super().__new__` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:38 (em ScannersCache.__new__)
```

### 🔍 Objeto: `sys`

#### `sys.path` (18 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:15 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:14 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:15 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:15 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:16 (em module.top-level)
  ... e mais 13 ocorrências
```

#### `sys.path.insert` (16 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/corrigir_imports_automatico.py:15 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:14 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:15 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:15 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:16 (em module.top-level)
  ... e mais 11 ocorrências
```

#### `sys.exit` (11 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/pre_commit_check.py:212 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:328 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:335 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:338 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:344 (em module.top-level)
  ... e mais 6 ocorrências
```

#### `sys.argv` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:322 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:325 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:330 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:332 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:333 (em module.top-level)
  ... e mais 3 ocorrências
```

#### `sys.executable` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:154 (em CursorMonitor.run_validator)
```

#### `sys.path.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:19 (em module.top-level)
```

### 🔍 Objeto: `system`

#### `system.__class__.__name__` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/__init__.py:200 (em module.initialize_integration_system)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/__init__.py:205 (em module.initialize_integration_system)
```

#### `system.__class__` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/__init__.py:200 (em module.initialize_integration_system)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/__init__.py:205 (em module.initialize_integration_system)
```

#### `system.initialize_complete_system` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/__init__.py:190 (em module.initialize_integration_system)
```

### 🔍 Objeto: `system_claude_config`

#### `system_claude_config.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/advanced_config.py:100 (em AdvancedConfig.get_config)
```

### 🔍 Objeto: `system_config`

#### `system_config.get_config` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:163 (em module.get_config)
```

#### `system_config.set_config` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:215 (em module.set_config)
```

#### `system_config.get_profile_config` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:243 (em module.get_profile_config)
```

#### `system_config.switch_profile` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:264 (em module.switch_profile)
```

#### `system_config.reload_config` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:286 (em module.reload_config)
```

#### `system_config.validate_configuration` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:313 (em module.validate_configuration)
```

#### `system_config.export_config` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:341 (em module.export_config)
```

#### `system_config.import_config` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:369 (em module.import_config)
```

#### `system_config.register_config_watcher` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:393 (em module.register_config_watcher)
```

#### `system_config.get_system_status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/config/__init__.py:414 (em module.get_system_status)
```

### 🔍 Objeto: `system_status`

#### `system_status.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:452 (em WebFlaskRoutes.health_check)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/integration/web_integration.py:453 (em WebFlaskRoutes.health_check)
```

### 🔍 Objeto: `t`

#### `t.strip().strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:179 (em ReadmeScanner._extrair_termos_da_string)
```

#### `t.strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:179 (em ReadmeScanner._extrair_termos_da_string)
```

#### `t.start` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:208 (em TestLoopPrevention.test_stress_concurrent_requests)
```

#### `t.join` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:212 (em TestLoopPrevention.test_stress_concurrent_requests)
```

### 🔍 Objeto: `tabelas_nao_documentadas`

#### `tabelas_nao_documentadas.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:245 (em SemanticValidator.validar_consistencia_readme_banco)
```

### 🔍 Objeto: `tables`

#### `tables.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:280 (em DatabaseScanner._analyze_relationships)
```

### 🔍 Objeto: `target`

#### `target.id` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:56 (em VariableTracker.visit_ClassDef)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:63 (em VariableTracker.visit_Assign)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:64 (em VariableTracker.visit_Assign)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:151 (em CodeScanner._parse_form_field)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:235 (em StructureScanner._extract_table_name)
  ... e mais 1 ocorrências
```

#### `target.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:403 (em ValidatorManager.run_full_validation_suite)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:416 (em ValidatorManager.run_full_validation_suite)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:421 (em ValidatorManager.run_full_validation_suite)
```

### 🔍 Objeto: `target_dir`

#### `target_dir.exists` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:227 (em FileScanner.list_directory_contents)
```

#### `target_dir.is_dir` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:227 (em FileScanner.list_directory_contents)
```

#### `target_dir.relative_to` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:231 (em FileScanner.list_directory_contents)
```

#### `target_dir.iterdir` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:240 (em FileScanner.list_directory_contents)
```

### 🔍 Objeto: `target_orchestrator`

#### `target_orchestrator.value` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:292 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:297 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:316 (em OrchestratorManager.top-level)
```

#### `target_orchestrator.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:795 (em module.top-level)
```

### 🔍 Objeto: `task`

#### `task.operation` (18 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:488 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:545 (em OrchestratorManager._execute_workflow_operation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:546 (em OrchestratorManager._execute_workflow_operation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:548 (em OrchestratorManager._execute_workflow_operation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:553 (em OrchestratorManager.top-level)
  ... e mais 13 ocorrências
```

#### `task.parameters` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:489 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:547 (em OrchestratorManager._execute_workflow_operation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:559 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:602 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:603 (em OrchestratorManager.top-level)
  ... e mais 3 ocorrências
```

#### `task.orchestrator_type` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:473 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:475 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:478 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:480 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:635 (em OrchestratorManager._record_operation)
```

#### `task.parameters.get` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:602 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:603 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:609 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:610 (em OrchestratorManager.top-level)
```

#### `task.created_at` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:299 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:638 (em OrchestratorManager._record_operation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:640 (em OrchestratorManager._record_operation)
```

#### `task.orchestrator_type.value` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:475 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:635 (em OrchestratorManager._record_operation)
```

#### `task.operation.lower` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:488 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:578 (em OrchestratorManager.top-level)
```

#### `task.task_id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:634 (em OrchestratorManager._record_operation)
```

#### `task.status` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:637 (em OrchestratorManager._record_operation)
```

#### `task.created_at.isoformat` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:638 (em OrchestratorManager._record_operation)
```

#### `task.error` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:641 (em OrchestratorManager._record_operation)
```

#### `task.done` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:203 (em ValidatorManager.validate_agent_responses)
```

#### `task.result` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:203 (em ValidatorManager.validate_agent_responses)
```

### 🔍 Objeto: `tempfile`

#### `tempfile.gettempdir` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:61 (em BaseCommand.__init__)
```

### 🔍 Objeto: `template_info`

#### `template_info.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:251 (em ProjectScanner._calculate_quality_metrics)
```

### 🔍 Objeto: `templates_dir`

#### `templates_dir.exists` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:52 (em FileScanner.discover_all_templates)
```

### 🔍 Objeto: `temporal`

#### `temporal.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:246 (em ContextEnricher._calculate_context_score)
```

### 🔍 Objeto: `temporal_words`

#### `temporal_words.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:201 (em QueryAnalyzer._detect_temporal_patterns)
```

### 🔍 Objeto: `termo`

#### `termo.lower` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:63 (em BaseMapper.buscar_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:101 (em BaseMapper.buscar_mapeamento_fuzzy)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:65 (em KnowledgeMemory.aprender_mapeamento_cliente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:89 (em KnowledgeMemory.aprender_mapeamento_cliente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:405 (em SemanticValidator._calcular_similaridade_termo_campo)
  ... e mais 1 ocorrências
```

#### `termo.strip` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:68 (em MapperManager.analisar_consulta_semantica)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:185 (em ReadmeScanner._extrair_termos_da_string)
```

#### `termo.lower().strip` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:63 (em BaseMapper.buscar_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:101 (em BaseMapper.buscar_mapeamento_fuzzy)
```

#### `termo.strip().strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:185 (em ReadmeScanner._extrair_termos_da_string)
```

#### `termo.lower().replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:405 (em SemanticValidator._calcular_similaridade_termo_campo)
```

#### `termo.lower().split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:413 (em SemanticValidator._calcular_similaridade_termo_campo)
```

### 🔍 Objeto: `termo_natural`

#### `termo_natural.lower` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:69 (em BaseMapper.buscar_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:106 (em BaseMapper.buscar_mapeamento_fuzzy)
```

### 🔍 Objeto: `termos`

#### `termos.append` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:464 (em PatternLearner._extrair_termos_cliente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:470 (em PatternLearner._extrair_termos_cliente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:478 (em PatternLearner._extrair_termos_cliente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:405 (em KnowledgeMemory._extrair_termos_cliente)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:411 (em KnowledgeMemory._extrair_termos_cliente)
  ... e mais 3 ocorrências
```

#### `termos.extend` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:144 (em BaseMapper.listar_termos_naturais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:166 (em ReadmeScanner._extrair_termos_da_string)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:172 (em ReadmeScanner._extrair_termos_da_string)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:180 (em ReadmeScanner._extrair_termos_da_string)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:234 (em AutoMapper._gerar_termos_automaticos)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `termos_compostos`

#### `termos_compostos.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:146 (em MapperManager._extrair_termos_compostos)
```

### 🔍 Objeto: `termos_encontrados`

#### `termos_encontrados.extend` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:116 (em ReadmeScanner.buscar_termos_naturais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:124 (em ReadmeScanner.buscar_termos_naturais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:133 (em ReadmeScanner.buscar_termos_naturais)
```

### 🔍 Objeto: `termos_limpos`

#### `termos_limpos.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:187 (em ReadmeScanner._extrair_termos_da_string)
```

### 🔍 Objeto: `termos_melhorados`

#### `termos_melhorados.extend` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:422 (em AutoMapper._melhorar_termos_com_analise)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:426 (em AutoMapper._melhorar_termos_com_analise)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:430 (em AutoMapper._melhorar_termos_com_analise)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:434 (em AutoMapper._melhorar_termos_com_analise)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:438 (em AutoMapper._melhorar_termos_com_analise)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `termos_originais`

#### `termos_originais.copy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:412 (em AutoMapper._melhorar_termos_com_analise)
```

### 🔍 Objeto: `termos_tipo`

#### `termos_tipo.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:316 (em AutoMapper._obter_termos_por_tipo)
```

### 🔍 Objeto: `termos_unicos`

#### `termos_unicos.append` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:142 (em ReadmeScanner.buscar_termos_naturais)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:251 (em AutoMapper._gerar_termos_automaticos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:453 (em AutoMapper._melhorar_termos_com_analise)
```

### 🔍 Objeto: `tester`

#### `tester.testar_todos_modulos` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:426 (em module.main)
```

### 🔍 Objeto: `tests`

#### `tests.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:59 (em ValidadorSistemaReal.test_basic_imports)
```

### 🔍 Objeto: `text`

#### `text.split` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:33 (em FallbackNLPEnhancedAnalyzer.analyze_text)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:33 (em FallbackNLPEnhancedAnalyzer.analyze_text)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:505 (em AnalyzerManager.analyze_nlp)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:506 (em AnalyzerManager.analyze_nlp)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/__init__.py:52 (em NLPEnhancedAnalyzer.analyze_text)
  ... e mais 2 ocorrências
```

#### `text.lower` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:272 (em SemanticAnalyzer._extract_keywords)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:301 (em AutoCommandProcessor._detect_commands)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:168 (em CriticAgent._validate_data_consistency)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:170 (em CriticAgent._validate_data_consistency)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:187 (em CriticAgent._validate_data_consistency)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `texto`

#### `texto.lower` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:118 (em NLPEnhancedAnalyzer.analisar_com_nlp)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:285 (em NLPEnhancedAnalyzer._calcular_similaridades)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:384 (em PatternLearner._extrair_palavras_chave_dominio)
```

#### `texto.lower().strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:118 (em NLPEnhancedAnalyzer.analisar_com_nlp)
```

#### `texto.lower().split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:384 (em PatternLearner._extrair_palavras_chave_dominio)
```

#### `texto.strip().strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:177 (em ReadmeScanner._extrair_termos_da_string)
```

#### `texto.strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:177 (em ReadmeScanner._extrair_termos_da_string)
```

### 🔍 Objeto: `texto_corrigido`

#### `texto_corrigido.replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:182 (em NLPEnhancedAnalyzer._aplicar_correcoes)
```

#### `texto_corrigido.split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:187 (em NLPEnhancedAnalyzer._aplicar_correcoes)
```

### 🔍 Objeto: `texto_limpo`

#### `texto_limpo.lower().split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:229 (em NLPEnhancedAnalyzer._tokenizar_basico)
```

#### `texto_limpo.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:229 (em NLPEnhancedAnalyzer._tokenizar_basico)
```

#### `texto_limpo.split` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:179 (em ReadmeScanner._extrair_termos_da_string)
```

### 🔍 Objeto: `thread`

#### `thread.start` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:112 (em ProductionSimulator.simulate_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:110 (em TestLoopPrevention.test_timeout_protection)
```

#### `thread.join` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:113 (em ProductionSimulator.simulate_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:113 (em TestLoopPrevention.test_timeout_protection)
```

#### `thread.is_alive` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:115 (em ProductionSimulator.simulate_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:115 (em TestLoopPrevention.test_timeout_protection)
```

### 🔍 Objeto: `threading`

#### `threading.Thread` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:110 (em ProductionSimulator.simulate_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:108 (em TestLoopPrevention.test_timeout_protection)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:206 (em TestLoopPrevention.test_stress_concurrent_requests)
```

#### `threading.Lock` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:32 (em ScannersCache.top-level)
```

### 🔍 Objeto: `threads`

#### `threads.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:207 (em TestLoopPrevention.test_stress_concurrent_requests)
```

### 🔍 Objeto: `time`

#### `time.time` (31 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:38 (em ProductionSimulator.track_call)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:69 (em ProductionSimulator.simulate_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:76 (em ProductionSimulator.simulate_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:124 (em ProductionSimulator.simulate_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:173 (em ProductionSimulator.run_production_tests)
  ... e mais 26 ocorrências
```

#### `time.sleep` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:184 (em ProductionSimulator.run_production_tests)
```

### 🔍 Objeto: `time_since_activity`

#### `time_since_activity.total_seconds` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:311 (em ConversationManager.cleanup_expired_conversations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:381 (em ConversationManager._is_conversation_active)
```

### 🔍 Objeto: `timestamp`

#### `timestamp.hour` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:358 (em AdaptiveLearning._detect_time_pattern)
```

### 🔍 Objeto: `tipo`

#### `tipo.title` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:350 (em module.create_excel_summary)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:362 (em ExcelOrchestrator._fallback_tipo_indisponivel)
```

### 🔍 Objeto: `tipo_disp`

#### `tipo_disp.title` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:369 (em ExcelOrchestrator._fallback_tipo_indisponivel)
```

### 🔍 Objeto: `tipos_count`

#### `tipos_count.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:268 (em MetadataReader.obter_tipos_campo_disponiveis)
```

### 🔍 Objeto: `tipos_distribuicao`

#### `tipos_distribuicao.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:297 (em MetadataReader.obter_estatisticas_tabelas)
```

### 🔍 Objeto: `tipos_pergunta`

#### `tipos_pergunta.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:499 (em PatternLearner._classificar_tipo_pergunta)
```

### 🔍 Objeto: `todos_clientes`

#### `todos_clientes.add` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:505 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:512 (em ContextLoader._carregar_todos_clientes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:517 (em ContextLoader._carregar_todos_clientes_sistema)
```

### 🔍 Objeto: `token`

#### `token.text` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:219 (em NLPEnhancedAnalyzer._tokenizar_spacy)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:220 (em NLPEnhancedAnalyzer._tokenizar_spacy)
```

#### `token.text.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:219 (em NLPEnhancedAnalyzer._tokenizar_spacy)
```

#### `token.is_stop` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:220 (em NLPEnhancedAnalyzer._tokenizar_spacy)
```

#### `token.is_punct` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:220 (em NLPEnhancedAnalyzer._tokenizar_spacy)
```

### 🔍 Objeto: `tokens_usage`

#### `tokens_usage.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:156 (em PerformanceAnalyzer.analyze_ai_performance)
```

### 🔍 Objeto: `traceback`

#### `traceback.print_exc` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/detector_modulos_orfaos.py:404 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/simular_producao.py:107 (em ProductionSimulator.run_query)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:410 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_producao.py:49 (em module.verificar_configuracao)
```

#### `traceback.format_exc` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:40 (em module.testar_modulo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:204 (em TesteIntegracaoCompleta.testar_modulo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:447 (em module.main)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:79 (em ValidadorSistemaReal.test_basic_imports)
```

### 🔍 Objeto: `tracker`

#### `tracker.visit` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:115 (em UninitializedVariableFinder.scan_file)
```

#### `tracker.used_vars` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:120 (em UninitializedVariableFinder.scan_file)
```

#### `tracker.imports` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:143 (em UninitializedVariableFinder._is_suspicious_usage)
```

#### `tracker.assignments` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:161 (em UninitializedVariableFinder._is_suspicious_usage)
```

#### `tracker.defined_vars` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:171 (em UninitializedVariableFinder._is_suspicious_usage)
```

### 🔍 Objeto: `transformation`

#### `transformation.get` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:404 (em DataProcessor._apply_transformation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:407 (em DataProcessor._apply_transformation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:409 (em DataProcessor._apply_transformation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:411 (em DataProcessor._apply_transformation)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:411 (em DataProcessor._apply_transformation)
```

### 🔍 Objeto: `transition`

#### `transition.sistema_ativo` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_ativo.py:30 (em module.verificar_sistema_ativo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_ativo.py:32 (em module.verificar_sistema_ativo)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_ativo.py:35 (em module.verificar_sistema_ativo)
```

#### `transition.sistema_ativo.upper` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_ativo.py:30 (em module.verificar_sistema_ativo)
```

### 🔍 Objeto: `transportadora`

#### `transportadora.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:309 (em DataProvider._serialize_transportadora)
```

#### `transportadora.razao_social` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:310 (em DataProvider._serialize_transportadora)
```

#### `transportadora.cidade` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:311 (em DataProvider._serialize_transportadora)
```

#### `transportadora.uf` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:312 (em DataProvider._serialize_transportadora)
```

#### `transportadora.cnpj` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:313 (em DataProvider._serialize_transportadora)
```

#### `transportadora.freteiro` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/providers/data_provider.py:314 (em DataProvider._serialize_transportadora)
```

### 🔍 Objeto: `transportadoras`

#### `transportadoras.items` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:320 (em ExcelFretes._criar_aba_transportadoras)
```

### 🔍 Objeto: `tree`

#### `tree.body` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:103 (em CodeScanner._parse_forms_file)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:181 (em StructureScanner._parse_models_file)
```

### 🔍 Objeto: `trend`

#### `trend.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:738 (em IntelligenceProcessor._calculate_trend_strength)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:745 (em IntelligenceProcessor._determine_trend_direction)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:746 (em IntelligenceProcessor._determine_trend_direction)
```

### 🔍 Objeto: `type()`

#### `type().__name__` (21 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:323 (em TesteIntegracaoCompleta.testar_fallbacks_mocks)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_modulos_esquecidos.py:27 (em module.teste_modulos_esquecidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_modulos_esquecidos.py:47 (em module.teste_modulos_esquecidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_modulos_esquecidos.py:65 (em module.teste_modulos_esquecidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_modulos_esquecidos.py:83 (em module.teste_modulos_esquecidos)
  ... e mais 16 ocorrências
```

### 🔍 Objeto: `type_counts`

#### `type_counts.most_common` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:391 (em AdaptiveLearning._detect_query_pattern)
```

### 🔍 Objeto: `type_node`

#### `type_node.value` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:324 (em StructureScanner._extract_column_type)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:324 (em StructureScanner._extract_column_type)
```

#### `type_node.attr` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:324 (em StructureScanner._extract_column_type)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:324 (em StructureScanner._extract_column_type)
```

#### `type_node.func` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:328 (em StructureScanner._extract_column_type)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:329 (em StructureScanner._extract_column_type)
```

#### `type_node.value.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:324 (em StructureScanner._extract_column_type)
```

#### `type_node.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:326 (em StructureScanner._extract_column_type)
```

#### `type_node.func.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:329 (em StructureScanner._extract_column_type)
```

### 🔍 Objeto: `types`

#### `types.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:208 (em StructuralAnalyzer._analyze_data_types)
```

### 🔍 Objeto: `uf`

#### `uf.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/domain/pedidos_mapper.py:169 (em PedidosMapper.map_query_to_filters)
```

### 🔍 Objeto: `uf_code`

#### `uf_code.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:170 (em QueryAnalyzer._extract_entities)
```

### 🔍 Objeto: `undefined_methods`

#### `undefined_methods.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:169 (em module.find_undefined_methods)
```

### 🔍 Objeto: `unique_commands`

#### `unique_commands.values` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:327 (em AutoCommandProcessor._detect_commands)
```

### 🔍 Objeto: `unique_domains`

#### `unique_domains.update` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:533 (em PerformanceAnalyzer._generate_behavior_insights)
```

### 🔍 Objeto: `unittest`

#### `unittest.TestCase` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:21 (em TestLoopPrevention.top-level)
```

#### `unittest.TestLoader().loadTestsFromTestCase` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:254 (em module.run_pre_commit_tests)
```

#### `unittest.TestLoader` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:254 (em module.run_pre_commit_tests)
```

#### `unittest.TextTestRunner` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:257 (em module.run_pre_commit_tests)
```

### 🔍 Objeto: `uptime`

#### `uptime.days` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:376 (em SystemMemory._calculate_uptime)
```

#### `uptime.seconds` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:377 (em SystemMemory._calculate_uptime)
```

#### `uptime.total_seconds` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:248 (em ClaudeAIMetrics.get_usage_metrics)
```

### 🔍 Objeto: `uq`

#### `uq.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:233 (em MetadataReader._obter_constraints_tabela)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/metadata_reader.py:234 (em MetadataReader._obter_constraints_tabela)
```

### 🔍 Objeto: `use_new`

#### `use_new.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/verificar_sistema_ativo.py:18 (em module.verificar_sistema_ativo)
```

### 🔍 Objeto: `user`

#### `user.id` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:798 (em SessionOrchestrator._get_current_user_id)
```

### 🔍 Objeto: `user_behaviors`

#### `user_behaviors.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:286 (em PerformanceAnalyzer.analyze_user_behavior)
```

### 🔍 Objeto: `user_context`

#### `user_context.get` (11 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:190 (em SuggestionsEngine.get_intelligent_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:202 (em SuggestionsEngine.get_intelligent_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:231 (em SuggestionsEngine._generate_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:232 (em SuggestionsEngine._generate_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:233 (em SuggestionsEngine._generate_suggestions)
  ... e mais 6 ocorrências
```

#### `user_context.get().lower` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:231 (em SuggestionsEngine._generate_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:321 (em SuggestionsEngine._generate_data_based_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:489 (em SuggestionsEngine._get_fallback_suggestions)
```

### 🔍 Objeto: `user_feedback`

#### `user_feedback.lower().strip` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:130 (em MetacognitiveAnalyzer._interpret_user_feedback)
```

#### `user_feedback.lower` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:130 (em MetacognitiveAnalyzer._interpret_user_feedback)
```

### 🔍 Objeto: `user_profile`

#### `user_profile.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:276 (em SuggestionsManager.get_suggestion_recommendations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:658 (em SuggestionsManager._generate_personalized_suggestions)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/__init__.py:191 (em module.get_suggestion_recommendations)
```

### 🔍 Objeto: `user_question`

#### `user_question.lower` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:211 (em ConversationContext.extract_metadata)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:219 (em ConversationContext.extract_metadata)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:224 (em ConversationContext.extract_metadata)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:226 (em ConversationContext.extract_metadata)
```

### 🔍 Objeto: `utils`

#### `utils.validate` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:480 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:481 (em module.top-level)
```

#### `utils.validate_query` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:484 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:485 (em module.top-level)
```

#### `utils.validate_context` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:488 (em module.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:489 (em module.top-level)
```

### 🔍 Objeto: `uuid`

#### `uuid.uuid4` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:246 (em OrchestratorManager.top-level)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:240 (em SessionOrchestrator.create_session)
```

### 🔍 Objeto: `v`

#### `v.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:249 (em ProcessorCoordinator.get_active_chains)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:414 (em BaseValidationUtils.get_validation_summary)
```

### 🔍 Objeto: `valid_suggestions`

#### `valid_suggestions.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:309 (em SuggestionsEngine._validate_suggestions_list)
```

### 🔍 Objeto: `validacao`

#### `validacao.get` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:292 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:371 (em SemanticValidator._avaliar_qualidade_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:371 (em SemanticValidator._avaliar_qualidade_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:375 (em SemanticValidator._avaliar_qualidade_mapeamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:378 (em SemanticValidator._avaliar_qualidade_mapeamento)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `validador`

#### `validador.validar_sistema_completo` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:874 (em module.main)
```

#### `validador.salvar_resultados` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:877 (em module.main)
```

#### `validador.imprimir_resumo` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_completo.py:880 (em module.main)
```

#### `validador.executar_validacao` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:107 (em ClaudeAIMetrics.get_system_health_metrics)
```

### 🔍 Objeto: `validation_result`

#### `validation_result.get` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:327 (em CriticAgent._generate_recommendations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:328 (em CriticAgent._generate_recommendations)
```

### 🔍 Objeto: `validations_to_run`

#### `validations_to_run.append` (7 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:420 (em ValidatorManager.run_full_validation_suite)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:424 (em ValidatorManager.run_full_validation_suite)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:428 (em ValidatorManager.run_full_validation_suite)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:429 (em ValidatorManager.run_full_validation_suite)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:432 (em ValidatorManager.run_full_validation_suite)
  ... e mais 2 ocorrências
```

### 🔍 Objeto: `validator`

#### `validator.validate_responses` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:200 (em ValidatorManager.validate_agent_responses)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:219 (em ValidatorManager.validate_agent_responses)
```

#### `validator.validate_all_modules` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:476 (em module.top-level)
```

#### `validator.run_comprehensive_validation` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validador_sistema_real.py:398 (em module.main)
```

#### `validator.validar_consistencia_readme_banco` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:263 (em DiagnosticsAnalyzer._avaliar_integracao)
```

#### `validator.validate` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/utils/utils_manager.py:147 (em UtilsManager.validate)
```

#### `validator.validar_contexto_negocio` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:99 (em ValidatorManager.validate_context)
```

#### `validator.validar_mapeamento_completo` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:287 (em ValidatorManager.validate_complete_mapping)
```

#### `validator.__class__.__name__` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:365 (em ValidatorManager.get_validation_status)
```

#### `validator.__class__` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:365 (em ValidatorManager.get_validation_status)
```

### 🔍 Objeto: `validator_path`

#### `validator_path.exists` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:150 (em CursorMonitor.run_validator)
```

### 🔍 Objeto: `validator_result`

#### `validator_result.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:249 (em CursorMonitor.display_status)
```

### 🔍 Objeto: `validators`

#### `validators.append` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:197 (em CodeScanner._extract_validators)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:199 (em CodeScanner._extract_validators)
```

### 🔍 Objeto: `validators_node`

#### `validators_node.elts` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:194 (em CodeScanner._extract_validators)
```

### 🔍 Objeto: `valor`

#### `valor.upper` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:115 (em SemanticValidator.validar_contexto_negocio)
```

### 🔍 Objeto: `valor_match`

#### `valor_match.group().replace().replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:154 (em BaseCommand._extract_filters_advanced)
```

#### `valor_match.group().replace` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:154 (em BaseCommand._extract_filters_advanced)
```

#### `valor_match.group` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/base_command.py:154 (em BaseCommand._extract_filters_advanced)
```

### 🔍 Objeto: `value`

#### `value.strip` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:385 (em DataProcessor._clean_dict)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/data_processor.py:477 (em DataProcessor._normalize_dict)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:390 (em IntelligenceProcessor._normalize_dict_for_intelligence)
```

#### `value.startswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1171 (em MainOrchestrator._resolve_parameters)
```

#### `value.endswith` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1171 (em MainOrchestrator._resolve_parameters)
```

#### `value.value` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:213 (em CodeScanner._extract_dict_value)
```

### 🔍 Objeto: `value_node`

#### `value_node.func` (8 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:170 (em CodeScanner._extract_form_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:171 (em CodeScanner._extract_form_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:172 (em CodeScanner._extract_form_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:173 (em CodeScanner._extract_form_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:272 (em StructureScanner._extract_field_info)
  ... e mais 3 ocorrências
```

#### `value_node.value` (6 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:236 (em CodeScanner._extract_simple_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:338 (em StructureScanner._extract_boolean_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:340 (em StructureScanner._extract_boolean_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:349 (em StructureScanner._extract_string_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:360 (em StructureScanner._extract_value)
  ... e mais 1 ocorrências
```

#### `value_node.args` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:278 (em StructureScanner._extract_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:279 (em StructureScanner._extract_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:294 (em StructureScanner._extract_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:295 (em StructureScanner._extract_field_info)
```

#### `value_node.keywords` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:176 (em CodeScanner._extract_form_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:283 (em StructureScanner._extract_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:302 (em StructureScanner._extract_field_info)
```

#### `value_node.s` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:238 (em CodeScanner._extract_simple_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:351 (em StructureScanner._extract_string_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:362 (em StructureScanner._extract_value)
```

#### `value_node.func.id` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:171 (em CodeScanner._extract_form_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:313 (em StructureScanner._extract_field_info)
```

#### `value_node.func.attr` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:173 (em CodeScanner._extract_form_field_info)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:273 (em StructureScanner._extract_field_info)
```

#### `value_node.n` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:240 (em CodeScanner._extract_simple_value)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:364 (em StructureScanner._extract_value)
```

### 🔍 Objeto: `var_name`

#### `var_name.startswith` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:182 (em UninitializedVariableFinder._identify_pattern)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:98 (em FileScanner._extract_template_variables)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:98 (em FileScanner._extract_template_variables)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:114 (em FileScanner._extract_template_variables)
```

### 🔍 Objeto: `variables`

#### `variables.add` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:99 (em FileScanner._extract_template_variables)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:107 (em FileScanner._extract_template_variables)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:115 (em FileScanner._extract_template_variables)
```

### 🔍 Objeto: `violations`

#### `violations.append` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:104 (em StructuralAnalyzer.validate_architecture)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:108 (em StructuralAnalyzer.validate_architecture)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:112 (em StructuralAnalyzer.validate_architecture)
```

### 🔍 Objeto: `visitadas`

#### `visitadas.add` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:323 (em RelationshipMapper._explorar_cluster)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:391 (em RelationshipMapper.obter_caminho_relacionamentos)
```

### 🔍 Objeto: `visitor`

#### `visitor.visit` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:101 (em module.analyze_file)
```

#### `visitor.method_calls` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:105 (em module.analyze_file)
```

#### `visitor.defined_methods` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:106 (em module.analyze_file)
```

#### `visitor.imported_names` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:107 (em module.analyze_file)
```

### 🔍 Objeto: `vocabulario_dominio`

#### `vocabulario_dominio.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:395 (em PatternLearner._extrair_palavras_chave_dominio)
```

### 🔍 Objeto: `w`

#### `w.isupper` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:55 (em MetacognitiveAnalyzer._assess_query_complexity)
```

### 🔍 Objeto: `wb`

#### `wb.create_sheet` (15 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:256 (em ExcelOrchestrator._gerar_excel_geral_multi)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:265 (em ExcelOrchestrator._gerar_excel_geral_multi)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:274 (em ExcelOrchestrator._gerar_excel_geral_multi)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:282 (em ExcelOrchestrator._gerar_excel_geral_multi)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:173 (em ExcelEntregas._criar_excel_entregas)
  ... e mais 10 ocorrências
```

#### `wb.active` (10 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:248 (em ExcelOrchestrator._gerar_excel_geral_multi)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:249 (em ExcelOrchestrator._gerar_excel_geral_multi)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:169 (em ExcelEntregas._criar_excel_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:170 (em ExcelEntregas._criar_excel_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:142 (em ExcelFaturamento._criar_excel_faturamento)
  ... e mais 5 ocorrências
```

#### `wb.remove` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:249 (em ExcelOrchestrator._gerar_excel_geral_multi)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:170 (em ExcelEntregas._criar_excel_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:143 (em ExcelFaturamento._criar_excel_faturamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:161 (em ExcelFretes._criar_excel_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:208 (em ExcelPedidos._criar_excel_pedidos)
```

#### `wb.save` (5 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:290 (em ExcelOrchestrator._gerar_excel_geral_multi)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:188 (em ExcelEntregas._criar_excel_entregas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:157 (em ExcelFaturamento._criar_excel_faturamento)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:179 (em ExcelFretes._criar_excel_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:226 (em ExcelPedidos._criar_excel_pedidos)
```

### 🔍 Objeto: `weaknesses`

#### `weaknesses.append` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:687 (em IntelligenceProcessor._evaluate_option)
```

### 🔍 Objeto: `weekly_feedback`

#### `weekly_feedback.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:358 (em HumanInLoopLearning._analyze_trends)
```

#### `weekly_feedback.keys` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:361 (em HumanInLoopLearning._analyze_trends)
```

### 🔍 Objeto: `weights`

#### `weights.get` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:406 (em HumanInLoopLearning._calculate_satisfaction_score)
```

### 🔍 Objeto: `word`

#### `word.upper` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:166 (em QueryAnalyzer._extract_entities)
```

### 🔍 Objeto: `workflow`

#### `workflow.copy` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:870 (em MainOrchestrator.top-level)
```

### 🔍 Objeto: `workflow_data`

#### `workflow_data.get` (10 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:427 (em SessionOrchestrator._execute_learning_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:427 (em SessionOrchestrator._execute_learning_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:428 (em SessionOrchestrator._execute_learning_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:428 (em SessionOrchestrator._execute_learning_workflow)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:430 (em SessionOrchestrator._execute_learning_workflow)
  ... e mais 5 ocorrências
```

### 🔍 Objeto: `workflow_orch`

#### `workflow_orch.executar_workflow` (1 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/teste_integracao_completa.py:96 (em module.teste_sistema_basico)
```

### 🔍 Objeto: `ws`

#### `ws.cell` (127 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:325 (em ExcelOrchestrator._criar_aba_resumo_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:326 (em ExcelOrchestrator._criar_aba_resumo_fretes)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:331 (em ExcelOrchestrator._criar_aba_resumo_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:332 (em ExcelOrchestrator._criar_aba_resumo_pedidos)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:337 (em ExcelOrchestrator._criar_aba_resumo_entregas)
  ... e mais 122 ocorrências
```

#### `ws.columns` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:438 (em ExcelEntregas._auto_ajustar_colunas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:293 (em ExcelFaturamento._auto_ajustar_colunas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:404 (em ExcelFretes._auto_ajustar_colunas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:436 (em ExcelPedidos._auto_ajustar_colunas)
```

#### `ws.column_dimensions` (4 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:450 (em ExcelEntregas._auto_ajustar_colunas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:305 (em ExcelFaturamento._auto_ajustar_colunas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:416 (em ExcelFretes._auto_ajustar_colunas)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:448 (em ExcelPedidos._auto_ajustar_colunas)
```

### 🔍 Objeto: `x`

#### `x.get` (3 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:838 (em IntelligenceCoordinator._best_result_synthesis)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:486 (em AdaptiveLearning._rank_recommendations)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:456 (em SuggestionsManager._prioritize_suggestions)
```

#### `x.priority` (2 ocorrências)
```
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/mappers/context_mapper.py:87 (em ContextMapper.map_context)
  C:/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:263 (em SuggestionsEngine._generate_suggestions)
```


## 🎯 PROBLEMAS CONHECIDOS IDENTIFICADOS

- **orchestrator.obter_readers**: Método não existe - verificar implementação
- **orchestrator.verificar_saude_sistema**: Método não existe - verificar implementação
- **readme_reader**: Objeto pode não existir - adicionar verificação
- **database_reader**: Objeto pode não existir - adicionar verificação