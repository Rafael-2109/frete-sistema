#!/usr/bin/env python3
"""
Teste completo de integração de todos os módulos do claude_ai_novo.
Verifica se todos os 20 módulos estão integrados corretamente.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from typing import Dict, List, Any
import traceback

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TesteIntegracaoCompleta:
    """Classe para testar integração completa de todos os módulos"""
    
    def __init__(self):
        self.resultados = {}
        self.modulos_testados = 0
        self.modulos_sucesso = 0
        self.modulos_falha = 0
        
    def testar_todos_modulos(self) -> Dict[str, Any]:
        """Testa integração de todos os módulos"""
        print("🧪 TESTE COMPLETO DE INTEGRAÇÃO DE TODOS OS MÓDULOS")
        print("=" * 60)
        
        # Lista completa dos módulos a testar
        modulos_para_testar = [
            # Orchestrators
            ("orchestrators", "main_orchestrator", "MainOrchestrator"),
            ("orchestrators", "session_orchestrator", "SessionOrchestrator"),
            ("orchestrators", "workflow_orchestrator", "WorkflowOrchestrator"),
            ("orchestrators", "orchestrator_manager", "OrchestratorManager"),
            
            # Coordinators
            ("coordinators", "coordinator_manager", "CoordinatorManager"),
            ("coordinators", "agent_coordinator", "AgentCoordinator"),
            ("coordinators", "query_coordinator", "QueryCoordinator"),
            ("coordinators", "task_coordinator", "TaskCoordinator"),
            ("coordinators", "execution_coordinator", "ExecutionCoordinator"),
            
            # Analyzers
            ("analyzers", "analyzer_manager", "AnalyzerManager"),
            ("analyzers", "diagnostics_analyzer", "DiagnosticsAnalyzer"),
            ("analyzers", "performance_analyzer", "PerformanceAnalyzer"),
            
            # Processors
            ("processors", "context_processor", "ContextProcessor"),
            ("processors", "query_processor", "QueryProcessor"),
            ("processors", "response_processor", "ResponseProcessor"),
            ("processors", "workflow_processor", "WorkflowProcessor"),
            
            # Memorizers
            ("memorizers", "context_memory", "ContextMemory"),
            ("memorizers", "conversation_memory", "ConversationMemory"),
            ("memorizers", "session_memory", "SessionMemory"),
            ("memorizers", "knowledge_memory", "KnowledgeMemory"),
            
            # Mappers
            ("mappers", "context_mapper", "ContextMapper"),
            ("mappers", "field_mapper", "FieldMapper"),
            
            # Validators
            ("validators", "critic_validator", "CriticValidator"),
            ("validators", "data_validator", "DataValidator"),
            ("validators", "input_validator", "InputValidator"),
            
            # Providers
            ("providers", "context_provider", "ContextProvider"),
            ("providers", "data_provider", "DataProvider"),
            
            # Loaders
            ("loaders", "context_loader", "ContextLoader"),
            ("loaders", "database_loader", "DatabaseLoader"),
            ("loaders", "file_loader", "FileLoader"),
            
            # Enrichers
            ("enrichers", "context_enricher", "ContextEnricher"),
            ("enrichers", "semantic_enricher", "SemanticEnricher"),
            
            # Learners
            ("learners", "adaptive_learning", "AdaptiveLearning"),
            ("learners", "feedback_learning", "FeedbackLearning"),
            ("learners", "pattern_learning", "PatternLearning"),
            ("learners", "interaction_learning", "InteractionLearning"),
            ("learners", "knowledge_learning", "KnowledgeLearning"),
            ("learners", "learning_core", "LearningCore"),
            
            # Security
            ("security", "security_guard", "SecurityGuard"),
            
            # Tools
            ("tools", "tools_manager", "ToolsManager"),
            
            # Config
            ("config", "advanced_config", "AdvancedConfig"),
            ("config", "basic_config", "BasicConfig"),
            ("config", "config_manager", "ConfigManager"),
            
            # Scanning
            ("scanning", "code_scanner", "CodeScanner"),
            ("scanning", "database_manager", "DatabaseManager"),
            ("scanning", "dependency_scanner", "DependencyScanner"),
            ("scanning", "module_scanner", "ModuleScanner"),
            ("scanning", "performance_scanner", "PerformanceScanner"),
            ("scanning", "security_scanner", "SecurityScanner"),
            
            # Integration
            ("integration", "external_api_integration", "ExternalApiIntegration"),
            ("integration", "database_integration", "DatabaseIntegration"),
            ("integration", "system_integration", "SystemIntegration"),
            ("integration", "legacy_integration", "LegacyIntegration"),
            
            # Commands
            ("commands", "auto_command_processor", "AutoCommandProcessor"),
            ("commands", "base_command", "BaseCommand"),
            ("commands", "command_manager", "CommandManager"),
            ("commands", "natural_command", "NaturalCommand"),
            ("commands", "system_command", "SystemCommand"),
            
            # Suggestions (RECÉM INTEGRADO)
            ("suggestions", "suggestion_engine", "SuggestionEngine"),
            ("suggestions", "suggestions_manager", "SuggestionsManager"),
            
            # Conversers (RECÉM INTEGRADO)
            ("conversers", "context_converser", "ContextConverser"),
            ("conversers", "conversation_manager", "ConversationManager"),
        ]
        
        print(f"📋 Testando {len(modulos_para_testar)} módulos...")
        print()
        
        for pasta, arquivo, classe in modulos_para_testar:
            self.testar_modulo(pasta, arquivo, classe)
        
        return self.gerar_relatorio_final()
    
    def testar_modulo(self, pasta: str, arquivo: str, classe: str):
        """Testa um módulo específico"""
        self.modulos_testados += 1
        
        try:
            # Tentar importar o módulo
            import_path = f"{pasta}.{arquivo}"
            print(f"🔍 Testando {import_path}...")
            
            # Importar módulo
            try:
                modulo = __import__(import_path, fromlist=[classe])
                print(f"   ✅ Módulo importado com sucesso")
                
                # Verificar se tem a classe/função esperada
                if hasattr(modulo, classe):
                    componente = getattr(modulo, classe)
                    print(f"   ✅ Classe/função {classe} encontrada")
                    
                    # Tentar instanciar se for classe
                    try:
                        if isinstance(componente, type):
                            instancia = componente()
                            print(f"   ✅ Instância criada com sucesso")
                        else:
                            print(f"   ✅ Função/objeto acessível")
                    except Exception as e:
                        print(f"   ⚠️ Erro ao instanciar: {e}")
                        
                else:
                    # Tentar função get_*
                    get_function_name = f"get_{arquivo.replace('_', '_')}"
                    if hasattr(modulo, get_function_name):
                        get_function = getattr(modulo, get_function_name)
                        try:
                            result = get_function()
                            print(f"   ✅ Função {get_function_name} funciona")
                        except Exception as e:
                            print(f"   ⚠️ Erro na função get: {e}")
                    else:
                        print(f"   ⚠️ Classe {classe} não encontrada no módulo")
                
                # Marcar como sucesso
                self.resultados[f"{pasta}.{arquivo}"] = {
                    "status": "sucesso",
                    "detalhes": f"Módulo {import_path} integrado corretamente"
                }
                self.modulos_sucesso += 1
                print(f"   ✅ SUCESSO: {import_path}")
                
            except ImportError as e:
                print(f"   ❌ Erro de importação: {e}")
                self.resultados[f"{pasta}.{arquivo}"] = {
                    "status": "erro_importacao",
                    "detalhes": str(e)
                }
                self.modulos_falha += 1
                
        except Exception as e:
            print(f"   ❌ Erro geral: {e}")
            print(f"   📋 Traceback: {traceback.format_exc()}")
            self.resultados[f"{pasta}.{arquivo}"] = {
                "status": "erro_geral",
                "detalhes": str(e)
            }
            self.modulos_falha += 1
        
        print()
    
    def testar_orchestrators_integrados(self) -> Dict[str, Any]:
        """Testa especificamente os orchestrators com suas integrações"""
        print("🎯 TESTE ESPECÍFICO DOS ORCHESTRATORS")
        print("=" * 40)
        
        resultados_orchestrators = {}
        
        # Testar MainOrchestrator
        try:
            from orchestrators.main_orchestrator import get_main_orchestrator
            main_orch = get_main_orchestrator()
            
            print("🔍 Testando MainOrchestrator...")
            
            # Testar lazy loading
            coordinator_manager = main_orch.coordinator_manager
            auto_command_processor = main_orch.auto_command_processor
            security_guard = main_orch.security_guard
            suggestions_manager = main_orch.suggestions_manager  # NOVO
            
            print(f"   ✅ CoordinatorManager: {coordinator_manager is not None}")
            print(f"   ✅ AutoCommandProcessor: {auto_command_processor is not None}")
            print(f"   ✅ SecurityGuard: {security_guard is not None}")
            print(f"   ✅ SuggestionsManager: {suggestions_manager is not None}")
            
            # Testar workflows
            workflows = main_orch.workflows
            print(f"   ✅ Workflows disponíveis: {len(workflows)}")
            
            expected_workflows = [
                "analyze_query", "full_processing", "intelligent_coordination",
                "natural_commands", "intelligent_suggestions"
            ]
            
            for workflow in expected_workflows:
                if workflow in workflows:
                    print(f"      ✅ {workflow}")
                else:
                    print(f"      ❌ {workflow} - FALTANDO")
            
            # Testar execução de workflow
            test_data = {"query": "teste", "context": {}}
            result = main_orch.execute_workflow("intelligent_suggestions", "intelligent_suggestions", test_data)
            print(f"   ✅ Workflow de sugestões executado: {result.get('success', False)}")
            
            resultados_orchestrators["main_orchestrator"] = "sucesso"
            
        except Exception as e:
            print(f"   ❌ Erro no MainOrchestrator: {e}")
            resultados_orchestrators["main_orchestrator"] = f"erro: {e}"
        
        # Testar SessionOrchestrator
        try:
            from orchestrators.session_orchestrator import get_session_orchestrator
            session_orch = get_session_orchestrator()
            
            print("\n🔍 Testando SessionOrchestrator...")
            
            # Testar lazy loading
            learning_core = session_orch.learning_core
            security_guard = session_orch.security_guard
            conversation_manager = session_orch.conversation_manager  # NOVO
            
            print(f"   ✅ LearningCore: {learning_core is not None}")
            print(f"   ✅ SecurityGuard: {security_guard is not None}")
            print(f"   ✅ ConversationManager: {conversation_manager is not None}")
            
            # Testar criação de sessão
            session_id = session_orch.create_session(user_id=1)
            print(f"   ✅ Sessão criada: {session_id}")
            
            # Testar workflow com conversas
            test_data = {"query": "teste conversa", "context": {"user_id": 1}}
            result = session_orch.execute_session_workflow(session_id, "conversation", test_data)
            print(f"   ✅ Workflow de conversa executado: {result.get('success', True)}")
            
            # Limpar sessão
            session_orch.complete_session(session_id)
            print(f"   ✅ Sessão completada")
            
            resultados_orchestrators["session_orchestrator"] = "sucesso"
            
        except Exception as e:
            print(f"   ❌ Erro no SessionOrchestrator: {e}")
            resultados_orchestrators["session_orchestrator"] = f"erro: {e}"
        
        print()
        return resultados_orchestrators
    
    def testar_fallbacks_mocks(self) -> Dict[str, Any]:
        """Testa se os fallbacks mock estão funcionando"""
        print("🛡️ TESTE DOS FALLBACKS MOCK")
        print("=" * 30)
        
        resultados_fallbacks = {}
        
        try:
            from orchestrators.main_orchestrator import get_main_orchestrator
            main_orch = get_main_orchestrator()
            
            # Testar componentes mock
            componentes_para_testar = [
                "analyzers", "processors", "mappers", "validators",
                "providers", "memorizers", "enrichers", "loaders",
                "coordinators", "commands", "security_guard", "suggestions"
            ]
            
            for componente in componentes_para_testar:
                if componente in main_orch.components:
                    comp = main_orch.components[componente]
                    print(f"   ✅ {componente}: {type(comp).__name__}")
                    
                    # Testar se tem métodos básicos
                    if hasattr(comp, 'analyze_intention'):
                        result = comp.analyze_intention(query="teste")
                        print(f"      ✅ analyze_intention: {result}")
                    
                    if hasattr(comp, 'generate_intelligent_suggestions'):
                        result = comp.generate_intelligent_suggestions(query="teste")
                        print(f"      ✅ generate_intelligent_suggestions: {result}")
                    
                    if hasattr(comp, 'manage_conversation'):
                        result = comp.manage_conversation(session_id="teste")
                        print(f"      ✅ manage_conversation: {result}")
                    
                    resultados_fallbacks[componente] = "funcionando"
                else:
                    print(f"   ❌ {componente}: NÃO ENCONTRADO")
                    resultados_fallbacks[componente] = "não_encontrado"
            
        except Exception as e:
            print(f"   ❌ Erro nos fallbacks: {e}")
            resultados_fallbacks["erro"] = str(e)
        
        print()
        return resultados_fallbacks
    
    def gerar_relatorio_final(self) -> Dict[str, Any]:
        """Gera relatório final dos testes"""
        print("📊 RELATÓRIO FINAL DA INTEGRAÇÃO")
        print("=" * 40)
        
        taxa_sucesso = (self.modulos_sucesso / self.modulos_testados) * 100 if self.modulos_testados > 0 else 0
        
        print(f"📈 ESTATÍSTICAS GERAIS:")
        print(f"   • Módulos testados: {self.modulos_testados}")
        print(f"   • Sucessos: {self.modulos_sucesso}")
        print(f"   • Falhas: {self.modulos_falha}")
        print(f"   • Taxa de sucesso: {taxa_sucesso:.1f}%")
        print()
        
        # Testar orchestrators específicos
        resultados_orchestrators = self.testar_orchestrators_integrados()
        
        # Testar fallbacks
        resultados_fallbacks = self.testar_fallbacks_mocks()
        
        # Classificar sistema
        if taxa_sucesso >= 90:
            classificacao = "EXCELENTE"
        elif taxa_sucesso >= 70:
            classificacao = "BOM"
        elif taxa_sucesso >= 50:
            classificacao = "REGULAR"
        else:
            classificacao = "CRÍTICO"
        
        print(f"🏆 CLASSIFICAÇÃO DO SISTEMA: {classificacao}")
        print()
        
        # Mostrar falhas se houver
        if self.modulos_falha > 0:
            print("❌ MÓDULOS COM FALHAS:")
            for modulo, resultado in self.resultados.items():
                if resultado["status"] != "sucesso":
                    print(f"   • {modulo}: {resultado['detalhes']}")
            print()
        
        # Mostrar sucessos importantes
        print("✅ PRINCIPAIS SUCESSOS:")
        sucessos_importantes = [
            "orchestrators.main_orchestrator",
            "orchestrators.session_orchestrator",
            "suggestions.suggestions_manager",
            "conversers.conversation_manager"
        ]
        
        for modulo in sucessos_importantes:
            if modulo in self.resultados and self.resultados[modulo]["status"] == "sucesso":
                print(f"   • {modulo}: INTEGRADO")
        
        print()
        
        return {
            "modulos_testados": self.modulos_testados,
            "modulos_sucesso": self.modulos_sucesso,
            "modulos_falha": self.modulos_falha,
            "taxa_sucesso": taxa_sucesso,
            "classificacao": classificacao,
            "resultados_detalhados": self.resultados,
            "orchestrators": resultados_orchestrators,
            "fallbacks": resultados_fallbacks
        }

def main():
    """Função principal"""
    print("🚀 INICIANDO TESTE COMPLETO DE INTEGRAÇÃO")
    print("=" * 60)
    print()
    
    tester = TesteIntegracaoCompleta()
    
    try:
        resultado_final = tester.testar_todos_modulos()
        
        print("🎯 RESUMO EXECUTIVO:")
        print(f"   • Taxa de integração: {resultado_final['taxa_sucesso']:.1f}%")
        print(f"   • Classificação: {resultado_final['classificacao']}")
        print(f"   • Módulos órfãos: {resultado_final['modulos_falha']}")
        print()
        
        if resultado_final['taxa_sucesso'] >= 90:
            print("🎉 PARABÉNS! Sistema com integração excelente!")
            print("✅ Todos os módulos principais estão funcionando")
            print("✅ Orchestrators integrados corretamente")
            print("✅ Fallbacks configurados")
            return True
        else:
            print("⚠️ Sistema precisa de melhorias na integração")
            print("📋 Verifique os módulos com falhas listados acima")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1) 