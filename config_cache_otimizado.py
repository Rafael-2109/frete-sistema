#!/usr/bin/env python3
"""
⚡ CONFIGURAÇÃO DE CACHE OTIMIZADA
Configurações específicas para performance e cache
"""

import os
from datetime import timedelta

class CacheConfig:
    """Configurações otimizadas de cache para produção"""
    
    # ==========================================
    # 🔄 REDIS CACHE CONFIGURATION
    # ==========================================
    
    # Configurações de TTL otimizadas por tipo de dados
    CACHE_TTL = {
        # Dados em tempo real (30 segundos)
        'dashboard_metrics': 30,
        'system_status': 30,
        'active_shipments': 30,
        
        # Dados operacionais (5 minutos)
        'user_context': 300,
        'intelligent_suggestions': 300,
        'ai_insights': 300,
        
        # Dados analíticos (15 minutos)
        'query_results': 900,
        'excel_data': 900,
        'report_data': 900,
        
        # Dados estáticos (1 hora)
        'transportadoras': 3600,
        'clientes': 3600,
        'tabelas_frete': 3600,
        
        # Machine Learning (6 horas)
        'ml_predictions': 21600,
        'ml_models': 21600,
        'anomaly_detection': 21600
    }
    
    # Configurações de conexão Redis
    REDIS_CONFIG = {
        'socket_timeout': 5,
        'socket_connect_timeout': 5,
        'retry_on_timeout': True,
        'health_check_interval': 30,
        'max_connections': 50,
        'decode_responses': True,
        'skip_full_coverage_check': True
    }
    
    # ==========================================
    # 📊 CACHE STRATEGIES
    # ==========================================
    
    # Estratégias de cache por funcionalidade
    CACHE_STRATEGIES = {
        'claude_ai': {
            'strategy': 'write_through',  # Sempre atualizar cache
            'ttl': CACHE_TTL['ai_insights'],
            'max_size': 1000  # Máximo de 1000 conversas
        },
        'dashboard': {
            'strategy': 'refresh_ahead',  # Atualizar antes de expirar
            'ttl': CACHE_TTL['dashboard_metrics'],
            'refresh_threshold': 0.8  # Refresh quando 80% do TTL
        },
        'reports': {
            'strategy': 'lazy_loading',  # Carregar apenas quando necessário
            'ttl': CACHE_TTL['report_data'],
            'background_refresh': True
        },
        'ml_models': {
            'strategy': 'cache_aside',  # Cache manual
            'ttl': CACHE_TTL['ml_models'],
            'persistent': True  # Manter mesmo após restart
        }
    }
    
    # ==========================================
    # 🔧 PERFORMANCE TUNING
    # ==========================================
    
    # Configurações de performance
    PERFORMANCE_CONFIG = {
        # Batching para operações em lote
        'batch_size': 100,
        'max_batch_wait_time': 1.0,  # 1 segundo
        
        # Compressão de dados
        'compression': 'gzip',
        'compression_threshold': 1024,  # Comprimir > 1KB
        
        # Pipelines Redis
        'use_pipeline': True,
        'pipeline_size': 50,
        
        # Async operations
        'async_enabled': True,
        'worker_pool_size': 4
    }
    
    # ==========================================
    # 📈 MONITORING & METRICS
    # ==========================================
    
    # Métricas de cache
    METRICS_CONFIG = {
        'track_hit_rate': True,
        'track_memory_usage': True,
        'track_response_time': True,
        'alert_thresholds': {
            'hit_rate_min': 0.85,  # 85% hit rate mínimo
            'memory_usage_max': 0.90,  # 90% memória máximo
            'response_time_max': 100  # 100ms máximo
        }
    }
    
    # Logs de cache
    LOGGING_CONFIG = {
        'log_cache_misses': True,
        'log_slow_operations': True,
        'log_memory_warnings': True,
        'slow_operation_threshold': 50  # 50ms
    }
    
    @classmethod
    def get_redis_url(cls) -> str:
        """Retorna URL do Redis com configurações otimizadas"""
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        
        # Adicionar parâmetros de performance
        if '?' not in redis_url:
            redis_url += '?'
        else:
            redis_url += '&'
            
        params = [
            'socket_timeout=5',
            'socket_connect_timeout=5',
            'retry_on_timeout=true',
            'health_check_interval=30'
        ]
        
        return redis_url + '&'.join(params)
    
    @classmethod
    def get_cache_key(cls, prefix: str, *args) -> str:
        """Gera chave de cache padronizada"""
        key_parts = [prefix] + [str(arg) for arg in args]
        return ':'.join(key_parts)
    
    @classmethod
    def should_cache(cls, data_type: str, data_size: int) -> bool:
        """Determina se dados devem ser cacheados"""
        # Não cachear dados muito grandes
        if data_size > 10 * 1024 * 1024:  # 10MB
            return False
        
        # Não cachear dados com TTL muito baixo
        ttl = cls.CACHE_TTL.get(data_type, 300)
        if ttl < 30:  # Menos de 30 segundos
            return False
            
        return True

# Instância global
cache_config = CacheConfig() 