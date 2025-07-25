"""
🎭 ORCHESTRATOR MANAGER - Maestro dos Orquestradores
===================================================

Responsabilidade: COORDENAR todos os orquestradores do sistema.
Especialização: Workflow Master, Process Director, System Conductor.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from threading import Lock
import uuid

# Import dos tipos compartilhados
from .types import OrchestrationMode, OrchestratorType, OrchestrationTask

# Imports internos robustos com fallbacks
try:
    from app.claude_ai_novo.orchestrators.main_orchestrator import MainOrchestrator
    from app.claude_ai_novo.orchestrators.session_orchestrator import SessionOrchestrator, get_session_orchestrator
    from app.claude_ai_novo.orchestrators.workflow_orchestrator import WorkflowOrchestrator
    ORCHESTRATORS_AVAILABLE = True
except ImportError as e:
    try:
        # Fallback para imports relativos
        from .main_orchestrator import MainOrchestrator
        from .session_orchestrator import SessionOrchestrator, get_session_orchestrator
        from .workflow_orchestrator import WorkflowOrchestrator
        ORCHESTRATORS_AVAILABLE = True
    except ImportError as e2:
        logging.warning(f"⚠️ Alguns orchestrators não disponíveis: {e2}")
        ORCHESTRATORS_AVAILABLE = False

logger = logging.getLogger(__name__)

class OrchestratorManager:
    """
    Maestro dos Orquestradores - Coordena todos os sistemas de orquestração.
    
    Responsabilidades:
    - Coordenar múltiplos orquestradores especializados
    - Gerenciar workflows complexos inter-orchestradores
    - Roteamento inteligente de operações
    - Monitoramento de saúde dos orquestradores
    - Fallback e recuperação de falhas
    """
    
    def __init__(self, default_timeout: int = 300):
        """
        Inicializa o manager de orquestradores.
        
        Args:
            default_timeout: Timeout padrão em segundos (5 minutos)
        """
        self.default_timeout = default_timeout
        self.orchestrators: Dict[OrchestratorType, Any] = {}
        self.active_tasks: Dict[str, OrchestrationTask] = {}
        self.task_lock = Lock()
        self.operation_history: List[Dict[str, Any]] = []
        
        # Lazy loading do SecurityGuard (CRÍTICO)
        self._security_guard = None
        
        # Lazy loading do IntegrationManager (INTEGRAÇÕES)
        self._integration_manager = None
        
        # Inicializar orquestradores
        self._initialize_orchestrators()
        
        logger.info("🎭 OrchestratorManager inicializado como maestro")
    
    @property
    def security_guard(self):
        """Lazy loading do SecurityGuard"""
        if self._security_guard is None:
            try:
                from app.claude_ai_novo.security.security_guard import get_security_guard
                self._security_guard = get_security_guard()
                logger.info("🔐 SecurityGuard integrado ao MAESTRO")
            except ImportError as e:
                logger.warning(f"⚠️ SecurityGuard não disponível: {e}")
                self._security_guard = False  # Marcar como indisponível
        return self._security_guard if self._security_guard is not False else None
    
    @property
    def integration_manager(self):
        """Lazy loading do IntegrationManager"""
        # REMOVIDO: Import circular - IntegrationManager não deve ser carregado aqui
        # para evitar loop infinito entre Integration e Orchestrator
        return None
    
    def _initialize_orchestrators(self):
        """Inicializa todos os orquestradores disponíveis."""
        initialized_count = 0
        
        # Orquestradores essenciais
        if ORCHESTRATORS_AVAILABLE:
            try:
                self.orchestrators[OrchestratorType.MAIN] = MainOrchestrator()
                initialized_count += 1
                logger.info("🎯 MainOrchestrator inicializado")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar MainOrchestrator: {e}")
            
            try:
                self.orchestrators[OrchestratorType.SESSION] = get_session_orchestrator()
                initialized_count += 1
                logger.info("🔄 SessionOrchestrator inicializado")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar SessionOrchestrator: {e}")
            
            try:
                self.orchestrators[OrchestratorType.WORKFLOW] = WorkflowOrchestrator()
                initialized_count += 1
                logger.info("⚙️ WorkflowOrchestrator inicializado")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar WorkflowOrchestrator: {e}")
        
        logger.info(f"🎭 OrchestratorManager: {initialized_count} orquestradores inicializados")
    
    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processa uma consulta usando os orquestradores apropriados.
        
        Args:
            query: Consulta a processar
            context: Contexto adicional
            
        Returns:
            Resultado do processamento
        """
        # Verificar se veio do IntegrationManager para evitar loop
        if context and context.get("_from_integration"):
            logger.debug("📍 Chamada do IntegrationManager detectada")
            # Adicionar flag para evitar loop de volta
            context = (context or {}).copy()
            context["_from_orchestrator"] = True
        
        try:
            # Preparar dados para orquestração
            data = {
                'query': query,
                'context': context or {},
                'user_id': context.get('user_id') if context else None,
                'timestamp': datetime.now().isoformat()
            }
            
            # Detectar tipo de operação baseado na consulta
            operation_type = self._detect_operation_type(query)
            
            # Orquestrar usando o sistema inteligente
            result = await self.orchestrate_operation(
                operation_type=operation_type,
                data=data,
                mode=OrchestrationMode.INTELLIGENT,
                priority=1
            )
            
            logger.info(f"🎭 Query processada: {query[:50]}... via {operation_type}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar query: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'fallback': True,
                'timestamp': datetime.now().isoformat()
            }
    
    def _detect_operation_type(self, query: str) -> str:
        """
        Detecta o tipo de operação baseado na consulta.
        
        Args:
            query: Consulta a analisar
            
        Returns:
            Tipo da operação
        """
        query_lower = query.lower()
        
        # Mapeamento de palavras-chave para tipos de operação
        if any(word in query_lower for word in ['conversa', 'sessão', 'contexto', 'usuário']):
            return 'session_query'
        elif any(word in query_lower for word in ['workflow', 'processo', 'etapa', 'pipeline']):
            return 'workflow_query'
        elif any(word in query_lower for word in ['integração', 'api', 'externo', 'conectar']):
            return 'integration_query'
        elif any(word in query_lower for word in ['sugestão', 'ajuda', 'dica', 'recomendar']):
            return 'intelligent_suggestions'
        elif any(word in query_lower for word in ['comando', 'executar', 'fazer']):
            return 'natural_command'
        else:
            return 'intelligent_query'
    
    async def orchestrate_operation(self, operation_type: str, 
                            data: Dict[str, Any],
                            target_orchestrator: Optional[OrchestratorType] = None,
                            mode: OrchestrationMode = OrchestrationMode.INTELLIGENT,
                            priority: int = 1,
                            timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Orquestra uma operação usando o sistema adequado.
        
        Args:
            operation_type: Tipo da operação
            data: Dados da operação
            target_orchestrator: Orquestrador específico (opcional)
            mode: Modo de orquestração
            priority: Prioridade da operação
            timeout: Timeout específico
            
        Returns:
            Resultado da orquestração
        """
        task_id = str(uuid.uuid4())
        
        try:
            # 🔐 VALIDAÇÃO DE SEGURANÇA CRÍTICA
            if not self._validate_operation_security(operation_type, data):
                security_error = f"Operação bloqueada por motivos de segurança: {operation_type}"
                logger.warning(f"🚫 {security_error}")
                return {
                    'task_id': task_id,
                    'success': False,
                    'error': security_error,
                    'security_blocked': True,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Detectar orquestrador apropriado se não especificado
            if target_orchestrator is None:
                target_orchestrator = self._detect_appropriate_orchestrator(operation_type, data)
            
            # Criar task
            task = OrchestrationTask(
                task_id=task_id,
                orchestrator_type=target_orchestrator,
                operation=operation_type,
                parameters=data,
                priority=priority,
                timeout=timeout or self.default_timeout
            )
            
            # Registrar task
            with self.task_lock:
                self.active_tasks[task_id] = task
            
            # Executar operação
            result = await self._execute_orchestration_task(task, mode)
            
            # Atualizar task
            task.status = "completed"
            task.result = result
            
            # Histórico
            self._record_operation(task)
            
            # 🔐 LOG DE AUDITORIA DE SEGURANÇA
            self._log_security_audit(operation_type, data, True, "Operação autorizada e executada")
            
            logger.info(f"🎭 Operação orquestrada com sucesso: {operation_type} via {target_orchestrator.value}")
            return {
                'task_id': task_id,
                'success': True,
                'result': result,
                'orchestrator': target_orchestrator.value,
                'mode': mode.value,
                'execution_time': (datetime.now() - task.created_at).total_seconds()
            }
            
        except Exception as e:
            # Atualizar task com erro
            if task_id in self.active_tasks:
                self.active_tasks[task_id].status = "failed"
                self.active_tasks[task_id].error = str(e)
            
            # 🔐 LOG DE AUDITORIA DE ERRO
            self._log_security_audit(operation_type, data, False, f"Erro na execução: {str(e)}")
            
            logger.error(f"❌ Erro na orquestração de {operation_type}: {e}")
            return {
                'task_id': task_id,
                'success': False,
                'error': str(e),
                'orchestrator': target_orchestrator.value if target_orchestrator else 'unknown',
                'mode': mode.value
            }
        finally:
            # Limpar task ativa
            with self.task_lock:
                self.active_tasks.pop(task_id, None)
    
    def _validate_operation_security(self, operation_type: str, data: Dict[str, Any]) -> bool:
        """
        Valida segurança da operação antes da execução.
        
        Args:
            operation_type: Tipo da operação
            data: Dados da operação
            
        Returns:
            True se operação é segura, False caso contrário
        """
        try:
            if not self.security_guard:
                # Sem SecurityGuard, permitir operação (modo degradado)
                logger.warning("⚠️ SecurityGuard não disponível - operação permitida em modo degradado")
                return True
            
            # Validar acesso do usuário à operação
            if not self.security_guard.validate_user_access(operation_type):
                logger.warning(f"🚫 Usuário sem acesso à operação: {operation_type}")
                return False
            
            # Validar dados de entrada
            if not self.security_guard.validate_input(data):
                logger.warning(f"🚫 Dados de entrada inválidos para operação: {operation_type}")
                return False
            
            # Validar operações administrativas críticas
            admin_operations = [
                'system_reset', 'delete_all', 'admin_override', 
                'security_config', 'user_management'
            ]
            
            if any(admin_op in operation_type.lower() for admin_op in admin_operations):
                if not self.security_guard.validate_user_access(operation_type, 'admin_resource'):
                    logger.warning(f"🚫 Operação administrativa bloqueada: {operation_type}")
                    return False
            
            # Validação adicional para operações de sessão críticas
            if 'session' in operation_type.lower() and 'delete' in operation_type.lower():
                if not self.security_guard.validate_user_access(operation_type, 'session_management'):
                    logger.warning(f"🚫 Operação de sessão crítica bloqueada: {operation_type}")
                    return False
            
            logger.debug(f"✅ Validação de segurança passou para: {operation_type}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na validação de segurança: {e}")
            # Em caso de erro, bloquear operação por segurança
            return False
    
    def _log_security_audit(self, operation_type: str, data: Dict[str, Any], 
                           success: bool, message: str):
        """
        Registra evento de auditoria de segurança.
        
        Args:
            operation_type: Tipo da operação
            data: Dados da operação (sanitizados)
            success: Se operação foi bem-sucedida
            message: Mensagem do evento
        """
        try:
            if self.security_guard:
                # Sanitizar dados sensíveis
                safe_data = self.security_guard.sanitize_input(str(data))
                
                audit_event = {
                    'timestamp': datetime.now().isoformat(),
                    'component': 'OrchestratorManager',
                    'operation_type': operation_type,
                    'success': success,
                    'message': message,
                    'data_hash': self.security_guard.generate_token(safe_data[:100]),  # Apenas primeiros 100 chars
                    'user_authenticated': getattr(self.security_guard, '_is_user_authenticated', lambda: False)()
                }
                
                # Log estruturado para auditoria
                if success:
                    logger.info(f"🔐 AUDIT: {audit_event}")
                else:
                    logger.warning(f"🚫 AUDIT: {audit_event}")
            
        except Exception as e:
            logger.error(f"❌ Erro no log de auditoria: {e}")
    
    def _detect_appropriate_orchestrator(self, operation_type: str, data: Dict[str, Any]) -> OrchestratorType:
        """
        Detecta o orquestrador mais apropriado para a operação.
        
        Args:
            operation_type: Tipo da operação
            data: Dados da operação
            
        Returns:
            Tipo do orquestrador mais adequado
        """
        # Mapeamento inteligente baseado em palavras-chave
        session_keywords = ['session', 'user', 'conversation', 'context']
        workflow_keywords = ['workflow', 'process', 'step', 'pipeline']
        integration_keywords = ['integration', 'api', 'external', 'service', 'connect']
        
        operation_lower = operation_type.lower()
        data_str = str(data).lower()
        combined_text = f"{operation_lower} {data_str}"
        
        # Contagem de keywords
        scores = {
            OrchestratorType.SESSION: sum(1 for kw in session_keywords if kw in combined_text),
            OrchestratorType.WORKFLOW: sum(1 for kw in workflow_keywords if kw in combined_text),
        }
        
        # Filtrar apenas orquestradores disponíveis
        available_scores = {
            orch_type: score for orch_type, score in scores.items()
            if orch_type in self.orchestrators and score > 0
        }
        
        if available_scores:
            # Retornar o com maior score
            best_orchestrator = max(available_scores.items(), key=lambda x: x[1])[0]
            logger.debug(f"🎯 Orquestrador detectado: {best_orchestrator.value} (score: {available_scores[best_orchestrator]})")
            return best_orchestrator
        
        # Fallback para main orchestrator se disponível
        if OrchestratorType.MAIN in self.orchestrators:
            logger.debug("🎯 Usando MainOrchestrator como fallback")
            return OrchestratorType.MAIN
        
        # Último recurso - primeiro orquestrador disponível
        if self.orchestrators:
            fallback = next(iter(self.orchestrators.keys()))
            logger.debug(f"🎯 Usando {fallback.value} como último recurso")
            return fallback
        
        raise ValueError("Nenhum orquestrador disponível")
    
    async def _execute_orchestration_task(self, task: OrchestrationTask, mode: OrchestrationMode) -> Any:
        """
        Executa uma task de orquestração.
        
        Args:
            task: Task a ser executada
            mode: Modo de execução
            
        Returns:
            Resultado da execução
        """
        orchestrator = self.orchestrators.get(task.orchestrator_type)
        if not orchestrator:
            raise ValueError(f"Orquestrador {task.orchestrator_type.value} não disponível")
        
        # Tentar diferentes métodos de execução baseados no tipo
        if task.orchestrator_type == OrchestratorType.SESSION:
            return await self._execute_session_operation(orchestrator, task)
        elif task.orchestrator_type == OrchestratorType.WORKFLOW:
            return self._execute_workflow_operation(orchestrator, task)
        else:
            # Método genérico
            return await self._execute_generic_operation(orchestrator, task)
    
    async def _execute_session_operation(self, orchestrator, task: OrchestrationTask) -> Any:
        """Executa operação de sessão."""
        operation = task.operation.lower()
        params = task.parameters
        
        if 'create' in operation:
            # Usar valores diretos para evitar conflitos de tipo
            priority_value = params.get('priority', 'normal')
            
            # Tentar import e uso direto
            try:
                from app.claude_ai_novo.orchestrators.session_orchestrator import SessionPriority
                if priority_value.upper() == 'HIGH':
                    session_priority = SessionPriority.HIGH
                elif priority_value.upper() == 'LOW':
                    session_priority = SessionPriority.LOW
                elif priority_value.upper() == 'CRITICAL':
                    session_priority = SessionPriority.CRITICAL
                else:
                    session_priority = SessionPriority.NORMAL
            except ImportError:
                # Fallback para string simples
                session_priority = priority_value
            
            return orchestrator.create_session(
                user_id=params.get('user_id'),
                priority=session_priority,
                timeout=params.get('timeout'),
                metadata=params.get('metadata')
            )
        elif 'complete' in operation:
            return orchestrator.complete_session(
                params.get('session_id'),
                params.get('result')
            )
        elif 'workflow' in operation:
            return orchestrator.execute_session_workflow(
                params.get('session_id'),
                params.get('workflow_type'),
                params.get('workflow_data', {})
            )
        elif 'query' in operation or 'intelligent' in operation:
            # CORREÇÃO: Usar await adequadamente para métodos async
            query = params.get('query', '')
            context = params.get('context', {})
            
            # Chama o método process_query que acabei de adicionar
            if hasattr(orchestrator, 'process_query'):
                # CORRIGIDO: Usar await em vez de criar novo loop
                return await orchestrator.process_query(query, context)
            else:
                return {"error": "SessionOrchestrator não tem método process_query"}
        else:
            # Operação genérica
            return getattr(orchestrator, operation, lambda: "Operação não encontrada")()
    
    def _execute_workflow_operation(self, orchestrator, task: OrchestrationTask) -> Any:
        """Executa operação de workflow."""
        # Implementação específica para workflow
        if hasattr(orchestrator, task.operation):
            method = getattr(orchestrator, task.operation)
            return method(**task.parameters)
        return f"Workflow operation: {task.operation}"
    
    async def _execute_generic_operation(self, orchestrator, task: OrchestrationTask) -> Any:
        """Executa operação genérica."""
        # Verificar se é uma operação de integração
        if self._is_integration_operation(task.operation):
            return await self._execute_integration_operation(task)
        
        if hasattr(orchestrator, task.operation):
            method = getattr(orchestrator, task.operation)
            if callable(method):
                return await method(**task.parameters)
        return f"Generic operation: {task.operation} executed"
    
    def _is_integration_operation(self, operation: str) -> bool:
        """Verifica se é uma operação de integração."""
        integration_keywords = ['integration', 'api', 'external', 'service', 'connect']
        return any(keyword in operation.lower() for keyword in integration_keywords)
    
    async def _execute_integration_operation(self, task: OrchestrationTask) -> Any:
        """Executa operação de integração usando IntegrationManager."""
        try:
            if not self.integration_manager:
                return {
                    "status": "no_integration_manager",
                    "message": "IntegrationManager não disponível",
                    "operation": task.operation
                }
            
            # Mapear operações para métodos do IntegrationManager
            operation_lower = task.operation.lower()
            
            if 'initialize' in operation_lower:
                # CORRIGIDO: integration_manager sempre retorna None agora
                return {
                    "status": "integration_initialization_skipped",
                    "message": "Inicialização do IntegrationManager ignorada para evitar loop",
                    "operation": task.operation
                }
            elif 'health' in operation_lower:
                # CORRIGIDO: integration_manager sempre retorna None agora
                return {
                    "status": "integration_health_unavailable",
                    "message": "Health check do IntegrationManager não disponível",
                    "operation": task.operation
                }
            elif 'status' in operation_lower:
                # CORRIGIDO: integration_manager sempre retorna None agora
                return {
                    "status": "integration_status_unavailable",
                    "message": "Status do IntegrationManager não disponível",
                    "operation": task.operation
                }
            elif 'process' in operation_lower:
                query = task.parameters.get('query')
                context = task.parameters.get('context', {})
                # CORRIGIDO: Removida chamada recursiva que causava loop infinito
                # Em vez de chamar integration_manager, retornar resultado direto
                return {
                    "status": "integration_operation_direct",
                    "operation": task.operation,
                    "query": task.parameters.get('query'),
                    "context": task.parameters.get('context', {}),
                    "message": "Operação de integração processada diretamente",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Operação genérica de integração
                return {
                    "status": "integration_executed",
                    "operation": task.operation,
                    "parameters": task.parameters,
                    "manager": "IntegrationManager"
                }
                
        except Exception as e:
            logger.error(f"❌ Erro na operação de integração {task.operation}: {e}")
            return {
                "status": "integration_error",
                "error": str(e),
                "operation": task.operation
            }
    
    def _record_operation(self, task: OrchestrationTask):
        """Registra operação no histórico."""
        self.operation_history.append({
            'task_id': task.task_id,
            'orchestrator': task.orchestrator_type.value,
            'operation': task.operation,
            'status': task.status,
            'created_at': task.created_at.isoformat(),
            'completed_at': datetime.now().isoformat(),
            'duration_seconds': (datetime.now() - task.created_at).total_seconds(),
            'error': task.error
        })
        
        # Manter apenas últimas 100 operações
        if len(self.operation_history) > 100:
            self.operation_history = self.operation_history[-100:]
    
    def get_orchestrator_status(self) -> Dict[str, Any]:
        """
        Retorna status completo de todos os orquestradores.
        
        Returns:
            Status detalhado dos orquestradores
        """
        status = {
            'manager': 'OrchestratorManager',
            'total_orchestrators': len(self.orchestrators),
            'active_tasks': len(self.active_tasks),
            'operation_history_count': len(self.operation_history),
            'orchestrators': {},
            'availability': {
                'main_orchestrators': ORCHESTRATORS_AVAILABLE,
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Status individual dos orquestradores
        for orch_type, orch_instance in self.orchestrators.items():
            try:
                if hasattr(orch_instance, 'get_status'):
                    orch_status = orch_instance.get_status()
                elif hasattr(orch_instance, 'health_check'):
                    orch_status = {
                        'healthy': orch_instance.health_check(),
                        'type': orch_type.value
                    }
                else:
                    orch_status = {
                        'available': True,
                        'type': orch_type.value
                    }
                
                status['orchestrators'][orch_type.value] = orch_status
                
            except Exception as e:
                logger.error(f"❌ Erro ao obter status do {orch_type.value}: {e}")
                status['orchestrators'][orch_type.value] = {
                    'available': False,
                    'error': str(e),
                    'type': orch_type.value
                }
        
        return status
    
    def health_check(self) -> bool:
        """
        Verifica saúde geral do sistema de orquestração.
        
        Returns:
            True se sistema está saudável
        """
        try:
            # Verificar se pelo menos metade dos orquestradores está funcionando
            healthy_count = 0
            total_count = len(self.orchestrators)
            
            for orch_type, orch_instance in self.orchestrators.items():
                try:
                    if hasattr(orch_instance, 'health_check'):
                        if orch_instance.health_check():
                            healthy_count += 1
                    else:
                        # Assumir saudável se não há método de health check
                        healthy_count += 1
                except Exception:
                    # Orquestrador com problema
                    pass
            
            health_ratio = healthy_count / total_count if total_count > 0 else 0
            is_healthy = health_ratio >= 0.5
            
            if is_healthy:
                logger.debug(f"✅ OrchestratorManager saudável: {healthy_count}/{total_count} orquestradores ativos")
            else:
                logger.warning(f"⚠️ OrchestratorManager com problemas: {healthy_count}/{total_count} orquestradores ativos")
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"❌ Erro no health check do OrchestratorManager: {e}")
            return False
    
    def get_operation_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retorna histórico de operações.
        
        Args:
            limit: Número máximo de operações
            
        Returns:
            Lista das últimas operações
        """
        return self.operation_history[-limit:] if self.operation_history else []
    
    def clear_history(self):
        """Limpa histórico de operações."""
        self.operation_history.clear()
        logger.info("🧹 Histórico de operações limpo")


# Instância global para conveniência
_orchestrator_manager = None
_manager_lock = Lock()

def get_orchestrator_manager() -> OrchestratorManager:
    """
    Retorna instância global do OrchestratorManager.
    
    Returns:
        Instância do OrchestratorManager
    """
    global _orchestrator_manager
    
    if _orchestrator_manager is None:
        with _manager_lock:
            if _orchestrator_manager is None:
                _orchestrator_manager = OrchestratorManager()
    
    return _orchestrator_manager

async def orchestrate_system_operation(operation_type: str, 
                                data: Dict[str, Any],
                                target_orchestrator: Optional[str] = None,
                                mode: str = "intelligent",
                                priority: int = 1) -> Dict[str, Any]:
    """
    Função de conveniência para orquestrar operações no sistema.
    
    Args:
        operation_type: Tipo da operação
        data: Dados da operação
        target_orchestrator: Orquestrador específico (opcional)
        mode: Modo de orquestração
        priority: Prioridade da operação
        
    Returns:
        Resultado da orquestração
    """
    manager = get_orchestrator_manager()
    
    # Converter strings para enums se necessário
    target_enum = None
    if target_orchestrator:
        try:
            target_enum = OrchestratorType(target_orchestrator.lower())
        except ValueError:
            logger.warning(f"⚠️ Tipo de orquestrador inválido: {target_orchestrator}")
    
    try:
        mode_enum = OrchestrationMode(mode.lower())
    except ValueError:
        logger.warning(f"⚠️ Modo inválido: {mode}, usando intelligent")
        mode_enum = OrchestrationMode.INTELLIGENT
    
    return await manager.orchestrate_operation(
        operation_type=operation_type,
        data=data,
        target_orchestrator=target_enum,
        mode=mode_enum,
        priority=priority
    )

def get_orchestration_status() -> Dict[str, Any]:
    """
    Função de conveniência para obter status dos orquestradores.
    
    Returns:
        Status completo do sistema de orquestração
    """
    manager = get_orchestrator_manager()
    return manager.get_orchestrator_status()

# Compatibilidade com código existente
def get_system_orchestrator():
    """Alias para compatibilidade."""
    return get_orchestrator_manager() 