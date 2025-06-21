#!/usr/bin/env python3
"""
⚡ SISTEMA DE CACHE REDIS INTELIGENTE - MCP v4.0
Cache otimizado para IA, ML e real-time data
"""

import redis
import json
import pickle
import logging
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import time

# Importar configurações de IA
try:
    from config_ai import ai_config
except ImportError:
    # Fallback para desenvolvimento
    class MockConfig:
        @staticmethod
        def get_redis_config():
            return {'host': 'localhost', 'port': 6379, 'db': 0}
        @staticmethod
        def get_ml_redis_config():
            return {'host': 'localhost', 'port': 6379, 'db': 1}
        CACHE_TIMEOUTS = {
            'real_time_metrics': 30,
            'ai_insights': 300,
            'ml_predictions': 1800,
            'user_context': 3600,
            'dashboard_data': 60,
            'system_status': 120,
            'alerts_cache': 15,
            'query_results': 600
        }
    ai_config = MockConfig()

logger = logging.getLogger(__name__)

class IntelligentRedisCache:
    """Sistema de cache Redis inteligente para MCP v4.0"""
    
    def __init__(self):
        """Inicializa o sistema de cache"""
        self.primary_redis = None
        self.ml_redis = None
        self.connected = False
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'errors': 0,
            'last_connection_attempt': None
        }
        self._connect()
    
    def _connect(self):
        """Conecta aos servidores Redis"""
        try:
            # Redis principal
            primary_config = ai_config.get_redis_config()
            self.primary_redis = redis.Redis(**primary_config)
            
            # Redis para ML
            ml_config = ai_config.get_ml_redis_config()
            self.ml_redis = redis.Redis(**ml_config)
            
            # Testar conexões
            self.primary_redis.ping()
            self.ml_redis.ping()
            
            self.connected = True
            self.stats['last_connection_attempt'] = datetime.now()
            logger.info("✅ Conectado ao Redis com sucesso")
            
        except Exception as e:
            self.connected = False
            self.stats['errors'] += 1
            self.stats['last_connection_attempt'] = datetime.now()
            logger.error(f"❌ Erro ao conectar ao Redis: {e}")
            
            # Usar cache em memória como fallback
            self._setup_memory_fallback()
    
    def _setup_memory_fallback(self):
        """Configura cache em memória como fallback"""
        self.memory_cache = {}
        logger.warning("⚠️ Usando cache em memória como fallback")
    
    def _get_cache_key(self, key: str, prefix: str = "mcp_v4") -> str:
        """Gera chave de cache padronizada"""
        return f"{prefix}:{key}"
    
    def _serialize_data(self, data: Any, use_pickle: bool = False) -> Union[str, bytes]:
        """Serializa dados para cache"""
        try:
            if use_pickle:
                return pickle.dumps(data)
            else:
                return json.dumps(data, default=str, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao serializar dados: {e}")
            return json.dumps({"error": "serialization_failed"})
    
    def _deserialize_data(self, data: Union[str, bytes], use_pickle: bool = False) -> Any:
        """Deserializa dados do cache"""
        try:
            if use_pickle:
                return pickle.loads(data)
            else:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Erro ao deserializar dados: {e}")
            return None
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None, 
            category: str = "default", use_ml_redis: bool = False, 
            use_pickle: bool = False) -> bool:
        """
        Define valor no cache com timeout inteligente
        
        Args:
            key: Chave do cache
            value: Valor a ser armazenado
            timeout: Timeout em segundos (None = usar padrão da categoria)
            category: Categoria do cache para timeout automático
            use_ml_redis: Usar Redis de ML
            use_pickle: Usar pickle ao invés de JSON
        """
        try:
            cache_key = self._get_cache_key(key)
            
            # Determinar timeout
            if timeout is None:
                timeout = ai_config.CACHE_TIMEOUTS.get(category, 300)
            
            # Serializar dados
            serialized_data = self._serialize_data(value, use_pickle)
            
            # Escolher Redis apropriado
            redis_client = self.ml_redis if use_ml_redis else self.primary_redis
            
            if self.connected and redis_client:
                # Redis disponível
                result = redis_client.setex(cache_key, timeout, serialized_data)
                
                # Adicionar metadados
                metadata = {
                    'created_at': datetime.now().isoformat(),
                    'category': category,
                    'timeout': timeout,
                    'use_pickle': use_pickle
                }
                redis_client.setex(f"{cache_key}:meta", timeout, json.dumps(metadata))
                
                self.stats['sets'] += 1
                return result
                
            else:
                # Fallback para memória
                self.memory_cache[cache_key] = {
                    'data': value,
                    'expires_at': datetime.now() + timedelta(seconds=timeout),
                    'category': category
                }
                self.stats['sets'] += 1
                return True
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Erro ao definir cache {key}: {e}")
            return False
    
    def get(self, key: str, use_ml_redis: bool = False, 
            use_pickle: bool = False) -> Optional[Any]:
        """
        Obtém valor do cache
        
        Args:
            key: Chave do cache
            use_ml_redis: Usar Redis de ML
            use_pickle: Usar pickle para deserializar
        """
        try:
            cache_key = self._get_cache_key(key)
            
            # Escolher Redis apropriado
            redis_client = self.ml_redis if use_ml_redis else self.primary_redis
            
            if self.connected and redis_client:
                # Redis disponível
                data = redis_client.get(cache_key)
                
                if data is not None:
                    self.stats['hits'] += 1
                    return self._deserialize_data(data, use_pickle)
                else:
                    self.stats['misses'] += 1
                    return None
                    
            else:
                # Fallback para memória
                cached_item = self.memory_cache.get(cache_key)
                
                if cached_item and cached_item['expires_at'] > datetime.now():
                    self.stats['hits'] += 1
                    return cached_item['data']
                else:
                    self.stats['misses'] += 1
                    # Remover item expirado
                    if cached_item:
                        del self.memory_cache[cache_key]
                    return None
                    
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Erro ao obter cache {key}: {e}")
            return None
    
    def delete(self, key: str, use_ml_redis: bool = False) -> bool:
        """Remove item do cache"""
        try:
            cache_key = self._get_cache_key(key)
            
            # Escolher Redis apropriado
            redis_client = self.ml_redis if use_ml_redis else self.primary_redis
            
            if self.connected and redis_client:
                result = redis_client.delete(cache_key)
                redis_client.delete(f"{cache_key}:meta")  # Remover metadados também
                return bool(result)
            else:
                # Fallback para memória
                if cache_key in self.memory_cache:
                    del self.memory_cache[cache_key]
                    return True
                return False
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Erro ao deletar cache {key}: {e}")
            return False
    
    def get_by_pattern(self, pattern: str, use_ml_redis: bool = False) -> List[str]:
        """Obtém chaves que correspondem ao padrão"""
        try:
            redis_client = self.ml_redis if use_ml_redis else self.primary_redis
            
            if self.connected and redis_client:
                cache_pattern = self._get_cache_key(pattern)
                keys = redis_client.keys(cache_pattern)
                return [key.decode() if isinstance(key, bytes) else key for key in keys]
            else:
                # Fallback para memória
                import fnmatch
                cache_pattern = self._get_cache_key(pattern)
                return [key for key in self.memory_cache.keys() 
                       if fnmatch.fnmatch(key, cache_pattern)]
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Erro ao buscar padrão {pattern}: {e}")
            return []
    
    def clear_category(self, category: str) -> int:
        """Remove todos os itens de uma categoria"""
        try:
            pattern = f"*:meta"
            keys_to_delete = []
            
            redis_client = self.primary_redis if self.connected else None
            
            if redis_client:
                # Buscar por metadados da categoria
                meta_keys = redis_client.keys(self._get_cache_key(pattern))
                
                for meta_key in meta_keys:
                    meta_data = redis_client.get(meta_key)
                    if meta_data:
                        try:
                            metadata = json.loads(meta_data)
                            if metadata.get('category') == category:
                                # Adicionar chave de dados correspondente
                                data_key = meta_key.replace(':meta', '')
                                keys_to_delete.extend([data_key, meta_key])
                        except:
                            continue
                
                # Deletar todas as chaves encontradas
                if keys_to_delete:
                    return redis_client.delete(*keys_to_delete)
                    
            else:
                # Fallback para memória
                keys_to_delete = [key for key, value in self.memory_cache.items() 
                                if value.get('category') == category]
                
                for key in keys_to_delete:
                    del self.memory_cache[key]
                
                return len(keys_to_delete)
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Erro ao limpar categoria {category}: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        hit_rate = 0
        if self.stats['hits'] + self.stats['misses'] > 0:
            hit_rate = self.stats['hits'] / (self.stats['hits'] + self.stats['misses'])
        
        return {
            **self.stats,
            'hit_rate': hit_rate,
            'connected': self.connected,
            'memory_cache_size': len(getattr(self, 'memory_cache', {})),
            'redis_info': self._get_redis_info()
        }
    
    def _get_redis_info(self) -> Dict[str, Any]:
        """Obtém informações do Redis"""
        if not self.connected:
            return {'status': 'disconnected'}
        
        try:
            info = self.primary_redis.info()
            return {
                'status': 'connected',
                'redis_version': info.get('redis_version'),
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'uptime_in_seconds': info.get('uptime_in_seconds')
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def health_check(self) -> bool:
        """Verifica saúde da conexão Redis"""
        try:
            if self.connected:
                self.primary_redis.ping()
                self.ml_redis.ping()
                return True
            return False
        except Exception as e:
            logger.error(f"Health check falhou: {e}")
            self.connected = False
            return False

# Decorador para cache automático
def cache_result(timeout: int = 300, category: str = "default", 
                use_ml_redis: bool = False, use_pickle: bool = False):
    """
    Decorador para cache automático de resultados de funções
    
    Args:
        timeout: Timeout em segundos
        category: Categoria do cache
        use_ml_redis: Usar Redis de ML
        use_pickle: Usar pickle para serialização
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gerar chave única baseada na função e parâmetros
            func_signature = f"{func.__module__}.{func.__name__}"
            params_hash = hashlib.md5(
                str(args).encode() + str(sorted(kwargs.items())).encode()
            ).hexdigest()
            cache_key = f"func_cache:{func_signature}:{params_hash}"
            
            # Tentar obter do cache
            cached_result = intelligent_cache.get(
                cache_key, use_ml_redis=use_ml_redis, use_pickle=use_pickle
            )
            
            if cached_result is not None:
                return cached_result
            
            # Executar função e cachear resultado
            result = func(*args, **kwargs)
            intelligent_cache.set(
                cache_key, result, timeout=timeout, category=category,
                use_ml_redis=use_ml_redis, use_pickle=use_pickle
            )
            
            return result
        return wrapper
    return decorator

# Instância global do cache
intelligent_cache = IntelligentRedisCache()

# Funções de conveniência
def cache_set(key: str, value: Any, timeout: Optional[int] = None, 
              category: str = "default") -> bool:
    """Função de conveniência para set"""
    return intelligent_cache.set(key, value, timeout, category)

def cache_get(key: str) -> Optional[Any]:
    """Função de conveniência para get"""
    return intelligent_cache.get(key)

def cache_delete(key: str) -> bool:
    """Função de conveniência para delete"""
    return intelligent_cache.delete(key)

def cache_clear_category(category: str) -> int:
    """Função de conveniência para limpar categoria"""
    return intelligent_cache.clear_category(category)

def cache_stats() -> Dict[str, Any]:
    """Função de conveniência para estatísticas"""
    return intelligent_cache.get_stats()

# Inicialização e testes básicos
if __name__ == "__main__":
    # Teste básico do sistema de cache
    print("🧪 Testando sistema de cache Redis...")
    
    # Teste de conexão
    health = intelligent_cache.health_check()
    print(f"Health check: {'✅' if health else '❌'}")
    
    # Teste de operações básicas
    test_key = "test_mcp_v4"
    test_data = {"message": "MCP v4.0 Cache Test", "timestamp": datetime.now().isoformat()}
    
    # Set
    set_result = cache_set(test_key, test_data, timeout=60, category="testing")
    print(f"Cache set: {'✅' if set_result else '❌'}")
    
    # Get
    cached_data = cache_get(test_key)
    print(f"Cache get: {'✅' if cached_data else '❌'}")
    if cached_data:
        print(f"Data: {cached_data}")
    
    # Stats
    stats = cache_stats()
    print(f"Cache stats: {stats}")
    
    # Cleanup
    cache_delete(test_key)
    print("✅ Teste concluído") 