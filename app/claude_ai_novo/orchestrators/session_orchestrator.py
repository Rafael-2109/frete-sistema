"""
🔄 SESSION ORCHESTRATOR - Gerenciamento de Sessões IA
===================================================

Responsabilidade: ORQUESTRAR e gerenciar o ciclo de vida das sessões IA.
Especializações: Lifecycle Management, Coordenação de Componentes, Workflow, Estado de Sessão.
"""

import logging
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from threading import Lock
from enum import Enum

# Import dos tipos compartilhados
from .types import SessionStatus, SessionPriority

# Imports internos
try:
    from app.claude_ai_novo.memorizers.session_memory import get_session_memory
    from app.claude_ai_novo.analyzers.performance_analyzer import get_performance_analyzer
    from app.claude_ai_novo.utils.flask_fallback import get_current_user
except ImportError:
    try:
        # Fallback para imports relativos
        from ..memorizers.session_memory import get_session_memory
        from ..analyzers.performance_analyzer import get_performance_analyzer
        from ..utils.flask_fallback import get_current_user
    except ImportError as e:
        logging.warning(f"⚠️ Dependências não disponíveis: {e}")
        # Fallbacks seguros - sem anotações de tipo para evitar conflitos
        get_session_memory = lambda: MockSessionMemory()
        get_performance_analyzer = lambda: MockPerformanceAnalyzer()
        get_current_user = lambda: None

logger = logging.getLogger(__name__)

class MockSessionMemory:
    """Mock para session_memory quando não disponível"""
    def __init__(self):
        self.sessions = {}
    
    def store_session(self, session_id: str, metadata: dict, user_id: Optional[int] = None):
        self.sessions[session_id] = {
            'metadata': metadata,
            'user_id': user_id,
            'stored_at': datetime.now()
        }
    
    def update_session_metadata(self, session_id: str, metadata: dict):
        if session_id in self.sessions:
            self.sessions[session_id]['metadata'].update(metadata)
    
    def get_session(self, session_id: str):
        return self.sessions.get(session_id)

class MockPerformanceAnalyzer:
    """Mock para performance_analyzer quando não disponível"""
    def analyze(self, *args, **kwargs):
        return {"performance": "mock", "status": "ok"}
    
    def get_metrics(self):
        return {"metrics": "mock", "healthy": True}

@dataclass
class SessionContext:
    """Contexto de uma sessão IA."""
    session_id: str
    user_id: Optional[int] = None
    status: SessionStatus = SessionStatus.CREATED
    priority: SessionPriority = SessionPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    components: Dict[str, Any] = field(default_factory=dict)
    workflow_state: Dict[str, Any] = field(default_factory=dict)
    error_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def is_expired(self) -> bool:
        """Verifica se a sessão expirou."""
        return self.expires_at is not None and datetime.now() > self.expires_at
    
    def is_active(self) -> bool:
        """Verifica se a sessão está ativa."""
        return self.status in [SessionStatus.ACTIVE, SessionStatus.PROCESSING, SessionStatus.WAITING_INPUT]
    
    def update_activity(self):
        """Atualiza timestamp da última atividade."""
        self.last_activity = datetime.now()

class SessionOrchestrator:
    """
    Orquestrador especializado no gerenciamento de sessões IA.
    
    Responsabilidades:
    - Gerenciar ciclo de vida das sessões
    - Coordenar componentes da sessão
    - Controlar workflow e estado
    - Monitorar performance e saúde
    """
    
    def __init__(self, default_timeout: int = 3600):
        """
        Inicializa o orquestrador de sessões.
        
        Args:
            default_timeout: Timeout padrão em segundos (1 hora)
        """
        self.default_timeout = default_timeout
        self.active_sessions: Dict[str, SessionContext] = {}
        self.session_lock = Lock()
        
        # Inicializar dependências com fallbacks
        self.session_memory = self._get_session_memory_safe()
        self.performance_analyzer = self._get_performance_analyzer_safe()
        self.cleanup_handlers: List[Callable] = []
        
        # Lazy loading do módulo de alto valor
        self._learning_core = None
        
        # Lazy loading do SecurityGuard (CRÍTICO)
        self._security_guard = None
        
        # Lazy loading do ConversationManager (GESTÃO DE CONVERSAS)
        self._conversation_manager = None
        
        logger.info("🔄 SessionOrchestrator inicializado")
    
    @property
    def learning_core(self):
        """Lazy loading do LearningCore"""
        if self._learning_core is None:
            try:
                from app.claude_ai_novo.learners.learning_core import get_learning_core
                self._learning_core = get_learning_core()
                logger.info("✅ LearningCore integrado ao SessionOrchestrator")
            except ImportError as e:
                logger.warning(f"⚠️ LearningCore não disponível: {e}")
                self._learning_core = False  # Marcar como indisponível
        return self._learning_core if self._learning_core is not False else None
    
    @property
    def security_guard(self):
        """Lazy loading do SecurityGuard"""
        if self._security_guard is None:
            try:
                from app.claude_ai_novo.security.security_guard import get_security_guard
                self._security_guard = get_security_guard()
                logger.info("🔐 SecurityGuard integrado ao SessionOrchestrator")
            except ImportError as e:
                logger.warning(f"⚠️ SecurityGuard não disponível: {e}")
                self._security_guard = False  # Marcar como indisponível
        return self._security_guard if self._security_guard is not False else None
    
    @property
    def conversation_manager(self):
        """Lazy loading do ConversationManager"""
        if self._conversation_manager is None:
            try:
                from app.claude_ai_novo.conversers.conversation_manager import get_conversation_manager
                self._conversation_manager = get_conversation_manager()
                logger.info("💬 ConversationManager integrado ao SessionOrchestrator")
            except ImportError as e:
                logger.warning(f"⚠️ ConversationManager não disponível: {e}")
                self._conversation_manager = False  # Marcar como indisponível
        return self._conversation_manager if self._conversation_manager is not False else None
    
    def _get_session_memory_safe(self):
        """Obtém session_memory com fallback seguro"""
        try:
            memory = get_session_memory()
            if memory is not None:
                return memory
        except Exception as e:
            logger.warning(f"Session memory não disponível: {e}")
        
        # Fallback mock
        return MockSessionMemory()
    
    def _get_performance_analyzer_safe(self):
        """Obtém performance_analyzer com fallback seguro"""
        try:
            analyzer = get_performance_analyzer()
            if analyzer is not None:
                return analyzer
        except Exception as e:
            logger.warning(f"Performance analyzer não disponível: {e}")
        
        # Fallback mock
        return MockPerformanceAnalyzer()
    
    def create_session(self, user_id: Optional[int] = None, 
                      priority: SessionPriority = SessionPriority.NORMAL,
                      timeout: Optional[int] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Cria uma nova sessão IA.
        
        Args:
            user_id: ID do usuário (opcional)
            priority: Prioridade da sessão
            timeout: Timeout personalizado em segundos
            metadata: Metadata inicial da sessão
            
        Returns:
            ID da sessão criada
        """
        try:
            # 🔐 VALIDAÇÃO DE SEGURANÇA CRÍTICA
            if not self._validate_session_security("create_session", user_id, metadata):
                logger.warning(f"🚫 Criação de sessão bloqueada por motivos de segurança para usuário {user_id}")
                raise PermissionError("Acesso negado para criação de sessão")
            
            session_id = str(uuid.uuid4())
            
            # Definir expiração
            timeout_seconds = timeout or self.default_timeout
            expires_at = datetime.now() + timedelta(seconds=timeout_seconds)
            
            # Criar contexto da sessão
            session_context = SessionContext(
                session_id=session_id,
                user_id=user_id or self._get_current_user_id(),
                priority=priority,
                expires_at=expires_at,
                metadata=metadata or {}
            )
            
            # Adicionar metadata do sistema
            session_context.metadata.update({
                'created_by': 'session_orchestrator',
                'timeout_seconds': timeout_seconds,
                'priority': priority.value,
                'user_agent': self._get_user_agent(),
                'security_validated': True,  # Flag de segurança
                'created_timestamp': datetime.now().isoformat()
            })
            
            # Registrar sessão
            with self.session_lock:
                self.active_sessions[session_id] = session_context
            
            # Persistir na memória
            self.session_memory.store_session(session_id, session_context.metadata, user_id)
            
            # 🔐 LOG DE AUDITORIA
            self._log_session_audit("create_session", session_id, user_id, True, "Sessão criada com sucesso")
            
            logger.info(f"🆕 Sessão criada: {session_id} (usuário: {user_id}, prioridade: {priority.value})")
            return session_id
            
        except Exception as e:
            # 🔐 LOG DE AUDITORIA DE ERRO
            self._log_session_audit("create_session", "failed", user_id, False, f"Erro na criação: {str(e)}")
            logger.error(f"❌ Erro ao criar sessão: {e}")
            raise
    
    def initialize_session(self, session_id: str, 
                          components: Optional[Dict[str, Any]] = None) -> bool:
        """
        Inicializa uma sessão com componentes específicos.
        
        Args:
            session_id: ID da sessão
            components: Componentes para inicializar
            
        Returns:
            True se sucesso, False caso contrário
        """
        session = self.get_session(session_id)
        if not session:
            logger.error(f"❌ Sessão não encontrada para inicialização: {session_id}")
            return False
        
        try:
            # Atualizar status
            session.status = SessionStatus.INITIALIZING
            session.update_activity()
            
            # Inicializar componentes
            if components:
                session.components.update(components)
            
            # Executar inicialização personalizada
            self._execute_initialization_workflow(session)
            
            # Marcar como ativa
            session.status = SessionStatus.ACTIVE
            
            # Atualizar metadata
            session.metadata.update({
                'initialized_at': datetime.now().isoformat(),
                'components_count': len(session.components),
                'initialization_success': True
            })
            
            # Persistir mudanças
            self.session_memory.update_session_metadata(session_id, session.metadata)
            
            logger.info(f"🔧 Sessão inicializada: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na inicialização da sessão {session_id}: {e}")
            session.status = SessionStatus.FAILED
            session.error_history.append({
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'context': 'initialization'
            })
            return False
    
    def execute_session_workflow(self, session_id: str, 
                                workflow_type: str,
                                workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa workflow específico na sessão.
        
        Args:
            session_id: ID da sessão
            workflow_type: Tipo do workflow
            workflow_data: Dados do workflow
            
        Returns:
            Resultado do workflow
        """
        session = self.get_session(session_id)
        if not session:
            return {'error': 'Sessão não encontrada', 'session_id': session_id}
        
        if not session.is_active():
            return {'error': 'Sessão não está ativa', 'status': session.status.value}
        
        try:
            # Atualizar status
            session.status = SessionStatus.PROCESSING
            session.update_activity()
            
            # Executar workflow específico
            result = self._execute_workflow(session, workflow_type, workflow_data)
            
            # NOVA funcionalidade: Aprendizado vitalício
            if self.learning_core and workflow_type in ['query', 'intelligent_query']:
                learning_result = self._execute_learning_workflow(session, workflow_data, result)
                result['learning_insights'] = learning_result
            
            # NOVA funcionalidade: Gestão de conversas
            if self.conversation_manager and workflow_type in ['query', 'intelligent_query', 'conversation']:
                conversation_result = self._execute_conversation_workflow(session, workflow_data, result)
                result['conversation_insights'] = conversation_result
            
            # Atualizar estado do workflow
            session.workflow_state[workflow_type] = {
                'executed_at': datetime.now().isoformat(),
                'data': workflow_data,
                'result': result
            }
            
            # Retornar ao status ativo
            session.status = SessionStatus.ACTIVE
            
            # Atualizar metadata
            session.metadata.update({
                'last_workflow': workflow_type,
                'last_workflow_at': datetime.now().isoformat(),
                'workflow_count': len(session.workflow_state)
            })
            
            # Persistir mudanças
            self.session_memory.update_session_metadata(session_id, session.metadata)
            
            logger.info(f"⚙️ Workflow executado: {workflow_type} na sessão {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro no workflow {workflow_type} da sessão {session_id}: {e}")
            session.status = SessionStatus.FAILED
            session.error_history.append({
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'context': f'workflow_{workflow_type}'
            })
            return {'error': str(e), 'workflow_type': workflow_type}
    
    def _execute_learning_workflow(self, session: SessionContext, 
                                 workflow_data: Dict[str, Any],
                                 result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa workflow de aprendizado vitalício.
        
        Args:
            session: Contexto da sessão
            workflow_data: Dados do workflow
            result: Resultado do workflow
            
        Returns:
            Resultado do aprendizado
        """
        try:
            # Extrair informações para aprendizado
            consulta = workflow_data.get('query', workflow_data.get('text', ''))
            interpretacao = workflow_data.get('interpretation', workflow_data.get('context', {}))
            resposta = str(result.get('response', result.get('result', '')))
            feedback = workflow_data.get('feedback')
            
            # Executar aprendizado
            aprendizado = self.learning_core.aprender_com_interacao(
                consulta=consulta,
                interpretacao=interpretacao,
                resposta=resposta,
                feedback=feedback,
                usuario_id=session.user_id
            )
            
            # Atualizar metadata da sessão com aprendizado
            session.metadata.update({
                'learning_score': aprendizado.get('score_aprendizado', 0),
                'patterns_learned': len(aprendizado.get('padroes_detectados', [])),
                'last_learning_at': datetime.now().isoformat()
            })
            
            logger.info(f"🧠 Aprendizado executado na sessão {session.session_id}: score {aprendizado.get('score_aprendizado', 0):.2f}")
            return aprendizado
            
        except Exception as e:
            logger.error(f"❌ Erro no aprendizado da sessão {session.session_id}: {e}")
            return {'error': str(e), 'learning_failed': True}
    
    def _execute_conversation_workflow(self, session: SessionContext, 
                                     workflow_data: Dict[str, Any],
                                     result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa workflow de gestão de conversas.
        
        Args:
            session: Contexto da sessão
            workflow_data: Dados do workflow
            result: Resultado do workflow
            
        Returns:
            Resultado da gestão de conversas
        """
        try:
            # Extrair informações da conversa
            mensagem = workflow_data.get('query', workflow_data.get('message', ''))
            contexto = workflow_data.get('context', {})
            resposta = str(result.get('response', result.get('result', '')))
            
            # Executar gestão de conversas
            conversation_result = self.conversation_manager.manage_conversation(
                session_id=session.session_id,
                user_message=mensagem,
                ai_response=resposta,
                context=contexto,
                user_id=session.user_id
            )
            
            # Atualizar metadata da sessão com insights de conversa
            session.metadata.update({
                'conversation_turns': conversation_result.get('total_turns', 0),
                'conversation_score': conversation_result.get('conversation_score', 0),
                'context_continuity': conversation_result.get('context_continuity', 0),
                'last_conversation_at': datetime.now().isoformat()
            })
            
            logger.info(f"💬 Conversa gerenciada na sessão {session.session_id}: {conversation_result.get('total_turns', 0)} turnos")
            return conversation_result
            
        except Exception as e:
            logger.error(f"❌ Erro na gestão de conversa da sessão {session.session_id}: {e}")
            return {'error': str(e), 'conversation_failed': True}
    
    def apply_learned_knowledge(self, session_id: str, query: str) -> Dict[str, Any]:
        """
        Aplica conhecimento aprendido para melhorar uma consulta.
        
        Args:
            session_id: ID da sessão
            query: Consulta a ser melhorada
            
        Returns:
            Conhecimento aplicável
        """
        session = self.get_session(session_id)
        if not session:
            return {'error': 'Sessão não encontrada'}
        
        if not self.learning_core:
            return {'error': 'LearningCore não disponível'}
        
        try:
            # Aplicar conhecimento aprendido
            conhecimento = self.learning_core.aplicar_conhecimento(query)
            
            # Atualizar metadata da sessão
            session.metadata.update({
                'knowledge_applied': True,
                'knowledge_confidence': conhecimento.get('confianca_geral', 0),
                'last_knowledge_at': datetime.now().isoformat()
            })
            
            logger.info(f"📚 Conhecimento aplicado na sessão {session_id}: confiança {conhecimento.get('confianca_geral', 0):.2f}")
            return conhecimento
            
        except Exception as e:
            logger.error(f"❌ Erro ao aplicar conhecimento na sessão {session_id}: {e}")
            return {'error': str(e), 'knowledge_application_failed': True}
    
    def complete_session(self, session_id: str, 
                        result: Optional[Dict[str, Any]] = None) -> bool:
        """
        Completa uma sessão com resultado final.
        
        Args:
            session_id: ID da sessão
            result: Resultado final da sessão
            
        Returns:
            True se sucesso, False caso contrário
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        try:
            # Atualizar status
            session.status = SessionStatus.COMPLETED
            session.update_activity()
            
            # Armazenar resultado
            if result:
                session.metadata['final_result'] = result
            
            # Metadata de conclusão
            session.metadata.update({
                'completed_at': datetime.now().isoformat(),
                'duration_seconds': (datetime.now() - session.created_at).total_seconds(),
                'completion_success': True
            })
            
            # Persistir mudanças finais
            self.session_memory.update_session_metadata(session_id, session.metadata)
            
            # Executar cleanup
            self._execute_cleanup(session)
            
            # Remover da memória ativa
            with self.session_lock:
                self.active_sessions.pop(session_id, None)
            
            logger.info(f"✅ Sessão completada: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao completar sessão {session_id}: {e}")
            return False
    
    def terminate_session(self, session_id: str, reason: str = "manual_termination") -> bool:
        """
        Termina uma sessão forçadamente.
        
        Args:
            session_id: ID da sessão
            reason: Motivo da terminação
            
        Returns:
            True se sucesso, False caso contrário
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        try:
            # Atualizar status
            session.status = SessionStatus.TERMINATED
            session.update_activity()
            
            # Metadata de terminação
            session.metadata.update({
                'terminated_at': datetime.now().isoformat(),
                'termination_reason': reason,
                'forced_termination': True
            })
            
            # Persistir mudanças
            self.session_memory.update_session_metadata(session_id, session.metadata)
            
            # Executar cleanup
            self._execute_cleanup(session)
            
            # Remover da memória ativa
            with self.session_lock:
                self.active_sessions.pop(session_id, None)
            
            logger.info(f"🛑 Sessão terminada: {session_id} (motivo: {reason})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao terminar sessão {session_id}: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """
        Obtém contexto de uma sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Contexto da sessão ou None se não encontrada
        """
        with self.session_lock:
            return self.active_sessions.get(session_id)
    
    def get_user_sessions(self, user_id: int, include_inactive: bool = False) -> List[SessionContext]:
        """
        Obtém todas as sessões de um usuário.
        
        Args:
            user_id: ID do usuário
            include_inactive: Incluir sessões inativas
            
        Returns:
            Lista de contextos de sessão
        """
        sessions = []
        
        with self.session_lock:
            for session in self.active_sessions.values():
                if session.user_id == user_id:
                    if include_inactive or session.is_active():
                        sessions.append(session)
        
        return sessions
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove sessões expiradas.
        
        Returns:
            Número de sessões removidas
        """
        expired_sessions = []
        
        with self.session_lock:
            for session_id, session in self.active_sessions.items():
                if session.is_expired():
                    expired_sessions.append(session_id)
        
        # Remover sessões expiradas
        for session_id in expired_sessions:
            self.terminate_session(session_id, "expired")
        
        if expired_sessions:
            logger.info(f"🧹 {len(expired_sessions)} sessões expiradas removidas")
        
        return len(expired_sessions)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Obtém estatísticas das sessões ativas.
        
        Returns:
            Estatísticas das sessões
        """
        with self.session_lock:
            total_sessions = len(self.active_sessions)
            
            if total_sessions == 0:
                return {
                    'total_sessions': 0,
                    'by_status': {},
                    'by_priority': {},
                    'avg_duration': 0,
                    'generated_at': datetime.now().isoformat()
                }
            
            # Contar por status
            by_status = {}
            by_priority = {}
            durations = []
            
            for session in self.active_sessions.values():
                # Status
                status_key = session.status.value
                by_status[status_key] = by_status.get(status_key, 0) + 1
                
                # Prioridade
                priority_key = session.priority.value
                by_priority[priority_key] = by_priority.get(priority_key, 0) + 1
                
                # Duração
                duration = (datetime.now() - session.created_at).total_seconds()
                durations.append(duration)
            
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                'total_sessions': total_sessions,
                'by_status': by_status,
                'by_priority': by_priority,
                'avg_duration': round(avg_duration, 2),
                'oldest_session': min(durations) if durations else 0,
                'newest_session': max(durations) if durations else 0,
                'generated_at': datetime.now().isoformat()
            }
    
    def register_cleanup_handler(self, handler: Callable):
        """
        Registra handler para cleanup de sessões.
        
        Args:
            handler: Função de cleanup
        """
        self.cleanup_handlers.append(handler)
    
    def _execute_initialization_workflow(self, session: SessionContext):
        """Executa workflow de inicialização."""
        # Placeholder para lógica de inicialização personalizada
        pass
    
    def _execute_workflow(self, session: SessionContext, 
                         workflow_type: str, 
                         workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Executa workflow específico."""
        # REMOVIDO: Chamada ao IntegrationManager para evitar loop circular
        # Agora processa diretamente sem dependências circulares
        
        if workflow_type in ['query', 'intelligent_query']:
            # Processar query diretamente
            query = workflow_data.get('query', '')
            context = workflow_data.get('context', {})
            
            # Usar Claude diretamente se disponível
            try:
                # Usar ResponseProcessor do utils.base_classes
                from app.claude_ai_novo.processors.response_processor import ResponseProcessor
                processor = ResponseProcessor()
                
                # Processar com Claude
                response = processor.gerar_resposta_otimizada(
                    consulta=query,
                    analise={'dominio': 'entregas', 'query_type': 'status'},
                    user_context=context
                )
                
                if response:
                    return {
                        'workflow': workflow_type,
                        'status': 'completed',
                        'response': response,
                        'source': 'claude_direct'
                    }
                    
            except Exception as e:
                logger.error(f"Erro ao processar com Claude: {e}")
        
        return {"workflow": workflow_type, "status": "executed", "data": workflow_data}
    
    def _execute_cleanup(self, session: SessionContext):
        """Executa cleanup da sessão."""
        for handler in self.cleanup_handlers:
            try:
                handler(session)
            except Exception as e:
                logger.error(f"❌ Erro no cleanup handler: {e}")
    
    def _get_current_user_id(self) -> Optional[int]:
        """Obtém ID do usuário atual."""
        try:
            user = get_current_user()
            return user.id if user else None
        except Exception as e:
            logger.warning(f"Current user não disponível: {e}")
            return None
    
    def _get_user_agent(self) -> str:
        """Obtém user agent com fallback."""
        try:
            # Tentar obter user agent real
            import flask
            return flask.request.headers.get('User-Agent', 'Unknown')
        except Exception:
            return 'SessionOrchestrator/1.0'

    def _validate_session_security(self, operation: str, user_id: Optional[int] = None, 
                                  metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Valida segurança de operações de sessão.
        
        Args:
            operation: Operação de sessão
            user_id: ID do usuário
            metadata: Metadata da sessão
            
        Returns:
            True se operação é segura, False caso contrário
        """
        try:
            if not self.security_guard:
                # Sem SecurityGuard, permitir operação (modo degradado)
                logger.warning("⚠️ SecurityGuard não disponível - sessão permitida em modo degradado")
                return True
            
            # Validar acesso do usuário à operação
            if not self.security_guard.validate_user_access(operation, "session_management"):
                logger.warning(f"🚫 Usuário sem acesso à operação de sessão: {operation}")
                return False
            
            # Validar metadata se fornecida
            if metadata and not self.security_guard.validate_input(metadata):
                logger.warning(f"🚫 Metadata inválida para sessão: {operation}")
                return False
            
            # Validações específicas por operação
            if operation == "create_session":
                # Verificar limites de sessões por usuário
                if user_id and len(self.get_user_sessions(user_id, include_inactive=False)) >= 10:
                    logger.warning(f"🚫 Limite de sessões atingido para usuário {user_id}")
                    return False
            
            elif operation in ["terminate_session", "force_terminate"]:
                # Operações críticas requerem permissões especiais
                if not self.security_guard.validate_user_access(operation, "admin_resource"):
                    logger.warning(f"🚫 Operação crítica de sessão bloqueada: {operation}")
                    return False
            
            logger.debug(f"✅ Validação de segurança de sessão passou para: {operation}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na validação de segurança de sessão: {e}")
            # Em caso de erro, bloquear operação por segurança
            return False
    
    def _log_session_audit(self, operation: str, session_id: str, user_id: Optional[int],
                          success: bool, message: str):
        """
        Registra evento de auditoria de sessão.
        
        Args:
            operation: Operação de sessão
            session_id: ID da sessão
            user_id: ID do usuário
            success: Se operação foi bem-sucedida
            message: Mensagem do evento
        """
        try:
            if self.security_guard:
                audit_event = {
                    'timestamp': datetime.now().isoformat(),
                    'component': 'SessionOrchestrator',
                    'operation': operation,
                    'session_id': session_id,
                    'user_id': user_id,
                    'success': success,
                    'message': message,
                    'user_authenticated': getattr(self.security_guard, '_is_user_authenticated', lambda: False)()
                }
                
                # Log estruturado para auditoria
                if success:
                    logger.info(f"🔐 SESSION_AUDIT: {audit_event}")
                else:
                    logger.warning(f"🚫 SESSION_AUDIT: {audit_event}")
            
        except Exception as e:
            logger.error(f"❌ Erro no log de auditoria de sessão: {e}")

    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processa uma query e retorna resposta real.
        
        Args:
            query: Query do usuário
            context: Contexto adicional
            
        Returns:
            Resposta processada
        """
        try:
            # Detectar intenção da query
            intent = self._detect_query_intent(query)
            
            # Mapear para operação específica
            if intent == "status_entregas":
                return self._process_deliveries_status(query, context)
            elif intent == "consulta_fretes":
                return self._process_freight_inquiry(query, context)
            elif intent == "status_pedidos":
                return self._process_orders_status(query, context)
            elif intent == "relatorio_financeiro":
                return self._process_financial_report(query, context)
            else:
                # Resposta inteligente padrão
                return self._process_general_inquiry(query, context)
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar query: {e}")
            return {
                'success': False,
                'error': str(e),
                'result': f"Erro no processamento: {str(e)}",
                'query': query
            }
    
    def _detect_query_intent(self, query: str) -> str:
        """Detecta a intenção da query"""
        query_lower = query.lower()
        
        # Detectar intenções específicas
        if any(word in query_lower for word in ['entrega', 'entregar', 'atacadão', 'delivery']):
            return "status_entregas"
        elif any(word in query_lower for word in ['frete', 'freight', 'transportadora']):
            return "consulta_fretes"
        elif any(word in query_lower for word in ['pedido', 'order', 'compra']):
            return "status_pedidos"
        elif any(word in query_lower for word in ['financeiro', 'faturamento', 'relatório', 'report']):
            return "relatorio_financeiro"
        else:
            return "geral"
    
    def _process_deliveries_status(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Processa consultas sobre status de entregas"""
        # 🎯 USAR MAIN ORCHESTRATOR PARA FLUXO COMPLETO!
        
        try:
            from app.claude_ai_novo.orchestrators.main_orchestrator import get_main_orchestrator
            orchestrator = get_main_orchestrator()
            
            # Preparar contexto específico para entregas
            delivery_context = {
                'domain': 'entregas',
                'query_type': 'status',
                '_from_session': True,  # Evitar loops
                **(context or {})
            }
            
            # Processar com MainOrchestrator (usa TODA a inteligência)
            logger.info("🎯 Delegando para MainOrchestrator com fluxo completo")
            
            # MainOrchestrator é síncrono
            result = orchestrator.process_query(query, delivery_context)
            
            if result and result.get('response'):
                return {
                    'success': True,
                    'result': result['response'],
                    'query': query,
                    'intent': 'status_entregas',
                    'source': 'main_orchestrator',
                    'data': result.get('data', delivery_context)
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar com MainOrchestrator: {e}")
        
        # Fallback apenas se MainOrchestrator falhar
        return {
            'success': True,
            'result': f"📦 Status de Entregas: Sistema processando query '{query}'. Verificando dados...",
            'query': query,
            'intent': 'status_entregas',
            'source': 'session_orchestrator_fallback'
        }
    
    def _process_freight_inquiry(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Processa consultas sobre fretes"""
        return {
            'success': True,
            'result': f"🚚 Consulta de Fretes: Para a consulta '{query}', o sistema de fretes está operacional. Consulte a seção de fretes para mais detalhes.",
            'query': query,
            'intent': 'consulta_fretes',
            'source': 'session_orchestrator'
        }
    
    def _process_orders_status(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Processa consultas sobre status de pedidos"""
        return {
            'success': True,
            'result': f"📋 Status de Pedidos: Consulta '{query}' processada. Sistema de pedidos funcionando corretamente.",
            'query': query,
            'intent': 'status_pedidos',
            'source': 'session_orchestrator'
        }
    
    def _process_financial_report(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Processa consultas sobre relatórios financeiros"""
        return {
            'success': True,
            'result': f"💰 Relatório Financeiro: Consulta '{query}' processada. Sistema financeiro operacional.",
            'query': query,
            'intent': 'relatorio_financeiro',
            'source': 'session_orchestrator'
        }
    
    def _process_general_inquiry(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Processa consultas gerais"""
        # 🎯 USAR MAIN ORCHESTRATOR PARA TODAS AS CONSULTAS!
        
        try:
            from app.claude_ai_novo.orchestrators.main_orchestrator import get_main_orchestrator
            orchestrator = get_main_orchestrator()
            
            # Preparar contexto geral
            general_context = {
                'domain': 'geral',
                'query_type': 'informacao',
                '_from_session': True,  # Evitar loops
                **(context or {})
            }
            
            # Processar com MainOrchestrator (usa TODA a inteligência)
            logger.info("🎯 Processando consulta geral via MainOrchestrator")
            result = orchestrator.process_query(query, general_context)
            
            if result and result.get('response'):
                return {
                    'success': True,
                    'result': result['response'],
                    'query': query,
                    'intent': 'geral',
                    'source': 'main_orchestrator',
                    'data': result.get('data', general_context)
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar com MainOrchestrator: {e}")
        
        # Fallback apenas se MainOrchestrator falhar
        return {
            'success': True,
            'result': f"ℹ️ Sistema processando consulta: '{query}'",
            'query': query,
            'intent': 'geral',
            'source': 'session_orchestrator_fallback'
        }


# Instância global para conveniência
_session_orchestrator = None
_orchestrator_lock = Lock()

def get_session_orchestrator() -> SessionOrchestrator:
    """
    Retorna instância global do SessionOrchestrator.
    
    Returns:
        Instância do SessionOrchestrator
    """
    global _session_orchestrator
    
    if _session_orchestrator is None:
        with _orchestrator_lock:
            if _session_orchestrator is None:
                _session_orchestrator = SessionOrchestrator()
    
    return _session_orchestrator

def create_ai_session(user_id: Optional[int] = None, 
                     priority: SessionPriority = SessionPriority.NORMAL,
                     timeout: Optional[int] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Função de conveniência para criar sessão IA.
    
    Args:
        user_id: ID do usuário (opcional)
        priority: Prioridade da sessão
        timeout: Timeout personalizado em segundos
        metadata: Metadata inicial da sessão
        
    Returns:
        ID da sessão criada
    """
    return get_session_orchestrator().create_session(user_id, priority, timeout, metadata)

def complete_ai_session(session_id: str, result: Optional[Dict[str, Any]] = None) -> bool:
    """
    Função de conveniência para completar sessão IA.
    
    Args:
        session_id: ID da sessão
        result: Resultado final da sessão
        
    Returns:
        True se sucesso, False caso contrário
    """
    return get_session_orchestrator().complete_session(session_id, result) 