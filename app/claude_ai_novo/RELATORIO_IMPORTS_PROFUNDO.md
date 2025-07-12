# 🔍 RELATÓRIO DE VERIFICAÇÃO PROFUNDA DE IMPORTS

**Data**: 2025-07-12 19:01:27

**Total de arquivos**: 178
**Arquivos com problemas**: 121
**Imports quebrados**: 831
**Placeholders encontrados**: 68

## ❌ IMPORTS QUEBRADOS

### detector_modulos_orfaos.py:403
- **Import**: `traceback`
- **Contexto**: function:main > in_except
- ⚠️ **Dentro de função**

### detector_modulos_orfaos.py:403
- **Import**: `traceback`
- **Contexto**: function:main
- ⚠️ **Dentro de função**

### pre_commit_check.py:9
- **Import**: `subprocess`
- **Contexto**: module_level

### simular_producao.py:8
- **Import**: `time`
- **Contexto**: module_level

### simular_producao.py:10
- **Import**: `threading`
- **Contexto**: module_level

### simular_producao.py:12
- **Import**: `traceback`
- **Contexto**: module_level

### testar_todos_modulos_completo.py:9
- **Import**: `importlib`
- **Contexto**: module_level

### testar_todos_modulos_completo.py:10
- **Import**: `traceback`
- **Contexto**: module_level

### teste_integracao_completa_todos_modulos.py:13
- **Import**: `traceback`
- **Contexto**: module_level

### validador_deep_profundo.py:17
- **Import**: `traceback`
- **Contexto**: module_level

### validador_deep_profundo.py:18
- **Import**: `importlib`
- **Contexto**: module_level

### validador_sistema_completo.py:13
- **Import**: `traceback`
- **Contexto**: module_level

### validador_sistema_completo.py:14
- **Import**: `importlib`
- **Contexto**: module_level

### validador_sistema_completo.py:18
- **Import**: `subprocess`
- **Contexto**: module_level

### validador_sistema_completo.py:19
- **Import**: `time`
- **Contexto**: module_level

### validador_sistema_real.py:14
- **Import**: `traceback`
- **Contexto**: module_level

### validador_sistema_real.py:15
- **Import**: `importlib`
- **Contexto**: module_level

### validador_sistema_real.py:88
- **Import**: `app` (from ... import create_app)
- **Contexto**: class:ValidadorSistemaReal > function:_test_flask_app_import > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### validador_sistema_real.py:88
- **Import**: `app` (from ... import create_app)
- **Contexto**: class:ValidadorSistemaReal > function:_test_flask_app_import
- ⚠️ **Dentro de função**

### verificar_imports_quebrados.py:10
- **Import**: `importlib`
- **Contexto**: module_level

### verificar_imports_quebrados.py:11
- **Import**: `traceback`
- **Contexto**: module_level

### verificar_sistema_ativo.py:146
- **Import**: `app` (from ... import db)
- **Contexto**: function:diagnosticar_problemas > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### verificar_sistema_ativo.py:146
- **Import**: `app` (from ... import db)
- **Contexto**: function:diagnosticar_problemas
- ⚠️ **Dentro de função**

### verificar_sistema_producao.py:48
- **Import**: `traceback`
- **Contexto**: function:verificar_configuracao > in_except
- ⚠️ **Dentro de função**

### verificar_sistema_producao.py:48
- **Import**: `traceback`
- **Contexto**: function:verificar_configuracao
- ⚠️ **Dentro de função**

### __init__.py:312
- **Import**: `app` (from ... import db)
- **Contexto**: function:get_claude_ai_instance > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### __init__.py:313
- **Import**: `app.claude_ai_novo.integration.claude.claude_client` (from ... import get_claude_client)
- **Contexto**: function:get_claude_ai_instance > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### __init__.py:312
- **Import**: `app` (from ... import db)
- **Contexto**: function:get_claude_ai_instance
- ⚠️ **Dentro de função**

### __init__.py:313
- **Import**: `app.claude_ai_novo.integration.claude.claude_client` (from ... import get_claude_client)
- **Contexto**: function:get_claude_ai_instance
- ⚠️ **Dentro de função**

### analyzers\nlp_enhanced_analyzer.py:9
- **Import**: `dataclasses` (from ... import dataclass)
- **Contexto**: module_level

### analyzers\nlp_enhanced_analyzer.py:14
- **Import**: `spacy`
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\nlp_enhanced_analyzer.py:15
- **Import**: `spacy.lang.pt.stop_words` (from ... import STOP_WORDS)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\nlp_enhanced_analyzer.py:14
- **Import**: `spacy`
- **Contexto**: module_level

### analyzers\nlp_enhanced_analyzer.py:15
- **Import**: `spacy.lang.pt.stop_words` (from ... import STOP_WORDS)
- **Contexto**: module_level

### analyzers\nlp_enhanced_analyzer.py:30
- **Import**: `fuzzywuzzy` (from ... import fuzz)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\nlp_enhanced_analyzer.py:30
- **Import**: `fuzzywuzzy` (from ... import process)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\nlp_enhanced_analyzer.py:30
- **Import**: `fuzzywuzzy` (from ... import fuzz)
- **Contexto**: module_level

### analyzers\nlp_enhanced_analyzer.py:30
- **Import**: `fuzzywuzzy` (from ... import process)
- **Contexto**: module_level

### analyzers\nlp_enhanced_analyzer.py:37
- **Import**: `nltk`
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\nlp_enhanced_analyzer.py:38
- **Import**: `nltk.corpus` (from ... import stopwords)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\nlp_enhanced_analyzer.py:37
- **Import**: `nltk`
- **Contexto**: module_level

### analyzers\nlp_enhanced_analyzer.py:38
- **Import**: `nltk.corpus` (from ... import stopwords)
- **Contexto**: module_level

### analyzers\performance_analyzer.py:15
- **Import**: `statistics`
- **Contexto**: module_level

### analyzers\query_analyzer.py:12
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: module_level

### analyzers\query_analyzer.py:14
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### analyzers\query_analyzer.py:23
- **Import**: `time`
- **Contexto**: module_level

### analyzers\__init__.py:22
- **Import**: `intention_analyzer` (from ... import IntentionAnalyzer)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\__init__.py:23
- **Import**: `query_analyzer` (from ... import QueryAnalyzer)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\__init__.py:24
- **Import**: `metacognitive_analyzer` (from ... import MetacognitiveAnalyzer)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\__init__.py:25
- **Import**: `nlp_enhanced_analyzer` (from ... import NLPEnhancedAnalyzer)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\__init__.py:26
- **Import**: `analyzer_manager` (from ... import AnalyzerManager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\__init__.py:27
- **Import**: `diagnostics_analyzer` (from ... import DiagnosticsAnalyzer)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\__init__.py:27
- **Import**: `diagnostics_analyzer` (from ... import get_diagnostics_analyzer)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\__init__.py:28
- **Import**: `structural_analyzer` (from ... import StructuralAnalyzer)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\__init__.py:28
- **Import**: `structural_analyzer` (from ... import get_structural_analyzer)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\__init__.py:29
- **Import**: `semantic_analyzer` (from ... import SemanticAnalyzer)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\__init__.py:29
- **Import**: `semantic_analyzer` (from ... import get_semantic_analyzer)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\__init__.py:30
- **Import**: `performance_analyzer` (from ... import PerformanceAnalyzer)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\__init__.py:30
- **Import**: `performance_analyzer` (from ... import get_performance_analyzer)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### analyzers\__init__.py:22
- **Import**: `intention_analyzer` (from ... import IntentionAnalyzer)
- **Contexto**: module_level

### analyzers\__init__.py:23
- **Import**: `query_analyzer` (from ... import QueryAnalyzer)
- **Contexto**: module_level

### analyzers\__init__.py:24
- **Import**: `metacognitive_analyzer` (from ... import MetacognitiveAnalyzer)
- **Contexto**: module_level

### analyzers\__init__.py:25
- **Import**: `nlp_enhanced_analyzer` (from ... import NLPEnhancedAnalyzer)
- **Contexto**: module_level

### analyzers\__init__.py:26
- **Import**: `analyzer_manager` (from ... import AnalyzerManager)
- **Contexto**: module_level

### analyzers\__init__.py:27
- **Import**: `diagnostics_analyzer` (from ... import DiagnosticsAnalyzer)
- **Contexto**: module_level

### analyzers\__init__.py:27
- **Import**: `diagnostics_analyzer` (from ... import get_diagnostics_analyzer)
- **Contexto**: module_level

### analyzers\__init__.py:28
- **Import**: `structural_analyzer` (from ... import StructuralAnalyzer)
- **Contexto**: module_level

### analyzers\__init__.py:28
- **Import**: `structural_analyzer` (from ... import get_structural_analyzer)
- **Contexto**: module_level

### analyzers\__init__.py:29
- **Import**: `semantic_analyzer` (from ... import SemanticAnalyzer)
- **Contexto**: module_level

### analyzers\__init__.py:29
- **Import**: `semantic_analyzer` (from ... import get_semantic_analyzer)
- **Contexto**: module_level

### analyzers\__init__.py:30
- **Import**: `performance_analyzer` (from ... import PerformanceAnalyzer)
- **Contexto**: module_level

### analyzers\__init__.py:30
- **Import**: `performance_analyzer` (from ... import get_performance_analyzer)
- **Contexto**: module_level

### analyzers\__init__.py:116
- **Import**: `diagnostics_analyzer` (from ... import DiagnosticsAnalyzer)
- **Contexto**: function:get_diagnostics_analyzer > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### analyzers\__init__.py:116
- **Import**: `diagnostics_analyzer` (from ... import DiagnosticsAnalyzer)
- **Contexto**: function:get_diagnostics_analyzer
- ⚠️ **Dentro de função**

### analyzers\__init__.py:129
- **Import**: `performance_analyzer` (from ... import PerformanceAnalyzer)
- **Contexto**: function:get_performance_analyzer > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### analyzers\__init__.py:129
- **Import**: `performance_analyzer` (from ... import PerformanceAnalyzer)
- **Contexto**: function:get_performance_analyzer
- ⚠️ **Dentro de função**

### commands\base_command.py:11
- **Import**: `time`
- **Contexto**: module_level

### commands\base_command.py:21
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: module_level

### commands\base_command.py:25
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### commands\base_command.py:60
- **Import**: `tempfile`
- **Contexto**: class:BaseCommand > function:__init__ > in_except
- ⚠️ **Dentro de função**

### commands\base_command.py:60
- **Import**: `tempfile`
- **Contexto**: class:BaseCommand > function:__init__
- ⚠️ **Dentro de função**

### commands\excel_command_manager.py:240
- **Import**: `openpyxl` (from ... import Workbook)
- **Contexto**: class:ExcelOrchestrator > function:_gerar_excel_geral_multi > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### commands\excel_command_manager.py:241
- **Import**: `openpyxl.styles` (from ... import Font)
- **Contexto**: class:ExcelOrchestrator > function:_gerar_excel_geral_multi > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### commands\excel_command_manager.py:241
- **Import**: `openpyxl.styles` (from ... import PatternFill)
- **Contexto**: class:ExcelOrchestrator > function:_gerar_excel_geral_multi > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### commands\excel_command_manager.py:240
- **Import**: `openpyxl` (from ... import Workbook)
- **Contexto**: class:ExcelOrchestrator > function:_gerar_excel_geral_multi
- ⚠️ **Dentro de função**

### commands\excel_command_manager.py:241
- **Import**: `openpyxl.styles` (from ... import Font)
- **Contexto**: class:ExcelOrchestrator > function:_gerar_excel_geral_multi
- ⚠️ **Dentro de função**

### commands\excel_command_manager.py:241
- **Import**: `openpyxl.styles` (from ... import PatternFill)
- **Contexto**: class:ExcelOrchestrator > function:_gerar_excel_geral_multi
- ⚠️ **Dentro de função**

### commands\__init__.py:11
- **Import**: `importlib`
- **Contexto**: module_level

### commands\__init__.py:187
- **Import**: `excel_command_manager` (from ... import ExcelOrchestrator)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:187
- **Import**: `excel_command_manager` (from ... import get_excel_orchestrator)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:187
- **Import**: `excel_command_manager` (from ... import ExcelOrchestrator)
- **Contexto**: module_level

### commands\__init__.py:187
- **Import**: `excel_command_manager` (from ... import get_excel_orchestrator)
- **Contexto**: module_level

### commands\__init__.py:194
- **Import**: `cursor_commands` (from ... import CursorCommands)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:194
- **Import**: `cursor_commands` (from ... import get_cursor_commands)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:194
- **Import**: `cursor_commands` (from ... import CursorCommands)
- **Contexto**: module_level

### commands\__init__.py:194
- **Import**: `cursor_commands` (from ... import get_cursor_commands)
- **Contexto**: module_level

### commands\__init__.py:201
- **Import**: `dev_commands` (from ... import DevCommands)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:201
- **Import**: `dev_commands` (from ... import get_dev_commands)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:201
- **Import**: `dev_commands` (from ... import DevCommands)
- **Contexto**: module_level

### commands\__init__.py:201
- **Import**: `dev_commands` (from ... import get_dev_commands)
- **Contexto**: module_level

### commands\__init__.py:208
- **Import**: `file_commands` (from ... import FileCommands)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:208
- **Import**: `file_commands` (from ... import get_file_commands)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:208
- **Import**: `file_commands` (from ... import FileCommands)
- **Contexto**: module_level

### commands\__init__.py:208
- **Import**: `file_commands` (from ... import get_file_commands)
- **Contexto**: module_level

### commands\__init__.py:215
- **Import**: `excel` (from ... import ExcelFretes)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:215
- **Import**: `excel` (from ... import ExcelPedidos)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:215
- **Import**: `excel` (from ... import ExcelEntregas)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:215
- **Import**: `excel` (from ... import ExcelFaturamento)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:215
- **Import**: `excel` (from ... import get_excel_fretes)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:215
- **Import**: `excel` (from ... import get_excel_pedidos)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:215
- **Import**: `excel` (from ... import get_excel_entregas)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:215
- **Import**: `excel` (from ... import get_excel_faturamento)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\__init__.py:215
- **Import**: `excel` (from ... import ExcelFretes)
- **Contexto**: module_level

### commands\__init__.py:215
- **Import**: `excel` (from ... import ExcelPedidos)
- **Contexto**: module_level

### commands\__init__.py:215
- **Import**: `excel` (from ... import ExcelEntregas)
- **Contexto**: module_level

### commands\__init__.py:215
- **Import**: `excel` (from ... import ExcelFaturamento)
- **Contexto**: module_level

### commands\__init__.py:215
- **Import**: `excel` (from ... import get_excel_fretes)
- **Contexto**: module_level

### commands\__init__.py:215
- **Import**: `excel` (from ... import get_excel_pedidos)
- **Contexto**: module_level

### commands\__init__.py:215
- **Import**: `excel` (from ... import get_excel_entregas)
- **Contexto**: module_level

### commands\__init__.py:215
- **Import**: `excel` (from ... import get_excel_faturamento)
- **Contexto**: module_level

### commands\__init__.py:308
- **Import**: `auto_command_processor` (from ... import get_auto_command_processor)
- **Contexto**: function:get_command_manager
- ⚠️ **Dentro de função**

### commands\excel\entregas.py:15
- **Import**: `openpyxl` (from ... import Workbook)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\entregas.py:16
- **Import**: `openpyxl.styles` (from ... import Font)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\entregas.py:16
- **Import**: `openpyxl.styles` (from ... import PatternFill)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\entregas.py:16
- **Import**: `openpyxl.styles` (from ... import Border)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\entregas.py:16
- **Import**: `openpyxl.styles` (from ... import Side)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\entregas.py:16
- **Import**: `openpyxl.styles` (from ... import Alignment)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\entregas.py:17
- **Import**: `openpyxl.utils` (from ... import get_column_letter)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\entregas.py:15
- **Import**: `openpyxl` (from ... import Workbook)
- **Contexto**: module_level

### commands\excel\entregas.py:16
- **Import**: `openpyxl.styles` (from ... import Font)
- **Contexto**: module_level

### commands\excel\entregas.py:16
- **Import**: `openpyxl.styles` (from ... import PatternFill)
- **Contexto**: module_level

### commands\excel\entregas.py:16
- **Import**: `openpyxl.styles` (from ... import Border)
- **Contexto**: module_level

### commands\excel\entregas.py:16
- **Import**: `openpyxl.styles` (from ... import Side)
- **Contexto**: module_level

### commands\excel\entregas.py:16
- **Import**: `openpyxl.styles` (from ... import Alignment)
- **Contexto**: module_level

### commands\excel\entregas.py:17
- **Import**: `openpyxl.utils` (from ... import get_column_letter)
- **Contexto**: module_level

### commands\excel\faturamento.py:16
- **Import**: `openpyxl` (from ... import Workbook)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\faturamento.py:17
- **Import**: `openpyxl.styles` (from ... import Font)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\faturamento.py:17
- **Import**: `openpyxl.styles` (from ... import PatternFill)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\faturamento.py:17
- **Import**: `openpyxl.styles` (from ... import Border)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\faturamento.py:17
- **Import**: `openpyxl.styles` (from ... import Side)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\faturamento.py:17
- **Import**: `openpyxl.styles` (from ... import Alignment)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\faturamento.py:18
- **Import**: `openpyxl.utils` (from ... import get_column_letter)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\faturamento.py:16
- **Import**: `openpyxl` (from ... import Workbook)
- **Contexto**: module_level

### commands\excel\faturamento.py:17
- **Import**: `openpyxl.styles` (from ... import Font)
- **Contexto**: module_level

### commands\excel\faturamento.py:17
- **Import**: `openpyxl.styles` (from ... import PatternFill)
- **Contexto**: module_level

### commands\excel\faturamento.py:17
- **Import**: `openpyxl.styles` (from ... import Border)
- **Contexto**: module_level

### commands\excel\faturamento.py:17
- **Import**: `openpyxl.styles` (from ... import Side)
- **Contexto**: module_level

### commands\excel\faturamento.py:17
- **Import**: `openpyxl.styles` (from ... import Alignment)
- **Contexto**: module_level

### commands\excel\faturamento.py:18
- **Import**: `openpyxl.utils` (from ... import get_column_letter)
- **Contexto**: module_level

### commands\excel\fretes.py:15
- **Import**: `openpyxl` (from ... import Workbook)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\fretes.py:16
- **Import**: `openpyxl.styles` (from ... import Font)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\fretes.py:16
- **Import**: `openpyxl.styles` (from ... import PatternFill)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\fretes.py:16
- **Import**: `openpyxl.styles` (from ... import Border)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\fretes.py:16
- **Import**: `openpyxl.styles` (from ... import Side)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\fretes.py:16
- **Import**: `openpyxl.styles` (from ... import Alignment)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\fretes.py:17
- **Import**: `openpyxl.utils` (from ... import get_column_letter)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\fretes.py:15
- **Import**: `openpyxl` (from ... import Workbook)
- **Contexto**: module_level

### commands\excel\fretes.py:16
- **Import**: `openpyxl.styles` (from ... import Font)
- **Contexto**: module_level

### commands\excel\fretes.py:16
- **Import**: `openpyxl.styles` (from ... import PatternFill)
- **Contexto**: module_level

### commands\excel\fretes.py:16
- **Import**: `openpyxl.styles` (from ... import Border)
- **Contexto**: module_level

### commands\excel\fretes.py:16
- **Import**: `openpyxl.styles` (from ... import Side)
- **Contexto**: module_level

### commands\excel\fretes.py:16
- **Import**: `openpyxl.styles` (from ... import Alignment)
- **Contexto**: module_level

### commands\excel\fretes.py:17
- **Import**: `openpyxl.utils` (from ... import get_column_letter)
- **Contexto**: module_level

### commands\excel\pedidos.py:19
- **Import**: `openpyxl` (from ... import Workbook)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\pedidos.py:20
- **Import**: `openpyxl.styles` (from ... import Font)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\pedidos.py:20
- **Import**: `openpyxl.styles` (from ... import PatternFill)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\pedidos.py:20
- **Import**: `openpyxl.styles` (from ... import Border)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\pedidos.py:20
- **Import**: `openpyxl.styles` (from ... import Side)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\pedidos.py:20
- **Import**: `openpyxl.styles` (from ... import Alignment)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\pedidos.py:21
- **Import**: `openpyxl.utils` (from ... import get_column_letter)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\pedidos.py:19
- **Import**: `openpyxl` (from ... import Workbook)
- **Contexto**: module_level

### commands\excel\pedidos.py:20
- **Import**: `openpyxl.styles` (from ... import Font)
- **Contexto**: module_level

### commands\excel\pedidos.py:20
- **Import**: `openpyxl.styles` (from ... import PatternFill)
- **Contexto**: module_level

### commands\excel\pedidos.py:20
- **Import**: `openpyxl.styles` (from ... import Border)
- **Contexto**: module_level

### commands\excel\pedidos.py:20
- **Import**: `openpyxl.styles` (from ... import Side)
- **Contexto**: module_level

### commands\excel\pedidos.py:20
- **Import**: `openpyxl.styles` (from ... import Alignment)
- **Contexto**: module_level

### commands\excel\pedidos.py:21
- **Import**: `openpyxl.utils` (from ... import get_column_letter)
- **Contexto**: module_level

### commands\excel\__init__.py:9
- **Import**: `fretes` (from ... import ExcelFretes)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\__init__.py:9
- **Import**: `fretes` (from ... import get_excel_fretes)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\__init__.py:9
- **Import**: `fretes` (from ... import ExcelFretes)
- **Contexto**: module_level

### commands\excel\__init__.py:9
- **Import**: `fretes` (from ... import get_excel_fretes)
- **Contexto**: module_level

### commands\excel\__init__.py:15
- **Import**: `pedidos` (from ... import ExcelPedidos)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\__init__.py:15
- **Import**: `pedidos` (from ... import get_excel_pedidos)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\__init__.py:15
- **Import**: `pedidos` (from ... import ExcelPedidos)
- **Contexto**: module_level

### commands\excel\__init__.py:15
- **Import**: `pedidos` (from ... import get_excel_pedidos)
- **Contexto**: module_level

### commands\excel\__init__.py:21
- **Import**: `entregas` (from ... import ExcelEntregas)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\__init__.py:21
- **Import**: `entregas` (from ... import get_excel_entregas)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\__init__.py:21
- **Import**: `entregas` (from ... import ExcelEntregas)
- **Contexto**: module_level

### commands\excel\__init__.py:21
- **Import**: `entregas` (from ... import get_excel_entregas)
- **Contexto**: module_level

### commands\excel\__init__.py:27
- **Import**: `faturamento` (from ... import ExcelFaturamento)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\__init__.py:27
- **Import**: `faturamento` (from ... import get_excel_faturamento)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### commands\excel\__init__.py:27
- **Import**: `faturamento` (from ... import ExcelFaturamento)
- **Contexto**: module_level

### commands\excel\__init__.py:27
- **Import**: `faturamento` (from ... import get_excel_faturamento)
- **Contexto**: module_level

### config\advanced_config.py:7
- **Import**: `basic_config` (from ... import ClaudeAIConfig)
- **Contexto**: module_level

### config\advanced_config.py:8
- **Import**: `system_config` (from ... import get_system_config)
- **Contexto**: module_level

### config\system_config.py:724
- **Import**: `fnmatch`
- **Contexto**: class:SystemConfig > function:_key_matches_pattern
- ⚠️ **Dentro de função**

### config\__init__.py:15
- **Import**: `advanced_config` (from ... import AdvancedConfig)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### config\__init__.py:15
- **Import**: `advanced_config` (from ... import get_advanced_config)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### config\__init__.py:15
- **Import**: `advanced_config` (from ... import AdvancedConfig)
- **Contexto**: module_level

### config\__init__.py:15
- **Import**: `advanced_config` (from ... import get_advanced_config)
- **Contexto**: module_level

### config\__init__.py:22
- **Import**: `system_config` (from ... import SystemConfig)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### config\__init__.py:22
- **Import**: `system_config` (from ... import get_system_config)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### config\__init__.py:22
- **Import**: `system_config` (from ... import SystemConfig)
- **Contexto**: module_level

### config\__init__.py:22
- **Import**: `system_config` (from ... import get_system_config)
- **Contexto**: module_level

### config\__init__.py:47
- **Import**: `advanced_config` (from ... import AdvancedConfig)
- **Contexto**: function:get_advanced_config > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### config\__init__.py:47
- **Import**: `advanced_config` (from ... import AdvancedConfig)
- **Contexto**: function:get_advanced_config
- ⚠️ **Dentro de função**

### config\__init__.py:71
- **Import**: `system_config` (from ... import SystemConfig)
- **Contexto**: function:get_system_config > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### config\__init__.py:71
- **Import**: `system_config` (from ... import SystemConfig)
- **Contexto**: function:get_system_config
- ⚠️ **Dentro de função**

### conversers\context_converser.py:11
- **Import**: `dataclasses` (from ... import dataclass)
- **Contexto**: module_level

### conversers\context_converser.py:11
- **Import**: `dataclasses` (from ... import asdict)
- **Contexto**: module_level

### coordinators\coordinator_manager.py:12
- **Import**: `enum` (from ... import Enum)
- **Contexto**: module_level

### coordinators\coordinator_manager.py:87
- **Import**: `intelligence_coordinator` (from ... import get_intelligence_coordinator)
- **Contexto**: class:CoordinatorManager > function:_load_intelligence_coordinator > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### coordinators\coordinator_manager.py:87
- **Import**: `intelligence_coordinator` (from ... import get_intelligence_coordinator)
- **Contexto**: class:CoordinatorManager > function:_load_intelligence_coordinator
- ⚠️ **Dentro de função**

### coordinators\coordinator_manager.py:105
- **Import**: `processor_coordinator` (from ... import ProcessorCoordinator)
- **Contexto**: class:CoordinatorManager > function:_load_processor_coordinator > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### coordinators\coordinator_manager.py:105
- **Import**: `processor_coordinator` (from ... import ProcessorCoordinator)
- **Contexto**: class:CoordinatorManager > function:_load_processor_coordinator
- ⚠️ **Dentro de função**

### coordinators\coordinator_manager.py:121
- **Import**: `specialist_agents` (from ... import SpecialistAgent)
- **Contexto**: class:CoordinatorManager > function:_load_specialist_coordinator > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### coordinators\coordinator_manager.py:121
- **Import**: `specialist_agents` (from ... import SpecialistAgent)
- **Contexto**: class:CoordinatorManager > function:_load_specialist_coordinator
- ⚠️ **Dentro de função**

### coordinators\intelligence_coordinator.py:13
- **Import**: `concurrent.futures` (from ... import ThreadPoolExecutor)
- **Contexto**: module_level

### coordinators\intelligence_coordinator.py:13
- **Import**: `concurrent.futures` (from ... import as_completed)
- **Contexto**: module_level

### coordinators\intelligence_coordinator.py:709
- **Import**: `hashlib`
- **Contexto**: class:IntelligenceCoordinator > function:_generate_cache_key
- ⚠️ **Dentro de função**

### coordinators\__init__.py:21
- **Import**: `coordinator_manager` (from ... import get_coordinator_manager)
- **Contexto**: function:get_coordinator_manager > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### coordinators\__init__.py:21
- **Import**: `coordinator_manager` (from ... import get_coordinator_manager)
- **Contexto**: function:get_coordinator_manager
- ⚠️ **Dentro de função**

### coordinators\__init__.py:38
- **Import**: `intelligence_coordinator` (from ... import get_intelligence_coordinator)
- **Contexto**: function:get_intelligence_coordinator > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### coordinators\__init__.py:38
- **Import**: `intelligence_coordinator` (from ... import get_intelligence_coordinator)
- **Contexto**: function:get_intelligence_coordinator
- ⚠️ **Dentro de função**

### coordinators\__init__.py:55
- **Import**: `processor_coordinator` (from ... import ProcessorCoordinator)
- **Contexto**: function:get_processor_coordinator > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### coordinators\__init__.py:55
- **Import**: `processor_coordinator` (from ... import ProcessorCoordinator)
- **Contexto**: function:get_processor_coordinator
- ⚠️ **Dentro de função**

### coordinators\__init__.py:72
- **Import**: `specialist_agents` (from ... import create_fretes_agent)
- **Contexto**: function:get_specialist_coordinator > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### coordinators\__init__.py:72
- **Import**: `specialist_agents` (from ... import create_entregas_agent)
- **Contexto**: function:get_specialist_coordinator > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### coordinators\__init__.py:72
- **Import**: `specialist_agents` (from ... import create_pedidos_agent)
- **Contexto**: function:get_specialist_coordinator > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### coordinators\__init__.py:72
- **Import**: `specialist_agents` (from ... import create_embarques_agent)
- **Contexto**: function:get_specialist_coordinator > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### coordinators\__init__.py:72
- **Import**: `specialist_agents` (from ... import create_financeiro_agent)
- **Contexto**: function:get_specialist_coordinator > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### coordinators\__init__.py:72
- **Import**: `specialist_agents` (from ... import get_all_agent_types)
- **Contexto**: function:get_specialist_coordinator > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### coordinators\__init__.py:72
- **Import**: `specialist_agents` (from ... import create_fretes_agent)
- **Contexto**: function:get_specialist_coordinator
- ⚠️ **Dentro de função**

### coordinators\__init__.py:72
- **Import**: `specialist_agents` (from ... import create_entregas_agent)
- **Contexto**: function:get_specialist_coordinator
- ⚠️ **Dentro de função**

### coordinators\__init__.py:72
- **Import**: `specialist_agents` (from ... import create_pedidos_agent)
- **Contexto**: function:get_specialist_coordinator
- ⚠️ **Dentro de função**

### coordinators\__init__.py:72
- **Import**: `specialist_agents` (from ... import create_embarques_agent)
- **Contexto**: function:get_specialist_coordinator
- ⚠️ **Dentro de função**

### coordinators\__init__.py:72
- **Import**: `specialist_agents` (from ... import create_financeiro_agent)
- **Contexto**: function:get_specialist_coordinator
- ⚠️ **Dentro de função**

### coordinators\__init__.py:72
- **Import**: `specialist_agents` (from ... import get_all_agent_types)
- **Contexto**: function:get_specialist_coordinator
- ⚠️ **Dentro de função**

### coordinators\domain_agents\base_agent.py:12
- **Import**: `abc` (from ... import ABC)
- **Contexto**: module_level

### coordinators\domain_agents\base_agent.py:12
- **Import**: `abc` (from ... import abstractmethod)
- **Contexto**: module_level

### coordinators\domain_agents\smart_base_agent.py:16
- **Import**: `abc` (from ... import ABC)
- **Contexto**: module_level

### coordinators\domain_agents\smart_base_agent.py:16
- **Import**: `abc` (from ... import abstractmethod)
- **Contexto**: module_level

### coordinators\domain_agents\__init__.py:21
- **Import**: `smart_base_agent` (from ... import SmartBaseAgent)
- **Contexto**: module_level

### coordinators\domain_agents\__init__.py:22
- **Import**: `entregas_agent` (from ... import EntregasAgent)
- **Contexto**: module_level

### coordinators\domain_agents\__init__.py:23
- **Import**: `embarques_agent` (from ... import EmbarquesAgent)
- **Contexto**: module_level

### coordinators\domain_agents\__init__.py:24
- **Import**: `financeiro_agent` (from ... import FinanceiroAgent)
- **Contexto**: module_level

### coordinators\domain_agents\__init__.py:25
- **Import**: `pedidos_agent` (from ... import PedidosAgent)
- **Contexto**: module_level

### coordinators\domain_agents\__init__.py:26
- **Import**: `fretes_agent` (from ... import FretesAgent)
- **Contexto**: module_level

### enrichers\context_enricher.py:9
- **Import**: `performance_cache` (from ... import cached_result)
- **Contexto**: module_level

### enrichers\context_enricher.py:9
- **Import**: `performance_cache` (from ... import performance_monitor)
- **Contexto**: module_level

### enrichers\performance_cache.py:9
- **Import**: `time`
- **Contexto**: module_level

### enrichers\semantic_enricher.py:19
- **Import**: `performance_cache` (from ... import cached_result)
- **Contexto**: module_level

### enrichers\semantic_enricher.py:19
- **Import**: `performance_cache` (from ... import performance_monitor)
- **Contexto**: module_level

### enrichers\__init__.py:10
- **Import**: `semantic_enricher` (from ... import SemanticEnricher)
- **Contexto**: module_level

### enrichers\__init__.py:19
- **Import**: `semantic_enricher` (from ... import SemanticEnricher)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### enrichers\__init__.py:19
- **Import**: `semantic_enricher` (from ... import SemanticEnricher)
- **Contexto**: module_level

### enrichers\__init__.py:25
- **Import**: `context_enricher` (from ... import ContextEnricher)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### enrichers\__init__.py:25
- **Import**: `context_enricher` (from ... import ContextEnricher)
- **Contexto**: module_level

### integration\external_api_integration.py:231
- **Import**: `integration_manager` (from ... import IntegrationManager)
- **Contexto**: class:ExternalAPIIntegration > function:_get_integration_manager > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### integration\external_api_integration.py:231
- **Import**: `integration_manager` (from ... import IntegrationManager)
- **Contexto**: class:ExternalAPIIntegration > function:_get_integration_manager
- ⚠️ **Dentro de função**

### integration\integration_manager.py:22
- **Import**: `time`
- **Contexto**: module_level

### integration\standalone_integration.py:76
- **Import**: `integration_manager` (from ... import IntegrationManager)
- **Contexto**: class:StandaloneIntegration > function:_get_integration_manager > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### integration\standalone_integration.py:76
- **Import**: `integration_manager` (from ... import IntegrationManager)
- **Contexto**: class:StandaloneIntegration > function:_get_integration_manager
- ⚠️ **Dentro de função**

### integration\standalone_integration.py:92
- **Import**: `external_api_integration` (from ... import get_external_api_integration)
- **Contexto**: class:StandaloneIntegration > function:_get_external_api_integration > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### integration\standalone_integration.py:92
- **Import**: `external_api_integration` (from ... import get_external_api_integration)
- **Contexto**: class:StandaloneIntegration > function:_get_external_api_integration
- ⚠️ **Dentro de função**

### integration\web_integration.py:22
- **Import**: `flask_login` (from ... import login_required)
- **Contexto**: module_level

### integration\web_integration.py:22
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: module_level

### integration\web_integration.py:58
- **Import**: `integration_manager` (from ... import IntegrationManager)
- **Contexto**: class:WebIntegrationAdapter > function:_get_integration_manager > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### integration\web_integration.py:62
- **Import**: `app` (from ... import db)
- **Contexto**: class:WebIntegrationAdapter > function:_get_integration_manager > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### integration\web_integration.py:62
- **Import**: `app` (from ... import db)
- **Contexto**: class:WebIntegrationAdapter > function:_get_integration_manager > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### integration\web_integration.py:58
- **Import**: `integration_manager` (from ... import IntegrationManager)
- **Contexto**: class:WebIntegrationAdapter > function:_get_integration_manager
- ⚠️ **Dentro de função**

### integration\web_integration.py:62
- **Import**: `app` (from ... import db)
- **Contexto**: class:WebIntegrationAdapter > function:_get_integration_manager > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### integration\web_integration.py:62
- **Import**: `app` (from ... import db)
- **Contexto**: class:WebIntegrationAdapter > function:_get_integration_manager
- ⚠️ **Dentro de função**

### integration\web_integration.py:81
- **Import**: `external_api_integration` (from ... import get_external_api_integration)
- **Contexto**: class:WebIntegrationAdapter > function:_get_external_api_integration > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### integration\web_integration.py:81
- **Import**: `external_api_integration` (from ... import get_external_api_integration)
- **Contexto**: class:WebIntegrationAdapter > function:_get_external_api_integration
- ⚠️ **Dentro de função**

### integration\__init__.py:33
- **Import**: `integration_manager` (from ... import IntegrationManager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:33
- **Import**: `integration_manager` (from ... import get_integration_manager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:33
- **Import**: `integration_manager` (from ... import IntegrationManager)
- **Contexto**: module_level

### integration\__init__.py:33
- **Import**: `integration_manager` (from ... import get_integration_manager)
- **Contexto**: module_level

### integration\__init__.py:41
- **Import**: `external_api_integration` (from ... import ExternalAPIIntegration)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:41
- **Import**: `external_api_integration` (from ... import ClaudeAPIClient)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:41
- **Import**: `external_api_integration` (from ... import get_external_api_integration)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:41
- **Import**: `external_api_integration` (from ... import get_claude_client)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:41
- **Import**: `external_api_integration` (from ... import create_claude_client)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:41
- **Import**: `external_api_integration` (from ... import ExternalAPIIntegration)
- **Contexto**: module_level

### integration\__init__.py:41
- **Import**: `external_api_integration` (from ... import ClaudeAPIClient)
- **Contexto**: module_level

### integration\__init__.py:41
- **Import**: `external_api_integration` (from ... import get_external_api_integration)
- **Contexto**: module_level

### integration\__init__.py:41
- **Import**: `external_api_integration` (from ... import get_claude_client)
- **Contexto**: module_level

### integration\__init__.py:41
- **Import**: `external_api_integration` (from ... import create_claude_client)
- **Contexto**: module_level

### integration\__init__.py:52
- **Import**: `web_integration` (from ... import WebIntegrationAdapter)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:52
- **Import**: `web_integration` (from ... import WebFlaskRoutes)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:52
- **Import**: `web_integration` (from ... import get_web_integration_adapter)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:52
- **Import**: `web_integration` (from ... import get_flask_routes)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:52
- **Import**: `web_integration` (from ... import create_integration_routes)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:52
- **Import**: `web_integration` (from ... import WebIntegrationAdapter)
- **Contexto**: module_level

### integration\__init__.py:52
- **Import**: `web_integration` (from ... import WebFlaskRoutes)
- **Contexto**: module_level

### integration\__init__.py:52
- **Import**: `web_integration` (from ... import get_web_integration_adapter)
- **Contexto**: module_level

### integration\__init__.py:52
- **Import**: `web_integration` (from ... import get_flask_routes)
- **Contexto**: module_level

### integration\__init__.py:52
- **Import**: `web_integration` (from ... import create_integration_routes)
- **Contexto**: module_level

### integration\__init__.py:63
- **Import**: `standalone_integration` (from ... import StandaloneIntegration)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:63
- **Import**: `standalone_integration` (from ... import get_standalone_integration)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:63
- **Import**: `standalone_integration` (from ... import get_standalone_adapter)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:63
- **Import**: `standalone_integration` (from ... import create_standalone_system)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### integration\__init__.py:63
- **Import**: `standalone_integration` (from ... import StandaloneIntegration)
- **Contexto**: module_level

### integration\__init__.py:63
- **Import**: `standalone_integration` (from ... import get_standalone_integration)
- **Contexto**: module_level

### integration\__init__.py:63
- **Import**: `standalone_integration` (from ... import get_standalone_adapter)
- **Contexto**: module_level

### integration\__init__.py:63
- **Import**: `standalone_integration` (from ... import create_standalone_system)
- **Contexto**: module_level

### learners\adaptive_learning.py:12
- **Import**: `hashlib`
- **Contexto**: module_level

### learners\feedback_learning.py:20
- **Import**: `dataclasses` (from ... import dataclass)
- **Contexto**: module_level

### learners\human_in_loop_learning.py:10
- **Import**: `enum` (from ... import Enum)
- **Contexto**: module_level

### learners\human_in_loop_learning.py:12
- **Import**: `dataclasses` (from ... import dataclass)
- **Contexto**: module_level

### learners\human_in_loop_learning.py:13
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: module_level

### learners\human_in_loop_learning.py:15
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### learners\learning_core.py:266
- **Import**: `app` (from ... import db)
- **Contexto**: class:LearningCore > function:_atualizar_metricas > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### learners\learning_core.py:296
- **Import**: `app` (from ... import db)
- **Contexto**: class:LearningCore > function:_atualizar_metricas > in_try > in_except
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### learners\learning_core.py:296
- **Import**: `app` (from ... import db)
- **Contexto**: class:LearningCore > function:_atualizar_metricas > in_except
- ⚠️ **Dentro de função**

### learners\learning_core.py:266
- **Import**: `app` (from ... import db)
- **Contexto**: class:LearningCore > function:_atualizar_metricas
- ⚠️ **Dentro de função**

### learners\learning_core.py:296
- **Import**: `app` (from ... import db)
- **Contexto**: class:LearningCore > function:_atualizar_metricas > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### learners\learning_core.py:296
- **Import**: `app` (from ... import db)
- **Contexto**: class:LearningCore > function:_atualizar_metricas
- ⚠️ **Dentro de função**

### learners\learning_core.py:313
- **Import**: `app` (from ... import db)
- **Contexto**: class:LearningCore > function:_salvar_historico_aprendizado > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### learners\learning_core.py:338
- **Import**: `app` (from ... import db)
- **Contexto**: class:LearningCore > function:_salvar_historico_aprendizado > in_try > in_except
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### learners\learning_core.py:338
- **Import**: `app` (from ... import db)
- **Contexto**: class:LearningCore > function:_salvar_historico_aprendizado > in_except
- ⚠️ **Dentro de função**

### learners\learning_core.py:313
- **Import**: `app` (from ... import db)
- **Contexto**: class:LearningCore > function:_salvar_historico_aprendizado
- ⚠️ **Dentro de função**

### learners\learning_core.py:338
- **Import**: `app` (from ... import db)
- **Contexto**: class:LearningCore > function:_salvar_historico_aprendizado > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### learners\learning_core.py:338
- **Import**: `app` (from ... import db)
- **Contexto**: class:LearningCore > function:_salvar_historico_aprendizado
- ⚠️ **Dentro de função**

### learners\lifelong_learning.py:16
- **Import**: `learning_core` (from ... import LearningCore)
- **Contexto**: module_level

### learners\lifelong_learning.py:17
- **Import**: `pattern_learning` (from ... import PatternLearner)
- **Contexto**: module_level

### learners\lifelong_learning.py:18
- **Import**: `human_in_loop_learning` (from ... import HumanInLoopLearning)
- **Contexto**: module_level

### learners\lifelong_learning.py:19
- **Import**: `feedback_learning` (from ... import FeedbackProcessor)
- **Contexto**: module_level

### learners\pattern_learning.py:261
- **Import**: `app` (from ... import db)
- **Contexto**: class:PatternLearner > function:_salvar_padrao_otimizado > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### learners\pattern_learning.py:321
- **Import**: `app` (from ... import db)
- **Contexto**: class:PatternLearner > function:_salvar_padrao_otimizado > in_try > in_except
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### learners\pattern_learning.py:321
- **Import**: `app` (from ... import db)
- **Contexto**: class:PatternLearner > function:_salvar_padrao_otimizado > in_except
- ⚠️ **Dentro de função**

### learners\pattern_learning.py:261
- **Import**: `app` (from ... import db)
- **Contexto**: class:PatternLearner > function:_salvar_padrao_otimizado
- ⚠️ **Dentro de função**

### learners\pattern_learning.py:321
- **Import**: `app` (from ... import db)
- **Contexto**: class:PatternLearner > function:_salvar_padrao_otimizado > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### learners\pattern_learning.py:321
- **Import**: `app` (from ... import db)
- **Contexto**: class:PatternLearner > function:_salvar_padrao_otimizado
- ⚠️ **Dentro de função**

### learners\pattern_learning.py:340
- **Import**: `app` (from ... import db)
- **Contexto**: class:PatternLearner > function:buscar_padroes_aplicaveis > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### learners\pattern_learning.py:340
- **Import**: `app` (from ... import db)
- **Contexto**: class:PatternLearner > function:buscar_padroes_aplicaveis
- ⚠️ **Dentro de função**

### learners\__init__.py:10
- **Import**: `human_in_loop_learning` (from ... import HumanInLoopLearning)
- **Contexto**: module_level

### learners\__init__.py:11
- **Import**: `lifelong_learning` (from ... import LifelongLearningSystem)
- **Contexto**: module_level

### learners\__init__.py:12
- **Import**: `adaptive_learning` (from ... import AdaptiveLearning)
- **Contexto**: module_level

### learners\__init__.py:13
- **Import**: `feedback_learning` (from ... import FeedbackProcessor)
- **Contexto**: module_level

### learners\__init__.py:14
- **Import**: `pattern_learning` (from ... import PatternLearner)
- **Contexto**: module_level

### learners\__init__.py:15
- **Import**: `learning_core` (from ... import LearningCore)
- **Contexto**: module_level

### learners\__init__.py:24
- **Import**: `learning_core` (from ... import LearningCore)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### learners\__init__.py:24
- **Import**: `learning_core` (from ... import LearningCore)
- **Contexto**: module_level

### learners\__init__.py:30
- **Import**: `human_in_loop_learning` (from ... import HumanInLoopLearning)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### learners\__init__.py:30
- **Import**: `human_in_loop_learning` (from ... import HumanInLoopLearning)
- **Contexto**: module_level

### learners\__init__.py:36
- **Import**: `lifelong_learning` (from ... import LifelongLearningSystem)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### learners\__init__.py:36
- **Import**: `lifelong_learning` (from ... import LifelongLearningSystem)
- **Contexto**: module_level

### learners\__init__.py:42
- **Import**: `adaptive_learning` (from ... import AdaptiveLearning)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### learners\__init__.py:42
- **Import**: `adaptive_learning` (from ... import AdaptiveLearning)
- **Contexto**: module_level

### learners\__init__.py:48
- **Import**: `feedback_learning` (from ... import FeedbackProcessor)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### learners\__init__.py:48
- **Import**: `feedback_learning` (from ... import FeedbackProcessor)
- **Contexto**: module_level

### learners\__init__.py:54
- **Import**: `pattern_learning` (from ... import PatternLearner)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### learners\__init__.py:54
- **Import**: `pattern_learning` (from ... import PatternLearner)
- **Contexto**: module_level

### loaders\context_loader.py:11
- **Import**: `time`
- **Contexto**: module_level

### loaders\context_loader.py:15
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: module_level

### loaders\context_loader.py:18
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### loaders\database_loader.py:14
- **Import**: `dataclasses` (from ... import dataclass)
- **Contexto**: module_level

### loaders\loader_manager.py:15
- **Import**: `domain.pedidos_loader` (from ... import PedidosLoader)
- **Contexto**: module_level

### loaders\loader_manager.py:16
- **Import**: `domain.entregas_loader` (from ... import EntregasLoader)
- **Contexto**: module_level

### loaders\loader_manager.py:17
- **Import**: `domain.fretes_loader` (from ... import FretesLoader)
- **Contexto**: module_level

### loaders\loader_manager.py:18
- **Import**: `domain.embarques_loader` (from ... import EmbarquesLoader)
- **Contexto**: module_level

### loaders\loader_manager.py:19
- **Import**: `domain.faturamento_loader` (from ... import FaturamentoLoader)
- **Contexto**: module_level

### loaders\loader_manager.py:20
- **Import**: `domain.agendamentos_loader` (from ... import AgendamentosLoader)
- **Contexto**: module_level

### loaders\loader_manager.py:51
- **Import**: `domain.pedidos_loader` (from ... import get_pedidos_loader)
- **Contexto**: class:LoaderManager > function:_initialize_loaders > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### loaders\loader_manager.py:52
- **Import**: `domain.entregas_loader` (from ... import get_entregas_loader)
- **Contexto**: class:LoaderManager > function:_initialize_loaders > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### loaders\loader_manager.py:53
- **Import**: `domain.fretes_loader` (from ... import get_fretes_loader)
- **Contexto**: class:LoaderManager > function:_initialize_loaders > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### loaders\loader_manager.py:54
- **Import**: `domain.embarques_loader` (from ... import get_embarques_loader)
- **Contexto**: class:LoaderManager > function:_initialize_loaders > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### loaders\loader_manager.py:55
- **Import**: `domain.faturamento_loader` (from ... import get_faturamento_loader)
- **Contexto**: class:LoaderManager > function:_initialize_loaders > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### loaders\loader_manager.py:56
- **Import**: `domain.agendamentos_loader` (from ... import get_agendamentos_loader)
- **Contexto**: class:LoaderManager > function:_initialize_loaders > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### loaders\loader_manager.py:51
- **Import**: `domain.pedidos_loader` (from ... import get_pedidos_loader)
- **Contexto**: class:LoaderManager > function:_initialize_loaders
- ⚠️ **Dentro de função**

### loaders\loader_manager.py:52
- **Import**: `domain.entregas_loader` (from ... import get_entregas_loader)
- **Contexto**: class:LoaderManager > function:_initialize_loaders
- ⚠️ **Dentro de função**

### loaders\loader_manager.py:53
- **Import**: `domain.fretes_loader` (from ... import get_fretes_loader)
- **Contexto**: class:LoaderManager > function:_initialize_loaders
- ⚠️ **Dentro de função**

### loaders\loader_manager.py:54
- **Import**: `domain.embarques_loader` (from ... import get_embarques_loader)
- **Contexto**: class:LoaderManager > function:_initialize_loaders
- ⚠️ **Dentro de função**

### loaders\loader_manager.py:55
- **Import**: `domain.faturamento_loader` (from ... import get_faturamento_loader)
- **Contexto**: class:LoaderManager > function:_initialize_loaders
- ⚠️ **Dentro de função**

### loaders\loader_manager.py:56
- **Import**: `domain.agendamentos_loader` (from ... import get_agendamentos_loader)
- **Contexto**: class:LoaderManager > function:_initialize_loaders
- ⚠️ **Dentro de função**

### loaders\__init__.py:22
- **Import**: `context_loader` (from ... import ContextLoader)
- **Contexto**: function:get_context_loader > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### loaders\__init__.py:22
- **Import**: `context_loader` (from ... import ContextLoader)
- **Contexto**: function:get_context_loader
- ⚠️ **Dentro de função**

### loaders\__init__.py:39
- **Import**: `database_loader` (from ... import DatabaseLoader)
- **Contexto**: function:get_database_loader > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### loaders\__init__.py:39
- **Import**: `database_loader` (from ... import DatabaseLoader)
- **Contexto**: function:get_database_loader
- ⚠️ **Dentro de função**

### loaders\__init__.py:56
- **Import**: `loader_manager` (from ... import get_loader_manager)
- **Contexto**: function:get_loader_manager > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### loaders\__init__.py:56
- **Import**: `loader_manager` (from ... import get_loader_manager)
- **Contexto**: function:get_loader_manager
- ⚠️ **Dentro de função**

### loaders\__init__.py:93
- **Import**: `domain` (from ... import get_pedidos_loader)
- **Contexto**: function:get_domain_loaders > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### loaders\__init__.py:93
- **Import**: `domain` (from ... import get_entregas_loader)
- **Contexto**: function:get_domain_loaders > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### loaders\__init__.py:93
- **Import**: `domain` (from ... import get_fretes_loader)
- **Contexto**: function:get_domain_loaders > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### loaders\__init__.py:93
- **Import**: `domain` (from ... import get_embarques_loader)
- **Contexto**: function:get_domain_loaders > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### loaders\__init__.py:93
- **Import**: `domain` (from ... import get_faturamento_loader)
- **Contexto**: function:get_domain_loaders > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### loaders\__init__.py:93
- **Import**: `domain` (from ... import get_agendamentos_loader)
- **Contexto**: function:get_domain_loaders > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### loaders\__init__.py:93
- **Import**: `domain` (from ... import get_pedidos_loader)
- **Contexto**: function:get_domain_loaders
- ⚠️ **Dentro de função**

### loaders\__init__.py:93
- **Import**: `domain` (from ... import get_entregas_loader)
- **Contexto**: function:get_domain_loaders
- ⚠️ **Dentro de função**

### loaders\__init__.py:93
- **Import**: `domain` (from ... import get_fretes_loader)
- **Contexto**: function:get_domain_loaders
- ⚠️ **Dentro de função**

### loaders\__init__.py:93
- **Import**: `domain` (from ... import get_embarques_loader)
- **Contexto**: function:get_domain_loaders
- ⚠️ **Dentro de função**

### loaders\__init__.py:93
- **Import**: `domain` (from ... import get_faturamento_loader)
- **Contexto**: function:get_domain_loaders
- ⚠️ **Dentro de função**

### loaders\__init__.py:93
- **Import**: `domain` (from ... import get_agendamentos_loader)
- **Contexto**: function:get_domain_loaders
- ⚠️ **Dentro de função**

### loaders\domain\agendamentos_loader.py:9
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### loaders\domain\embarques_loader.py:9
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### loaders\domain\entregas_loader.py:9
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### loaders\domain\faturamento_loader.py:9
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### loaders\domain\fretes_loader.py:9
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### loaders\domain\pedidos_loader.py:9
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### loaders\domain\__init__.py:7
- **Import**: `faturamento_loader` (from ... import FaturamentoLoader)
- **Contexto**: module_level

### loaders\domain\__init__.py:7
- **Import**: `faturamento_loader` (from ... import get_faturamento_loader)
- **Contexto**: module_level

### loaders\domain\__init__.py:8
- **Import**: `embarques_loader` (from ... import EmbarquesLoader)
- **Contexto**: module_level

### loaders\domain\__init__.py:8
- **Import**: `embarques_loader` (from ... import get_embarques_loader)
- **Contexto**: module_level

### loaders\domain\__init__.py:9
- **Import**: `fretes_loader` (from ... import FretesLoader)
- **Contexto**: module_level

### loaders\domain\__init__.py:9
- **Import**: `fretes_loader` (from ... import get_fretes_loader)
- **Contexto**: module_level

### loaders\domain\__init__.py:10
- **Import**: `entregas_loader` (from ... import EntregasLoader)
- **Contexto**: module_level

### loaders\domain\__init__.py:10
- **Import**: `entregas_loader` (from ... import get_entregas_loader)
- **Contexto**: module_level

### loaders\domain\__init__.py:11
- **Import**: `pedidos_loader` (from ... import PedidosLoader)
- **Contexto**: module_level

### loaders\domain\__init__.py:11
- **Import**: `pedidos_loader` (from ... import get_pedidos_loader)
- **Contexto**: module_level

### loaders\domain\__init__.py:12
- **Import**: `agendamentos_loader` (from ... import AgendamentosLoader)
- **Contexto**: module_level

### loaders\domain\__init__.py:12
- **Import**: `agendamentos_loader` (from ... import get_agendamentos_loader)
- **Contexto**: module_level

### mappers\context_mapper.py:14
- **Import**: `dataclasses` (from ... import dataclass)
- **Contexto**: module_level

### mappers\context_mapper.py:14
- **Import**: `dataclasses` (from ... import field)
- **Contexto**: module_level

### mappers\field_mapper.py:14
- **Import**: `dataclasses` (from ... import dataclass)
- **Contexto**: module_level

### mappers\field_mapper.py:15
- **Import**: `enum` (from ... import Enum)
- **Contexto**: module_level

### mappers\query_mapper.py:14
- **Import**: `dataclasses` (from ... import dataclass)
- **Contexto**: module_level

### mappers\query_mapper.py:15
- **Import**: `enum` (from ... import Enum)
- **Contexto**: module_level

### mappers\__init__.py:24
- **Import**: `mapper_manager` (from ... import MapperManager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:24
- **Import**: `mapper_manager` (from ... import get_mapper_manager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:27
- **Import**: `context_mapper` (from ... import ContextMapper)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:27
- **Import**: `context_mapper` (from ... import get_context_mapper)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:28
- **Import**: `field_mapper` (from ... import FieldMapper)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:28
- **Import**: `field_mapper` (from ... import get_field_mapper)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:29
- **Import**: `query_mapper` (from ... import QueryMapper)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:29
- **Import**: `query_mapper` (from ... import get_query_mapper)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:32
- **Import**: `domain.base_mapper` (from ... import BaseMapper)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:33
- **Import**: `domain.pedidos_mapper` (from ... import PedidosMapper)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:34
- **Import**: `domain.embarques_mapper` (from ... import EmbarquesMapper)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:35
- **Import**: `domain.monitoramento_mapper` (from ... import MonitoramentoMapper)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:36
- **Import**: `domain.faturamento_mapper` (from ... import FaturamentoMapper)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:37
- **Import**: `domain.transportadoras_mapper` (from ... import TransportadorasMapper)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:40
- **Import**: `mapper_manager` (from ... import SemanticMapper)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:40
- **Import**: `mapper_manager` (from ... import get_semantic_mapper)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### mappers\__init__.py:24
- **Import**: `mapper_manager` (from ... import MapperManager)
- **Contexto**: module_level

### mappers\__init__.py:24
- **Import**: `mapper_manager` (from ... import get_mapper_manager)
- **Contexto**: module_level

### mappers\__init__.py:27
- **Import**: `context_mapper` (from ... import ContextMapper)
- **Contexto**: module_level

### mappers\__init__.py:27
- **Import**: `context_mapper` (from ... import get_context_mapper)
- **Contexto**: module_level

### mappers\__init__.py:28
- **Import**: `field_mapper` (from ... import FieldMapper)
- **Contexto**: module_level

### mappers\__init__.py:28
- **Import**: `field_mapper` (from ... import get_field_mapper)
- **Contexto**: module_level

### mappers\__init__.py:29
- **Import**: `query_mapper` (from ... import QueryMapper)
- **Contexto**: module_level

### mappers\__init__.py:29
- **Import**: `query_mapper` (from ... import get_query_mapper)
- **Contexto**: module_level

### mappers\__init__.py:32
- **Import**: `domain.base_mapper` (from ... import BaseMapper)
- **Contexto**: module_level

### mappers\__init__.py:33
- **Import**: `domain.pedidos_mapper` (from ... import PedidosMapper)
- **Contexto**: module_level

### mappers\__init__.py:34
- **Import**: `domain.embarques_mapper` (from ... import EmbarquesMapper)
- **Contexto**: module_level

### mappers\__init__.py:35
- **Import**: `domain.monitoramento_mapper` (from ... import MonitoramentoMapper)
- **Contexto**: module_level

### mappers\__init__.py:36
- **Import**: `domain.faturamento_mapper` (from ... import FaturamentoMapper)
- **Contexto**: module_level

### mappers\__init__.py:37
- **Import**: `domain.transportadoras_mapper` (from ... import TransportadorasMapper)
- **Contexto**: module_level

### mappers\__init__.py:40
- **Import**: `mapper_manager` (from ... import SemanticMapper)
- **Contexto**: module_level

### mappers\__init__.py:40
- **Import**: `mapper_manager` (from ... import get_semantic_mapper)
- **Contexto**: module_level

### mappers\domain\base_mapper.py:10
- **Import**: `abc` (from ... import ABC)
- **Contexto**: module_level

### mappers\domain\base_mapper.py:10
- **Import**: `abc` (from ... import abstractmethod)
- **Contexto**: module_level

### mappers\domain\base_mapper.py:96
- **Import**: `fuzzywuzzy` (from ... import fuzz)
- **Contexto**: class:BaseMapper > function:buscar_mapeamento_fuzzy > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### mappers\domain\base_mapper.py:96
- **Import**: `fuzzywuzzy` (from ... import fuzz)
- **Contexto**: class:BaseMapper > function:buscar_mapeamento_fuzzy
- ⚠️ **Dentro de função**

### mappers\domain\embarques_mapper.py:18
- **Import**: `base_mapper` (from ... import BaseMapper)
- **Contexto**: module_level

### mappers\domain\faturamento_mapper.py:18
- **Import**: `base_mapper` (from ... import BaseMapper)
- **Contexto**: module_level

### mappers\domain\monitoramento_mapper.py:16
- **Import**: `base_mapper` (from ... import BaseMapper)
- **Contexto**: module_level

### mappers\domain\pedidos_mapper.py:7
- **Import**: `base_mapper` (from ... import BaseMapper)
- **Contexto**: module_level

### mappers\domain\transportadoras_mapper.py:15
- **Import**: `base_mapper` (from ... import BaseMapper)
- **Contexto**: module_level

### mappers\domain\__init__.py:6
- **Import**: `base_mapper` (from ... import BaseMapper)
- **Contexto**: module_level

### mappers\domain\__init__.py:7
- **Import**: `pedidos_mapper` (from ... import PedidosMapper)
- **Contexto**: module_level

### mappers\domain\__init__.py:8
- **Import**: `embarques_mapper` (from ... import EmbarquesMapper)
- **Contexto**: module_level

### mappers\domain\__init__.py:9
- **Import**: `faturamento_mapper` (from ... import FaturamentoMapper)
- **Contexto**: module_level

### mappers\domain\__init__.py:10
- **Import**: `monitoramento_mapper` (from ... import MonitoramentoMapper)
- **Contexto**: module_level

### mappers\domain\__init__.py:11
- **Import**: `transportadoras_mapper` (from ... import TransportadorasMapper)
- **Contexto**: module_level

### memorizers\context_memory.py:19
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### memorizers\context_memory.py:19
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: module_level

### memorizers\conversation_memory.py:13
- **Import**: `context_memory` (from ... import ContextMemory)
- **Contexto**: module_level

### memorizers\conversation_memory.py:13
- **Import**: `context_memory` (from ... import get_context_memory)
- **Contexto**: module_level

### memorizers\knowledge_memory.py:48
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:aprender_mapeamento_cliente > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### memorizers\knowledge_memory.py:108
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:aprender_mapeamento_cliente > in_try > in_except
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### memorizers\knowledge_memory.py:108
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:aprender_mapeamento_cliente > in_except
- ⚠️ **Dentro de função**

### memorizers\knowledge_memory.py:48
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:aprender_mapeamento_cliente
- ⚠️ **Dentro de função**

### memorizers\knowledge_memory.py:108
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:aprender_mapeamento_cliente > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### memorizers\knowledge_memory.py:108
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:aprender_mapeamento_cliente
- ⚠️ **Dentro de função**

### memorizers\knowledge_memory.py:134
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:descobrir_grupo_empresarial > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### memorizers\knowledge_memory.py:182
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:descobrir_grupo_empresarial > in_try > in_except
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### memorizers\knowledge_memory.py:182
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:descobrir_grupo_empresarial > in_except
- ⚠️ **Dentro de função**

### memorizers\knowledge_memory.py:134
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:descobrir_grupo_empresarial
- ⚠️ **Dentro de função**

### memorizers\knowledge_memory.py:182
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:descobrir_grupo_empresarial > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### memorizers\knowledge_memory.py:182
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:descobrir_grupo_empresarial
- ⚠️ **Dentro de função**

### memorizers\knowledge_memory.py:200
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:buscar_grupos_aplicaveis > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### memorizers\knowledge_memory.py:200
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:buscar_grupos_aplicaveis
- ⚠️ **Dentro de função**

### memorizers\knowledge_memory.py:255
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:buscar_mapeamentos_aplicaveis > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### memorizers\knowledge_memory.py:255
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:buscar_mapeamentos_aplicaveis
- ⚠️ **Dentro de função**

### memorizers\knowledge_memory.py:296
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:obter_estatisticas_aprendizado > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### memorizers\knowledge_memory.py:296
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:obter_estatisticas_aprendizado
- ⚠️ **Dentro de função**

### memorizers\knowledge_memory.py:549
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:_verificar_acesso_banco > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### memorizers\knowledge_memory.py:549
- **Import**: `app` (from ... import db)
- **Contexto**: class:KnowledgeMemory > function:_verificar_acesso_banco
- ⚠️ **Dentro de função**

### memorizers\memory_manager.py:15
- **Import**: `context_memory` (from ... import ContextMemory)
- **Contexto**: module_level

### memorizers\memory_manager.py:15
- **Import**: `context_memory` (from ... import get_context_memory)
- **Contexto**: module_level

### memorizers\memory_manager.py:16
- **Import**: `conversation_memory` (from ... import ConversationMemory)
- **Contexto**: module_level

### memorizers\memory_manager.py:16
- **Import**: `conversation_memory` (from ... import get_conversation_memory)
- **Contexto**: module_level

### memorizers\memory_manager.py:17
- **Import**: `system_memory` (from ... import SystemMemory)
- **Contexto**: module_level

### memorizers\memory_manager.py:17
- **Import**: `system_memory` (from ... import get_system_memory)
- **Contexto**: module_level

### memorizers\memory_manager.py:18
- **Import**: `knowledge_memory` (from ... import KnowledgeMemory)
- **Contexto**: module_level

### memorizers\memory_manager.py:18
- **Import**: `knowledge_memory` (from ... import get_knowledge_memory)
- **Contexto**: module_level

### memorizers\__init__.py:10
- **Import**: `context_memory` (from ... import ContextMemory)
- **Contexto**: module_level

### memorizers\__init__.py:11
- **Import**: `system_memory` (from ... import SystemMemory)
- **Contexto**: module_level

### memorizers\__init__.py:12
- **Import**: `knowledge_memory` (from ... import KnowledgeMemory)
- **Contexto**: module_level

### memorizers\__init__.py:13
- **Import**: `memory_manager` (from ... import MemoryManager)
- **Contexto**: module_level

### memorizers\__init__.py:14
- **Import**: `session_memory` (from ... import SessionMemory)
- **Contexto**: module_level

### memorizers\__init__.py:15
- **Import**: `conversation_memory` (from ... import ConversationMemory)
- **Contexto**: module_level

### memorizers\__init__.py:24
- **Import**: `context_memory` (from ... import ContextMemory)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### memorizers\__init__.py:24
- **Import**: `context_memory` (from ... import ContextMemory)
- **Contexto**: module_level

### memorizers\__init__.py:30
- **Import**: `system_memory` (from ... import SystemMemory)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### memorizers\__init__.py:30
- **Import**: `system_memory` (from ... import SystemMemory)
- **Contexto**: module_level

### memorizers\__init__.py:36
- **Import**: `knowledge_memory` (from ... import KnowledgeMemory)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### memorizers\__init__.py:36
- **Import**: `knowledge_memory` (from ... import KnowledgeMemory)
- **Contexto**: module_level

### memorizers\__init__.py:42
- **Import**: `memory_manager` (from ... import MemoryManager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### memorizers\__init__.py:42
- **Import**: `memory_manager` (from ... import MemoryManager)
- **Contexto**: module_level

### memorizers\__init__.py:48
- **Import**: `conversation_memory` (from ... import ConversationMemory)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### memorizers\__init__.py:48
- **Import**: `conversation_memory` (from ... import ConversationMemory)
- **Contexto**: module_level

### memorizers\__init__.py:54
- **Import**: `session_memory` (from ... import SessionMemory)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### memorizers\__init__.py:54
- **Import**: `session_memory` (from ... import SessionMemory)
- **Contexto**: module_level

### monitoring\cursor_monitor.py:16
- **Import**: `time`
- **Contexto**: module_level

### monitoring\cursor_monitor.py:18
- **Import**: `subprocess`
- **Contexto**: module_level

### monitoring\cursor_monitor.py:24
- **Import**: `dataclasses` (from ... import dataclass)
- **Contexto**: module_level

### monitoring\cursor_monitor.py:25
- **Import**: `threading`
- **Contexto**: module_level

### monitoring\cursor_monitor.py:26
- **Import**: `signal`
- **Contexto**: module_level

### monitoring\cursor_monitor.py:117
- **Import**: `psutil`
- **Contexto**: class:CursorMonitor > function:get_system_stats > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### monitoring\cursor_monitor.py:117
- **Import**: `psutil`
- **Contexto**: class:CursorMonitor > function:get_system_stats
- ⚠️ **Dentro de função**

### monitoring\cursor_monitor.py:358
- **Import**: `argparse`
- **Contexto**: function:main
- ⚠️ **Dentro de função**

### monitoring\real_time_metrics.py:14
- **Import**: `time`
- **Contexto**: module_level

### monitoring\real_time_metrics.py:121
- **Import**: `app` (from ... import db)
- **Contexto**: class:ClaudeAIMetrics > function:get_system_health_metrics > in_try > in_except
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### monitoring\real_time_metrics.py:121
- **Import**: `app` (from ... import db)
- **Contexto**: class:ClaudeAIMetrics > function:get_system_health_metrics > in_except
- ⚠️ **Dentro de função**

### monitoring\real_time_metrics.py:121
- **Import**: `app` (from ... import db)
- **Contexto**: class:ClaudeAIMetrics > function:get_system_health_metrics > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### monitoring\real_time_metrics.py:121
- **Import**: `app` (from ... import db)
- **Contexto**: class:ClaudeAIMetrics > function:get_system_health_metrics
- ⚠️ **Dentro de função**

### orchestrators\main_orchestrator.py:14
- **Import**: `dataclasses` (from ... import dataclass)
- **Contexto**: module_level

### orchestrators\main_orchestrator.py:15
- **Import**: `enum` (from ... import Enum)
- **Contexto**: module_level

### orchestrators\orchestrator_manager.py:13
- **Import**: `enum` (from ... import Enum)
- **Contexto**: module_level

### orchestrators\orchestrator_manager.py:14
- **Import**: `dataclasses` (from ... import dataclass)
- **Contexto**: module_level

### orchestrators\orchestrator_manager.py:14
- **Import**: `dataclasses` (from ... import field)
- **Contexto**: module_level

### orchestrators\orchestrator_manager.py:15
- **Import**: `threading` (from ... import Lock)
- **Contexto**: module_level

### orchestrators\orchestrator_manager.py:16
- **Import**: `uuid`
- **Contexto**: module_level

### orchestrators\orchestrator_manager.py:27
- **Import**: `main_orchestrator` (from ... import MainOrchestrator)
- **Contexto**: in_try > in_except
- ⚠️ **Dentro de try/except**

### orchestrators\orchestrator_manager.py:28
- **Import**: `session_orchestrator` (from ... import SessionOrchestrator)
- **Contexto**: in_try > in_except
- ⚠️ **Dentro de try/except**

### orchestrators\orchestrator_manager.py:28
- **Import**: `session_orchestrator` (from ... import get_session_orchestrator)
- **Contexto**: in_try > in_except
- ⚠️ **Dentro de try/except**

### orchestrators\orchestrator_manager.py:29
- **Import**: `workflow_orchestrator` (from ... import WorkflowOrchestrator)
- **Contexto**: in_try > in_except
- ⚠️ **Dentro de try/except**

### orchestrators\orchestrator_manager.py:27
- **Import**: `main_orchestrator` (from ... import MainOrchestrator)
- **Contexto**: in_except

### orchestrators\orchestrator_manager.py:28
- **Import**: `session_orchestrator` (from ... import SessionOrchestrator)
- **Contexto**: in_except

### orchestrators\orchestrator_manager.py:28
- **Import**: `session_orchestrator` (from ... import get_session_orchestrator)
- **Contexto**: in_except

### orchestrators\orchestrator_manager.py:29
- **Import**: `workflow_orchestrator` (from ... import WorkflowOrchestrator)
- **Contexto**: in_except

### orchestrators\orchestrator_manager.py:27
- **Import**: `main_orchestrator` (from ... import MainOrchestrator)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### orchestrators\orchestrator_manager.py:28
- **Import**: `session_orchestrator` (from ... import SessionOrchestrator)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### orchestrators\orchestrator_manager.py:28
- **Import**: `session_orchestrator` (from ... import get_session_orchestrator)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### orchestrators\orchestrator_manager.py:29
- **Import**: `workflow_orchestrator` (from ... import WorkflowOrchestrator)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### orchestrators\orchestrator_manager.py:27
- **Import**: `main_orchestrator` (from ... import MainOrchestrator)
- **Contexto**: module_level

### orchestrators\orchestrator_manager.py:28
- **Import**: `session_orchestrator` (from ... import SessionOrchestrator)
- **Contexto**: module_level

### orchestrators\orchestrator_manager.py:28
- **Import**: `session_orchestrator` (from ... import get_session_orchestrator)
- **Contexto**: module_level

### orchestrators\orchestrator_manager.py:29
- **Import**: `workflow_orchestrator` (from ... import WorkflowOrchestrator)
- **Contexto**: module_level

### orchestrators\session_orchestrator.py:10
- **Import**: `uuid`
- **Contexto**: module_level

### orchestrators\session_orchestrator.py:14
- **Import**: `enum` (from ... import Enum)
- **Contexto**: module_level

### orchestrators\session_orchestrator.py:15
- **Import**: `dataclasses` (from ... import dataclass)
- **Contexto**: module_level

### orchestrators\session_orchestrator.py:15
- **Import**: `dataclasses` (from ... import field)
- **Contexto**: module_level

### orchestrators\session_orchestrator.py:16
- **Import**: `threading` (from ... import Lock)
- **Contexto**: module_level

### orchestrators\__init__.py:20
- **Import**: `orchestrator_manager` (from ... import OrchestratorManager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### orchestrators\__init__.py:20
- **Import**: `orchestrator_manager` (from ... import get_orchestrator_manager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### orchestrators\__init__.py:20
- **Import**: `orchestrator_manager` (from ... import orchestrate_system_operation)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### orchestrators\__init__.py:20
- **Import**: `orchestrator_manager` (from ... import get_orchestration_status)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### orchestrators\__init__.py:20
- **Import**: `orchestrator_manager` (from ... import OrchestratorManager)
- **Contexto**: module_level

### orchestrators\__init__.py:20
- **Import**: `orchestrator_manager` (from ... import get_orchestrator_manager)
- **Contexto**: module_level

### orchestrators\__init__.py:20
- **Import**: `orchestrator_manager` (from ... import orchestrate_system_operation)
- **Contexto**: module_level

### orchestrators\__init__.py:20
- **Import**: `orchestrator_manager` (from ... import get_orchestration_status)
- **Contexto**: module_level

### orchestrators\__init__.py:32
- **Import**: `main_orchestrator` (from ... import MainOrchestrator)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### orchestrators\__init__.py:32
- **Import**: `main_orchestrator` (from ... import MainOrchestrator)
- **Contexto**: module_level

### orchestrators\__init__.py:39
- **Import**: `session_orchestrator` (from ... import SessionOrchestrator)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### orchestrators\__init__.py:39
- **Import**: `session_orchestrator` (from ... import get_session_orchestrator)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### orchestrators\__init__.py:39
- **Import**: `session_orchestrator` (from ... import SessionOrchestrator)
- **Contexto**: module_level

### orchestrators\__init__.py:39
- **Import**: `session_orchestrator` (from ... import get_session_orchestrator)
- **Contexto**: module_level

### orchestrators\__init__.py:46
- **Import**: `workflow_orchestrator` (from ... import WorkflowOrchestrator)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### orchestrators\__init__.py:46
- **Import**: `workflow_orchestrator` (from ... import WorkflowOrchestrator)
- **Contexto**: module_level

### orchestrators\__init__.py:60
- **Import**: `orchestrator_manager` (from ... import get_orchestrator_manager)
- **Contexto**: function:get_orchestrator_manager > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### orchestrators\__init__.py:60
- **Import**: `orchestrator_manager` (from ... import get_orchestrator_manager)
- **Contexto**: function:get_orchestrator_manager
- ⚠️ **Dentro de função**

### orchestrators\__init__.py:87
- **Import**: `session_orchestrator` (from ... import get_session_orchestrator)
- **Contexto**: function:get_session_orchestrator > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### orchestrators\__init__.py:87
- **Import**: `session_orchestrator` (from ... import get_session_orchestrator)
- **Contexto**: function:get_session_orchestrator
- ⚠️ **Dentro de função**

### processors\base.py:9
- **Import**: `time`
- **Contexto**: module_level

### processors\context_processor.py:7
- **Import**: `base` (from ... import ProcessorBase)
- **Contexto**: module_level

### processors\context_processor.py:7
- **Import**: `base` (from ... import logging)
- **Contexto**: module_level

### processors\context_processor.py:12
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### processors\context_processor.py:13
- **Import**: `app` (from ... import db)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### processors\context_processor.py:12
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: module_level

### processors\context_processor.py:13
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### processors\context_processor.py:44
- **Import**: `time`
- **Contexto**: module_level

### processors\data_processor.py:13
- **Import**: `base` (from ... import ProcessorBase)
- **Contexto**: module_level

### processors\intelligence_processor.py:12
- **Import**: `base` (from ... import ProcessorBase)
- **Contexto**: module_level

### processors\processor_manager.py:7
- **Import**: `base` (from ... import ProcessorBase)
- **Contexto**: module_level

### processors\processor_manager.py:7
- **Import**: `base` (from ... import logging)
- **Contexto**: module_level

### processors\processor_manager.py:7
- **Import**: `base` (from ... import datetime)
- **Contexto**: module_level

### processors\response_processor.py:18
- **Import**: `time`
- **Contexto**: module_level

### processors\response_processor.py:22
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### processors\response_processor.py:23
- **Import**: `app` (from ... import db)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### processors\response_processor.py:22
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: module_level

### processors\response_processor.py:23
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### processors\semantic_loop_processor.py:8
- **Import**: `base` (from ... import ProcessorBase)
- **Contexto**: module_level

### processors\semantic_loop_processor.py:8
- **Import**: `base` (from ... import logging)
- **Contexto**: module_level

### processors\semantic_loop_processor.py:8
- **Import**: `base` (from ... import datetime)
- **Contexto**: module_level

### processors\__init__.py:15
- **Import**: `base` (from ... import BaseProcessor)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### processors\__init__.py:15
- **Import**: `base` (from ... import BaseProcessor)
- **Contexto**: module_level

### processors\__init__.py:22
- **Import**: `context_processor` (from ... import ContextProcessor)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### processors\__init__.py:22
- **Import**: `context_processor` (from ... import get_context_processor)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### processors\__init__.py:22
- **Import**: `context_processor` (from ... import ContextProcessor)
- **Contexto**: module_level

### processors\__init__.py:22
- **Import**: `context_processor` (from ... import get_context_processor)
- **Contexto**: module_level

### processors\__init__.py:29
- **Import**: `query_processor` (from ... import QueryProcessor)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### processors\__init__.py:29
- **Import**: `query_processor` (from ... import get_query_processor)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### processors\__init__.py:29
- **Import**: `query_processor` (from ... import QueryProcessor)
- **Contexto**: module_level

### processors\__init__.py:29
- **Import**: `query_processor` (from ... import get_query_processor)
- **Contexto**: module_level

### processors\__init__.py:36
- **Import**: `data_processor` (from ... import DataProcessor)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### processors\__init__.py:36
- **Import**: `data_processor` (from ... import get_data_processor)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### processors\__init__.py:36
- **Import**: `data_processor` (from ... import DataProcessor)
- **Contexto**: module_level

### processors\__init__.py:36
- **Import**: `data_processor` (from ... import get_data_processor)
- **Contexto**: module_level

### processors\__init__.py:43
- **Import**: `intelligence_processor` (from ... import IntelligenceProcessor)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### processors\__init__.py:43
- **Import**: `intelligence_processor` (from ... import get_intelligence_processor)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### processors\__init__.py:43
- **Import**: `intelligence_processor` (from ... import IntelligenceProcessor)
- **Contexto**: module_level

### processors\__init__.py:43
- **Import**: `intelligence_processor` (from ... import get_intelligence_processor)
- **Contexto**: module_level

### processors\__init__.py:70
- **Import**: `context_processor` (from ... import ContextProcessor)
- **Contexto**: function:get_context_processor > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### processors\__init__.py:70
- **Import**: `context_processor` (from ... import ContextProcessor)
- **Contexto**: function:get_context_processor
- ⚠️ **Dentro de função**

### processors\__init__.py:94
- **Import**: `query_processor` (from ... import QueryProcessor)
- **Contexto**: function:get_query_processor > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### processors\__init__.py:94
- **Import**: `query_processor` (from ... import QueryProcessor)
- **Contexto**: function:get_query_processor
- ⚠️ **Dentro de função**

### processors\__init__.py:123
- **Import**: `data_processor` (from ... import DataProcessor)
- **Contexto**: function:get_data_processor > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### processors\__init__.py:123
- **Import**: `data_processor` (from ... import DataProcessor)
- **Contexto**: function:get_data_processor
- ⚠️ **Dentro de função**

### processors\__init__.py:147
- **Import**: `intelligence_processor` (from ... import IntelligenceProcessor)
- **Contexto**: function:get_intelligence_processor > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### processors\__init__.py:147
- **Import**: `intelligence_processor` (from ... import IntelligenceProcessor)
- **Contexto**: function:get_intelligence_processor
- ⚠️ **Dentro de função**

### providers\context_provider.py:12
- **Import**: `hashlib`
- **Contexto**: module_level

### providers\data_provider.py:51
- **Import**: `time`
- **Contexto**: module_level

### providers\provider_manager.py:16
- **Import**: `dataclasses` (from ... import dataclass)
- **Contexto**: module_level

### providers\provider_manager.py:58
- **Import**: `context_provider` (from ... import ContextProvider)
- **Contexto**: class:ProviderManager > function:_initialize_providers > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### providers\provider_manager.py:58
- **Import**: `context_provider` (from ... import ContextProvider)
- **Contexto**: class:ProviderManager > function:_initialize_providers
- ⚠️ **Dentro de função**

### providers\provider_manager.py:65
- **Import**: `data_provider` (from ... import DataProvider)
- **Contexto**: class:ProviderManager > function:_initialize_providers > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### providers\provider_manager.py:65
- **Import**: `data_provider` (from ... import DataProvider)
- **Contexto**: class:ProviderManager > function:_initialize_providers
- ⚠️ **Dentro de função**

### providers\__init__.py:25
- **Import**: `provider_manager` (from ... import ProviderManager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### providers\__init__.py:25
- **Import**: `provider_manager` (from ... import get_provider_manager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### providers\__init__.py:25
- **Import**: `provider_manager` (from ... import ProviderRequest)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### providers\__init__.py:28
- **Import**: `context_provider` (from ... import ContextProvider)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### providers\__init__.py:28
- **Import**: `context_provider` (from ... import get_context_provider)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### providers\__init__.py:29
- **Import**: `data_provider` (from ... import DataProvider)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### providers\__init__.py:29
- **Import**: `data_provider` (from ... import get_data_provider)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### providers\__init__.py:32
- **Import**: `provider_manager` (from ... import provide_data)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### providers\__init__.py:32
- **Import**: `provider_manager` (from ... import provide_context)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### providers\__init__.py:25
- **Import**: `provider_manager` (from ... import ProviderManager)
- **Contexto**: module_level

### providers\__init__.py:25
- **Import**: `provider_manager` (from ... import get_provider_manager)
- **Contexto**: module_level

### providers\__init__.py:25
- **Import**: `provider_manager` (from ... import ProviderRequest)
- **Contexto**: module_level

### providers\__init__.py:28
- **Import**: `context_provider` (from ... import ContextProvider)
- **Contexto**: module_level

### providers\__init__.py:28
- **Import**: `context_provider` (from ... import get_context_provider)
- **Contexto**: module_level

### providers\__init__.py:29
- **Import**: `data_provider` (from ... import DataProvider)
- **Contexto**: module_level

### providers\__init__.py:29
- **Import**: `data_provider` (from ... import get_data_provider)
- **Contexto**: module_level

### providers\__init__.py:32
- **Import**: `provider_manager` (from ... import provide_data)
- **Contexto**: module_level

### providers\__init__.py:32
- **Import**: `provider_manager` (from ... import provide_context)
- **Contexto**: module_level

### scanning\database_scanner.py:45
- **Import**: `app` (from ... import db)
- **Contexto**: class:DatabaseScanner > function:discover_database_schema > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### scanning\database_scanner.py:45
- **Import**: `app` (from ... import db)
- **Contexto**: class:DatabaseScanner > function:discover_database_schema
- ⚠️ **Dentro de função**

### scanning\database_scanner.py:394
- **Import**: `app` (from ... import db)
- **Contexto**: class:DatabaseScanner > function:obter_estatisticas_gerais > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### scanning\database_scanner.py:394
- **Import**: `app` (from ... import db)
- **Contexto**: class:DatabaseScanner > function:obter_estatisticas_gerais
- ⚠️ **Dentro de função**

### scanning\structure_scanner.py:104
- **Import**: `app` (from ... import db)
- **Contexto**: class:StructureScanner > function:_discover_models_via_database > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### scanning\structure_scanner.py:104
- **Import**: `app` (from ... import db)
- **Contexto**: class:StructureScanner > function:_discover_models_via_database
- ⚠️ **Dentro de função**

### scanning\__init__.py:26
- **Import**: `scanning_manager` (from ... import ScanningManager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### scanning\__init__.py:26
- **Import**: `scanning_manager` (from ... import ScanningManager)
- **Contexto**: module_level

### scanning\__init__.py:32
- **Import**: `database_manager` (from ... import DatabaseManager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### scanning\__init__.py:32
- **Import**: `database_manager` (from ... import DatabaseManager)
- **Contexto**: module_level

### scanning\__init__.py:38
- **Import**: `project_scanner` (from ... import ProjectScanner)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### scanning\__init__.py:38
- **Import**: `project_scanner` (from ... import ProjectScanner)
- **Contexto**: module_level

### scanning\__init__.py:44
- **Import**: `database_scanner` (from ... import DatabaseScanner)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### scanning\__init__.py:44
- **Import**: `database_scanner` (from ... import DatabaseScanner)
- **Contexto**: module_level

### scanning\__init__.py:50
- **Import**: `code_scanner` (from ... import CodeScanner)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### scanning\__init__.py:50
- **Import**: `code_scanner` (from ... import CodeScanner)
- **Contexto**: module_level

### scanning\__init__.py:56
- **Import**: `file_scanner` (from ... import FileScanner)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### scanning\__init__.py:56
- **Import**: `file_scanner` (from ... import FileScanner)
- **Contexto**: module_level

### scanning\__init__.py:62
- **Import**: `structure_scanner` (from ... import StructureScanner)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### scanning\__init__.py:62
- **Import**: `structure_scanner` (from ... import StructureScanner)
- **Contexto**: module_level

### scanning\__init__.py:68
- **Import**: `readme_scanner` (from ... import ReadmeScanner)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### scanning\__init__.py:68
- **Import**: `readme_scanner` (from ... import ReadmeScanner)
- **Contexto**: module_level

### scanning\database\database_connection.py:84
- **Import**: `app` (from ... import create_app)
- **Contexto**: class:DatabaseConnection > function:_try_flask_connection > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### scanning\database\database_connection.py:84
- **Import**: `app` (from ... import db)
- **Contexto**: class:DatabaseConnection > function:_try_flask_connection > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### scanning\database\database_connection.py:84
- **Import**: `app` (from ... import create_app)
- **Contexto**: class:DatabaseConnection > function:_try_flask_connection
- ⚠️ **Dentro de função**

### scanning\database\database_connection.py:84
- **Import**: `app` (from ... import db)
- **Contexto**: class:DatabaseConnection > function:_try_flask_connection
- ⚠️ **Dentro de função**

### scanning\database\__init__.py:14
- **Import**: `database_connection` (from ... import DatabaseConnection)
- **Contexto**: module_level

### scanning\database\__init__.py:15
- **Import**: `metadata_scanner` (from ... import MetadataScanner)
- **Contexto**: module_level

### scanning\database\__init__.py:16
- **Import**: `data_analyzer` (from ... import DataAnalyzer)
- **Contexto**: module_level

### scanning\database\__init__.py:17
- **Import**: `relationship_mapper` (from ... import RelationshipMapper)
- **Contexto**: module_level

### scanning\database\__init__.py:18
- **Import**: `field_searcher` (from ... import FieldSearcher)
- **Contexto**: module_level

### scanning\database\__init__.py:19
- **Import**: `auto_mapper` (from ... import AutoMapper)
- **Contexto**: module_level

### security\security_guard.py:15
- **Import**: `hashlib`
- **Contexto**: module_level

### security\security_guard.py:20
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### security\security_guard.py:20
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: module_level

### security\__init__.py:25
- **Import**: `security_guard` (from ... import SecurityGuard)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### security\__init__.py:25
- **Import**: `security_guard` (from ... import get_security_guard)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### security\__init__.py:25
- **Import**: `security_guard` (from ... import validate_user_access)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### security\__init__.py:25
- **Import**: `security_guard` (from ... import validate_input)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### security\__init__.py:25
- **Import**: `security_guard` (from ... import sanitize_input)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### security\__init__.py:25
- **Import**: `security_guard` (from ... import SecurityGuard)
- **Contexto**: module_level

### security\__init__.py:25
- **Import**: `security_guard` (from ... import get_security_guard)
- **Contexto**: module_level

### security\__init__.py:25
- **Import**: `security_guard` (from ... import validate_user_access)
- **Contexto**: module_level

### security\__init__.py:25
- **Import**: `security_guard` (from ... import validate_input)
- **Contexto**: module_level

### security\__init__.py:25
- **Import**: `security_guard` (from ... import sanitize_input)
- **Contexto**: module_level

### suggestions\suggestions_manager.py:12
- **Import**: `hashlib`
- **Contexto**: module_level

### suggestions\suggestion_engine.py:10
- **Import**: `dataclasses` (from ... import dataclass)
- **Contexto**: module_level

### suggestions\suggestion_engine.py:12
- **Import**: `random`
- **Contexto**: module_level

### suggestions\suggestion_engine.py:438
- **Import**: `app` (from ... import db)
- **Contexto**: class:SuggestionsEngine > function:_get_data_analyzer > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### suggestions\suggestion_engine.py:438
- **Import**: `app` (from ... import db)
- **Contexto**: class:SuggestionsEngine > function:_get_data_analyzer
- ⚠️ **Dentro de função**

### suggestions\__init__.py:15
- **Import**: `suggestion_engine` (from ... import SuggestionsEngine)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### suggestions\__init__.py:15
- **Import**: `suggestion_engine` (from ... import get_suggestions_engine)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### suggestions\__init__.py:15
- **Import**: `suggestion_engine` (from ... import SuggestionsEngine)
- **Contexto**: module_level

### suggestions\__init__.py:15
- **Import**: `suggestion_engine` (from ... import get_suggestions_engine)
- **Contexto**: module_level

### suggestions\__init__.py:22
- **Import**: `suggestions_manager` (from ... import SuggestionsManager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### suggestions\__init__.py:22
- **Import**: `suggestions_manager` (from ... import get_suggestions_manager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### suggestions\__init__.py:22
- **Import**: `suggestions_manager` (from ... import SuggestionsManager)
- **Contexto**: module_level

### suggestions\__init__.py:22
- **Import**: `suggestions_manager` (from ... import get_suggestions_manager)
- **Contexto**: module_level

### suggestions\__init__.py:47
- **Import**: `suggestion_engine` (from ... import SuggestionsEngine)
- **Contexto**: function:get_suggestions_engine > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### suggestions\__init__.py:47
- **Import**: `suggestion_engine` (from ... import SuggestionsEngine)
- **Contexto**: function:get_suggestions_engine
- ⚠️ **Dentro de função**

### suggestions\__init__.py:71
- **Import**: `suggestions_manager` (from ... import SuggestionsManager)
- **Contexto**: function:get_suggestions_manager > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### suggestions\__init__.py:71
- **Import**: `suggestions_manager` (from ... import SuggestionsManager)
- **Contexto**: function:get_suggestions_manager
- ⚠️ **Dentro de função**

### tests\test_loop_prevention.py:9
- **Import**: `time`
- **Contexto**: module_level

### tests\test_loop_prevention.py:10
- **Import**: `threading`
- **Contexto**: module_level

### tools\__init__.py:1
- **Import**: `tools_manager` (from ... import ToolsManager)
- **Contexto**: module_level

### tools\__init__.py:1
- **Import**: `tools_manager` (from ... import get_toolsmanager)
- **Contexto**: module_level

### utils\agent_types.py:7
- **Import**: `enum` (from ... import Enum)
- **Contexto**: module_level

### utils\agent_types.py:9
- **Import**: `dataclasses` (from ... import dataclass)
- **Contexto**: module_level

### utils\base_classes.py:16
- **Import**: `time`
- **Contexto**: module_level

### utils\base_classes.py:23
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: module_level

### utils\base_classes.py:29
- **Import**: `app` (from ... import db)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\base_classes.py:29
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### utils\base_classes.py:367
- **Import**: `hashlib`
- **Contexto**: class:BaseProcessor > function:_generate_cache_key
- ⚠️ **Dentro de função**

### utils\flask_context_wrapper.py:53
- **Import**: `app` (from ... import db)
- **Contexto**: class:FlaskContextWrapper > function:get_db_session > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### utils\flask_context_wrapper.py:53
- **Import**: `app` (from ... import db)
- **Contexto**: class:FlaskContextWrapper > function:get_db_session
- ⚠️ **Dentro de função**

### utils\flask_fallback.py:189
- **Import**: `app` (from ... import db)
- **Contexto**: class:FlaskFallback > function:get_db > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### utils\flask_fallback.py:189
- **Import**: `app` (from ... import db)
- **Contexto**: class:FlaskFallback > function:get_db > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### utils\flask_fallback.py:189
- **Import**: `app` (from ... import db)
- **Contexto**: class:FlaskFallback > function:get_db > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### utils\flask_fallback.py:189
- **Import**: `app` (from ... import db)
- **Contexto**: class:FlaskFallback > function:get_db
- ⚠️ **Dentro de função**

### utils\flask_fallback.py:221
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: class:FlaskFallback > function:get_current_user > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### utils\flask_fallback.py:221
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: class:FlaskFallback > function:get_current_user
- ⚠️ **Dentro de função**

### utils\performance_cache.py:15
- **Import**: `threading`
- **Contexto**: module_level

### utils\performance_cache.py:16
- **Import**: `time`
- **Contexto**: module_level

### utils\performance_cache.py:17
- **Import**: `weakref`
- **Contexto**: module_level

### utils\response_utils.py:12
- **Import**: `flask_login` (from ... import current_user)
- **Contexto**: module_level

### utils\response_utils.py:14
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### utils\response_utils.py:24
- **Import**: `time`
- **Contexto**: module_level

### utils\response_utils.py:28
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### utils\response_utils.py:35
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### utils\response_utils.py:37
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### utils\response_utils.py:40
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### utils\response_utils.py:42
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### utils\response_utils.py:48
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### utils\response_utils.py:52
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### utils\response_utils.py:61
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### utils\response_utils.py:64
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### utils\response_utils.py:67
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### utils\response_utils.py:69
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### utils\response_utils.py:72
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### utils\response_utils.py:74
- **Import**: `app` (from ... import db)
- **Contexto**: module_level

### utils\utils_manager.py:14
- **Import**: `response_utils` (from ... import ResponseUtils)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\utils_manager.py:14
- **Import**: `response_utils` (from ... import ResponseUtils)
- **Contexto**: module_level

### utils\utils_manager.py:21
- **Import**: `validation_utils` (from ... import BaseValidationUtils)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\utils_manager.py:21
- **Import**: `validation_utils` (from ... import BaseValidationUtils)
- **Contexto**: module_level

### utils\utils_manager.py:63
- **Import**: `app` (from ... import db)
- **Contexto**: class:FlaskContextWrapper > function:_get_db_session > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### utils\utils_manager.py:63
- **Import**: `app` (from ... import db)
- **Contexto**: class:FlaskContextWrapper > function:_get_db_session
- ⚠️ **Dentro de função**

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import FlaskFallback)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import get_flask_fallback)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import is_flask_available)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import get_app)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import get_model)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import get_db)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import get_current_user)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import get_config)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import FlaskFallback)
- **Contexto**: module_level

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import get_flask_fallback)
- **Contexto**: module_level

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import is_flask_available)
- **Contexto**: module_level

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import get_app)
- **Contexto**: module_level

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import get_model)
- **Contexto**: module_level

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import get_db)
- **Contexto**: module_level

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import get_current_user)
- **Contexto**: module_level

### utils\__init__.py:14
- **Import**: `flask_fallback` (from ... import get_config)
- **Contexto**: module_level

### utils\__init__.py:31
- **Import**: `utils_manager` (from ... import UtilsManager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:31
- **Import**: `utils_manager` (from ... import get_utilsmanager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:31
- **Import**: `utils_manager` (from ... import UtilsManager)
- **Contexto**: module_level

### utils\__init__.py:31
- **Import**: `utils_manager` (from ... import get_utilsmanager)
- **Contexto**: module_level

### utils\__init__.py:38
- **Import**: `data_manager` (from ... import DataManager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:38
- **Import**: `data_manager` (from ... import get_datamanager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:38
- **Import**: `data_manager` (from ... import DataManager)
- **Contexto**: module_level

### utils\__init__.py:38
- **Import**: `data_manager` (from ... import get_datamanager)
- **Contexto**: module_level

### utils\__init__.py:45
- **Import**: `base_context_manager` (from ... import BaseContextManager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:45
- **Import**: `base_context_manager` (from ... import BaseContextManager)
- **Contexto**: module_level

### utils\__init__.py:53
- **Import**: `base_classes` (from ... import BaseOrchestrator)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:53
- **Import**: `base_classes` (from ... import BaseProcessor)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:53
- **Import**: `base_classes` (from ... import BaseOrchestrator)
- **Contexto**: module_level

### utils\__init__.py:53
- **Import**: `base_classes` (from ... import BaseProcessor)
- **Contexto**: module_level

### utils\__init__.py:61
- **Import**: `agent_types` (from ... import AgentType)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:61
- **Import**: `agent_types` (from ... import AgentResponse)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:61
- **Import**: `agent_types` (from ... import ValidationResult)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:61
- **Import**: `agent_types` (from ... import OperationRecord)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:61
- **Import**: `agent_types` (from ... import AgentType)
- **Contexto**: module_level

### utils\__init__.py:61
- **Import**: `agent_types` (from ... import AgentResponse)
- **Contexto**: module_level

### utils\__init__.py:61
- **Import**: `agent_types` (from ... import ValidationResult)
- **Contexto**: module_level

### utils\__init__.py:61
- **Import**: `agent_types` (from ... import OperationRecord)
- **Contexto**: module_level

### utils\__init__.py:69
- **Import**: `response_utils` (from ... import ResponseUtils)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:69
- **Import**: `response_utils` (from ... import ResponseUtils)
- **Contexto**: module_level

### utils\__init__.py:76
- **Import**: `validation_utils` (from ... import BaseValidationUtils)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:76
- **Import**: `validation_utils` (from ... import get_validation_utils)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:76
- **Import**: `validation_utils` (from ... import BaseValidationUtils)
- **Contexto**: module_level

### utils\__init__.py:76
- **Import**: `validation_utils` (from ... import get_validation_utils)
- **Contexto**: module_level

### utils\__init__.py:83
- **Import**: `performance_cache` (from ... import ScannersCache)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:83
- **Import**: `performance_cache` (from ... import ScannersCache)
- **Contexto**: module_level

### utils\__init__.py:90
- **Import**: `processor_registry` (from ... import ProcessorRegistry)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:90
- **Import**: `processor_registry` (from ... import ProcessorRegistry)
- **Contexto**: module_level

### utils\__init__.py:97
- **Import**: `flask_context_wrapper` (from ... import FlaskContextWrapper)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:97
- **Import**: `flask_context_wrapper` (from ... import FlaskContextWrapper)
- **Contexto**: module_level

### utils\__init__.py:104
- **Import**: `legacy_compatibility` (from ... import ExternalAPIIntegration)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### utils\__init__.py:104
- **Import**: `legacy_compatibility` (from ... import ExternalAPIIntegration)
- **Contexto**: module_level

### validators\data_validator.py:50
- **Import**: `time`
- **Contexto**: module_level

### validators\validator_manager.py:51
- **Import**: `semantic_validator` (from ... import SemanticValidator)
- **Contexto**: class:ValidatorManager > function:_init_validators > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### validators\validator_manager.py:51
- **Import**: `semantic_validator` (from ... import SemanticValidator)
- **Contexto**: class:ValidatorManager > function:_init_validators
- ⚠️ **Dentro de função**

### validators\validator_manager.py:61
- **Import**: `data_validator` (from ... import ValidationUtils)
- **Contexto**: class:ValidatorManager > function:_init_validators > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### validators\validator_manager.py:61
- **Import**: `data_validator` (from ... import ValidationUtils)
- **Contexto**: class:ValidatorManager > function:_init_validators
- ⚠️ **Dentro de função**

### validators\validator_manager.py:68
- **Import**: `critic_validator` (from ... import CriticAgent)
- **Contexto**: class:ValidatorManager > function:_init_validators > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### validators\validator_manager.py:68
- **Import**: `critic_validator` (from ... import CriticAgent)
- **Contexto**: class:ValidatorManager > function:_init_validators
- ⚠️ **Dentro de função**

### validators\validator_manager.py:78
- **Import**: `structural_validator` (from ... import StructuralAI)
- **Contexto**: class:ValidatorManager > function:_init_validators > in_try
- ⚠️ **Dentro de função**
- ⚠️ **Dentro de try/except**

### validators\validator_manager.py:78
- **Import**: `structural_validator` (from ... import StructuralAI)
- **Contexto**: class:ValidatorManager > function:_init_validators
- ⚠️ **Dentro de função**

### validators\__init__.py:10
- **Import**: `semantic_validator` (from ... import SemanticValidator)
- **Contexto**: module_level

### validators\__init__.py:11
- **Import**: `structural_validator` (from ... import StructuralAI)
- **Contexto**: module_level

### validators\__init__.py:12
- **Import**: `critic_validator` (from ... import CriticAgent)
- **Contexto**: module_level

### validators\__init__.py:13
- **Import**: `data_validator` (from ... import ValidationUtils)
- **Contexto**: module_level

### validators\__init__.py:14
- **Import**: `validator_manager` (from ... import ValidatorManager)
- **Contexto**: module_level

### validators\__init__.py:23
- **Import**: `semantic_validator` (from ... import SemanticValidator)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### validators\__init__.py:23
- **Import**: `semantic_validator` (from ... import SemanticValidator)
- **Contexto**: module_level

### validators\__init__.py:29
- **Import**: `structural_validator` (from ... import StructuralAI)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### validators\__init__.py:29
- **Import**: `structural_validator` (from ... import StructuralAI)
- **Contexto**: module_level

### validators\__init__.py:35
- **Import**: `critic_validator` (from ... import CriticAgent)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### validators\__init__.py:35
- **Import**: `critic_validator` (from ... import CriticAgent)
- **Contexto**: module_level

### validators\__init__.py:41
- **Import**: `data_validator` (from ... import ValidationUtils)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### validators\__init__.py:41
- **Import**: `data_validator` (from ... import ValidationUtils)
- **Contexto**: module_level

### validators\__init__.py:47
- **Import**: `validator_manager` (from ... import ValidatorManager)
- **Contexto**: in_try
- ⚠️ **Dentro de try/except**

### validators\__init__.py:47
- **Import**: `validator_manager` (from ... import ValidatorManager)
- **Contexto**: module_level

## 🔧 PLACEHOLDERS E FALLBACKS

### conversers\conversation_manager.py:20
- **Tipo**: mock_assignment
- **Variável**: `get_context_memory`
- **Contexto**: in_except

### conversers\conversation_manager.py:21
- **Tipo**: mock_assignment
- **Variável**: `get_conversation_memory`
- **Contexto**: in_except

### integration\external_api_integration.py:466
- **Tipo**: none_assignment
- **Variável**: `_claude_client`
- **Contexto**: function:get_claude_client > in_except

### memorizers\context_memory.py:23
- **Tipo**: mock_assignment
- **Variável**: `redis_cache`
- **Contexto**: in_except

### memorizers\context_memory.py:25
- **Tipo**: mock_assignment
- **Variável**: `current_user`
- **Contexto**: in_except

### memorizers\system_memory.py:22
- **Tipo**: mock_assignment
- **Variável**: `redis_cache`
- **Contexto**: in_except

### memorizers\system_memory.py:24
- **Tipo**: mock_assignment
- **Variável**: `ClaudeAIConfig`
- **Contexto**: in_except

### memorizers\system_memory.py:24
- **Tipo**: mock_assignment
- **Variável**: `AdvancedConfig`
- **Contexto**: in_except

### processors\context_processor.py:18
- **Tipo**: none_assignment
- **Variável**: `current_user`
- **Contexto**: in_except

### processors\context_processor.py:19
- **Tipo**: none_assignment
- **Variável**: `db`
- **Contexto**: in_except

### processors\context_processor.py:20
- **Tipo**: none_assignment
- **Variável**: `func`
- **Contexto**: in_except

### processors\context_processor.py:20
- **Tipo**: none_assignment
- **Variável**: `and_`
- **Contexto**: in_except

### processors\context_processor.py:20
- **Tipo**: none_assignment
- **Variável**: `or_`
- **Contexto**: in_except

### processors\context_processor.py:20
- **Tipo**: none_assignment
- **Variável**: `text`
- **Contexto**: in_except

### processors\context_processor.py:36
- **Tipo**: none_assignment
- **Variável**: `Frete`
- **Contexto**: in_except

### processors\context_processor.py:36
- **Tipo**: none_assignment
- **Variável**: `Embarque`
- **Contexto**: in_except

### processors\context_processor.py:36
- **Tipo**: none_assignment
- **Variável**: `EmbarqueItem`
- **Contexto**: in_except

### processors\context_processor.py:36
- **Tipo**: none_assignment
- **Variável**: `Transportadora`
- **Contexto**: in_except

### processors\context_processor.py:37
- **Tipo**: none_assignment
- **Variável**: `Pedido`
- **Contexto**: in_except

### processors\context_processor.py:37
- **Tipo**: none_assignment
- **Variável**: `EntregaMonitorada`
- **Contexto**: in_except

### processors\context_processor.py:37
- **Tipo**: none_assignment
- **Variável**: `AgendamentoEntrega`
- **Contexto**: in_except

### processors\context_processor.py:38
- **Tipo**: none_assignment
- **Variável**: `RelatorioFaturamentoImportado`
- **Contexto**: in_except

### processors\context_processor.py:38
- **Tipo**: none_assignment
- **Variável**: `PendenciaFinanceiraNF`
- **Contexto**: in_except

### processors\context_processor.py:38
- **Tipo**: none_assignment
- **Variável**: `DespesaExtra`
- **Contexto**: in_except

### processors\response_processor.py:27
- **Tipo**: none_assignment
- **Variável**: `current_user`
- **Contexto**: in_except

### processors\response_processor.py:28
- **Tipo**: none_assignment
- **Variável**: `db`
- **Contexto**: in_except

### processors\response_processor.py:29
- **Tipo**: none_assignment
- **Variável**: `func`
- **Contexto**: in_except

### processors\response_processor.py:29
- **Tipo**: none_assignment
- **Variável**: `and_`
- **Contexto**: in_except

### processors\response_processor.py:29
- **Tipo**: none_assignment
- **Variável**: `or_`
- **Contexto**: in_except

### processors\response_processor.py:29
- **Tipo**: none_assignment
- **Variável**: `text`
- **Contexto**: in_except

### processors\semantic_loop_processor.py:16
- **Tipo**: none_assignment
- **Variável**: `get_semantic_mapper`
- **Contexto**: in_except

### providers\data_provider.py:39
- **Tipo**: mock_assignment
- **Variável**: `db`
- **Contexto**: in_except

### providers\data_provider.py:40
- **Tipo**: mock_assignment
- **Variável**: `current_user`
- **Contexto**: in_except

### providers\data_provider.py:43
- **Tipo**: mock_assignment
- **Variável**: `redis_cache`
- **Contexto**: in_except

### providers\data_provider.py:43
- **Tipo**: mock_assignment
- **Variável**: `cache_aside`
- **Contexto**: in_except

### providers\data_provider.py:43
- **Tipo**: mock_assignment
- **Variável**: `cached_query`
- **Contexto**: in_except

### providers\data_provider.py:44
- **Tipo**: mock_assignment
- **Variável**: `GrupoEmpresarialDetector`
- **Contexto**: in_except

### providers\data_provider.py:44
- **Tipo**: mock_assignment
- **Variável**: `detectar_grupo_empresarial`
- **Contexto**: in_except

### providers\data_provider.py:45
- **Tipo**: mock_assignment
- **Variável**: `get_ml_models_system`
- **Contexto**: in_except

### providers\data_provider.py:45
- **Tipo**: mock_assignment
- **Variável**: `get_system_alerts`
- **Contexto**: in_except

### providers\data_provider.py:46
- **Tipo**: mock_assignment
- **Variável**: `ClaudeAIConfig`
- **Contexto**: in_except

### providers\data_provider.py:46
- **Tipo**: mock_assignment
- **Variável**: `AdvancedConfig`
- **Contexto**: in_except

### providers\data_provider.py:46
- **Tipo**: mock_assignment
- **Variável**: `ai_logger`
- **Contexto**: in_except

### providers\data_provider.py:46
- **Tipo**: mock_assignment
- **Variável**: `AILogger`
- **Contexto**: in_except

### security\security_guard.py:24
- **Tipo**: mock_assignment
- **Variável**: `current_user`
- **Contexto**: in_except

### utils\base_classes.py:33
- **Tipo**: none_assignment
- **Variável**: `db`
- **Contexto**: in_except

### utils\processor_registry.py:124
- **Tipo**: none_assignment
- **Variável**: `processor_instance`
- **Contexto**: class:ProcessorRegistry > function:_register_processor > in_try > in_except

### utils\processor_registry.py:124
- **Tipo**: none_assignment
- **Variável**: `processor_instance`
- **Contexto**: class:ProcessorRegistry > function:_register_processor > in_try > in_except

### utils\processor_registry.py:124
- **Tipo**: none_assignment
- **Variável**: `processor_instance`
- **Contexto**: class:ProcessorRegistry > function:_register_processor > in_except

### utils\processor_registry.py:124
- **Tipo**: none_assignment
- **Variável**: `processor_instance`
- **Contexto**: class:ProcessorRegistry > function:_register_processor > in_except

### utils\utils_manager.py:18
- **Tipo**: none_assignment
- **Variável**: `ResponseUtils`
- **Contexto**: in_except

### utils\utils_manager.py:25
- **Tipo**: none_assignment
- **Variável**: `BaseValidationUtils`
- **Contexto**: in_except

### utils\__init__.py:109
- **Tipo**: none_assignment
- **Variável**: `LegacyCompatibility`
- **Contexto**: in_except

### validators\data_validator.py:37
- **Tipo**: mock_assignment
- **Variável**: `db`
- **Contexto**: in_except

### validators\data_validator.py:38
- **Tipo**: mock_assignment
- **Variável**: `current_user`
- **Contexto**: in_except

### validators\data_validator.py:41
- **Tipo**: mock_assignment
- **Variável**: `redis_cache`
- **Contexto**: in_except

### validators\data_validator.py:41
- **Tipo**: mock_assignment
- **Variável**: `cache_aside`
- **Contexto**: in_except

### validators\data_validator.py:41
- **Tipo**: mock_assignment
- **Variável**: `cached_query`
- **Contexto**: in_except

### validators\data_validator.py:42
- **Tipo**: mock_assignment
- **Variável**: `GrupoEmpresarialDetector`
- **Contexto**: in_except

### validators\data_validator.py:42
- **Tipo**: mock_assignment
- **Variável**: `detectar_grupo_empresarial`
- **Contexto**: in_except

### validators\data_validator.py:43
- **Tipo**: mock_assignment
- **Variável**: `get_ml_models_system`
- **Contexto**: in_except

### validators\data_validator.py:43
- **Tipo**: mock_assignment
- **Variável**: `get_system_alerts`
- **Contexto**: in_except

### validators\data_validator.py:44
- **Tipo**: mock_assignment
- **Variável**: `ClaudeAIConfig`
- **Contexto**: in_except

### validators\data_validator.py:44
- **Tipo**: mock_assignment
- **Variável**: `AdvancedConfig`
- **Contexto**: in_except

### validators\data_validator.py:44
- **Tipo**: mock_assignment
- **Variável**: `ai_logger`
- **Contexto**: in_except

### validators\data_validator.py:44
- **Tipo**: mock_assignment
- **Variável**: `AILogger`
- **Contexto**: in_except

### validators\data_validator.py:192
- **Tipo**: none_assignment
- **Variável**: `claude`
- **Contexto**: class:ValidationUtils > function:_calcular_estatisticas_por_dominio > in_try > in_except

### validators\data_validator.py:192
- **Tipo**: none_assignment
- **Variável**: `claude`
- **Contexto**: class:ValidationUtils > function:_calcular_estatisticas_por_dominio > in_except

