"""
Sistema de tratamento de erros e fallback
"""

import logging
import traceback
from typing import Dict, Optional, List, Any, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Níveis de severidade de erro"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Categorias de erro"""
    NLP_PROCESSING = "nlp_processing"
    ENTITY_RESOLUTION = "entity_resolution"
    INTENT_CLASSIFICATION = "intent_classification"
    DATABASE_QUERY = "database_query"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"

@dataclass
class MCPError:
    """Representação de um erro no sistema MCP"""
    code: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    details: Optional[Dict] = None
    timestamp: datetime = None
    traceback: Optional[str] = None
    user_context: Optional[Dict] = None
    recovery_suggestions: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
            
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return {
            'code': self.code,
            'message': self.message,
            'category': self.category.value,
            'severity': self.severity.value,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'traceback': self.traceback,
            'recovery_suggestions': self.recovery_suggestions
        }

class ErrorHandler:
    """Gerenciador de erros com fallback e recuperação"""
    
    def __init__(self, notification_service=None):
        self.notification_service = notification_service
        self.error_log = []
        self.fallback_strategies = {}
        self.recovery_handlers = {}
        self.error_patterns = []
        self._initialize_default_strategies()
        
    def _initialize_default_strategies(self):
        """Inicializa estratégias de fallback padrão"""
        self.fallback_strategies = {
            ErrorCategory.NLP_PROCESSING: self._nlp_fallback,
            ErrorCategory.ENTITY_RESOLUTION: self._entity_fallback,
            ErrorCategory.INTENT_CLASSIFICATION: self._intent_fallback,
            ErrorCategory.DATABASE_QUERY: self._database_fallback,
            ErrorCategory.VALIDATION: self._validation_fallback,
            ErrorCategory.EXTERNAL_SERVICE: self._external_service_fallback
        }
        
    def handle_error(self, 
                    exception: Exception,
                    category: ErrorCategory,
                    context: Optional[Dict] = None,
                    user_id: Optional[str] = None) -> MCPError:
        """Trata um erro e aplica estratégia de fallback"""
        
        # Cria objeto de erro
        error = self._create_error_object(exception, category, context, user_id)
        
        # Log do erro
        self._log_error(error)
        
        # Detecta padrões de erro
        self._analyze_error_pattern(error)
        
        # Aplica estratégia de fallback
        fallback_result = self._apply_fallback(error)
        if fallback_result:
            error.recovery_suggestions = fallback_result.get('suggestions', [])
            
        # Notifica se crítico
        if error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self._notify_critical_error(error)
            
        return error
        
    def _create_error_object(self, 
                           exception: Exception,
                           category: ErrorCategory,
                           context: Optional[Dict],
                           user_id: Optional[str]) -> MCPError:
        """Cria objeto de erro estruturado"""
        
        # Determina código e severidade baseado no tipo de exceção
        code, severity = self._classify_exception(exception, category)
        
        # Captura traceback se disponível
        tb = None
        if hasattr(exception, '__traceback__'):
            tb = ''.join(traceback.format_tb(exception.__traceback__))
            
        error = MCPError(
            code=code,
            message=str(exception),
            category=category,
            severity=severity,
            details=context,
            traceback=tb,
            user_context={'user_id': user_id} if user_id else None
        )
        
        return error
        
    def _classify_exception(self, exception: Exception, category: ErrorCategory) -> tuple[str, ErrorSeverity]:
        """Classifica exceção para determinar código e severidade"""
        
        # Mapeia tipos de exceção para códigos e severidade
        exception_map = {
            ValueError: ("INVALID_VALUE", ErrorSeverity.MEDIUM),
            KeyError: ("MISSING_KEY", ErrorSeverity.MEDIUM),
            AttributeError: ("MISSING_ATTRIBUTE", ErrorSeverity.MEDIUM),
            TypeError: ("TYPE_ERROR", ErrorSeverity.MEDIUM),
            ConnectionError: ("CONNECTION_ERROR", ErrorSeverity.HIGH),
            TimeoutError: ("TIMEOUT_ERROR", ErrorSeverity.HIGH),
            PermissionError: ("PERMISSION_DENIED", ErrorSeverity.HIGH),
            FileNotFoundError: ("FILE_NOT_FOUND", ErrorSeverity.LOW),
            ImportError: ("IMPORT_ERROR", ErrorSeverity.CRITICAL),
            MemoryError: ("MEMORY_ERROR", ErrorSeverity.CRITICAL),
            SystemError: ("SYSTEM_ERROR", ErrorSeverity.CRITICAL)
        }
        
        # Verifica tipo específico
        for exc_type, (code, severity) in exception_map.items():
            if isinstance(exception, exc_type):
                return code, severity
                
        # Default baseado na categoria
        category_defaults = {
            ErrorCategory.NLP_PROCESSING: ("NLP_ERROR", ErrorSeverity.MEDIUM),
            ErrorCategory.ENTITY_RESOLUTION: ("ENTITY_ERROR", ErrorSeverity.MEDIUM),
            ErrorCategory.DATABASE_QUERY: ("DB_ERROR", ErrorSeverity.HIGH),
            ErrorCategory.AUTHENTICATION: ("AUTH_ERROR", ErrorSeverity.HIGH),
            ErrorCategory.SYSTEM: ("SYSTEM_ERROR", ErrorSeverity.CRITICAL)
        }
        
        default = category_defaults.get(category, ("UNKNOWN_ERROR", ErrorSeverity.MEDIUM))
        return default
        
    def _apply_fallback(self, error: MCPError) -> Optional[Dict]:
        """Aplica estratégia de fallback baseada na categoria"""
        strategy = self.fallback_strategies.get(error.category)
        
        if strategy:
            try:
                return strategy(error)
            except Exception as e:
                logger.error(f"Erro ao aplicar fallback: {e}")
                
        return None
        
    def _nlp_fallback(self, error: MCPError) -> Dict:
        """Fallback para erros de processamento NLP"""
        suggestions = []
        
        if "encoding" in error.message.lower():
            suggestions.append("Tente reformular a consulta sem caracteres especiais")
        elif "timeout" in error.message.lower():
            suggestions.append("Consulta muito complexa. Tente simplificar")
        else:
            suggestions.append("Tente reformular sua consulta de forma mais clara")
            suggestions.append("Use termos mais específicos")
            
        # Sugere consultas alternativas baseadas no contexto
        if error.details and error.details.get('original_query'):
            query = error.details['original_query']
            if len(query) > 100:
                suggestions.append("Consulta muito longa. Tente dividir em partes menores")
                
        return {
            'fallback_action': 'suggest_reformulation',
            'suggestions': suggestions
        }
        
    def _entity_fallback(self, error: MCPError) -> Dict:
        """Fallback para erros de resolução de entidade"""
        suggestions = []
        
        if error.details and error.details.get('entity_reference'):
            ref = error.details['entity_reference']
            suggestions.append(f"Não foi possível identificar '{ref}'")
            suggestions.append("Tente usar o nome completo ou CNPJ")
            suggestions.append("Verifique a ortografia")
            
            # Sugere entidades similares se disponível
            if error.details.get('similar_entities'):
                similar = error.details['similar_entities'][:3]
                suggestions.append(f"Você quis dizer: {', '.join(similar)}?")
                
        return {
            'fallback_action': 'suggest_alternatives',
            'suggestions': suggestions
        }
        
    def _intent_fallback(self, error: MCPError) -> Dict:
        """Fallback para erros de classificação de intenção"""
        suggestions = [
            "Não consegui entender o que você deseja fazer",
            "Tente usar palavras-chave como: buscar, listar, contar, status",
            "Exemplos de consultas válidas:",
            "- Quantas entregas estão atrasadas?",
            "- Buscar pedidos do cliente X",
            "- Status da NF 12345"
        ]
        
        return {
            'fallback_action': 'show_examples',
            'suggestions': suggestions
        }
        
    def _database_fallback(self, error: MCPError) -> Dict:
        """Fallback para erros de banco de dados"""
        suggestions = []
        
        if "connection" in error.message.lower():
            suggestions.append("Problema de conexão com o banco de dados")
            suggestions.append("Tente novamente em alguns instantes")
        elif "timeout" in error.message.lower():
            suggestions.append("Consulta demorou muito para executar")
            suggestions.append("Tente filtrar por um período menor")
        else:
            suggestions.append("Erro ao acessar dados")
            suggestions.append("Tente uma consulta mais simples")
            
        return {
            'fallback_action': 'retry_simplified',
            'suggestions': suggestions
        }
        
    def _validation_fallback(self, error: MCPError) -> Dict:
        """Fallback para erros de validação"""
        suggestions = []
        
        if error.details and error.details.get('missing_fields'):
            fields = error.details['missing_fields']
            suggestions.append(f"Informações necessárias: {', '.join(fields)}")
            
        if error.details and error.details.get('invalid_format'):
            field = error.details['invalid_format']
            suggestions.append(f"Formato inválido para {field}")
            suggestions.append("Use o formato correto (ex: DD/MM/AAAA para datas)")
            
        return {
            'fallback_action': 'request_missing_info',
            'suggestions': suggestions
        }
        
    def _external_service_fallback(self, error: MCPError) -> Dict:
        """Fallback para erros de serviços externos"""
        return {
            'fallback_action': 'use_cached_data',
            'suggestions': [
                "Serviço temporariamente indisponível",
                "Usando dados em cache",
                "Algumas informações podem estar desatualizadas"
            ]
        }
        
    def register_recovery_handler(self, 
                                error_code: str,
                                handler: Callable[[MCPError], bool]):
        """Registra handler de recuperação para código de erro específico"""
        self.recovery_handlers[error_code] = handler
        
    def add_error_pattern(self, 
                         pattern: Dict[str, Any],
                         action: Callable[[List[MCPError]], None]):
        """Adiciona padrão de erro para detecção"""
        self.error_patterns.append({
            'pattern': pattern,
            'action': action
        })
        
    def _analyze_error_pattern(self, error: MCPError):
        """Analisa padrões de erro para detecção de problemas sistêmicos"""
        # Adiciona à lista de erros recentes
        self.error_log.append(error)
        
        # Mantém apenas últimos 1000 erros
        if len(self.error_log) > 1000:
            self.error_log = self.error_log[-1000:]
            
        # Verifica padrões
        for pattern_config in self.error_patterns:
            pattern = pattern_config['pattern']
            action = pattern_config['action']
            
            # Conta erros que correspondem ao padrão
            matching_errors = []
            for logged_error in self.error_log[-100:]:  # Últimos 100 erros
                if self._matches_pattern(logged_error, pattern):
                    matching_errors.append(logged_error)
                    
            # Se excede threshold, executa ação
            threshold = pattern.get('threshold', 5)
            if len(matching_errors) >= threshold:
                action(matching_errors)
                
    def _matches_pattern(self, error: MCPError, pattern: Dict) -> bool:
        """Verifica se erro corresponde a um padrão"""
        if 'category' in pattern and error.category != pattern['category']:
            return False
            
        if 'severity' in pattern and error.severity != pattern['severity']:
            return False
            
        if 'code' in pattern and error.code != pattern['code']:
            return False
            
        if 'message_contains' in pattern:
            if pattern['message_contains'] not in error.message:
                return False
                
        return True
        
    def _log_error(self, error: MCPError):
        """Registra erro no log"""
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        
        level = log_level.get(error.severity, logging.ERROR)
        
        logger.log(
            level,
            f"MCP Error [{error.code}] - {error.category.value}: {error.message}",
            extra={
                'error_code': error.code,
                'category': error.category.value,
                'severity': error.severity.value,
                'details': error.details
            }
        )
        
    def _notify_critical_error(self, error: MCPError):
        """Notifica sobre erros críticos"""
        if self.notification_service:
            try:
                self.notification_service.notify_admin(
                    subject=f"Erro Crítico MCP: {error.code}",
                    message=f"{error.message}\n\nCategoria: {error.category.value}\nDetalhes: {json.dumps(error.details)}",
                    priority="high"
                )
            except Exception as e:
                logger.error(f"Erro ao notificar: {e}")
                
    def get_error_statistics(self, 
                           category: Optional[ErrorCategory] = None,
                           severity: Optional[ErrorSeverity] = None,
                           hours: int = 24) -> Dict:
        """Obtém estatísticas de erros"""
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        
        filtered_errors = []
        for error in self.error_log:
            if error.timestamp.timestamp() < cutoff_time:
                continue
                
            if category and error.category != category:
                continue
                
            if severity and error.severity != severity:
                continue
                
            filtered_errors.append(error)
            
        # Calcula estatísticas
        stats = {
            'total_errors': len(filtered_errors),
            'by_category': {},
            'by_severity': {},
            'by_code': {},
            'most_common': []
        }
        
        # Conta por categoria
        for error in filtered_errors:
            cat = error.category.value
            stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
            
            sev = error.severity.value
            stats['by_severity'][sev] = stats['by_severity'].get(sev, 0) + 1
            
            code = error.code
            stats['by_code'][code] = stats['by_code'].get(code, 0) + 1
            
        # Top 5 erros mais comuns
        if stats['by_code']:
            sorted_codes = sorted(stats['by_code'].items(), key=lambda x: x[1], reverse=True)
            stats['most_common'] = sorted_codes[:5]
            
        return stats
        
    def create_error_report(self, 
                          start_date: datetime,
                          end_date: datetime) -> Dict:
        """Cria relatório de erros para período"""
        report_errors = []
        
        for error in self.error_log:
            if start_date <= error.timestamp <= end_date:
                report_errors.append(error)
                
        report = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'summary': {
                'total_errors': len(report_errors),
                'critical_errors': sum(1 for e in report_errors if e.severity == ErrorSeverity.CRITICAL),
                'high_errors': sum(1 for e in report_errors if e.severity == ErrorSeverity.HIGH)
            },
            'details': [e.to_dict() for e in report_errors[-100:]]  # Últimos 100
        }
        
        return report