"""
🌐 WEB INTEGRATION - Integração com Interfaces Web
===============================================

Responsabilidade: INTEGRAR com interfaces web (Flask, futuras interfaces).
Consolida: flask_adapter.py + flask_routes.py

Especializações:
- Adapter síncrono para Flask
- Rotas organizadas e optimizadas  
- Interface padronizada para web
- Compatibilidade com sistema modular
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

# Flask imports
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)

# Imports das funções superiores para substituir duplicatas
try:
    from ..processors.context_processor import get_contextprocessor
    from ..learners.feedback_learning import get_feedback_processor
    ADVANCED_FUNCTIONS_AVAILABLE = True
except ImportError:
    ADVANCED_FUNCTIONS_AVAILABLE = False
    logger.warning("⚠️ Funções avançadas não disponíveis - usando fallbacks básicos")

class WebIntegrationAdapter:
    """
    Adapter para integração com interfaces web, especialmente Flask.
    
    Responsabilidades:
    - Prover interface síncrona para web
    - Coordenar com sistema modular
    - Gerenciar contexto de usuário web
    - Manter compatibilidade com código existente
    """
    
    def __init__(self):
        """Inicializa adapter para web."""
        self._integration_manager = None
        self._external_api_integration = None
        self.system_ready = False
        
        logger.info("🌐 Web Integration Adapter inicializado")
    
    def _get_integration_manager(self):
        """Lazy loading do Integration Manager."""
        if self._integration_manager is None:
            try:
                from .integration_manager import IntegrationManager
                
                # Tentar obter dependencies do Flask
                try:
                    from app import db
                    self._integration_manager = IntegrationManager(
                        claude_client=None,  # Será configurado via external API
                        db_engine=db.engine,
                        db_session=db.session
                    )
                except ImportError:
                    # Fallback sem Flask
                    self._integration_manager = IntegrationManager()
                    
            except Exception as e:
                logger.error(f"❌ Erro ao carregar Integration Manager: {e}")
        
        return self._integration_manager
    
    def _get_external_api_integration(self):
        """Lazy loading do External API Integration."""
        if self._external_api_integration is None:
            try:
                from .external_api_integration import get_external_api_integration
                self._external_api_integration = get_external_api_integration()
            except Exception as e:
                logger.error(f"❌ Erro ao carregar External API Integration: {e}")
        
        return self._external_api_integration
    
    def process_query_sync(self, query: Optional[str], context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Processa consulta de forma síncrona para uso em interfaces web.
        
        Args:
            query: Consulta do usuário
            context: Contexto adicional (usuário, sessão, etc.)
            
        Returns:
            Resultado processado
        """
        if not query or not isinstance(query, str):
            return {
                'success': False,
                'error': 'Consulta inválida',
                'fallback_response': 'Por favor, forneça uma consulta válida.'
            }
        
        try:
            # Rota 1: Usar External API Integration (Claude + sistema completo)
            external_api = self._get_external_api_integration()
            if external_api:
                result = self._run_async(external_api.process_query(query, context))
                
                if isinstance(result, str):
                    return {
                        'success': True,
                        'agent_response': {'response': result},
                        'method': 'external_api_integration'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Resposta inválida da API externa',
                        'fallback_response': result or 'Erro no processamento'
                    }
            
            # Rota 2: Usar Integration Manager diretamente
            manager = self._get_integration_manager()
            if manager:
                result = self._run_async(manager.process_unified_query(query, context))
                
                if result and result.get('success'):
                    return result
            
            # Rota 3: Fallback simples
            return {
                'success': False,
                'error': 'Nenhum sistema de processamento disponível',
                'fallback_response': 'Sistema temporariamente indisponível. Tente novamente em alguns momentos.'
            }
                
        except Exception as e:
            logger.error(f"❌ Erro no processamento web: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback_response': f'Erro interno: {str(e)}'
            }
    
    def processar_consulta_sync(self, query: Optional[str], context: Optional[Dict] = None) -> str:
        """
        Método de compatibilidade que retorna string diretamente.
        
        Args:
            query: Consulta do usuário
            context: Contexto adicional
            
        Returns:
            Resposta como string
        """
        result = self.process_query_sync(query, context)
        
        if result.get('success'):
            # Extrair resposta principal
            agent_response = result.get('agent_response', {})
            if isinstance(agent_response, dict) and 'response' in agent_response:
                return agent_response['response']
            elif isinstance(agent_response, str):
                return agent_response
            else:
                return str(result.get('agent_response', 'Resposta processada com sucesso'))
        else:
            return result.get('fallback_response', 'Erro no processamento')
    
    def get_module(self, module_name: str) -> Any:
        """
        Obtém acesso a um módulo específico do sistema.
        
        Args:
            module_name: Nome do módulo
            
        Returns:
            Instância do módulo ou None
        """
        try:
            manager = self._get_integration_manager()
            if manager and hasattr(manager, 'get_module'):
                return manager.get_module(module_name)
            else:
                logger.warning(f"⚠️ Integration Manager não disponível para módulo {module_name}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao obter módulo {module_name}: {e}")
            return None
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Obtém status completo do sistema para interfaces web.
        
        Returns:
            Dict com status detalhado
        """
        status = {
            'timestamp': datetime.now().isoformat(),
            'web_integration': {
                'available': True,
                'adapter_ready': True
            }
        }
        
        try:
            # Status do Integration Manager
            manager = self._get_integration_manager()
            if manager:
                manager_status = manager.get_system_status()
                status['integration_manager'] = manager_status
                status['system_ready'] = manager_status.get('ready_for_operation', False)
            
            # Status do External API Integration
            external_api = self._get_external_api_integration()
            if external_api:
                api_status = external_api.get_system_status()
                status['external_apis'] = api_status
            
            return status
                
        except Exception as e:
            logger.error(f"❌ Erro ao obter status: {e}")
            status['error'] = str(e)
            return status
    
    def get_available_modules(self) -> List[str]:
        """
        Lista módulos disponíveis no sistema.
        
        Returns:
            Lista de nomes dos módulos
        """
        try:
            manager = self._get_integration_manager()
            if manager and hasattr(manager, 'get_available_modules'):
                return manager.get_available_modules()
            else:
                return []
                
        except Exception as e:
            logger.error(f"❌ Erro ao listar módulos: {e}")
            return []
    
    def _run_async(self, coro):
        """
        Executa corrotina de forma síncrona para interfaces web.
        
        Args:
            coro: Corrotina para executar
            
        Returns:
            Resultado da corrotina
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(coro)
    
    # Propriedades de compatibilidade
    @property
    def claude_client(self):
        """Propriedade de compatibilidade para claude_client."""
        external_api = self._get_external_api_integration()
        if external_api and hasattr(external_api, 'claude_client'):
            return external_api.claude_client
        return None
    
    @property
    def db_engine(self):
        """Propriedade de compatibilidade para db_engine."""
        manager = self._get_integration_manager()
        if manager:
            return getattr(manager, 'db_engine', None)
        return None
    
    @property
    def initialization_result(self):
        """Propriedade de compatibilidade para initialization_result."""
        manager = self._get_integration_manager()
        if manager:
            return getattr(manager, 'initialization_result', None)
        return None

class WebFlaskRoutes:
    """
    Gerenciador de rotas Flask para integração web.
    
    Responsabilidades:
    - Definir rotas Flask organizadas
    - Processar requisições web
    - Gerenciar contexto de usuário
    - Integrar com WebIntegrationAdapter
    """
    
    def __init__(self, web_adapter: WebIntegrationAdapter):
        """
        Inicializa gerenciador de rotas.
        
        Args:
            web_adapter: Adapter de integração web
        """
        self.web_adapter = web_adapter
        self.blueprint = self._create_blueprint()
        
        logger.info("🛣️ Web Flask Routes inicializado")
    
    def _create_blueprint(self) -> Blueprint:
        """Cria e configura blueprint Flask."""
        bp = Blueprint('claude_ai', __name__, url_prefix='/claude-ai')
        
        # Registrar rotas
        self._register_routes(bp)
        
        return bp
    
    def _register_routes(self, bp: Blueprint):
        """Registra todas as rotas no blueprint."""
        
        @bp.route('/chat')
        @login_required
        def chat_page():
            """Página principal do chat."""
            return render_template('claude_ai/chat.html', user=current_user)
        
        @bp.route('/api/query', methods=['POST'])
        @login_required
        def api_query():
            """API principal para consultas."""
            try:
                data = request.get_json()
                query = data.get('query', '').strip()
                
                if not query:
                    return jsonify({'success': False, 'error': 'Consulta vazia'})
                
                # Contexto do usuário web
                user_context = self._build_user_context(query)
                
                # Processar consulta
                response_result = self.web_adapter.process_query_sync(query, user_context)
                
                # Extrair resposta
                if response_result.get('success'):
                    agent_response = response_result.get('agent_response', {})
                    
                    if isinstance(agent_response, dict) and 'response' in agent_response:
                        response_text = agent_response['response']
                    elif isinstance(agent_response, str):
                        response_text = agent_response
                    else:
                        response_text = str(response_result.get('agent_response', 'Resposta processada'))
                    
                    return jsonify({
                        'success': True,
                        'response': response_text,
                        'system_info': {
                            'method': response_result.get('method', 'unknown'),
                            'modules_used': response_result.get('modules_used', []),
                            'enhanced_query': response_result.get('enhanced_query') != query
                        }
                    })
                else:
                    # Fallback
                    fallback_response = self.web_adapter.processar_consulta_sync(query, user_context)
                    
                    return jsonify({
                        'success': True,
                        'response': fallback_response,
                        'system_info': {'method': 'fallback'}
                    })
                
            except Exception as e:
                logger.error(f"❌ Erro na API de consulta: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Erro interno: {str(e)}'
                }), 500
        
        @bp.route('/api/feedback', methods=['POST'])
        @login_required
        def api_feedback():
            """API para feedback do usuário."""
            try:
                data = request.get_json()
                query = data.get('query', '')
                response = data.get('response', '')
                feedback_type = data.get('feedback_type', 'positive')
                feedback_text = data.get('feedback_text', '')
                
                feedback = {
                    'type': feedback_type,
                    'text': feedback_text,
                    'user_id': current_user.id,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Registrar feedback
                self._record_feedback(query, response, feedback)
                
                return jsonify({
                    'success': True,
                    'message': 'Feedback registrado com sucesso'
                })
                
            except Exception as e:
                logger.error(f"❌ Erro ao registrar feedback: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Erro interno: {str(e)}'
                }), 500
        
        @bp.route('/clear-context')
        @login_required
        def clear_context():
            """Limpa contexto conversacional."""
            try:
                # Tentar limpar contexto via módulo
                context_module = self.web_adapter.get_module('conversation_context')
                if context_module and hasattr(context_module, 'clear_context'):
                    context_module.clear_context(str(current_user.id))
                    logger.info("✅ Contexto limpo via módulo")
                else:
                    logger.info("💡 Módulo de contexto não disponível")
                
                return jsonify({
                    'success': True,
                    'message': 'Contexto limpo com sucesso'
                })
                
            except Exception as e:
                logger.error(f"❌ Erro ao limpar contexto: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @bp.route('/health')
        @login_required
        def health_check():
            """Health check do sistema."""
            try:
                system_status = self.web_adapter.get_system_status()
                
                is_ready = system_status.get('system_ready', False)
                manager_status = system_status.get('integration_manager', {})
                
                active_modules = manager_status.get('active_modules', 0)
                total_modules = manager_status.get('total_modules', 0)
                
                return jsonify({
                    'status': 'healthy' if is_ready else 'degraded',
                    'system_ready': is_ready,
                    'modules': {
                        'active': active_modules,
                        'total': total_modules,
                        'percentage': round((active_modules / max(total_modules, 1)) * 100, 1)
                    },
                    'claude_client': self.web_adapter.claude_client is not None,
                    'database': self.web_adapter.db_engine is not None,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"❌ Erro no health check: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @bp.route('/system-status')
        @login_required
        def system_status():
            """Status detalhado do sistema para debug."""
            try:
                status = self.web_adapter.get_system_status()
                
                return jsonify({
                    'success': True,
                    'status': status,
                    'available_modules': self.web_adapter.get_available_modules(),
                    'initialization_result': self.web_adapter.initialization_result
                })
                
            except Exception as e:
                logger.error(f"❌ Erro ao obter status: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    
    def _build_user_context(self, query: Optional[str] = None) -> Dict[str, Any]:
        """Constrói contexto avançado do usuário usando ContextProcessor."""
        # Contexto básico para compatibilidade
        basic_context = {
            'user_id': current_user.id,
            'user_name': current_user.nome,
            'user_profile': getattr(current_user, 'perfil', 'user'),
            'vendedor_codigo': getattr(current_user, 'vendedor_codigo', None),
            'source': 'web_interface'
        }
        
        # Se funções avançadas disponíveis e query fornecida, usar contexto inteligente
        if ADVANCED_FUNCTIONS_AVAILABLE and query:
            try:
                context_processor = get_contextprocessor()
                
                # Análise básica para contexto inteligente
                analise = {
                    'periodo_dias': 30,
                    'cliente_especifico': None,
                    'usuario_id': current_user.id
                }
                
                # Carregar contexto inteligente
                intelligent_context = context_processor.carregar_contexto_inteligente(query, analise)
                
                # Combinar contextos
                if intelligent_context:
                    basic_context.update({
                        'intelligent_data': intelligent_context,
                        'enhanced': True,
                        'dominio': intelligent_context.get('dominio', 'geral')
                    })
                    logger.debug(f"🧠 Contexto inteligente carregado: {intelligent_context.get('dominio', 'geral')}")
                
            except Exception as e:
                logger.warning(f"⚠️ Erro ao carregar contexto inteligente: {e}")
                basic_context['enhanced'] = False
        else:
            basic_context['enhanced'] = False
        
        return basic_context
    
    def _record_feedback(self, query: str, response: str, feedback: Dict[str, Any]):
        """Registra feedback avançado no sistema usando FeedbackProcessor."""
        try:
            # Usar FeedbackProcessor avançado se disponível
            if ADVANCED_FUNCTIONS_AVAILABLE:
                feedback_processor = get_feedback_processor()
                
                # Construir interpretação básica para o feedback
                interpretacao = {
                    'query_original': query,
                    'resposta_gerada': response,
                    'metodo_processamento': 'web_integration',
                    'timestamp': datetime.now().isoformat()
                }
                
                # Processar feedback completo
                melhorias = feedback_processor.processar_feedback_completo(
                    consulta=query,
                    interpretacao=interpretacao,
                    resposta=response,
                    feedback=feedback,
                    usuario_id=feedback.get('user_id')
                )
                
                if melhorias:
                    logger.info(f"🎯 Feedback avançado processado: {len(melhorias)} melhorias aplicadas")
                    # Adicionar info sobre melhorias no contexto
                    feedback['melhorias_aplicadas'] = len(melhorias)
                    feedback['processamento_avancado'] = True
                else:
                    logger.info("📝 Feedback avançado registrado (sem melhorias automáticas)")
                    feedback['processamento_avancado'] = True
                
            else:
                # Fallback para sistema básico
                learning_module = self.web_adapter.get_module('learning_core')
                if learning_module and hasattr(learning_module, 'record_feedback'):
                    # Executar de forma assíncrona
                    self.web_adapter._run_async(
                        learning_module.record_feedback(query, response, feedback)
                    )
                    logger.info("✅ Feedback registrado no sistema de aprendizado básico")
                    feedback['processamento_avancado'] = False
                else:
                    logger.info("💡 Sistema de aprendizado não disponível")
                    feedback['processamento_avancado'] = False
                    
        except Exception as e:
            logger.warning(f"⚠️ Erro ao registrar feedback: {e}")
            # Tentar fallback simples
            try:
                learning_module = self.web_adapter.get_module('learning_core')
                if learning_module and hasattr(learning_module, 'record_feedback'):
                    self.web_adapter._run_async(
                        learning_module.record_feedback(query, response, feedback)
                    )
                    logger.info("✅ Feedback registrado via fallback")
            except Exception as fallback_error:
                logger.error(f"❌ Erro no fallback de feedback: {fallback_error}")
    
    def get_blueprint(self) -> Blueprint:
        """Retorna blueprint Flask configurado."""
        return self.blueprint


# Instâncias globais
_web_integration_adapter = None
_flask_routes = None

def get_web_integration_adapter() -> WebIntegrationAdapter:
    """
    Retorna instância global do Web Integration Adapter.
    
    Returns:
        Instância do WebIntegrationAdapter
    """
    global _web_integration_adapter
    if _web_integration_adapter is None:
        _web_integration_adapter = WebIntegrationAdapter()
    return _web_integration_adapter

def get_flask_routes() -> WebFlaskRoutes:
    """
    Retorna instância global do Flask Routes.
    
    Returns:
        Instância do WebFlaskRoutes
    """
    global _flask_routes
    if _flask_routes is None:
        adapter = get_web_integration_adapter()
        _flask_routes = WebFlaskRoutes(adapter)
    return _flask_routes

def create_integration_routes() -> Blueprint:
    """
    Cria blueprint com rotas de integração web.
    
    Returns:
        Blueprint Flask configurado
    """
    routes = get_flask_routes()
    return routes.get_blueprint()

# Funções de compatibilidade
def get_flask_adapter():
    """Compatibilidade - retorna web integration adapter."""
    return get_web_integration_adapter()

def get_claude_ai_instance():
    """Compatibilidade - retorna web integration adapter."""
    return get_web_integration_adapter() 