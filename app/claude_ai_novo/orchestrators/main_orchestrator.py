"""
🔄 MAIN ORCHESTRATOR - Orquestrador Principal
============================================

Responsabilidade: ORQUESTRAR todos os componentes do sistema
de forma coordenada e inteligente.

Autor: Claude AI Novo
Data: 2025-01-07
"""

import logging
from typing import Dict, List, Any, Optional, Union
import asyncio
from datetime import datetime

# Import dos tipos compartilhados
from .types import OrchestrationMode, OrchestrationStep

logger = logging.getLogger(__name__)

class MainOrchestrator:
    """
    Orquestrador principal do sistema Claude AI Novo.
    
    Coordena a execução de todos os componentes de forma
    inteligente e eficiente.
    """
    
    def __init__(self):
        self.components: Dict[str, Any] = {}
        self.workflows: Dict[str, List[OrchestrationStep]] = {}
        self.execution_history: List[Dict[str, Any]] = []
        
        # Lazy loading dos módulos de alto valor
        self._coordinator_manager = None
        self._auto_command_processor = None
        
        # Lazy loading do SecurityGuard (CRÍTICO)
        self._security_guard = None
        
        # Lazy loading do SuggestionsManager (SUGESTÕES INTELIGENTES)
        self._suggestions_manager = None
        
        # Lazy loading do ToolsManager (GERENCIAMENTO DE FERRAMENTAS)
        self._tools_manager = None
        
        # Lazy loading do BaseCommand (COMANDOS BÁSICOS)
        self._base_command = None
        
        # Lazy loading do ResponseProcessor (PROCESSAMENTO DE RESPOSTAS)
        self._response_processor = None
        
        self._setup_default_workflows()
    
    @property
    def coordinator_manager(self):
        """Lazy loading do CoordinatorManager"""
        if self._coordinator_manager is None:
            try:
                from app.claude_ai_novo.coordinators.coordinator_manager import get_coordinator_manager
                self._coordinator_manager = get_coordinator_manager()
                logger.info("✅ CoordinatorManager integrado ao MainOrchestrator")
            except ImportError as e:
                logger.warning(f"⚠️ CoordinatorManager não disponível: {e}")
                self._coordinator_manager = False  # Marcar como indisponível
        return self._coordinator_manager if self._coordinator_manager is not False else None
    
    @property
    def auto_command_processor(self):
        """Lazy loading do AutoCommandProcessor"""
        if self._auto_command_processor is None:
            try:
                from app.claude_ai_novo.commands.auto_command_processor import get_auto_command_processor
                self._auto_command_processor = get_auto_command_processor()
                logger.info("✅ AutoCommandProcessor integrado ao MainOrchestrator")
            except ImportError as e:
                logger.warning(f"⚠️ AutoCommandProcessor não disponível: {e}")
                self._auto_command_processor = False  # Marcar como indisponível
        return self._auto_command_processor if self._auto_command_processor is not False else None
    
    @property
    def security_guard(self):
        """Lazy loading do SecurityGuard"""
        if self._security_guard is None:
            try:
                from app.claude_ai_novo.security.security_guard import get_security_guard
                self._security_guard = get_security_guard()
                logger.info("🔐 SecurityGuard integrado ao MainOrchestrator")
            except ImportError as e:
                logger.warning(f"⚠️ SecurityGuard não disponível: {e}")
                self._security_guard = False  # Marcar como indisponível
        return self._security_guard if self._security_guard is not False else None
    
    @property
    def suggestions_manager(self):
        """Lazy loading do SuggestionsManager"""
        if self._suggestions_manager is None:
            try:
                from app.claude_ai_novo.suggestions.suggestions_manager import get_suggestions_manager
                self._suggestions_manager = get_suggestions_manager()
                logger.info("💡 SuggestionsManager integrado ao MainOrchestrator")
            except ImportError as e:
                logger.warning(f"⚠️ SuggestionsManager não disponível: {e}")
                self._suggestions_manager = False  # Marcar como indisponível
        return self._suggestions_manager if self._suggestions_manager is not False else None
    
    @property
    def tools_manager(self):
        """Lazy loading do ToolsManager"""
        if self._tools_manager is None:
            try:
                from app.claude_ai_novo.tools.tools_manager import get_toolsmanager
                self._tools_manager = get_toolsmanager()
                logger.info("🔧 ToolsManager integrado ao MainOrchestrator")
            except ImportError as e:
                logger.warning(f"⚠️ ToolsManager não disponível: {e}")
                self._tools_manager = False  # Marcar como indisponível
        return self._tools_manager if self._tools_manager is not False else None
    
    @property
    def base_command(self):
        """Lazy loading do BaseCommand"""
        if self._base_command is None:
            try:
                from app.claude_ai_novo.commands.base_command import BaseCommand
                self._base_command = BaseCommand()
                logger.info("⚡ BaseCommand integrado ao MainOrchestrator")
            except ImportError as e:
                logger.warning(f"⚠️ BaseCommand não disponível: {e}")
                self._base_command = False  # Marcar como indisponível
        return self._base_command if self._base_command is not False else None
    
    @property
    def response_processor(self):
        """Lazy loading do ResponseProcessor"""
        if self._response_processor is None:
            try:
                from app.claude_ai_novo.processors.response_processor import get_responseprocessor
                self._response_processor = get_responseprocessor()
                logger.info("📝 ResponseProcessor integrado ao MainOrchestrator")
            except ImportError as e:
                logger.warning(f"⚠️ ResponseProcessor não disponível: {e}")
                self._response_processor = False  # Marcar como indisponível
        return self._response_processor if self._response_processor is not False else None
    
    def _setup_default_workflows(self):
        """Configura workflows padrão"""
        # Pré-carregar componentes essenciais
        self._preload_essential_components()
        
        # Conectar módulos via injeção de dependência
        self._connect_modules()
        
        # Workflow de análise de consulta
        self.add_workflow("analyze_query", [
            OrchestrationStep(
                name="intention_analysis",
                component="analyzers",
                method="analyze_intention",
                parameters={"query": "{query}"}
            ),
            OrchestrationStep(
                name="semantic_mapping",
                component="mappers",
                method="map_semantic_context",
                parameters={"context": "{intention_result}"},
                dependencies=["intention_analysis"]
            ),
            OrchestrationStep(
                name="data_loading",
                component="loaders",
                method="load_relevant_data",
                parameters={"mapped_context": "{semantic_result}"},
                dependencies=["semantic_mapping"]
            )
        ])
        
        # Workflow de processamento completo
        self.add_workflow("full_processing", [
            OrchestrationStep(
                name="analyze",
                component="analyzers",
                method="analyze_comprehensive",
                parameters={"input": "{input}"}
            ),
            OrchestrationStep(
                name="process",
                component="processors",
                method="process_context",
                parameters={"analysis_result": "{analyze_result}"},
                dependencies=["analyze"]
            ),
            OrchestrationStep(
                name="enrich",
                component="enrichers",
                method="enrich_data",
                parameters={"processed_data": "{process_result}"},
                dependencies=["process"]
            ),
            OrchestrationStep(
                name="validate",
                component="validators",
                method="validate_result",
                parameters={"enriched_data": "{enrich_result}"},
                dependencies=["enrich"]
            )
        ])
        
        # NOVO: Workflow de coordenação inteligente
        self.add_workflow("intelligent_coordination", [
            OrchestrationStep(
                name="domain_analysis",
                component="analyzers",
                method="analyze_intention",
                parameters={"query": "{query}"}
            ),
            OrchestrationStep(
                name="coordinate_query",
                component="coordinators",
                method="coordinate_query",
                parameters={"query": "{query}", "context": "{domain_result}"},
                dependencies=["domain_analysis"]
            )
        ])
        
        # NOVO: Workflow de comandos naturais
        self.add_workflow("natural_commands", [
            OrchestrationStep(
                name="detect_commands",
                component="commands",
                method="process_natural_command",
                parameters={"text": "{text}", "context": "{context}"}
            ),
            OrchestrationStep(
                name="execute_commands",
                component="coordinators",
                method="coordinate_query",
                parameters={"query": "{detect_result}", "context": "{context}"},
                dependencies=["detect_commands"]
            )
        ])
        
        # NOVO: Workflow de sugestões inteligentes
        self.add_workflow("intelligent_suggestions", [
            OrchestrationStep(
                name="analyze_context",
                component="analyzers",
                method="analyze_intention",
                parameters={"query": "{query}", "context": "{context}"}
            ),
            OrchestrationStep(
                name="generate_suggestions",
                component="suggestions",
                method="generate_intelligent_suggestions",
                parameters={"analysis": "{analyze_context_result}", "user_context": "{context}"},
                dependencies=["analyze_context"]
            )
        ])
        
        # NOVO: Workflow de comandos básicos
        self.add_workflow("basic_commands", [
            OrchestrationStep(
                name="validate_command",
                component="base_command",
                method="validate_input",
                parameters={"consulta": "{query}"}
            ),
            OrchestrationStep(
                name="extract_filters",
                component="base_command",
                method="extract_filters_advanced",
                parameters={"consulta": "{query}"},
                dependencies=["validate_command"]
            ),
            OrchestrationStep(
                name="execute_command",
                component="base_command",
                method="process_command",
                parameters={"consulta": "{query}", "filtros": "{extract_filters_result}"},
                dependencies=["extract_filters"]
            )
        ])
        
        # NOVO: Workflow de processamento de respostas
        self.add_workflow("response_processing", [
            OrchestrationStep(
                name="load_memory",
                component="memorizers",
                method="get_context",
                parameters={"session_id": "{session_id}"},
                dependencies=[]
            ),
            OrchestrationStep(
                name="analyze_query",
                component="analyzers",
                method="analyze_query",  # Mudando para analyze_query que é mais completo
                parameters={"query": "{query}", "context": "{load_memory_result}"},
                dependencies=["load_memory"]
            ),
            OrchestrationStep(
                name="load_data",
                component="loaders",  # Usar LoaderManager ao invés de providers!
                method="load_data_by_domain",
                # Correção: analyze_query retorna 'domains' (lista), pegar o primeiro
                parameters={"domain": "{analyze_query_result.domains[0]}", "filters": "{analyze_query_result.filters}"},
                dependencies=["analyze_query"]
            ),
            OrchestrationStep(
                name="enrich_data",
                component="enrichers",
                method="enrich_context",
                parameters={
                    "data": "{load_data_result}",
                    "query": "{query}",
                    "domain": "{analyze_query_result.domains[0]}"  # Mesma correção aqui
                },
                dependencies=["load_data"]
            ),
            OrchestrationStep(
                name="generate_response",
                component="response_processor",
                method="gerar_resposta_otimizada",
                parameters={"consulta": "{query}", "analise": "{analyze_query_result}", "user_context": "{context}", "dados_reais": "{enrich_data_result}"},
                dependencies=["analyze_query", "enrich_data"]
            ),
            OrchestrationStep(
                name="save_memory",
                component="memorizers",
                method="save_interaction",
                parameters={
                    "session_id": "{session_id}",
                    "query": "{query}",
                    "response": "{generate_response_result}"
                },
                dependencies=["generate_response"]
            ),
            OrchestrationStep(
                name="validate_response",
                component="validators",
                method="validate_result",
                parameters={"result": "{generate_response_result}"},
                dependencies=["generate_response"]
            )
        ])
    
    def _generate_session_id(self) -> str:
        """Gera um ID único para a sessão"""
        import uuid
        return f"session_{uuid.uuid4().hex[:12]}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        🎯 MÉTODO PRINCIPAL: Processa uma query usando TODA a inteligência do sistema
        
        Args:
            query: Query do usuário
            context: Contexto adicional
            
        Returns:
            Resposta processada com dados reais
        """
        logger.info(f"🎯 MainOrchestrator.process_query: '{query[:50]}...'")
        
        # Garantir que temos um session_id
        context = context or {}
        if 'session_id' not in context:
            context['session_id'] = self._generate_session_id()
        
        # Preparar dados para o workflow
        data = {
            'query': query,
            'context': context,
            'timestamp': datetime.now().isoformat(),
            'session_id': context['session_id'],  # Passar session_id explicitamente
            '_from_main': True  # Evitar loops
        }
        
        # Detectar se veio do SessionOrchestrator
        if context and context.get('_from_session'):
            logger.debug("📍 Query veio do SessionOrchestrator")
        
        try:
            # Executar workflow principal com TODA inteligência
            # Usar response_processing que já tem todos os steps necessários
            result = self.execute_workflow(
                workflow_name="response_processing",
                operation_type="intelligent_query",
                data=data
            )
            
            # Garantir formato de resposta
            if result.get('success'):
                response_text = None
                logger.debug(f"🔍 Estrutura do resultado: {list(result.keys())}")
                
                # Tentar extrair resposta de diferentes locais
                # 🎯 PRIORIDADE: Verificar response_result do ResponseProcessor
                if 'response_result' in result:
                    response_text = result['response_result']
                    logger.info(f"✅ Resposta extraída diretamente do ResponseProcessor: {len(str(response_text))} caracteres")
                elif 'response' in result:
                    response_text = result['response']
                elif 'steps_results' in result:
                    # Procurar resposta nos resultados dos steps
                    for step_name, step_result in result['steps_results'].items():
                        if isinstance(step_result, dict):
                            if 'response' in step_result:
                                response_text = step_result['response']
                                break
                            elif 'result' in step_result:
                                response_text = step_result['result']
                                break
                        elif isinstance(step_result, str):
                            response_text = step_result
                            break
                
                if not response_text:
                    # Gerar resposta baseada nos dados carregados
                    if 'load_data' in result.get('steps_results', {}):
                        data_loaded = result['steps_results']['load_data']
                        if isinstance(data_loaded, dict) and data_loaded.get('data'):
                            records = data_loaded['data']
                            response_text = f"Encontrei {len(records)} registros relacionados à sua consulta."
                        else:
                            response_text = "Processamento concluído, mas não encontrei dados específicos."
                    else:
                        # 🤖 Fallback melhorado - usar o ResponseProcessor diretamente
                        try:
                            if self.response_processor:
                                response_text = self.response_processor._processar_consulta_padrao(
                                    consulta=data.get("query", ""),
                                    user_context=data.get("context", {})
                                )
                                logger.info("✅ Resposta gerada pelo fallback do ResponseProcessor")
                            else:
                                response_text = f"""🤖 **Sistema Ativo**
                                
Sua consulta foi processada mas não conseguimos gerar uma resposta específica.

**🔍 Consulta recebida:** {data.get("query", "Não especificada")}
**⚡ Status:** Sistema funcionando normalmente
**🕒 Timestamp:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

**💡 Sugestão:** Tente reformular sua pergunta de forma mais específica.
"""
                        except Exception as e:
                            logger.error(f"Erro no fallback: {e}")
                            response_text = f"Sistema processou a consulta mas encontrou erro no fallback: {str(e)}"
                
                return {
                    'success': True,
                    'response': response_text,
                    'data': result.get('steps_results', {}),
                    'source': 'main_orchestrator',
                    'query': query
                }
            else:
                # Erro no processamento
                return {
                    'success': False,
                    'response': f"Erro ao processar: {result.get('error', 'Erro desconhecido')}",
                    'query': query,
                    'source': 'main_orchestrator_error'
                }
                
        except Exception as e:
            logger.error(f"❌ Erro no MainOrchestrator.process_query: {e}")
            return {
                'success': False,
                'response': f"Erro ao processar consulta: {str(e)}",
                'query': query,
                'source': 'main_orchestrator_exception'
            }
    
    def register_component(self, name: str, component: Any):
        """
        Registra um componente para orquestração.
        
        Args:
            name: Nome do componente
            component: Instância do componente
        """
        self.components[name] = component
        logger.info(f"Componente registrado: {name}")
    
    def add_workflow(self, workflow_name: str, steps: List[OrchestrationStep]):
        """
        Adiciona um workflow de orquestração.
        
        Args:
            workflow_name: Nome do workflow
            steps: Lista de passos do workflow
        """
        self.workflows[workflow_name] = steps
        logger.info(f"Workflow adicionado: {workflow_name} com {len(steps)} passos")
    
    def execute_workflow(self, workflow_name: str, operation_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa workflow de forma síncrona com funcionalidades avançadas.
        
        Args:
            workflow_name: Nome do workflow
            operation_type: Tipo de operação (intelligent_query, natural_command, etc.)
            data: Dados para processamento
            
        Returns:
            Resultado da execução
        """
        try:
            # 🔐 VALIDAÇÃO DE SEGURANÇA CRÍTICA
            if not self._validate_workflow_security(workflow_name, operation_type, data):
                security_error = f"Workflow bloqueado por motivos de segurança: {workflow_name}"
                logger.warning(f"🚫 {security_error}")
                return {
                    'workflow': workflow_name,
                    'operation_type': operation_type,
                    'success': False,
                    'error': security_error,
                    'security_blocked': True,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Funcionalidade existente preservada
            if workflow_name == "analyze_query":
                result = self._execute_analyze_query(data)
            elif workflow_name == "full_processing":
                result = self._execute_full_processing(data)
            # NOVAS funcionalidades com módulos de alto valor
            elif workflow_name == "intelligent_coordination" or operation_type == "intelligent_query":
                result = self._execute_intelligent_coordination(data)
            elif workflow_name == "natural_commands" or operation_type == "natural_command":
                result = self._execute_natural_commands(data)
            elif workflow_name == "intelligent_suggestions" or operation_type == "intelligent_suggestions":
                result = self._execute_intelligent_suggestions(data)
            elif workflow_name == "basic_commands" or operation_type == "basic_command":
                result = self._execute_basic_commands(data)
            elif workflow_name == "response_processing" or operation_type == "response_processing":
                result = self._execute_response_processing(data)
            # Fallback para workflows customizados
            else:
                result = self._execute_generic_workflow(workflow_name, data)
            
            # 🔐 LOG DE AUDITORIA DE SEGURANÇA
            self._log_workflow_audit(workflow_name, operation_type, True, "Workflow executado com sucesso")
            
            return result
            
        except Exception as e:
            # 🔐 LOG DE AUDITORIA DE ERRO
            self._log_workflow_audit(workflow_name, operation_type, False, f"Erro na execução: {str(e)}")
            logger.error(f"❌ Erro na execução do workflow {workflow_name}: {e}")
            return {
                'workflow': workflow_name,
                'operation_type': operation_type,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _validate_workflow_security(self, workflow_name: str, operation_type: str, 
                                   data: Dict[str, Any]) -> bool:
        """
        Valida segurança do workflow antes da execução.
        
        Args:
            workflow_name: Nome do workflow
            operation_type: Tipo de operação
            data: Dados do workflow
            
        Returns:
            True se workflow é seguro, False caso contrário
        """
        try:
            if not self.security_guard:
                # Sem SecurityGuard, permitir execução (modo degradado)
                logger.warning("⚠️ SecurityGuard não disponível - workflow permitido em modo degradado")
                return True
            
            # Validar acesso do usuário ao workflow
            if not self.security_guard.validate_user_access(f"workflow_{workflow_name}"):
                logger.warning(f"🚫 Usuário sem acesso ao workflow: {workflow_name}")
                return False
            
            # Validar dados de entrada
            if not self.security_guard.validate_input(data):
                logger.warning(f"🚫 Dados de entrada inválidos para workflow: {workflow_name}")
                return False
            
            # Validar workflows administrativos críticos
            admin_workflows = [
                'system_management', 'admin_override', 'security_config',
                'user_management', 'database_admin'
            ]
            
            if workflow_name in admin_workflows:
                if not self.security_guard.validate_user_access(workflow_name, 'admin_resource'):
                    logger.warning(f"🚫 Workflow administrativo bloqueado: {workflow_name}")
                    return False
            
            # Validar operações críticas baseadas no tipo
            if operation_type in ['system_reset', 'delete_all', 'admin_command']:
                if not self.security_guard.validate_user_access(operation_type, 'admin_resource'):
                    logger.warning(f"🚫 Operação crítica bloqueada: {operation_type}")
                    return False
            
            # Validação específica para comandos naturais
            if operation_type == 'natural_command' and 'text' in data:
                if not self.security_guard.validate_input(data['text']):
                    logger.warning(f"🚫 Comando natural com entrada inválida: {workflow_name}")
                    return False
            
            logger.debug(f"✅ Validação de segurança do workflow passou para: {workflow_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na validação de segurança do workflow: {e}")
            # Em caso de erro, bloquear execução por segurança
            return False
    
    def _log_workflow_audit(self, workflow_name: str, operation_type: str,
                           success: bool, message: str):
        """
        Registra evento de auditoria de workflow.
        
        Args:
            workflow_name: Nome do workflow
            operation_type: Tipo de operação
            success: Se execução foi bem-sucedida
            message: Mensagem do evento
        """
        try:
            if self.security_guard:
                audit_event = {
                    'timestamp': datetime.now().isoformat(),
                    'component': 'MainOrchestrator',
                    'workflow_name': workflow_name,
                    'operation_type': operation_type,
                    'success': success,
                    'message': message,
                    'user_authenticated': getattr(self.security_guard, '_is_user_authenticated', lambda: False)()
                }
                
                # Log estruturado para auditoria
                if success:
                    logger.info(f"🔐 WORKFLOW_AUDIT: {audit_event}")
                else:
                    logger.warning(f"🚫 WORKFLOW_AUDIT: {audit_event}")
            
        except Exception as e:
            logger.error(f"❌ Erro no log de auditoria de workflow: {e}")
    
    def _execute_intelligent_coordination(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Executa coordenação inteligente usando CoordinatorManager"""
        try:
            result = {
                "workflow": "intelligent_coordination",
                "operation_type": "intelligent_query",
                "success": True,
                "traditional_result": None,
                "intelligent_result": None
            }
            
            # Execução tradicional (preservada)
            result["traditional_result"] = self._execute_analyze_query(data)
            
            # NOVA funcionalidade: Coordenação inteligente
            if self.coordinator_manager:
                query = data.get("query", "")
                context = data.get("context", {})
                
                coordination_result = self.coordinator_manager.coordinate_query(
                    query=query,
                    context=context
                )
                
                result["intelligent_result"] = coordination_result
                logger.info(f"✅ Coordenação inteligente: {coordination_result.get('coordinator_used', 'unknown')}")
            else:
                logger.warning("⚠️ CoordinatorManager não disponível - usando resultado tradicional")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro na coordenação inteligente: {e}")
            return {
                "workflow": "intelligent_coordination",
                "success": False,
                "error": str(e),
                "fallback_result": self._execute_analyze_query(data)
            }
    
    def _execute_natural_commands(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Executa processamento de comandos naturais"""
        try:
            result = {
                "workflow": "natural_commands",
                "operation_type": "natural_command",
                "success": True,
                "command_result": None,
                "coordination_result": None
            }
            
            # NOVA funcionalidade: Processamento de comandos naturais
            if self.auto_command_processor:
                text = data.get("text", data.get("query", ""))
                context = data.get("context", {})
                
                command_result = self.auto_command_processor.process_natural_command(
                    text=text,
                    context=context
                )
                
                result["command_result"] = command_result
                logger.info(f"✅ Comando natural processado: {command_result.get('status', 'unknown')}")
                
                # Se comando foi detectado, usar também coordenação inteligente
                if command_result.get("detected_commands") and self.coordinator_manager:
                    coordination_result = self.coordinator_manager.coordinate_query(
                        query=text,
                        context=context
                    )
                    result["coordination_result"] = coordination_result
            else:
                logger.warning("⚠️ AutoCommandProcessor não disponível - processamento básico")
                result["command_result"] = {"status": "no_processor", "message": "Processamento básico"}
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento de comandos naturais: {e}")
            return {
                "workflow": "natural_commands",
                "success": False,
                "error": str(e),
                "fallback_result": self._execute_analyze_query(data)
            }
    
    def _execute_intelligent_suggestions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Executa geração de sugestões inteligentes"""
        try:
            result = {
                "workflow": "intelligent_suggestions",
                "operation_type": "intelligent_suggestions",
                "success": True,
                "suggestions_result": None,
                "fallback_suggestions": None
            }
            
            # NOVA funcionalidade: Sugestões inteligentes
            if self.suggestions_manager:
                query = data.get("query", data.get("text", ""))
                context = data.get("context", {})
                user_id = data.get("user_id")
                
                suggestions_result = self.suggestions_manager.generate_intelligent_suggestions(
                    query=query,
                    context=context,
                    user_id=user_id
                )
                
                result["suggestions_result"] = suggestions_result
                logger.info(f"💡 Sugestões inteligentes geradas: {len(suggestions_result.get('suggestions', []))} sugestões")
            else:
                logger.warning("⚠️ SuggestionsManager não disponível - gerando sugestões básicas")
                result["fallback_suggestions"] = {
                    "suggestions": ["Tente ser mais específico", "Forneça mais contexto"],
                    "confidence": 0.3,
                    "source": "fallback"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro na geração de sugestões inteligentes: {e}")
            return {
                "workflow": "intelligent_suggestions",
                "success": False,
                "error": str(e),
                "fallback_result": {
                    "suggestions": ["Erro na geração de sugestões"],
                    "confidence": 0.1,
                    "source": "error_fallback"
                }
            }
    
    def _execute_basic_commands(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Executa comandos básicos usando BaseCommand"""
        try:
            result = {
                "workflow": "basic_commands",
                "operation_type": "basic_command",
                "success": True,
                "command_result": None,
                "filters_extracted": None
            }
            
            # NOVA funcionalidade: Comandos básicos
            if self.base_command:
                query = data.get("query", data.get("consulta", ""))
                
                # Validar entrada
                if not self.base_command._validate_input(query):
                    return {
                        "workflow": "basic_commands",
                        "success": False,
                        "error": "Entrada inválida",
                        "query": query
                    }
                
                # Extrair filtros
                filters = self.base_command._extract_filters_advanced(query)
                result["filters_extracted"] = filters
                
                # Sanitizar entrada
                sanitized_query = self.base_command._sanitize_input(query)
                
                # Preparar resultado do comando
                command_result = {
                    "original_query": query,
                    "sanitized_query": sanitized_query,
                    "filters": filters,
                    "command_type": self.base_command.__class__.__name__,
                    "processed_at": datetime.now().isoformat()
                }
                
                result["command_result"] = command_result
                logger.info(f"⚡ Comando básico processado: {len(filters)} filtros extraídos")
            else:
                logger.warning("⚠️ BaseCommand não disponível - processamento básico")
                result["command_result"] = {
                    "status": "no_base_command",
                    "message": "BaseCommand não disponível",
                    "query": data.get("query", "")
                }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento de comandos básicos: {e}")
            return {
                "workflow": "basic_commands",
                "success": False,
                "error": str(e),
                "query": data.get("query", "")
            }
    
    def _execute_response_processing(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Executa processamento de respostas usando ResponseProcessor"""
        try:
            result = {
                "workflow": "response_processing",
                "operation_type": "response_processing",
                "success": True,
                "analysis_result": None,
                "response_result": None,
                "validation_result": None
            }
            
            # NOVA funcionalidade: Processamento de respostas
            if self.response_processor:
                query = data.get("query", "")
                context = data.get("context", {})
                
                # Análise da consulta (usar analyzers se disponível)
                analysis = {"tipo_consulta": "geral", "dominio": "sistema"}
                if hasattr(self, 'components') and 'analyzers' in self.components:
                    try:
                        analysis = self.components['analyzers'].analyze_intention(query=query)
                    except Exception as e:
                        logger.warning(f"Erro na análise: {e}")
                
                result["analysis_result"] = analysis
                
                # Gerar resposta otimizada
                response = self.response_processor.gerar_resposta_otimizada(
                    consulta=query,
                    analise=analysis,
                    user_context=context
                )
                
                result["response_result"] = response
                logger.info(f"📝 Resposta processada: {len(response)} caracteres")
                
                # Validar resposta (usar validators se disponível)
                validation = {"valid": True, "status": "validated"}
                if hasattr(self, 'components') and 'validators' in self.components:
                    try:
                        validation = self.components['validators'].validate_result(result=response)
                    except Exception as e:
                        logger.warning(f"Erro na validação: {e}")
                
                result["validation_result"] = validation
                
            else:
                logger.warning("⚠️ ResponseProcessor não disponível - processamento básico")
                result["response_result"] = {
                    "status": "no_response_processor",
                    "message": "ResponseProcessor não disponível",
                    "query": data.get("query", "")
                }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento de respostas: {e}")
            return {
                "workflow": "response_processing",
                "success": False,
                "error": str(e),
                "query": data.get("query", "")
            }
    
    def _execute_analyze_query(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Executa análise de consulta (funcionalidade existente preservada)"""
        return {
            "workflow": "analyze_query",
            "steps_completed": [
                {"name": "intention_analysis", "result": "mock_analysis"},
                {"name": "semantic_mapping", "result": "mock_mapping"},
                {"name": "data_loading", "result": "mock_loading"}
            ],
            "success": True
        }
    
    def _execute_full_processing(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Executa processamento completo (funcionalidade existente preservada)"""
        return {
            "workflow": "full_processing",
            "steps_completed": [
                {"name": "analyze", "result": "mock_analysis"},
                {"name": "process", "result": "mock_processing"},
                {"name": "enrich", "result": "mock_enrichment"},
                {"name": "validate", "result": "mock_validation"}
            ],
            "success": True
        }
    
    def _execute_generic_workflow(self, workflow_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Executa workflow genérico (fallback)"""
        return {
            "workflow": workflow_name,
            "success": True,
            "result": "generic_execution",
            "data": data
        }
    
    async def execute_workflow_async(self, workflow_name: str, initial_data: Dict[str, Any], 
                              mode: OrchestrationMode = OrchestrationMode.SEQUENTIAL) -> Dict[str, Any]:
        """
        Executa um workflow de orquestração de forma assíncrona.
        
        Args:
            workflow_name: Nome do workflow
            initial_data: Dados iniciais
            mode: Modo de execução
            
        Returns:
            Resultado da execução
        """
        if workflow_name not in self.workflows:
            logger.error(f"Workflow não encontrado: {workflow_name}")
            return {"error": f"Workflow {workflow_name} não encontrado"}
        
        workflow = self.workflows[workflow_name]
        execution_context = initial_data.copy()
        results = {}
        
        logger.info(f"Iniciando execução do workflow: {workflow_name}")
        
        try:
            if mode == OrchestrationMode.SEQUENTIAL:
                results = await self._execute_sequential(workflow, execution_context)
            elif mode == OrchestrationMode.PARALLEL:
                results = await self._execute_parallel(workflow, execution_context)
            elif mode == OrchestrationMode.ADAPTIVE:
                results = await self._execute_adaptive(workflow, execution_context)
            
            # Registrar execução
            self.execution_history.append({
                "workflow": workflow_name,
                "mode": mode.value,
                "success": True,
                "results": results
            })
            
            logger.info(f"Workflow {workflow_name} executado com sucesso")
            return results
            
        except Exception as e:
            logger.error(f"Erro na execução do workflow {workflow_name}: {e}")
            self.execution_history.append({
                "workflow": workflow_name,
                "mode": mode.value,
                "success": False,
                "error": str(e)
            })
            return {"error": str(e)}
    
    async def _execute_sequential(self, workflow: List[OrchestrationStep], 
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """Executa workflow sequencialmente"""
        results = {}
        
        for step in workflow:
            # Verificar dependências
            if step.dependencies:
                for dep in step.dependencies:
                    if dep not in results:
                        raise Exception(f"Dependência não satisfeita: {dep}")
            
            # Executar passo
            step_result = await self._execute_step(step, context, results)
            results[f"{step.name}_result"] = step_result
            
            # Atualizar contexto
            context.update(results)
        
        return results
    
    async def _execute_parallel(self, workflow: List[OrchestrationStep], 
                               context: Dict[str, Any]) -> Dict[str, Any]:
        """Executa workflow em paralelo quando possível"""
        results = {}
        pending_steps = workflow.copy()
        
        while pending_steps:
            # Encontrar passos que podem ser executados
            ready_steps = []
            for step in pending_steps:
                if not step.dependencies or all(dep in results for dep in step.dependencies):
                    ready_steps.append(step)
            
            if not ready_steps:
                raise Exception("Dependências circulares detectadas no workflow")
            
            # Executar passos prontos em paralelo
            tasks = [self._execute_step(step, context, results) for step in ready_steps]
            step_results = await asyncio.gather(*tasks)
            
            # Atualizar resultados
            for step, result in zip(ready_steps, step_results):
                results[f"{step.name}_result"] = result
                pending_steps.remove(step)
            
            # Atualizar contexto
            context.update(results)
        
        return results
    
    async def _execute_adaptive(self, workflow: List[OrchestrationStep], 
                               context: Dict[str, Any]) -> Dict[str, Any]:
        """Executa workflow de forma adaptativa"""
        # Por enquanto, usa execução paralela
        # Pode ser expandido com lógica de adaptação baseada em performance
        return await self._execute_parallel(workflow, context)
    
    async def _execute_step(self, step: OrchestrationStep, context: Dict[str, Any], 
                           results: Dict[str, Any]) -> Any:
        """
        Executa um passo individual do workflow.
        
        Args:
            step: Passo a executar
            context: Contexto atual
            results: Resultados anteriores
            
        Returns:
            Resultado do passo
        """
        try:
            # Obter componente
            if step.component not in self.components:
                # Tentar carregar componente dinamicamente
                await self._load_component(step.component)
            
            component = self.components.get(step.component)
            if not component:
                raise Exception(f"Componente não disponível: {step.component}")
            
            # Preparar parâmetros
            parameters = step.parameters or {}
            resolved_params = self._resolve_parameters(parameters, context, results)
            
            # Executar método
            if hasattr(component, step.method):
                method = getattr(component, step.method)
                if asyncio.iscoroutinefunction(method):
                    result = await method(**resolved_params)
                else:
                    result = method(**resolved_params)
                
                logger.debug(f"Passo {step.name} executado com sucesso")
                return result
            else:
                raise Exception(f"Método não encontrado: {step.method} em {step.component}")
                
        except Exception as e:
            logger.error(f"Erro na execução do passo {step.name}: {e}")
            raise
    
    async def _load_component(self, component_name: str):
        """Carrega componente dinamicamente"""
        try:
            # Tentar carregar componentes conhecidos
            if component_name == "analyzers":
                try:
                    from app.claude_ai_novo.analyzers.analyzer_manager import get_analyzer_manager
                    self.components[component_name] = get_analyzer_manager()
                except ImportError:
                    # Fallback - criar componente mock
                    self.components[component_name] = MockComponent("analyzers")
            elif component_name == "processors":
                try:
                    from app.claude_ai_novo.processors import get_context_processor
                    self.components[component_name] = get_context_processor()
                except ImportError:
                    # Fallback - criar componente mock
                    self.components[component_name] = MockComponent("processors")
            elif component_name == "mappers":
                try:
                    from app.claude_ai_novo.mappers import get_mapper_manager
                    self.components[component_name] = get_mapper_manager()
                except ImportError:
                    # Fallback - criar componente mock
                    self.components[component_name] = MockComponent("mappers")
            elif component_name == "coordinators":
                # NOVO: Carregar CoordinatorManager
                if self.coordinator_manager:
                    self.components[component_name] = self.coordinator_manager
                else:
                    self.components[component_name] = MockComponent("coordinators")
            elif component_name == "commands":
                # NOVO: Carregar AutoCommandProcessor
                if self.auto_command_processor:
                    self.components[component_name] = self.auto_command_processor
                else:
                    self.components[component_name] = MockComponent("commands")
            elif component_name == "security_guard":
                # NOVO: Carregar SecurityGuard
                if self.security_guard:
                    self.components[component_name] = self.security_guard
                else:
                    self.components[component_name] = MockComponent("security_guard")
            elif component_name == "suggestions":
                # NOVO: Carregar SuggestionsManager
                if self.suggestions_manager:
                    self.components[component_name] = self.suggestions_manager
                else:
                    self.components[component_name] = MockComponent("suggestions")
            elif component_name == "tools":
                # NOVO: Carregar ToolsManager
                if self.tools_manager:
                    self.components[component_name] = self.tools_manager
                else:
                    self.components[component_name] = MockComponent("tools")
            elif component_name == "base_command":
                # NOVO: Carregar BaseCommand
                if self.base_command:
                    self.components[component_name] = self.base_command
                else:
                    self.components[component_name] = MockComponent("base_command")
            elif component_name == "response_processor":
                # NOVO: Carregar ResponseProcessor
                if self.response_processor:
                    self.components[component_name] = self.response_processor
                else:
                    self.components[component_name] = MockComponent("response_processor")
            elif component_name == "providers":
                # NOVO: Carregar DataProvider
                if hasattr(self, 'components') and 'providers' in self.components:
                    self.components[component_name] = self.components['providers']
                else:
                    self.components[component_name] = MockComponent("providers")
            elif component_name == "memorizers":
                # NOVO: Carregar MemoryManager
                if hasattr(self, 'components') and 'memorizers' in self.components:
                    self.components[component_name] = self.components['memorizers']
                else:
                    self.components[component_name] = MockComponent("memorizers")
            elif component_name == "conversers":
                # NOVO: Carregar ConversationManager
                if hasattr(self, 'components') and 'conversers' in self.components:
                    self.components[component_name] = self.components['conversers']
                else:
                    self.components[component_name] = MockComponent("conversers")
            # Adicionar outros componentes conforme necessário
            
            logger.info(f"Componente carregado dinamicamente: {component_name}")
            
        except Exception as e:
            logger.warning(f"Não foi possível carregar componente {component_name}: {e}")
            # Criar componente mock para continuar funcionando
            self.components[component_name] = MockComponent(component_name)
    
    def _preload_essential_components(self):
        """Pré-carrega componentes essenciais para workflows"""
        
        # Componentes com managers
        try:
            from app.claude_ai_novo.analyzers.analyzer_manager import get_analyzer_manager
            self.components["analyzers"] = get_analyzer_manager()
            logger.debug("✅ Analyzers carregado")
        except ImportError:
            self.components["analyzers"] = MockComponent("analyzers")
            logger.debug("⚠️ Analyzers mock")
        
        try:
            from app.claude_ai_novo.processors.processor_manager import get_processormanager
            self.components["processors"] = get_processormanager()
            logger.debug("✅ Processors carregado")
        except ImportError:
            self.components["processors"] = MockComponent("processors")
            logger.debug("⚠️ Processors mock")
        
        try:
            from app.claude_ai_novo.mappers import get_mapper_manager
            self.components["mappers"] = get_mapper_manager()
            logger.debug("✅ Mappers carregado")
        except ImportError:
            self.components["mappers"] = MockComponent("mappers")
            logger.debug("⚠️ Mappers mock")
        
        try:
            from app.claude_ai_novo.validators import get_validator_manager
            self.components["validators"] = get_validator_manager()
            logger.debug("✅ Validators carregado")
        except ImportError:
            self.components["validators"] = MockComponent("validators")
            logger.debug("⚠️ Validators mock")
        
        try:
            from app.claude_ai_novo.providers import get_provider_manager
            self.components["providers"] = get_provider_manager()
            logger.debug("✅ Providers carregado")
        except ImportError:
            self.components["providers"] = MockComponent("providers")
            logger.debug("⚠️ Providers mock")
        
        try:
            from app.claude_ai_novo.memorizers import get_memory_manager
            self.components["memorizers"] = get_memory_manager()
            logger.debug("✅ Memorizers carregado")
        except ImportError:
            self.components["memorizers"] = MockComponent("memorizers")
            logger.debug("⚠️ Memorizers mock")
        
        # Enrichers - Agora tem manager
        try:
            from app.claude_ai_novo.enrichers import get_enricher_manager
            self.components["enrichers"] = get_enricher_manager()
            logger.debug("✅ EnricherManager carregado")
        except ImportError:
            # Fallback para enrichers individuais
            try:
                from app.claude_ai_novo.enrichers import get_semantic_enricher, get_context_enricher
                # Criar um wrapper para os enrichers
                class EnrichersWrapper:
                    def __init__(self):
                        self.semantic = get_semantic_enricher()
                        self.context = get_context_enricher()
                    
                    def enrich_data(self, **kwargs):
                        # Usar ambos os enrichers
                        data = kwargs.get('processed_data', {})
                        if self.semantic:
                            data = self.semantic.enrich(data)
                        if self.context:
                            data = self.context.enrich(data)
                        return data
                    
                    def enrich_context(self, **kwargs):
                        # Método compatível com EnricherManager
                        return self.enrich_data(**kwargs)
                
                self.components["enrichers"] = EnrichersWrapper()
                logger.debug("✅ Enrichers (semantic + context) carregados")
            except ImportError:
                self.components["enrichers"] = MockComponent("enrichers")
                logger.debug("⚠️ Enrichers mock")
        
        # Loaders - USAR O LOADER MANAGER QUE FUNCIONA!
        try:
            from app.claude_ai_novo.loaders import get_loader_manager
            self.components['loaders'] = get_loader_manager()
            logger.info("✅ LoaderManager carregado com loaders por domínio")
        except ImportError:
            self.components['loaders'] = MockComponent('loaders')
            logger.debug("⚠️ LoaderManager mock")
        
        # Scanners - Para descobrir estrutura do banco
        try:
            from app.claude_ai_novo.scanning import get_scanning_manager
            self.components['scanners'] = get_scanning_manager()
            logger.info("✅ ScanningManager carregado")
        except ImportError:
            self.components['scanners'] = MockComponent('scanners')
            logger.debug("⚠️ ScanningManager mock")
        
        # Learners - Para aprendizado contínuo
        try:
            from app.claude_ai_novo.learners import get_learning_core
            self.components['learners'] = get_learning_core()
            logger.info("✅ LearningManager carregado")
        except ImportError:
            self.components['learners'] = MockComponent('learners')
            logger.debug("⚠️ LearningManager mock")
        
        # Conversers
        try:
            from app.claude_ai_novo.conversers import get_conversation_manager
            self.components["conversers"] = get_conversation_manager()
            logger.debug("✅ Conversers carregado")
        except ImportError:
            self.components["conversers"] = MockComponent("conversers")
            logger.debug("⚠️ Conversers mock")
        
        # NOVO: Pré-carregar módulos de alto valor
        # CoordinatorManager
        if self.coordinator_manager:
            self.components["coordinators"] = self.coordinator_manager
            logger.debug("✅ CoordinatorManager pré-carregado")
        else:
            self.components["coordinators"] = MockComponent("coordinators")
            logger.debug("⚠️ CoordinatorManager mock")
        
        # AutoCommandProcessor
        if self.auto_command_processor:
            self.components["commands"] = self.auto_command_processor
            logger.debug("✅ AutoCommandProcessor pré-carregado")
        else:
            self.components["commands"] = MockComponent("commands")
            logger.debug("⚠️ AutoCommandProcessor mock")
        
        # SecurityGuard
        if self.security_guard:
            self.components["security_guard"] = self.security_guard
            logger.debug("✅ SecurityGuard pré-carregado")
        else:
            self.components["security_guard"] = MockComponent("security_guard")
            logger.debug("⚠️ SecurityGuard mock")
        
        # SuggestionsManager
        if self.suggestions_manager:
            self.components["suggestions"] = self.suggestions_manager
            logger.debug("✅ SuggestionsManager pré-carregado")
        else:
            self.components["suggestions"] = MockComponent("suggestions")
            logger.debug("⚠️ SuggestionsManager mock")
        
        # ToolsManager
        if self.tools_manager:
            self.components["tools"] = self.tools_manager
            logger.debug("✅ ToolsManager pré-carregado")
        else:
            self.components["tools"] = MockComponent("tools")
            logger.debug("⚠️ ToolsManager mock")
        
        # BaseCommand
        if self.base_command:
            self.components["base_command"] = self.base_command
            logger.debug("✅ BaseCommand pré-carregado")
        else:
            self.components["base_command"] = MockComponent("base_command")
            logger.debug("⚠️ BaseCommand mock")
        
        # ResponseProcessor
        if self.response_processor:
            self.components["response_processor"] = self.response_processor
            logger.debug("✅ ResponseProcessor pré-carregado")
        else:
            self.components["response_processor"] = MockComponent("response_processor")
            logger.debug("⚠️ ResponseProcessor mock")
    
    def _connect_modules(self):
        """Conecta todos os módulos via injeção de dependência"""
        logger.info("🔗 Conectando módulos via Orchestrator...")
        
        try:
            # 1. Scanner → Loader (com otimizações de índices)
            if 'scanners' in self.components and 'loaders' in self.components:
                scanner = self.components['scanners']
                loader = self.components['loaders']
                
                # Obter informações do banco via Scanner
                if hasattr(scanner, 'get_database_info'):
                    try:
                        db_info = scanner.get_database_info()
                        logger.info("✅ Informações do banco obtidas do Scanner")
                        
                        # Configurar Loader com Scanner
                        if hasattr(loader, 'configure_with_scanner'):
                            loader.configure_with_scanner(scanner)
                            logger.info("✅ Scanner → Loader conectados")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao conectar Scanner → Loader: {e}")
            
            # 2. Mapper → Loader (para mapeamento semântico)
            if 'mappers' in self.components and 'loaders' in self.components:
                mapper = self.components['mappers']
                loader = self.components['loaders']
                
                if hasattr(loader, 'configure_with_mapper'):
                    try:
                        loader.configure_with_mapper(mapper)
                        logger.info("✅ Mapper → Loader conectados")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao conectar Mapper → Loader: {e}")
            
            # 3. Loader → Provider (evitar duplicação de carregamento)
            if 'loaders' in self.components and 'providers' in self.components:
                loader = self.components['loaders']
                provider = self.components['providers']
                
                # Verificar se é ProviderManager e acessar DataProvider interno
                if hasattr(provider, 'data_provider'):
                    # ProviderManager tem data_provider interno
                    data_provider = provider.data_provider
                    if hasattr(data_provider, 'set_loader'):
                        try:
                            data_provider.set_loader(loader)
                            logger.info("✅ Loader → Provider conectados (via ProviderManager.data_provider)")
                        except Exception as e:
                            logger.warning(f"⚠️ Erro ao conectar Loader → Provider: {e}")
                elif hasattr(provider, 'set_loader'):
                    # Fallback: tentar direto no provider
                    try:
                        provider.set_loader(loader)
                        logger.info("✅ Loader → Provider conectados (direto)")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao conectar Loader → Provider: {e}")
                else:
                    logger.warning("⚠️ Provider não tem método set_loader nem data_provider")
            
            # 4. Memorizer → Processor (contexto histórico)
            if 'memorizers' in self.components and 'processors' in self.components:
                memorizer = self.components['memorizers']
                processor = self.components['processors']
                
                if hasattr(processor, 'set_memory_manager'):
                    try:
                        processor.set_memory_manager(memorizer)
                        logger.info("✅ Memorizer → Processor conectados")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao conectar Memorizer → Processor: {e}")
            
            # 5. Learner → Analyzer (aprendizado contínuo)
            if 'learners' in self.components and 'analyzers' in self.components:
                learner = self.components['learners']
                analyzer = self.components['analyzers']
                
                if hasattr(analyzer, 'set_learner'):
                    try:
                        analyzer.set_learner(learner)
                        logger.info("✅ Learner → Analyzer conectados")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao conectar Learner → Analyzer: {e}")
            
            # 6. Enricher → Processor (enriquecimento de dados)
            if 'enrichers' in self.components and 'processors' in self.components:
                enricher = self.components['enrichers']
                processor = self.components['processors']
                
                if hasattr(processor, 'set_enricher'):
                    try:
                        processor.set_enricher(enricher)
                        logger.info("✅ Enricher → Processor conectados")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao conectar Enricher → Processor: {e}")
            
            # 7. Converser → Memorizer (gerenciamento de conversas com memória)
            if 'conversers' in self.components and 'memorizers' in self.components:
                converser = self.components['conversers']
                memorizer = self.components['memorizers']
                
                if hasattr(converser, 'set_memorizer'):
                    try:
                        converser.set_memorizer(memorizer)
                        logger.info("✅ Converser → Memorizer conectados")
                    except Exception as e:
                        logger.error(f"❌ Erro ao conectar Converser → Memorizer: {e}")
                else:
                    logger.warning("⚠️ Converser não tem método set_memorizer")
            else:
                logger.debug("⚠️ Converser ou Memorizer não disponíveis para conexão")
            
            logger.info("✅ Processo de conexão de módulos concluído!")
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar módulos: {e}")
            import traceback
            traceback.print_exc()
    
    def _resolve_parameters(self, parameters: Dict[str, Any], context: Dict[str, Any], 
                           results: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve parâmetros com placeholders"""
        resolved = {}
        
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                # Placeholder - resolver valor
                placeholder = value[1:-1]  # Remove { }
                
                if placeholder in context:
                    resolved[key] = context[placeholder]
                elif placeholder in results:
                    resolved[key] = results[placeholder]
                else:
                    logger.warning(f"Placeholder não resolvido: {placeholder}")
                    resolved[key] = value
            else:
                resolved[key] = value
        
        return resolved

class MockComponent:
    """Componente mock para fallback"""
    def __init__(self, component_type: str):
        self.component_type = component_type
    
    def analyze_intention(self, **kwargs):
        return {"intention": "mock", "confidence": 0.5}
    
    def map_semantic_context(self, **kwargs):
        return {"context": "mock", "mapped": True}
    
    def load_relevant_data(self, **kwargs):
        return {"data": "mock", "loaded": True}
    
    def analyze_comprehensive(self, **kwargs):
        return {"analysis": "mock", "comprehensive": True}
    
    def process_context(self, **kwargs):
        return {"processed": True, "context": "mock"}
    
    def enrich_data(self, **kwargs):
        return {"enriched": True, "data": "mock"}
    
    def validate_result(self, **kwargs):
        return {"valid": True, "result": "mock"}
    
    def coordinate_query(self, **kwargs):
        return {"status": "mock", "coordinator_used": "mock"}
    
    def process_natural_command(self, **kwargs):
        return {"status": "mock", "detected_commands": [], "message": "Mock command processing"}
    
    def generate_intelligent_suggestions(self, **kwargs):
        return {"suggestions": ["Sugestão mock 1", "Sugestão mock 2", "Sugestão mock 3"], "confidence": 0.7, "source": "mock"}
    
    def manage_conversation(self, **kwargs):
        return {"total_turns": 1, "conversation_score": 0.8, "context_continuity": 0.6, "source": "mock"}
    
    # Métodos de segurança para SecurityGuard mock
    def validate_user_access(self, operation: str, resource: Optional[str] = None) -> bool:
        """Mock de validação de acesso do usuário"""
        return True  # Permitir tudo no modo mock
    
    def validate_input(self, input_data) -> bool:
        """Mock de validação de entrada"""
        return True  # Permitir tudo no modo mock
    
    def sanitize_input(self, input_data: str) -> str:
        """Mock de sanitização"""
        return str(input_data)[:100]  # Limitar a 100 chars
    
    def generate_token(self, data: str) -> str:
        """Mock de geração de token"""
        return "mock_token_12345678901234567890"
    
    def get_security_info(self) -> Dict[str, Any]:
        """Mock de informações de segurança"""
        return {
            'security_level': 'mock',
            'user_authenticated': False,
            'user_admin': False,
            'module': f'Mock{self.component_type.title()}',
            'version': '1.0.0-mock'
        }
    
    # Métodos de ferramentas para ToolsManager mock
    def get_available_tools(self, **kwargs):
        """Mock de ferramentas disponíveis"""
        return {
            "tools": ["mock_tool1", "mock_tool2", "mock_tool3"],
            "count": 3,
            "source": "mock"
        }
    
    def execute_tool(self, **kwargs):
        """Mock de execução de ferramentas"""
        return {
            "status": "mock_executed",
            "result": "mock_result",
            "tool": kwargs.get("tool_name", "unknown")
        }
    
    def register_tool(self, **kwargs):
        """Mock de registro de ferramentas"""
        return {
            "status": "mock_registered",
            "tool": kwargs.get("tool_name", "unknown")
        }
    
    def validate_tool(self, **kwargs):
        """Mock de validação de ferramentas"""
        return {
            "valid": True,
            "status": "mock_validated",
            "tool": kwargs.get("tool_name", "unknown")
        }
    
    # Métodos de comandos básicos para BaseCommand mock
    def _validate_input(self, **kwargs):
        """Mock de validação de entrada"""
        return True
    
    def _extract_filters_advanced(self, **kwargs):
        """Mock de extração de filtros"""
        return {
            "cliente": "Mock Cliente",
            "periodo": "mock",
            "status": "mock"
        }
    
    def _sanitize_input(self, **kwargs):
        """Mock de sanitização"""
        return kwargs.get("consulta", "mock_query")
    
    def process_command(self, **kwargs):
        """Mock de processamento de comando"""
        return {
            "status": "mock_processed",
            "consulta": kwargs.get("consulta", "mock"),
            "filtros": kwargs.get("filtros", {})
        }
    

    # Métodos de processamento de respostas para ResponseProcessor mock
    def gerar_resposta_otimizada(self, **kwargs):
        """Mock de geração de resposta otimizada"""
        consulta = kwargs.get("consulta", "mock_query")
        analise = kwargs.get("analise", {})
        
        return f"""**Resposta Mock do ResponseProcessor**

Consulta: {consulta}
Análise: {analise.get('tipo_consulta', 'mock')}
Domínio: {analise.get('dominio', 'sistema')}

Esta é uma resposta simulada gerada pelo sistema mock.
O ResponseProcessor real não está disponível no momento.

Status: Mock ativo
Timestamp: {datetime.now().isoformat()}"""

# Instância global
_main_orchestrator = None

def get_main_orchestrator() -> MainOrchestrator:
    """
    Retorna instância global do MainOrchestrator.
    
    Returns:
        MainOrchestrator: Instância do orquestrador
    """
    global _main_orchestrator
    if _main_orchestrator is None:
        _main_orchestrator = MainOrchestrator()
        logger.info("✅ MainOrchestrator inicializado")
    return _main_orchestrator

# Exports
__all__ = [
    'MainOrchestrator',
    'OrchestrationStep',
    'OrchestrationMode',
    'get_main_orchestrator'
] 