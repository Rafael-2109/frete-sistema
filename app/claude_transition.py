"""
Interface de Transição - Claude AI
Permite usar tanto o sistema antigo quanto o novo com diagnóstico completo
"""

import time
from datetime import datetime
from typing import Optional, Dict, Any
import logging
import asyncio
import os

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClaudeTransitionManager:
    """
    Gerenciador de transição entre sistemas Claude AI
    Responsável por rotear queries para o sistema apropriado
    """
    
    def __init__(self):
        self._use_new_system = os.getenv('USE_NEW_CLAUDE_SYSTEM', 'false').lower() == 'true'
        self.claude = None
        self._initialize_system()
    
    def _initialize_system(self):
        """Inicializa o sistema Claude ativo"""
        if self._use_new_system:
            try:
                # SOLUÇÃO: Criar app context para o sistema novo
                from app import create_app
                app = create_app()
                
                with app.app_context():
                    # Inicializar sistema novo com Flask context
                    from app.claude_ai_novo.orchestrators.orchestrator_manager import OrchestratorManager
                    self.claude = OrchestratorManager()
                    # Guardar referência do app para usar depois
                    self._app = app
                    
                logger.info("✅ Sistema Claude AI Novo inicializado com Flask context")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar sistema novo: {e}")
                self._use_new_system = False
        
        if not self._use_new_system:
            try:
                # Fallback para sistema antigo
                from app.claude_ai.claude_real_integration import ClaudeRealIntegration
                self.claude = ClaudeRealIntegration()
                logger.info("✅ Sistema Claude AI Antigo inicializado (fallback)")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar sistema antigo: {e}")
                self.claude = None
    
    async def processar_consulta(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processa consulta usando o sistema ativo (com métricas integradas)"""
        
        # Registrar início da query
        start_time = time.time()
        query_type = self._classify_query_type(consulta)
        success = False
        tokens_used = 0
        
        try:
            # Registrar métricas - importação dinâmica para evitar problemas de inicialização
            try:
                from app.claude_ai_novo.monitoring.real_time_metrics import record_query_metric
                metrics_available = True
            except ImportError:
                metrics_available = False
            
            if self._use_new_system:
                try:
                    # Sistema novo - verificar se é assíncrono
                    if hasattr(self.claude, 'process_query'):
                        # CORREÇÃO: Executar com Flask context se disponível
                        if hasattr(self, '_app'):
                            with self._app.app_context():
                                result = await self.claude.process_query(consulta, user_context)
                        else:
                            result = await self.claude.process_query(consulta, user_context)
                        
                        # CORREÇÃO: Extrair resposta corretamente do resultado complexo
                        if isinstance(result, dict):
                            # Tentar extrair a resposta real do resultado
                            if result.get('success'):
                                # Usar o novo método de extração recursiva
                                response_text = self._extract_response_from_nested(result)
                                
                                if response_text:
                                    success = True
                                    tokens_used = self._estimate_tokens(response_text)
                                    
                                    # Registrar métricas se disponível
                                    if metrics_available:
                                        response_time = time.time() - start_time
                                        record_query_metric(query_type, response_time, success, tokens_used)
                                    
                                    return response_text
                                else:
                                    # Se não conseguiu extrair, tentar retornar estrutura como JSON
                                    logger.warning(f"⚠️ Não foi possível extrair resposta de: {type(result)}")
                                    
                                    # Registrar métricas de erro parcial
                                    if metrics_available:
                                        response_time = time.time() - start_time
                                        record_query_metric(query_type, response_time, False, 0)
                                    
                                    # Retornar resultado como JSON string se possível
                                    try:
                                        import json
                                        return json.dumps(result, ensure_ascii=False, indent=2)
                                    except:
                                        return str(result)
                            
                            # Se não conseguir extrair, tentar outras estruturas
                            if 'error' in result:
                                error_msg = result['error']
                                logger.error(f"❌ Erro no sistema novo: {error_msg}")
                                
                                # Registrar métricas de erro
                                if metrics_available:
                                    response_time = time.time() - start_time
                                    record_query_metric(query_type, response_time, False, 0)
                                
                                return f"Erro no processamento: {error_msg}"
                        
                        # Se chegou aqui, algo deu errado na extração
                        logger.warning(f"⚠️ Resposta não extraída corretamente: {type(result)}")
                        
                        # Registrar métricas de erro
                        if metrics_available:
                            response_time = time.time() - start_time
                            record_query_metric(query_type, response_time, False, 0)
                        
                        return str(result) if result is not None else "Resposta não disponível"
                    
                    else:
                        logger.error("❌ Sistema novo não possui método process_query")
                        
                        # Registrar métricas de erro
                        if metrics_available:
                            response_time = time.time() - start_time
                            record_query_metric(query_type, response_time, False, 0)
                        
                        return "Sistema novo não configurado corretamente"
                        
                except Exception as e:
                    logger.error(f"❌ Erro no sistema novo: {e}")
                    
                    # Registrar métricas de erro
                    if metrics_available:
                        response_time = time.time() - start_time
                        record_query_metric(query_type, response_time, False, 0)
                    
                    return f"Erro no sistema novo: {str(e)}"
            
            else:
                # Sistema antigo
                try:
                    if hasattr(self.claude, 'process_query'):
                        result = await self.claude.process_query(consulta, user_context)
                        
                        if result:
                            success = True
                            tokens_used = self._estimate_tokens(str(result))
                            
                            # Registrar métricas se disponível
                            if metrics_available:
                                response_time = time.time() - start_time
                                record_query_metric(query_type, response_time, success, tokens_used)
                            
                            return str(result)
                        else:
                            # Registrar métricas de erro
                            if metrics_available:
                                response_time = time.time() - start_time
                                record_query_metric(query_type, response_time, False, 0)
                            
                            return "Resposta não disponível"
                            
                    else:
                        # Registrar métricas de erro
                        if metrics_available:
                            response_time = time.time() - start_time
                            record_query_metric(query_type, response_time, False, 0)
                        
                        return "Sistema antigo não configurado corretamente"
                        
                except Exception as e:
                    logger.error(f"❌ Erro no sistema antigo: {e}")
                    
                    # Registrar métricas de erro
                    if metrics_available:
                        response_time = time.time() - start_time
                        record_query_metric(query_type, response_time, False, 0)
                    
                    return f"Erro no sistema antigo: {str(e)}"
        
        except Exception as e:
            logger.error(f"❌ Erro geral no processamento: {e}")
            
            # Registrar métricas de erro
            try:
                if metrics_available:
                    response_time = time.time() - start_time
                    record_query_metric(query_type, response_time, False, 0)
            except:
                pass
            
            return f"Erro no processamento: {str(e)}"
    
    def _extract_response_from_nested(self, data: Any, depth: int = 0) -> Optional[str]:
        """
        Extrai a resposta de texto de uma estrutura aninhada.
        
        Args:
            data: Dados para extrair resposta
            depth: Profundidade atual da recursão
            
        Returns:
            Texto da resposta ou None
        """
        # Evitar recursão infinita
        if depth > 10:
            return None
        
        # Se já é uma string válida, retornar
        if isinstance(data, str) and len(data.strip()) > 10:
            # Evitar retornar strings que são claramente não-respostas
            if not any(skip in data for skip in ['task_id', 'success', 'error', 'timestamp']):
                return data
        
        # Se é um dicionário, procurar em campos conhecidos
        if isinstance(data, dict):
            # Campos prioritários para resposta
            priority_fields = ['response', 'result', 'answer', 'message', 'text', 'content']
            
            for field in priority_fields:
                if field in data and data[field]:
                    # Recursão para extrair do campo
                    extracted = self._extract_response_from_nested(data[field], depth + 1)
                    if extracted:
                        return extracted
            
            # Se não encontrou nos campos prioritários, tentar todos os campos
            for key, value in data.items():
                if value and key not in ['task_id', 'success', 'error', 'timestamp', 'mode', 'orchestrator']:
                    extracted = self._extract_response_from_nested(value, depth + 1)
                    if extracted:
                        return extracted
        
        # Se é uma lista, verificar cada item
        elif isinstance(data, list) and data:
            for item in data:
                extracted = self._extract_response_from_nested(item, depth + 1)
                if extracted:
                    return extracted
        
        return None
    
    def _classify_query_type(self, consulta: str) -> str:
        """Classifica o tipo da query para métricas"""
        consulta_lower = consulta.lower()
        
        if any(word in consulta_lower for word in ['entrega', 'entregar', 'delivery']):
            return 'status_entregas'
        elif any(word in consulta_lower for word in ['frete', 'transporte', 'cotação']):
            return 'consulta_fretes'
        elif any(word in consulta_lower for word in ['pedido', 'order']):
            return 'consulta_pedidos'
        elif any(word in consulta_lower for word in ['embarque', 'embarcar']):
            return 'consulta_embarques'
        elif any(word in consulta_lower for word in ['financeiro', 'pagar', 'pagamento']):
            return 'consulta_financeiro'
        elif any(word in consulta_lower for word in ['relatório', 'report', 'análise']):
            return 'gerar_relatorio'
        elif any(word in consulta_lower for word in ['status', 'como está']):
            return 'status_sistema'
        else:
            return 'consulta_geral'
    
    def _estimate_tokens(self, text: str) -> int:
        """Estima o número de tokens baseado no texto"""
        # Estimativa aproximada: 1 token ≈ 4 caracteres
        return len(text) // 4
    
    @property
    def sistema_ativo(self) -> str:
        """Retorna o sistema ativo"""
        return "novo" if self._use_new_system else "antigo"

# Instância global do gerenciador
_transition_manager = None

def get_transition_manager() -> ClaudeTransitionManager:
    """Obtém instância do gerenciador de transição"""
    global _transition_manager
    if _transition_manager is None:
        _transition_manager = ClaudeTransitionManager()
    return _transition_manager

def processar_consulta_transicao(consulta: str, user_context: Optional[Dict] = None) -> str:
    """Função principal para processar consultas com transição"""
    
    try:
        # Obter gerenciador
        manager = get_transition_manager()
        
        # Processar consulta de forma assíncrona
        try:
            # Verificar se há loop rodando
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Se já há um loop rodando, usar run_in_executor
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        manager.processar_consulta(consulta, user_context)
                    )
                    return future.result(timeout=30)  # 30 segundos timeout
            else:
                # Se não há loop, usar run_until_complete
                return loop.run_until_complete(
                    manager.processar_consulta(consulta, user_context)
                )
        except RuntimeError:
            # Se não há loop, criar um novo
            return asyncio.run(manager.processar_consulta(consulta, user_context))
            
    except Exception as e:
        logger.error(f"❌ Erro na transição: {e}")
        return f"Erro no processamento: {str(e)}"
