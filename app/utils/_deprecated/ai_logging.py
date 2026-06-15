#!/usr/bin/env python3
"""
📊 SISTEMA DE LOGGING AVANÇADO - MCP v4.0
Logging estruturado para IA, ML e monitoramento inteligente
"""

import logging
import structlog
import colorlog
import json
import os
import sys
from datetime import datetime
from app.utils.timezone import agora_utc_naive
from typing import Any, Dict, Optional, Union
from functools import wraps
import traceback
import time
from pathlib import Path

# Configurar estrutura de logs
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

class AILogger:
    """Sistema de logging avançado para MCP v4.0"""
    
    def __init__(self):
        """Inicializa o sistema de logging"""
        self.setup_structured_logging()
        self.setup_file_logging()
        self.setup_console_logging()
        
        # Métricas de logging
        self.metrics = {
            'total_logs': 0,
            'errors': 0,
            'warnings': 0,
            'ml_operations': 0,
            'cache_operations': 0,
            'api_calls': 0,
            'start_time': agora_utc_naive()
        }
        
        # Logger principal
        self.logger = structlog.get_logger("mcp_v4")
        self.logger.info("🚀 Sistema de logging MCP v4.0 inicializado")
    
    def setup_structured_logging(self):
        """Configura logging estruturado com structlog"""
        
        def add_timestamp(logger, method_name, event_dict):
            """Adiciona timestamp aos logs"""
            event_dict["timestamp"] = agora_utc_naive().isoformat()
            return event_dict
        
        def add_level_name(logger, method_name, event_dict):
            """Adiciona nome do nível de log"""
            event_dict["level"] = method_name.upper()
            return event_dict
        
        def add_context(logger, method_name, event_dict):
            """Adiciona contexto adicional"""
            event_dict["component"] = "mcp_v4"
            event_dict["version"] = "4.0"
            return event_dict
        
        # Configurar processadores
        processors = [
            add_timestamp,
            add_level_name,
            add_context,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
        ]
        
        # Adicionar formatação JSON para arquivos
        if os.environ.get('LOG_FORMAT') == 'json':
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer(colors=True))
        
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    def setup_file_logging(self):
        """Configura logging para arquivos"""
        
        # Diferentes níveis de log em arquivos separados
        log_files = {
            'all': LOG_DIR / 'mcp_v4_all.log',
            'errors': LOG_DIR / 'mcp_v4_errors.log',
            'ml': LOG_DIR / 'mcp_v4_ml.log',
            'api': LOG_DIR / 'mcp_v4_api.log',
            'cache': LOG_DIR / 'mcp_v4_cache.log',
            'performance': LOG_DIR / 'mcp_v4_performance.log'
        }
        
        # Formatter JSON para arquivos
        json_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        )
        
        # Configurar handlers para cada arquivo
        for log_type, log_file in log_files.items():
            handler = logging.FileHandler(log_file)
            handler.setFormatter(json_formatter)
            
            # Configurar níveis específicos
            if log_type == 'errors':
                handler.setLevel(logging.ERROR)
            else:
                handler.setLevel(logging.INFO)
            
            # Adicionar ao logger principal
            logging.getLogger(f"mcp_v4_{log_type}").addHandler(handler)
    
    def setup_console_logging(self):
        """Configura logging colorido para console"""
        
        # Formatter colorido para desenvolvimento
        color_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt='%H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        
        # Handler para console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(color_formatter)
        console_handler.setLevel(logging.INFO)
        
        # Adicionar ao root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(console_handler)
        root_logger.setLevel(logging.INFO)
    
    def log_ml_operation(self, operation: str, model_name: str, 
                        duration: float, success: bool, **kwargs):
        """Log específico para operações de ML"""
        self.metrics['ml_operations'] += 1
        
        log_data = {
            'operation_type': 'ml_operation',
            'operation': operation,
            'model_name': model_name,
            'duration_seconds': duration,
            'success': success,
            **kwargs
        }
        
        logger = structlog.get_logger("mcp_v4_ml")
        
        if success:
            logger.info("ML operation completed", **log_data)
        else:
            logger.error("ML operation failed", **log_data)
            self.metrics['errors'] += 1
        
        self.metrics['total_logs'] += 1
    
    def log_cache_operation(self, operation: str, key: str, hit: Optional[bool] = None, 
                           category: Optional[str] = None, **kwargs):
        """Log específico para operações de cache"""
        self.metrics['cache_operations'] += 1
        
        log_data = {
            'operation_type': 'cache_operation',
            'operation': operation,
            'cache_key': key,
            'category': category,
            **kwargs
        }
        
        if hit is not None:
            log_data['cache_hit'] = hit
        
        logger = structlog.get_logger("mcp_v4_cache")
        logger.info("Cache operation", **log_data)
        
        self.metrics['total_logs'] += 1
    
    def log_api_call(self, endpoint: str, method: str, duration: float, 
                    status_code: int, user_id: Optional[str] = None, **kwargs):
        """Log específico para chamadas de API"""
        self.metrics['api_calls'] += 1
        
        log_data = {
            'operation_type': 'api_call',
            'endpoint': endpoint,
            'method': method,
            'duration_seconds': duration,
            'status_code': status_code,
            'user_id': user_id,
            **kwargs
        }
        
        logger = structlog.get_logger("mcp_v4_api")
        
        if 200 <= status_code < 400:
            logger.info("API call successful", **log_data)
        else:
            logger.warning("API call failed", **log_data)
            if status_code >= 500:
                self.metrics['errors'] += 1
        
        self.metrics['total_logs'] += 1
    
    def log_performance(self, component: str, operation: str, duration: float, 
                       memory_usage: Optional[float] = None, cpu_usage: Optional[float] = None, **kwargs):
        """Log específico para métricas de performance"""
        
        log_data = {
            'operation_type': 'performance',
            'component': component,
            'operation': operation,
            'duration_seconds': duration,
            **kwargs
        }
        
        if memory_usage is not None:
            log_data['memory_usage_mb'] = memory_usage
        
        if cpu_usage is not None:
            log_data['cpu_usage_percent'] = cpu_usage
        
        logger = structlog.get_logger("mcp_v4_performance")
        
        # Alertar sobre performance ruim
        if duration > 5.0:  # Mais de 5 segundos
            logger.warning("Slow operation detected", **log_data)
            self.metrics['warnings'] += 1
        elif duration > 2.0:  # Mais de 2 segundos
            logger.info("Operation completed (slow)", **log_data)
        else:
            logger.debug("Operation completed", **log_data)
        
        self.metrics['total_logs'] += 1
    
    def log_ai_insight(self, insight_type: str, confidence: float, 
                      impact: str, description: str, **kwargs):
        """Log específico para insights de IA"""
        
        log_data = {
            'operation_type': 'ai_insight',
            'insight_type': insight_type,
            'confidence': confidence,
            'impact': impact,
            'description': description,
            **kwargs
        }
        
        logger = structlog.get_logger("mcp_v4_ml")
        
        if confidence > 0.8 and impact in ['high', 'critical']:
            logger.info("High confidence AI insight", **log_data)
        else:
            logger.debug("AI insight generated", **log_data)
        
        self.metrics['total_logs'] += 1
    
    def log_user_interaction(self, user_id: str, action: str, query: Optional[str] = None, 
                           response_time: Optional[float] = None, **kwargs):
        """Log específico para interações do usuário"""
        
        log_data = {
            'operation_type': 'user_interaction',
            'user_id': user_id,
            'action': action,
            'query': query,
            'response_time': response_time,
            **kwargs
        }
        
        logger = structlog.get_logger("mcp_v4_api")
        logger.info("User interaction", **log_data)
        
        self.metrics['total_logs'] += 1
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None, 
                 operation: Optional[str] = None):
        """Log estruturado para erros"""
        self.metrics['errors'] += 1
        
        log_data = {
            'operation_type': 'error',
            'error_type': type(error).__name__,
            'error_message': str(error),
            'operation': operation,
            'traceback': traceback.format_exc()
        }
        
        if context:
            log_data.update(context)
        
        logger = structlog.get_logger("mcp_v4_errors")
        logger.error("Error occurred", **log_data)
        
        self.metrics['total_logs'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas de logging"""
        uptime = agora_utc_naive() - self.metrics['start_time']
        
        return {
            **self.metrics,
            'uptime_seconds': uptime.total_seconds(),
            'logs_per_minute': self.metrics['total_logs'] / max(uptime.total_seconds() / 60, 1),
            'error_rate': self.metrics['errors'] / max(self.metrics['total_logs'], 1)
        }
    
    def export_logs(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None, 
                   log_types: Optional[list] = None) -> Dict[str, list]:
        """Exporta logs para análise"""
        
        if log_types is None:
            log_types = ['all', 'errors', 'ml', 'api', 'cache', 'performance']
        
        exported_logs = {}
        
        for log_type in log_types:
            log_file = LOG_DIR / f'mcp_v4_{log_type}.log'
            
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Filtrar por tempo se especificado
                    if start_time or end_time:
                        filtered_lines = []
                        for line in lines:
                            # Implementar filtro de tempo (simplificado)
                            filtered_lines.append(line.strip())
                        exported_logs[log_type] = filtered_lines
                    else:
                        exported_logs[log_type] = [line.strip() for line in lines]
                        
                except Exception as e:
                    exported_logs[log_type] = [f"Error reading log file: {e}"]
            else:
                exported_logs[log_type] = []
        
        return exported_logs

# Decoradores para logging automático
def log_execution_time(operation_name: Optional[str] = None, component: str = "general"):
    """Decorador para log automático de tempo de execução"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            operation = operation_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                ai_logger.log_performance(
                    component=component,
                    operation=operation,
                    duration=duration,
                    success=True
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                ai_logger.log_performance(
                    component=component,
                    operation=operation,
                    duration=duration,
                    success=False
                )
                
                ai_logger.log_error(e, {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs)
                }, operation)
                
                raise
        
        return wrapper
    return decorator

def log_ml_operation(model_name: str, operation_type: str = "prediction"):
    """Decorador para log automático de operações ML"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                ai_logger.log_ml_operation(
                    operation=operation_type,
                    model_name=model_name,
                    duration=duration,
                    success=True,
                    function=func.__name__
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                ai_logger.log_ml_operation(
                    operation=operation_type,
                    model_name=model_name,
                    duration=duration,
                    success=False,
                    error=str(e),
                    function=func.__name__
                )
                
                raise
        
        return wrapper
    return decorator

def log_api_endpoint(endpoint_name: Optional[str] = None):
    """Decorador para log automático de endpoints de API"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            endpoint = endpoint_name or func.__name__
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Extrair status code se estiver no resultado
                status_code = 200
                if hasattr(result, 'status_code'):
                    status_code = result.status_code
                elif isinstance(result, tuple) and len(result) > 1:
                    status_code = result[1]
                
                ai_logger.log_api_call(
                    endpoint=endpoint,
                    method="UNKNOWN",  # Seria melhor extrair do request
                    duration=duration,
                    status_code=status_code
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                ai_logger.log_api_call(
                    endpoint=endpoint,
                    method="UNKNOWN",
                    duration=duration,
                    status_code=500
                )
                
                raise
        
        return wrapper
    return decorator

# Instância global do logger
ai_logger = AILogger()

# Logger principal para compatibilidade
logger = ai_logger.logger

# Funções de conveniência
def log_info(message: str, **kwargs):
    """Log de informação"""
    logger = structlog.get_logger("mcp_v4")
    logger.info(message, **kwargs)
    ai_logger.metrics['total_logs'] += 1

def log_warning(message: str, **kwargs):
    """Log de aviso"""
    logger = structlog.get_logger("mcp_v4")
    logger.warning(message, **kwargs)
    ai_logger.metrics['warnings'] += 1
    ai_logger.metrics['total_logs'] += 1

def log_error(message: str, error: Optional[Exception] = None, **kwargs):
    """Log de erro"""
    logger = structlog.get_logger("mcp_v4")
    
    if error:
        kwargs['error_type'] = type(error).__name__
        kwargs['error_message'] = str(error)
        kwargs['traceback'] = traceback.format_exc()
    
    logger.error(message, **kwargs)
    ai_logger.metrics['errors'] += 1
    ai_logger.metrics['total_logs'] += 1

def log_debug(message: str, **kwargs):
    """Log de debug"""
    logger = structlog.get_logger("mcp_v4")
    logger.debug(message, **kwargs)
    ai_logger.metrics['total_logs'] += 1

# Teste do sistema
if __name__ == "__main__":
    print("🧪 Testando sistema de logging...")
    
    # Testes básicos
    log_info("Sistema de logging inicializado")
    log_warning("Teste de warning")
    
    # Teste de decoradores
    @log_execution_time("test_function", "testing")
    def test_function():
        time.sleep(0.1)
        return "sucesso"
    
    result = test_function()
    print(f"Resultado da função: {result}")
    
    # Teste de ML logging
    ai_logger.log_ml_operation("test_model", "training", 1.5, True, samples=100)
    
    # Teste de cache logging
    ai_logger.log_cache_operation("get", "test_key", hit=True, category="testing")
    
    # Métricas
    metrics = ai_logger.get_metrics()
    print(f"Métricas: {metrics}")
    
    print("✅ Teste de logging concluído") 