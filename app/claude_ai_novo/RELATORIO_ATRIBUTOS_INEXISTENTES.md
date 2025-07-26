# 🔍 RELATÓRIO DE ATRIBUTOS INEXISTENTES

**Data**: 2025-07-25T22:10:00.287869
**Arquivos analisados**: 173
**Total de acessos**: 13894
**Classes definidas**: 200
**Atributos suspeitos**: 7660

## 📋 ATRIBUTOS POTENCIALMENTE INEXISTENTES

### 🔍 Objeto: `AgendamentoEntrega`

#### `AgendamentoEntrega.entrega_id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:90 (em AgendamentosLoader._load_with_context)
```

#### `AgendamentoEntrega.status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:101 (em AgendamentosLoader._load_with_context)
```

### 🔍 Objeto: `AgentType`

#### `AgentType.FRETES` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:125 (em CoordinatorManager._load_specialist_coordinator)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/specialist_agents.py:46 (em SpecialistAgent.__new__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/fretes_agent.py:22 (em FretesAgent.__init__)
```

#### `AgentType.ENTREGAS` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/specialist_agents.py:45 (em SpecialistAgent.__new__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:21 (em EntregasAgent.__init__)
```

#### `AgentType.PEDIDOS` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/specialist_agents.py:47 (em SpecialistAgent.__new__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/pedidos_agent.py:22 (em PedidosAgent.__init__)
```

#### `AgentType.EMBARQUES` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/specialist_agents.py:48 (em SpecialistAgent.__new__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/embarques_agent.py:22 (em EmbarquesAgent.__init__)
```

#### `AgentType.FINANCEIRO` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/specialist_agents.py:49 (em SpecialistAgent.__new__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/financeiro_agent.py:22 (em FinanceiroAgent.__init__)
```

### 🔍 Objeto: `ClaudeAPIClient`

#### `ClaudeAPIClient.from_environment` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:217 (em ExternalAPIIntegration._initialize_clients)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:466 (em module.get_claude_client)
```

#### `ClaudeAPIClient.from_mode` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:483 (em module.create_claude_client)
```

### 🔍 Objeto: `Embarque`

#### `Embarque.data_embarque` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:229 (em DataProvider._get_embarques_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:231 (em DataProvider._get_embarques_data)
```

#### `Embarque.status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:227 (em DataProvider._get_embarques_data)
```

#### `Embarque.transportadora_id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:101 (em EmbarquesLoader._load_with_context)
```

### 🔍 Objeto: `EntregaMonitorada`

#### `EntregaMonitorada.cliente` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:541 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:543 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:544 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:602 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:605 (em ContextLoader._carregar_todos_clientes_sistema)
  ... e mais 3 ocorrências
```

#### `EntregaMonitorada.data_embarque` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:294 (em ContextProcessor._carregar_dados_entregas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:604 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:177 (em DataProvider._get_entregas_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:179 (em DataProvider._get_entregas_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:211 (em EntregasLoader._load_with_app_context)
  ... e mais 2 ocorrências
```

#### `EntregaMonitorada.nome_cliente.ilike` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:289 (em ContextProcessor._carregar_dados_entregas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:200 (em EntregasLoader._load_with_app_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:97 (em AgendamentosLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:129 (em ExcelEntregas._buscar_dados_entregas)
```

#### `EntregaMonitorada.nome_cliente` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:289 (em ContextProcessor._carregar_dados_entregas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:200 (em EntregasLoader._load_with_app_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:97 (em AgendamentosLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:129 (em ExcelEntregas._buscar_dados_entregas)
```

#### `EntregaMonitorada.data_entrega_prevista` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:149 (em ExcelEntregas._buscar_dados_entregas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:161 (em ExcelEntregas._buscar_dados_entregas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:162 (em ExcelEntregas._buscar_dados_entregas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:168 (em ExcelEntregas._buscar_dados_entregas)
```

#### `EntregaMonitorada.cliente.ilike` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:173 (em DataProvider._get_entregas_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:204 (em EntregasLoader._load_with_app_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:176 (em AgendamentosLoader._build_agendamentos_query)
```

#### `EntregaMonitorada.entregue` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:141 (em ExcelEntregas._buscar_dados_entregas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:143 (em ExcelEntregas._buscar_dados_entregas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:148 (em ExcelEntregas._buscar_dados_entregas)
```

#### `EntregaMonitorada.id` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:90 (em AgendamentosLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:168 (em ExcelEntregas._buscar_dados_entregas)
```

#### `EntregaMonitorada.status_finalizacao` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:175 (em DataProvider._get_entregas_data)
```

#### `EntregaMonitorada.uf_destino` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:136 (em ExcelEntregas._buscar_dados_entregas)
```

#### `EntregaMonitorada.data_entrega_prevista.desc` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:168 (em ExcelEntregas._buscar_dados_entregas)
```

#### `EntregaMonitorada.id.desc` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:168 (em ExcelEntregas._buscar_dados_entregas)
```

### 🔍 Objeto: `FeedbackSeverity`

#### `FeedbackSeverity.CRITICAL` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:109 (em HumanInLoopLearning.capture_feedback)
```

### 🔍 Objeto: `FeedbackType`

#### `FeedbackType.NEGATIVE` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:155 (em HumanInLoopLearning._analyze_feedback_patterns)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:406 (em HumanInLoopLearning._calculate_satisfaction_score)
```

#### `FeedbackType.CORRECTION` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:155 (em HumanInLoopLearning._analyze_feedback_patterns)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:405 (em HumanInLoopLearning._calculate_satisfaction_score)
```

#### `FeedbackType.POSITIVE` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:403 (em HumanInLoopLearning._calculate_satisfaction_score)
```

#### `FeedbackType.IMPROVEMENT` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:404 (em HumanInLoopLearning._calculate_satisfaction_score)
```

#### `FeedbackType.BUG_REPORT` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:407 (em HumanInLoopLearning._calculate_satisfaction_score)
```

### 🔍 Objeto: `FieldType`

#### `FieldType.STRING` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:147 (em FieldMapper.create_pedidos_mapping)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:148 (em FieldMapper.create_pedidos_mapping)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:151 (em FieldMapper.create_pedidos_mapping)
```

#### `FieldType.FLOAT` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:149 (em FieldMapper.create_pedidos_mapping)
```

#### `FieldType.DATE` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:150 (em FieldMapper.create_pedidos_mapping)
```

### 🔍 Objeto: `Frete`

#### `Frete.nome_cliente.ilike` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:326 (em ContextProcessor._carregar_dados_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:105 (em FretesLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:131 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.nome_cliente` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:326 (em ContextProcessor._carregar_dados_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:105 (em FretesLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:131 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.data_cotacao` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:331 (em ContextProcessor._carregar_dados_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:306 (em DataProvider._get_fretes_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:308 (em DataProvider._get_fretes_data)
```

#### `Frete.data_embarque` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:150 (em ExcelFretes._buscar_dados_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:151 (em ExcelFretes._buscar_dados_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:159 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.numero_cte` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:143 (em ExcelFretes._buscar_dados_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:145 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.transportadora.ilike` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:302 (em DataProvider._get_fretes_data)
```

#### `Frete.transportadora` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:302 (em DataProvider._get_fretes_data)
```

#### `Frete.status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:304 (em DataProvider._get_fretes_data)
```

#### `Frete.transportadora_id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:97 (em FretesLoader._load_with_context)
```

#### `Frete.razao_social_cliente.ilike` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:132 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.razao_social_cliente` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:132 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.uf_destino` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:138 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.numero_cte.is_` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:143 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.numero_cte.isnot` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:145 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.valor_cotado` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:156 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.data_embarque.desc` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:159 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.id.desc` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:159 (em ExcelFretes._buscar_dados_fretes)
```

#### `Frete.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:159 (em ExcelFretes._buscar_dados_fretes)
```

### 🔍 Objeto: `LoaderManager`

#### `LoaderManager._is_initialized` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:47 (em LoaderManager.__init__)
```

### 🔍 Objeto: `OrchestrationMode`

#### `OrchestrationMode.INTELLIGENT` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:157 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:203 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:777 (em module.top-level)
```

#### `OrchestrationMode.SEQUENTIAL` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:949 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:972 (em MainOrchestrator.top-level)
```

#### `OrchestrationMode.PARALLEL` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:974 (em MainOrchestrator.top-level)
```

#### `OrchestrationMode.ADAPTIVE` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:976 (em MainOrchestrator.top-level)
```

### 🔍 Objeto: `OrchestratorType`

#### `OrchestratorType.MAIN` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:101 (em OrchestratorManager._initialize_orchestrators)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:424 (em OrchestratorManager._detect_appropriate_orchestrator)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:426 (em OrchestratorManager._detect_appropriate_orchestrator)
```

#### `OrchestratorType.SESSION` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:108 (em OrchestratorManager._initialize_orchestrators)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:407 (em OrchestratorManager._detect_appropriate_orchestrator)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:452 (em OrchestratorManager.top-level)
```

#### `OrchestratorType.WORKFLOW` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:115 (em OrchestratorManager._initialize_orchestrators)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:408 (em OrchestratorManager._detect_appropriate_orchestrator)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:454 (em OrchestratorManager.top-level)
```

### 🔍 Objeto: `Path()`

#### `Path().parent` (18 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:14 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:271 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:230 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:316 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:17 (em DependencyChecker.__init__)
  ... e mais 13 ocorrências
```

#### `Path().parent.parent` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:29 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:381 (em module.get_file_scanner)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:42 (em ScanningManager.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:381 (em module.get_code_scanner)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:396 (em module.get_structure_scanner)
  ... e mais 1 ocorrências
```

#### `Path().parts` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:154 (em module.contar_linhas_codigo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:189 (em module.verificar_modulos_especiais)
```

#### `Path().relative_to` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:236 (em UninitializedVariableFinder.generate_report)
```

#### `Path().absolute` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:313 (em module.main)
```

#### `Path().stat().st_mtime` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:195 (em CircularDependencyMapper.generate_report)
```

#### `Path().stat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:195 (em CircularDependencyMapper.generate_report)
```

#### `Path().parent.parent.parent.parent` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:29 (em module.top-level)
```

#### `Path().parent.parent.parent` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:29 (em module.top-level)
```

### 🔍 Objeto: `Pedido`

#### `Pedido.data_pedido` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:368 (em ContextProcessor._carregar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:204 (em DataProvider._get_pedidos_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:206 (em DataProvider._get_pedidos_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:192 (em ExcelPedidos._buscar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:193 (em ExcelPedidos._buscar_dados_pedidos)
  ... e mais 3 ocorrências
```

#### `Pedido.nf_cd` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:153 (em ExcelPedidos._buscar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:159 (em ExcelPedidos._buscar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:167 (em ExcelPedidos._buscar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:172 (em ExcelPedidos._buscar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:179 (em ExcelPedidos._buscar_dados_pedidos)
  ... e mais 1 ocorrências
```

#### `Pedido.raz_social_red` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:363 (em ContextProcessor._carregar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:549 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:551 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:552 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:140 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.nf` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:157 (em ExcelPedidos._buscar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:158 (em ExcelPedidos._buscar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:166 (em ExcelPedidos._buscar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:166 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.data_embarque` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:165 (em ExcelPedidos._buscar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:171 (em ExcelPedidos._buscar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:178 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.raz_social_red.ilike` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:363 (em ContextProcessor._carregar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:140 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.cliente.ilike` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:200 (em DataProvider._get_pedidos_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:93 (em PedidosLoader._load_with_context)
```

#### `Pedido.cliente` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:200 (em DataProvider._get_pedidos_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:93 (em PedidosLoader._load_with_context)
```

#### `Pedido.data_embarque.isnot` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:165 (em ExcelPedidos._buscar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:171 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.cotacao_id` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:177 (em ExcelPedidos._buscar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:184 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:202 (em DataProvider._get_pedidos_data)
```

#### `Pedido.cnpj_cpf.ilike` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:141 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.cnpj_cpf` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:141 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.cod_uf` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:147 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.nf.isnot` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:157 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.nf.is_` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:166 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.cotacao_id.isnot` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:177 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.data_embarque.is_` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:178 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.cotacao_id.is_` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:184 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.valor_saldo_total` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:203 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.data_pedido.desc` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:206 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.id.desc` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:206 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:206 (em ExcelPedidos._buscar_dados_pedidos)
```

#### `Pedido.nome_cliente.ilike` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:130 (em ExcelEntregas._buscar_dados_entregas)
```

#### `Pedido.nome_cliente` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:130 (em ExcelEntregas._buscar_dados_entregas)
```

### 🔍 Objeto: `PendenciaFinanceiraNF`

#### `PendenciaFinanceiraNF.nome_cliente.ilike` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:400 (em ContextProcessor._carregar_dados_financeiro)
```

#### `PendenciaFinanceiraNF.nome_cliente` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:400 (em ContextProcessor._carregar_dados_financeiro)
```

### 🔍 Objeto: `QueryType`

#### `QueryType.SQL` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:53 (em QueryMapper._setup_default_mappings)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:60 (em QueryMapper._setup_default_mappings)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:79 (em QueryMapper.map_query)
```

#### `QueryType.NATURAL_LANGUAGE` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:52 (em QueryMapper._setup_default_mappings)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:59 (em QueryMapper._setup_default_mappings)
```

### 🔍 Objeto: `RelatorioFaturamentoImportado`

#### `RelatorioFaturamentoImportado.nome_cliente` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:532 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:535 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:536 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:252 (em DataProvider._get_faturamento_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:93 (em FaturamentoLoader._load_with_context)
  ... e mais 1 ocorrências
```

#### `RelatorioFaturamentoImportado.data_fatura` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:254 (em DataProvider._get_faturamento_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:256 (em DataProvider._get_faturamento_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:132 (em ExcelFaturamento._buscar_dados_faturamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:133 (em ExcelFaturamento._buscar_dados_faturamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:141 (em ExcelFaturamento._buscar_dados_faturamento)
```

#### `RelatorioFaturamentoImportado.nome_cliente.ilike` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:252 (em DataProvider._get_faturamento_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:93 (em FaturamentoLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:127 (em ExcelFaturamento._buscar_dados_faturamento)
```

#### `RelatorioFaturamentoImportado.cnpj_cliente` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:533 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:97 (em FaturamentoLoader._load_with_context)
```

#### `RelatorioFaturamentoImportado.valor_total` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:138 (em ExcelFaturamento._buscar_dados_faturamento)
```

#### `RelatorioFaturamentoImportado.data_fatura.desc` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:141 (em ExcelFaturamento._buscar_dados_faturamento)
```

#### `RelatorioFaturamentoImportado.id.desc` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:141 (em ExcelFaturamento._buscar_dados_faturamento)
```

#### `RelatorioFaturamentoImportado.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:141 (em ExcelFaturamento._buscar_dados_faturamento)
```

### 🔍 Objeto: `SessionPriority`

#### `SessionPriority.NORMAL` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:479 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:74 (em SessionContext.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:197 (em SessionOrchestrator.create_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:1065 (em module.create_ai_session)
```

#### `SessionPriority.HIGH` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:473 (em OrchestratorManager.top-level)
```

#### `SessionPriority.LOW` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:475 (em OrchestratorManager.top-level)
```

#### `SessionPriority.CRITICAL` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:477 (em OrchestratorManager.top-level)
```

### 🔍 Objeto: `SessionStatus`

#### `SessionStatus.ACTIVE` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:89 (em SessionContext.is_active)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:292 (em SessionOrchestrator.initialize_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:364 (em SessionOrchestrator.execute_session_workflow)
```

#### `SessionStatus.PROCESSING` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:89 (em SessionContext.is_active)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:340 (em SessionOrchestrator.execute_session_workflow)
```

#### `SessionStatus.FAILED` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:309 (em SessionOrchestrator.initialize_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:381 (em SessionOrchestrator.execute_session_workflow)
```

#### `SessionStatus.CREATED` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:73 (em SessionContext.top-level)
```

#### `SessionStatus.WAITING_INPUT` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:89 (em SessionContext.is_active)
```

#### `SessionStatus.INITIALIZING` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:281 (em SessionOrchestrator.initialize_session)
```

#### `SessionStatus.COMPLETED` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:531 (em SessionOrchestrator.complete_session)
```

#### `SessionStatus.TERMINATED` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:579 (em SessionOrchestrator.terminate_session)
```

### 🔍 Objeto: `Transportadora`

#### `Transportadora.razao_social.ilike` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:277 (em DataProvider._get_transportadoras_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:103 (em EmbarquesLoader._load_with_context)
```

#### `Transportadora.razao_social` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:277 (em DataProvider._get_transportadoras_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:103 (em EmbarquesLoader._load_with_context)
```

#### `Transportadora.id` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:97 (em FretesLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:101 (em EmbarquesLoader._load_with_context)
```

#### `Transportadora.cidade.ilike` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:279 (em DataProvider._get_transportadoras_data)
```

#### `Transportadora.cidade` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:279 (em DataProvider._get_transportadoras_data)
```

#### `Transportadora.uf` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:281 (em DataProvider._get_transportadoras_data)
```

### 🔍 Objeto: `__all__`

#### `__all__.extend` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:328 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:335 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:338 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:341 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:344 (em module.top-level)
  ... e mais 2 ocorrências
```

### 🔍 Objeto: `__import__()`

#### `__import__().datetime.now` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:284 (em DependencyChecker._create_markdown_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/__init__.py:347 (em module.export_config)
```

#### `__import__().datetime` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:284 (em DependencyChecker._create_markdown_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/__init__.py:347 (em module.export_config)
```

#### `__import__().datetime.now().strftime` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:284 (em DependencyChecker._create_markdown_report)
```

### 🔍 Objeto: `_cache_store`

#### `_cache_store.keys` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/performance_cache.py:54 (em module.cached_result)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/performance_cache.py:119 (em module.get_cache_stats)
```

#### `_cache_store.values` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/performance_cache.py:120 (em module.get_cache_stats)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/performance_cache.py:121 (em module.get_cache_stats)
```

### 🔍 Objeto: `_claude_ai_instance`

#### `_claude_ai_instance.initialize_system` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:354 (em module.get_claude_ai_instance)
```

### 🔍 Objeto: `_commands_registry`

#### `_commands_registry.discover_commands` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:165 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:240 (em module.get_available_commands)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:316 (em module.reset_commands_cache)
```

#### `_commands_registry.get_available_commands` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:241 (em module.get_available_commands)
```

#### `_commands_registry.get_status_report` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:290 (em module.get_commands_info)
```

### 🔍 Objeto: `_components`

#### `_components.get` (29 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/__init__.py:35 (em module.get_conversation_manager)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/__init__.py:49 (em module.get_conversation_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/__init__.py:63 (em module.get_learning_core)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/__init__.py:77 (em module.get_human_in_loop_learning)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/__init__.py:91 (em module.get_lifelong_learning)
  ... e mais 24 ocorrências
```

#### `_components.keys` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/__init__.py:175 (em module.get_system_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/__init__.py:200 (em module.diagnose_orchestrator_module)
```

### 🔍 Objeto: `_field_mapper`

#### `_field_mapper.create_pedidos_mapping` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:170 (em module.get_field_mapper)
```

### 🔍 Objeto: `_global_instances`

#### `_global_instances.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/__init__.py:293 (em module.get_global_instance)
```

### 🔍 Objeto: `a`

#### `a.data_agendada` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:112 (em AgendamentosLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:112 (em AgendamentosLoader._load_with_context)
```

#### `a.confirmado_em` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:116 (em AgendamentosLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:116 (em AgendamentosLoader._load_with_context)
```

#### `a.criado_em` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:119 (em AgendamentosLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:119 (em AgendamentosLoader._load_with_context)
```

#### `a.entrega` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:122 (em AgendamentosLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:123 (em AgendamentosLoader._load_with_context)
```

#### `a.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:110 (em AgendamentosLoader._load_with_context)
```

#### `a.entrega_id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:111 (em AgendamentosLoader._load_with_context)
```

#### `a.data_agendada.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:112 (em AgendamentosLoader._load_with_context)
```

#### `a.periodo` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:113 (em AgendamentosLoader._load_with_context)
```

#### `a.status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:114 (em AgendamentosLoader._load_with_context)
```

#### `a.confirmado_por` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:115 (em AgendamentosLoader._load_with_context)
```

#### `a.confirmado_em.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:116 (em AgendamentosLoader._load_with_context)
```

#### `a.observacoes` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:117 (em AgendamentosLoader._load_with_context)
```

#### `a.observacoes_confirmacao` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:118 (em AgendamentosLoader._load_with_context)
```

#### `a.criado_em.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:119 (em AgendamentosLoader._load_with_context)
```

#### `a.criado_por` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:120 (em AgendamentosLoader._load_with_context)
```

#### `a.entrega.nome_cliente` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:122 (em AgendamentosLoader._load_with_context)
```

#### `a.entrega.numero_nf` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:123 (em AgendamentosLoader._load_with_context)
```

### 🔍 Objeto: `acao`

#### `acao.action_type` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:156 (em FeedbackProcessor.processar_feedback_completo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:297 (em FeedbackProcessor.aplicar_acao_corretiva)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:300 (em FeedbackProcessor.aplicar_acao_corretiva)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:303 (em FeedbackProcessor.aplicar_acao_corretiva)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:306 (em FeedbackProcessor.aplicar_acao_corretiva)
  ... e mais 2 ocorrências
```

#### `acao.description` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:158 (em FeedbackProcessor.processar_feedback_completo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:479 (em FeedbackProcessor._aplicar_update_mapping)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:485 (em FeedbackProcessor._aplicar_improve_search)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:491 (em FeedbackProcessor._aplicar_enhance_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:497 (em FeedbackProcessor._aplicar_adjust_parameters)
```

#### `acao.confidence` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:152 (em FeedbackProcessor.processar_feedback_completo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:159 (em FeedbackProcessor.processar_feedback_completo)
```

#### `acao.target_component` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:157 (em FeedbackProcessor.processar_feedback_completo)
```

### 🔍 Objeto: `acoes`

#### `acoes.extend` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:265 (em FeedbackProcessor.extrair_acoes_corretivas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:268 (em FeedbackProcessor.extrair_acoes_corretivas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:271 (em FeedbackProcessor.extrair_acoes_corretivas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:275 (em FeedbackProcessor.extrair_acoes_corretivas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:278 (em FeedbackProcessor.extrair_acoes_corretivas)
  ... e mais 1 ocorrências
```

#### `acoes.append` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:406 (em FeedbackProcessor._gerar_acoes_correcao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:421 (em FeedbackProcessor._gerar_acoes_melhoria)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:436 (em FeedbackProcessor._gerar_acoes_clarificacao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:450 (em FeedbackProcessor._gerar_acoes_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:464 (em FeedbackProcessor._gerar_acoes_busca)
```

### 🔍 Objeto: `active_list`

#### `active_list.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:308 (em ConversationManager.get_active_conversations)
```

### 🔍 Objeto: `active_sessions`

#### `active_sessions.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:222 (em ContextMemory.get_active_sessions)
```

### 🔍 Objeto: `adaptations`

#### `adaptations.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:411 (em AdaptiveLearning._apply_adaptations)
```

### 🔍 Objeto: `adjustments`

#### `adjustments.append` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:518 (em AdaptiveLearning._handle_negative_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:522 (em AdaptiveLearning._handle_negative_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:533 (em AdaptiveLearning._handle_positive_feedback)
```

### 🔍 Objeto: `advanced_config`

#### `advanced_config.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/__init__.py:168 (em module.get_config)
```

#### `advanced_config.set` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/__init__.py:220 (em module.set_config)
```

### 🔍 Objeto: `agent`

#### `agent.process_query` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:273 (em CoordinatorManager._process_with_coordinator)
```

### 🔍 Objeto: `agent_classes`

#### `agent_classes.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/specialist_agents.py:52 (em SpecialistAgent.__new__)
```

### 🔍 Objeto: `agent_name`

#### `agent_name.value` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:148 (em SmartBaseAgent._conectar_integration_manager)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:158 (em SmartBaseAgent._conectar_integration_manager)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:167 (em SmartBaseAgent._conectar_integration_manager)
```

### 🔍 Objeto: `aggregations`

#### `aggregations.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:267 (em DataProcessor.aggregate_data)
```

### 🔍 Objeto: `ai_response`

#### `ai_response.lower` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:211 (em ConversationContext.extract_metadata)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:219 (em ConversationContext.extract_metadata)
```

### 🔍 Objeto: `alias`

#### `alias.asname` (14 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:30 (em MethodCallVisitor.visit_Import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:30 (em MethodCallVisitor.visit_Import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:37 (em MethodCallVisitor.visit_ImportFrom)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:37 (em MethodCallVisitor.visit_ImportFrom)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:29 (em VariableTracker.visit_Import)
  ... e mais 9 ocorrências
```

#### `alias.name` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:30 (em MethodCallVisitor.visit_Import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:37 (em MethodCallVisitor.visit_ImportFrom)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:29 (em VariableTracker.visit_Import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:36 (em VariableTracker.visit_ImportFrom)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:40 (em DependencyAnalyzer.visit_Import)
  ... e mais 6 ocorrências
```

### 🔍 Objeto: `all_content`

#### `all_content.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:292 (em ConversationContext.get_context_summary)
```

### 🔍 Objeto: `all_defined_methods`

#### `all_defined_methods.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:148 (em module.find_undefined_methods)
```

### 🔍 Objeto: `all_inconsistencies`

#### `all_inconsistencies.extend` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:91 (em CriticAgent.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:92 (em CriticAgent.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:93 (em CriticAgent.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:94 (em CriticAgent.top-level)
```

### 🔍 Objeto: `all_insights`

#### `all_insights.extend` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:623 (em IntelligenceProcessor._comprehensive_synthesis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:680 (em IntelligenceCoordinator._create_simple_consensus)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:682 (em IntelligenceCoordinator._create_simple_consensus)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:859 (em IntelligenceCoordinator._combine_all_insights)
```

### 🔍 Objeto: `all_method_calls`

#### `all_method_calls.extend` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:147 (em module.find_undefined_methods)
```

### 🔍 Objeto: `all_problems`

#### `all_problems.extend` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:175 (em module.find_real_problems)
```

### 🔍 Objeto: `all_suggestions`

#### `all_suggestions.extend` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:122 (em SuggestionsManager.generate_suggestions)
```

### 🔍 Objeto: `analise`

#### `analise.get` (75 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:130 (em ResponseProcessor._obter_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:134 (em ResponseProcessor._obter_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:137 (em ResponseProcessor._obter_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:286 (em ResponseProcessor._construir_prompt_otimizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:287 (em ResponseProcessor._construir_prompt_otimizado)
  ... e mais 70 ocorrências
```

#### `analise.confianca` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:410 (em FeedbackProcessor._gerar_acoes_correcao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:425 (em FeedbackProcessor._gerar_acoes_melhoria)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:440 (em FeedbackProcessor._gerar_acoes_clarificacao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:454 (em FeedbackProcessor._gerar_acoes_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:468 (em FeedbackProcessor._gerar_acoes_busca)
  ... e mais 1 ocorrências
```

#### `analise.tipo` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:264 (em FeedbackProcessor.extrair_acoes_corretivas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:267 (em FeedbackProcessor.extrair_acoes_corretivas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:270 (em FeedbackProcessor.extrair_acoes_corretivas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:506 (em FeedbackProcessor._salvar_feedback_analise)
```

#### `analise.categoria` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:274 (em FeedbackProcessor.extrair_acoes_corretivas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:277 (em FeedbackProcessor.extrair_acoes_corretivas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:405 (em FeedbackProcessor._gerar_acoes_correcao)
```

#### `analise.acoes_sugeridas` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:405 (em FeedbackProcessor._gerar_acoes_correcao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:424 (em FeedbackProcessor._gerar_acoes_melhoria)
```

### 🔍 Objeto: `analise_completa`

#### `analise_completa.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:96 (em DataAnalyzer.analisar_dados_reais)
```

### 🔍 Objeto: `analise_dados`

#### `analise_dados.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:415 (em AutoMapper._melhorar_termos_com_analise)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:441 (em AutoMapper._melhorar_termos_com_analise)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:472 (em AutoMapper._ajustar_confianca_com_analise)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:479 (em AutoMapper._ajustar_confianca_com_analise)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:484 (em AutoMapper._ajustar_confianca_com_analise)
```

### 🔍 Objeto: `analysis`

#### `analysis.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:80 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:81 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:87 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:94 (em module.run_complete_flow)
```

#### `analysis.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:193 (em ClassDuplicateFinder.generate_report)
```

### 🔍 Objeto: `analysis1`

#### `analysis1.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:363 (em SemanticAnalyzer._calculate_similarity)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:370 (em SemanticAnalyzer._calculate_similarity)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:377 (em SemanticAnalyzer._calculate_similarity)
```

### 🔍 Objeto: `analysis2`

#### `analysis2.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:364 (em SemanticAnalyzer._calculate_similarity)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:371 (em SemanticAnalyzer._calculate_similarity)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:377 (em SemanticAnalyzer._calculate_similarity)
```

### 🔍 Objeto: `analyzer`

#### `analyzer.try_imports` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:209 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:224 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:239 (em module.analisar_arquivo)
```

#### `analyzer.analyze_query` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:77 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/__init__.py:149 (em module.analyze_semantic_meaning)
```

#### `analyzer.visit` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:160 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:214 (em module.analisar_arquivo)
```

#### `analyzer.redis_usage` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:180 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:225 (em module.analisar_arquivo)
```

#### `analyzer.model_usage` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:197 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:227 (em module.analisar_arquivo)
```

#### `analyzer.fallback_patterns` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:208 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:228 (em module.analisar_arquivo)
```

#### `analyzer.all_imports` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:218 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:237 (em module.analisar_arquivo)
```

#### `analyzer.placeholders` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:241 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:242 (em module.analisar_arquivo)
```

#### `analyzer.conditional_imports` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:166 (em module.analisar_arquivo)
```

#### `analyzer.imports` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:223 (em module.analisar_arquivo)
```

#### `analyzer.db_usage` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:226 (em module.analisar_arquivo)
```

#### `analyzer.function_imports` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:238 (em module.analisar_arquivo)
```

#### `analyzer.analyze` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/__init__.py:139 (em module.analyze_query_intention)
```

#### `analyzer.analyze_structure` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/__init__.py:144 (em module.analyze_text_structure)
```

#### `analyzer.detect_anomalies` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:648 (em module.detect_system_anomalies)
```

#### `analyzer.set_learner` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1454 (em MainOrchestrator._connect_modules)
```

### 🔍 Objeto: `anomalies`

#### `anomalies.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:581 (em PerformanceAnalyzer._detect_statistical_anomalies)
```

### 🔍 Objeto: `anthropic`

#### `anthropic.Anthropic` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:162 (em ResponseProcessor._init_anthropic_client)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:73 (em ClaudeAPIClient.__init__)
```

### 🔍 Objeto: `api_tasks`

#### `api_tasks.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:299 (em CursorMonitor.top-level)
```

### 🔍 Objeto: `app`

#### `app.app_context` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:154 (em EntregasLoader._load_with_context)
```

### 🔍 Objeto: `aprendizado`

#### `aprendizado.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:421 (em SessionOrchestrator._execute_learning_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:422 (em SessionOrchestrator._execute_learning_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:426 (em SessionOrchestrator._execute_learning_workflow)
```

### 🔍 Objeto: `aprendizados`

#### `aprendizados.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:365 (em LearningCore._calcular_score_aprendizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:368 (em LearningCore._calcular_score_aprendizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:371 (em LearningCore._calcular_score_aprendizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:374 (em LearningCore._calcular_score_aprendizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:377 (em LearningCore._calcular_score_aprendizado)
```

### 🔍 Objeto: `architectural_compliance`

#### `architectural_compliance.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/__init__.py:236 (em module.validate_integration_architecture)
```

### 🔍 Objeto: `architecture_data`

#### `architecture_data.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:103 (em StructuralAnalyzer.validate_architecture)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:107 (em StructuralAnalyzer.validate_architecture)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:111 (em StructuralAnalyzer.validate_architecture)
```

### 🔍 Objeto: `arg`

#### `arg.arg` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:44 (em VariableTracker.visit_FunctionDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:45 (em VariableTracker.visit_FunctionDef)
```

### 🔍 Objeto: `argparse`

#### `argparse.ArgumentParser` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:360 (em module.main)
```

### 🔍 Objeto: `args`

#### `args.url` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:366 (em module.main)
```

#### `args.interval` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:367 (em module.main)
```

### 🔍 Objeto: `arquivo`

#### `arquivo.replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:175 (em TesteIntegracaoCompleta.testar_modulo)
```

### 🔍 Objeto: `arquivos_grandes`

#### `arquivos_grandes.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:200 (em module.verificar_modulos_especiais)
```

### 🔍 Objeto: `arquivos_importantes`

#### `arquivos_importantes.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:205 (em module.verificar_modulos_especiais)
```

### 🔍 Objeto: `arquivos_ok`

#### `arquivos_ok.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_finais_v2.py:69 (em module.verificar_imports)
```

### 🔍 Objeto: `arquivos_py_local`

#### `arquivos_py_local.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:66 (em module.contar_arquivos_detalhado)
```

### 🔍 Objeto: `assign_node`

#### `assign_node.targets` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:149 (em CodeScanner._parse_form_field)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:252 (em StructureScanner._parse_model_assignment)
```

#### `assign_node.value` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:152 (em CodeScanner._parse_form_field)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:255 (em StructureScanner._parse_model_assignment)
```

### 🔍 Objeto: `ast`

#### `ast.Name` (21 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:68 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:71 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:82 (em MethodCallVisitor._get_object_name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:55 (em VariableTracker.visit_ClassDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:62 (em VariableTracker.visit_Assign)
  ... e mais 16 ocorrências
```

#### `ast.parse` (10 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:48 (em ClassDuplicateFinder.scan_file)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:99 (em module.analyze_file)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:110 (em UninitializedVariableFinder.scan_file)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:158 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:212 (em module.analisar_arquivo)
  ... e mais 5 ocorrências
```

#### `ast.Constant` (10 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:67 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:79 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:210 (em CodeScanner._extract_dict_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:212 (em CodeScanner._extract_dict_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:235 (em CodeScanner._extract_simple_value)
  ... e mais 5 ocorrências
```

#### `ast.Attribute` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:70 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:84 (em MethodCallVisitor._get_object_name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:142 (em CodeScanner._is_flask_form)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:172 (em CodeScanner._extract_form_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:198 (em CodeScanner._extract_validators)
  ... e mais 3 ocorrências
```

#### `ast.Assign` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:53 (em VariableTracker.visit_ClassDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:85 (em DependencyAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:75 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:120 (em CodeScanner._parse_forms_file)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:147 (em CodeScanner._parse_form_field)
  ... e mais 3 ocorrências
```

#### `ast.ClassDef` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:52 (em ClassDuplicateFinder.scan_file)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:60 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:104 (em CodeScanner._parse_forms_file)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:136 (em CodeScanner._is_flask_form)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:190 (em StructureScanner._parse_models_file)
  ... e mais 2 ocorrências
```

#### `ast.Call` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:88 (em MethodCallVisitor._get_object_name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:86 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:168 (em CodeScanner._extract_form_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:195 (em CodeScanner._extract_validators)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:279 (em StructureScanner._extract_field_info)
  ... e mais 1 ocorrências
```

#### `ast.NodeVisitor` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:16 (em MethodCallVisitor.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:15 (em VariableTracker.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:20 (em DependencyAnalyzer.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:20 (em DeepImportAnalyzer.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:68 (em RealProblemFinder.top-level)
```

#### `ast.Str` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:237 (em CodeScanner._extract_simple_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:246 (em StructureScanner._extract_table_name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:306 (em StructureScanner._extract_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:358 (em StructureScanner._extract_string_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:369 (em StructureScanner._extract_value)
```

#### `ast.FunctionDef` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:76 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:49 (em MethodCallVisitor.visit_ClassDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:122 (em CodeScanner._parse_forms_file)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:210 (em StructureScanner._parse_models_file)
```

#### `ast.Load` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:66 (em MethodCallVisitor.visit_Attribute)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:69 (em VariableTracker.visit_Name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:130 (em RealProblemFinder.visit_Name)
```

#### `ast.walk` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:51 (em ClassDuplicateFinder.scan_file)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:102 (em ImportChecker.extract_imports)
```

#### `ast.Import` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:34 (em CircularDependencyMapper.extract_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:103 (em ImportChecker.extract_imports)
```

#### `ast.ImportFrom` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:39 (em CircularDependencyMapper.extract_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:112 (em ImportChecker.extract_imports)
```

#### `ast.List` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:193 (em CodeScanner._extract_validators)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:222 (em CodeScanner._extract_choices)
```

#### `ast.Num` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:239 (em CodeScanner._extract_simple_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:371 (em StructureScanner._extract_value)
```

#### `ast.NameConstant` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:347 (em StructureScanner._extract_boolean_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:373 (em StructureScanner._extract_value)
```

#### `ast.get_docstring` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:63 (em ClassDuplicateFinder.extract_class_info)
```

#### `ast.Store` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:72 (em VariableTracker.visit_Name)
```

#### `ast.unparse` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:91 (em DependencyAnalyzer.visit_Try)
```

#### `ast.Return` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:66 (em DeepImportAnalyzer.visit_Try)
```

#### `ast.AST` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:98 (em ImportChecker.extract_imports)
```

#### `ast.Dict` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:208 (em CodeScanner._extract_dict_value)
```

#### `ast.Tuple` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:224 (em CodeScanner._extract_choices)
```

### 🔍 Objeto: `asyncio`

#### `asyncio.run` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:83 (em ProcessorManager.process_semantic_loop)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:106 (em ProcessorCoordinator._execute_chain_step)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:115 (em ProcessorCoordinator._execute_chain_step)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:125 (em ProcessorCoordinator._execute_chain_step)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:133 (em ProcessorCoordinator._execute_chain_step)
  ... e mais 6 ocorrências
```

#### `asyncio.get_event_loop` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:237 (em ClaudeAINovo.process_query_sync)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:348 (em module.get_claude_ai_instance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/__init__.py:195 (em module.initialize_integration_system)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:510 (em module.processar_com_claude_real)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:124 (em StandaloneIntegration.initialize_system)
  ... e mais 3 ocorrências
```

#### `asyncio.iscoroutinefunction` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:105 (em ProcessorCoordinator._execute_chain_step)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:114 (em ProcessorCoordinator._execute_chain_step)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:124 (em ProcessorCoordinator._execute_chain_step)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:131 (em ProcessorCoordinator._execute_chain_step)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:227 (em ProcessorCoordinator._execute_single_processor)
  ... e mais 1 ocorrências
```

#### `asyncio.to_thread` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:297 (em CursorMonitor.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:311 (em CursorMonitor.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:312 (em CursorMonitor.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:316 (em CursorMonitor.top-level)
```

#### `asyncio.new_event_loop` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:239 (em ClaudeAINovo.process_query_sync)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:350 (em module.get_claude_ai_instance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:273 (em WebIntegrationAdapter._run_async)
```

#### `asyncio.set_event_loop` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:240 (em ClaudeAINovo.process_query_sync)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:351 (em module.get_claude_ai_instance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:274 (em WebIntegrationAdapter._run_async)
```

#### `asyncio.gather` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:301 (em CursorMonitor.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1039 (em MainOrchestrator.top-level)
```

#### `asyncio.sleep` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:326 (em CursorMonitor.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:334 (em CursorMonitor.top-level)
```

#### `asyncio.create_task` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:296 (em CursorMonitor.top-level)
```

### 🔍 Objeto: `atrasos`

#### `atrasos.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:140 (em ValidationUtils._calcular_metricas_prazo)
```

### 🔍 Objeto: `attr`

#### `attr.startswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:197 (em DeepValidator._test_class_exists)
```

### 🔍 Objeto: `auto_mappings`

#### `auto_mappings.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:340 (em MapperManager.apply_auto_suggestions)
```

### 🔍 Objeto: `available_scores`

#### `available_scores.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:419 (em OrchestratorManager._detect_appropriate_orchestrator)
```

### 🔍 Objeto: `base`

#### `base.value` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:71 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:71 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:231 (em StructureScanner._is_sqlalchemy_model)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:231 (em StructureScanner._is_sqlalchemy_model)
```

#### `base.attr` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:71 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:71 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:143 (em CodeScanner._is_flask_form)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:231 (em StructureScanner._is_sqlalchemy_model)
```

#### `base.id` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:69 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:140 (em CodeScanner._is_flask_form)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:234 (em StructureScanner._is_sqlalchemy_model)
```

#### `base.value.id` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:71 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:231 (em StructureScanner._is_sqlalchemy_model)
```

#### `base.replace().lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:245 (em BaseCommand._generate_cache_key)
```

#### `base.replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:245 (em BaseCommand._generate_cache_key)
```

### 🔍 Objeto: `base_cmd`

#### `base_cmd._format_currency` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:373 (em module.create_excel_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:374 (em module.create_excel_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:375 (em module.create_excel_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:376 (em module.create_excel_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:382 (em module.create_excel_summary)
  ... e mais 1 ocorrências
```

#### `base_cmd._format_weight` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:383 (em module.create_excel_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:385 (em module.create_excel_summary)
```

#### `base_cmd._create_summary_stats` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:356 (em module.create_excel_summary)
```

#### `base_cmd._format_percentage` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:393 (em module.create_excel_summary)
```

### 🔍 Objeto: `base_dir`

#### `base_dir.rglob` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:139 (em module.find_undefined_methods)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:250 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:267 (em module.main)
```

#### `base_dir.parent` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:189 (em module.verificar_import_existe)
```

### 🔍 Objeto: `base_parts`

#### `base_parts.pop` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:52 (em CircularDependencyMapper.extract_imports)
```

#### `base_parts.extend` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:56 (em CircularDependencyMapper.extract_imports)
```

### 🔍 Objeto: `base_status`

#### `base_status.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:176 (em ClaudeAINovo.get_system_status)
```

### 🔍 Objeto: `bases`

#### `bases.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:69 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:71 (em ClassDuplicateFinder.extract_class_info)
```

### 🔍 Objeto: `basic_context`

#### `basic_context.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:538 (em WebFlaskRoutes._build_user_context)
```

### 🔍 Objeto: `batch_result`

#### `batch_result.get().get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:167 (em DataProcessor.batch_process)
```

#### `batch_result.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:167 (em DataProcessor.batch_process)
```

### 🔍 Objeto: `best_orchestrator`

#### `best_orchestrator.value` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:420 (em OrchestratorManager._detect_appropriate_orchestrator)
```

### 🔍 Objeto: `blocks`

#### `blocks.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:151 (em FileScanner._extract_template_blocks)
```

### 🔍 Objeto: `bp`

#### `bp.route` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:338 (em WebFlaskRoutes.chat_page)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:344 (em WebFlaskRoutes.api_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:398 (em WebFlaskRoutes.api_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:431 (em WebFlaskRoutes.clear_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:456 (em WebFlaskRoutes.health_check)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `business_logic`

#### `business_logic.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:94 (em CriticAgent.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:103 (em CriticAgent.top-level)
```

### 🔍 Objeto: `by_file`

#### `by_file.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:280 (em ImportChecker.print_report)
```

### 🔍 Objeto: `by_module`

#### `by_module.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:240 (em ImportFilterer.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:302 (em ImportChecker.print_report)
```

### 🔍 Objeto: `by_priority`

#### `by_priority.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:694 (em SessionOrchestrator.get_session_stats)
```

### 🔍 Objeto: `by_status`

#### `by_status.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:690 (em SessionOrchestrator.get_session_stats)
```

### 🔍 Objeto: `by_variable`

#### `by_variable.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:223 (em UninitializedVariableFinder.generate_report)
```

### 🔍 Objeto: `c`

#### `c.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:307 (em ProcessorCoordinator.get_coordinator_stats)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:308 (em ProcessorCoordinator.get_coordinator_stats)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:309 (em ProcessorCoordinator.get_coordinator_stats)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:270 (em SystemMemory.get_system_overview)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:156 (em BaseMapper.gerar_estatisticas)
```

#### `c.strip` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:241 (em KnowledgeMemory.buscar_grupos_aplicaveis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:241 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `c.split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:284 (em module.main)
```

#### `c.get().get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:270 (em SystemMemory.get_system_overview)
```

### 🔍 Objeto: `cache`

#### `cache.get_cached_result` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:260 (em module.cached_result)
```

#### `cache.set_cached_result` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:268 (em module.cached_result)
```

### 🔍 Objeto: `cache_entry`

#### `cache_entry.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/context_provider.py:415 (em ContextProvider._get_cached_context)
```

### 🔍 Objeto: `cache_obj`

#### `cache_obj.set` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:324 (em BaseProcessor._safe_cache_set)
```

### 🔍 Objeto: `campo`

#### `campo.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:178 (em MapperManager._calcular_confianca_integrada)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:181 (em MapperManager._calcular_confianca_integrada)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:204 (em MapperManager._agrupar_por_mapper)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:149 (em DatabaseManager.buscar_campos_por_tipo)
```

#### `campo.lower` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:423 (em SemanticValidator._calcular_similaridade_termo_campo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:431 (em SemanticValidator._calcular_similaridade_termo_campo)
```

#### `campo.endswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:191 (em SemanticValidator._validacoes_gerais)
```

#### `campo.lower().split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:431 (em SemanticValidator._calcular_similaridade_termo_campo)
```

### 🔍 Objeto: `campo_comp`

#### `campo_comp.get` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:467 (em FieldSearcher._calcular_similaridade_campos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:470 (em FieldSearcher._calcular_similaridade_campos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:475 (em FieldSearcher._calcular_similaridade_campos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:507 (em FieldSearcher._analisar_fatores_similaridade)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:510 (em FieldSearcher._analisar_fatores_similaridade)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `campo_ref`

#### `campo_ref.get` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:467 (em FieldSearcher._calcular_similaridade_campos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:470 (em FieldSearcher._calcular_similaridade_campos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:474 (em FieldSearcher._calcular_similaridade_campos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:507 (em FieldSearcher._analisar_fatores_similaridade)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:510 (em FieldSearcher._analisar_fatores_similaridade)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `campos_baixa_confianca`

#### `campos_baixa_confianca.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:511 (em AutoMapper._gerar_sugestoes_melhoria)
```

### 🔍 Objeto: `campos_detectados`

#### `campos_detectados.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:86 (em MapperManager.analisar_consulta_semantica)
```

#### `campos_detectados.extend` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:96 (em MapperManager.analisar_consulta_semantica)
```

### 🔍 Objeto: `campos_encontrados`

#### `campos_encontrados.append` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:99 (em FieldSearcher.buscar_campos_por_tipo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:179 (em FieldSearcher.buscar_campos_por_nome)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:314 (em FieldSearcher.buscar_campos_por_caracteristica)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:367 (em FieldSearcher.buscar_campos_por_tamanho)
```

#### `campos_encontrados.sort` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:102 (em FieldSearcher.buscar_campos_por_tipo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:182 (em FieldSearcher.buscar_campos_por_nome)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:370 (em FieldSearcher.buscar_campos_por_tamanho)
```

### 🔍 Objeto: `campos_por_tabela`

#### `campos_por_tabela.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:305 (em MetadataScanner.obter_estatisticas_tabelas)
```

### 🔍 Objeto: `campos_similares`

#### `campos_similares.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:428 (em FieldSearcher.buscar_campos_similares)
```

#### `campos_similares.sort` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:431 (em FieldSearcher.buscar_campos_similares)
```

### 🔍 Objeto: `candidate`

#### `candidate.exists` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:443 (em SystemConfig._get_default_config_path)
```

### 🔍 Objeto: `categorias`

#### `categorias.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:384 (em AutoMapper._identificar_categoria_semantica)
```

### 🔍 Objeto: `category`

#### `category.upper` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:165 (em DependencyChecker.analyze_dependencies)
```

### 🔍 Objeto: `category_patterns`

#### `category_patterns.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:354 (em FeedbackProcessor._classificar_categoria)
```

### 🔍 Objeto: `cell`

#### `cell.value` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:418 (em ExcelFretes._auto_ajustar_colunas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:419 (em ExcelFretes._auto_ajustar_colunas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:450 (em ExcelPedidos._auto_ajustar_colunas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:451 (em ExcelPedidos._auto_ajustar_colunas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:307 (em ExcelFaturamento._auto_ajustar_colunas)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `chain_info`

#### `chain_info.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:290 (em ProcessorCoordinator.cleanup_completed_chains)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:291 (em ProcessorCoordinator.cleanup_completed_chains)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:291 (em ProcessorCoordinator.cleanup_completed_chains)
```

### 🔍 Objeto: `chain_result`

#### `chain_result.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:199 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:205 (em module.run_complete_flow)
```

### 🔍 Objeto: `chains`

#### `chains.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:135 (em ProcessorManager.get_processor_chain)
```

### 🔍 Objeto: `chains_to_remove`

#### `chains_to_remove.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:293 (em ProcessorCoordinator.cleanup_completed_chains)
```

### 🔍 Objeto: `check_name`

#### `check_name.upper` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:232 (em CursorMonitor.display_status)
```

### 🔍 Objeto: `checker`

#### `checker.run` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:349 (em module.top-level)
```

#### `checker.check_directory` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:328 (em module.main)
```

#### `checker.print_report` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:331 (em module.main)
```

#### `checker.save_report` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:335 (em module.main)
```

### 🔍 Objeto: `choices`

#### `choices.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:227 (em CodeScanner._extract_choices)
```

### 🔍 Objeto: `choices_node`

#### `choices_node.elts` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:223 (em CodeScanner._extract_choices)
```

### 🔍 Objeto: `chr()`

#### `chr().join` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/response_utils.py:39 (em ResponseUtils._formatar_resultado_cursor)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/response_utils.py:77 (em ResponseUtils._formatar_status_cursor)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/response_utils.py:80 (em ResponseUtils._formatar_status_cursor)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/response_utils.py:83 (em ResponseUtils._formatar_status_cursor)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:127 (em CursorCommands._ativar_cursor_mode)
```

### 🔍 Objeto: `ck`

#### `ck.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:241 (em MetadataScanner._obter_constraints_tabela)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:242 (em MetadataScanner._obter_constraints_tabela)
```

### 🔍 Objeto: `class_node`

#### `class_node.bases` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:138 (em CodeScanner._is_flask_form)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:229 (em StructureScanner._is_sqlalchemy_model)
```

#### `class_node.body` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:240 (em StructureScanner._extract_table_name)
```

### 🔍 Objeto: `classes`

#### `classes.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:162 (em StructuralAnalyzer.detect_patterns)
```

#### `classes.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:265 (em StructuralAnalyzer._calculate_complexity)
```

### 🔍 Objeto: `classification`

#### `classification.upper` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:260 (em CursorMonitor.display_status)
```

### 🔍 Objeto: `claude_ai`

#### `claude_ai.initialize_system` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:305 (em module.top-level)
```

### 🔍 Objeto: `claude_data`

#### `claude_data.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:242 (em CursorMonitor.display_status)
```

### 🔍 Objeto: `claude_instance`

#### `claude_instance.__class__.__name__` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/__init__.py:350 (em module.top-level)
```

#### `claude_instance.__class__` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/__init__.py:350 (em module.top-level)
```

### 🔍 Objeto: `claude_metrics`

#### `claude_metrics.record_query` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:319 (em module.record_query_metric)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:322 (em module.record_query_metric)
```

### 🔍 Objeto: `cleanup_results`

#### `cleanup_results.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:291 (em MemoryManager.cleanup_expired_data)
```

### 🔍 Objeto: `cliente`

#### `cliente.lower` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:211 (em ConversationContext.extract_metadata)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:211 (em ConversationContext.extract_metadata)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:292 (em ConversationContext.get_context_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:459 (em PatternLearner._extrair_termos_cliente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:409 (em KnowledgeMemory._extrair_termos_cliente)
```

#### `cliente.title` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:470 (em SuggestionsEngine._get_contextual_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:474 (em SuggestionsEngine._get_contextual_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/base.py:53 (em ProcessorBase._extract_filters)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:105 (em BaseCommand._extract_client_from_query)
```

### 🔍 Objeto: `cliente_lower`

#### `cliente_lower.split` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:466 (em PatternLearner._extrair_termos_cliente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:416 (em KnowledgeMemory._extrair_termos_cliente)
```

#### `cliente_lower.startswith` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:476 (em PatternLearner._extrair_termos_cliente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:425 (em KnowledgeMemory._extrair_termos_cliente)
```

### 🔍 Objeto: `clientes_mencionados`

#### `clientes_mencionados.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:293 (em ConversationContext.get_context_summary)
```

### 🔍 Objeto: `clientes_stats`

#### `clientes_stats.values` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:466 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:249 (em PedidosLoader._format_pedidos_results)
```

#### `clientes_stats.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:216 (em FaturamentoLoader._format_faturamento_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:259 (em FretesLoader._format_fretes_results)
```

### 🔍 Objeto: `cls`

#### `cls._instance` (10 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:35 (em ScannersCache.__new__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:37 (em ScannersCache.__new__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:39 (em ScannersCache.__new__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:40 (em ScannersCache.__new__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:39 (em ClaudeAIMetrics.__new__)
  ... e mais 5 ocorrências
```

#### `cls._lock` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:36 (em ScannersCache.__new__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:40 (em ClaudeAIMetrics.__new__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:40 (em ClaudeAIMetricsOptimized.__new__)
```

#### `cls.ANTHROPIC_API_KEY` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/basic_config.py:46 (em ClaudeAIConfig.get_anthropic_api_key)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/basic_config.py:69 (em ClaudeAIConfig.validate)
```

#### `cls.CLAUDE_MODEL` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/basic_config.py:52 (em ClaudeAIConfig.get_claude_params)
```

#### `cls.MAX_TOKENS` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/basic_config.py:53 (em ClaudeAIConfig.get_claude_params)
```

#### `cls.TEMPERATURE` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/basic_config.py:54 (em ClaudeAIConfig.get_claude_params)
```

### 🔍 Objeto: `cluster`

#### `cluster.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:324 (em RelationshipMapper._explorar_cluster)
```

### 🔍 Objeto: `clusters`

#### `clusters.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:286 (em RelationshipMapper._identificar_clusters)
```

#### `clusters.sort` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:294 (em RelationshipMapper._identificar_clusters)
```

### 🔍 Objeto: `cnpj_prefix`

#### `cnpj_prefix.replace().replace().replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:346 (em EntregasLoader._build_entregas_query)
```

#### `cnpj_prefix.replace().replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:346 (em EntregasLoader._build_entregas_query)
```

#### `cnpj_prefix.replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:346 (em EntregasLoader._build_entregas_query)
```

### 🔍 Objeto: `col`

#### `col.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:132 (em StructureScanner._discover_models_via_database)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:132 (em StructureScanner._discover_models_via_database)
```

### 🔍 Objeto: `coluna`

#### `coluna.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:101 (em MetadataScanner.obter_campos_tabela)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:102 (em MetadataScanner.obter_campos_tabela)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:103 (em MetadataScanner.obter_campos_tabela)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:105 (em MetadataScanner.obter_campos_tabela)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:106 (em MetadataScanner.obter_campos_tabela)
```

### 🔍 Objeto: `combined`

#### `combined.extend` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:576 (em DataProcessor._combine_processed_data)
```

#### `combined.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:582 (em DataProcessor._combine_processed_data)
```

#### `combined.encode` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:317 (em SecurityGuard.generate_token)
```

### 🔍 Objeto: `command`

#### `command.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:372 (em AutoCommandProcessor._validate_security)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:380 (em AutoCommandProcessor._validate_security)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:399 (em AutoCommandProcessor._execute_command)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:486 (em AutoCommandProcessor._validate_command_syntax)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:487 (em AutoCommandProcessor._validate_command_syntax)
```

#### `command.get().get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:372 (em AutoCommandProcessor._validate_security)
```

#### `command.get().lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:380 (em AutoCommandProcessor._validate_security)
```

### 🔍 Objeto: `command_result`

#### `command_result.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:715 (em MainOrchestrator._execute_natural_commands)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:718 (em MainOrchestrator._execute_natural_commands)
```

### 🔍 Objeto: `common`

#### `common.extend` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:389 (em SemanticAnalyzer._find_common_entities)
```

### 🔍 Objeto: `common_issues`

#### `common_issues.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:383 (em HumanInLoopLearning._analyze_trends)
```

#### `common_issues.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:386 (em HumanInLoopLearning._analyze_trends)
```

### 🔍 Objeto: `comp`

#### `comp.analyze_intention` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:327 (em TesteIntegracaoCompleta.testar_fallbacks_mocks)
```

#### `comp.generate_intelligent_suggestions` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:331 (em TesteIntegracaoCompleta.testar_fallbacks_mocks)
```

#### `comp.manage_conversation` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:335 (em TesteIntegracaoCompleta.testar_fallbacks_mocks)
```

### 🔍 Objeto: `component_data`

#### `component_data.get().get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:300 (em SystemMemory.get_component_status)
```

#### `component_data.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:300 (em SystemMemory.get_component_status)
```

### 🔍 Objeto: `component_info`

#### `component_info.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:590 (em IntelligenceCoordinator._component_supports_operation)
```

### 🔍 Objeto: `component_instance`

#### `component_instance.analyze` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:547 (em IntelligenceCoordinator._execute_component_operation)
```

#### `component_instance.synthesize` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:549 (em IntelligenceCoordinator._execute_component_operation)
```

#### `component_instance.predict` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:551 (em IntelligenceCoordinator._execute_component_operation)
```

#### `component_instance.optimize` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:553 (em IntelligenceCoordinator._execute_component_operation)
```

#### `component_instance.process` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:555 (em IntelligenceCoordinator._execute_component_operation)
```

#### `component_instance.process_intelligence` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:557 (em IntelligenceCoordinator._execute_component_operation)
```

### 🔍 Objeto: `components`

#### `components.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/__init__.py:225 (em module.validate_integration_architecture)
```

#### `components.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:243 (em CursorMonitor.display_status)
```

### 🔍 Objeto: `compressed`

#### `compressed.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:278 (em ContextMemory._compress_context)
```

### 🔍 Objeto: `condicoes`

#### `condicoes.append` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:338 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:340 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:347 (em EntregasLoader._build_entregas_query)
```

### 🔍 Objeto: `conditions`

#### `conditions.append` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:148 (em DatabaseLoader.load_table_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:215 (em SessionMemory.search_sessions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:218 (em SessionMemory.search_sessions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:221 (em SessionMemory.search_sessions)
```

### 🔍 Objeto: `confiancas`

#### `confiancas.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:291 (em IntentionAnalyzer.get_performance_stats)
```

### 🔍 Objeto: `confidences`

#### `confidences.append` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:134 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:357 (em AnalyzerManager._calculate_combined_confidence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:359 (em AnalyzerManager._calculate_combined_confidence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:671 (em IntelligenceCoordinator._create_simple_consensus)
```

### 🔍 Objeto: `config`

#### `config.get` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:123 (em IntentionAnalyzer._detectar_intencoes_multiplas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:180 (em ProcessorCoordinator.execute_parallel_processors)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:206 (em ProcessorCoordinator._execute_single_processor)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:207 (em ProcessorCoordinator._execute_single_processor)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:208 (em ProcessorCoordinator._execute_single_processor)
  ... e mais 6 ocorrências
```

#### `config.get_claude_params` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:90 (em ClaudeAPIClient.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:114 (em ClaudeAPIClient.from_mode)
```

#### `config.get_anthropic_api_key` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:159 (em ResponseProcessor._init_anthropic_client)
```

#### `config.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:644 (em SystemConfig._validate_profile_config)
```

### 🔍 Objeto: `config_data`

#### `config_data.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:104 (em SystemMemory.retrieve_system_config)
```

### 🔍 Objeto: `config_params`

#### `config_params.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:83 (em ClaudeAPIClient.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:84 (em ClaudeAPIClient.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:85 (em ClaudeAPIClient.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:86 (em ClaudeAPIClient.__init__)
```

### 🔍 Objeto: `conhecimento`

#### `conhecimento.get` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:395 (em LearningCore._gerar_recomendacoes_aplicacao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:405 (em LearningCore._gerar_recomendacoes_aplicacao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:406 (em LearningCore._gerar_recomendacoes_aplicacao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:407 (em LearningCore._gerar_recomendacoes_aplicacao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:502 (em SessionOrchestrator.apply_learned_knowledge)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `conn`

#### `conn.execute` (13 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:71 (em DatabaseLoader._initialize_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:112 (em DatabaseLoader.load_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:308 (em DatabaseConnection.test_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:127 (em DataAnalyzer._get_field_type)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:177 (em DataAnalyzer._analisar_estatisticas_basicas)
  ... e mais 8 ocorrências
```

#### `conn.execute().fetchone` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:127 (em DataAnalyzer._get_field_type)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:177 (em DataAnalyzer._analisar_estatisticas_basicas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:208 (em DataAnalyzer._analisar_estatisticas_basicas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:352 (em DataAnalyzer._analisar_comprimento_valores)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:419 (em DataAnalyzer._verificar_padrao_numerico)
  ... e mais 3 ocorrências
```

#### `conn.execute().fetchall` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:267 (em DataAnalyzer._obter_exemplos_valores)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:311 (em DataAnalyzer._analisar_distribuicao)
```

### 🔍 Objeto: `connected`

#### `connected.sort` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:234 (em CircularDependencyMapper.generate_report)
```

### 🔍 Objeto: `connection_count`

#### `connection_count.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:308 (em DatabaseScanner._analyze_relationships)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:315 (em DatabaseScanner._analyze_relationships)
```

#### `connection_count.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:322 (em DatabaseScanner._analyze_relationships)
```

### 🔍 Objeto: `consistencia`

#### `consistencia.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:360 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
```

### 🔍 Objeto: `consistency_check`

#### `consistency_check.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:329 (em ValidatorManager.validate_consistency)
```

### 🔍 Objeto: `consulta`

#### `consulta.lower` (30 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:69 (em MapperManager.analisar_consulta_semantica)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:62 (em IntentionAnalyzer._detectar_intencoes_multiplas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:140 (em IntentionAnalyzer._analisar_contexto_intencao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:203 (em IntentionAnalyzer._detectar_urgencia)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:225 (em IntentionAnalyzer._calcular_complexidade_intencao)
  ... e mais 25 ocorrências
```

#### `consulta.split` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:150 (em MapperManager._extrair_termos_compostos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:222 (em IntentionAnalyzer._calcular_complexidade_intencao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:249 (em IntentionAnalyzer._deve_usar_sistema_avancado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/data_manager.py:339 (em DataManager.get_best_loader)
```

#### `consulta.strip` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:84 (em BaseCommand._validate_input)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:93 (em BaseCommand._sanitize_input)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:225 (em PatternLearner._extrair_padroes_linguisticos)
```

#### `consulta.replace().strip` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:231 (em CursorCommands._buscar_codigo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:270 (em CursorCommands._cursor_chat)
```

#### `consulta.replace` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:231 (em CursorCommands._buscar_codigo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:270 (em CursorCommands._cursor_chat)
```

#### `consulta.lower().strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:69 (em MapperManager.analisar_consulta_semantica)
```

#### `consulta.strip().endswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:225 (em PatternLearner._extrair_padroes_linguisticos)
```

### 🔍 Objeto: `consulta_lower`

#### `consulta_lower.split` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:77 (em MapperManager.analisar_consulta_semantica)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:106 (em MapperManager.analisar_consulta_semantica)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:472 (em PatternLearner._extrair_termos_cliente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:422 (em KnowledgeMemory._extrair_termos_cliente)
```

#### `consulta_lower.index` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:188 (em ExcelOrchestrator._detectar_tipo_excel)
```

### 🔍 Objeto: `contagem`

#### `contagem.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:205 (em MapperManager._agrupar_por_mapper)
```

### 🔍 Objeto: `content`

#### `content.split` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:80 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:189 (em UninitializedVariableFinder._get_line_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:176 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:261 (em CodeScanner._parse_routes_file)
```

#### `content.encode` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:491 (em SuggestionsManager._generate_cache_key)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:711 (em IntelligenceCoordinator._generate_cache_key)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/context_provider.py:404 (em ContextProvider._generate_cache_key)
```

### 🔍 Objeto: `context`

#### `context.get` (20 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:378 (em ConversationManager.get_conversation_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:379 (em ConversationManager.get_conversation_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:380 (em ConversationManager.get_conversation_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:352 (em SemanticAnalyzer._enhance_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:313 (em LoaderManager.get_best_loader_for_query)
  ... e mais 15 ocorrências
```

#### `context.append` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:154 (em DeepImportAnalyzer._get_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:156 (em DeepImportAnalyzer._get_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:158 (em DeepImportAnalyzer._get_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:160 (em DeepImportAnalyzer._get_context)
```

#### `context.update` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1017 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1047 (em MainOrchestrator.top-level)
```

#### `context.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:115 (em ImportFilterer.is_false_positive)
```

#### `context.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:177 (em BaseValidationUtils.validate_context)
```

#### `context.copy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:271 (em ContextMemory._compress_context)
```

### 🔍 Objeto: `context_history`

#### `context_history.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:71 (em ConversationContext.add_message)
```

### 🔍 Objeto: `context_lines`

#### `context_lines.append` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:177 (em ConversationContext.build_context_prompt)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:179 (em ConversationContext.build_context_prompt)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:180 (em ConversationContext.build_context_prompt)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:181 (em ConversationContext.build_context_prompt)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:182 (em ConversationContext.build_context_prompt)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `context_module`

#### `context_module.clear_context` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:439 (em WebFlaskRoutes.clear_context)
```

### 🔍 Objeto: `context_processor`

#### `context_processor.carregar_contexto_inteligente` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:46 (em ProcessorManager.process_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:534 (em WebFlaskRoutes._build_user_context)
```

#### `context_processor.set_memory_manager` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:266 (em ProcessorManager.set_memory_manager)
```

#### `context_processor.set_enricher` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:295 (em ProcessorManager.set_enricher)
```

### 🔍 Objeto: `context_result`

#### `context_result.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:219 (em ProviderManager._provide_data_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:251 (em ProviderManager._provide_context_with_data)
```

### 🔍 Objeto: `contexto`

#### `contexto.append` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:261 (em NLPEnhancedAnalyzer._detectar_negacoes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:262 (em NLPEnhancedAnalyzer._detectar_negacoes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:264 (em NLPEnhancedAnalyzer._detectar_negacoes)
```

#### `contexto.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:246 (em IntentionAnalyzer._deve_usar_sistema_avancado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:248 (em IntentionAnalyzer._deve_usar_sistema_avancado)
```

### 🔍 Objeto: `contextual_suggestions`

#### `contextual_suggestions.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:468 (em SuggestionsEngine._get_contextual_suggestions)
```

### 🔍 Objeto: `conversation_context`

#### `conversation_context.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:462 (em SuggestionsEngine._get_contextual_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:547 (em SuggestionsEngine._generate_cache_key)
```

#### `conversation_context.get().lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:462 (em SuggestionsEngine._get_contextual_suggestions)
```

### 🔍 Objeto: `conversation_result`

#### `conversation_result.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:464 (em SessionOrchestrator._execute_conversation_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:465 (em SessionOrchestrator._execute_conversation_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:466 (em SessionOrchestrator._execute_conversation_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:470 (em SessionOrchestrator._execute_conversation_workflow)
```

### 🔍 Objeto: `conversational`

#### `conversational.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:254 (em ContextEnricher._calculate_context_score)
```

### 🔍 Objeto: `converser`

#### `converser.context_memory` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:158 (em module.run_complete_flow)
```

#### `converser.get_manager_stats` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:162 (em module.run_complete_flow)
```

#### `converser.set_memorizer` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1478 (em MainOrchestrator._connect_modules)
```

### 🔍 Objeto: `coordination_result`

#### `coordination_result.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:678 (em MainOrchestrator._execute_intelligent_coordination)
```

### 🔍 Objeto: `coordinator`

#### `coordinator.coordinate_intelligence_operation` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:219 (em module.coordinate_intelligence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:283 (em CoordinatorManager._process_with_coordinator)
```

#### `coordinator.coordinate_processors` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:236 (em module.coordinate_processors)
```

#### `coordinator.execute_processor_chain` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:291 (em CoordinatorManager._process_with_coordinator)
```

#### `coordinator.process_query` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:295 (em CoordinatorManager._process_with_coordinator)
```

#### `coordinator.process` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:306 (em CoordinatorManager._process_with_coordinator)
```

### 🔍 Objeto: `coordinator_name`

#### `coordinator_name.startswith` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:269 (em CoordinatorManager._process_with_coordinator)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:327 (em CoordinatorManager._update_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:361 (em CoordinatorManager.reload_coordinator)
```

### 🔍 Objeto: `corrections`

#### `corrections.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:248 (em module.find_real_problems)
```

### 🔍 Objeto: `criteria`

#### `criteria.items` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:681 (em IntelligenceProcessor._evaluate_option)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:597 (em DataProcessor._apply_filters)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:213 (em SessionMemory.search_sessions)
```

#### `criteria.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:228 (em IntelligenceProcessor.make_intelligent_decision)
```

### 🔍 Objeto: `criterios`

#### `criterios.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:256 (em IntentionAnalyzer._deve_usar_sistema_avancado)
```

### 🔍 Objeto: `current_app`

#### `current_app.app_context` (19 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_context_wrapper.py:52 (em FlaskContextWrapper.get_db_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_context_wrapper.py:92 (em FlaskContextWrapper.execute_in_app_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:276 (em LearningCore._atualizar_metricas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:322 (em LearningCore._salvar_historico_aprendizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:269 (em PatternLearner._salvar_padrao_otimizado)
  ... e mais 14 ocorrências
```

#### `current_app.config` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:218 (em DependencyChecker.check_database_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_context_wrapper.py:26 (em FlaskContextWrapper._init_flask_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_context_wrapper.py:41 (em FlaskContextWrapper.get_app_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:159 (em FlaskFallback.get_model)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:224 (em FlaskFallback.get_db)
  ... e mais 3 ocorrências
```

#### `current_app.config.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:218 (em DependencyChecker.check_database_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:307 (em FlaskFallback.get_config)
```

#### `current_app.name` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_context_wrapper.py:76 (em FlaskContextWrapper.get_flask_context_info)
```

#### `current_app.debug` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_context_wrapper.py:77 (em FlaskContextWrapper.get_flask_context_info)
```

### 🔍 Objeto: `current_dir`

#### `current_dir.parent` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:16 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:17 (em module.top-level)
```

#### `current_dir.parent.parent` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:17 (em module.top-level)
```

### 🔍 Objeto: `current_results`

#### `current_results.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:310 (em AnalyzerManager._should_use_nlp_analysis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:315 (em AnalyzerManager._should_use_nlp_analysis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:337 (em AnalyzerManager._should_use_advanced_analysis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:342 (em AnalyzerManager._should_use_advanced_analysis)
```

### 🔍 Objeto: `current_user`

#### `current_user.id` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:412 (em WebFlaskRoutes.api_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:439 (em WebFlaskRoutes.clear_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:514 (em WebFlaskRoutes._build_user_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:530 (em WebFlaskRoutes._build_user_context)
```

#### `current_user.vendedor` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:216 (em ContextLoader._obter_filtros_usuario)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:114 (em ValidationUtils._obter_filtros_usuario)
```

#### `current_user.nome` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:515 (em WebFlaskRoutes._build_user_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:116 (em ValidationUtils._obter_filtros_usuario)
```

#### `current_user.is_authenticated` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:378 (em SecurityGuard._is_user_authenticated)
```

#### `current_user.perfil` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:393 (em SecurityGuard._is_user_admin)
```

### 🔍 Objeto: `cycle`

#### `cycle.index` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:174 (em CircularDependencyMapper.analyze_circular_dependencies)
```

### 🔍 Objeto: `cycles`

#### `cycles.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:138 (em CircularDependencyMapper.dfs)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:146 (em CircularDependencyMapper.dfs)
```

### 🔍 Objeto: `d`

#### `d.startswith` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:121 (em DependencyChecker.check_fallback_quality)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:159 (em module.find_real_problems)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:45 (em ImportChecker.check_directory)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:300 (em FileScanner.search_in_files)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:63 (em StructureScanner.discover_project_structure)
```

#### `d.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:435 (em ContextProcessor._carregar_dados_geral)
```

#### `d.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:214 (em StructureScanner._parse_models_file)
```

### 🔍 Objeto: `dados`

#### `dados.get` (29 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:145 (em ResponseProcessor._obter_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:233 (em ContextProcessor.carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:67 (em module._carregar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:68 (em module._carregar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:84 (em module._carregar_dados_fretes)
  ... e mais 24 ocorrências
```

#### `dados.get().get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:457 (em SemanticEnricher._calcular_estatisticas_batch)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:460 (em SemanticEnricher._calcular_estatisticas_batch)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:463 (em SemanticEnricher._calcular_estatisticas_batch)
```

### 🔍 Objeto: `dados_agendamentos`

#### `dados_agendamentos.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:109 (em EntregasAgent._resumir_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:110 (em EntregasAgent._resumir_dados_reais)
```

### 🔍 Objeto: `dados_completos`

#### `dados_completos.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:465 (em ContextLoader._carregar_contexto_inteligente)
```

### 🔍 Objeto: `dados_cotacoes`

#### `dados_cotacoes.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/pedidos_agent.py:56 (em PedidosAgent._resumir_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/pedidos_agent.py:57 (em PedidosAgent._resumir_dados_reais)
```

### 🔍 Objeto: `dados_embarques`

#### `dados_embarques.get` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:340 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:341 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:412 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/embarques_agent.py:39 (em EmbarquesAgent._resumir_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/embarques_agent.py:40 (em EmbarquesAgent._resumir_dados_reais)
  ... e mais 2 ocorrências
```

### 🔍 Objeto: `dados_entregas`

#### `dados_entregas.get` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:369 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:370 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:374 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:375 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:441 (em ContextLoader._carregar_contexto_inteligente)
  ... e mais 6 ocorrências
```

### 🔍 Objeto: `dados_faturamento`

#### `dados_faturamento.get` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:346 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:347 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:418 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/financeiro_agent.py:39 (em FinanceiroAgent._resumir_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/financeiro_agent.py:40 (em FinanceiroAgent._resumir_dados_reais)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `dados_financeiro`

#### `dados_financeiro.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:352 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:353 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:424 (em ContextLoader._carregar_contexto_inteligente)
```

### 🔍 Objeto: `dados_fretes`

#### `dados_fretes.get` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:328 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:329 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:399 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:400 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/fretes_agent.py:39 (em FretesAgent._resumir_dados_reais)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `dados_geral`

#### `dados_geral.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:435 (em ContextProcessor._carregar_dados_geral)
```

### 🔍 Objeto: `dados_json`

#### `dados_json.append` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:449 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:230 (em AgendamentosLoader._format_agendamentos_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:224 (em FaturamentoLoader._format_faturamento_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:267 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:236 (em PedidosLoader._format_pedidos_results)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `dados_pedidos`

#### `dados_pedidos.get` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:322 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:323 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:392 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:393 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/pedidos_agent.py:39 (em PedidosAgent._resumir_dados_reais)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `dados_pendencias`

#### `dados_pendencias.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/financeiro_agent.py:55 (em FinanceiroAgent._resumir_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/financeiro_agent.py:56 (em FinanceiroAgent._resumir_dados_reais)
```

### 🔍 Objeto: `dados_reais`

#### `dados_reais.get` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:295 (em ResponseProcessor._construir_prompt_otimizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:296 (em ResponseProcessor._construir_prompt_otimizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:299 (em ResponseProcessor._construir_prompt_otimizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:300 (em ResponseProcessor._construir_prompt_otimizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:314 (em ResponseProcessor._construir_prompt_otimizado)
  ... e mais 6 ocorrências
```

### 🔍 Objeto: `dados_transportadoras`

#### `dados_transportadoras.get` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:334 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:335 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:406 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:117 (em EntregasAgent._resumir_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:118 (em EntregasAgent._resumir_dados_reais)
  ... e mais 2 ocorrências
```

### 🔍 Objeto: `dados_volumes`

#### `dados_volumes.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/embarques_agent.py:56 (em EmbarquesAgent._resumir_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/embarques_agent.py:57 (em EmbarquesAgent._resumir_dados_reais)
```

### 🔍 Objeto: `daily_data`

#### `daily_data.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:370 (em PerformanceAnalyzer.detect_anomalies)
```

#### `daily_data.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:403 (em PerformanceAnalyzer._analyze_trends)
```

### 🔍 Objeto: `data`

#### `data.get` (37 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:175 (em ImportFilterer.analyze_real_problems)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:74 (em module.create_processor_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:75 (em module.create_processor_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:76 (em module.create_processor_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:350 (em WebFlaskRoutes.api_query)
  ... e mais 32 ocorrências
```

#### `data.values` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:198 (em StructuralAnalyzer._count_nested_levels)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:206 (em StructuralAnalyzer._analyze_data_types)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:225 (em StructuralAnalyzer._detect_structural_issues)
```

#### `data.strip` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:72 (em BaseValidationUtils._basic_validation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:259 (em BaseProcessor._validate_input)
```

#### `data.get().get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:175 (em ImportFilterer.analyze_real_problems)
```

#### `data.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:220 (em StructuralAnalyzer._detect_structural_issues)
```

#### `data.strftime` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:278 (em BaseCommand._format_date_br)
```

#### `data.get().strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:350 (em WebFlaskRoutes.api_query)
```

#### `data.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:663 (em SystemConfig._flatten_dict)
```

#### `data.copy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/enricher_manager.py:59 (em EnricherManager.enrich_context)
```

### 🔍 Objeto: `data_consistency`

#### `data_consistency.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:92 (em CriticAgent.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:101 (em CriticAgent.top-level)
```

### 🔍 Objeto: `data_context`

#### `data_context.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/structural_validator.py:109 (em StructuralAI._validate_data_relationships)
```

### 🔍 Objeto: `data_dict`

#### `data_dict.items` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:377 (em IntelligenceProcessor._normalize_dict_for_intelligence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:382 (em DataProcessor._clean_dict)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:471 (em DataProcessor._normalize_dict)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:561 (em DataProcessor._transform_dict_schema)
```

### 🔍 Objeto: `data_loaded`

#### `data_loaded.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:422 (em MainOrchestrator.process_query)
```

### 🔍 Objeto: `data_manager`

#### `data_manager.load_data` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/__init__.py:200 (em module.load_data)
```

### 🔍 Objeto: `data_processor`

#### `data_processor.set_enricher` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:289 (em ProcessorManager.set_enricher)
```

### 🔍 Objeto: `data_provider`

#### `data_provider.get_data_by_domain` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:143 (em ResponseProcessor._obter_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:65 (em module._carregar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:82 (em module._carregar_dados_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:98 (em module._carregar_dados_transportadoras)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:114 (em module._carregar_dados_embarques)
  ... e mais 2 ocorrências
```

#### `data_provider.get_entregas_recentes` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:526 (em ResponseProcessor._processar_consulta_entregas)
```

#### `data_provider.set_loader` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1421 (em MainOrchestrator._connect_modules)
```

### 🔍 Objeto: `data_result`

#### `data_result.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:218 (em ProviderManager._provide_data_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:252 (em ProviderManager._provide_context_with_data)
```

### 🔍 Objeto: `database_data`

#### `database_data.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:299 (em SemanticEnricher._sugestoes_qualidade_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:340 (em SemanticEnricher._sugestoes_campos_similares)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:377 (em SemanticEnricher._sugestoes_otimizacao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:389 (em SemanticEnricher._sugestoes_otimizacao)
```

### 🔍 Objeto: `database_scanner`

#### `database_scanner.obter_estatisticas_gerais` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:236 (em DiagnosticsAnalyzer.gerar_relatorio_enriquecido)
```

#### `database_scanner.buscar_campos_por_nome` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:165 (em SemanticEnricher._enriquecer_via_banco)
```

#### `database_scanner.analisar_dados_reais` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:181 (em SemanticEnricher._enriquecer_via_banco)
```

#### `database_scanner.listar_tabelas` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:243 (em SemanticValidator.validar_consistencia_readme_banco)
```

#### `database_scanner.obter_campos_tabela` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:314 (em SemanticValidator._validar_campos_modelo_tabela)
```

### 🔍 Objeto: `database_url`

#### `database_url.startswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:112 (em DatabaseConnection._try_direct_connection)
```

#### `database_url.replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:113 (em DatabaseConnection._try_direct_connection)
```

### 🔍 Objeto: `date_consistency`

#### `date_consistency.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:91 (em CriticAgent.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:100 (em CriticAgent.top-level)
```

### 🔍 Objeto: `date_obj`

#### `date_obj.strftime` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:386 (em BaseProcessor._format_date_br)
```

### 🔍 Objeto: `datetime`

#### `datetime.now().isoformat` (299 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:28 (em DeepValidator.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:248 (em ClassDuplicateFinder.save_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:47 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:132 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:239 (em module.run_complete_flow)
  ... e mais 294 ocorrências
```

#### `datetime.now().strftime` (44 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:465 (em DeepValidator._generate_final_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:172 (em ClassDuplicateFinder.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:37 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:243 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:198 (em UninitializedVariableFinder.generate_report)
  ... e mais 39 ocorrências
```

#### `datetime.now().timestamp` (17 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:467 (em SuggestionsManager._enrich_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:493 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:497 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:25 (em ProcessorCoordinator.execute_processor_chain)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:165 (em ProcessorCoordinator.execute_parallel_processors)
  ... e mais 12 ocorrências
```

#### `datetime.now().date` (17 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/base.py:59 (em ProcessorBase._extract_filters)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/base.py:60 (em ProcessorBase._extract_filters)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/base.py:63 (em ProcessorBase._extract_filters)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/base.py:64 (em ProcessorBase._extract_filters)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/base.py:67 (em ProcessorBase._extract_filters)
  ... e mais 12 ocorrências
```

#### `datetime.now().hour` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:401 (em SuggestionsManager._analyze_context)
```

#### `datetime.now().weekday` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:402 (em SuggestionsManager._analyze_context)
```

### 🔍 Objeto: `db`

#### `db.session.query` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:207 (em ContextProcessor.carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:284 (em ContextProcessor._carregar_dados_entregas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:321 (em ContextProcessor._carregar_dados_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:358 (em ContextProcessor._carregar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:395 (em ContextProcessor._carregar_dados_financeiro)
  ... e mais 1 ocorrências
```

#### `db.session.execute` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:186 (em EntregasLoader._load_with_app_context)
```

### 🔍 Objeto: `db_conn`

#### `db_conn.get_inspector` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:553 (em DataAnalyzer.analisar_tabela_completa)
```

### 🔍 Objeto: `db_info`

#### `db_info.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:375 (em ScanningManager.get_database_info)
```

### 🔍 Objeto: `db_obj`

#### `db_obj.engine` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:440 (em SuggestionsEngine._get_data_analyzer)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:441 (em SuggestionsEngine._get_data_analyzer)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:76 (em WebIntegrationAdapter._get_integration_manager)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:88 (em DatabaseConnection._try_flask_connection)
```

#### `db_obj.session` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:77 (em WebIntegrationAdapter._get_integration_manager)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:89 (em DatabaseConnection._try_flask_connection)
```

### 🔍 Objeto: `db_status`

#### `db_status.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:352 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:353 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
```

### 🔍 Objeto: `db_uri`

#### `db_uri.split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:220 (em DependencyChecker.check_database_connection)
```

### 🔍 Objeto: `dependencies`

#### `dependencies.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:244 (em BaseProcessor._check_dependencies)
```

### 🔍 Objeto: `deps`

#### `deps.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:168 (em DependencyChecker.analyze_dependencies)
```

### 🔍 Objeto: `detected`

#### `detected.append` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:160 (em StructuralAnalyzer.detect_patterns)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:166 (em StructuralAnalyzer.detect_patterns)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:171 (em StructuralAnalyzer.detect_patterns)
```

### 🔍 Objeto: `detected_commands`

#### `detected_commands.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:312 (em AutoCommandProcessor._detect_commands)
```

### 🔍 Objeto: `detected_domains`

#### `detected_domains.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:221 (em ContextEnricher._enrich_domain_context)
```

### 🔍 Objeto: `detector`

#### `detector.detectar_grupo_na_consulta` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:583 (em ContextLoader._carregar_todos_clientes_sistema)
```

### 🔍 Objeto: `detector_grupos`

#### `detector_grupos.detectar_grupo_na_consulta` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:144 (em QueryAnalyzer._extract_entities)
```

### 🔍 Objeto: `df`

#### `df.columns` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:268 (em DataProcessor.aggregate_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:283 (em DataProcessor.aggregate_data)
```

#### `df.groupby().agg().reset_index` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:284 (em DataProcessor.aggregate_data)
```

#### `df.groupby().agg` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:284 (em DataProcessor.aggregate_data)
```

#### `df.groupby` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:284 (em DataProcessor.aggregate_data)
```

#### `df.agg().to_frame().T` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:287 (em DataProcessor.aggregate_data)
```

#### `df.agg().to_frame` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:287 (em DataProcessor.aggregate_data)
```

#### `df.agg` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:287 (em DataProcessor.aggregate_data)
```

### 🔍 Objeto: `diagnostico`

#### `diagnostico.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:186 (em DiagnosticsAnalyzer._determinar_status_geral)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:187 (em DiagnosticsAnalyzer._determinar_status_geral)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:294 (em ScanningManager.executar_diagnostico_completo)
```

### 🔍 Objeto: `dict_node`

#### `dict_node.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:209 (em CodeScanner._extract_dict_value)
```

#### `dict_node.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:209 (em CodeScanner._extract_dict_value)
```

### 🔍 Objeto: `dir_name`

#### `dir_name.startswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:77 (em module.contar_arquivos_detalhado)
```

### 🔍 Objeto: `directory`

#### `directory.rglob` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:35 (em ClassDuplicateFinder.scan_directory)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:97 (em UninitializedVariableFinder.scan_directory)
```

### 🔍 Objeto: `dirs`

#### `dirs.copy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:70 (em StructureScanner.discover_project_structure)
```

### 🔍 Objeto: `distribuicao`

#### `distribuicao.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:442 (em AutoMapper._melhorar_termos_com_analise)
```

### 🔍 Objeto: `doc`

#### `doc.ents` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:242 (em NLPEnhancedAnalyzer._extrair_entidades_spacy)
```

### 🔍 Objeto: `domain`

#### `domain.lower` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/__init__.py:101 (em module.get_best_mapper_for_domain)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:354 (em LoaderManager.get_loader)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/__init__.py:32 (em module.get_domain_mapper)
```

#### `domain.lower().strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:354 (em LoaderManager.get_loader)
```

#### `domain.title` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:149 (em CoordinatorManager._load_domain_agents)
```

#### `domain.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:259 (em ContextEnricher._calculate_context_score)
```

### 🔍 Objeto: `domain_data`

#### `domain_data.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:265 (em LoaderManager.load_multiple_domains)
```

### 🔍 Objeto: `domain_keywords`

#### `domain_keywords.items` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:131 (em QueryAnalyzer._detect_domains)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:306 (em LoaderManager.get_best_loader_for_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:241 (em CoordinatorManager._select_best_coordinator)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:219 (em ContextEnricher._enrich_domain_context)
```

### 🔍 Objeto: `domain_knowledge`

#### `domain_knowledge.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:96 (em SmartBaseAgent.process_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:288 (em SmartBaseAgent.top-level)
```

### 🔍 Objeto: `domain_loaders`

#### `domain_loaders.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/__init__.py:98 (em module.get_domain_loaders)
```

### 🔍 Objeto: `domain_mappers`

#### `domain_mappers.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/__init__.py:101 (em module.get_best_mapper_for_domain)
```

### 🔍 Objeto: `domain_scores`

#### `domain_scores.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:322 (em LoaderManager.get_best_loader_for_query)
```

### 🔍 Objeto: `domains`

#### `domains.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:133 (em QueryAnalyzer._detect_domains)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:252 (em SemanticAnalyzer._identify_domains)
```

#### `domains.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:114 (em MetacognitiveAnalyzer._assess_domain_coverage)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:184 (em PerformanceAnalyzer.analyze_ai_performance)
```

### 🔍 Objeto: `dominios`

#### `dominios.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:261 (em ContextProcessor._detectar_dominio)
```

### 🔍 Objeto: `duration`

#### `duration.seconds` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:188 (em ConversationMemory._calculate_duration)
```

### 🔍 Objeto: `durations`

#### `durations.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:698 (em SessionOrchestrator.get_session_stats)
```

### 🔍 Objeto: `e`

#### `e.data_entrega_prevista` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:261 (em ContextLoader._carregar_entregas_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:261 (em ContextLoader._carregar_entregas_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:131 (em ValidationUtils._calcular_metricas_prazo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:132 (em ValidationUtils._calcular_metricas_prazo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:138 (em ValidationUtils._calcular_metricas_prazo)
  ... e mais 2 ocorrências
```

#### `e.data_embarque` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:260 (em ContextLoader._carregar_entregas_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:260 (em ContextLoader._carregar_entregas_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:225 (em EntregasLoader._load_with_app_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:225 (em EntregasLoader._load_with_app_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:114 (em EmbarquesLoader._load_with_context)
  ... e mais 1 ocorrências
```

#### `e.data_hora_entrega_realizada` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:128 (em ValidationUtils._calcular_metricas_prazo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:131 (em ValidationUtils._calcular_metricas_prazo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:132 (em ValidationUtils._calcular_metricas_prazo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:138 (em ValidationUtils._calcular_metricas_prazo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:139 (em ValidationUtils._calcular_metricas_prazo)
```

#### `e.lead_time` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:148 (em ValidationUtils._calcular_metricas_prazo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:148 (em ValidationUtils._calcular_metricas_prazo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:148 (em ValidationUtils._calcular_metricas_prazo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:148 (em ValidationUtils._calcular_metricas_prazo)
```

#### `e.id` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:257 (em ContextLoader._carregar_entregas_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:219 (em EntregasLoader._load_with_app_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:112 (em EmbarquesLoader._load_with_context)
```

#### `e.data_embarque.isoformat` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:260 (em ContextLoader._carregar_entregas_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:225 (em EntregasLoader._load_with_app_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:114 (em EmbarquesLoader._load_with_context)
```

#### `e.data_hora_entrega_realizada.date` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:132 (em ValidationUtils._calcular_metricas_prazo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:138 (em ValidationUtils._calcular_metricas_prazo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:139 (em ValidationUtils._calcular_metricas_prazo)
```

#### `e.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:303 (em ResponseProcessor._construir_prompt_otimizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:304 (em ResponseProcessor._construir_prompt_otimizado)
```

#### `e.numero_nf` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:259 (em ContextLoader._carregar_entregas_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:220 (em EntregasLoader._load_with_app_context)
```

#### `e.entregue` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:262 (em ContextLoader._carregar_entregas_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:223 (em EntregasLoader._load_with_app_context)
```

#### `e.data_entrega_realizada` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:224 (em EntregasLoader._load_with_app_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:224 (em EntregasLoader._load_with_app_context)
```

#### `e.transportadora` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:116 (em EmbarquesLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:116 (em EmbarquesLoader._load_with_context)
```

#### `e.criado_em` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:122 (em EmbarquesLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:122 (em EmbarquesLoader._load_with_context)
```

#### `e.cliente` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:258 (em ContextLoader._carregar_entregas_banco)
```

#### `e.data_entrega_prevista.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:261 (em ContextLoader._carregar_entregas_banco)
```

#### `e.destino` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:222 (em EntregasLoader._load_with_app_context)
```

#### `e.data_entrega_realizada.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:224 (em EntregasLoader._load_with_app_context)
```

#### `e.valor_nf` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:226 (em EntregasLoader._load_with_app_context)
```

#### `e.peso_total` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:227 (em EntregasLoader._load_with_app_context)
```

#### `e.numero_embarque` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:113 (em EmbarquesLoader._load_with_context)
```

#### `e.transportadora_id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:115 (em EmbarquesLoader._load_with_context)
```

#### `e.transportadora.razao_social` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:116 (em EmbarquesLoader._load_with_context)
```

#### `e.status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:117 (em EmbarquesLoader._load_with_context)
```

#### `e.total_peso_pedidos` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:118 (em EmbarquesLoader._load_with_context)
```

#### `e.total_valor_pedidos` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:119 (em EmbarquesLoader._load_with_context)
```

#### `e.tipo_carga` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:120 (em EmbarquesLoader._load_with_context)
```

#### `e.placa_veiculo` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:121 (em EmbarquesLoader._load_with_context)
```

#### `e.criado_em.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:122 (em EmbarquesLoader._load_with_context)
```

### 🔍 Objeto: `elt`

#### `elt.func` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:196 (em CodeScanner._extract_validators)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:197 (em CodeScanner._extract_validators)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:198 (em CodeScanner._extract_validators)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:199 (em CodeScanner._extract_validators)
```

#### `elt.elts` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:224 (em CodeScanner._extract_choices)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:225 (em CodeScanner._extract_choices)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:226 (em CodeScanner._extract_choices)
```

#### `elt.func.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:197 (em CodeScanner._extract_validators)
```

#### `elt.func.attr` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:199 (em CodeScanner._extract_validators)
```

### 🔍 Objeto: `embarque`

#### `embarque.data_embarque` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:359 (em DataProvider._serialize_embarque)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:359 (em DataProvider._serialize_embarque)
```

#### `embarque.valor_total` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:362 (em DataProvider._serialize_embarque)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:362 (em DataProvider._serialize_embarque)
```

#### `embarque.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:357 (em DataProvider._serialize_embarque)
```

#### `embarque.numero` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:358 (em DataProvider._serialize_embarque)
```

#### `embarque.data_embarque.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:359 (em DataProvider._serialize_embarque)
```

#### `embarque.destino` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:360 (em DataProvider._serialize_embarque)
```

#### `embarque.status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:361 (em DataProvider._serialize_embarque)
```

### 🔍 Objeto: `end_date`

#### `end_date.replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:263 (em BaseValidationUtils.validate_date_range)
```

### 🔍 Objeto: `end_time`

#### `end_time.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:575 (em IntelligenceCoordinator._execute_component_operation)
```

### 🔍 Objeto: `engine`

#### `engine.generate_suggestions` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/__init__.py:101 (em module.generate_suggestions)
```

### 🔍 Objeto: `enriched`

#### `enriched.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:484 (em SuggestionsManager._enrich_suggestions)
```

#### `enriched.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/enricher_manager.py:88 (em EnricherManager.enrich_context)
```

#### `enriched.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/enricher_manager.py:99 (em EnricherManager.enrich_context)
```

### 🔍 Objeto: `enriched_context`

#### `enriched_context.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:58 (em ContextEnricher.enrich_context)
```

#### `enriched_context.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:242 (em ContextEnricher._calculate_context_score)
```

### 🔍 Objeto: `enrichments`

#### `enrichments.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:245 (em ContextEnricher._calculate_context_score)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:249 (em ContextEnricher._calculate_context_score)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:253 (em ContextEnricher._calculate_context_score)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:258 (em ContextEnricher._calculate_context_score)
```

### 🔍 Objeto: `enriquecimentos`

#### `enriquecimentos.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:456 (em SemanticEnricher._calcular_estatisticas_batch)
```

### 🔍 Objeto: `ent`

#### `ent.text` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:244 (em NLPEnhancedAnalyzer._extrair_entidades_spacy)
```

#### `ent.label_` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:245 (em NLPEnhancedAnalyzer._extrair_entidades_spacy)
```

#### `ent.start_char` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:246 (em NLPEnhancedAnalyzer._extrair_entidades_spacy)
```

#### `ent.end_char` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:247 (em NLPEnhancedAnalyzer._extrair_entidades_spacy)
```

### 🔍 Objeto: `entidades`

#### `entidades.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:243 (em NLPEnhancedAnalyzer._extrair_entidades_spacy)
```

### 🔍 Objeto: `entities`

#### `entities.append` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:147 (em QueryAnalyzer._extract_entities)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:152 (em QueryAnalyzer._extract_entities)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:161 (em QueryAnalyzer._extract_entities)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:174 (em QueryAnalyzer._extract_entities)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:179 (em QueryAnalyzer._extract_entities)
  ... e mais 2 ocorrências
```

#### `entities.extend` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/context_provider.py:495 (em ContextProvider._extract_simple_entities)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/context_provider.py:499 (em ContextProvider._extract_simple_entities)
```

### 🔍 Objeto: `entity_keywords`

#### `entity_keywords.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:149 (em ContextEnricher._enrich_semantic_context)
```

### 🔍 Objeto: `entrega`

#### `entrega.data_entrega_prevista` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:333 (em DataProvider._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:333 (em DataProvider._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:92 (em ValidationUtils._verificar_prazo_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:95 (em ValidationUtils._verificar_prazo_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:98 (em ValidationUtils._calcular_dias_atraso)
  ... e mais 2 ocorrências
```

#### `entrega.data_hora_entrega_realizada` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:334 (em DataProvider._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:334 (em DataProvider._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:92 (em ValidationUtils._verificar_prazo_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:95 (em ValidationUtils._verificar_prazo_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:98 (em ValidationUtils._calcular_dias_atraso)
  ... e mais 2 ocorrências
```

#### `entrega.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:312 (em ResponseProcessor._construir_prompt_otimizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:312 (em ResponseProcessor._construir_prompt_otimizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:312 (em ResponseProcessor._construir_prompt_otimizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/enricher_manager.py:143 (em EnricherManager._analyze_deliveries)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/enricher_manager.py:144 (em EnricherManager._analyze_deliveries)
```

#### `entrega.numero_nf` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:448 (em ContextProcessor._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:327 (em DataProvider._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:237 (em AgendamentosLoader._format_agendamentos_results)
```

#### `entrega.data_embarque` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:450 (em ContextProcessor._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:332 (em DataProvider._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:332 (em DataProvider._serialize_entrega)
```

#### `entrega.municipio` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:328 (em DataProvider._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:330 (em DataProvider._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:330 (em DataProvider._serialize_entrega)
```

#### `entrega.uf` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:329 (em DataProvider._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:330 (em DataProvider._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:330 (em DataProvider._serialize_entrega)
```

#### `entrega.data_hora_entrega_realizada.date` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:95 (em ValidationUtils._verificar_prazo_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:101 (em ValidationUtils._calcular_dias_atraso)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:102 (em ValidationUtils._calcular_dias_atraso)
```

#### `entrega.id` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:447 (em ContextProcessor._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:325 (em DataProvider._serialize_entrega)
```

#### `entrega.status_finalizacao` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:451 (em ContextProcessor._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:331 (em DataProvider._serialize_entrega)
```

#### `entrega.entregue` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:452 (em ContextProcessor._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:338 (em DataProvider._serialize_entrega)
```

#### `entrega.cliente` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:326 (em DataProvider._serialize_entrega)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:236 (em AgendamentosLoader._format_agendamentos_results)
```

#### `entrega.nome_cliente` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:449 (em ContextProcessor._serialize_entrega)
```

#### `entrega.data_embarque.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:332 (em DataProvider._serialize_entrega)
```

#### `entrega.data_entrega_prevista.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:333 (em DataProvider._serialize_entrega)
```

#### `entrega.data_hora_entrega_realizada.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:334 (em DataProvider._serialize_entrega)
```

#### `entrega.vendedor` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:335 (em DataProvider._serialize_entrega)
```

#### `entrega.transportadora` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:336 (em DataProvider._serialize_entrega)
```

#### `entrega.valor_nf` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:337 (em DataProvider._serialize_entrega)
```

#### `entrega.cnpj_cliente` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:339 (em DataProvider._serialize_entrega)
```

#### `entrega.destino` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:238 (em AgendamentosLoader._format_agendamentos_results)
```

### 🔍 Objeto: `entregas_cache`

#### `entregas_cache.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:364 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:435 (em ContextLoader._carregar_contexto_inteligente)
```

### 🔍 Objeto: `errors`

#### `errors.append` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:480 (em AutoCommandProcessor._validate_command_syntax)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:483 (em AutoCommandProcessor._validate_command_syntax)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:487 (em AutoCommandProcessor._validate_command_syntax)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:201 (em TestLoopPrevention.make_request)
```

### 🔍 Objeto: `erros`

#### `erros.append` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:179 (em BaseMapper.validar_mapeamentos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:182 (em BaseMapper.validar_mapeamentos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:184 (em BaseMapper.validar_mapeamentos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:186 (em BaseMapper.validar_mapeamentos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:189 (em BaseMapper.validar_mapeamentos)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `esqueleto`

#### `esqueleto.gerar_excel_faturamento` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:159 (em ExcelOrchestrator._processar_excel_interno)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:229 (em ExcelOrchestrator._tentar_fallback_esqueletos)
```

#### `esqueleto.gerar_excel_fretes` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:161 (em ExcelOrchestrator._processar_excel_interno)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:223 (em ExcelOrchestrator._tentar_fallback_esqueletos)
```

#### `esqueleto.gerar_excel_pedidos` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:163 (em ExcelOrchestrator._processar_excel_interno)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:225 (em ExcelOrchestrator._tentar_fallback_esqueletos)
```

#### `esqueleto.gerar_excel_entregas` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:165 (em ExcelOrchestrator._processar_excel_interno)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:227 (em ExcelOrchestrator._tentar_fallback_esqueletos)
```

### 🔍 Objeto: `estado`

#### `estado.upper` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:192 (em QueryAnalyzer._extract_entities)
```

#### `estado.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:155 (em BaseCommand._extract_filters_advanced)
```

### 🔍 Objeto: `estatisticas`

#### `estatisticas.get` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:157 (em DiagnosticsAnalyzer._avaliar_qualidade_geral)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:162 (em DiagnosticsAnalyzer._avaliar_qualidade_geral)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:164 (em DiagnosticsAnalyzer._avaliar_qualidade_geral)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:437 (em LearningCore._avaliar_saude_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:442 (em LearningCore._avaliar_saude_sistema)
  ... e mais 1 ocorrências
```

#### `estatisticas.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:416 (em DatabaseScanner.obter_estatisticas_gerais)
```

### 🔍 Objeto: `etapa_config`

#### `etapa_config.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:180 (em WorkflowOrchestrator._executar_etapas_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:202 (em WorkflowOrchestrator._executar_etapas_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:211 (em WorkflowOrchestrator._executar_etapas_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:235 (em WorkflowOrchestrator._executar_etapa)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:236 (em WorkflowOrchestrator._executar_etapa)
```

### 🔍 Objeto: `etapas_concluidas`

#### `etapas_concluidas.add` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:193 (em WorkflowOrchestrator._executar_etapas_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:207 (em WorkflowOrchestrator._executar_etapas_workflow)
```

### 🔍 Objeto: `existe`

#### `existe.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:85 (em KnowledgeMemory.aprender_mapeamento_cliente)
```

### 🔍 Objeto: `existing_pattern`

#### `existing_pattern.examples.extend` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:207 (em HumanInLoopLearning._create_learning_pattern)
```

#### `existing_pattern.examples` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:207 (em HumanInLoopLearning._create_learning_pattern)
```

#### `existing_pattern.confidence_score` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:208 (em HumanInLoopLearning._create_learning_pattern)
```

#### `existing_pattern.frequency` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:209 (em HumanInLoopLearning._create_learning_pattern)
```

### 🔍 Objeto: `expansions`

#### `expansions.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:215 (em SemanticLoopProcessor._expand_unmapped_terms)
```

### 🔍 Objeto: `expired_keys`

#### `expired_keys.append` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:725 (em SuggestionsManager._optimize_cache)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:166 (em ScannersCache._cleanup_expired_cache)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:913 (em IntelligenceCoordinator._optimize_ai_cache)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:350 (em SystemMemory.cleanup_expired_data)
```

### 🔍 Objeto: `expired_sessions`

#### `expired_sessions.append` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:339 (em ConversationManager.cleanup_expired_conversations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:652 (em SessionOrchestrator.cleanup_expired_sessions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:245 (em ContextMemory.cleanup_expired_contexts)
```

### 🔍 Objeto: `external_api`

#### `external_api.process_query` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:188 (em StandaloneIntegration.process_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:121 (em WebIntegrationAdapter.process_query_sync)
```

#### `external_api.initialize_complete_system` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:118 (em StandaloneIntegration.initialize_system)
```

#### `external_api.get_system_status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:232 (em WebIntegrationAdapter.get_system_status)
```

#### `external_api.claude_client` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:284 (em WebIntegrationAdapter.claude_client)
```

### 🔍 Objeto: `f`

#### `f.write` (43 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:263 (em ImportFilterer.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:244 (em ClassDuplicateFinder.save_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:242 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:293 (em UninitializedVariableFinder.save_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:322 (em DependencyChecker._create_markdown_report)
  ... e mais 38 ocorrências
```

#### `f.read` (19 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:46 (em ClassDuplicateFinder.scan_file)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_finais_v2.py:36 (em module.verificar_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:97 (em module.analyze_file)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:108 (em UninitializedVariableFinder.scan_file)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:128 (em DependencyChecker.check_fallback_quality)
  ... e mais 14 ocorrências
```

#### `f.feedback_text` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:154 (em HumanInLoopLearning._analyze_feedback_patterns)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:162 (em HumanInLoopLearning._analyze_feedback_patterns)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:168 (em HumanInLoopLearning._analyze_feedback_patterns)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:176 (em HumanInLoopLearning._analyze_feedback_patterns)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:182 (em HumanInLoopLearning._analyze_feedback_patterns)
  ... e mais 1 ocorrências
```

#### `f.endswith` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:71 (em StructureScanner.discover_project_structure)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:72 (em StructureScanner.discover_project_structure)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:73 (em StructureScanner.discover_project_structure)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:74 (em StructureScanner.discover_project_structure)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:75 (em StructureScanner.discover_project_structure)
```

#### `f.feedback_text.lower` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:154 (em HumanInLoopLearning._analyze_feedback_patterns)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:168 (em HumanInLoopLearning._analyze_feedback_patterns)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:182 (em HumanInLoopLearning._analyze_feedback_patterns)
```

#### `f.readlines` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:162 (em module.contar_linhas_codigo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:197 (em module.verificar_modulos_especiais)
```

#### `f.id` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:106 (em FaturamentoLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:114 (em FretesLoader._load_with_context)
```

#### `f.nome_cliente` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:108 (em FaturamentoLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:116 (em FretesLoader._load_with_context)
```

#### `f.cnpj_cliente` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:109 (em FaturamentoLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:117 (em FretesLoader._load_with_context)
```

#### `f.data_fatura` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:112 (em FaturamentoLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:112 (em FaturamentoLoader._load_with_context)
```

#### `f.status` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:115 (em FaturamentoLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:119 (em FretesLoader._load_with_context)
```

#### `f.transportadora` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:118 (em FretesLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:118 (em FretesLoader._load_with_context)
```

#### `f.vencimento` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:124 (em FretesLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:124 (em FretesLoader._load_with_context)
```

#### `f.criado_em` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:125 (em FretesLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:125 (em FretesLoader._load_with_context)
```

#### `f.feedback_type` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:155 (em HumanInLoopLearning._analyze_feedback_patterns)
```

#### `f.feedback_id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:283 (em HumanInLoopLearning.apply_improvement)
```

#### `f.timestamp` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:296 (em HumanInLoopLearning.generate_learning_report)
```

#### `f.numero_nf` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:107 (em FaturamentoLoader._load_with_context)
```

#### `f.origem` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:110 (em FaturamentoLoader._load_with_context)
```

#### `f.destino` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:111 (em FaturamentoLoader._load_with_context)
```

#### `f.data_fatura.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:112 (em FaturamentoLoader._load_with_context)
```

#### `f.valor_total` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:113 (em FaturamentoLoader._load_with_context)
```

#### `f.peso_total` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:114 (em FaturamentoLoader._load_with_context)
```

#### `f.incoterm` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:116 (em FaturamentoLoader._load_with_context)
```

#### `f.numero_cte` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:115 (em FretesLoader._load_with_context)
```

#### `f.transportadora.razao_social` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:118 (em FretesLoader._load_with_context)
```

#### `f.valor_cotado` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:120 (em FretesLoader._load_with_context)
```

#### `f.valor_cte` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:121 (em FretesLoader._load_with_context)
```

#### `f.valor_considerado` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:122 (em FretesLoader._load_with_context)
```

#### `f.valor_pago` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:123 (em FretesLoader._load_with_context)
```

#### `f.vencimento.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:124 (em FretesLoader._load_with_context)
```

#### `f.criado_em.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:125 (em FretesLoader._load_with_context)
```

### 🔍 Objeto: `factories`

#### `factories.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:106 (em SpecialistCoordinator.get_agent)
```

### 🔍 Objeto: `fallback`

#### `fallback.is_flask_available` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/__init__.py:133 (em module.initialize_flask_fallback)
```

#### `fallback.value` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:431 (em OrchestratorManager._detect_appropriate_orchestrator)
```

### 🔍 Objeto: `fatores`

#### `fatores.append` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:499 (em FieldSearcher._analisar_fatores_similaridade)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:503 (em FieldSearcher._analisar_fatores_similaridade)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:505 (em FieldSearcher._analisar_fatores_similaridade)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:508 (em FieldSearcher._analisar_fatores_similaridade)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:511 (em FieldSearcher._analisar_fatores_similaridade)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `faturamento`

#### `faturamento.data_fatura` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:371 (em DataProvider._serialize_faturamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:371 (em DataProvider._serialize_faturamento)
```

#### `faturamento.valor_total` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:372 (em DataProvider._serialize_faturamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:372 (em DataProvider._serialize_faturamento)
```

#### `faturamento.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:368 (em DataProvider._serialize_faturamento)
```

#### `faturamento.numero_nf` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:369 (em DataProvider._serialize_faturamento)
```

#### `faturamento.nome_cliente` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:370 (em DataProvider._serialize_faturamento)
```

#### `faturamento.data_fatura.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:371 (em DataProvider._serialize_faturamento)
```

#### `faturamento.origem` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:373 (em DataProvider._serialize_faturamento)
```

#### `faturamento.incoterm` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:374 (em DataProvider._serialize_faturamento)
```

### 🔍 Objeto: `feedback`

#### `feedback.get` (10 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:212 (em AdaptiveLearning.update_learning_from_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:218 (em AdaptiveLearning.update_learning_from_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:219 (em AdaptiveLearning.update_learning_from_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:516 (em AdaptiveLearning._handle_negative_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:520 (em AdaptiveLearning._handle_negative_feedback)
  ... e mais 5 ocorrências
```

#### `feedback.feedback_text` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:132 (em HumanInLoopLearning._process_critical_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:141 (em HumanInLoopLearning._process_critical_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:380 (em HumanInLoopLearning._analyze_trends)
```

#### `feedback.severity` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:109 (em HumanInLoopLearning.capture_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:315 (em HumanInLoopLearning.generate_learning_report)
```

#### `feedback.feedback_id` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:126 (em HumanInLoopLearning._process_critical_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:131 (em HumanInLoopLearning._process_critical_feedback)
```

#### `feedback.timestamp` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:134 (em HumanInLoopLearning._process_critical_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:365 (em HumanInLoopLearning._analyze_trends)
```

#### `feedback.feedback_type` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:311 (em HumanInLoopLearning.generate_learning_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:414 (em HumanInLoopLearning._calculate_satisfaction_score)
```

#### `feedback.suggested_improvement` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:133 (em HumanInLoopLearning._process_critical_feedback)
```

#### `feedback.timestamp.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:134 (em HumanInLoopLearning._process_critical_feedback)
```

#### `feedback.context` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:135 (em HumanInLoopLearning._process_critical_feedback)
```

#### `feedback.feedback_type.value` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:311 (em HumanInLoopLearning.generate_learning_report)
```

#### `feedback.severity.value` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:315 (em HumanInLoopLearning.generate_learning_report)
```

#### `feedback.user_id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:319 (em HumanInLoopLearning.generate_learning_report)
```

#### `feedback.timestamp.strftime` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:365 (em HumanInLoopLearning._analyze_trends)
```

#### `feedback.feedback_text.lower().split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:380 (em HumanInLoopLearning._analyze_trends)
```

#### `feedback.feedback_text.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:380 (em HumanInLoopLearning._analyze_trends)
```

### 🔍 Objeto: `feedback_processor`

#### `feedback_processor.processar_feedback_completo` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:569 (em WebFlaskRoutes._record_feedback)
```

### 🔍 Objeto: `field_info`

#### `field_info.get` (13 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:154 (em CodeScanner._parse_form_field)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:154 (em CodeScanner._parse_form_field)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:157 (em CodeScanner._parse_form_field)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:158 (em CodeScanner._parse_form_field)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:159 (em CodeScanner._parse_form_field)
  ... e mais 8 ocorrências
```

### 🔍 Objeto: `field_mapper`

#### `field_mapper.map_fields` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/__init__.py:84 (em module.map_query_fields)
```

### 🔍 Objeto: `field_mapping`

#### `field_mapping.source_field` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:91 (em FieldMapper.add_mapping)
```

#### `field_mapping.target_field` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:91 (em FieldMapper.add_mapping)
```

### 🔍 Objeto: `fila`

#### `fila.pop` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:383 (em RelationshipMapper.obter_caminho_relacionamentos)
```

#### `fila.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:404 (em RelationshipMapper.obter_caminho_relacionamentos)
```

### 🔍 Objeto: `file`

#### `file.endswith` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:65 (em module.contar_arquivos_detalhado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:158 (em module.contar_linhas_codigo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:193 (em module.verificar_modulos_especiais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_finais_v2.py:31 (em module.verificar_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:124 (em DependencyChecker.check_fallback_quality)
  ... e mais 4 ocorrências
```

#### `file.startswith` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:69 (em module.contar_arquivos_detalhado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_finais_v2.py:31 (em module.verificar_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:162 (em module.find_real_problems)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:48 (em ImportChecker.check_directory)
```

#### `file.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:203 (em module.verificar_modulos_especiais)
```

### 🔍 Objeto: `file_errors`

#### `file_errors.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:78 (em ImportChecker.check_file)
```

### 🔍 Objeto: `file_module`

#### `file_module.split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:158 (em ImportChecker.check_import)
```

### 🔍 Objeto: `file_path`

#### `file_path.relative_to` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:136 (em DependencyChecker.check_fallback_quality)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:104 (em CircularDependencyMapper.build_dependency_graph)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:57 (em FileScanner.discover_all_templates)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:315 (em FileScanner.search_in_files)
```

#### `file_path.exists` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:200 (em module.verificar_import_existe)
```

#### `file_path.parts` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:43 (em CircularDependencyMapper.extract_imports)
```

#### `file_path.stat().st_size` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:61 (em FileScanner.discover_all_templates)
```

#### `file_path.stat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:61 (em FileScanner.discover_all_templates)
```

### 🔍 Objeto: `file_types`

#### `file_types.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:261 (em FileScanner.list_directory_contents)
```

### 🔍 Objeto: `filepath`

#### `filepath.relative_to` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:86 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:236 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:247 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:164 (em module.find_real_problems)
```

### 🔍 Objeto: `filtered_data`

#### `filtered_data.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:331 (em DataProcessor.filter_data)
```

### 🔍 Objeto: `filtered_queue`

#### `filtered_queue.sort` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:259 (em HumanInLoopLearning.get_improvement_suggestions)
```

### 🔍 Objeto: `filterer`

#### `filterer.analyze_real_problems` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:280 (em module.main)
```

#### `filterer.generate_report` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:284 (em module.main)
```

### 🔍 Objeto: `filters`

#### `filters.get` (54 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:172 (em DataProvider._get_entregas_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:174 (em DataProvider._get_entregas_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:176 (em DataProvider._get_entregas_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:178 (em DataProvider._get_entregas_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:199 (em DataProvider._get_pedidos_data)
  ... e mais 49 ocorrências
```

#### `filters.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:589 (em DataProcessor._apply_filters)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:147 (em DatabaseLoader.load_table_data)
```

#### `filters.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/__init__.py:194 (em module.load_data)
```

### 🔍 Objeto: `filtros`

#### `filtros.get` (42 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:176 (em BaseCommand._log_command)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:177 (em BaseCommand._log_command)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:173 (em CursorCommands._analisar_codigo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:164 (em DevCommands._construir_contexto_projeto)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:342 (em DevCommands._template_modulo_fallback)
  ... e mais 37 ocorrências
```

#### `filtros.items` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:306 (em ExcelOrchestrator._gerar_excel_geral_multi)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:243 (em BaseCommand._generate_cache_key)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:366 (em module.create_excel_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:108 (em ExcelFretes._gerar_excel_fretes_interno)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:112 (em ExcelPedidos._gerar_excel_pedidos_interno)
  ... e mais 2 ocorrências
```

#### `filtros.get().lower().replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:342 (em DevCommands._template_modulo_fallback)
```

#### `filtros.get().lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:342 (em DevCommands._template_modulo_fallback)
```

### 🔍 Objeto: `filtros_usuario`

#### `filtros_usuario.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:191 (em ValidationUtils._calcular_estatisticas_especificas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:206 (em ValidationUtils._calcular_estatisticas_especificas)
```

### 🔍 Objeto: `finder`

#### `finder.stats` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:279 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:279 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:324 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:325 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:326 (em module.main)
  ... e mais 2 ocorrências
```

#### `finder.duplicates` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:284 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:285 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:289 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:294 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:295 (em module.main)
```

#### `finder.root_path.absolute` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:276 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:321 (em module.main)
```

#### `finder.root_path` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:276 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:321 (em module.main)
```

#### `finder.scan_directory` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:277 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:322 (em module.main)
```

#### `finder.save_results` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:301 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:336 (em module.main)
```

#### `finder.problems` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:174 (em module.find_real_problems)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:175 (em module.find_real_problems)
```

#### `finder.find_duplicates` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:282 (em module.main)
```

#### `finder.duplicates.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:289 (em module.main)
```

#### `finder.uninitialized_vars` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:329 (em module.main)
```

#### `finder.visit` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:172 (em module.find_real_problems)
```

### 🔍 Objeto: `first_arg`

#### `first_arg.value` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:305 (em StructureScanner._extract_field_info)
```

#### `first_arg.s` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:307 (em StructureScanner._extract_field_info)
```

### 🔍 Objeto: `fk`

#### `fk.get` (13 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:297 (em DatabaseScanner._analyze_relationships)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:302 (em DatabaseScanner._analyze_relationships)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:303 (em DatabaseScanner._analyze_relationships)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:80 (em RelationshipMapper.obter_relacionamentos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:81 (em RelationshipMapper.obter_relacionamentos)
  ... e mais 8 ocorrências
```

### 🔍 Objeto: `flask`

#### `flask.request.headers.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:786 (em SessionOrchestrator._get_user_agent)
```

#### `flask.request.headers` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:786 (em SessionOrchestrator._get_user_agent)
```

#### `flask.request` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:786 (em SessionOrchestrator._get_user_agent)
```

### 🔍 Objeto: `flask_fallback`

#### `flask_fallback.is_flask_available` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/__init__.py:260 (em module.top-level)
```

### 🔍 Objeto: `flask_status`

#### `flask_status.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:201 (em CursorMonitor.display_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:202 (em CursorMonitor.display_status)
```

#### `flask_status.get().upper` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:202 (em CursorMonitor.display_status)
```

### 🔍 Objeto: `flattened`

#### `flattened.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:667 (em SystemConfig._flatten_dict)
```

### 🔍 Objeto: `fnmatch`

#### `fnmatch.fnmatch` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:725 (em SystemConfig._key_matches_pattern)
```

### 🔍 Objeto: `focused_insights`

#### `focused_insights.extend` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:636 (em IntelligenceProcessor._focused_synthesis)
```

### 🔍 Objeto: `folder_stats`

#### `folder_stats.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:225 (em ClassDuplicateFinder.generate_report)
```

### 🔍 Objeto: `forms`

#### `forms.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:54 (em CodeScanner.discover_all_forms)
```

### 🔍 Objeto: `forms_file`

#### `forms_file.exists` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:53 (em CodeScanner.discover_all_forms)
```

### 🔍 Objeto: `frete`

#### `frete.id` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:459 (em ContextProcessor._serialize_frete)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:391 (em DataProvider._serialize_frete)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:211 (em ExcelFretes._criar_aba_fretes_principal)
```

#### `frete.valor_cotado` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:461 (em ContextProcessor._serialize_frete)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:393 (em DataProvider._serialize_frete)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:393 (em DataProvider._serialize_frete)
```

#### `frete.valor_considerado` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:462 (em ContextProcessor._serialize_frete)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:394 (em DataProvider._serialize_frete)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:394 (em DataProvider._serialize_frete)
```

#### `frete.data_cotacao` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:463 (em ContextProcessor._serialize_frete)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:396 (em DataProvider._serialize_frete)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:396 (em DataProvider._serialize_frete)
```

#### `frete.nome_cliente` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:460 (em ContextProcessor._serialize_frete)
```

#### `frete.status_aprovacao` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:464 (em ContextProcessor._serialize_frete)
```

#### `frete.transportadora` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:392 (em DataProvider._serialize_frete)
```

#### `frete.status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:395 (em DataProvider._serialize_frete)
```

#### `frete.data_cotacao.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:396 (em DataProvider._serialize_frete)
```

### 🔍 Objeto: `full_path`

#### `full_path.exists` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:190 (em FileScanner.read_file_content)
```

#### `full_path.stat().st_size` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:198 (em FileScanner.read_file_content)
```

#### `full_path.stat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:198 (em FileScanner.read_file_content)
```

### 🔍 Objeto: `func`

#### `func.__name__` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:293 (em module.wrapper)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:295 (em module.wrapper)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:301 (em module.wrapper)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/performance_cache.py:89 (em module.wrapper)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/performance_cache.py:91 (em module.wrapper)
  ... e mais 2 ocorrências
```

### 🔍 Objeto: `function`

#### `function.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:153 (em ImportFilterer.is_false_positive)
```

### 🔍 Objeto: `future`

#### `future.result` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:215 (em IntelligenceCoordinator.coordinate_multi_ai_synthesis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:441 (em IntelligenceCoordinator._execute_parallel_intelligence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:512 (em IntelligenceCoordinator._execute_hybrid_intelligence)
```

### 🔍 Objeto: `futures`

#### `futures.append` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:210 (em IntelligenceCoordinator.coordinate_multi_ai_synthesis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:436 (em IntelligenceCoordinator._execute_parallel_intelligence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:508 (em IntelligenceCoordinator._execute_hybrid_intelligence)
```

### 🔍 Objeto: `fuzz`

#### `fuzz.ratio` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:196 (em NLPEnhancedAnalyzer._aplicar_correcoes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:106 (em BaseMapper.buscar_mapeamento_fuzzy)
```

#### `fuzz.partial_ratio` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:285 (em NLPEnhancedAnalyzer._calcular_similaridades)
```

### 🔍 Objeto: `get_cache()`

#### `get_cache().get_readme_scanner` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:234 (em module.cached_readme_scanner)
```

#### `get_cache().get_database_scanner` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:243 (em module.cached_database_scanner)
```

### 🔍 Objeto: `get_commands_status()`

#### `get_commands_status().values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:365 (em module.top-level)
```

### 🔍 Objeto: `get_flask_fallback()`

#### `get_flask_fallback().get_app` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:331 (em module.get_app)
```

#### `get_flask_fallback().get_model` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:335 (em module.get_model)
```

#### `get_flask_fallback().get_db` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:339 (em module.get_db)
```

#### `get_flask_fallback().get_current_user` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:343 (em module.get_current_user)
```

#### `get_flask_fallback().is_flask_available` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:347 (em module.is_flask_available)
```

#### `get_flask_fallback().get_config` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:351 (em module.get_config)
```

### 🔍 Objeto: `get_performance_analyzer()`

#### `get_performance_analyzer().analyze_ai_performance` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:635 (em module.analyze_system_performance)
```

### 🔍 Objeto: `get_security_guard()`

#### `get_security_guard().validate_user_access` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:456 (em module.validate_user_access)
```

#### `get_security_guard().validate_input` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:460 (em module.validate_input)
```

#### `get_security_guard().sanitize_input` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:464 (em module.sanitize_input)
```

### 🔍 Objeto: `get_session_memory()`

#### `get_session_memory().store_session` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:398 (em module.store_session_data)
```

#### `get_session_memory().get_session` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:410 (em module.get_session_data)
```

### 🔍 Objeto: `get_session_orchestrator()`

#### `get_session_orchestrator().create_session` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:1080 (em module.create_ai_session)
```

#### `get_session_orchestrator().complete_session` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:1093 (em module.complete_ai_session)
```

### 🔍 Objeto: `get_validation_utils()`

#### `get_validation_utils().validate` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:459 (em module.validate_data)
```

#### `get_validation_utils().validate_query` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:463 (em module.validate_query)
```

#### `get_validation_utils().validate_context` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:467 (em module.validate_context)
```

#### `get_validation_utils().sanitize_input` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:471 (em module.sanitize_input)
```

### 🔍 Objeto: `grafo_relacionamentos`

#### `grafo_relacionamentos.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:224 (em DatabaseManager.obter_estatisticas_gerais)
```

### 🔍 Objeto: `grau_entrada`

#### `grau_entrada.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:264 (em RelationshipMapper._calcular_estatisticas_grafo)
```

### 🔍 Objeto: `grau_saida`

#### `grau_saida.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:265 (em RelationshipMapper._calcular_estatisticas_grafo)
```

### 🔍 Objeto: `grouped`

#### `grouped.to_dict` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:290 (em DataProcessor.aggregate_data)
```

### 🔍 Objeto: `grupo`

#### `grupo.cnpjs_str` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:234 (em KnowledgeMemory.buscar_grupos_aplicaveis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:234 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `grupo.palavras_str` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:235 (em KnowledgeMemory.buscar_grupos_aplicaveis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:235 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `grupo.cnpjs_str.split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:234 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `grupo.palavras_str.split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:235 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `grupo.nome_grupo` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:238 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `grupo.tipo_negocio` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:239 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `grupo.filtro_sql` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:240 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

### 🔍 Objeto: `grupo_detectado`

#### `grupo_detectado.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:150 (em QueryAnalyzer._extract_entities)
```

### 🔍 Objeto: `grupo_info`

#### `grupo_info.get` (20 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:137 (em KnowledgeMemory.descobrir_grupo_empresarial)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:163 (em KnowledgeMemory.descobrir_grupo_empresarial)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:164 (em KnowledgeMemory.descobrir_grupo_empresarial)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:165 (em KnowledgeMemory.descobrir_grupo_empresarial)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:166 (em KnowledgeMemory.descobrir_grupo_empresarial)
  ... e mais 15 ocorrências
```

### 🔍 Objeto: `grupos_aplicaveis`

#### `grupos_aplicaveis.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:237 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

### 🔍 Objeto: `grupos_detectados`

#### `grupos_detectados.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:623 (em ContextLoader._carregar_todos_clientes_sistema)
```

### 🔍 Objeto: `grupos_tipos`

#### `grupos_tipos.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:136 (em FieldSearcher._obter_tipos_similares)
```

### 🔍 Objeto: `guard`

#### `guard.validate_user_access` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/__init__.py:84 (em module.secure_validate)
```

#### `guard.validate_input` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/__init__.py:90 (em module.secure_validate)
```

#### `guard.sanitize_input` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/__init__.py:91 (em module.secure_validate)
```

#### `guard.get_security_info` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/__init__.py:98 (em module.get_security_status)
```

### 🔍 Objeto: `handler`

#### `handler.body` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:81 (em DependencyAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:84 (em DependencyAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:64 (em DeepImportAnalyzer.visit_Try)
```

### 🔍 Objeto: `hashlib`

#### `hashlib.md5().hexdigest` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:491 (em SuggestionsManager._generate_cache_key)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:373 (em BaseProcessor._generate_cache_key)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:711 (em IntelligenceCoordinator._generate_cache_key)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/context_provider.py:404 (em ContextProvider._generate_cache_key)
```

#### `hashlib.md5` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:491 (em SuggestionsManager._generate_cache_key)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:373 (em BaseProcessor._generate_cache_key)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:711 (em IntelligenceCoordinator._generate_cache_key)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/context_provider.py:404 (em ContextProvider._generate_cache_key)
```

#### `hashlib.sha256().hexdigest` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:317 (em SecurityGuard.generate_token)
```

#### `hashlib.sha256` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:317 (em SecurityGuard.generate_token)
```

### 🔍 Objeto: `health`

#### `health.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/__init__.py:200 (em module.top-level)
```

### 🔍 Objeto: `hoje`

#### `hoje.strftime` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:636 (em ResponseProcessor._processar_consulta_temporal)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:640 (em ResponseProcessor._processar_consulta_temporal)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:641 (em ResponseProcessor._processar_consulta_temporal)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:642 (em ResponseProcessor._processar_consulta_temporal)
```

#### `hoje.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:278 (em EntregasLoader._get_mock_data)
```

### 🔍 Objeto: `hour_counts`

#### `hour_counts.most_common` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:366 (em AdaptiveLearning._detect_time_pattern)
```

### 🔍 Objeto: `hourly_distribution`

#### `hourly_distribution.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:183 (em PerformanceAnalyzer.analyze_ai_performance)
```

### 🔍 Objeto: `hours`

#### `hours.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:358 (em AdaptiveLearning._detect_time_pattern)
```

### 🔍 Objeto: `i`

#### `i.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:266 (em DependencyChecker.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:267 (em DependencyChecker.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:329 (em HumanInLoopLearning.generate_learning_report)
```

### 🔍 Objeto: `idx`

#### `idx.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:400 (em MapperManager._optimize_mappings_with_indexes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:401 (em MapperManager._optimize_mappings_with_indexes)
```

### 🔍 Objeto: `imp`

#### `imp.get` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:316 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:190 (em ImportChecker.check_import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:191 (em ImportChecker.check_import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:201 (em ImportChecker.check_import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:202 (em ImportChecker.check_import)
  ... e mais 2 ocorrências
```

### 🔍 Objeto: `import_configs`

#### `import_configs.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:395 (em SystemConfig.import_config)
```

### 🔍 Objeto: `import_info`

#### `import_info.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:113 (em ImportFilterer.is_false_positive)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:119 (em ImportFilterer.is_false_positive)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:135 (em ImportFilterer.is_false_positive)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:152 (em ImportFilterer.is_false_positive)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:178 (em ImportFilterer.analyze_real_problems)
```

### 🔍 Objeto: `importlib`

#### `importlib.import_module` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:178 (em DeepValidator._test_module_import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:191 (em DeepValidator._test_class_exists)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:24 (em module.testar_modulo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:27 (em module.testar_modulo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:64 (em DependencyChecker.check_module)
  ... e mais 4 ocorrências
```

### 🔍 Objeto: `imports`

#### `imports.add` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:36 (em CircularDependencyMapper.extract_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:59 (em CircularDependencyMapper.extract_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:63 (em CircularDependencyMapper.extract_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:65 (em CircularDependencyMapper.extract_imports)
```

#### `imports.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:105 (em ImportChecker.extract_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:124 (em ImportChecker.extract_imports)
```

### 🔍 Objeto: `imports_quebrados`

#### `imports_quebrados.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:226 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:233 (em module.analisar_arquivo)
```

### 🔍 Objeto: `improvements`

#### `improvements.append` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:180 (em MetacognitiveAnalyzer._suggest_self_improvements)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:183 (em MetacognitiveAnalyzer._suggest_self_improvements)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:186 (em MetacognitiveAnalyzer._suggest_self_improvements)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:191 (em MetacognitiveAnalyzer._suggest_self_improvements)
```

### 🔍 Objeto: `inc`

#### `inc.lower` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:333 (em CriticAgent._generate_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:336 (em CriticAgent._generate_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:336 (em CriticAgent._generate_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:339 (em CriticAgent._generate_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:339 (em CriticAgent._generate_recommendations)
```

### 🔍 Objeto: `includes`

#### `includes.extend` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:168 (em FileScanner._extract_template_includes)
```

### 🔍 Objeto: `inconsistencias`

#### `inconsistencias.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:322 (em SemanticValidator._validar_campos_modelo_tabela)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:327 (em SemanticValidator._validar_campos_modelo_tabela)
```

### 🔍 Objeto: `inconsistencies`

#### `inconsistencies.append` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:144 (em CriticAgent._validate_date_consistency)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:149 (em CriticAgent._validate_date_consistency)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:175 (em CriticAgent._validate_data_consistency)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:191 (em CriticAgent._validate_data_consistency)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:249 (em CriticAgent._validate_numerical_consistency)
```

#### `inconsistencies.extend` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:289 (em CriticAgent._validate_business_logic)
```

### 🔍 Objeto: `inconsistency`

#### `inconsistency.lower` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:195 (em SemanticLoopProcessor.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:198 (em SemanticLoopProcessor.top-level)
```

### 🔍 Objeto: `indice`

#### `indice.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:176 (em MetadataScanner._obter_indices_tabela)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:177 (em MetadataScanner._obter_indices_tabela)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:178 (em MetadataScanner._obter_indices_tabela)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:179 (em MetadataScanner._obter_indices_tabela)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:180 (em MetadataScanner._obter_indices_tabela)
```

### 🔍 Objeto: `indices_info`

#### `indices_info.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:182 (em MetadataScanner._obter_indices_tabela)
```

### 🔍 Objeto: `individual_results`

#### `individual_results.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:216 (em IntelligenceCoordinator.coordinate_multi_ai_synthesis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:224 (em IntelligenceCoordinator.coordinate_multi_ai_synthesis)
```

### 🔍 Objeto: `info`

#### `info.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:89 (em DependencyChecker.check_pip_package)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:90 (em DependencyChecker.check_pip_package)
```

### 🔍 Objeto: `info_campo`

#### `info_campo.get` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:96 (em FieldSearcher.buscar_campos_por_tipo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:305 (em FieldSearcher.buscar_campos_por_caracteristica)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:311 (em FieldSearcher.buscar_campos_por_caracteristica)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:350 (em FieldSearcher.buscar_campos_por_tamanho)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:159 (em AutoMapper._mapear_campo_automatico)
  ... e mais 2 ocorrências
```

### 🔍 Objeto: `info_tabela`

#### `info_tabela.get` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:315 (em SemanticValidator._validar_campos_modelo_tabela)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:87 (em FieldSearcher.buscar_campos_por_tipo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:165 (em FieldSearcher.buscar_campos_por_nome)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:304 (em FieldSearcher.buscar_campos_por_caracteristica)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:349 (em FieldSearcher.buscar_campos_por_tamanho)
  ... e mais 4 ocorrências
```

#### `info_tabela.get().items` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:87 (em FieldSearcher.buscar_campos_por_tipo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:165 (em FieldSearcher.buscar_campos_por_nome)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:304 (em FieldSearcher.buscar_campos_por_caracteristica)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:349 (em FieldSearcher.buscar_campos_por_tamanho)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:411 (em FieldSearcher.buscar_campos_similares)
```

#### `info_tabela.get().values` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:266 (em MetadataScanner.obter_tipos_campo_disponiveis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:295 (em MetadataScanner.obter_estatisticas_tabelas)
```

#### `info_tabela.get().keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:315 (em SemanticValidator._validar_campos_modelo_tabela)
```

### 🔍 Objeto: `info_tabela_ref`

#### `info_tabela_ref.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:399 (em FieldSearcher.buscar_campos_similares)
```

### 🔍 Objeto: `init_file`

#### `init_file.exists` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:200 (em module.verificar_import_existe)
```

### 🔍 Objeto: `init_result`

#### `init_result.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:269 (em ExternalAPIIntegration.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:328 (em ExternalAPIIntegration.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:129 (em StandaloneIntegration.initialize_system)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:182 (em StandaloneIntegration.process_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:183 (em StandaloneIntegration.process_query)
```

### 🔍 Objeto: `initial_data`

#### `initial_data.copy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:966 (em MainOrchestrator.top-level)
```

### 🔍 Objeto: `initialization_result`

#### `initialization_result.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:355 (em module.get_claude_ai_instance)
```

### 🔍 Objeto: `input_data`

#### `input_data.get` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:103 (em ProcessorCoordinator._execute_chain_step)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:104 (em ProcessorCoordinator._execute_chain_step)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:112 (em ProcessorCoordinator._execute_chain_step)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:113 (em ProcessorCoordinator._execute_chain_step)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:113 (em ProcessorCoordinator._execute_chain_step)
  ... e mais 4 ocorrências
```

#### `input_data.strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:400 (em BaseValidationUtils.sanitize_input)
```

### 🔍 Objeto: `insights`

#### `insights.append` (21 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:483 (em PerformanceAnalyzer._generate_insights)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:485 (em PerformanceAnalyzer._generate_insights)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:487 (em PerformanceAnalyzer._generate_insights)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:491 (em PerformanceAnalyzer._generate_insights)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:493 (em PerformanceAnalyzer._generate_insights)
  ... e mais 16 ocorrências
```

### 🔍 Objeto: `inspector`

#### `inspector.get_table_names` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:64 (em DatabaseScanner.discover_database_schema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:402 (em DatabaseScanner.obter_estatisticas_gerais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:115 (em StructureScanner._discover_models_via_database)
```

#### `inspector.get_columns` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:70 (em DatabaseScanner.discover_database_schema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:423 (em DatabaseScanner.obter_estatisticas_gerais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:119 (em StructureScanner._discover_models_via_database)
```

#### `inspector.get_foreign_keys` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:72 (em DatabaseScanner.discover_database_schema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:424 (em DatabaseScanner.obter_estatisticas_gerais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:120 (em StructureScanner._discover_models_via_database)
```

#### `inspector.get_pk_constraint` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:71 (em DatabaseScanner.discover_database_schema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:122 (em StructureScanner._discover_models_via_database)
```

#### `inspector.get_indexes` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:73 (em DatabaseScanner.discover_database_schema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:121 (em StructureScanner._discover_models_via_database)
```

#### `inspector.get_unique_constraints` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:74 (em DatabaseScanner.discover_database_schema)
```

#### `inspector.get_check_constraints` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:129 (em DatabaseScanner._get_check_constraints)
```

### 🔍 Objeto: `inst`

#### `inst.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:206 (em module.find_real_problems)
```

### 🔍 Objeto: `instance`

#### `instance.is_excel_fretes_command` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:228 (em DeepValidator._test_excel_fretes)
```

#### `instance.is_excel_pedidos_command` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:255 (em DeepValidator._test_excel_pedidos)
```

#### `instance.is_excel_entregas_command` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:280 (em DeepValidator._test_excel_entregas)
```

#### `instance.is_excel_faturamento_command` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:305 (em DeepValidator._test_excel_faturamento)
```

### 🔍 Objeto: `integracao`

#### `integracao.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:337 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:359 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
```

### 🔍 Objeto: `integration`

#### `integration.process_query` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:497 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:512 (em module.processar_com_claude_real)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:517 (em module.processar_com_claude_real)
```

#### `integration.initialize_system` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:349 (em module.create_standalone_system)
```

### 🔍 Objeto: `integration_system`

#### `integration_system.__class__.__name__` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/__init__.py:343 (em module.top-level)
```

#### `integration_system.__class__` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/__init__.py:343 (em module.top-level)
```

### 🔍 Objeto: `intelligence_processor`

#### `intelligence_processor.set_enricher` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:301 (em ProcessorManager.set_enricher)
```

### 🔍 Objeto: `intelligent_cache`

#### `intelligent_cache.set` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:227 (em BaseCommand._set_cached_result)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:230 (em BaseCommand._set_cached_result)
```

#### `intelligent_cache.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:214 (em BaseCommand._get_cached_result)
```

### 🔍 Objeto: `intelligent_context`

#### `intelligent_context.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:541 (em WebFlaskRoutes._build_user_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:543 (em WebFlaskRoutes._build_user_context)
```

### 🔍 Objeto: `intencoes`

#### `intencoes.values` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:29 (em IntentionAnalyzer.analyze_intention)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:223 (em IntentionAnalyzer._calcular_complexidade_intencao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:224 (em IntentionAnalyzer._calcular_complexidade_intencao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:244 (em IntentionAnalyzer._deve_usar_sistema_avancado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:245 (em IntentionAnalyzer._deve_usar_sistema_avancado)
```

#### `intencoes.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:28 (em IntentionAnalyzer.analyze_intention)
```

#### `intencoes.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:437 (em PatternLearner._detectar_intencao_avancada)
```

### 🔍 Objeto: `intencoes_count`

#### `intencoes_count.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:290 (em IntentionAnalyzer.get_performance_stats)
```

#### `intencoes_count.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:297 (em IntentionAnalyzer.get_performance_stats)
```

### 🔍 Objeto: `intencoes_scores`

#### `intencoes_scores.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:130 (em IntentionAnalyzer._detectar_intencoes_multiplas)
```

### 🔍 Objeto: `intent_patterns`

#### `intent_patterns.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:338 (em SemanticAnalyzer._classify_intents)
```

### 🔍 Objeto: `intention`

#### `intention.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:85 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:86 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:92 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:93 (em module.run_complete_flow)
```

### 🔍 Objeto: `intention_analysis`

#### `intention_analysis.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:316 (em AnalyzerManager._should_use_nlp_analysis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:338 (em AnalyzerManager._should_use_advanced_analysis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:387 (em AnalyzerManager._generate_combined_insights)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:388 (em AnalyzerManager._generate_combined_insights)
```

### 🔍 Objeto: `intents`

#### `intents.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:341 (em SemanticAnalyzer._classify_intents)
```

### 🔍 Objeto: `interaction`

#### `interaction.get().get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:382 (em AdaptiveLearning._detect_query_pattern)
```

#### `interaction.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:382 (em AdaptiveLearning._detect_query_pattern)
```

### 🔍 Objeto: `interaction_data`

#### `interaction_data.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:311 (em AdaptiveLearning._extract_preferences)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:317 (em AdaptiveLearning._extract_preferences)
```

### 🔍 Objeto: `internal_imports`

#### `internal_imports.add` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:115 (em CircularDependencyMapper.build_dependency_graph)
```

### 🔍 Objeto: `interpretacao`

#### `interpretacao.get` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:123 (em LearningCore.aprender_com_interacao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:130 (em LearningCore.aprender_com_interacao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:297 (em LearningCore._atualizar_metricas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:114 (em PatternLearner._extrair_padroes_periodo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:144 (em PatternLearner._extrair_padroes_dominio)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `issues`

#### `issues.append` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:217 (em StructuralAnalyzer._detect_structural_issues)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:222 (em StructuralAnalyzer._detect_structural_issues)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:227 (em StructuralAnalyzer._detect_structural_issues)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/structural_validator.py:96 (em StructuralAI._validate_temporal_consistency)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/structural_validator.py:110 (em StructuralAI._validate_data_relationships)
```

### 🔍 Objeto: `item`

#### `item.name` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:77 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:50 (em MethodCallVisitor.visit_ClassDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:51 (em MethodCallVisitor.visit_ClassDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:241 (em FileScanner.list_directory_contents)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:243 (em FileScanner.list_directory_contents)
  ... e mais 4 ocorrências
```

#### `item.value` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:244 (em StructureScanner._extract_table_name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:245 (em StructureScanner._extract_table_name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:246 (em StructureScanner._extract_table_name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:247 (em StructureScanner._extract_table_name)
```

#### `item.targets` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:54 (em VariableTracker.visit_ClassDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:242 (em StructureScanner._extract_table_name)
```

#### `item.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:269 (em HumanInLoopLearning.apply_improvement)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:270 (em HumanInLoopLearning.apply_improvement)
```

#### `item.is_dir` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:241 (em FileScanner.list_directory_contents)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:244 (em FileScanner.list_directory_contents)
```

#### `item.name.startswith` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:241 (em FileScanner.list_directory_contents)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:125 (em CodeScanner._parse_forms_file)
```

#### `item.stat` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:247 (em FileScanner.list_directory_contents)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:254 (em FileScanner.list_directory_contents)
```

#### `item.suffix` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:253 (em FileScanner.list_directory_contents)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:260 (em FileScanner.list_directory_contents)
```

#### `item.cliente` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:258 (em EmbarquesLoader._format_embarques_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:258 (em EmbarquesLoader._format_embarques_results)
```

#### `item.iterdir` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:244 (em FileScanner.list_directory_contents)
```

#### `item.is_file` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:246 (em FileScanner.list_directory_contents)
```

#### `item.stat().st_size` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:247 (em FileScanner.list_directory_contents)
```

#### `item.stat().st_mtime` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:254 (em FileScanner.list_directory_contents)
```

#### `item.decorator_list` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:215 (em StructureScanner._parse_models_file)
```

#### `item.value.value` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:245 (em StructureScanner._extract_table_name)
```

#### `item.value.s` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:247 (em StructureScanner._extract_table_name)
```

#### `item.peso_total` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:244 (em EmbarquesLoader._format_embarques_results)
```

#### `item.valor_total` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:245 (em EmbarquesLoader._format_embarques_results)
```

### 🔍 Objeto: `json`

#### `json.dumps` (16 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:139 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:297 (em LearningCore._atualizar_metricas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:334 (em LearningCore._salvar_historico_aprendizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:336 (em LearningCore._salvar_historico_aprendizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:337 (em LearningCore._salvar_historico_aprendizado)
  ... e mais 11 ocorrências
```

#### `json.dump` (13 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:470 (em DeepValidator._generate_final_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:268 (em ImportFilterer.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:259 (em ClassDuplicateFinder.save_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:245 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:237 (em module.main)
  ... e mais 8 ocorrências
```

#### `json.load` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:163 (em ImportFilterer.analyze_real_problems)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:540 (em SystemConfig._load_profile_config)
```

#### `json.loads` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:359 (em PatternLearner.buscar_padroes_aplicaveis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:385 (em SystemConfig.import_config)
```

#### `json.JSONDecodeError` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:363 (em PatternLearner.buscar_padroes_aplicaveis)
```

### 🔍 Objeto: `key`

#### `key.lower` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:379 (em IntelligenceProcessor._normalize_dict_for_intelligence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:473 (em DataProcessor._normalize_dict)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:611 (em SystemConfig._validate_config_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:614 (em SystemConfig._validate_config_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:617 (em SystemConfig._validate_config_value)
  ... e mais 1 ocorrências
```

#### `key.strip` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:86 (em DependencyChecker.check_pip_package)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:383 (em DataProcessor._clean_dict)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:385 (em DataProcessor._clean_dict)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:387 (em DataProcessor._clean_dict)
```

#### `key.lower().replace` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:379 (em IntelligenceProcessor._normalize_dict_for_intelligence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:473 (em DataProcessor._normalize_dict)
```

#### `key.startswith` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/basic_config.py:63 (em ClaudeAIConfig.to_dict)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:727 (em SystemConfig._key_matches_pattern)
```

#### `key.split` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:582 (em SystemConfig._get_nested_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:595 (em SystemConfig._set_nested_value)
```

#### `key.lower().replace().replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:473 (em DataProcessor._normalize_dict)
```

#### `key.value` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:211 (em CodeScanner._extract_dict_value)
```

### 🔍 Objeto: `key_data`

#### `key_data.encode` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:373 (em BaseProcessor._generate_cache_key)
```

### 🔍 Objeto: `keyword`

#### `keyword.arg` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:177 (em CodeScanner._extract_form_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:179 (em CodeScanner._extract_form_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:181 (em CodeScanner._extract_form_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:292 (em StructureScanner._extract_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:294 (em StructureScanner._extract_field_info)
  ... e mais 3 ocorrências
```

#### `keyword.value` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:178 (em CodeScanner._extract_form_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:180 (em CodeScanner._extract_form_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:182 (em CodeScanner._extract_form_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:293 (em StructureScanner._extract_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:295 (em StructureScanner._extract_field_info)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `keywords`

#### `keywords.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:281 (em SemanticAnalyzer._extract_keywords)
```

### 🔍 Objeto: `keywords_entregas`

#### `keywords_entregas.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:69 (em EntregasAgent._calculate_relevance)
```

### 🔍 Objeto: `kwargs`

#### `kwargs.get` (35 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:85 (em IntelligenceProcessor.process_intelligence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:539 (em IntelligenceProcessor._learn_from_processing)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:543 (em IntelligenceProcessor._learn_from_processing)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:630 (em IntelligenceProcessor._focused_synthesis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:392 (em DataProcessor._transform_data)
  ... e mais 30 ocorrências
```

#### `kwargs.items` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:490 (em SuggestionsManager._generate_cache_key)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:710 (em IntelligenceCoordinator._generate_cache_key)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:392 (em module.provide_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:403 (em module.provide_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/context_provider.py:403 (em ContextProvider._generate_cache_key)
```

#### `kwargs.copy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/__init__.py:192 (em module.load_data)
```

### 🔍 Objeto: `l`

#### `l.strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:468 (em ResponseProcessor._validar_resposta_final)
```

### 🔍 Objeto: `learning_module`

#### `learning_module.record_feedback` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:592 (em WebFlaskRoutes._record_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:607 (em WebFlaskRoutes._record_feedback)
```

### 🔍 Objeto: `learning_system`

#### `learning_system.capture_feedback` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:433 (em module.capture_user_feedback)
```

#### `learning_system.generate_learning_report` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:439 (em module.get_learning_insights)
```

### 🔍 Objeto: `level`

#### `level.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:286 (em BaseProcessor._log_operation)
```

### 🔍 Objeto: `line`

#### `line.split` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:85 (em DependencyChecker.check_pip_package)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:285 (em CodeScanner._extract_blueprint_name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:346 (em CodeScanner._extract_function_info)
```

#### `line.strip` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:317 (em FileScanner.search_in_files)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:298 (em CodeScanner._extract_routes_from_lines)
```

#### `line.startswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:345 (em CodeScanner._extract_function_info)
```

### 🔍 Objeto: `linha`

#### `linha.strip` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:468 (em ResponseProcessor._validar_resposta_final)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:468 (em ResponseProcessor._validar_resposta_final)
```

### 🔍 Objeto: `linhas_unicas`

#### `linhas_unicas.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:469 (em ResponseProcessor._validar_resposta_final)
```

### 🔍 Objeto: `loader`

#### `loader.__class__.__name__` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:162 (em LoaderManager.load_data_by_domain)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:194 (em LoaderManager.load_data_by_domain)
```

#### `loader.__class__` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:162 (em LoaderManager.load_data_by_domain)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:194 (em LoaderManager.load_data_by_domain)
```

#### `loader._get_mock_data` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:182 (em LoaderManager.load_data_by_domain)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:203 (em LoaderManager.load_data_by_domain)
```

#### `loader.load_context` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/__init__.py:156 (em module.load_context)
```

#### `loader.load_database` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/__init__.py:172 (em module.load_database)
```

#### `loader.load_data` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:165 (em LoaderManager.load_data_by_domain)
```

#### `loader.configure_with_scanner` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1393 (em MainOrchestrator._connect_modules)
```

#### `loader.configure_with_mapper` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1405 (em MainOrchestrator._connect_modules)
```

### 🔍 Objeto: `logging`

#### `logging.getLogger` (159 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:17 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:30 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:56 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:20 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:24 (em module.top-level)
  ... e mais 154 ocorrências
```

#### `logging.warning` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:24 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:27 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:34 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:50 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:33 (em module.top-level)
  ... e mais 1 ocorrências
```

#### `logging.INFO` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:16 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:19 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:370 (em module.top-level)
```

#### `logging.basicConfig` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:16 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:19 (em module.top-level)
```

#### `logging.Logger` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:98 (em module.top-level)
```

### 🔍 Objeto: `loop`

#### `loop.run_until_complete` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:242 (em ClaudeAINovo.process_query_sync)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:354 (em module.get_claude_ai_instance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/__init__.py:196 (em module.initialize_integration_system)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:511 (em module.processar_com_claude_real)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:125 (em StandaloneIntegration.initialize_system)
  ... e mais 3 ocorrências
```

#### `loop.is_running` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:198 (em ValidatorManager.validate_agent_responses)
```

#### `loop.create_task` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:200 (em ValidatorManager.validate_agent_responses)
```

### 🔍 Objeto: `m`

#### `m.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:257 (em ProjectScanner._calculate_quality_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:147 (em ConversationMemory.get_conversation_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:148 (em ConversationMemory.get_conversation_summary)
```

#### `m.strip().strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:332 (em CodeScanner._extract_route_methods)
```

#### `m.strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:332 (em CodeScanner._extract_route_methods)
```

#### `m.get().startswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:257 (em ProjectScanner._calculate_quality_metrics)
```

### 🔍 Objeto: `main_orch`

#### `main_orch.components` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:321 (em TesteIntegracaoCompleta.testar_fallbacks_mocks)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:322 (em TesteIntegracaoCompleta.testar_fallbacks_mocks)
```

#### `main_orch.coordinator_manager` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:228 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `main_orch.auto_command_processor` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:229 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `main_orch.security_guard` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:230 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `main_orch.suggestions_manager` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:231 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `main_orch.workflows` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:239 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `main_orch.execute_workflow` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:255 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

### 🔍 Objeto: `manager`

#### `manager.get_status` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:700 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:358 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/utils_manager.py:273 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/data_manager.py:420 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tools/tools_manager.py:202 (em module.top-level)
```

#### `manager.health_check` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:701 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:359 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/utils_manager.py:274 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/data_manager.py:421 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tools/tools_manager.py:203 (em module.top-level)
```

#### `manager.provide` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/__init__.py:114 (em module.provide_integrated_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/__init__.py:139 (em module.provide_integrated_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/__init__.py:165 (em module.provide_mixed_intelligence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:394 (em module.provide_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:405 (em module.provide_context)
```

#### `manager.process_unified_query` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:151 (em ClaudeAINovo.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:352 (em ExternalAPIIntegration.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:139 (em WebIntegrationAdapter.process_query_sync)
```

#### `manager.get_system_status` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:174 (em ClaudeAINovo.get_system_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:272 (em ExternalAPIIntegration.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:225 (em WebIntegrationAdapter.get_system_status)
```

#### `manager.load_data_by_domain` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/__init__.py:195 (em module.load_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/__init__.py:217 (em module.load_domain_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:422 (em module.load_domain_data)
```

#### `manager.initialize_all_modules` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:112 (em ClaudeAINovo.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:268 (em ExternalAPIIntegration.top-level)
```

#### `manager.get_module` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:164 (em ClaudeAINovo.get_module)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:197 (em WebIntegrationAdapter.get_module)
```

#### `manager.get_best_loader_for_query` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/__init__.py:191 (em module.load_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:432 (em module.get_best_loader)
```

#### `manager.coordinate_query` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:174 (em module.coordinate_smart_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:404 (em module.coordinate_intelligent_query)
```

#### `manager.domain_agents.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:189 (em module.get_domain_agent)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:417 (em module.get_domain_agent)
```

#### `manager.domain_agents` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:189 (em module.get_domain_agent)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:417 (em module.get_domain_agent)
```

#### `manager.get_coordinator_status` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:201 (em module.get_coordination_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:427 (em module.get_coordination_status)
```

#### `manager.get_scanner_status` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/__init__.py:172 (em module.get_scanning_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/__init__.py:198 (em module.top-level)
```

#### `manager.orchestrate_operation` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/__init__.py:142 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:779 (em module.top-level)
```

#### `manager.get_orchestrator_status` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/__init__.py:170 (em module.get_system_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:795 (em module.get_orchestration_status)
```

#### `manager.get_validation_status` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/__init__.py:151 (em module.get_validation_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/__init__.py:177 (em module.top-level)
```

#### `manager.get_memory_health` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/__init__.py:172 (em module.get_memory_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/__init__.py:199 (em module.top-level)
```

#### `manager.modules.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:193 (em ClaudeAINovo.get_available_modules)
```

#### `manager.modules` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:193 (em ClaudeAINovo.get_available_modules)
```

#### `manager.initialize_diagnostics_analyzer` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:693 (em module.get_analyzer_manager)
```

#### `manager.generate_suggestions` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/__init__.py:96 (em module.generate_suggestions)
```

#### `manager.register_suggestion_engine` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/__init__.py:137 (em module.register_suggestion_engine)
```

#### `manager.submit_feedback` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/__init__.py:162 (em module.submit_suggestion_feedback)
```

#### `manager.get_suggestion_recommendations` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/__init__.py:185 (em module.get_suggestion_recommendations)
```

#### `manager.optimize_suggestion_performance` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/__init__.py:233 (em module.optimize_suggestions_performance)
```

#### `manager.get_processor_chain` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:363 (em module.top-level)
```

#### `manager.get_detailed_health_report` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:367 (em module.top-level)
```

#### `manager.load_multiple_domains` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:427 (em module.load_multiple_data)
```

#### `manager.get_available_modules` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:252 (em WebIntegrationAdapter.get_available_modules)
```

#### `manager.get_best_provider_for_query` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/__init__.py:170 (em module.get_best_provider_recommendation)
```

#### `manager.get_provider_status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/__init__.py:175 (em module.get_all_providers_status)
```

#### `manager.scan_complete_project` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/__init__.py:150 (em module.scan_project)
```

#### `manager.validate_context` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/__init__.py:129 (em module.validate_context)
```

#### `manager.validate_data_structure` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/__init__.py:140 (em module.validate_data_structure)
```

#### `manager.store_conversation_context` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/__init__.py:150 (em module.memorize_context)
```

#### `manager.retrieve_conversation_context` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/__init__.py:161 (em module.recall_context)
```

### 🔍 Objeto: `manager_status`

#### `manager_status.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:227 (em WebIntegrationAdapter.get_system_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:466 (em WebFlaskRoutes.health_check)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:467 (em WebFlaskRoutes.health_check)
```

### 🔍 Objeto: `mapa`

#### `mapa.campo_sistema` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:283 (em KnowledgeMemory.buscar_mapeamentos_aplicaveis)
```

#### `mapa.modelo` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:284 (em KnowledgeMemory.buscar_mapeamentos_aplicaveis)
```

#### `mapa.frequencia` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:285 (em KnowledgeMemory.buscar_mapeamentos_aplicaveis)
```

#### `mapa.termos` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:286 (em KnowledgeMemory.buscar_mapeamentos_aplicaveis)
```

### 🔍 Objeto: `mapeamento`

#### `mapeamento.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:296 (em SemanticValidator._mapear_modelo_para_tabela)
```

### 🔍 Objeto: `mapeamento_atual`

#### `mapeamento_atual.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:262 (em SemanticEnricher._sugestoes_readme_vs_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:279 (em SemanticEnricher._sugestoes_readme_vs_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:381 (em SemanticEnricher._sugestoes_otimizacao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:382 (em SemanticEnricher._sugestoes_otimizacao)
```

### 🔍 Objeto: `mapeamento_campo`

#### `mapeamento_campo.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:114 (em AutoMapper.gerar_mapeamento_automatico)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:118 (em AutoMapper.gerar_mapeamento_automatico)
```

### 🔍 Objeto: `mapeamentos`

#### `mapeamentos.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:151 (em MetadataScanner._normalizar_tipo_sqlalchemy)
```

### 🔍 Objeto: `mapeamentos_aplicaveis`

#### `mapeamentos_aplicaveis.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:282 (em KnowledgeMemory.buscar_mapeamentos_aplicaveis)
```

### 🔍 Objeto: `mapeamentos_criados`

#### `mapeamentos_criados.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:87 (em KnowledgeMemory.aprender_mapeamento_cliente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:102 (em KnowledgeMemory.aprender_mapeamento_cliente)
```

### 🔍 Objeto: `mapper`

#### `mapper.mapeamentos` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:209 (em SemanticEnricher._obter_mapeamento_atual)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:210 (em SemanticEnricher._obter_mapeamento_atual)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:185 (em SemanticValidator._validacoes_gerais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:197 (em SemanticValidator._validacoes_gerais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:198 (em SemanticValidator._validacoes_gerais)
  ... e mais 1 ocorrências
```

#### `mapper.gerar_estatisticas` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:254 (em MapperManager.obter_estatisticas_mappers)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:73 (em DiagnosticsAnalyzer.gerar_estatisticas_completas)
```

#### `mapper.modelo_nome` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:214 (em SemanticEnricher._obter_mapeamento_atual)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:319 (em SemanticValidator._validar_campos_modelo_tabela)
```

#### `mapper.analyze_circular_dependencies` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:269 (em module.main)
```

#### `mapper.generate_report` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:273 (em module.main)
```

#### `mapper.buscar_mapeamento` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:82 (em MapperManager.analisar_consulta_semantica)
```

#### `mapper.buscar_mapeamento_fuzzy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:128 (em MapperManager._buscar_fuzzy_integrado)
```

#### `mapper.adicionar_mapeamento` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:345 (em MapperManager.apply_auto_suggestions)
```

#### `mapper.validar_mapeamentos` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:119 (em DiagnosticsAnalyzer.diagnosticar_qualidade)
```

#### `mapper.modelo_nome.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:319 (em SemanticValidator._validar_campos_modelo_tabela)
```

#### `mapper.mapeamentos.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:320 (em SemanticValidator._validar_campos_modelo_tabela)
```

### 🔍 Objeto: `mappers`

#### `mappers.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/__init__.py:32 (em module.get_domain_mapper)
```

#### `mappers.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/__init__.py:34 (em module.get_domain_mapper)
```

### 🔍 Objeto: `mappers_consultados`

#### `mappers_consultados.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:89 (em MapperManager.analisar_consulta_semantica)
```

### 🔍 Objeto: `mapping`

#### `mapping.source_field` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:114 (em FieldMapper.map_fields)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:122 (em FieldMapper.map_fields)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:131 (em FieldMapper.map_fields)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:138 (em FieldMapper.map_fields)
```

#### `mapping.transform_function` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:126 (em FieldMapper.map_fields)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:127 (em FieldMapper.map_fields)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/context_mapper.py:96 (em ContextMapper.map_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/context_mapper.py:97 (em ContextMapper.map_context)
```

#### `mapping.pattern` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:98 (em QueryMapper.map_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:100 (em QueryMapper.map_query)
```

#### `mapping.default_value` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:117 (em FieldMapper.map_fields)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:118 (em FieldMapper.map_fields)
```

#### `mapping.validation_function` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:130 (em FieldMapper.map_fields)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:130 (em FieldMapper.map_fields)
```

#### `mapping.target_key` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/context_mapper.py:100 (em ContextMapper.map_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/context_mapper.py:103 (em ContextMapper.map_context)
```

#### `mapping.target_type` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:96 (em QueryMapper.map_query)
```

#### `mapping.template` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:103 (em QueryMapper.map_query)
```

#### `mapping.required` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:121 (em FieldMapper.map_fields)
```

#### `mapping.target_field` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:135 (em FieldMapper.map_fields)
```

#### `mapping.source_keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/context_mapper.py:91 (em ContextMapper.map_context)
```

#### `mapping.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:166 (em ValidatorManager.validate_critical_rules)
```

### 🔍 Objeto: `mapping_result`

#### `mapping_result.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:129 (em SemanticLoopProcessor.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:130 (em SemanticLoopProcessor.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:131 (em SemanticLoopProcessor.top-level)
```

### 🔍 Objeto: `mappings`

#### `mappings.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:386 (em MapperManager._identify_mapper_for_table)
```

### 🔍 Objeto: `match`

#### `match.group` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:110 (em BaseCommand._extract_client_from_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:132 (em FileScanner._extract_template_extends)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:114 (em ReadmeScanner.buscar_termos_naturais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:271 (em ReadmeScanner._buscar_campo_na_secao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:316 (em ReadmeScanner.obter_informacoes_campo)
  ... e mais 2 ocorrências
```

#### `match.strip` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:340 (em FeedbackProcessor._extrair_acoes_sugeridas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:340 (em FeedbackProcessor._extrair_acoes_sugeridas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:105 (em FileScanner._extract_template_variables)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:149 (em FileScanner._extract_template_blocks)
```

#### `match.split` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:97 (em FileScanner._extract_template_variables)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:113 (em FileScanner._extract_template_variables)
```

#### `match.start` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:342 (em FileScanner._extract_match_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:225 (em ReadmeScanner._extrair_secao_modelo)
```

#### `match.group().title` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:110 (em BaseCommand._extract_client_from_query)
```

#### `match.end` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:343 (em FileScanner._extract_match_context)
```

#### `match.lower().replace().capitalize` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:367 (em ReadmeScanner.listar_modelos_disponiveis)
```

#### `match.lower().replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:367 (em ReadmeScanner.listar_modelos_disponiveis)
```

#### `match.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:367 (em ReadmeScanner.listar_modelos_disponiveis)
```

### 🔍 Objeto: `match_contexto`

#### `match_contexto.group().strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:334 (em ReadmeScanner.obter_informacoes_campo)
```

#### `match_contexto.group` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:334 (em ReadmeScanner.obter_informacoes_campo)
```

### 🔍 Objeto: `match_obs`

#### `match_obs.group().strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:340 (em ReadmeScanner.obter_informacoes_campo)
```

#### `match_obs.group` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:340 (em ReadmeScanner.obter_informacoes_campo)
```

### 🔍 Objeto: `match_proximo`

#### `match_proximo.start` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:240 (em ReadmeScanner._extrair_secao_modelo)
```

### 🔍 Objeto: `match_significado`

#### `match_significado.group().strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:328 (em ReadmeScanner.obter_informacoes_campo)
```

#### `match_significado.group` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:328 (em ReadmeScanner.obter_informacoes_campo)
```

### 🔍 Objeto: `match_termos`

#### `match_termos.group` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:322 (em ReadmeScanner.obter_informacoes_campo)
```

### 🔍 Objeto: `matches_por_mapper`

#### `matches_por_mapper.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:226 (em MapperManager.detectar_dominio_principal)
```

#### `matches_por_mapper.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:227 (em MapperManager.detectar_dominio_principal)
```

#### `matches_por_mapper.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:232 (em MapperManager.detectar_dominio_principal)
```

### 🔍 Objeto: `md`

#### `md.append` (18 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:284 (em DependencyChecker._create_markdown_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:287 (em DependencyChecker._create_markdown_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:289 (em DependencyChecker._create_markdown_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:290 (em DependencyChecker._create_markdown_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:291 (em DependencyChecker._create_markdown_report)
  ... e mais 13 ocorrências
```

### 🔍 Objeto: `melhorias`

#### `melhorias.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:155 (em FeedbackProcessor.processar_feedback_completo)
```

### 🔍 Objeto: `memorizer`

#### `memorizer.save_interaction` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:136 (em module.run_complete_flow)
```

#### `memorizer.get_context` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:144 (em module.run_complete_flow)
```

#### `memorizer.context_memory` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:57 (em ConversationManager.set_memorizer)
```

#### `memorizer.conversation_memory` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:61 (em ConversationManager.set_memorizer)
```

### 🔍 Objeto: `mentioned_dates`

#### `mentioned_dates.extend` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:136 (em CriticAgent._validate_date_consistency)
```

### 🔍 Objeto: `mes`

#### `mes.capitalize` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:220 (em ConversationContext.extract_metadata)
```

### 🔍 Objeto: `message`

#### `message.to_dict` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:71 (em ConversationContext.add_message)
```

### 🔍 Objeto: `metadata`

#### `metadata.get` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:52 (em module.format_response_advanced)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:54 (em module.format_response_advanced)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:57 (em module.format_response_advanced)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:60 (em module.format_response_advanced)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:63 (em module.format_response_advanced)
  ... e mais 6 ocorrências
```

### 🔍 Objeto: `metadata_scanner`

#### `metadata_scanner.obter_campos_tabela` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:556 (em DataAnalyzer.analisar_tabela_completa)
```

### 🔍 Objeto: `method`

#### `method.startswith` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:279 (em ProcessorRegistry.validate_all_processors)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:134 (em ValidatorManager.validate_data_structure)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:366 (em ValidatorManager.get_validation_status)
```

### 🔍 Objeto: `method_name`

#### `method_name.startswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:164 (em module.find_undefined_methods)
```

#### `method_name.endswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:164 (em module.find_undefined_methods)
```

### 🔍 Objeto: `methods`

#### `methods.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:77 (em ClassDuplicateFinder.extract_class_info)
```

### 🔍 Objeto: `methods_count`

#### `methods_count.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:360 (em CodeScanner._analyze_route_methods)
```

### 🔍 Objeto: `methods_str`

#### `methods_str.split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:332 (em CodeScanner._extract_route_methods)
```

### 🔍 Objeto: `mock_db`

#### `mock_db.session` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:246 (em FlaskFallback._create_mock_db)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:247 (em FlaskFallback._create_mock_db)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:248 (em FlaskFallback._create_mock_db)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:249 (em FlaskFallback._create_mock_db)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:250 (em FlaskFallback._create_mock_db)
```

### 🔍 Objeto: `mock_query`

#### `mock_query.all` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:94 (em FlaskFallback._create_mock_model)
```

#### `mock_query.first` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:95 (em FlaskFallback._create_mock_model)
```

#### `mock_query.count` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:96 (em FlaskFallback._create_mock_model)
```

#### `mock_query.filter` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:97 (em FlaskFallback._create_mock_model)
```

#### `mock_query.filter_by` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:98 (em FlaskFallback._create_mock_model)
```

#### `mock_query.order_by` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:99 (em FlaskFallback._create_mock_model)
```

#### `mock_query.limit` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:100 (em FlaskFallback._create_mock_model)
```

#### `mock_query.offset` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:101 (em FlaskFallback._create_mock_model)
```

#### `mock_query.join` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:102 (em FlaskFallback._create_mock_model)
```

### 🔍 Objeto: `mode`

#### `mode.value` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:982 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:994 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:272 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:291 (em OrchestratorManager.top-level)
```

#### `mode.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:774 (em module.top-level)
```

### 🔍 Objeto: `model_info`

#### `model_info.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:240 (em ProjectScanner._calculate_quality_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:240 (em ProjectScanner._calculate_quality_metrics)
```

### 🔍 Objeto: `model_name`

#### `model_name.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:90 (em FlaskFallback._create_mock_model)
```

### 🔍 Objeto: `modelo`

#### `modelo.lower` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:206 (em SemanticEnricher._obter_mapeamento_atual)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:184 (em SemanticValidator._validacoes_gerais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:296 (em SemanticValidator._mapear_modelo_para_tabela)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:319 (em SemanticValidator._validar_campos_modelo_tabela)
```

### 🔍 Objeto: `modelos`

#### `modelos.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:369 (em ReadmeScanner.listar_modelos_disponiveis)
```

### 🔍 Objeto: `models`

#### `models.update` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:96 (em StructureScanner.discover_all_models)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:99 (em StructureScanner.discover_all_models)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:164 (em StructureScanner._discover_models_via_files)
```

#### `models.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:185 (em PerformanceAnalyzer.analyze_ai_performance)
```

### 🔍 Objeto: `models_file`

#### `models_file.exists` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:163 (em StructureScanner._discover_models_via_files)
```

### 🔍 Objeto: `module`

#### `module.startswith` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:75 (em CircularDependencyMapper.normalize_module_path)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:79 (em CircularDependencyMapper.normalize_module_path)
```

#### `module.split` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:223 (em CircularDependencyMapper.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:237 (em CircularDependencyMapper.generate_report)
```

#### `module.replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:83 (em CircularDependencyMapper.normalize_module_path)
```

### 🔍 Objeto: `module_dir`

#### `module_dir.name` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:51 (em CodeScanner.discover_all_forms)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:54 (em CodeScanner.discover_all_forms)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:74 (em CodeScanner.discover_all_routes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:77 (em CodeScanner.discover_all_routes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:161 (em StructureScanner._discover_models_via_files)
  ... e mais 1 ocorrências
```

#### `module_dir.is_dir` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:51 (em CodeScanner.discover_all_forms)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:74 (em CodeScanner.discover_all_routes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:161 (em StructureScanner._discover_models_via_files)
```

#### `module_dir.name.startswith` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:51 (em CodeScanner.discover_all_forms)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:74 (em CodeScanner.discover_all_routes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:161 (em StructureScanner._discover_models_via_files)
```

### 🔍 Objeto: `module_name`

#### `module_name.lstrip` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:166 (em ImportChecker.check_import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:167 (em ImportChecker.check_import)
```

#### `module_name.startswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:101 (em CommandsRegistry._try_import_command)
```

### 🔍 Objeto: `module_path`

#### `module_path.startswith` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:173 (em DeepValidator._test_module_import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:186 (em DeepValidator._test_class_exists)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:22 (em module.testar_modulo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:186 (em module.verificar_import_existe)
```

#### `module_path.replace` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:188 (em module.verificar_import_existe)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:192 (em module.verificar_import_existe)
```

#### `module_path.split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:179 (em module.verificar_import_existe)
```

#### `module_path.replace().replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:188 (em module.verificar_import_existe)
```

### 🔍 Objeto: `modulos_teste`

#### `modulos_teste.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:174 (em module.main)
```

#### `modulos_teste.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:182 (em module.main)
```

### 🔍 Objeto: `monitor`

#### `monitor.start` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:369 (em module.main)
```

### 🔍 Objeto: `msg`

#### `msg.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:165 (em ConversationContext.build_context_prompt)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:166 (em ConversationContext.build_context_prompt)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:169 (em ConversationContext.build_context_prompt)
```

### 🔍 Objeto: `name`

#### `name.lower` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:116 (em DependencyAnalyzer.visit_Attribute)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:116 (em DependencyAnalyzer.visit_Attribute)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:125 (em DependencyAnalyzer.visit_Attribute)
```

#### `name.split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:30 (em VariableTracker.visit_Import)
```

### 🔍 Objeto: `negacoes_encontradas`

#### `negacoes_encontradas.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:266 (em NLPEnhancedAnalyzer._detectar_negacoes)
```

### 🔍 Objeto: `nltk`

#### `nltk.download` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:41 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:42 (em module.top-level)
```

### 🔍 Objeto: `node`

#### `node.lineno` (18 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:83 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:87 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:74 (em MethodCallVisitor.visit_Attribute)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:64 (em VariableTracker.visit_Assign)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:71 (em VariableTracker.visit_Name)
  ... e mais 13 ocorrências
```

#### `node.name` (17 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:54 (em ClassDuplicateFinder.scan_file)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:44 (em MethodCallVisitor.visit_ClassDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:45 (em MethodCallVisitor.visit_ClassDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:50 (em MethodCallVisitor.visit_ClassDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:51 (em MethodCallVisitor.visit_ClassDef)
  ... e mais 12 ocorrências
```

#### `node.names` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:29 (em MethodCallVisitor.visit_Import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:36 (em MethodCallVisitor.visit_ImportFrom)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:28 (em VariableTracker.visit_Import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:35 (em VariableTracker.visit_ImportFrom)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:37 (em DependencyAnalyzer.visit_Import)
  ... e mais 6 ocorrências
```

#### `node.module` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:53 (em DependencyAnalyzer.visit_ImportFrom)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:126 (em DeepImportAnalyzer.visit_ImportFrom)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:40 (em CircularDependencyMapper.extract_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:55 (em CircularDependencyMapper.extract_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:56 (em CircularDependencyMapper.extract_imports)
  ... e mais 4 ocorrências
```

#### `node.body` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:75 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:48 (em MethodCallVisitor.visit_ClassDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:52 (em VariableTracker.visit_ClassDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:75 (em DependencyAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:103 (em DependencyAnalyzer.visit_Try)
  ... e mais 3 ocorrências
```

#### `node.value` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:68 (em MethodCallVisitor.visit_Attribute)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:85 (em MethodCallVisitor._get_object_name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:111 (em DependencyAnalyzer.visit_Attribute)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:112 (em DependencyAnalyzer.visit_Attribute)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:98 (em RealProblemFinder.visit_Attribute)
  ... e mais 1 ocorrências
```

#### `node.attr` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:73 (em MethodCallVisitor.visit_Attribute)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:76 (em MethodCallVisitor.visit_Attribute)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:87 (em MethodCallVisitor._get_object_name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:113 (em DependencyAnalyzer.visit_Attribute)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:100 (em RealProblemFinder.visit_Attribute)
```

#### `node.ctx` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:66 (em MethodCallVisitor.visit_Attribute)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:69 (em VariableTracker.visit_Name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:72 (em VariableTracker.visit_Name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:130 (em RealProblemFinder.visit_Name)
```

#### `node.id` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:83 (em MethodCallVisitor._get_object_name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:71 (em VariableTracker.visit_Name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:74 (em VariableTracker.visit_Name)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:131 (em RealProblemFinder.visit_Name)
```

#### `node.level` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:42 (em CircularDependencyMapper.extract_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:50 (em CircularDependencyMapper.extract_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:114 (em ImportChecker.extract_imports)
```

#### `node.end_lineno` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:82 (em ClassDuplicateFinder.extract_class_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:83 (em ClassDuplicateFinder.extract_class_info)
```

#### `node.handlers` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:80 (em DependencyAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:60 (em DeepImportAnalyzer.visit_Try)
```

#### `node.value.id` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:112 (em DependencyAnalyzer.visit_Attribute)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:99 (em RealProblemFinder.visit_Attribute)
```

#### `node.bases` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:67 (em ClassDuplicateFinder.extract_class_info)
```

#### `node.func` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:89 (em MethodCallVisitor._get_object_name)
```

#### `node.args.args` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:43 (em VariableTracker.visit_FunctionDef)
```

#### `node.args` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:43 (em VariableTracker.visit_FunctionDef)
```

#### `node.targets` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:61 (em VariableTracker.visit_Assign)
```

#### `node.module.split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:56 (em CircularDependencyMapper.extract_imports)
```

### 🔍 Objeto: `nome_campo`

#### `nome_campo.lower` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:206 (em FieldSearcher._calcular_score_match_nome)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:246 (em FieldSearcher._determinar_tipo_match)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:231 (em AutoMapper._gerar_termos_automaticos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:332 (em AutoMapper._calcular_confianca_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:367 (em AutoMapper._identificar_categoria_semantica)
```

#### `nome_campo.replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:226 (em AutoMapper._gerar_termos_automaticos)
```

### 🔍 Objeto: `nome_lower`

#### `nome_lower.startswith` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:213 (em FieldSearcher._calcular_score_match_nome)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:221 (em FieldSearcher._calcular_score_match_nome)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:251 (em FieldSearcher._determinar_tipo_match)
```

#### `nome_lower.endswith` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:216 (em FieldSearcher._calcular_score_match_nome)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:223 (em FieldSearcher._calcular_score_match_nome)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:253 (em FieldSearcher._determinar_tipo_match)
```

### 🔍 Objeto: `nome_modelo`

#### `nome_modelo.upper` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:215 (em ReadmeScanner._extrair_secao_modelo)
```

#### `nome_modelo.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:218 (em ReadmeScanner._extrair_secao_modelo)
```

#### `nome_modelo.endswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:204 (em AutoMapper._gerar_nome_modelo)
```

### 🔍 Objeto: `nome_modulo`

#### `nome_modulo.title` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:360 (em DevCommands._template_modulo_fallback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:368 (em DevCommands._template_modulo_fallback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:385 (em DevCommands._template_modulo_fallback)
```

### 🔍 Objeto: `nome_padrao`

#### `nome_padrao.lower` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:160 (em FieldSearcher.buscar_campos_por_nome)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:207 (em FieldSearcher._calcular_score_match_nome)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:247 (em FieldSearcher._determinar_tipo_match)
```

### 🔍 Objeto: `nome_tabela`

#### `nome_tabela.replace().split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:200 (em AutoMapper._gerar_nome_modelo)
```

#### `nome_tabela.replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:200 (em AutoMapper._gerar_nome_modelo)
```

### 🔍 Objeto: `nota`

#### `nota.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/enricher_manager.py:209 (em EnricherManager._analyze_billing)
```

### 🔍 Objeto: `numerical_consistency`

#### `numerical_consistency.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:93 (em CriticAgent.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:102 (em CriticAgent.top-level)
```

### 🔍 Objeto: `numerical_data`

#### `numerical_data.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:223 (em CriticAgent._validate_numerical_consistency)
```

### 🔍 Objeto: `operation`

#### `operation.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:539 (em OrchestratorManager._is_integration_operation)
```

### 🔍 Objeto: `operation_mapping`

#### `operation_mapping.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:600 (em IntelligenceCoordinator._component_supports_operation)
```

### 🔍 Objeto: `operation_type`

#### `operation_type.lower` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:331 (em OrchestratorManager._validate_operation_security)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:337 (em OrchestratorManager._validate_operation_security)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:337 (em OrchestratorManager._validate_operation_security)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:401 (em OrchestratorManager._detect_appropriate_orchestrator)
```

### 🔍 Objeto: `option_evaluations`

#### `option_evaluations.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:242 (em IntelligenceProcessor.make_intelligent_decision)
```

#### `option_evaluations.sort` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:245 (em IntelligenceProcessor.make_intelligent_decision)
```

### 🔍 Objeto: `orch_instance`

#### `orch_instance.health_check` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:648 (em OrchestratorManager.get_orchestrator_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:684 (em OrchestratorManager.health_check)
```

#### `orch_instance.get_status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:645 (em OrchestratorManager.get_orchestrator_status)
```

### 🔍 Objeto: `orch_type`

#### `orch_type.value` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:649 (em OrchestratorManager.get_orchestrator_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:654 (em OrchestratorManager.get_orchestrator_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:657 (em OrchestratorManager.get_orchestrator_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:660 (em OrchestratorManager.get_orchestrator_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:661 (em OrchestratorManager.get_orchestrator_status)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `orchestrator`

#### `orchestrator.components` (14 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:63 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:68 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:75 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:126 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:155 (em module.run_complete_flow)
  ... e mais 9 ocorrências
```

#### `orchestrator.components.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:75 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:126 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:155 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:176 (em module.run_complete_flow)
```

#### `orchestrator.workflows` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:64 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:69 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:101 (em module.run_complete_flow)
```

#### `orchestrator.process_query` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:509 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:947 (em SessionOrchestrator._process_deliveries_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:1019 (em SessionOrchestrator._process_general_inquiry)
```

#### `orchestrator.workflows.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:69 (em module.run_complete_flow)
```

#### `orchestrator.execute_workflow` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:107 (em module.run_complete_flow)
```

#### `orchestrator.create_session` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:484 (em OrchestratorManager.top-level)
```

#### `orchestrator.complete_session` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:491 (em OrchestratorManager.top-level)
```

#### `orchestrator.execute_session_workflow` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:496 (em OrchestratorManager.top-level)
```

### 🔍 Objeto: `original_response`

#### `original_response.copy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:161 (em AdaptiveLearning.adapt_response)
```

### 🔍 Objeto: `os`

#### `os.path` (50 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:9 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:9 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:9 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:15 (em ImportFilterer.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:15 (em ImportFilterer.__init__)
  ... e mais 45 ocorrências
```

#### `os.getenv` (33 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:99 (em ClaudeAPIClient.from_environment)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/integration_manager.py:375 (em IntegrationManager.get_integration_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/integration_manager.py:376 (em IntegrationManager.get_integration_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/integration_manager.py:380 (em IntegrationManager.get_integration_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/integration_manager.py:381 (em IntegrationManager.get_integration_status)
  ... e mais 28 ocorrências
```

#### `os.path.dirname` (21 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:9 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:9 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:15 (em ImportFilterer.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:222 (em ClassDuplicateFinder.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:17 (em module.top-level)
  ... e mais 16 ocorrências
```

#### `os.path.join` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:162 (em ImportFilterer.analyze_real_problems)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:261 (em ImportFilterer.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:266 (em ImportFilterer.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_finais_v2.py:32 (em module.verificar_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:18 (em module.top-level)
  ... e mais 6 ocorrências
```

#### `os.walk` (10 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:39 (em module.contar_arquivos_detalhado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:152 (em module.contar_linhas_codigo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:188 (em module.verificar_modulos_especiais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_finais_v2.py:29 (em module.verificar_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:119 (em DependencyChecker.check_fallback_quality)
  ... e mais 5 ocorrências
```

#### `os.environ.get` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:34 (em StandaloneContextManager._load_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:35 (em StandaloneContextManager._load_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:36 (em StandaloneContextManager._load_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:37 (em StandaloneContextManager._load_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:38 (em StandaloneContextManager._load_config)
  ... e mais 4 ocorrências
```

#### `os.environ` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:34 (em StandaloneContextManager._load_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:35 (em StandaloneContextManager._load_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:36 (em StandaloneContextManager._load_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:37 (em StandaloneContextManager._load_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:38 (em StandaloneContextManager._load_config)
  ... e mais 4 ocorrências
```

#### `os.getenv().lower` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:452 (em SystemConfig._detect_active_profile)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:457 (em SystemConfig._detect_active_profile)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:458 (em SystemConfig._detect_active_profile)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:86 (em SecurityGuard._is_production_mode)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:87 (em SecurityGuard._is_production_mode)
  ... e mais 4 ocorrências
```

#### `os.path.abspath` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:9 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:15 (em ImportFilterer.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:17 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:18 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:24 (em ImportChecker.__init__)
  ... e mais 2 ocorrências
```

#### `os.path.relpath` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:57 (em ImportChecker.check_file)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:185 (em ImportChecker.check_import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:196 (em ImportChecker.check_import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:207 (em ImportChecker.check_import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:65 (em StructureScanner.discover_project_structure)
```

#### `os.name` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:70 (em CursorMonitor.clear_screen)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:121 (em CursorMonitor.get_system_stats)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:131 (em CursorMonitor.check_flask_process)
```

#### `os.getcwd` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:52 (em ReadmeScanner._localizar_readme)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:78 (em SecurityGuard._is_production_mode)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:79 (em SecurityGuard._is_production_mode)
```

#### `os.getpid` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:34 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:40 (em module.top-level)
```

#### `os.path.exists` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_finais_v2.py:26 (em module.verificar_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:59 (em ReadmeScanner._localizar_readme)
```

#### `os.sep` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:188 (em module.verificar_import_existe)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:192 (em module.verificar_import_existe)
```

#### `os.environ.get().lower` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:34 (em StandaloneContextManager._load_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:35 (em StandaloneContextManager._load_config)
```

#### `os.path.basename` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_finais_v2.py:69 (em module.verificar_imports)
```

#### `os.path.split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:226 (em ImportChecker.filepath_to_module)
```

#### `os.system` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:70 (em CursorMonitor.clear_screen)
```

#### `os.path.isabs` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:187 (em FileScanner.read_file_content)
```

#### `os.path.normpath` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:58 (em ReadmeScanner._localizar_readme)
```

#### `os.sys.version` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:219 (em ProjectScanner._generate_scan_metadata)
```

#### `os.sys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:219 (em ProjectScanner._generate_scan_metadata)
```

#### `os.getenv().startswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:71 (em SecurityGuard._is_production_mode)
```

### 🔍 Objeto: `outliers`

#### `outliers.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:573 (em PerformanceAnalyzer.detect_outliers)
```

### 🔍 Objeto: `output`

#### `output.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:537 (em IntelligenceProcessor._learn_from_processing)
```

#### `output.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:636 (em IntelligenceProcessor._focused_synthesis)
```

### 🔍 Objeto: `outros_arquivos_local`

#### `outros_arquivos_local.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:70 (em module.contar_arquivos_detalhado)
```

### 🔍 Objeto: `overview`

#### `overview.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/response_utils.py:64 (em ResponseUtils._formatar_analise_projeto)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/response_utils.py:65 (em ResponseUtils._formatar_analise_projeto)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/response_utils.py:66 (em ResponseUtils._formatar_analise_projeto)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/response_utils.py:67 (em ResponseUtils._formatar_analise_projeto)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/response_utils.py:69 (em ResponseUtils._formatar_analise_projeto)
```

### 🔍 Objeto: `p`

#### `p.pattern_type` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:202 (em HumanInLoopLearning._create_learning_pattern)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:345 (em HumanInLoopLearning.generate_learning_report)
```

#### `p.strip` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:242 (em KnowledgeMemory.buscar_grupos_aplicaveis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:242 (em KnowledgeMemory.buscar_grupos_aplicaveis)
```

#### `p.data_pedido` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:108 (em PedidosLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:108 (em PedidosLoader._load_with_context)
```

#### `p.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:199 (em LearningCore.aplicar_conhecimento)
```

#### `p.created_at` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:323 (em HumanInLoopLearning.generate_learning_report)
```

#### `p.description` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:346 (em HumanInLoopLearning.generate_learning_report)
```

#### `p.frequency` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:347 (em HumanInLoopLearning.generate_learning_report)
```

#### `p.confidence_score` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:348 (em HumanInLoopLearning.generate_learning_report)
```

#### `p.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:102 (em PedidosLoader._load_with_context)
```

#### `p.num_pedido` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:103 (em PedidosLoader._load_with_context)
```

#### `p.cliente` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:104 (em PedidosLoader._load_with_context)
```

#### `p.destino` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:105 (em PedidosLoader._load_with_context)
```

#### `p.status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:106 (em PedidosLoader._load_with_context)
```

#### `p.status_calculado` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:107 (em PedidosLoader._load_with_context)
```

#### `p.data_pedido.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:108 (em PedidosLoader._load_with_context)
```

#### `p.valor_total` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:109 (em PedidosLoader._load_with_context)
```

#### `p.peso_total` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:110 (em PedidosLoader._load_with_context)
```

### 🔍 Objeto: `padrao`

#### `padrao.interpretation` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:358 (em PatternLearner.buscar_padroes_aplicaveis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:359 (em PatternLearner.buscar_padroes_aplicaveis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:362 (em PatternLearner.buscar_padroes_aplicaveis)
```

#### `padrao.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:308 (em PatternLearner._salvar_padrao_otimizado)
```

#### `padrao.pattern_type` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:368 (em PatternLearner.buscar_padroes_aplicaveis)
```

#### `padrao.pattern_text` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:369 (em PatternLearner.buscar_padroes_aplicaveis)
```

#### `padrao.confidence` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:371 (em PatternLearner.buscar_padroes_aplicaveis)
```

#### `padrao.usage_count` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:372 (em PatternLearner.buscar_padroes_aplicaveis)
```

### 🔍 Objeto: `padroes`

#### `padroes.append` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:126 (em PatternLearner._extrair_padroes_periodo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:149 (em PatternLearner._extrair_padroes_dominio)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:170 (em PatternLearner._extrair_padroes_intencao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:193 (em PatternLearner._extrair_padroes_entidades)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:207 (em PatternLearner._extrair_padroes_entidades)
  ... e mais 2 ocorrências
```

#### `padroes.extend` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:94 (em PatternLearner._extrair_padroes_multipos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:97 (em PatternLearner._extrair_padroes_multipos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:100 (em PatternLearner._extrair_padroes_multipos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:103 (em PatternLearner._extrair_padroes_multipos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:106 (em PatternLearner._extrair_padroes_multipos)
```

#### `padroes.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:485 (em AutoMapper._ajustar_confianca_com_analise)
```

### 🔍 Objeto: `padroes_aplicaveis`

#### `padroes_aplicaveis.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:367 (em PatternLearner.buscar_padroes_aplicaveis)
```

### 🔍 Objeto: `padroes_detectados`

#### `padroes_detectados.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:71 (em PatternLearner.extrair_e_salvar_padroes)
```

### 🔍 Objeto: `padroes_intencao`

#### `padroes_intencao.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:114 (em IntentionAnalyzer._detectar_intencoes_multiplas)
```

### 🔍 Objeto: `palavra`

#### `palavra.capitalize` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:201 (em AutoMapper._gerar_nome_modelo)
```

### 🔍 Objeto: `palavras_chave`

#### `palavras_chave.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:306 (em NLPEnhancedAnalyzer._extrair_palavras_chave)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:311 (em NLPEnhancedAnalyzer._extrair_palavras_chave)
```

### 🔍 Objeto: `palavras_corrigidas`

#### `palavras_corrigidas.append` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:199 (em NLPEnhancedAnalyzer._aplicar_correcoes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:203 (em NLPEnhancedAnalyzer._aplicar_correcoes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:205 (em NLPEnhancedAnalyzer._aplicar_correcoes)
```

### 🔍 Objeto: `palavras_relevantes`

#### `palavras_relevantes.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:397 (em PatternLearner._extrair_palavras_chave_dominio)
```

### 🔍 Objeto: `palavras_termo`

#### `palavras_termo.intersection` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:433 (em SemanticValidator._calcular_similaridade_termo_campo)
```

### 🔍 Objeto: `palavras_unicas`

#### `palavras_unicas.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:318 (em NLPEnhancedAnalyzer._extrair_palavras_chave)
```

### 🔍 Objeto: `parameters`

#### `parameters.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1499 (em MainOrchestrator._resolve_parameters)
```

### 🔍 Objeto: `params`

#### `params.get` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:467 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:485 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:487 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:488 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:492 (em OrchestratorManager.top-level)
  ... e mais 6 ocorrências
```

#### `params.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:163 (em QueryMapper._apply_template)
```

### 🔍 Objeto: `parent_parts`

#### `parent_parts.pop` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:163 (em ImportChecker.check_import)
```

#### `parent_parts.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:167 (em ImportChecker.check_import)
```

### 🔍 Objeto: `parsed`

#### `parsed.username` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:122 (em DatabaseConnection._try_direct_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:123 (em DatabaseConnection._try_direct_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:125 (em DatabaseConnection._try_direct_connection)
```

#### `parsed.password` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:127 (em DatabaseConnection._try_direct_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:128 (em DatabaseConnection._try_direct_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:130 (em DatabaseConnection._try_direct_connection)
```

#### `parsed.port` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:142 (em DatabaseConnection._try_direct_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:143 (em DatabaseConnection._try_direct_connection)
```

#### `parsed.query` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:146 (em DatabaseConnection._try_direct_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:147 (em DatabaseConnection._try_direct_connection)
```

#### `parsed.hostname` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:133 (em DatabaseConnection._try_direct_connection)
```

#### `parsed.scheme` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:153 (em DatabaseConnection._try_direct_connection)
```

#### `parsed.path` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:155 (em DatabaseConnection._try_direct_connection)
```

#### `parsed.params` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:156 (em DatabaseConnection._try_direct_connection)
```

#### `parsed.fragment` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:158 (em DatabaseConnection._try_direct_connection)
```

### 🔍 Objeto: `parsed_values`

#### `parsed_values.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:238 (em CriticAgent._validate_numerical_consistency)
```

### 🔍 Objeto: `parser`

#### `parser.add_argument` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:361 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:362 (em module.main)
```

#### `parser.parse_args` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:364 (em module.main)
```

### 🔍 Objeto: `part`

#### `part.startswith` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:43 (em module.contar_arquivos_detalhado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:154 (em module.contar_linhas_codigo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:189 (em module.verificar_modulos_especiais)
```

### 🔍 Objeto: `partial_text`

#### `partial_text.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:161 (em AutoCommandProcessor.get_command_suggestions)
```

### 🔍 Objeto: `parts`

#### `parts.insert` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:228 (em ImportChecker.filepath_to_module)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:234 (em ImportChecker.filepath_to_module)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:235 (em ImportChecker.filepath_to_module)
```

#### `parts.index` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:46 (em CircularDependencyMapper.extract_imports)
```

### 🔍 Objeto: `patch`

#### `patch.object` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:125 (em TestLoopPrevention.test_circular_reference_detection)
```

### 🔍 Objeto: `path`

#### `path.suffix` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:238 (em BaseValidationUtils.validate_file_path)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:238 (em BaseValidationUtils.validate_file_path)
```

#### `path.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:132 (em CircularDependencyMapper.dfs)
```

#### `path.index` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:143 (em CircularDependencyMapper.dfs)
```

#### `path.pop` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:148 (em CircularDependencyMapper.dfs)
```

#### `path.is_absolute` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:232 (em BaseValidationUtils.validate_file_path)
```

#### `path.exists` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:232 (em BaseValidationUtils.validate_file_path)
```

#### `path.suffix.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:238 (em BaseValidationUtils.validate_file_path)
```

### 🔍 Objeto: `pattern`

#### `pattern.lower` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:123 (em QueryMapper._pattern_matches)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:170 (em AutoCommandProcessor.get_command_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:305 (em AutoCommandProcessor._detect_commands)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:460 (em AutoCommandProcessor._calculate_detection_confidence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:464 (em AutoCommandProcessor._calculate_detection_confidence)
```

#### `pattern.confidence_score` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:227 (em HumanInLoopLearning._create_learning_pattern)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:234 (em HumanInLoopLearning._add_to_improvement_queue)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:239 (em HumanInLoopLearning._add_to_improvement_queue)
```

#### `pattern.lower().split` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:170 (em AutoCommandProcessor.get_command_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:464 (em AutoCommandProcessor._calculate_detection_confidence)
```

#### `pattern.lower().replace().replace().split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:123 (em QueryMapper._pattern_matches)
```

#### `pattern.lower().replace().replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:123 (em QueryMapper._pattern_matches)
```

#### `pattern.lower().replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:123 (em QueryMapper._pattern_matches)
```

#### `pattern.pattern_id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:235 (em HumanInLoopLearning._add_to_improvement_queue)
```

#### `pattern.description` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:237 (em HumanInLoopLearning._add_to_improvement_queue)
```

#### `pattern.improvement_suggestion` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:238 (em HumanInLoopLearning._add_to_improvement_queue)
```

#### `pattern.frequency` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:240 (em HumanInLoopLearning._add_to_improvement_queue)
```

#### `pattern.examples` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:241 (em HumanInLoopLearning._add_to_improvement_queue)
```

#### `pattern.pattern_type` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:246 (em HumanInLoopLearning._add_to_improvement_queue)
```

### 🔍 Objeto: `pattern_count`

#### `pattern_count.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:253 (em UninitializedVariableFinder.generate_report)
```

### 🔍 Objeto: `patterns`

#### `patterns.append` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:211 (em QueryAnalyzer._detect_temporal_patterns)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:344 (em AdaptiveLearning._detect_patterns)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:349 (em AdaptiveLearning._detect_patterns)
```

### 🔍 Objeto: `pd`

#### `pd.DataFrame` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:59 (em DataProcessor.process_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:263 (em DataProcessor.aggregate_data)
```

### 🔍 Objeto: `pedido`

#### `pedido.get` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:319 (em ResponseProcessor._construir_prompt_otimizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:319 (em ResponseProcessor._construir_prompt_otimizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:319 (em ResponseProcessor._construir_prompt_otimizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/enricher_manager.py:176 (em EnricherManager._analyze_orders)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/enricher_manager.py:178 (em EnricherManager._analyze_orders)
  ... e mais 1 ocorrências
```

#### `pedido.data_pedido` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:474 (em ContextProcessor._serialize_pedido)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:348 (em DataProvider._serialize_pedido)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:348 (em DataProvider._serialize_pedido)
```

#### `pedido.id` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:471 (em ContextProcessor._serialize_pedido)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:345 (em DataProvider._serialize_pedido)
```

#### `pedido.num_pedido` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:472 (em ContextProcessor._serialize_pedido)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:346 (em DataProvider._serialize_pedido)
```

#### `pedido.valor_total` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:349 (em DataProvider._serialize_pedido)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:349 (em DataProvider._serialize_pedido)
```

#### `pedido.raz_social_red` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:473 (em ContextProcessor._serialize_pedido)
```

#### `pedido.valor_saldo_total` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:475 (em ContextProcessor._serialize_pedido)
```

#### `pedido.status_calculado` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:476 (em ContextProcessor._serialize_pedido)
```

#### `pedido.cliente` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:347 (em DataProvider._serialize_pedido)
```

#### `pedido.data_pedido.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:348 (em DataProvider._serialize_pedido)
```

#### `pedido.status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:350 (em DataProvider._serialize_pedido)
```

#### `pedido.vendedor` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:351 (em DataProvider._serialize_pedido)
```

### 🔍 Objeto: `pendencia`

#### `pendencia.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:483 (em ContextProcessor._serialize_pendencia)
```

#### `pendencia.numero_nf` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:484 (em ContextProcessor._serialize_pendencia)
```

#### `pendencia.nome_cliente` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:485 (em ContextProcessor._serialize_pendencia)
```

#### `pendencia.descricao` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:486 (em ContextProcessor._serialize_pendencia)
```

#### `pendencia.data_criacao` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:487 (em ContextProcessor._serialize_pendencia)
```

#### `pendencia.resolvida` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:488 (em ContextProcessor._serialize_pendencia)
```

### 🔍 Objeto: `pending_steps`

#### `pending_steps.remove` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1044 (em MainOrchestrator.top-level)
```

### 🔍 Objeto: `performance_info`

#### `performance_info.update` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:347 (em DatabaseScanner._get_performance_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:349 (em DatabaseScanner._get_performance_info)
```

### 🔍 Objeto: `ph`

#### `ph.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:331 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:333 (em module.main)
```

### 🔍 Objeto: `pilha`

#### `pilha.pop` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:318 (em RelationshipMapper._explorar_cluster)
```

#### `pilha.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:338 (em RelationshipMapper._explorar_cluster)
```

### 🔍 Objeto: `pip_info`

#### `pip_info.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:177 (em DependencyChecker.analyze_dependencies)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:180 (em DependencyChecker.analyze_dependencies)
```

### 🔍 Objeto: `pk`

#### `pk.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:215 (em MetadataScanner._obter_constraints_tabela)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:216 (em MetadataScanner._obter_constraints_tabela)
```

### 🔍 Objeto: `pk_constraint`

#### `pk_constraint.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:133 (em StructureScanner._discover_models_via_database)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:144 (em StructureScanner._discover_models_via_database)
```

### 🔍 Objeto: `predictions`

#### `predictions.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:764 (em IntelligenceProcessor._make_trend_predictions)
```

### 🔍 Objeto: `preference_data`

#### `preference_data.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:460 (em AdaptiveLearning._generate_preference_recommendations)
```

### 🔍 Objeto: `preferences`

#### `preferences.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:128 (em AdaptiveLearning.get_personalized_recommendations)
```

### 🔍 Objeto: `primeiro_exemplo`

#### `primeiro_exemplo.isdigit` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:425 (em AutoMapper._melhorar_termos_com_analise)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:429 (em AutoMapper._melhorar_termos_com_analise)
```

#### `primeiro_exemplo.replace().replace().replace().isdigit` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:421 (em AutoMapper._melhorar_termos_com_analise)
```

#### `primeiro_exemplo.replace().replace().replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:421 (em AutoMapper._melhorar_termos_com_analise)
```

#### `primeiro_exemplo.replace().replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:421 (em AutoMapper._melhorar_termos_com_analise)
```

#### `primeiro_exemplo.replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:421 (em AutoMapper._melhorar_termos_com_analise)
```

#### `primeiro_exemplo.startswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:437 (em AutoMapper._melhorar_termos_com_analise)
```

### 🔍 Objeto: `priority`

#### `priority.value` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:237 (em SessionOrchestrator.create_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:253 (em SessionOrchestrator.create_session)
```

### 🔍 Objeto: `priority_filter`

#### `priority_filter.upper` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:253 (em HumanInLoopLearning.get_improvement_suggestions)
```

### 🔍 Objeto: `priority_order`

#### `priority_order.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:259 (em HumanInLoopLearning.get_improvement_suggestions)
```

### 🔍 Objeto: `priority_value`

#### `priority_value.upper` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:472 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:474 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:476 (em OrchestratorManager.top-level)
```

### 🔍 Objeto: `problem`

#### `problem.get` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:230 (em ImportFilterer.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:233 (em ImportFilterer.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:234 (em ImportFilterer.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:235 (em ImportFilterer.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:236 (em ImportFilterer.generate_report)
  ... e mais 2 ocorrências
```

#### `problem.startswith` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/__init__.py:264 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/__init__.py:266 (em module.top-level)
```

### 🔍 Objeto: `problem_key`

#### `problem_key.split` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:197 (em module.find_real_problems)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:281 (em module.find_real_problems)
```

### 🔍 Objeto: `problem_type`

#### `problem_type.upper` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:199 (em module.find_real_problems)
```

### 🔍 Objeto: `problema`

#### `problema.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:266 (em module.main)
```

### 🔍 Objeto: `problemas`

#### `problemas.append` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:168 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:189 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:200 (em module.analisar_arquivo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:213 (em module.analisar_arquivo)
```

### 🔍 Objeto: `problemas_por_tipo`

#### `problemas_por_tipo.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:294 (em module.main)
```

### 🔍 Objeto: `problemas_reais`

#### `problemas_reais.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_finais_v2.py:54 (em module.verificar_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_finais_v2.py:65 (em module.verificar_imports)
```

### 🔍 Objeto: `problems_by_type`

#### `problems_by_type.items` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:196 (em module.find_real_problems)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:266 (em module.find_real_problems)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:280 (em module.find_real_problems)
```

### 🔍 Objeto: `process`

#### `process.extractOne` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:193 (em NLPEnhancedAnalyzer._aplicar_correcoes)
```

### 🔍 Objeto: `processed_data_list`

#### `processed_data_list.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:172 (em DataProcessor.batch_process)
```

### 🔍 Objeto: `processing_times`

#### `processing_times.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:149 (em PerformanceAnalyzer.analyze_ai_performance)
```

### 🔍 Objeto: `processor`

#### `processor.memory_manager` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:179 (em module.run_complete_flow)
```

#### `processor.enricher` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:180 (em module.run_complete_flow)
```

#### `processor.execute_processing_chain` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:194 (em module.run_complete_flow)
```

#### `processor.process_data` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/__init__.py:171 (em module.process_data)
```

#### `processor.process_query` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/__init__.py:199 (em module.process_query)
```

#### `processor.process_context` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/__init__.py:227 (em module.process_context)
```

#### `processor.process_intelligence` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/__init__.py:255 (em module.process_intelligence)
```

#### `processor.synthesize_multi_source_intelligence` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/__init__.py:282 (em module.synthesize_multi_source_intelligence)
```

#### `processor.batch_process` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/__init__.py:310 (em module.batch_process_data)
```

#### `processor.set_memory` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:345 (em module.set_memory)
```

#### `processor.get_status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:198 (em ProcessorRegistry.get_processor_info)
```

#### `processor.health_check` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:210 (em ProcessorRegistry._check_processor_health)
```

#### `processor.initialized` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:214 (em ProcessorRegistry._check_processor_health)
```

#### `processor.set_memory_manager` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1442 (em MainOrchestrator._connect_modules)
```

#### `processor.set_enricher` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1466 (em MainOrchestrator._connect_modules)
```

#### `processor.gerar_resposta_otimizada` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:745 (em SessionOrchestrator._execute_workflow)
```

### 🔍 Objeto: `profile`

#### `profile.get` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:124 (em AdaptiveLearning.get_personalized_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:125 (em AdaptiveLearning.get_personalized_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:171 (em AdaptiveLearning.adapt_response)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:308 (em AdaptiveLearning._extract_preferences)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:427 (em AdaptiveLearning._calculate_learning_confidence)
  ... e mais 1 ocorrências
```

#### `profile.setdefault` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:517 (em AdaptiveLearning._handle_negative_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:521 (em AdaptiveLearning._handle_negative_feedback)
```

#### `profile.get().get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:532 (em AdaptiveLearning._handle_positive_feedback)
```

### 🔍 Objeto: `profile_path`

#### `profile_path.exists` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:537 (em SystemConfig._load_profile_config)
```

#### `profile_path.parent.mkdir` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:564 (em SystemConfig._save_profile_config)
```

#### `profile_path.parent` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:564 (em SystemConfig._save_profile_config)
```

### 🔍 Objeto: `provider`

#### `provider.gerar_system_prompt_real` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/data_manager.py:197 (em DataManager.provide_data)
```

#### `provider.gerar_relatorio_dados_sistema` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/data_manager.py:199 (em DataManager.provide_data)
```

#### `provider.buscar_clientes_reais` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/data_manager.py:201 (em DataManager.provide_data)
```

#### `provider.buscar_transportadoras_reais` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/data_manager.py:203 (em DataManager.provide_data)
```

#### `provider.buscar_todos_modelos_reais` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/data_manager.py:205 (em DataManager.provide_data)
```

#### `provider.validar_cliente_existe` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/data_manager.py:283 (em DataManager.validate_client)
```

#### `provider.sugerir_cliente_similar` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/data_manager.py:293 (em DataManager.validate_client)
```

#### `provider.data_provider` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1418 (em MainOrchestrator._connect_modules)
```

#### `provider.set_loader` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1428 (em MainOrchestrator._connect_modules)
```

### 🔍 Objeto: `psutil`

#### `psutil.disk_usage().percent` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:121 (em CursorMonitor.get_system_stats)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:121 (em CursorMonitor.get_system_stats)
```

#### `psutil.disk_usage` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:121 (em CursorMonitor.get_system_stats)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:121 (em CursorMonitor.get_system_stats)
```

#### `psutil.cpu_percent` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:119 (em CursorMonitor.get_system_stats)
```

#### `psutil.virtual_memory().percent` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:120 (em CursorMonitor.get_system_stats)
```

#### `psutil.virtual_memory` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:120 (em CursorMonitor.get_system_stats)
```

#### `psutil.boot_time` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:122 (em CursorMonitor.get_system_stats)
```

### 🔍 Objeto: `py_file`

#### `py_file.name` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:37 (em ClassDuplicateFinder.scan_directory)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:99 (em UninitializedVariableFinder.scan_directory)
```

#### `py_file.exists` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:198 (em module.verificar_import_existe)
```

### 🔍 Objeto: `py_files`

#### `py_files.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:97 (em CircularDependencyMapper.build_dependency_graph)
```

### 🔍 Objeto: `qualidade`

#### `qualidade.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:225 (em ResponseProcessor.gerar_resposta_otimizada)
```

### 🔍 Objeto: `query`

#### `query.filter` (86 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:289 (em ContextProcessor._carregar_dados_entregas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:294 (em ContextProcessor._carregar_dados_entregas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:326 (em ContextProcessor._carregar_dados_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:331 (em ContextProcessor._carregar_dados_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:363 (em ContextProcessor._carregar_dados_pedidos)
  ... e mais 81 ocorrências
```

#### `query.lower` (33 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:91 (em QueryMapper.map_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:61 (em QueryAnalyzer.analyze_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:111 (em QueryAnalyzer._calculate_complexity)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:115 (em QueryAnalyzer._calculate_complexity)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:160 (em QueryAnalyzer._extract_entities)
  ... e mais 28 ocorrências
```

#### `query.limit().all` (26 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:297 (em ContextProcessor._carregar_dados_entregas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:334 (em ContextProcessor._carregar_dados_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:371 (em ContextProcessor._carregar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:403 (em ContextProcessor._carregar_dados_financeiro)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:181 (em DataProvider._get_entregas_data)
  ... e mais 21 ocorrências
```

#### `query.limit` (26 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:297 (em ContextProcessor._carregar_dados_entregas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:334 (em ContextProcessor._carregar_dados_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:371 (em ContextProcessor._carregar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:403 (em ContextProcessor._carregar_dados_financeiro)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:181 (em DataProvider._get_entregas_data)
  ... e mais 21 ocorrências
```

#### `query.split` (12 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:142 (em QueryMapper._extract_parameters)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:62 (em QueryAnalyzer.analyze_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:52 (em MetacognitiveAnalyzer._assess_query_complexity)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:55 (em MetacognitiveAnalyzer._assess_query_complexity)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:48 (em IntentionAnalyzer.analyze_intention)
  ... e mais 7 ocorrências
```

#### `query.order_by` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:251 (em ContextLoader._carregar_entregas_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:370 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:186 (em AgendamentosLoader._build_agendamentos_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:176 (em FaturamentoLoader._build_faturamento_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:195 (em FretesLoader._build_fretes_query)
  ... e mais 6 ocorrências
```

#### `query.count` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:305 (em ContextProcessor._carregar_dados_entregas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:342 (em ContextProcessor._carregar_dados_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:379 (em ContextProcessor._carregar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:411 (em ContextProcessor._carregar_dados_financeiro)
```

#### `query.join().filter` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:175 (em AgendamentosLoader._build_agendamentos_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:99 (em EmbarquesLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:177 (em EmbarquesLoader._build_embarques_query)
```

#### `query.join` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:175 (em AgendamentosLoader._build_agendamentos_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:99 (em EmbarquesLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:177 (em EmbarquesLoader._build_embarques_query)
```

#### `query.lower().strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:91 (em QueryMapper.map_query)
```

#### `query.lower().split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:171 (em QueryAnalyzer._extract_entities)
```

#### `query.replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:217 (em SemanticLoopProcessor._expand_unmapped_terms)
```

#### `query.order_by().limit().all` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:251 (em ContextLoader._carregar_entregas_banco)
```

#### `query.order_by().limit` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:251 (em ContextLoader._carregar_entregas_banco)
```

#### `query.strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:131 (em BaseValidationUtils.validate_query)
```

### 🔍 Objeto: `query_base`

#### `query_base.filter` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:175 (em ValidationUtils._calcular_estatisticas_especificas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:180 (em ValidationUtils._calcular_estatisticas_especificas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:189 (em ValidationUtils._calcular_estatisticas_especificas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:192 (em ValidationUtils._calcular_estatisticas_especificas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:195 (em ValidationUtils._calcular_estatisticas_especificas)
  ... e mais 1 ocorrências
```

#### `query_base.filter().count` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:195 (em ValidationUtils._calcular_estatisticas_especificas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:196 (em ValidationUtils._calcular_estatisticas_especificas)
```

#### `query_base.count` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:194 (em ValidationUtils._calcular_estatisticas_especificas)
```

### 🔍 Objeto: `query_mapper`

#### `query_mapper.analisar_consulta_semantica` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/__init__.py:89 (em module.analyze_query_mapping)
```

### 🔍 Objeto: `query_processor`

#### `query_processor.process_query` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:101 (em ProcessorManager.process_query)
```

### 🔍 Objeto: `query_types`

#### `query_types.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:383 (em AdaptiveLearning._detect_query_pattern)
```

### 🔍 Objeto: `r`

#### `r.transportadora` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:462 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:232 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:232 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:274 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:274 (em FretesLoader._format_fretes_results)
  ... e mais 4 ocorrências
```

#### `r.data_embarque` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:453 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:453 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:272 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:272 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:213 (em EmbarquesLoader._format_embarques_results)
  ... e mais 3 ocorrências
```

#### `r.data_agendamento` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:212 (em AgendamentosLoader._format_agendamentos_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:212 (em AgendamentosLoader._format_agendamentos_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:213 (em AgendamentosLoader._format_agendamentos_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:213 (em AgendamentosLoader._format_agendamentos_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:214 (em AgendamentosLoader._format_agendamentos_results)
  ... e mais 3 ocorrências
```

#### `r.data_criacao` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:233 (em AgendamentosLoader._format_agendamentos_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:233 (em AgendamentosLoader._format_agendamentos_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:271 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:271 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:239 (em PedidosLoader._format_pedidos_results)
  ... e mais 3 ocorrências
```

#### `r.get` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:220 (em ProcessorManager.reload_processors)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:191 (em ProcessorCoordinator.execute_parallel_processors)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:737 (em IntelligenceCoordinator._calculate_performance_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:738 (em IntelligenceCoordinator._calculate_performance_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:864 (em IntelligenceCoordinator._calculate_overall_confidence)
  ... e mais 2 ocorrências
```

#### `r.data_entrega_prevista` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:399 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:399 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:443 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:443 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:454 (em EntregasLoader._format_entregas_results)
  ... e mais 1 ocorrências
```

#### `r.valor_total` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:198 (em FaturamentoLoader._format_faturamento_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:211 (em FaturamentoLoader._format_faturamento_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:228 (em FaturamentoLoader._format_faturamento_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:191 (em PedidosLoader._format_pedidos_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:228 (em PedidosLoader._format_pedidos_results)
  ... e mais 1 ocorrências
```

#### `r.entregue` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:393 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:399 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:439 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:455 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:457 (em EntregasLoader._format_entregas_results)
```

#### `r.peso_total` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:460 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:278 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:192 (em PedidosLoader._format_pedidos_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:229 (em PedidosLoader._format_pedidos_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:241 (em PedidosLoader._format_pedidos_results)
```

#### `r.created_at` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:185 (em SessionMemory.get_sessions_by_user)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:185 (em SessionMemory.get_sessions_by_user)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:239 (em SessionMemory.search_sessions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:239 (em SessionMemory.search_sessions)
```

#### `r.updated_at` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:186 (em SessionMemory.get_sessions_by_user)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:186 (em SessionMemory.get_sessions_by_user)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:240 (em SessionMemory.search_sessions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:240 (em SessionMemory.search_sessions)
```

#### `r.data_criacao.strftime` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:233 (em AgendamentosLoader._format_agendamentos_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:271 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:239 (em PedidosLoader._format_pedidos_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:249 (em EmbarquesLoader._format_embarques_results)
```

#### `r.valor_cotado` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:218 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:240 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:254 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:275 (em FretesLoader._format_fretes_results)
```

#### `r.valor_considerado` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:219 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:241 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:255 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:276 (em FretesLoader._format_fretes_results)
```

#### `r.status` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:224 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:273 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:219 (em EmbarquesLoader._format_embarques_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:251 (em EmbarquesLoader._format_embarques_results)
```

#### `r.transportadora.razao_social` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:232 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:274 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:227 (em EmbarquesLoader._format_embarques_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:252 (em EmbarquesLoader._format_embarques_results)
```

#### `r.cliente` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:246 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:269 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:199 (em PedidosLoader._format_pedidos_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:238 (em PedidosLoader._format_pedidos_results)
```

#### `r.itens` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:244 (em EmbarquesLoader._format_embarques_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:245 (em EmbarquesLoader._format_embarques_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:257 (em EmbarquesLoader._format_embarques_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:258 (em EmbarquesLoader._format_embarques_results)
```

#### `r.destino` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:452 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:270 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:244 (em PedidosLoader._format_pedidos_results)
```

#### `r.data_embarque.strftime` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:453 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:272 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:250 (em EmbarquesLoader._format_embarques_results)
```

#### `r.numero_embarque` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:461 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:280 (em FretesLoader._format_fretes_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:248 (em EmbarquesLoader._format_embarques_results)
```

#### `r.session_id` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:184 (em SessionMemory.get_sessions_by_user)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:238 (em SessionMemory.search_sessions)
```

#### `r.created_at.isoformat` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:185 (em SessionMemory.get_sessions_by_user)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:239 (em SessionMemory.search_sessions)
```

#### `r.updated_at.isoformat` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:186 (em SessionMemory.get_sessions_by_user)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:240 (em SessionMemory.search_sessions)
```

#### `r.user_id` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:187 (em SessionMemory.get_sessions_by_user)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:241 (em SessionMemory.search_sessions)
```

#### `r.metadata_jsonb` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:188 (em SessionMemory.get_sessions_by_user)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:242 (em SessionMemory.search_sessions)
```

#### `r.numero_nf` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:450 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:225 (em FaturamentoLoader._format_faturamento_results)
```

#### `r.data_entrega_real` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:456 (em EntregasLoader._format_entregas_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:456 (em EntregasLoader._format_entregas_results)
```

#### `r.observacoes` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:235 (em AgendamentosLoader._format_agendamentos_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:245 (em PedidosLoader._format_pedidos_results)
```

#### `r.nome_cliente` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:204 (em FaturamentoLoader._format_faturamento_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:226 (em FaturamentoLoader._format_faturamento_results)
```

#### `r.cnpj_cliente` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:209 (em FaturamentoLoader._format_faturamento_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:227 (em FaturamentoLoader._format_faturamento_results)
```

#### `r.data_fatura` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:229 (em FaturamentoLoader._format_faturamento_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:229 (em FaturamentoLoader._format_faturamento_results)
```

#### `r.data_expedicao` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:243 (em PedidosLoader._format_pedidos_results)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:243 (em PedidosLoader._format_pedidos_results)
```

#### `r.ping` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:241 (em DependencyChecker.check_redis_connection)
```

#### `r.data_entrega_prevista.strftime` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:454 (em EntregasLoader._format_entregas_results)
```

#### `r.data_entrega_real.strftime` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:456 (em EntregasLoader._format_entregas_results)
```

#### `r.lead_time` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:458 (em EntregasLoader._format_entregas_results)
```

#### `r.valor_nf` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:459 (em EntregasLoader._format_entregas_results)
```

#### `r.entrega_monitorada` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:228 (em AgendamentosLoader._format_agendamentos_results)
```

#### `r.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:231 (em AgendamentosLoader._format_agendamentos_results)
```

#### `r.data_agendamento.strftime` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:232 (em AgendamentosLoader._format_agendamentos_results)
```

#### `r.entrega_id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:239 (em AgendamentosLoader._format_agendamentos_results)
```

#### `r.data_fatura.strftime` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:229 (em FaturamentoLoader._format_faturamento_results)
```

#### `r.origem` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:230 (em FaturamentoLoader._format_faturamento_results)
```

#### `r.incoterm` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:231 (em FaturamentoLoader._format_faturamento_results)
```

#### `r.numero_frete` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:268 (em FretesLoader._format_fretes_results)
```

#### `r.valor_pago` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:277 (em FretesLoader._format_fretes_results)
```

#### `r.cte_numero` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:279 (em FretesLoader._format_fretes_results)
```

#### `r.num_pedido` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:237 (em PedidosLoader._format_pedidos_results)
```

#### `r.data_expedicao.strftime` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:243 (em PedidosLoader._format_pedidos_results)
```

#### `r.placa_veiculo` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:253 (em EmbarquesLoader._format_embarques_results)
```

#### `r.motorista` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:254 (em EmbarquesLoader._format_embarques_results)
```

### 🔍 Objeto: `re`

#### `re.search` (28 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:121 (em ImportFilterer.is_false_positive)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:126 (em ImportFilterer.is_false_positive)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:131 (em ImportFilterer.is_false_positive)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:139 (em ImportFilterer.is_false_positive)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:144 (em ImportFilterer.is_false_positive)
  ... e mais 23 ocorrências
```

#### `re.findall` (23 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:182 (em IntentionAnalyzer._detectar_especificidade)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:239 (em SemanticAnalyzer._extract_entities)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:272 (em SemanticAnalyzer._extract_keywords)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:335 (em AutoCommandProcessor._extract_parameters)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:340 (em AutoCommandProcessor._extract_parameters)
  ... e mais 18 ocorrências
```

#### `re.IGNORECASE` (21 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:121 (em ImportFilterer.is_false_positive)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:126 (em ImportFilterer.is_false_positive)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:131 (em ImportFilterer.is_false_positive)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:139 (em ImportFilterer.is_false_positive)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:144 (em ImportFilterer.is_false_positive)
  ... e mais 16 ocorrências
```

#### `re.sub` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:227 (em NLPEnhancedAnalyzer._tokenizar_basico)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:392 (em BaseValidationUtils.sanitize_input)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:395 (em BaseValidationUtils.sanitize_input)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:271 (em BaseProcessor._sanitize_input)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:91 (em BaseCommand._sanitize_input)
  ... e mais 4 ocorrências
```

#### `re.DOTALL` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:111 (em ReadmeScanner.buscar_termos_naturais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:268 (em ReadmeScanner._buscar_campo_na_secao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:313 (em ReadmeScanner.obter_informacoes_campo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:320 (em ReadmeScanner.obter_informacoes_campo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:326 (em ReadmeScanner.obter_informacoes_campo)
  ... e mais 4 ocorrências
```

#### `re.escape` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:110 (em ReadmeScanner.buscar_termos_naturais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:129 (em ReadmeScanner.buscar_termos_naturais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:215 (em ReadmeScanner._extrair_secao_modelo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:216 (em ReadmeScanner._extrair_secao_modelo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:217 (em ReadmeScanner._extrair_secao_modelo)
  ... e mais 3 ocorrências
```

#### `re.MULTILINE` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:133 (em DependencyChecker.check_fallback_quality)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:237 (em ReadmeScanner._extrair_secao_modelo)
```

#### `re.match` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:100 (em BaseValidationUtils._validate_with_rules)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:342 (em SecurityGuard.validate_token)
```

#### `re.sub().replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:236 (em CriticAgent._validate_numerical_consistency)
```

### 🔍 Objeto: `readme_data`

#### `readme_data.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:261 (em SemanticEnricher._sugestoes_readme_vs_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:374 (em SemanticEnricher._sugestoes_otimizacao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:389 (em SemanticEnricher._sugestoes_otimizacao)
```

### 🔍 Objeto: `readme_scanner`

#### `readme_scanner.validar_estrutura_readme` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:227 (em DiagnosticsAnalyzer.gerar_relatorio_enriquecido)
```

#### `readme_scanner.buscar_termos_naturais` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:131 (em SemanticEnricher._enriquecer_via_readme)
```

#### `readme_scanner.obter_informacoes_campo` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:138 (em SemanticEnricher._enriquecer_via_readme)
```

#### `readme_scanner.listar_modelos_disponiveis` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:240 (em SemanticValidator.validar_consistencia_readme_banco)
```

### 🔍 Objeto: `readme_status`

#### `readme_status.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:344 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:345 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
```

### 🔍 Objeto: `ready_steps`

#### `ready_steps.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1032 (em MainOrchestrator.top-level)
```

### 🔍 Objeto: `real_problems`

#### `real_problems.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:228 (em ImportFilterer.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:301 (em module.main)
```

### 🔍 Objeto: `reasoning`

#### `reasoning.append` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:713 (em IntelligenceProcessor._generate_decision_reasoning)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:716 (em IntelligenceProcessor._generate_decision_reasoning)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:719 (em IntelligenceProcessor._generate_decision_reasoning)
```

### 🔍 Objeto: `rec_stack`

#### `rec_stack.add` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:131 (em CircularDependencyMapper.dfs)
```

#### `rec_stack.remove` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:149 (em CircularDependencyMapper.dfs)
```

### 🔍 Objeto: `recomendacoes`

#### `recomendacoes.append` (16 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:340 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:348 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:356 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:362 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:368 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  ... e mais 11 ocorrências
```

### 🔍 Objeto: `recommendations`

#### `recommendations.append` (18 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:237 (em StructuralAnalyzer._generate_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:239 (em StructuralAnalyzer._generate_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:241 (em StructuralAnalyzer._generate_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:528 (em IntelligenceProcessor._generate_auto_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:669 (em IntelligenceProcessor._generate_synthetic_recommendations)
  ... e mais 13 ocorrências
```

#### `recommendations.extend` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:129 (em AdaptiveLearning.get_personalized_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:135 (em AdaptiveLearning.get_personalized_recommendations)
```

### 🔍 Objeto: `redis`

#### `redis.Redis` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:240 (em DependencyChecker.check_redis_connection)
```

### 🔍 Objeto: `redis_cache`

#### `redis_cache.set` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:509 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:233 (em BaseCommand._set_cached_result)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:68 (em ContextMemory.store_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:71 (em SystemMemory.store_system_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:150 (em SystemMemory.store_component_state)
  ... e mais 1 ocorrências
```

#### `redis_cache.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:285 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:216 (em BaseCommand._get_cached_result)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:98 (em ContextMemory.retrieve_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:101 (em SystemMemory.retrieve_system_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:180 (em SystemMemory.retrieve_component_state)
```

#### `redis_cache.cache_entregas_cliente` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:358 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:429 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:444 (em ContextLoader._carregar_contexto_inteligente)
```

#### `redis_cache.cache_estatisticas_cliente` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:471 (em ContextLoader._carregar_contexto_inteligente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:478 (em ContextLoader._carregar_contexto_inteligente)
```

#### `redis_cache._gerar_chave` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:276 (em ContextLoader._carregar_contexto_inteligente)
```

#### `redis_cache.delete` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:195 (em ContextMemory.clear_context)
```

### 🔍 Objeto: `redis_checks`

#### `redis_checks.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:178 (em module.analisar_arquivo)
```

### 🔍 Objeto: `reference_date`

#### `reference_date.isoformat` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/context_provider.py:177 (em ContextProvider.provide_temporal_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/context_provider.py:180 (em ContextProvider.provide_temporal_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/context_provider.py:200 (em ContextProvider.provide_temporal_context)
```

### 🔍 Objeto: `regra`

#### `regra.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:112 (em SemanticValidator.validar_contexto_negocio)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:115 (em SemanticValidator.validar_contexto_negocio)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:135 (em SemanticValidator.validar_contexto_negocio)
```

### 🔍 Objeto: `rel_path`

#### `rel_path.parts` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:62 (em FileScanner.discover_all_templates)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:62 (em FileScanner.discover_all_templates)
```

### 🔍 Objeto: `relacionamentos`

#### `relacionamentos.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:84 (em RelationshipMapper.obter_relacionamentos)
```

#### `relacionamentos.extend` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:88 (em RelationshipMapper.obter_relacionamentos)
```

### 🔍 Objeto: `relacionamentos_entrada`

#### `relacionamentos_entrada.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:136 (em RelationshipMapper._buscar_relacionamentos_entrada)
```

### 🔍 Objeto: `relatorio`

#### `relatorio.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:336 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:343 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:351 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:365 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:371 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
```

### 🔍 Objeto: `relevant_responses`

#### `relevant_responses.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:313 (em CriticAgent._check_business_rule)
```

### 🔍 Objeto: `report`

#### `report.append` (157 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:204 (em ImportFilterer.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:205 (em ImportFilterer.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:208 (em ImportFilterer.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:209 (em ImportFilterer.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:210 (em ImportFilterer.generate_report)
  ... e mais 152 ocorrências
```

### 🔍 Objeto: `request`

#### `request.query.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:118 (em ProviderManager._detect_provision_type)
```

### 🔍 Objeto: `request_data`

#### `request_data.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:292 (em StandaloneIntegration.process_request)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:293 (em StandaloneIntegration.process_request)
```

### 🔍 Objeto: `requests`

#### `requests.exceptions` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:95 (em CursorMonitor.check_url)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:101 (em CursorMonitor.check_url)
```

#### `requests.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:85 (em CursorMonitor.check_url)
```

#### `requests.exceptions.ConnectionError` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:95 (em CursorMonitor.check_url)
```

#### `requests.exceptions.Timeout` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:101 (em CursorMonitor.check_url)
```

### 🔍 Objeto: `response`

#### `response.headers.get().startswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:93 (em CursorMonitor.check_url)
```

#### `response.headers.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:93 (em CursorMonitor.check_url)
```

#### `response.get().lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:311 (em CriticAgent._check_business_rule)
```

### 🔍 Objeto: `response_processor`

#### `response_processor.gerar_resposta_otimizada` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:65 (em ProcessorManager.process_response)
```

#### `response_processor.set_memory_manager` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:260 (em ProcessorManager.set_memory_manager)
```

### 🔍 Objeto: `response_result`

#### `response_result.get` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:362 (em WebFlaskRoutes.api_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:363 (em WebFlaskRoutes.api_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:370 (em WebFlaskRoutes.api_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:376 (em WebFlaskRoutes.api_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:377 (em WebFlaskRoutes.api_query)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `response_text`

#### `response_text.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:239 (em TestLoopPrevention.test_anti_loop_response_quality)
```

### 🔍 Objeto: `resposta`

#### `resposta.lower` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:366 (em ResponseProcessor._avaliar_qualidade_resposta)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:366 (em ResponseProcessor._avaliar_qualidade_resposta)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:372 (em ResponseProcessor._avaliar_qualidade_resposta)
```

#### `resposta.count` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:377 (em ResponseProcessor._avaliar_qualidade_resposta)
```

#### `resposta.strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:461 (em ResponseProcessor._validar_resposta_final)
```

#### `resposta.split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:465 (em ResponseProcessor._validar_resposta_final)
```

### 🔍 Objeto: `result`

#### `result.get` (58 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:256 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:287 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:210 (em ClaudeAINovo.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:212 (em ClaudeAINovo.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:218 (em ClaudeAINovo.top-level)
  ... e mais 53 ocorrências
```

#### `result.stdout` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:83 (em DependencyChecker.check_pip_package)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:138 (em CursorMonitor.check_flask_process)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:139 (em CursorMonitor.check_flask_process)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:163 (em CursorMonitor.run_validator)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:174 (em CursorMonitor.run_validator)
```

#### `result.returncode` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:81 (em DependencyChecker.check_pip_package)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:138 (em CursorMonitor.check_flask_process)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:161 (em CursorMonitor.run_validator)
```

#### `result.stdout.strip` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:83 (em DependencyChecker.check_pip_package)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:138 (em CursorMonitor.check_flask_process)
```

#### `result.stderr` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:93 (em DependencyChecker.check_pip_package)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:176 (em CursorMonitor.run_validator)
```

#### `result.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:273 (em SuggestionsEngine._generate_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:276 (em SuggestionsEngine._generate_suggestions)
```

#### `result.get().get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:547 (em DataProcessor._update_global_stats)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:858 (em IntelligenceCoordinator._combine_all_insights)
```

#### `result.keys` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:116 (em DatabaseLoader.load_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:395 (em MainOrchestrator.process_query)
```

#### `result.stdout.split` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:139 (em CursorMonitor.check_flask_process)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:163 (em CursorMonitor.run_validator)
```

#### `result.created_at` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:145 (em SessionMemory.get_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:145 (em SessionMemory.get_session)
```

#### `result.updated_at` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:146 (em SessionMemory.get_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:146 (em SessionMemory.get_session)
```

#### `result.rowcount` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:272 (em SessionMemory.cleanup_old_sessions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:358 (em SessionMemory.update_session_metadata)
```

#### `result.stdout.strip().split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:83 (em DependencyChecker.check_pip_package)
```

#### `result.replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:164 (em QueryMapper._apply_template)
```

#### `result.fetchall` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:113 (em DatabaseLoader.load_data)
```

#### `result.fetchone` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:311 (em PatternLearner._salvar_padrao_otimizado)
```

#### `result.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:112 (em IntelligenceCoordinator.coordinate_intelligence_operation)
```

#### `result.get().get().get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:858 (em IntelligenceCoordinator._combine_all_insights)
```

#### `result.wasSuccessful` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:262 (em module.run_pre_commit_tests)
```

#### `result.errors` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:268 (em module.run_pre_commit_tests)
```

#### `result.failures` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:269 (em module.run_pre_commit_tests)
```

#### `result.scalar` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:172 (em KnowledgeMemory.descobrir_grupo_empresarial)
```

#### `result.session_id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:144 (em SessionMemory.get_session)
```

#### `result.created_at.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:145 (em SessionMemory.get_session)
```

#### `result.updated_at.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:146 (em SessionMemory.get_session)
```

#### `result.user_id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:147 (em SessionMemory.get_session)
```

#### `result.metadata_jsonb` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:148 (em SessionMemory.get_session)
```

#### `result.total_sessions` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:312 (em SessionMemory.get_session_stats)
```

#### `result.unique_users` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:313 (em SessionMemory.get_session_stats)
```

#### `result.avg_confidence` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:314 (em SessionMemory.get_session_stats)
```

#### `result.fretes_sessions` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:316 (em SessionMemory.get_session_stats)
```

#### `result.entregas_sessions` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:317 (em SessionMemory.get_session_stats)
```

#### `result.pedidos_sessions` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/session_memory.py:318 (em SessionMemory.get_session_stats)
```

### 🔍 Objeto: `resultado`

#### `resultado.get` (10 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:275 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:278 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:283 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/response_utils.py:33 (em ResponseUtils._formatar_resultado_cursor)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/response_utils.py:36 (em ResponseUtils._formatar_resultado_cursor)
  ... e mais 5 ocorrências
```

#### `resultado.update` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:147 (em SemanticValidator.validar_contexto_negocio)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:253 (em SmartBaseAgent.top-level)
```

#### `resultado.entidades_nomeadas` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:163 (em NLPEnhancedAnalyzer.analyze_text)
```

#### `resultado.palavras_chave` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:164 (em NLPEnhancedAnalyzer.analyze_text)
```

#### `resultado.sentimento` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:165 (em NLPEnhancedAnalyzer.analyze_text)
```

#### `resultado.tokens_limpos` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:167 (em NLPEnhancedAnalyzer.analyze_text)
```

#### `resultado.correcoes_sugeridas` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:168 (em NLPEnhancedAnalyzer.analyze_text)
```

#### `resultado.similaridades` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:169 (em NLPEnhancedAnalyzer.analyze_text)
```

#### `resultado.tempo_verbal` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:170 (em NLPEnhancedAnalyzer.analyze_text)
```

#### `resultado.split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:312 (em DevCommands._processar_com_claude)
```

### 🔍 Objeto: `resultado_batch`

#### `resultado_batch.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:446 (em SemanticEnricher._calcular_estatisticas_batch)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:469 (em SemanticEnricher._calcular_estatisticas_batch)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:470 (em SemanticEnricher._calcular_estatisticas_batch)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:486 (em SemanticEnricher._gerar_sugestoes_batch)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:489 (em SemanticEnricher._gerar_sugestoes_batch)
```

### 🔍 Objeto: `resultado_etapa`

#### `resultado_etapa.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:203 (em WorkflowOrchestrator._executar_etapas_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:204 (em WorkflowOrchestrator._executar_etapas_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:206 (em WorkflowOrchestrator._executar_etapas_workflow)
```

### 🔍 Objeto: `resultado_grupo`

#### `resultado_grupo.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:590 (em ContextLoader._carregar_todos_clientes_sistema)
```

### 🔍 Objeto: `resultado_validacao`

#### `resultado_validacao.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:451 (em SemanticValidator._gerar_recomendacoes_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:452 (em SemanticValidator._gerar_recomendacoes_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:460 (em SemanticValidator._gerar_recomendacoes_mapeamento)
```

### 🔍 Objeto: `resultados`

#### `resultados.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:80 (em BaseMapper.buscar_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:120 (em BaseMapper.buscar_mapeamento_fuzzy)
```

#### `resultados.sort` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:123 (em BaseMapper.buscar_mapeamento_fuzzy)
```

### 🔍 Objeto: `resultados_categoria`

#### `resultados_categoria.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:192 (em module.main)
```

### 🔍 Objeto: `resultados_detalhados`

#### `resultados_detalhados.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:227 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:238 (em module.main)
```

### 🔍 Objeto: `resultados_fuzzy`

#### `resultados_fuzzy.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:132 (em MapperManager._buscar_fuzzy_integrado)
```

### 🔍 Objeto: `results`

#### `results.get` (15 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:355 (em AnalyzerManager._calculate_combined_confidence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:382 (em AnalyzerManager._generate_combined_insights)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:383 (em AnalyzerManager._generate_combined_insights)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:395 (em AnalyzerManager._generate_combined_insights)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:398 (em AnalyzerManager._generate_combined_insights)
  ... e mais 10 ocorrências
```

#### `results.append` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:41 (em ProcessorCoordinator.execute_processor_chain)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:177 (em ProcessorCoordinator.execute_parallel_processors)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:179 (em ProcessorCoordinator.execute_parallel_processors)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:443 (em IntelligenceCoordinator._execute_parallel_intelligence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:467 (em IntelligenceCoordinator._execute_sequential_intelligence)
  ... e mais 4 ocorrências
```

#### `results.get().get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:749 (em IntelligenceCoordinator._validate_intelligence_quality)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:752 (em IntelligenceCoordinator._validate_intelligence_quality)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:240 (em CursorMonitor.display_status)
```

#### `results.values` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:220 (em ProcessorManager.reload_processors)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:137 (em StandaloneIntegration.initialize_system)
```

#### `results.get().items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:218 (em CursorMonitor.display_status)
```

#### `results.get().get().get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:240 (em CursorMonitor.display_status)
```

### 🔍 Objeto: `resumo`

#### `resumo.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:84 (em SmartBaseAgent.process_query)
```

#### `resumo.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:86 (em SmartBaseAgent.process_query)
```

### 🔍 Objeto: `root_path`

#### `root_path.parts` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:43 (em module.contar_arquivos_detalhado)
```

#### `root_path.parent` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:51 (em module.contar_arquivos_detalhado)
```

#### `root_path.name` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:52 (em module.contar_arquivos_detalhado)
```

#### `root_path.relative_to().parts` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:55 (em module.contar_arquivos_detalhado)
```

#### `root_path.relative_to` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:55 (em module.contar_arquivos_detalhado)
```

### 🔍 Objeto: `route`

#### `route.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:359 (em CodeScanner._analyze_route_methods)
```

### 🔍 Objeto: `route_info`

#### `route_info.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:182 (em ProjectScanner._generate_scan_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:245 (em ProjectScanner._calculate_quality_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:288 (em ProjectScanner._generate_recommendations)
```

#### `route_info.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:306 (em CodeScanner._extract_routes_from_lines)
```

### 🔍 Objeto: `routes`

#### `routes.get_blueprint` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:655 (em module.create_integration_routes)
```

#### `routes.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:77 (em CodeScanner.discover_all_routes)
```

#### `routes.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:308 (em CodeScanner._extract_routes_from_lines)
```

### 🔍 Objeto: `routes_file`

#### `routes_file.exists` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:76 (em CodeScanner.discover_all_routes)
```

### 🔍 Objeto: `row`

#### `row.created_at` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:169 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:170 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:171 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.confidence` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:133 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:134 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.domain` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:139 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:140 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.complexity` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:143 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:144 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.processing_time` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:148 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:149 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.model_used` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:154 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:155 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.tokens_used` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:159 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:160 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.success` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:165 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:165 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.session_count` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:287 (em PerformanceAnalyzer.analyze_user_behavior)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:292 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.active_days` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:287 (em PerformanceAnalyzer.analyze_user_behavior)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:297 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.avg_confidence` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:293 (em PerformanceAnalyzer.analyze_user_behavior)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:373 (em PerformanceAnalyzer.detect_anomalies)
```

#### `row.first_session` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:295 (em PerformanceAnalyzer.analyze_user_behavior)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:295 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.last_session` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:296 (em PerformanceAnalyzer.analyze_user_behavior)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:296 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.created_at.hour` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:170 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.created_at.date().isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:171 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.created_at.date` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:171 (em PerformanceAnalyzer.analyze_ai_performance)
```

#### `row.user_id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:291 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.domains_used` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:294 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.first_session.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:295 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.last_session.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:296 (em PerformanceAnalyzer.analyze_user_behavior)
```

#### `row.date.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:371 (em PerformanceAnalyzer.detect_anomalies)
```

#### `row.date` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:371 (em PerformanceAnalyzer.detect_anomalies)
```

#### `row.daily_sessions` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:372 (em PerformanceAnalyzer.detect_anomalies)
```

#### `row.avg_processing_time` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:374 (em PerformanceAnalyzer.detect_anomalies)
```

#### `row.failures` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:375 (em PerformanceAnalyzer.detect_anomalies)
```

### 🔍 Objeto: `rule_config`

#### `rule_config.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:336 (em BaseValidationUtils._validate_single_rule)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:337 (em BaseValidationUtils._validate_single_rule)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:346 (em BaseValidationUtils._validate_single_rule)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:357 (em BaseValidationUtils._validate_single_rule)
```

### 🔍 Objeto: `rule_result`

#### `rule_result.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:312 (em BaseValidationUtils.validate_business_rules)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:315 (em BaseValidationUtils.validate_business_rules)
```

### 🔍 Objeto: `rules`

#### `rules.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:305 (em BaseValidationUtils.validate_business_rules)
```

### 🔍 Objeto: `runner`

#### `runner.run` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:258 (em module.run_pre_commit_tests)
```

### 🔍 Objeto: `s`

#### `s.user_profiles` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:239 (em SuggestionsEngine._generate_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:239 (em SuggestionsEngine._generate_suggestions)
```

#### `s.to_dict` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:273 (em SuggestionsEngine._generate_suggestions)
```

#### `s.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:137 (em SuggestionsManager.generate_suggestions)
```

### 🔍 Objeto: `sa`

#### `sa.text` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:71 (em DatabaseLoader._initialize_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:112 (em DatabaseLoader.load_data)
```

### 🔍 Objeto: `safe`

#### `safe.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/filtrar_imports_reais.py:115 (em ImportFilterer.is_false_positive)
```

### 🔍 Objeto: `sanitized`

#### `sanitized.strip` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:274 (em BaseProcessor._sanitize_input)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/security/security_guard.py:295 (em SecurityGuard.sanitize_input)
```

### 🔍 Objeto: `saude`

#### `saude.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:366 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
```

### 🔍 Objeto: `scanner`

#### `scanner.esta_disponivel` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:308 (em MapperManager.apply_auto_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:71 (em ScannersCache.get_readme_scanner)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:97 (em ScannersCache.get_database_scanner)
```

#### `scanner.get_database_info` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:113 (em LoaderManager.configure_with_scanner)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1388 (em MainOrchestrator._connect_modules)
```

#### `scanner.scan_database_structure` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:309 (em MapperManager.apply_auto_suggestions)
```

#### `scanner.scan_complete_database` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/__init__.py:161 (em module.scan_database)
```

### 🔍 Objeto: `scanner_status`

#### `scanner_status.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:295 (em ScanningManager.executar_diagnostico_completo)
```

### 🔍 Objeto: `scanning_info`

#### `scanning_info.get().items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:325 (em MapperManager.apply_auto_suggestions)
```

#### `scanning_info.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:325 (em MapperManager.apply_auto_suggestions)
```

### 🔍 Objeto: `schema_mapping`

#### `schema_mapping.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:232 (em DataProcessor.transform_schema)
```

#### `schema_mapping.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:233 (em DataProcessor.transform_schema)
```

#### `schema_mapping.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:556 (em DataProcessor._transform_dict_schema)
```

### 🔍 Objeto: `scores`

#### `scores.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:270 (em ContextProcessor._detectar_dominio)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:413 (em OrchestratorManager._detect_appropriate_orchestrator)
```

#### `scores.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:267 (em ContextProcessor._detectar_dominio)
```

#### `scores.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:195 (em ExcelOrchestrator._detectar_tipo_excel)
```

### 🔍 Objeto: `scores_positivos`

#### `scores_positivos.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:132 (em IntentionAnalyzer._detectar_intencoes_multiplas)
```

### 🔍 Objeto: `section_data`

#### `section_data.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:648 (em SystemConfig._validate_profile_config)
```

### 🔍 Objeto: `seen`

#### `seen.add` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:178 (em CircularDependencyMapper.analyze_circular_dependencies)
```

### 🔍 Objeto: `self`

#### `self.logger.error` (213 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:71 (em ConversationManager.set_memorizer)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:123 (em ConversationManager.start_conversation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:170 (em ConversationManager.add_user_message)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:217 (em ConversationManager.add_assistant_message)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:236 (em ConversationManager.get_conversation_context)
  ... e mais 208 ocorrências
```

#### `self.logger.info` (150 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:45 (em ConversationManager.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:58 (em ConversationManager.set_memorizer)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:62 (em ConversationManager.set_memorizer)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:119 (em ConversationManager.start_conversation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:166 (em ConversationManager.add_user_message)
  ... e mais 145 ocorrências
```

#### `self.logger.warning` (107 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:66 (em ConversationManager.set_memorizer)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:141 (em ConversationManager.add_user_message)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:188 (em ConversationManager.add_assistant_message)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:129 (em AnalyzerManager._initialize_components)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:137 (em AnalyzerManager._initialize_components)
  ... e mais 102 ocorrências
```

#### `self.db.session` (92 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:66 (em PerformanceAnalyzer._ensure_table_exists)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:109 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:273 (em PerformanceAnalyzer.analyze_user_behavior)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:358 (em PerformanceAnalyzer.detect_anomalies)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:240 (em ContextLoader._carregar_entregas_banco)
  ... e mais 87 ocorrências
```

#### `self.logger.debug` (55 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:127 (em AnalyzerManager._initialize_components)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:135 (em AnalyzerManager._initialize_components)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:143 (em AnalyzerManager._initialize_components)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:151 (em AnalyzerManager._initialize_components)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:159 (em AnalyzerManager._initialize_components)
  ... e mais 50 ocorrências
```

#### `self.db.session.execute` (43 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:66 (em PerformanceAnalyzer._ensure_table_exists)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:109 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:273 (em PerformanceAnalyzer.analyze_user_behavior)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:358 (em PerformanceAnalyzer.detect_anomalies)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:289 (em LearningCore._atualizar_metricas)
  ... e mais 38 ocorrências
```

#### `self.components.get` (42 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:215 (em AnalyzerManager.analyze_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:226 (em AnalyzerManager.analyze_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:237 (em AnalyzerManager.analyze_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:250 (em AnalyzerManager.analyze_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:261 (em AnalyzerManager.analyze_query)
  ... e mais 37 ocorrências
```

#### `self.agent_type.value` (30 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:48 (em SmartBaseAgent.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:50 (em SmartBaseAgent.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:72 (em SmartBaseAgent.process_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:75 (em SmartBaseAgent.process_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:79 (em SmartBaseAgent.process_query)
  ... e mais 25 ocorrências
```

#### `self.db.session.query` (21 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:240 (em ContextLoader._carregar_entregas_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:531 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:540 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:548 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:601 (em ContextLoader._carregar_todos_clientes_sistema)
  ... e mais 16 ocorrências
```

#### `self.db.engine` (15 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:237 (em ExternalAPIIntegration._get_integration_manager)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:54 (em DatabaseScanner.discover_database_schema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:58 (em DatabaseScanner.discover_database_schema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:59 (em DatabaseScanner.discover_database_schema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:107 (em DatabaseScanner._get_database_version)
  ... e mais 10 ocorrências
```

#### `self.db.session.execute().fetchall` (12 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:109 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:273 (em PerformanceAnalyzer.analyze_user_behavior)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:358 (em PerformanceAnalyzer.detect_anomalies)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:342 (em PatternLearner.buscar_padroes_aplicaveis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:156 (em DatabaseScanner._get_postgresql_statistics)
  ... e mais 7 ocorrências
```

#### `self.registry.get_processor` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:39 (em ProcessorManager.process_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:58 (em ProcessorManager.process_response)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:75 (em ProcessorManager.process_semantic_loop)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:94 (em ProcessorManager.process_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:258 (em ProcessorManager.set_memory_manager)
  ... e mais 6 ocorrências
```

#### `self.db_engine.connect` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:307 (em DatabaseConnection.test_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:126 (em DataAnalyzer._get_field_type)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:176 (em DataAnalyzer._analisar_estatisticas_basicas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:207 (em DataAnalyzer._analisar_estatisticas_basicas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:266 (em DataAnalyzer._obter_exemplos_valores)
  ... e mais 6 ocorrências
```

#### `self.db.session.execute().fetchone` (10 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:66 (em PerformanceAnalyzer._ensure_table_exists)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:274 (em PatternLearner._salvar_padrao_otimizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:110 (em DatabaseScanner._get_database_version)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:113 (em DatabaseScanner._get_database_version)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:116 (em DatabaseScanner._get_database_version)
  ... e mais 5 ocorrências
```

#### `self.__class__.__name__` (10 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_context_manager.py:93 (em BaseContextManager.__repr__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:169 (em BaseOrchestrator.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:173 (em BaseOrchestrator.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:187 (em BaseOrchestrator.get_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:212 (em BaseProcessor.__init__)
  ... e mais 5 ocorrências
```

#### `self.db.session.rollback` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:307 (em LearningCore._atualizar_metricas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:347 (em LearningCore._salvar_historico_aprendizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:322 (em PatternLearner._salvar_padrao_otimizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:117 (em KnowledgeMemory.aprender_mapeamento_cliente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:191 (em KnowledgeMemory.descobrir_grupo_empresarial)
  ... e mais 4 ocorrências
```

#### `self.db.session.execute().scalar` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:310 (em KnowledgeMemory.obter_estatisticas_aprendizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:315 (em KnowledgeMemory.obter_estatisticas_aprendizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:320 (em KnowledgeMemory.obter_estatisticas_aprendizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:325 (em KnowledgeMemory.obter_estatisticas_aprendizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:330 (em KnowledgeMemory.obter_estatisticas_aprendizado)
  ... e mais 4 ocorrências
```

#### `self.db.session.commit` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:301 (em LearningCore._atualizar_metricas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:341 (em LearningCore._salvar_historico_aprendizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:315 (em PatternLearner._salvar_padrao_otimizado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:104 (em KnowledgeMemory.aprender_mapeamento_cliente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:173 (em KnowledgeMemory.descobrir_grupo_empresarial)
  ... e mais 3 ocorrências
```

#### `self.metadata_scanner.obter_campos_tabela` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:103 (em DatabaseManager.obter_campos_tabela)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:85 (em FieldSearcher.buscar_campos_por_tipo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:163 (em FieldSearcher.buscar_campos_por_nome)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:302 (em FieldSearcher.buscar_campos_por_caracteristica)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:347 (em FieldSearcher.buscar_campos_por_tamanho)
  ... e mais 3 ocorrências
```

#### `self.security_guard.validate_user_access` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:581 (em MainOrchestrator._validate_workflow_security)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:597 (em MainOrchestrator._validate_workflow_security)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:603 (em MainOrchestrator._validate_workflow_security)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:316 (em OrchestratorManager._validate_operation_security)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:332 (em OrchestratorManager._validate_operation_security)
  ... e mais 3 ocorrências
```

#### `self.inspector.get_table_names` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:114 (em RelationshipMapper._buscar_relacionamentos_entrada)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:189 (em RelationshipMapper.mapear_grafo_relacionamentos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:79 (em FieldSearcher.buscar_campos_por_tipo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:159 (em FieldSearcher.buscar_campos_por_nome)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:299 (em FieldSearcher.buscar_campos_por_caracteristica)
  ... e mais 3 ocorrências
```

#### `self.integration_manager.process_unified_query` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:47 (em TestLoopPrevention.test_direct_loop_detection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:68 (em TestLoopPrevention.test_direct_loop_detection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:98 (em TestLoopPrevention.run_with_timeout)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:169 (em TestLoopPrevention.test_real_production_scenario)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:195 (em TestLoopPrevention.make_request)
  ... e mais 2 ocorrências
```

#### `self.validators.get` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:97 (em ValidatorManager.validate_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:127 (em ValidatorManager.validate_data_structure)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:159 (em ValidatorManager.validate_critical_rules)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:191 (em ValidatorManager.validate_agent_responses)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:252 (em ValidatorManager.validate_structural_integrity)
  ... e mais 2 ocorrências
```

#### `self.components.items` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:629 (em AnalyzerManager.get_best_analyzer)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:657 (em AnalyzerManager.health_check)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/utils_manager.py:238 (em UtilsManager.health_check)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/data_manager.py:354 (em DataManager.get_best_loader)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/data_manager.py:383 (em DataManager.health_check)
  ... e mais 1 ocorrências
```

#### `self.EntregaMonitorada.cliente.ilike` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:248 (em ContextLoader._carregar_entregas_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:176 (em ValidationUtils._calcular_estatisticas_especificas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:182 (em ValidationUtils._calcular_estatisticas_especificas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:183 (em ValidationUtils._calcular_estatisticas_especificas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:184 (em ValidationUtils._calcular_estatisticas_especificas)
  ... e mais 1 ocorrências
```

#### `self.EntregaMonitorada.cliente` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:248 (em ContextLoader._carregar_entregas_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:176 (em ValidationUtils._calcular_estatisticas_especificas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:182 (em ValidationUtils._calcular_estatisticas_especificas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:183 (em ValidationUtils._calcular_estatisticas_especificas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:184 (em ValidationUtils._calcular_estatisticas_especificas)
  ... e mais 1 ocorrências
```

#### `self.project_scanner.file_scanner` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:111 (em ScanningManager.read_file_content)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:115 (em ScanningManager.list_directory_contents)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:120 (em ScanningManager.search_in_files)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:232 (em ScanningManager.discover_all_templates)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:254 (em ScanningManager.get_modulos_especializados)
  ... e mais 1 ocorrências
```

#### `self.connection.get_inspector` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:61 (em DatabaseManager.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:63 (em DatabaseManager.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:65 (em DatabaseManager.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:76 (em DatabaseManager.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:351 (em DatabaseManager.recarregar_conexao)
  ... e mais 1 ocorrências
```

#### `self.model.query` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:316 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:159 (em AgendamentosLoader._build_agendamentos_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:152 (em FaturamentoLoader._build_faturamento_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:161 (em FretesLoader._build_fretes_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:146 (em PedidosLoader._build_pedidos_query)
  ... e mais 1 ocorrências
```

#### `self.model.data_criacao` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:167 (em AgendamentosLoader._build_agendamentos_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:195 (em FretesLoader._build_fretes_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:151 (em PedidosLoader._build_pedidos_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:168 (em PedidosLoader._build_pedidos_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:168 (em EmbarquesLoader._build_embarques_query)
  ... e mais 1 ocorrências
```

#### `self.redis_cache.disponivel` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:78 (em ConversationContext.add_message)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:112 (em ConversationContext.get_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:248 (em ConversationContext.clear_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:302 (em ConversationContext.get_context_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:223 (em SuggestionsEngine._is_redis_available)
```

#### `self.context_memory.store_context` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:105 (em ConversationManager.start_conversation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:282 (em ConversationManager.end_conversation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:51 (em ConversationMemory.start_conversation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:72 (em ConversationMemory.end_conversation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:53 (em MemoryManager.store_conversation_context)
```

#### `self.context_memory.add_message` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:155 (em ConversationManager.add_user_message)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:202 (em ConversationManager.add_assistant_message)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:99 (em ConversationMemory.add_user_message)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:125 (em ConversationMemory.add_assistant_message)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:152 (em MemoryManager.add_conversation_message)
```

#### `self.context_memory.retrieve_context` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:232 (em ConversationManager.get_conversation_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:277 (em ConversationManager.end_conversation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:68 (em ConversationMemory.end_conversation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/conversation_memory.py:142 (em ConversationMemory.get_conversation_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:69 (em MemoryManager.retrieve_conversation_context)
```

#### `self.components.keys` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:645 (em AnalyzerManager.get_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/utils_manager.py:226 (em UtilsManager.get_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/data_manager.py:370 (em DataManager.get_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:190 (em BaseOrchestrator.get_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tools/tools_manager.py:155 (em ToolsManager.get_status)
```

#### `self.db.session.query().filter` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:531 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:540 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:548 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:601 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:161 (em ValidationUtils._calcular_estatisticas_especificas)
```

#### `self.user_profiles.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:118 (em AdaptiveLearning.get_personalized_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:165 (em AdaptiveLearning.adapt_response)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:222 (em AdaptiveLearning.update_learning_from_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:255 (em AdaptiveLearning.get_user_profile)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:426 (em AdaptiveLearning._calculate_learning_confidence)
```

#### `self.ai_components.items` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:426 (em IntelligenceCoordinator._execute_parallel_intelligence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:455 (em IntelligenceCoordinator._execute_sequential_intelligence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:477 (em IntelligenceCoordinator._execute_hybrid_intelligence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:482 (em IntelligenceCoordinator._execute_hybrid_intelligence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:607 (em IntelligenceCoordinator._select_best_component)
```

#### `self.db.engine.dialect.name` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:58 (em DatabaseScanner.discover_database_schema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:107 (em DatabaseScanner._get_database_version)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:137 (em DatabaseScanner._get_table_statistics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:335 (em DatabaseScanner._get_performance_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:408 (em DatabaseScanner.obter_estatisticas_gerais)
```

#### `self.db.engine.dialect` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:58 (em DatabaseScanner.discover_database_schema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:107 (em DatabaseScanner._get_database_version)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:137 (em DatabaseScanner._get_table_statistics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:335 (em DatabaseScanner._get_performance_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:408 (em DatabaseScanner.obter_estatisticas_gerais)
```

#### `self.project_scanner.structure_scanner` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:216 (em ScanningManager.discover_project_structure)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:220 (em ScanningManager.discover_all_models)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:252 (em ScanningManager.get_modulos_especializados)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:332 (em ScanningManager._discover_project_structure)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:336 (em ScanningManager._discover_all_models)
```

#### `self.project_scanner.code_scanner` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:224 (em ScanningManager.discover_all_forms)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:228 (em ScanningManager.discover_all_routes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:253 (em ScanningManager.get_modulos_especializados)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:340 (em ScanningManager._discover_all_forms)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:344 (em ScanningManager._discover_all_routes)
```

#### `self.system_config.get_config` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/advanced_config.py:69 (em AdvancedConfig.get_temperature)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/advanced_config.py:79 (em AdvancedConfig.get_claude_params)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/advanced_config.py:80 (em AdvancedConfig.get_claude_params)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/advanced_config.py:82 (em AdvancedConfig.get_claude_params)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/advanced_config.py:83 (em AdvancedConfig.get_claude_params)
```

#### `self.model.nome_cliente.ilike` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:338 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:358 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:162 (em FaturamentoLoader._build_faturamento_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:170 (em FaturamentoLoader._build_faturamento_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:180 (em FretesLoader._build_fretes_query)
```

#### `self.model.nome_cliente` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:338 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:358 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:162 (em FaturamentoLoader._build_faturamento_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:170 (em FaturamentoLoader._build_faturamento_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:180 (em FretesLoader._build_fretes_query)
```

#### `self.db.session.is_active` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:47 (em AgendamentosLoader.load_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:47 (em FaturamentoLoader.load_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:51 (em FretesLoader.load_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:47 (em PedidosLoader.load_data)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:49 (em EmbarquesLoader.load_data)
```

#### `self.db.session.query().join` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:88 (em AgendamentosLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:95 (em FretesLoader._load_with_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:124 (em ExcelFretes._buscar_dados_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:132 (em ExcelPedidos._buscar_dados_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:122 (em ExcelEntregas._buscar_dados_entregas)
```

#### `self.logger_estruturado.error` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/pedidos_agent.py:63 (em PedidosAgent._resumir_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/entregas_agent.py:126 (em EntregasAgent._resumir_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/fretes_agent.py:63 (em FretesAgent._resumir_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/embarques_agent.py:63 (em EmbarquesAgent._resumir_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/financeiro_agent.py:62 (em FinanceiroAgent._resumir_dados_reais)
```

#### `self.defined_vars.add` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:45 (em VariableTracker.visit_FunctionDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:50 (em VariableTracker.visit_ClassDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:63 (em VariableTracker.visit_Assign)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:74 (em VariableTracker.visit_Name)
```

#### `self.try_imports.append` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:46 (em DependencyAnalyzer.visit_Import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:64 (em DependencyAnalyzer.visit_ImportFrom)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:120 (em DeepImportAnalyzer.visit_Import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:146 (em DeepImportAnalyzer.visit_ImportFrom)
```

#### `self.orchestrator.mappers` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:61 (em DiagnosticsAnalyzer.gerar_estatisticas_completas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:71 (em DiagnosticsAnalyzer.gerar_estatisticas_completas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:117 (em DiagnosticsAnalyzer.diagnosticar_qualidade)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:318 (em SemanticValidator._validar_campos_modelo_tabela)
```

#### `self.scanning_manager.get_readme_scanner` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:220 (em DiagnosticsAnalyzer.gerar_relatorio_enriquecido)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:300 (em DiagnosticsAnalyzer._verificar_saude_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:86 (em SemanticEnricher.enriquecer_mapeamento_com_scanners)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:228 (em SemanticValidator.validar_consistencia_readme_banco)
```

#### `self.scanning_manager.get_database_scanner` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:221 (em DiagnosticsAnalyzer.gerar_relatorio_enriquecido)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:301 (em DiagnosticsAnalyzer._verificar_saude_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:87 (em SemanticEnricher.enriquecer_mapeamento_com_scanners)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:229 (em SemanticValidator.validar_consistencia_readme_banco)
```

#### `self.client.messages.create` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:258 (em ResponseProcessor._gerar_resposta_inicial)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:443 (em ResponseProcessor._melhorar_resposta)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:297 (em DevCommands._processar_com_claude)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:123 (em ClaudeAPIClient.send_message)
```

#### `self.client.messages` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:258 (em ResponseProcessor._gerar_resposta_inicial)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:443 (em ResponseProcessor._melhorar_resposta)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/dev_commands.py:297 (em DevCommands._processar_com_claude)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:123 (em ClaudeAPIClient.send_message)
```

#### `self.EntregaMonitorada.data_embarque` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:243 (em ContextLoader._carregar_entregas_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:251 (em ContextLoader._carregar_entregas_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:163 (em ValidationUtils._calcular_estatisticas_especificas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:164 (em ValidationUtils._calcular_estatisticas_especificas)
```

#### `self.db.session.query().filter().distinct` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:531 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:540 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:548 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:601 (em ContextLoader._carregar_todos_clientes_sistema)
```

#### `self.mock_models.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:197 (em FlaskFallback.get_model)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:202 (em FlaskFallback.get_model)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:207 (em FlaskFallback.get_model)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:209 (em FlaskFallback.get_model)
```

#### `self.esqueletos.keys` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:370 (em ExcelOrchestrator._fallback_tipo_indisponivel)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:379 (em ExcelOrchestrator._fallback_tipo_indisponivel)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:387 (em ExcelOrchestrator._fallback_tipo_indisponivel)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:412 (em ExcelOrchestrator.get_status_esqueletos)
```

#### `self.status.total_requests` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:267 (em CursorMonitor.display_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:269 (em CursorMonitor.display_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:269 (em CursorMonitor.display_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:315 (em CursorMonitor.top-level)
```

#### `self.db.engine.pool` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:339 (em DatabaseScanner._get_performance_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:340 (em DatabaseScanner._get_performance_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:341 (em DatabaseScanner._get_performance_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:342 (em DatabaseScanner._get_performance_info)
```

#### `self.connection.get_engine` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:62 (em DatabaseManager.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:74 (em DatabaseManager.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:352 (em DatabaseManager.recarregar_conexao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:366 (em DatabaseManager.recarregar_conexao)
```

#### `self.connection.is_connected` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:197 (em DatabaseManager.esta_disponivel)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:208 (em DatabaseManager.obter_estatisticas_gerais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:374 (em DatabaseManager.recarregar_conexao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:426 (em DatabaseManager.obter_info_modulos)
```

#### `self.security_guard.validate_input` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:586 (em MainOrchestrator._validate_workflow_security)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:609 (em MainOrchestrator._validate_workflow_security)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:321 (em OrchestratorManager._validate_operation_security)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:815 (em SessionOrchestrator._validate_session_security)
```

#### `self.session_memory.update_session_metadata` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:302 (em SessionOrchestrator.initialize_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:374 (em SessionOrchestrator.execute_session_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:546 (em SessionOrchestrator.complete_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:590 (em SessionOrchestrator.terminate_session)
```

#### `self.model.data_embarque` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:323 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:370 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:165 (em EmbarquesLoader._build_embarques_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:167 (em EmbarquesLoader._build_embarques_query)
```

#### `self.model.status` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:183 (em AgendamentosLoader._build_agendamentos_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:185 (em FretesLoader._build_fretes_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:184 (em EmbarquesLoader._build_embarques_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:187 (em EmbarquesLoader._build_embarques_query)
```

#### `self.defined_methods.add` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:51 (em MethodCallVisitor.visit_ClassDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:59 (em MethodCallVisitor.visit_FunctionDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:61 (em MethodCallVisitor.visit_FunctionDef)
```

#### `self.dependencies.items` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:164 (em DependencyChecker.analyze_dependencies)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:185 (em CircularDependencyMapper.analyze_circular_dependencies)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:233 (em CircularDependencyMapper.generate_report)
```

#### `self.placeholders.append` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:69 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:80 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:88 (em DeepImportAnalyzer.visit_Try)
```

#### `self.problems.append` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:104 (em RealProblemFinder.visit_Attribute)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:115 (em RealProblemFinder.visit_Attribute)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_problemas_reais.py:135 (em RealProblemFinder.visit_Name)
```

#### `self.mappers.items` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:74 (em MapperManager.analisar_consulta_semantica)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:125 (em MapperManager._buscar_fuzzy_integrado)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:252 (em MapperManager.obter_estatisticas_mappers)
```

#### `self.orchestrator.mappers.items` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:71 (em DiagnosticsAnalyzer.gerar_estatisticas_completas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:117 (em DiagnosticsAnalyzer.diagnosticar_qualidade)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:318 (em SemanticValidator._validar_campos_modelo_tabela)
```

#### `self.registry.list_processors` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:170 (em ProcessorManager.get_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:210 (em ProcessorManager.reload_processors)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:241 (em ProcessorManager.__str__)
```

#### `self.db.session.query().filter().distinct().all` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:531 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:540 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:548 (em ContextLoader._carregar_todos_clientes_sistema)
```

#### `self.active_chains.values` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:307 (em ProcessorCoordinator.get_coordinator_stats)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:308 (em ProcessorCoordinator.get_coordinator_stats)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:309 (em ProcessorCoordinator.get_coordinator_stats)
```

#### `self.thread_pool.submit` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:205 (em IntelligenceCoordinator.coordinate_multi_ai_synthesis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:428 (em IntelligenceCoordinator._execute_parallel_intelligence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:504 (em IntelligenceCoordinator._execute_hybrid_intelligence)
```

#### `self.web_adapter.get_module` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:437 (em WebFlaskRoutes.clear_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:588 (em WebFlaskRoutes._record_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:604 (em WebFlaskRoutes._record_feedback)
```

#### `self.orchestrator_manager.process_query` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/integration_manager.py:298 (em IntegrationManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:48 (em TestLoopPrevention.test_direct_loop_detection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:133 (em TestLoopPrevention.test_circular_reference_detection)
```

#### `self.project_scanner.get_scanner_status` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:241 (em ScanningManager.get_scanner_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:267 (em ScanningManager.executar_diagnostico_completo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:268 (em ScanningManager.executar_diagnostico_completo)
```

#### `self.app_path.iterdir` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:50 (em CodeScanner.discover_all_forms)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:73 (em CodeScanner.discover_all_routes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:160 (em StructureScanner._discover_models_via_files)
```

#### `self.tabelas_cache.clear` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:331 (em DatabaseManager.limpar_cache)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:44 (em MetadataScanner.set_inspector)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:312 (em MetadataScanner.limpar_cache)
```

#### `self.discovered_routes.values` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:183 (em ProjectScanner._generate_scan_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:246 (em ProjectScanner._calculate_quality_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:289 (em ProjectScanner._generate_recommendations)
```

#### `self.local_cache.items` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:220 (em ContextMemory.get_active_sessions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/context_memory.py:243 (em ContextMemory.cleanup_expired_contexts)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:348 (em SystemMemory.cleanup_expired_data)
```

#### `self.mapeamentos.items` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:66 (em BaseMapper.buscar_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:104 (em BaseMapper.buscar_mapeamento_fuzzy)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:176 (em BaseMapper.validar_mapeamentos)
```

#### `self.mapeamentos.values` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:143 (em BaseMapper.listar_termos_naturais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:155 (em BaseMapper.gerar_estatisticas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:156 (em BaseMapper.gerar_estatisticas)
```

#### `self.model.cliente.ilike` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:340 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:360 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:156 (em PedidosLoader._build_pedidos_query)
```

#### `self.model.cliente` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:340 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:360 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:156 (em PedidosLoader._build_pedidos_query)
```

#### `self.model.data_criacao.desc` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:195 (em FretesLoader._build_fretes_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:168 (em PedidosLoader._build_pedidos_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:190 (em EmbarquesLoader._build_embarques_query)
```

#### `self.knowledge_base.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:170 (em BaseSpecialistAgent._calculate_confidence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:181 (em BaseSpecialistAgent.get_agent_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:182 (em BaseSpecialistAgent.get_agent_info)
```

#### `self.inspector.get_foreign_keys` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:70 (em RelationshipMapper.obter_relacionamentos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:121 (em RelationshipMapper._buscar_relacionamentos_entrada)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:220 (em MetadataScanner._obter_constraints_tabela)
```

#### `self.search_cache.clear` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:46 (em FieldSearcher.set_inspector)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:56 (em FieldSearcher.set_metadata_scanner)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/field_searcher.py:524 (em FieldSearcher.limpar_cache)
```

#### `self.mapping_cache.clear` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:49 (em AutoMapper.set_metadata_scanner)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:59 (em AutoMapper.set_data_analyzer)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:573 (em AutoMapper.limpar_cache)
```

#### `self.duplicates.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:112 (em ClassDuplicateFinder.analyze_duplicates)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:220 (em ClassDuplicateFinder.generate_report)
```

#### `self.root_path.absolute` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:173 (em ClassDuplicateFinder.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:199 (em UninitializedVariableFinder.generate_report)
```

#### `self.imported_names.add` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:31 (em MethodCallVisitor.visit_Import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:38 (em MethodCallVisitor.visit_ImportFrom)
```

#### `self.imports.add` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:30 (em VariableTracker.visit_Import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:37 (em VariableTracker.visit_ImportFrom)
```

#### `self.uninitialized_vars.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:218 (em UninitializedVariableFinder.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:249 (em UninitializedVariableFinder.generate_report)
```

#### `self.base_dir.parent.parent` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:18 (em DependencyChecker.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:104 (em CircularDependencyMapper.build_dependency_graph)
```

#### `self.base_dir.parent` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:18 (em DependencyChecker.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:104 (em CircularDependencyMapper.build_dependency_graph)
```

#### `self.dependencies.values` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:262 (em DependencyChecker.generate_report)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:186 (em CircularDependencyMapper.analyze_circular_dependencies)
```

#### `self.imports.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:48 (em DependencyAnalyzer.visit_Import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:66 (em DependencyAnalyzer.visit_ImportFrom)
```

#### `self.all_imports.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:115 (em DeepImportAnalyzer.visit_Import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:141 (em DeepImportAnalyzer.visit_ImportFrom)
```

#### `self.function_imports.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:118 (em DeepImportAnalyzer.visit_Import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:144 (em DeepImportAnalyzer.visit_ImportFrom)
```

#### `self.redis_cache.set` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:80 (em ConversationContext.add_message)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:202 (em SuggestionsEngine.get_intelligent_suggestions)
```

#### `self.redis_cache.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:114 (em ConversationContext.get_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:189 (em SuggestionsEngine.get_intelligent_suggestions)
```

#### `self.conversation_memory.start_conversation` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:101 (em ConversationManager.start_conversation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:186 (em MemoryManager.start_conversation)
```

#### `self.context_memory.get_conversation_history` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:252 (em ConversationManager.get_conversation_history)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:169 (em MemoryManager.get_conversation_history)
```

#### `self.conversation_memory.end_conversation` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:273 (em ConversationManager.end_conversation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:202 (em MemoryManager.end_conversation)
```

#### `self.active_conversations.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:305 (em ConversationManager.get_active_conversations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:336 (em ConversationManager.cleanup_expired_conversations)
```

#### `self.context_memory.cleanup_expired_contexts` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:348 (em ConversationManager.cleanup_expired_conversations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:279 (em MemoryManager.cleanup_expired_data)
```

#### `self.conversation_memory.get_conversation_summary` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:371 (em ConversationManager.get_conversation_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:218 (em MemoryManager.get_conversation_summary)
```

#### `self.suggestion_engines.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:114 (em SuggestionsManager.generate_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:698 (em SuggestionsManager._optimize_engines)
```

#### `self.claude_client.send_message` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/query_processor.py:51 (em QueryProcessor._process_with_claude)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:387 (em ExternalAPIIntegration.top-level)
```

#### `self._ultimo_contexto_carregado.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:119 (em ContextProcessor._build_contexto_por_intencao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:152 (em ContextProcessor._descrever_contexto_carregado)
```

#### `self.registry.get_registry_stats` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:167 (em ProcessorManager.get_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:310 (em ProcessorCoordinator.get_coordinator_stats)
```

#### `self.flask_wrapper.health_check` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:182 (em ProcessorManager.health_check)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:195 (em ProcessorManager.get_detailed_health_report)
```

#### `self.registry.health_check` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:183 (em ProcessorManager.health_check)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:196 (em ProcessorManager.get_detailed_health_report)
```

#### `self.coordinator.health_check` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:184 (em ProcessorManager.health_check)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:197 (em ProcessorManager.get_detailed_health_report)
```

#### `self.processors.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:343 (em module.set_memory)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:273 (em ProcessorRegistry.validate_all_processors)
```

#### `self._loaders.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:137 (em LoaderManager._get_loader)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:381 (em LoaderManager.get_loader_status)
```

#### `self.config.username` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:60 (em DatabaseLoader._initialize_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:206 (em DatabaseLoader.get_connection_info)
```

#### `self.config.host` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:60 (em DatabaseLoader._initialize_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:203 (em DatabaseLoader.get_connection_info)
```

#### `self.config.port` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:60 (em DatabaseLoader._initialize_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:204 (em DatabaseLoader.get_connection_info)
```

#### `self.config.database` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:60 (em DatabaseLoader._initialize_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:205 (em DatabaseLoader.get_connection_info)
```

#### `self._engine.connect` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:70 (em DatabaseLoader._initialize_connection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:111 (em DatabaseLoader.load_data)
```

#### `self.processors.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:163 (em ProcessorRegistry.get_processor)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:182 (em ProcessorRegistry.get_processor_info)
```

#### `self.processors.keys` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:177 (em ProcessorRegistry.list_processors)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:262 (em ProcessorRegistry.get_registry_stats)
```

#### `self.processors.values` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:260 (em ProcessorRegistry.get_registry_stats)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:261 (em ProcessorRegistry.get_registry_stats)
```

#### `self._scanners_pool.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:83 (em ScannersCache.get_readme_scanner)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:109 (em ScannersCache.get_database_scanner)
```

#### `self.mock_app.config.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:309 (em FlaskFallback.get_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:311 (em FlaskFallback.get_config)
```

#### `self.mock_app.config` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:309 (em FlaskFallback.get_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py:311 (em FlaskFallback.get_config)
```

#### `self.prioridades.keys` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:201 (em ExcelOrchestrator._detectar_tipo_excel)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:213 (em ExcelOrchestrator._tentar_fallback_esqueletos)
```

#### `self.output_dir.mkdir` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:63 (em BaseCommand.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:71 (em BaseCommand.__init__)
```

#### `self.status.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:141 (em CommandsRegistry.get_available_commands)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:148 (em CommandsRegistry.get_status_report)
```

#### `self.knowledge_memory.aprender_mapeamento_cliente` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:124 (em LearningCore.aprender_com_interacao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:119 (em MemoryManager.learn_client_mapping)
```

#### `self.knowledge_memory.descobrir_grupo_empresarial` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:131 (em LearningCore.aprender_com_interacao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:135 (em MemoryManager.discover_business_group)
```

#### `self.knowledge_memory.obter_estatisticas_aprendizado` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:246 (em LearningCore.obter_status_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:258 (em MemoryManager.get_system_overview)
```

#### `self.learning_core.aprender_com_interacao` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/lifelong_learning.py:65 (em LifelongLearningSystem.aprender_com_interacao)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:411 (em SessionOrchestrator._execute_learning_workflow)
```

#### `self.learning_core.aplicar_conhecimento` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/lifelong_learning.py:81 (em LifelongLearningSystem.aplicar_conhecimento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:497 (em SessionOrchestrator.apply_learned_knowledge)
```

#### `self.agent_types.keys` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:116 (em SpecialistCoordinator.get_all_agents)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/__init__.py:120 (em SpecialistCoordinator.get_available_domains)
```

#### `self.active_chains.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:280 (em ProcessorCoordinator.get_active_chains)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:289 (em ProcessorCoordinator.cleanup_completed_chains)
```

#### `self.coordination_metrics.copy` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:363 (em IntelligenceCoordinator.get_intelligence_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:893 (em IntelligenceCoordinator._analyze_current_performance)
```

#### `self.config.copy` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:364 (em IntelligenceCoordinator.get_intelligence_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/context_provider.py:380 (em ContextProvider._enrich_context)
```

#### `self.claude_client.validate_connection` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:218 (em ExternalAPIIntegration._initialize_clients)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:397 (em ExternalAPIIntegration._validate_claude_connection)
```

#### `self.integration_manager.get_system_status` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:432 (em ExternalAPIIntegration.get_system_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:141 (em SmartBaseAgent._conectar_integration_manager)
```

#### `self.config.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:45 (em StandaloneContextManager.get_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:227 (em StandaloneIntegration.get_status)
```

#### `self.web_adapter.get_system_status` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:461 (em WebFlaskRoutes.health_check)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:494 (em WebFlaskRoutes.system_status)
```

#### `self.web_adapter._run_async` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:591 (em WebFlaskRoutes._record_feedback)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:606 (em WebFlaskRoutes._record_feedback)
```

#### `self.data_provider.get_data_by_domain` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:153 (em ProviderManager._provide_data_only)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:283 (em ProviderManager._provide_mixed)
```

#### `self.context_provider.get_context` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:177 (em ProviderManager._provide_context_only)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:273 (em ProviderManager._provide_mixed)
```

#### `self.status.errors_count` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:268 (em CursorMonitor.display_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:269 (em CursorMonitor.display_status)
```

#### `self.status.last_error` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:271 (em CursorMonitor.display_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:272 (em CursorMonitor.display_status)
```

#### `self.response_times.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:95 (em ClaudeAIMetrics.record_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:95 (em ClaudeAIMetricsOptimized.record_query)
```

#### `self.metrics_buffer.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:109 (em ClaudeAIMetrics.record_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:109 (em ClaudeAIMetricsOptimized.record_query)
```

#### `self.query_types.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:194 (em ClaudeAIMetrics.get_usage_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:194 (em ClaudeAIMetricsOptimized.get_usage_metrics)
```

#### `self.last_reset.isoformat` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:210 (em ClaudeAIMetrics.get_usage_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:210 (em ClaudeAIMetricsOptimized.get_usage_metrics)
```

#### `self.model_config.copy` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:260 (em ClaudeAIMetrics.get_comprehensive_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:260 (em ClaudeAIMetricsOptimized.get_comprehensive_metrics)
```

#### `self.metrics_buffer.clear` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:291 (em ClaudeAIMetrics.reset_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:291 (em ClaudeAIMetricsOptimized.reset_metrics)
```

#### `self.query_types.clear` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:292 (em ClaudeAIMetrics.reset_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:292 (em ClaudeAIMetricsOptimized.reset_metrics)
```

#### `self.response_times.clear` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:293 (em ClaudeAIMetrics.reset_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:293 (em ClaudeAIMetricsOptimized.reset_metrics)
```

#### `self._get_cached_health_metrics.cache_clear` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:302 (em ClaudeAIMetrics.reset_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:302 (em ClaudeAIMetricsOptimized.reset_metrics)
```

#### `self._get_cached_orchestrator_metrics.cache_clear` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:303 (em ClaudeAIMetrics.reset_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:303 (em ClaudeAIMetricsOptimized.reset_metrics)
```

#### `self._get_cached_ai_technical_metrics.cache_clear` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:304 (em ClaudeAIMetrics.reset_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:304 (em ClaudeAIMetricsOptimized.reset_metrics)
```

#### `self.db.engine.driver` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:59 (em DatabaseScanner.discover_database_schema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:409 (em DatabaseScanner.obter_estatisticas_gerais)
```

#### `self.project_scanner.scan_project_light` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:212 (em ScanningManager.scan_project_light)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:269 (em ScanningManager.executar_diagnostico_completo)
```

#### `self.project_scanner.structure_scanner.discover_project_structure` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:216 (em ScanningManager.discover_project_structure)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:332 (em ScanningManager._discover_project_structure)
```

#### `self.project_scanner.structure_scanner.discover_all_models` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:220 (em ScanningManager.discover_all_models)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:336 (em ScanningManager._discover_all_models)
```

#### `self.project_scanner.code_scanner.discover_all_forms` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:224 (em ScanningManager.discover_all_forms)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:340 (em ScanningManager._discover_all_forms)
```

#### `self.project_scanner.code_scanner.discover_all_routes` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:228 (em ScanningManager.discover_all_routes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:344 (em ScanningManager._discover_all_routes)
```

#### `self.project_scanner.file_scanner.discover_all_templates` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:232 (em ScanningManager.discover_all_templates)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:348 (em ScanningManager._discover_all_templates)
```

#### `self.connection.get_session` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:75 (em DatabaseManager.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:367 (em DatabaseManager.recarregar_conexao)
```

#### `self.data_analyzer.analisar_dados_reais` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:117 (em DatabaseManager.analisar_dados_reais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:170 (em AutoMapper._mapear_campo_automatico)
```

#### `self.relationship_mapper.obter_relacionamentos` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:129 (em DatabaseManager.obter_relacionamentos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:254 (em DatabaseManager.analisar_tabela_completa)
```

#### `self.auto_mapper.gerar_mapeamento_automatico` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:188 (em DatabaseManager.gerar_mapeamento_automatico)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:258 (em DatabaseManager.analisar_tabela_completa)
```

#### `self.relationship_mapper.mapear_grafo_relacionamentos` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:219 (em DatabaseManager.obter_estatisticas_gerais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:274 (em DatabaseManager.mapear_grafo_relacionamentos)
```

#### `self.metadata_scanner.is_available` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:226 (em DatabaseManager.obter_estatisticas_gerais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:431 (em DatabaseManager.obter_info_modulos)
```

#### `self.data_analyzer.is_available` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:227 (em DatabaseManager.obter_estatisticas_gerais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:435 (em DatabaseManager.obter_info_modulos)
```

#### `self.relationship_mapper.is_available` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:228 (em DatabaseManager.obter_estatisticas_gerais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:439 (em DatabaseManager.obter_info_modulos)
```

#### `self.field_searcher.is_available` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:229 (em DatabaseManager.obter_estatisticas_gerais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:443 (em DatabaseManager.obter_info_modulos)
```

#### `self.auto_mapper.is_available` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:230 (em DatabaseManager.obter_estatisticas_gerais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:447 (em DatabaseManager.obter_info_modulos)
```

#### `self.connection.connection_method` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:427 (em DatabaseManager.obter_info_modulos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:470 (em DatabaseManager.__str__)
```

#### `self.structure_scanner.discover_project_structure` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:101 (em ProjectScanner.scan_complete_project)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:152 (em ProjectScanner.scan_project_light)
```

#### `self.structure_scanner.discover_all_models` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:104 (em ProjectScanner.scan_complete_project)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:153 (em ProjectScanner.scan_project_light)
```

#### `self.file_scanner.discover_all_templates` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:113 (em ProjectScanner.scan_complete_project)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:154 (em ProjectScanner.scan_project_light)
```

#### `self.database_schema.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:185 (em ProjectScanner._generate_scan_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:298 (em ProjectScanner._generate_recommendations)
```

#### `self.discovered_models.values` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:239 (em ProjectScanner._calculate_quality_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:256 (em ProjectScanner._calculate_quality_metrics)
```

#### `self.system_config.active_profile` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/advanced_config.py:97 (em AdvancedConfig.get_config)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/advanced_config.py:105 (em AdvancedConfig.get_config)
```

#### `self.profiles.keys` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:191 (em SystemConfig.switch_profile)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:423 (em SystemConfig.get_system_status)
```

#### `self.default_configurations.copy` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:531 (em SystemConfig._load_initial_configurations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:552 (em SystemConfig._load_profile_config)
```

#### `self.change_history.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:684 (em SystemConfig._record_config_change)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:699 (em SystemConfig._record_profile_switch)
```

#### `self.orchestrator.obter_mapper` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:207 (em SemanticEnricher._obter_mapeamento_atual)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:184 (em SemanticValidator._validacoes_gerais)
```

#### `self.coordinator_manager.coordinate_query` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:672 (em MainOrchestrator._execute_intelligent_coordination)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:719 (em MainOrchestrator._execute_natural_commands)
```

#### `self.execution_history.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:980 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:992 (em MainOrchestrator.top-level)
```

#### `self.orchestrators.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:642 (em OrchestratorManager.get_orchestrator_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:681 (em OrchestratorManager.health_check)
```

#### `self.active_sessions.pop` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:553 (em SessionOrchestrator.complete_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:597 (em SessionOrchestrator.terminate_session)
```

#### `self.active_sessions.values` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:633 (em SessionOrchestrator.get_user_sessions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:687 (em SessionOrchestrator.get_session_stats)
```

#### `self.EntregaMonitorada.status_finalizacao` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:195 (em ValidationUtils._calcular_estatisticas_especificas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:196 (em ValidationUtils._calcular_estatisticas_especificas)
```

#### `self.db.session.execute().first` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:65 (em KnowledgeMemory.aprender_mapeamento_cliente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:146 (em KnowledgeMemory.descobrir_grupo_empresarial)
```

#### `self.model.cnpj_cliente` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:347 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:171 (em FaturamentoLoader._build_faturamento_query)
```

#### `self.model.entregue` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:365 (em EntregasLoader._build_entregas_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:367 (em EntregasLoader._build_entregas_query)
```

#### `self.model.data_agendamento` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:166 (em AgendamentosLoader._build_agendamentos_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:186 (em AgendamentosLoader._build_agendamentos_query)
```

#### `self.model.data_fatura` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:157 (em FaturamentoLoader._build_faturamento_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:176 (em FaturamentoLoader._build_faturamento_query)
```

#### `self.logger_estruturado.info` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:64 (em SmartBaseAgent.process_query)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:311 (em SmartBaseAgent._log_consulta_estruturada)
```

#### `self.agent_type.value.title` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:283 (em SmartBaseAgent.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:32 (em BaseSpecialistAgent.__init__)
```

#### `self.relationships_cache.clear` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:45 (em RelationshipMapper.set_inspector)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:412 (em RelationshipMapper.limpar_cache)
```

#### `self.analysis_cache.clear` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:47 (em DataAnalyzer.set_engine)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:581 (em DataAnalyzer.limpar_cache)
```

#### `self.resultados.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:386 (em TesteIntegracaoCompleta.gerar_relatorio_final)
```

#### `self.initialization_result.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:115 (em ClaudeAINovo.top-level)
```

#### `self.classes_map.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:97 (em ClassDuplicateFinder.find_duplicates)
```

#### `self.method_calls.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:71 (em MethodCallVisitor.visit_Attribute)
```

#### `self.function_params.add` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:44 (em VariableTracker.visit_FunctionDef)
```

#### `self.class_attributes.add` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:56 (em VariableTracker.visit_ClassDef)
```

#### `self.assignments.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:64 (em VariableTracker.visit_Assign)
```

#### `self.used_vars.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:71 (em VariableTracker.visit_Name)
```

#### `self.fallback_patterns.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:89 (em DependencyAnalyzer.visit_Try)
```

#### `self.conditional_imports.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:101 (em DependencyAnalyzer.visit_Try)
```

#### `self.redis_usage.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:117 (em DependencyAnalyzer.visit_Attribute)
```

#### `self.db_usage.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:126 (em DependencyAnalyzer.visit_Attribute)
```

#### `self.model_usage.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:135 (em DependencyAnalyzer.visit_Attribute)
```

#### `self.base_dir.rglob` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:95 (em CircularDependencyMapper.build_dependency_graph)
```

#### `self.import_graph.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:134 (em CircularDependencyMapper.dfs)
```

#### `self.checked_modules.add` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:147 (em ImportChecker.check_import)
```

#### `self.mappers.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:245 (em MapperManager.obter_estatisticas_mappers)
```

#### `self.mappings.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/query_mapper.py:94 (em QueryMapper.map_query)
```

#### `self.transformers.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:58 (em FieldMapper._setup_default_transformers)
```

#### `self.validators.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:71 (em FieldMapper._setup_default_validators)
```

#### `self.redis_cache.delete` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:250 (em ConversationContext.clear_context)
```

#### `self.conversation_memory.add_user_message` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:159 (em ConversationManager.add_user_message)
```

#### `self.conversation_memory.add_assistant_message` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:206 (em ConversationManager.add_assistant_message)
```

#### `self.self_performance_history.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:44 (em MetacognitiveAnalyzer.analyze_own_performance)
```

#### `self.correcoes_comuns.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:180 (em NLPEnhancedAnalyzer._aplicar_correcoes)
```

#### `self.correcoes_comuns.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:195 (em NLPEnhancedAnalyzer._aplicar_correcoes)
```

#### `self.sinonimos.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:309 (em NLPEnhancedAnalyzer._extrair_palavras_chave)
```

#### `self._historico_performance.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/intention_analyzer.py:266 (em IntentionAnalyzer._salvar_performance)
```

#### `self.entity_patterns.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:238 (em SemanticAnalyzer._extract_entities)
```

#### `self.domain_keywords.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:249 (em SemanticAnalyzer._identify_domains)
```

#### `self.domain_keywords.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:278 (em SemanticAnalyzer._extract_keywords)
```

#### `self.components.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:181 (em AnalyzerManager._initialize_components)
```

#### `self.suggestion_engines.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:207 (em SuggestionsManager.register_suggestion_engine)
```

#### `self.suggestions_cache.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:720 (em SuggestionsManager._optimize_cache)
```

#### `self.feedback_history.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:769 (em SuggestionsManager._cleanup_old_data)
```

#### `self.context_manager.enrich_query` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/query_processor.py:24 (em QueryProcessor.process_query)
```

#### `self.learning_system.get_relevant_knowledge` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/query_processor.py:27 (em QueryProcessor.process_query)
```

#### `self.learning_system.record_interaction` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/query_processor.py:33 (em QueryProcessor.process_query)
```

#### `self.coordinator.execute_processor_chain` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:152 (em ProcessorManager.execute_processing_chain)
```

#### `self.flask_wrapper.get_status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:166 (em ProcessorManager.get_status)
```

#### `self.coordinator.get_coordinator_stats` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:168 (em ProcessorManager.get_status)
```

#### `self.registry.validate_all_processors` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:199 (em ProcessorManager.get_detailed_health_report)
```

#### `self.flask_wrapper.get_flask_context_info` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:200 (em ProcessorManager.get_detailed_health_report)
```

#### `self.coordinator.get_active_chains` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:201 (em ProcessorManager.get_detailed_health_report)
```

#### `self.registry.reload_processor` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:212 (em ProcessorManager.reload_processors)
```

#### `self.coordinator.cleanup_completed_chains` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:231 (em ProcessorManager.cleanup_resources)
```

#### `self.EntregaMonitorada.data_embarque.desc` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:251 (em ContextLoader._carregar_entregas_banco)
```

#### `self.db.session.query().filter().distinct().count` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:601 (em ContextLoader._carregar_todos_clientes_sistema)
```

#### `self.scanner.get_database_info` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:73 (em LoaderManager.__init__)
```

#### `self._loader_mapping.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:341 (em LoaderManager.get_available_domains)
```

#### `self._loader_mapping.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:357 (em LoaderManager.get_loader)
```

#### `self._loader_mapping.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:380 (em LoaderManager.get_loader_status)
```

#### `self.config.password` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:60 (em DatabaseLoader._initialize_connection)
```

#### `self._session.close` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:213 (em DatabaseLoader.close)
```

#### `self._engine.dispose` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/database_loader.py:217 (em DatabaseLoader.close)
```

#### `self.processor_types.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:173 (em ProcessorRegistry.get_processor_type)
```

#### `self.flask_wrapper.is_flask_available` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/processor_registry.py:263 (em ProcessorRegistry.get_registry_stats)
```

#### `self._cache_timestamps.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:126 (em ScannersCache.get_cached_result)
```

#### `self._results_cache.pop` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:156 (em ScannersCache._remove_from_cache)
```

#### `self._cache_timestamps.pop` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:157 (em ScannersCache._remove_from_cache)
```

#### `self._cache_timestamps.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:164 (em ScannersCache._cleanup_expired_cache)
```

#### `self._results_cache.clear` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:196 (em ScannersCache.clear_cache)
```

#### `self._cache_timestamps.clear` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:197 (em ScannersCache.clear_cache)
```

#### `self._config.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_context_manager.py:39 (em BaseContextManager._get_config)
```

#### `self._config.copy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_context_manager.py:67 (em BaseContextManager.get_config_dict)
```

#### `self._config.clear` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_context_manager.py:80 (em BaseContextManager.clear_config)
```

#### `self._config.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_context_manager.py:89 (em BaseContextManager.update_config)
```

#### `self.cache.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/base_classes.py:308 (em BaseProcessor._get_cached_result)
```

#### `self.patterns_deteccao.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:182 (em ExcelOrchestrator._detectar_tipo_excel)
```

#### `self.cursor_mode.activated` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:87 (em CursorCommands._processar_comando_cursor_interno)
```

#### `self.cursor_mode.activate_cursor_mode` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/cursor_commands.py:109 (em CursorCommands._ativar_cursor_mode)
```

#### `self.command_registry.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:164 (em AutoCommandProcessor.get_command_suggestions)
```

#### `self.command_patterns.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:304 (em AutoCommandProcessor._detect_commands)
```

#### `self.command_history.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:501 (em AutoCommandProcessor._record_command_execution)
```

#### `self.interaction_history.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:282 (em AdaptiveLearning._record_interaction)
```

#### `self.feedback_patterns.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:191 (em FeedbackProcessor.analisar_feedback)
```

#### `self.sentiment_patterns.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/feedback_learning.py:321 (em FeedbackProcessor._detectar_sentimento)
```

#### `self.pattern_learner.extrair_e_salvar_padroes` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:119 (em LearningCore.aprender_com_interacao)
```

#### `self.feedback_processor.processar_feedback_completo` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:137 (em LearningCore.aprender_com_interacao)
```

#### `self.pattern_learner.buscar_padroes_aplicaveis` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:186 (em LearningCore.aplicar_conhecimento)
```

#### `self.knowledge_memory.buscar_grupos_aplicaveis` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:190 (em LearningCore.aplicar_conhecimento)
```

#### `self.knowledge_memory.buscar_mapeamentos_aplicaveis` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:191 (em LearningCore.aplicar_conhecimento)
```

#### `self.feedback_storage.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:106 (em HumanInLoopLearning.capture_feedback)
```

#### `self.improvement_queue.insert` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:138 (em HumanInLoopLearning._process_critical_feedback)
```

#### `self.learning_patterns.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:223 (em HumanInLoopLearning._create_learning_pattern)
```

#### `self.improvement_queue.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:245 (em HumanInLoopLearning._add_to_improvement_queue)
```

#### `self.learning_core.apply_learning` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/lifelong_learning.py:99 (em LifelongLearningSystem.apply_learning)
```

#### `self.learning_core.obter_estatisticas_aprendizado` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/lifelong_learning.py:113 (em LifelongLearningSystem.obter_estatisticas_aprendizado)
```

#### `self.coordinators.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:336 (em CoordinatorManager.get_coordinator_status)
```

#### `self.domain_agents.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:337 (em CoordinatorManager.get_coordinator_status)
```

#### `self.ai_cache.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:910 (em IntelligenceCoordinator._optimize_ai_cache)
```

#### `self.claude_client.client` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:236 (em ExternalAPIIntegration._get_integration_manager)
```

#### `self.claude_client.get_current_config` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:420 (em ExternalAPIIntegration.get_system_status)
```

#### `self.config.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:226 (em StandaloneIntegration.get_status)
```

#### `self._external_api_integration.get_system_status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:234 (em StandaloneIntegration.get_status)
```

#### `self._integration_manager.get_system_status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/standalone_integration.py:238 (em StandaloneIntegration.get_status)
```

#### `self.web_adapter.process_query_sync` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:359 (em WebFlaskRoutes.api_query)
```

#### `self.web_adapter.processar_consulta_sync` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:383 (em WebFlaskRoutes.api_query)
```

#### `self.web_adapter.claude_client` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:477 (em WebFlaskRoutes.health_check)
```

#### `self.web_adapter.db_engine` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:478 (em WebFlaskRoutes.health_check)
```

#### `self.web_adapter.get_available_modules` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:499 (em WebFlaskRoutes.system_status)
```

#### `self.web_adapter.initialization_result` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:500 (em WebFlaskRoutes.system_status)
```

#### `self.loader.load_data_by_domain` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:130 (em DataProvider.get_data_by_domain)
```

#### `self.request_stats.copy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:355 (em ProviderManager.get_provider_status)
```

#### `self.providers_cache.clear` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:362 (em ProviderManager.clear_cache)
```

#### `self.context_provider.clear_context_cache` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/provider_manager.py:364 (em ProviderManager.clear_cache)
```

#### `self.context_cache.clear` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/context_provider.py:267 (em ContextProvider.clear_context_cache)
```

#### `self.context_cache.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/context_provider.py:271 (em ContextProvider.clear_context_cache)
```

#### `self.context_sources.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/context_provider.py:344 (em ContextProvider._collect_complete_context)
```

#### `self.urls.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:295 (em CursorMonitor.top-level)
```

#### `self.project_scanner.scan_complete_project` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:91 (em ScanningManager.scan_complete_project)
```

#### `self.project_scanner.file_scanner.read_file_content` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:111 (em ScanningManager.read_file_content)
```

#### `self.project_scanner.file_scanner.list_directory_contents` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:115 (em ScanningManager.list_directory_contents)
```

#### `self.project_scanner.file_scanner.search_in_files` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:120 (em ScanningManager.search_in_files)
```

#### `self.database_manager.listar_tabelas` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:133 (em ScanningManager.scan_database)
```

#### `self.database_manager.obter_campos_tabela` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:145 (em ScanningManager.scan_database)
```

#### `self.database_manager.analisar_tabela_completa` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:157 (em ScanningManager.scan_database)
```

#### `self.database_manager.obter_estatisticas_gerais` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:165 (em ScanningManager.scan_database)
```

#### `self.database_manager.buscar_campos_por_tipo` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:176 (em ScanningManager.scan_database)
```

#### `self.database_manager.buscar_campos_por_nome` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:178 (em ScanningManager.scan_database)
```

#### `self.project_scanner.get_scanner_status().get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:267 (em ScanningManager.executar_diagnostico_completo)
```

#### `self._project_scanner.reset_scanner_data` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:313 (em ScanningManager.reset_scanner)
```

#### `self.project_scanner._generate_scan_summary` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:352 (em ScanningManager._generate_scan_summary)
```

#### `self.database_manager.scan_database_structure` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/scanning_manager.py:362 (em ScanningManager.get_database_info)
```

#### `self.metadata_scanner.listar_tabelas` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:91 (em DatabaseManager.listar_tabelas)
```

#### `self.field_searcher.buscar_campos_por_tipo` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:141 (em DatabaseManager.buscar_campos_por_tipo)
```

#### `self.field_searcher.buscar_campos_por_nome` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:164 (em DatabaseManager.buscar_campos_por_nome)
```

#### `self.metadata_scanner.obter_estatisticas_tabelas` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:213 (em DatabaseManager.obter_estatisticas_gerais)
```

#### `self.connection.get_connection_info` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:216 (em DatabaseManager.obter_estatisticas_gerais)
```

#### `self.data_analyzer.analisar_tabela_completa` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:251 (em DatabaseManager.analisar_tabela_completa)
```

#### `self.field_searcher.buscar_campos_similares` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:289 (em DatabaseManager.buscar_campos_similares)
```

#### `self.auto_mapper.gerar_mapeamento_multiplas_tabelas` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:303 (em DatabaseManager.gerar_mapeamento_multiplas_tabelas)
```

#### `self.relationship_mapper.obter_caminho_relacionamentos` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:316 (em DatabaseManager.obter_caminho_relacionamentos)
```

#### `self.metadata_scanner.limpar_cache` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:324 (em DatabaseManager.limpar_cache)
```

#### `self.data_analyzer.limpar_cache` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:325 (em DatabaseManager.limpar_cache)
```

#### `self.relationship_mapper.limpar_cache` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:326 (em DatabaseManager.limpar_cache)
```

#### `self.field_searcher.limpar_cache` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:327 (em DatabaseManager.limpar_cache)
```

#### `self.auto_mapper.limpar_cache` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:328 (em DatabaseManager.limpar_cache)
```

#### `self.modelos_cache.clear` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:332 (em DatabaseManager.limpar_cache)
```

#### `self.connection.close_connection` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:345 (em DatabaseManager.recarregar_conexao)
```

#### `self.connection._establish_connection` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:348 (em DatabaseManager.recarregar_conexao)
```

#### `self.metadata_scanner.set_inspector` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:355 (em DatabaseManager.recarregar_conexao)
```

#### `self.relationship_mapper.set_inspector` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:356 (em DatabaseManager.recarregar_conexao)
```

#### `self.field_searcher.set_inspector` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:357 (em DatabaseManager.recarregar_conexao)
```

#### `self.data_analyzer.set_engine` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:360 (em DatabaseManager.recarregar_conexao)
```

#### `self.field_searcher.set_metadata_scanner` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:361 (em DatabaseManager.recarregar_conexao)
```

#### `self.auto_mapper.set_metadata_scanner` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:362 (em DatabaseManager.recarregar_conexao)
```

#### `self.auto_mapper.set_data_analyzer` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:363 (em DatabaseManager.recarregar_conexao)
```

#### `self.connection.is_inspector_available` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:428 (em DatabaseManager.obter_info_modulos)
```

#### `self.metadata_scanner.tabelas_cache` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:432 (em DatabaseManager.obter_info_modulos)
```

#### `self.data_analyzer.analysis_cache` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:436 (em DatabaseManager.obter_info_modulos)
```

#### `self.relationship_mapper.relationships_cache` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:440 (em DatabaseManager.obter_info_modulos)
```

#### `self.field_searcher.search_cache` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:444 (em DatabaseManager.obter_info_modulos)
```

#### `self.auto_mapper.mapping_cache` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:448 (em DatabaseManager.obter_info_modulos)
```

#### `self.metadata_scanner._normalizar_tipo_sqlalchemy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:456 (em DatabaseManager._normalizar_tipo_sqlalchemy)
```

#### `self.field_searcher._calcular_score_match_nome` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:460 (em DatabaseManager._calcular_score_match)
```

#### `self.auto_mapper._gerar_termos_automaticos` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_manager.py:465 (em DatabaseManager._gerar_termos_automaticos)
```

#### `self.code_scanner.discover_all_forms` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:107 (em ProjectScanner.scan_complete_project)
```

#### `self.code_scanner.discover_all_routes` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:110 (em ProjectScanner.scan_complete_project)
```

#### `self.database_scanner.discover_database_schema` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:116 (em ProjectScanner.scan_complete_project)
```

#### `self.project_structure.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:177 (em ProjectScanner._generate_scan_summary)
```

#### `self.project_structure.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:178 (em ProjectScanner._generate_scan_summary)
```

#### `self.discovered_templates.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:250 (em ProjectScanner._calculate_quality_metrics)
```

#### `self.system_config.get_profile_config` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/advanced_config.py:97 (em AdvancedConfig.get_config)
```

#### `self.profiles.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:191 (em SystemConfig.switch_profile)
```

#### `self.configurations.get().copy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:231 (em SystemConfig.reload_config)
```

#### `self.configurations.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:231 (em SystemConfig.reload_config)
```

#### `self._flatten_dict().items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:281 (em SystemConfig.validate_configuration)
```

#### `self.configurations.copy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:355 (em SystemConfig.export_config)
```

#### `self.configurations.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:424 (em SystemConfig.get_system_status)
```

#### `self.metrics.copy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:426 (em SystemConfig.get_system_status)
```

#### `self.config_watchers.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:703 (em SystemConfig._notify_config_watchers)
```

#### `self.response_processor._processar_consulta_padrao` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:431 (em MainOrchestrator.process_query)
```

#### `self.auto_command_processor.process_natural_command` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:709 (em MainOrchestrator._execute_natural_commands)
```

#### `self.suggestions_manager.generate_intelligent_suggestions` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:756 (em MainOrchestrator._execute_intelligent_suggestions)
```

#### `self.base_command._validate_input` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:803 (em MainOrchestrator._execute_basic_commands)
```

#### `self.base_command._extract_filters_advanced` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:812 (em MainOrchestrator._execute_basic_commands)
```

#### `self.base_command._sanitize_input` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:816 (em MainOrchestrator._execute_basic_commands)
```

#### `self.base_command.__class__.__name__` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:823 (em MainOrchestrator._execute_basic_commands)
```

#### `self.base_command.__class__` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:823 (em MainOrchestrator._execute_basic_commands)
```

#### `self.response_processor.gerar_resposta_otimizada` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:876 (em MainOrchestrator._execute_response_processing)
```

#### `self.semantic.enrich` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1267 (em EnrichersWrapper.enrich_data)
```

#### `self.context.enrich` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1269 (em EnrichersWrapper.enrich_data)
```

#### `self.component_type.title` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1577 (em MockComponent.get_security_info)
```

#### `self.active_tasks.pop` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:296 (em OrchestratorManager.top-level)
```

#### `self.security_guard.sanitize_input` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:364 (em OrchestratorManager._log_security_audit)
```

#### `self.security_guard.generate_token` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:372 (em OrchestratorManager._log_security_audit)
```

#### `self.orchestrators.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:430 (em OrchestratorManager._detect_appropriate_orchestrator)
```

#### `self.orchestrators.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:447 (em OrchestratorManager.top-level)
```

#### `self.operation_history.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:607 (em OrchestratorManager._record_operation)
```

#### `self.operation_history.clear` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:721 (em OrchestratorManager.clear_history)
```

#### `self.workflows_ativos.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:317 (em WorkflowOrchestrator.obter_status_workflow)
```

#### `self.workflows_ativos.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:326 (em WorkflowOrchestrator.listar_workflows_ativos)
```

#### `self.workflows_ativos.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:353 (em WorkflowOrchestrator.limpar_workflows_concluidos)
```

#### `self.workflows_ativos.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:374 (em WorkflowOrchestrator.obter_estatisticas)
```

#### `self.templates_workflow.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:381 (em WorkflowOrchestrator.obter_estatisticas)
```

#### `self.executores.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:382 (em WorkflowOrchestrator.obter_estatisticas)
```

#### `self.sessions.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:58 (em MockSessionMemory.get_session)
```

#### `self.session_memory.store_session` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:248 (em SessionOrchestrator.create_session)
```

#### `self.conversation_manager.manage_conversation` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:454 (em SessionOrchestrator._execute_conversation_workflow)
```

#### `self.active_sessions.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:617 (em SessionOrchestrator.get_session)
```

#### `self.active_sessions.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:650 (em SessionOrchestrator.cleanup_expired_sessions)
```

#### `self.cleanup_handlers.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:719 (em SessionOrchestrator.register_cleanup_handler)
```

#### `self.validators.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:317 (em ValidatorManager.validate_consistency)
```

#### `self.validators.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:362 (em ValidatorManager.get_validation_status)
```

#### `self.EntregaMonitorada.data_embarque.is_` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:164 (em ValidationUtils._calcular_estatisticas_especificas)
```

#### `self.EntregaMonitorada.vendedor` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:192 (em ValidationUtils._calcular_estatisticas_especificas)
```

#### `self.EntregaMonitorada.status_finalizacao.in_` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/data_validator.py:196 (em ValidationUtils._calcular_estatisticas_especificas)
```

#### `self.orchestrator.mapear_termo_natural` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:358 (em SemanticValidator.validar_mapeamento_completo)
```

#### `self.system_memory.store_system_config` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:86 (em MemoryManager.store_system_configuration)
```

#### `self.system_memory.retrieve_system_config` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:102 (em MemoryManager.retrieve_system_configuration)
```

#### `self.system_memory.store_performance_metric` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:236 (em MemoryManager.record_performance_metric)
```

#### `self.context_memory.get_memory_stats` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:255 (em MemoryManager.get_system_overview)
```

#### `self.system_memory.get_system_overview` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:257 (em MemoryManager.get_system_overview)
```

#### `self.system_memory.cleanup_expired_data` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:283 (em MemoryManager.cleanup_expired_data)
```

#### `self.context_memory.clear_context` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:311 (em MemoryManager.clear_all_context)
```

#### `self.context_memory.get_active_sessions` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:324 (em MemoryManager.get_active_sessions)
```

#### `self.context_memory.set_processor` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:449 (em MemoryManager.set_processor)
```

#### `self.conversation_memory.set_processor` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/memory_manager.py:453 (em MemoryManager.set_processor)
```

#### `self.mapeamentos.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:133 (em BaseMapper.listar_todos_campos)
```

#### `self.model.data_entrega_prevista` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:324 (em EntregasLoader._build_entregas_query)
```

#### `self.model.cnpj_cliente.like` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:347 (em EntregasLoader._build_entregas_query)
```

#### `self.model.data_embarque.desc` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/entregas_loader.py:370 (em EntregasLoader._build_entregas_query)
```

#### `self.model.data_agendamento.desc` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/agendamentos_loader.py:186 (em AgendamentosLoader._build_agendamentos_query)
```

#### `self.model.cnpj_cliente.ilike` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:171 (em FaturamentoLoader._build_faturamento_query)
```

#### `self.model.data_fatura.desc` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/faturamento_loader.py:176 (em FaturamentoLoader._build_faturamento_query)
```

#### `self.model.query.join` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:161 (em FretesLoader._build_fretes_query)
```

#### `self.model.transportadora_id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:163 (em FretesLoader._build_fretes_query)
```

#### `self.transportadora_model.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:163 (em FretesLoader._build_fretes_query)
```

#### `self.model.criado_em` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:172 (em FretesLoader._build_fretes_query)
```

#### `self.model.data_emissao_cte` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:173 (em FretesLoader._build_fretes_query)
```

#### `self.transportadora_model.razao_social.ilike` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:191 (em FretesLoader._build_fretes_query)
```

#### `self.transportadora_model.razao_social` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/fretes_loader.py:191 (em FretesLoader._build_fretes_query)
```

#### `self.model.status_calculado` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/pedidos_loader.py:162 (em PedidosLoader._build_pedidos_query)
```

#### `self.model.data_embarque.is_` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:167 (em EmbarquesLoader._build_embarques_query)
```

#### `self.item_model.cliente.ilike` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:178 (em EmbarquesLoader._build_embarques_query)
```

#### `self.item_model.cliente` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/domain/embarques_loader.py:178 (em EmbarquesLoader._build_embarques_query)
```

#### `self.agent_type.value.upper` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:132 (em BaseSpecialistAgent.top-level)
```

#### `self.claude_client.messages.create` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:146 (em BaseSpecialistAgent.top-level)
```

#### `self.claude_client.messages` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/base_agent.py:146 (em BaseSpecialistAgent.top-level)
```

#### `self.term_patterns.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:232 (em AutoMapper._gerar_termos_automaticos)
```

#### `self.term_patterns.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:333 (em AutoMapper._calcular_confianca_mapeamento)
```

#### `self.db_session.close` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:336 (em DatabaseConnection.close_connection)
```

#### `self.db_engine.dispose` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:340 (em DatabaseConnection.close_connection)
```

#### `self.inspector.get_columns` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:85 (em MetadataScanner.obter_campos_tabela)
```

#### `self.inspector.get_indexes` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:171 (em MetadataScanner._obter_indices_tabela)
```

#### `self.inspector.get_pk_constraint` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:212 (em MetadataScanner._obter_constraints_tabela)
```

#### `self.inspector.get_unique_constraints` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:230 (em MetadataScanner._obter_constraints_tabela)
```

#### `self.inspector.get_check_constraints` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:238 (em MetadataScanner._obter_constraints_tabela)
```

#### `self._field_types_cache.clear` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/data_analyzer.py:48 (em DataAnalyzer.set_engine)
```

### 🔍 Objeto: `semantic`

#### `semantic.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:84 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:91 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:250 (em ContextEnricher._calculate_context_score)
```

### 🔍 Objeto: `semantic_analysis`

#### `semantic_analysis.get` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:311 (em AnalyzerManager._should_use_nlp_analysis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:343 (em AnalyzerManager._should_use_advanced_analysis)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:385 (em AnalyzerManager._generate_combined_insights)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:386 (em AnalyzerManager._generate_combined_insights)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:162 (em SemanticLoopProcessor.top-level)
  ... e mais 2 ocorrências
```

### 🔍 Objeto: `semantic_mapper`

#### `semantic_mapper.analisar_consulta_semantica` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:126 (em SemanticLoopProcessor.top-level)
```

### 🔍 Objeto: `semantic_processor`

#### `semantic_processor.process_semantic_loop` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/processor_manager.py:83 (em ProcessorManager.process_semantic_loop)
```

### 🔍 Objeto: `semantic_validator`

#### `semantic_validator.validar_consistencia_readme_banco` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:325 (em ValidatorManager.validate_consistency)
```

### 🔍 Objeto: `session`

#### `session.metadata` (12 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:295 (em SessionOrchestrator.initialize_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:302 (em SessionOrchestrator.initialize_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:367 (em SessionOrchestrator.execute_session_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:374 (em SessionOrchestrator.execute_session_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:420 (em SessionOrchestrator._execute_learning_workflow)
  ... e mais 7 ocorrências
```

#### `session.metadata.update` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:295 (em SessionOrchestrator.initialize_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:367 (em SessionOrchestrator.execute_session_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:420 (em SessionOrchestrator._execute_learning_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:463 (em SessionOrchestrator._execute_conversation_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:500 (em SessionOrchestrator.apply_learned_knowledge)
  ... e mais 2 ocorrências
```

#### `session.session_id` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:426 (em SessionOrchestrator._execute_learning_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:430 (em SessionOrchestrator._execute_learning_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:455 (em SessionOrchestrator._execute_conversation_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:470 (em SessionOrchestrator._execute_conversation_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:474 (em SessionOrchestrator._execute_conversation_workflow)
```

#### `session.update_activity` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:282 (em SessionOrchestrator.initialize_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:341 (em SessionOrchestrator.execute_session_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:532 (em SessionOrchestrator.complete_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:580 (em SessionOrchestrator.terminate_session)
```

#### `session.user_id` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:416 (em SessionOrchestrator._execute_learning_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:459 (em SessionOrchestrator._execute_conversation_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:634 (em SessionOrchestrator.get_user_sessions)
```

#### `session.components` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:286 (em SessionOrchestrator.initialize_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:297 (em SessionOrchestrator.initialize_session)
```

#### `session.error_history.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:310 (em SessionOrchestrator.initialize_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:382 (em SessionOrchestrator.execute_session_workflow)
```

#### `session.error_history` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:310 (em SessionOrchestrator.initialize_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:382 (em SessionOrchestrator.execute_session_workflow)
```

#### `session.is_active` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:335 (em SessionOrchestrator.execute_session_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:635 (em SessionOrchestrator.get_user_sessions)
```

#### `session.status.value` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:336 (em SessionOrchestrator.execute_session_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:689 (em SessionOrchestrator.get_session_stats)
```

#### `session.status` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:336 (em SessionOrchestrator.execute_session_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:689 (em SessionOrchestrator.get_session_stats)
```

#### `session.workflow_state` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:357 (em SessionOrchestrator.execute_session_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:370 (em SessionOrchestrator.execute_session_workflow)
```

#### `session.created_at` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:541 (em SessionOrchestrator.complete_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:697 (em SessionOrchestrator.get_session_stats)
```

#### `session.components.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:286 (em SessionOrchestrator.initialize_session)
```

#### `session.is_expired` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:651 (em SessionOrchestrator.cleanup_expired_sessions)
```

#### `session.priority.value` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:693 (em SessionOrchestrator.get_session_stats)
```

#### `session.priority` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:693 (em SessionOrchestrator.get_session_stats)
```

### 🔍 Objeto: `session_context`

#### `session_context.metadata` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:234 (em SessionOrchestrator.create_session)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:248 (em SessionOrchestrator.create_session)
```

#### `session_context.metadata.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:234 (em SessionOrchestrator.create_session)
```

### 🔍 Objeto: `session_orch`

#### `session_orch.learning_core` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:272 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `session_orch.security_guard` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:273 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `session_orch.conversation_manager` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:274 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `session_orch.create_session` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:281 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `session_orch.execute_session_workflow` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:286 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

#### `session_orch.complete_session` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:290 (em TesteIntegracaoCompleta.testar_orchestrators_integrados)
```

### 🔍 Objeto: `sessions`

#### `sessions.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:636 (em SessionOrchestrator.get_user_sessions)
```

### 🔍 Objeto: `set`

#### `set.intersection` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:138 (em ClassDuplicateFinder.calculate_similarity)
```

#### `set.union` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_classes_duplicadas.py:139 (em ClassDuplicateFinder.calculate_similarity)
```

### 🔍 Objeto: `signal`

#### `signal.signal` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:346 (em CursorMonitor.start)
```

#### `signal.SIGINT` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:346 (em CursorMonitor.start)
```

### 🔍 Objeto: `sistema`

#### `sistema.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:372 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
```

### 🔍 Objeto: `source_data`

#### `source_data.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:114 (em FieldMapper.map_fields)
```

### 🔍 Objeto: `source_results`

#### `source_results.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:176 (em IntelligenceProcessor.synthesize_multi_source_intelligence)
```

### 🔍 Objeto: `sources_used`

#### `sources_used.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:123 (em SuggestionsManager.generate_suggestions)
```

### 🔍 Objeto: `spacy`

#### `spacy.load` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:20 (em module.top-level)
```

#### `spacy.blank` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:23 (em module.top-level)
```

### 🔍 Objeto: `specific_results`

#### `specific_results.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:136 (em DeepValidator._test_individual_module)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:137 (em DeepValidator._test_individual_module)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:138 (em DeepValidator._test_individual_module)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:141 (em DeepValidator._test_individual_module)
```

### 🔍 Objeto: `start_date`

#### `start_date.replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:260 (em BaseValidationUtils.validate_date_range)
```

### 🔍 Objeto: `state`

#### `state.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:141 (em SystemMemory.store_component_state)
```

### 🔍 Objeto: `state_data`

#### `state_data.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:183 (em SystemMemory.retrieve_component_state)
```

### 🔍 Objeto: `statistics`

#### `statistics.mean` (10 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:177 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:178 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:179 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:304 (em PerformanceAnalyzer.analyze_user_behavior)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:408 (em PerformanceAnalyzer._analyze_trends)
  ... e mais 5 ocorrências
```

#### `statistics.stdev` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:197 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:567 (em PerformanceAnalyzer.detect_outliers)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:585 (em PerformanceAnalyzer._detect_statistical_anomalies)
```

#### `statistics.median` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:196 (em PerformanceAnalyzer.analyze_ai_performance)
```

### 🔍 Objeto: `stats`

#### `stats.get` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:164 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:165 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:354 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:343 (em module.format_response_advanced)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:488 (em SemanticEnricher._gerar_sugestoes_batch)
  ... e mais 6 ocorrências
```

#### `stats.update` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:297 (em BaseCommand._create_summary_stats)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:308 (em BaseCommand._create_summary_stats)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:317 (em BaseCommand._create_summary_stats)
```

#### `stats.get().get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:484 (em KnowledgeMemory.get_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:485 (em KnowledgeMemory.get_status)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:486 (em KnowledgeMemory.get_status)
```

### 🔍 Objeto: `status`

#### `status.get` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/response_utils.py:83 (em ResponseUtils._formatar_status_cursor)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/learning_core.py:430 (em LearningCore._avaliar_saude_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:273 (em ExternalAPIIntegration.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/external_api_integration.py:274 (em ExternalAPIIntegration.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/__init__.py:199 (em module.top-level)
  ... e mais 3 ocorrências
```

#### `status.values` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/__init__.py:169 (em module.validate_flask_dependencies)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:281 (em module.get_commands_info)
```

#### `status.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/__init__.py:372 (em module.top-level)
```

#### `status.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/integration_manager.py:372 (em IntegrationManager.get_integration_status)
```

### 🔍 Objeto: `status_count`

#### `status_count.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:326 (em ExcelPedidos._criar_aba_analise_vendas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:386 (em ExcelPedidos._criar_resumo_pedidos)
```

#### `status_count.items` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:328 (em ExcelPedidos._criar_aba_analise_vendas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:410 (em ExcelPedidos._criar_resumo_pedidos)
```

### 🔍 Objeto: `status_counts`

#### `status_counts.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/workflow_orchestrator.py:376 (em WorkflowOrchestrator.obter_estatisticas)
```

### 🔍 Objeto: `status_data`

#### `status_data.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:364 (em ExcelPedidos._criar_aba_status_agendamentos)
```

### 🔍 Objeto: `step`

#### `step.component` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1073 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1075 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1077 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1079 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1096 (em MainOrchestrator.top-level)
```

#### `step.dependencies` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1007 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1008 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1031 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1031 (em MainOrchestrator.top-level)
```

#### `step.name` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1014 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1043 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1093 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1099 (em MainOrchestrator.top-level)
```

#### `step.method` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1086 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1087 (em MainOrchestrator.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1096 (em MainOrchestrator.top-level)
```

#### `step.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:218 (em module.run_complete_flow)
```

#### `step.parameters` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1082 (em MainOrchestrator.top-level)
```

### 🔍 Objeto: `step_config`

#### `step_config.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:80 (em ProcessorCoordinator._execute_chain_step)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:81 (em ProcessorCoordinator._execute_chain_step)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:82 (em ProcessorCoordinator._execute_chain_step)
```

### 🔍 Objeto: `step_result`

#### `step_result.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:44 (em ProcessorCoordinator.execute_processor_chain)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:47 (em ProcessorCoordinator.execute_processor_chain)
```

### 🔍 Objeto: `stmt`

#### `stmt.value` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:91 (em DependencyAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:91 (em DependencyAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:67 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:68 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:68 (em DeepImportAnalyzer.visit_Try)
  ... e mais 6 ocorrências
```

#### `stmt.lineno` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:92 (em DependencyAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:72 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:83 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:91 (em DeepImportAnalyzer.visit_Try)
```

#### `stmt.value.value` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:68 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:68 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:71 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:79 (em DeepImportAnalyzer.visit_Try)
```

#### `stmt.targets` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:87 (em DependencyAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:77 (em DeepImportAnalyzer.visit_Try)
```

#### `stmt.value.func` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:87 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:87 (em DeepImportAnalyzer.visit_Try)
```

#### `stmt.value.func.id.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:87 (em DeepImportAnalyzer.visit_Try)
```

#### `stmt.value.func.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:87 (em DeepImportAnalyzer.visit_Try)
```

### 🔍 Objeto: `stopwords`

#### `stopwords.words` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:43 (em module.top-level)
```

### 🔍 Objeto: `str()`

#### `str().lower` (12 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:68 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:68 (em DeepImportAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:64 (em FieldMapper._setup_default_transformers)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:165 (em PerformanceAnalyzer.analyze_ai_performance)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:107 (em DatabaseScanner._get_database_version)
  ... e mais 7 ocorrências
```

#### `str().strip` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:65 (em FieldMapper._setup_default_transformers)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:72 (em FieldMapper._setup_default_validators)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/system_config.py:626 (em SystemConfig._validate_config_value)
```

#### `str().replace().replace` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:105 (em CircularDependencyMapper.build_dependency_graph)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:73 (em FieldMapper._setup_default_validators)
```

#### `str().replace` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:105 (em CircularDependencyMapper.build_dependency_graph)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:73 (em FieldMapper._setup_default_validators)
```

#### `str().upper` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:63 (em FieldMapper._setup_default_transformers)
```

#### `str().replace().replace().isdigit` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/field_mapper.py:73 (em FieldMapper._setup_default_validators)
```

#### `str().split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:606 (em SuggestionsManager._assess_query_complexity)
```

#### `str().startswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:194 (em FileScanner.read_file_content)
```

### 🔍 Objeto: `strengths`

#### `strengths.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:685 (em IntelligenceProcessor._evaluate_option)
```

### 🔍 Objeto: `structural_analysis`

#### `structural_analysis.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:407 (em AnalyzerManager._generate_combined_insights)
```

### 🔍 Objeto: `structure`

#### `structure.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:258 (em ValidatorManager.validate_structural_integrity)
```

### 🔍 Objeto: `subdirs_validos`

#### `subdirs_validos.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/contagem_detalhada_modulos.py:78 (em module.contar_arquivos_detalhado)
```

### 🔍 Objeto: `subprocess`

#### `subprocess.run` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:74 (em DependencyChecker.check_pip_package)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:136 (em CursorMonitor.check_flask_process)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:153 (em CursorMonitor.run_validator)
```

#### `subprocess.TimeoutExpired` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:178 (em CursorMonitor.run_validator)
```

### 🔍 Objeto: `sugestoes`

#### `sugestoes.append` (19 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:268 (em SemanticEnricher._sugestoes_readme_vs_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:275 (em SemanticEnricher._sugestoes_readme_vs_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:280 (em SemanticEnricher._sugestoes_readme_vs_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:307 (em SemanticEnricher._sugestoes_qualidade_banco)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:311 (em SemanticEnricher._sugestoes_qualidade_banco)
  ... e mais 14 ocorrências
```

#### `sugestoes.extend` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:233 (em SemanticEnricher._gerar_sugestoes_melhoria)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:236 (em SemanticEnricher._gerar_sugestoes_melhoria)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:239 (em SemanticEnricher._gerar_sugestoes_melhoria)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/semantic_enricher.py:242 (em SemanticEnricher._gerar_sugestoes_melhoria)
```

### 🔍 Objeto: `suggestion`

#### `suggestion.get` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:127 (em SuggestionsManager.generate_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:128 (em SuggestionsManager.generate_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:438 (em SuggestionsManager._prioritize_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:632 (em SuggestionsManager._categorize_suggestion)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:636 (em SuggestionsManager._generate_explanation)
  ... e mais 1 ocorrências
```

#### `suggestion.copy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:463 (em SuggestionsManager._enrich_suggestions)
```

### 🔍 Objeto: `suggestions`

#### `suggestions.extend` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:368 (em SuggestionsEngine._generate_data_based_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:391 (em SuggestionsEngine._generate_data_based_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:549 (em SuggestionsManager._contextual_suggestions_engine)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:564 (em SuggestionsManager._contextual_suggestions_engine)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/pedidos_mapper.py:189 (em PedidosMapper.get_semantic_suggestions)
  ... e mais 2 ocorrências
```

#### `suggestions.append` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:334 (em SuggestionsEngine._generate_data_based_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:345 (em SuggestionsEngine._generate_data_based_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:356 (em SuggestionsEngine._generate_data_based_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:418 (em SuggestionsEngine._generate_data_based_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:171 (em AutoCommandProcessor.get_command_suggestions)
```

#### `suggestions.sort` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:181 (em AutoCommandProcessor.get_command_suggestions)
```

### 🔍 Objeto: `suggestions_result`

#### `suggestions_result.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:763 (em MainOrchestrator._execute_intelligent_suggestions)
```

### 🔍 Objeto: `suitable_components`

#### `suitable_components.sort` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:615 (em IntelligenceCoordinator._select_best_component)
```

### 🔍 Objeto: `super()`

#### `super().__init__` (36 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:111 (em AnalyzerManager.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/base.py:30 (em ProcessorBase.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:104 (em ResponseProcessor.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/context_processor.py:71 (em ContextProcessor.__init__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/semantic_loop_processor.py:22 (em SemanticLoopProcessor.__init__)
  ... e mais 31 ocorrências
```

#### `super().__new__` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:41 (em MapperManager.__new__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/loader_manager.py:41 (em LoaderManager.__new__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:38 (em ScannersCache.__new__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:42 (em ClaudeAIMetrics.__new__)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:42 (em ClaudeAIMetricsOptimized.__new__)
```

#### `super()._get_cached_result` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/base.py:89 (em ProcessorBase._get_cached_result)
```

#### `super().to_dict` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/advanced_config.py:96 (em AdvancedConfig.get_config)
```

#### `super().analyze` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/domain_agents/smart_base_agent.py:231 (em SmartBaseAgent.top-level)
```

### 🔍 Objeto: `sys`

#### `sys.path` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:9 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:15 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:16 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:17 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:17 (em module.top-level)
  ... e mais 6 ocorrências
```

#### `sys.path.insert` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:9 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:15 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:16 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:17 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:17 (em module.top-level)
  ... e mais 4 ocorrências
```

#### `sys.exit` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:452 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:347 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:279 (em module.top-level)
```

#### `sys.modules` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:38 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:39 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:42 (em module.top-level)
```

#### `sys.executable` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:75 (em DependencyChecker.check_pip_package)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:154 (em CursorMonitor.run_validator)
```

#### `sys.path.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/database_connection.py:19 (em module.top-level)
```

### 🔍 Objeto: `system`

#### `system.__class__.__name__` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/__init__.py:200 (em module.initialize_integration_system)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/__init__.py:205 (em module.initialize_integration_system)
```

#### `system.__class__` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/__init__.py:200 (em module.initialize_integration_system)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/__init__.py:205 (em module.initialize_integration_system)
```

#### `system.initialize_complete_system` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/__init__.py:190 (em module.initialize_integration_system)
```

### 🔍 Objeto: `system_claude_config`

#### `system_claude_config.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/advanced_config.py:102 (em AdvancedConfig.get_config)
```

### 🔍 Objeto: `system_config`

#### `system_config.get_config` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/__init__.py:163 (em module.get_config)
```

#### `system_config.set_config` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/__init__.py:215 (em module.set_config)
```

#### `system_config.get_profile_config` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/__init__.py:243 (em module.get_profile_config)
```

#### `system_config.switch_profile` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/__init__.py:264 (em module.switch_profile)
```

#### `system_config.reload_config` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/__init__.py:286 (em module.reload_config)
```

#### `system_config.validate_configuration` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/__init__.py:313 (em module.validate_configuration)
```

#### `system_config.export_config` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/__init__.py:341 (em module.export_config)
```

#### `system_config.import_config` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/__init__.py:369 (em module.import_config)
```

#### `system_config.register_config_watcher` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/__init__.py:393 (em module.register_config_watcher)
```

#### `system_config.get_system_status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/config/__init__.py:414 (em module.get_system_status)
```

### 🔍 Objeto: `system_status`

#### `system_status.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:463 (em WebFlaskRoutes.health_check)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/integration/web_integration.py:464 (em WebFlaskRoutes.health_check)
```

### 🔍 Objeto: `t`

#### `t.start` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:208 (em TestLoopPrevention.test_stress_concurrent_requests)
```

#### `t.join` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:212 (em TestLoopPrevention.test_stress_concurrent_requests)
```

#### `t.strip().strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:179 (em ReadmeScanner._extrair_termos_da_string)
```

#### `t.strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:179 (em ReadmeScanner._extrair_termos_da_string)
```

### 🔍 Objeto: `tabelas_nao_documentadas`

#### `tabelas_nao_documentadas.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:262 (em SemanticValidator.validar_consistencia_readme_banco)
```

### 🔍 Objeto: `table_name`

#### `table_name.startswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:387 (em MapperManager._identify_mapper_for_table)
```

### 🔍 Objeto: `tables`

#### `tables.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database_scanner.py:288 (em DatabaseScanner._analyze_relationships)
```

### 🔍 Objeto: `tables_info`

#### `tables_info.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:397 (em MapperManager._optimize_mappings_with_indexes)
```

### 🔍 Objeto: `target`

#### `target.id` (9 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:56 (em VariableTracker.visit_ClassDef)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:63 (em VariableTracker.visit_Assign)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:64 (em VariableTracker.visit_Assign)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:90 (em DependencyAnalyzer.visit_Try)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_profundo.py:82 (em DeepImportAnalyzer.visit_Try)
  ... e mais 4 ocorrências
```

#### `target.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:403 (em ValidatorManager.run_full_validation_suite)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:416 (em ValidatorManager.run_full_validation_suite)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:421 (em ValidatorManager.run_full_validation_suite)
```

### 🔍 Objeto: `target_dir`

#### `target_dir.exists` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:227 (em FileScanner.list_directory_contents)
```

#### `target_dir.is_dir` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:227 (em FileScanner.list_directory_contents)
```

#### `target_dir.relative_to` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:231 (em FileScanner.list_directory_contents)
```

#### `target_dir.iterdir` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:240 (em FileScanner.list_directory_contents)
```

### 🔍 Objeto: `target_orchestrator`

#### `target_orchestrator.value` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:266 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:271 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:290 (em OrchestratorManager.top-level)
```

#### `target_orchestrator.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:769 (em module.top-level)
```

### 🔍 Objeto: `task`

#### `task.operation` (18 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:462 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:519 (em OrchestratorManager._execute_workflow_operation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:520 (em OrchestratorManager._execute_workflow_operation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:522 (em OrchestratorManager._execute_workflow_operation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:527 (em OrchestratorManager.top-level)
  ... e mais 13 ocorrências
```

#### `task.parameters` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:463 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:521 (em OrchestratorManager._execute_workflow_operation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:533 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:576 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:577 (em OrchestratorManager.top-level)
  ... e mais 3 ocorrências
```

#### `task.orchestrator_type` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:447 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:449 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:452 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:454 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:609 (em OrchestratorManager._record_operation)
```

#### `task.parameters.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:576 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:577 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:583 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:584 (em OrchestratorManager.top-level)
```

#### `task.created_at` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:273 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:612 (em OrchestratorManager._record_operation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:614 (em OrchestratorManager._record_operation)
```

#### `task.orchestrator_type.value` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:449 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:609 (em OrchestratorManager._record_operation)
```

#### `task.operation.lower` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:462 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:552 (em OrchestratorManager.top-level)
```

#### `task.task_id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:608 (em OrchestratorManager._record_operation)
```

#### `task.status` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:611 (em OrchestratorManager._record_operation)
```

#### `task.created_at.isoformat` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:612 (em OrchestratorManager._record_operation)
```

#### `task.error` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:615 (em OrchestratorManager._record_operation)
```

#### `task.done` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:203 (em ValidatorManager.validate_agent_responses)
```

#### `task.result` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:203 (em ValidatorManager.validate_agent_responses)
```

### 🔍 Objeto: `tempfile`

#### `tempfile.gettempdir` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:69 (em BaseCommand.__init__)
```

### 🔍 Objeto: `template_info`

#### `template_info.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/project_scanner.py:251 (em ProjectScanner._calculate_quality_metrics)
```

### 🔍 Objeto: `templates_dir`

#### `templates_dir.exists` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:52 (em FileScanner.discover_all_templates)
```

### 🔍 Objeto: `temporal`

#### `temporal.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/context_enricher.py:246 (em ContextEnricher._calculate_context_score)
```

### 🔍 Objeto: `temporal_words`

#### `temporal_words.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:209 (em QueryAnalyzer._detect_temporal_patterns)
```

### 🔍 Objeto: `termo`

#### `termo.lower` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:422 (em SemanticValidator._calcular_similaridade_termo_campo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:430 (em SemanticValidator._calcular_similaridade_termo_campo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:73 (em KnowledgeMemory.aprender_mapeamento_cliente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:97 (em KnowledgeMemory.aprender_mapeamento_cliente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:63 (em BaseMapper.buscar_mapeamento)
  ... e mais 1 ocorrências
```

#### `termo.strip` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:78 (em MapperManager.analisar_consulta_semantica)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:185 (em ReadmeScanner._extrair_termos_da_string)
```

#### `termo.lower().strip` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:63 (em BaseMapper.buscar_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:101 (em BaseMapper.buscar_mapeamento_fuzzy)
```

#### `termo.strip().strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:185 (em ReadmeScanner._extrair_termos_da_string)
```

#### `termo.lower().replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:422 (em SemanticValidator._calcular_similaridade_termo_campo)
```

#### `termo.lower().split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:430 (em SemanticValidator._calcular_similaridade_termo_campo)
```

### 🔍 Objeto: `termo_natural`

#### `termo_natural.lower` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:69 (em BaseMapper.buscar_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:106 (em BaseMapper.buscar_mapeamento_fuzzy)
```

### 🔍 Objeto: `termos`

#### `termos.append` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:463 (em PatternLearner._extrair_termos_cliente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:469 (em PatternLearner._extrair_termos_cliente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:477 (em PatternLearner._extrair_termos_cliente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:413 (em KnowledgeMemory._extrair_termos_cliente)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/knowledge_memory.py:419 (em KnowledgeMemory._extrair_termos_cliente)
  ... e mais 3 ocorrências
```

#### `termos.extend` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:166 (em ReadmeScanner._extrair_termos_da_string)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:172 (em ReadmeScanner._extrair_termos_da_string)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:180 (em ReadmeScanner._extrair_termos_da_string)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/base_mapper.py:144 (em BaseMapper.listar_termos_naturais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:234 (em AutoMapper._gerar_termos_automaticos)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `termos_compostos`

#### `termos_compostos.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/mapper_manager.py:156 (em MapperManager._extrair_termos_compostos)
```

### 🔍 Objeto: `termos_encontrados`

#### `termos_encontrados.extend` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:116 (em ReadmeScanner.buscar_termos_naturais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:124 (em ReadmeScanner.buscar_termos_naturais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:133 (em ReadmeScanner.buscar_termos_naturais)
```

### 🔍 Objeto: `termos_limpos`

#### `termos_limpos.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:187 (em ReadmeScanner._extrair_termos_da_string)
```

### 🔍 Objeto: `termos_melhorados`

#### `termos_melhorados.extend` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:422 (em AutoMapper._melhorar_termos_com_analise)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:426 (em AutoMapper._melhorar_termos_com_analise)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:430 (em AutoMapper._melhorar_termos_com_analise)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:434 (em AutoMapper._melhorar_termos_com_analise)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:438 (em AutoMapper._melhorar_termos_com_analise)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `termos_originais`

#### `termos_originais.copy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:412 (em AutoMapper._melhorar_termos_com_analise)
```

### 🔍 Objeto: `termos_tipo`

#### `termos_tipo.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:316 (em AutoMapper._obter_termos_por_tipo)
```

### 🔍 Objeto: `termos_unicos`

#### `termos_unicos.append` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:142 (em ReadmeScanner.buscar_termos_naturais)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:251 (em AutoMapper._gerar_termos_automaticos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/auto_mapper.py:453 (em AutoMapper._melhorar_termos_com_analise)
```

### 🔍 Objeto: `tester`

#### `tester.testar_todos_modulos` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:426 (em module.main)
```

### 🔍 Objeto: `text`

#### `text.split` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/__init__.py:52 (em NLPEnhancedAnalyzer.analyze_text)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/__init__.py:52 (em NLPEnhancedAnalyzer.analyze_text)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:33 (em FallbackNLPEnhancedAnalyzer.analyze_text)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:33 (em FallbackNLPEnhancedAnalyzer.analyze_text)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/analyzer_manager.py:528 (em AnalyzerManager.analyze_nlp)
  ... e mais 2 ocorrências
```

#### `text.lower` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/semantic_analyzer.py:272 (em SemanticAnalyzer._extract_keywords)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:301 (em AutoCommandProcessor._detect_commands)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:168 (em CriticAgent._validate_data_consistency)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:170 (em CriticAgent._validate_data_consistency)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:187 (em CriticAgent._validate_data_consistency)
  ... e mais 1 ocorrências
```

### 🔍 Objeto: `texto`

#### `texto.lower` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:118 (em NLPEnhancedAnalyzer.analisar_com_nlp)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:285 (em NLPEnhancedAnalyzer._calcular_similaridades)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:383 (em PatternLearner._extrair_palavras_chave_dominio)
```

#### `texto.lower().strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:118 (em NLPEnhancedAnalyzer.analisar_com_nlp)
```

#### `texto.lower().split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:383 (em PatternLearner._extrair_palavras_chave_dominio)
```

#### `texto.strip().strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:177 (em ReadmeScanner._extrair_termos_da_string)
```

#### `texto.strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:177 (em ReadmeScanner._extrair_termos_da_string)
```

### 🔍 Objeto: `texto_corrigido`

#### `texto_corrigido.replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:182 (em NLPEnhancedAnalyzer._aplicar_correcoes)
```

#### `texto_corrigido.split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:187 (em NLPEnhancedAnalyzer._aplicar_correcoes)
```

### 🔍 Objeto: `texto_limpo`

#### `texto_limpo.lower().split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:229 (em NLPEnhancedAnalyzer._tokenizar_basico)
```

#### `texto_limpo.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:229 (em NLPEnhancedAnalyzer._tokenizar_basico)
```

#### `texto_limpo.split` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/readme_scanner.py:179 (em ReadmeScanner._extrair_termos_da_string)
```

### 🔍 Objeto: `thread`

#### `thread.start` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:110 (em TestLoopPrevention.test_timeout_protection)
```

#### `thread.join` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:113 (em TestLoopPrevention.test_timeout_protection)
```

#### `thread.is_alive` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:115 (em TestLoopPrevention.test_timeout_protection)
```

### 🔍 Objeto: `threading`

#### `threading.Lock` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/response_processor.py:714 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:32 (em ScannersCache.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:30 (em ClaudeAIMetrics.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:30 (em ClaudeAIMetricsOptimized.top-level)
```

#### `threading.Thread` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:108 (em TestLoopPrevention.test_timeout_protection)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:206 (em TestLoopPrevention.test_stress_concurrent_requests)
```

### 🔍 Objeto: `threads`

#### `threads.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:207 (em TestLoopPrevention.test_stress_concurrent_requests)
```

### 🔍 Objeto: `time`

#### `time.time` (25 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/__init__.py:33 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/base.py:157 (em ProcessorBase._handle_error)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:127 (em ScannersCache.get_cached_result)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:146 (em ScannersCache.set_cached_result)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/performance_cache.py:161 (em ScannersCache._cleanup_expired_cache)
  ... e mais 20 ocorrências
```

### 🔍 Objeto: `time_since_activity`

#### `time_since_activity.total_seconds` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:338 (em ConversationManager.cleanup_expired_conversations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/conversation_manager.py:408 (em ConversationManager._is_conversation_active)
```

### 🔍 Objeto: `timestamp`

#### `timestamp.hour` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:358 (em AdaptiveLearning._detect_time_pattern)
```

### 🔍 Objeto: `tipo`

#### `tipo.title` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:364 (em ExcelOrchestrator._fallback_tipo_indisponivel)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:358 (em module.create_excel_summary)
```

#### `tipo.upper().replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:295 (em module.main)
```

#### `tipo.upper` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_ausentes.py:295 (em module.main)
```

### 🔍 Objeto: `tipo_disp`

#### `tipo_disp.title` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:371 (em ExcelOrchestrator._fallback_tipo_indisponivel)
```

### 🔍 Objeto: `tipos_count`

#### `tipos_count.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:268 (em MetadataScanner.obter_tipos_campo_disponiveis)
```

### 🔍 Objeto: `tipos_distribuicao`

#### `tipos_distribuicao.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:297 (em MetadataScanner.obter_estatisticas_tabelas)
```

### 🔍 Objeto: `tipos_pergunta`

#### `tipos_pergunta.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:498 (em PatternLearner._classificar_tipo_pergunta)
```

### 🔍 Objeto: `todos_clientes`

#### `todos_clientes.add` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:562 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:569 (em ContextLoader._carregar_todos_clientes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/loaders/context_loader.py:574 (em ContextLoader._carregar_todos_clientes_sistema)
```

### 🔍 Objeto: `token`

#### `token.text` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:219 (em NLPEnhancedAnalyzer._tokenizar_spacy)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:220 (em NLPEnhancedAnalyzer._tokenizar_spacy)
```

#### `token.text.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:219 (em NLPEnhancedAnalyzer._tokenizar_spacy)
```

#### `token.is_stop` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:220 (em NLPEnhancedAnalyzer._tokenizar_spacy)
```

#### `token.is_punct` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/nlp_enhanced_analyzer.py:220 (em NLPEnhancedAnalyzer._tokenizar_spacy)
```

### 🔍 Objeto: `tokens_usage`

#### `tokens_usage.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:160 (em PerformanceAnalyzer.analyze_ai_performance)
```

### 🔍 Objeto: `traceback`

#### `traceback.format_exc` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:204 (em TesteIntegracaoCompleta.testar_modulo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:447 (em module.main)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_todos_modulos_completo.py:40 (em module.testar_modulo)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/coordinator_manager.py:180 (em CoordinatorManager._load_domain_agents)
```

#### `traceback.print_exc` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1492 (em MainOrchestrator._connect_modules)
```

### 🔍 Objeto: `tracker`

#### `tracker.visit` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:115 (em UninitializedVariableFinder.scan_file)
```

#### `tracker.used_vars` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:120 (em UninitializedVariableFinder.scan_file)
```

#### `tracker.imports` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:143 (em UninitializedVariableFinder._is_suspicious_usage)
```

#### `tracker.assignments` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:161 (em UninitializedVariableFinder._is_suspicious_usage)
```

#### `tracker.defined_vars` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:171 (em UninitializedVariableFinder._is_suspicious_usage)
```

### 🔍 Objeto: `transformation`

#### `transformation.get` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:404 (em DataProcessor._apply_transformation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:407 (em DataProcessor._apply_transformation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:409 (em DataProcessor._apply_transformation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:411 (em DataProcessor._apply_transformation)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:411 (em DataProcessor._apply_transformation)
```

### 🔍 Objeto: `transp`

#### `transp.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/enrichers/enricher_manager.py:237 (em EnricherManager._analyze_carriers)
```

### 🔍 Objeto: `transportadora`

#### `transportadora.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:380 (em DataProvider._serialize_transportadora)
```

#### `transportadora.razao_social` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:381 (em DataProvider._serialize_transportadora)
```

#### `transportadora.cidade` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:382 (em DataProvider._serialize_transportadora)
```

#### `transportadora.uf` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:383 (em DataProvider._serialize_transportadora)
```

#### `transportadora.cnpj` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:384 (em DataProvider._serialize_transportadora)
```

#### `transportadora.freteiro` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/providers/data_provider.py:385 (em DataProvider._serialize_transportadora)
```

### 🔍 Objeto: `transportadoras`

#### `transportadoras.items` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:328 (em ExcelFretes._criar_aba_transportadoras)
```

### 🔍 Objeto: `tree`

#### `tree.body` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:32 (em CircularDependencyMapper.extract_imports)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:103 (em CodeScanner._parse_forms_file)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:189 (em StructureScanner._parse_models_file)
```

### 🔍 Objeto: `trend`

#### `trend.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:738 (em IntelligenceProcessor._calculate_trend_strength)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:745 (em IntelligenceProcessor._determine_trend_direction)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:746 (em IntelligenceProcessor._determine_trend_direction)
```

### 🔍 Objeto: `type()`

#### `type().__name__` (15 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/teste_integracao_completa_todos_modulos.py:323 (em TesteIntegracaoCompleta.testar_fallbacks_mocks)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_imports_quebrados.py:211 (em ImportChecker.check_import)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:207 (em StructuralAnalyzer._analyze_data_types)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:536 (em IntelligenceProcessor._learn_from_processing)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:75 (em DataProcessor.process_data)
  ... e mais 10 ocorrências
```

### 🔍 Objeto: `type_counts`

#### `type_counts.most_common` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:391 (em AdaptiveLearning._detect_query_pattern)
```

### 🔍 Objeto: `type_node`

#### `type_node.value` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:332 (em StructureScanner._extract_column_type)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:332 (em StructureScanner._extract_column_type)
```

#### `type_node.attr` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:332 (em StructureScanner._extract_column_type)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:332 (em StructureScanner._extract_column_type)
```

#### `type_node.func` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:336 (em StructureScanner._extract_column_type)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:337 (em StructureScanner._extract_column_type)
```

#### `type_node.value.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:332 (em StructureScanner._extract_column_type)
```

#### `type_node.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:334 (em StructureScanner._extract_column_type)
```

#### `type_node.func.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:337 (em StructureScanner._extract_column_type)
```

### 🔍 Objeto: `types`

#### `types.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:208 (em StructuralAnalyzer._analyze_data_types)
```

### 🔍 Objeto: `uf`

#### `uf.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/domain/pedidos_mapper.py:169 (em PedidosMapper.map_query_to_filters)
```

### 🔍 Objeto: `uf_code`

#### `uf_code.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:178 (em QueryAnalyzer._extract_entities)
```

### 🔍 Objeto: `undefined_methods`

#### `undefined_methods.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:169 (em module.find_undefined_methods)
```

### 🔍 Objeto: `unique_commands`

#### `unique_commands.values` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/auto_command_processor.py:327 (em AutoCommandProcessor._detect_commands)
```

### 🔍 Objeto: `unique_cycles`

#### `unique_cycles.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:179 (em CircularDependencyMapper.analyze_circular_dependencies)
```

### 🔍 Objeto: `unique_domains`

#### `unique_domains.update` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:537 (em PerformanceAnalyzer._generate_behavior_insights)
```

### 🔍 Objeto: `unittest`

#### `unittest.TestCase` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:21 (em TestLoopPrevention.top-level)
```

#### `unittest.TestLoader().loadTestsFromTestCase` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:254 (em module.run_pre_commit_tests)
```

#### `unittest.TestLoader` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:254 (em module.run_pre_commit_tests)
```

#### `unittest.TextTestRunner` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/tests/test_loop_prevention.py:257 (em module.run_pre_commit_tests)
```

### 🔍 Objeto: `uptime`

#### `uptime.total_seconds` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics.py:200 (em ClaudeAIMetrics.get_usage_metrics)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/real_time_metrics_otimizado.py:200 (em ClaudeAIMetricsOptimized.get_usage_metrics)
```

#### `uptime.days` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:376 (em SystemMemory._calculate_uptime)
```

#### `uptime.seconds` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/memorizers/system_memory.py:377 (em SystemMemory._calculate_uptime)
```

### 🔍 Objeto: `uq`

#### `uq.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:233 (em MetadataScanner._obter_constraints_tabela)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/metadata_scanner.py:234 (em MetadataScanner._obter_constraints_tabela)
```

### 🔍 Objeto: `user`

#### `user.id` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:776 (em SessionOrchestrator._get_current_user_id)
```

### 🔍 Objeto: `user_behaviors`

#### `user_behaviors.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/performance_analyzer.py:290 (em PerformanceAnalyzer.analyze_user_behavior)
```

### 🔍 Objeto: `user_context`

#### `user_context.get` (11 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:191 (em SuggestionsEngine.get_intelligent_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:203 (em SuggestionsEngine.get_intelligent_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:232 (em SuggestionsEngine._generate_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:233 (em SuggestionsEngine._generate_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:234 (em SuggestionsEngine._generate_suggestions)
  ... e mais 6 ocorrências
```

#### `user_context.get().lower` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:232 (em SuggestionsEngine._generate_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:322 (em SuggestionsEngine._generate_data_based_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:490 (em SuggestionsEngine._get_fallback_suggestions)
```

### 🔍 Objeto: `user_feedback`

#### `user_feedback.lower().strip` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:130 (em MetacognitiveAnalyzer._interpret_user_feedback)
```

#### `user_feedback.lower` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:130 (em MetacognitiveAnalyzer._interpret_user_feedback)
```

### 🔍 Objeto: `user_profile`

#### `user_profile.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/__init__.py:191 (em module.get_suggestion_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:276 (em SuggestionsManager.get_suggestion_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:658 (em SuggestionsManager._generate_personalized_suggestions)
```

### 🔍 Objeto: `user_question`

#### `user_question.lower` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:211 (em ConversationContext.extract_metadata)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:219 (em ConversationContext.extract_metadata)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:224 (em ConversationContext.extract_metadata)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/conversers/context_converser.py:226 (em ConversationContext.extract_metadata)
```

### 🔍 Objeto: `utils`

#### `utils.validate` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:480 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:481 (em module.top-level)
```

#### `utils.validate_query` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:484 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:485 (em module.top-level)
```

#### `utils.validate_context` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:488 (em module.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:489 (em module.top-level)
```

### 🔍 Objeto: `uuid`

#### `uuid.uuid4` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:350 (em MainOrchestrator._generate_session_id)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/orchestrator_manager.py:220 (em OrchestratorManager.top-level)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:218 (em SessionOrchestrator.create_session)
```

#### `uuid.uuid4().hex` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:350 (em MainOrchestrator._generate_session_id)
```

### 🔍 Objeto: `v`

#### `v.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/validation_utils.py:414 (em BaseValidationUtils.get_validation_summary)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/processor_coordinator.py:280 (em ProcessorCoordinator.get_active_chains)
```

### 🔍 Objeto: `valid_suggestions`

#### `valid_suggestions.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:310 (em SuggestionsEngine._validate_suggestions_list)
```

### 🔍 Objeto: `validacao`

#### `validacao.get` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:346 (em DiagnosticsAnalyzer._gerar_recomendacoes_sistema)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:388 (em SemanticValidator._avaliar_qualidade_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:388 (em SemanticValidator._avaliar_qualidade_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:392 (em SemanticValidator._avaliar_qualidade_mapeamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:395 (em SemanticValidator._avaliar_qualidade_mapeamento)
  ... e mais 3 ocorrências
```

### 🔍 Objeto: `validation_result`

#### `validation_result.get` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:327 (em CriticAgent._generate_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/critic_validator.py:328 (em CriticAgent._generate_recommendations)
```

### 🔍 Objeto: `validations_to_run`

#### `validations_to_run.append` (7 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:420 (em ValidatorManager.run_full_validation_suite)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:424 (em ValidatorManager.run_full_validation_suite)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:428 (em ValidatorManager.run_full_validation_suite)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:429 (em ValidatorManager.run_full_validation_suite)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:432 (em ValidatorManager.run_full_validation_suite)
  ... e mais 2 ocorrências
```

### 🔍 Objeto: `validator`

#### `validator.validate_responses` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:200 (em ValidatorManager.validate_agent_responses)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:219 (em ValidatorManager.validate_agent_responses)
```

#### `validator.validate_all_modules` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validador_deep_profundo.py:476 (em module.top-level)
```

#### `validator.validar_consistencia_readme_banco` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/diagnostics_analyzer.py:277 (em DiagnosticsAnalyzer._avaliar_integracao)
```

#### `validator.validate` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/utils_manager.py:117 (em UtilsManager.validate)
```

#### `validator.validar_contexto_negocio` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:99 (em ValidatorManager.validate_context)
```

#### `validator.validar_mapeamento_completo` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:287 (em ValidatorManager.validate_complete_mapping)
```

#### `validator.__class__.__name__` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:365 (em ValidatorManager.get_validation_status)
```

#### `validator.__class__` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/validator_manager.py:365 (em ValidatorManager.get_validation_status)
```

### 🔍 Objeto: `validator_path`

#### `validator_path.exists` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:150 (em CursorMonitor.run_validator)
```

### 🔍 Objeto: `validator_result`

#### `validator_result.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/monitoring/cursor_monitor.py:249 (em CursorMonitor.display_status)
```

### 🔍 Objeto: `validators`

#### `validators.append` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:197 (em CodeScanner._extract_validators)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:199 (em CodeScanner._extract_validators)
```

### 🔍 Objeto: `validators_node`

#### `validators_node.elts` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:194 (em CodeScanner._extract_validators)
```

### 🔍 Objeto: `valor`

#### `valor.upper` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/validators/semantic_validator.py:128 (em SemanticValidator.validar_contexto_negocio)
```

### 🔍 Objeto: `valor_match`

#### `valor_match.group().replace().replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:162 (em BaseCommand._extract_filters_advanced)
```

#### `valor_match.group().replace` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:162 (em BaseCommand._extract_filters_advanced)
```

#### `valor_match.group` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/base_command.py:162 (em BaseCommand._extract_filters_advanced)
```

### 🔍 Objeto: `value`

#### `value.strip` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/verificar_dependencias_sistema.py:86 (em DependencyChecker.check_pip_package)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:390 (em IntelligenceProcessor._normalize_dict_for_intelligence)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:385 (em DataProcessor._clean_dict)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/data_processor.py:477 (em DataProcessor._normalize_dict)
```

#### `value.value` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:213 (em CodeScanner._extract_dict_value)
```

#### `value.startswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1500 (em MainOrchestrator._resolve_parameters)
```

#### `value.endswith` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1500 (em MainOrchestrator._resolve_parameters)
```

### 🔍 Objeto: `value_node`

#### `value_node.func` (8 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:170 (em CodeScanner._extract_form_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:171 (em CodeScanner._extract_form_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:172 (em CodeScanner._extract_form_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:173 (em CodeScanner._extract_form_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:280 (em StructureScanner._extract_field_info)
  ... e mais 3 ocorrências
```

#### `value_node.value` (6 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:236 (em CodeScanner._extract_simple_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:346 (em StructureScanner._extract_boolean_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:348 (em StructureScanner._extract_boolean_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:357 (em StructureScanner._extract_string_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:368 (em StructureScanner._extract_value)
  ... e mais 1 ocorrências
```

#### `value_node.args` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:286 (em StructureScanner._extract_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:287 (em StructureScanner._extract_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:302 (em StructureScanner._extract_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:303 (em StructureScanner._extract_field_info)
```

#### `value_node.keywords` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:176 (em CodeScanner._extract_form_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:291 (em StructureScanner._extract_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:310 (em StructureScanner._extract_field_info)
```

#### `value_node.s` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:238 (em CodeScanner._extract_simple_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:359 (em StructureScanner._extract_string_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:370 (em StructureScanner._extract_value)
```

#### `value_node.func.id` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:171 (em CodeScanner._extract_form_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:321 (em StructureScanner._extract_field_info)
```

#### `value_node.func.attr` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:173 (em CodeScanner._extract_form_field_info)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:281 (em StructureScanner._extract_field_info)
```

#### `value_node.n` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/code_scanner.py:240 (em CodeScanner._extract_simple_value)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/structure_scanner.py:372 (em StructureScanner._extract_value)
```

### 🔍 Objeto: `var_name`

#### `var_name.startswith` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_variaveis_nao_inicializadas.py:182 (em UninitializedVariableFinder._identify_pattern)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:98 (em FileScanner._extract_template_variables)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:98 (em FileScanner._extract_template_variables)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:114 (em FileScanner._extract_template_variables)
```

### 🔍 Objeto: `variables`

#### `variables.add` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:99 (em FileScanner._extract_template_variables)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:107 (em FileScanner._extract_template_variables)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/file_scanner.py:115 (em FileScanner._extract_template_variables)
```

### 🔍 Objeto: `violations`

#### `violations.append` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:104 (em StructuralAnalyzer.validate_architecture)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:108 (em StructuralAnalyzer.validate_architecture)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/structural_analyzer.py:112 (em StructuralAnalyzer.validate_architecture)
```

### 🔍 Objeto: `visitadas`

#### `visitadas.add` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:323 (em RelationshipMapper._explorar_cluster)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/scanning/database/relationship_mapper.py:391 (em RelationshipMapper.obter_caminho_relacionamentos)
```

### 🔍 Objeto: `visited`

#### `visited.add` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_dependencias_circulares.py:130 (em CircularDependencyMapper.dfs)
```

### 🔍 Objeto: `visitor`

#### `visitor.visit` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:101 (em module.analyze_file)
```

#### `visitor.method_calls` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:105 (em module.analyze_file)
```

#### `visitor.defined_methods` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:106 (em module.analyze_file)
```

#### `visitor.imported_names` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mapear_metodos_inexistentes.py:107 (em module.analyze_file)
```

### 🔍 Objeto: `vocabulario_dominio`

#### `vocabulario_dominio.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/pattern_learning.py:394 (em PatternLearner._extrair_palavras_chave_dominio)
```

### 🔍 Objeto: `w`

#### `w.isupper` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/metacognitive_analyzer.py:55 (em MetacognitiveAnalyzer._assess_query_complexity)
```

### 🔍 Objeto: `wb`

#### `wb.create_sheet` (15 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:258 (em ExcelOrchestrator._gerar_excel_geral_multi)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:267 (em ExcelOrchestrator._gerar_excel_geral_multi)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:276 (em ExcelOrchestrator._gerar_excel_geral_multi)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:284 (em ExcelOrchestrator._gerar_excel_geral_multi)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:172 (em ExcelFretes._criar_excel_fretes)
  ... e mais 10 ocorrências
```

#### `wb.active` (10 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:250 (em ExcelOrchestrator._gerar_excel_geral_multi)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:251 (em ExcelOrchestrator._gerar_excel_geral_multi)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:168 (em ExcelFretes._criar_excel_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:169 (em ExcelFretes._criar_excel_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:215 (em ExcelPedidos._criar_excel_pedidos)
  ... e mais 5 ocorrências
```

#### `wb.remove` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:251 (em ExcelOrchestrator._gerar_excel_geral_multi)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:169 (em ExcelFretes._criar_excel_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:216 (em ExcelPedidos._criar_excel_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:151 (em ExcelFaturamento._criar_excel_faturamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:178 (em ExcelEntregas._criar_excel_entregas)
```

#### `wb.save` (5 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:292 (em ExcelOrchestrator._gerar_excel_geral_multi)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:187 (em ExcelFretes._criar_excel_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:234 (em ExcelPedidos._criar_excel_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:165 (em ExcelFaturamento._criar_excel_faturamento)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:196 (em ExcelEntregas._criar_excel_entregas)
```

### 🔍 Objeto: `weaknesses`

#### `weaknesses.append` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/processors/intelligence_processor.py:687 (em IntelligenceProcessor._evaluate_option)
```

### 🔍 Objeto: `weekly_feedback`

#### `weekly_feedback.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:366 (em HumanInLoopLearning._analyze_trends)
```

#### `weekly_feedback.keys` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:369 (em HumanInLoopLearning._analyze_trends)
```

### 🔍 Objeto: `weights`

#### `weights.get` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/human_in_loop_learning.py:414 (em HumanInLoopLearning._calculate_satisfaction_score)
```

### 🔍 Objeto: `word`

#### `word.upper` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/analyzers/query_analyzer.py:174 (em QueryAnalyzer._extract_entities)
```

### 🔍 Objeto: `workflow`

#### `workflow.copy` (1 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/main_orchestrator.py:1025 (em MainOrchestrator.top-level)
```

### 🔍 Objeto: `workflow_data`

#### `workflow_data.get` (10 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:405 (em SessionOrchestrator._execute_learning_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:405 (em SessionOrchestrator._execute_learning_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:406 (em SessionOrchestrator._execute_learning_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:406 (em SessionOrchestrator._execute_learning_workflow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/orchestrators/session_orchestrator.py:408 (em SessionOrchestrator._execute_learning_workflow)
  ... e mais 5 ocorrências
```

### 🔍 Objeto: `workflow_result`

#### `workflow_result.get` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:114 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:115 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:118 (em module.run_complete_flow)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/testar_fluxo_completo_e2e_revisado.py:120 (em module.run_complete_flow)
```

### 🔍 Objeto: `ws`

#### `ws.cell` (127 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:327 (em ExcelOrchestrator._criar_aba_resumo_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:328 (em ExcelOrchestrator._criar_aba_resumo_fretes)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:333 (em ExcelOrchestrator._criar_aba_resumo_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:334 (em ExcelOrchestrator._criar_aba_resumo_pedidos)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel_command_manager.py:339 (em ExcelOrchestrator._criar_aba_resumo_entregas)
  ... e mais 122 ocorrências
```

#### `ws.columns` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:412 (em ExcelFretes._auto_ajustar_colunas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:444 (em ExcelPedidos._auto_ajustar_colunas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:301 (em ExcelFaturamento._auto_ajustar_colunas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:446 (em ExcelEntregas._auto_ajustar_colunas)
```

#### `ws.column_dimensions` (4 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/fretes.py:424 (em ExcelFretes._auto_ajustar_colunas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/pedidos.py:456 (em ExcelPedidos._auto_ajustar_colunas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/faturamento.py:313 (em ExcelFaturamento._auto_ajustar_colunas)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/commands/excel/entregas.py:458 (em ExcelEntregas._auto_ajustar_colunas)
```

### 🔍 Objeto: `x`

#### `x.get` (3 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestions_manager.py:456 (em SuggestionsManager._prioritize_suggestions)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/learners/adaptive_learning.py:486 (em AdaptiveLearning._rank_recommendations)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/coordinators/intelligence_coordinator.py:838 (em IntelligenceCoordinator._best_result_synthesis)
```

#### `x.priority` (2 ocorrências)
```
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/mappers/context_mapper.py:87 (em ContextMapper.map_context)
  /home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/suggestions/suggestion_engine.py:264 (em SuggestionsEngine._generate_suggestions)
```


## 🎯 PROBLEMAS CONHECIDOS IDENTIFICADOS
