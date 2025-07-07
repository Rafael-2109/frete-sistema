#!/usr/bin/env python3
"""
Sistema de Cache Redis - Sistema de Fretes
Cache inteligente para consultas, estatísticas e dados do Claude AI
"""

import redis
import json
import logging
import hashlib
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import os
from functools import wraps

logger = logging.getLogger(__name__)

class RedisCache:
    """Sistema de Cache Redis para Sistema de Fretes"""
    
    def __init__(self):
        """Inicializa conexão Redis"""
        # Configuração para Render Key Value (Redis compatível)
        self.redis_url = os.getenv('REDIS_URL')  # URL interna do Render
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.redis_password = os.getenv('REDIS_PASSWORD', None)
        
        try:
            # PRIORIDADE 1: URL do Render Key Value (formato: redis://internal-url:6379)
            if self.redis_url:
                logger.info("🔗 Conectando via REDIS_URL (Render Key Value)")
                self.client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=10,
                    socket_timeout=10,
                    retry_on_timeout=True
                )
            # PRIORIDADE 2: Configuração manual (desenvolvimento local)
            else:
                logger.info("🔗 Conectando via host/port (desenvolvimento)")
                self.client = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    password=self.redis_password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            
            # Testar conexão
            self.client.ping()
            self.disponivel = True
            logger.info("🚀 Redis Cache conectado com sucesso!")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis não disponível: {e}")
            logger.info("💡 Para Render: Configure REDIS_URL na aba Environment")
            logger.info("💡 Para local: Instale Redis ou use cache em memória")
            self.client = None
            self.disponivel = False
    
    def _gerar_chave(self, prefixo: str, **kwargs) -> str:
        """Gera chave única para cache baseada nos parâmetros"""
        # Criar string única dos parâmetros
        params_str = json.dumps(kwargs, sort_keys=True, default=str)
        hash_params = hashlib.md5(params_str.encode()).hexdigest()[:12]
        
        return f"{prefixo}:{hash_params}"
    
    def get(self, chave: str) -> Optional[Any]:
        """Busca item no cache"""
        if not self.disponivel:
            return None
        
        try:
            valor = self.client.get(chave)
            if valor:
                # Garantir que valor é string antes do json.loads
                valor_str = str(valor) if valor is not None else None
                if valor_str:
                    return json.loads(valor_str)
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao buscar cache {chave}: {e}")
            return None
    
    def set(self, chave: str, valor: Any, ttl: int = 300) -> bool:
        """Armazena item no cache com TTL (Time To Live)"""
        if not self.disponivel:
            return False
        
        try:
            valor_json = json.dumps(valor, default=str, ensure_ascii=False)
            self.client.setex(chave, ttl, valor_json)
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao salvar cache {chave}: {e}")
            return False
    
    def delete(self, chave: str) -> bool:
        """Remove item do cache"""
        if not self.disponivel:
            return False
        
        try:
            self.client.delete(chave)
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao remover cache {chave}: {e}")
            return False
    
    def flush_pattern(self, pattern: str) -> int:
        """Remove todas as chaves que correspondem ao padrão"""
        if not self.disponivel:
            return 0
        
        try:
            chaves_raw = self.client.keys(f"{pattern}*")
            if chaves_raw:
                # Type cast explícito para resolver tipagem Redis
                from typing import cast
                chaves = cast(List[str], chaves_raw)
                resultado = cast(int, self.client.delete(*chaves))
                return resultado if resultado is not None else 0
            return 0
        except Exception as e:
            logger.error(f"❌ Erro ao limpar cache {pattern}: {e}")
            return 0
    
    # MÉTODOS ESPECÍFICOS PARA O SISTEMA DE FRETES
    
    def cache_consulta_claude(self, consulta: str, cliente: Optional[str] = None, 
                             periodo_dias: int = 30, resultado: Any = None, 
                             ttl: int = 300) -> Optional[Any]:
        """Cache específico para consultas do Claude AI"""
        chave = self._gerar_chave(
            "claude_consulta",
            consulta=consulta.lower().strip(),
            cliente=cliente,
            periodo_dias=periodo_dias
        )
        
        if resultado is not None:
            # Salvar no cache
            return self.set(chave, resultado, ttl)
        else:
            # Buscar do cache
            return self.get(chave)
    
    def cache_estatisticas_cliente(self, cliente: str, periodo_dias: int = 30, 
                                  dados: Any = None, ttl: int = 180) -> Optional[Any]:
        """Cache para estatísticas por cliente"""
        chave = self._gerar_chave(
            "stats_cliente",
            cliente=cliente,
            periodo_dias=periodo_dias
        )
        
        if dados is not None:
            return self.set(chave, dados, ttl)
        else:
            return self.get(chave)
    
    def cache_entregas_cliente(self, cliente: str, periodo_dias: int = 30, 
                              entregas: Any = None, ttl: int = 120) -> Optional[Any]:
        """Cache para entregas por cliente"""
        chave = self._gerar_chave(
            "entregas_cliente",
            cliente=cliente,
            periodo_dias=periodo_dias
        )
        
        if entregas is not None:
            return self.set(chave, entregas, ttl)
        else:
            return self.get(chave)
    
    def cache_dashboard_vendedor(self, vendedor: str, dados: Any = None, 
                                ttl: int = 60) -> Optional[Any]:
        """Cache para dashboard do vendedor"""
        chave = self._gerar_chave("dashboard_vendedor", vendedor=vendedor)
        
        if dados is not None:
            return self.set(chave, dados, ttl)
        else:
            return self.get(chave)
    
    def invalidar_cache_cliente(self, cliente: str) -> int:
        """Invalida todo cache relacionado a um cliente específico"""
        patterns = [
            f"claude_consulta:*{cliente}*",
            f"stats_cliente:*{cliente}*", 
            f"entregas_cliente:*{cliente}*"
        ]
        
        total_removido = 0
        for pattern in patterns:
            total_removido += self.flush_pattern(pattern)
        
        logger.info(f"🗑️ Cache do cliente {cliente} invalidado: {total_removido} chaves")
        return total_removido
    
    def get_info_cache(self) -> Dict[str, Any]:
        """Retorna informações sobre o cache"""
        if not self.disponivel:
            return {"disponivel": False, "erro": "Redis não conectado"}
        
        try:
            info = self.client.info()
            return {
                "disponivel": True,
                "memoria_usada": info.get('used_memory_human', 'N/A'),
                "chaves_totais": info.get('db0', {}).get('keys', 0),
                "hits": info.get('keyspace_hits', 0),
                "misses": info.get('keyspace_misses', 0),
                "versao_redis": info.get('redis_version', 'N/A')
            }
        except Exception as e:
            return {"disponivel": False, "erro": str(e)}


# Decorador para cache automático de funções
def cache_resultado(ttl: int = 300, prefixo: str = "funcao"):
    """Decorador para cachear automaticamente resultado de funções"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = RedisCache()
            if not cache.disponivel:
                return func(*args, **kwargs)
            
            # Gerar chave baseada na função e parâmetros
            chave = cache._gerar_chave(
                f"{prefixo}_{func.__name__}",
                args=args,
                kwargs=kwargs
            )
            
            # Tentar buscar do cache
            resultado_cache = cache.get(chave)
            if resultado_cache is not None:
                logger.debug(f"✅ Cache HIT: {func.__name__}")
                return resultado_cache
            
            # Executar função e cachear resultado
            resultado = func(*args, **kwargs)
            cache.set(chave, resultado, ttl)
            logger.debug(f"💾 Cache MISS: {func.__name__} - resultado cacheado")
            
            return resultado
        return wrapper
    return decorator


# Instância global do cache
redis_cache = RedisCache()

# Variável global para indicar disponibilidade
REDIS_DISPONIVEL = redis_cache.disponivel


# IMPLEMENTAÇÃO DO PADRÃO CACHE-ASIDE PARA CONSULTAS
class CacheAsideManager:
    """Implementa padrão Cache-Aside conforme documentação Redis oficial"""
    
    def __init__(self, cache_instance: Optional[RedisCache] = None):
        self.cache = cache_instance or redis_cache
    
    def get_or_set(self, cache_key: str, fetch_function, ttl: int = 300, *args, **kwargs):
        """
        Implementa Cache-Aside Pattern:
        1. Verifica se dados estão no cache (Cache Hit)
        2. Se não estão, busca da fonte original (Cache Miss)
        3. Armazena no cache para próximas consultas
        """
        # Step 1: Verificar cache (Cache Hit?)
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"🎯 CACHE HIT: {cache_key}")
            return cached_data, True  # True = veio do cache
        
        # Step 2: Cache Miss - buscar da fonte original
        logger.debug(f"💨 CACHE MISS: {cache_key}")
        fresh_data = fetch_function(*args, **kwargs)
        
        # Step 3: Armazenar no cache para próximas consultas
        if fresh_data is not None:
            self.cache.set(cache_key, fresh_data, ttl)
            logger.debug(f"💾 Dados armazenados no cache: {cache_key}")
        
        return fresh_data, False  # False = veio da fonte original


# Instância global do gerenciador Cache-Aside
cache_aside = CacheAsideManager()


# INTELLIGENT CACHE (para compatibilidade com MCP v4.0)
class IntelligentCache:
    """Cache inteligente com categorização para IA avançada"""
    
    def __init__(self, base_cache: Optional[RedisCache] = None):
        self.cache = base_cache or redis_cache
        self.categories = {}
    
    def set(self, key: str, value: Any, category: str = "general", ttl: int = 300) -> bool:
        """Armazena com categoria para organização"""
        categorized_key = f"{category}:{key}"
        
        # Rastrear categoria
        if category not in self.categories:
            self.categories[category] = []
        if categorized_key not in self.categories[category]:
            self.categories[category].append(categorized_key)
        
        return self.cache.set(categorized_key, value, ttl)
    
    def get(self, key: str, category: str = "general") -> Optional[Any]:
        """Busca por categoria"""
        categorized_key = f"{category}:{key}"
        return self.cache.get(categorized_key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Estatísticas do cache inteligente"""
        return {
            "categories": list(self.categories.keys()),
            "total_categories": len(self.categories),
            "cache_available": self.cache.disponivel,
            "cache_info": self.cache.get_info_cache() if self.cache.disponivel else {}
        }
    
    def clear_category(self, category: str) -> int:
        """Limpa cache de uma categoria específica"""
        if category in self.categories:
            count = 0
            for key in self.categories[category]:
                if self.cache.delete(key):
                    count += 1
            del self.categories[category]
            return count
        return 0

# Instância global do cache inteligente
intelligent_cache = IntelligentCache()

# Decorador compatível com cache_result
def cache_result(ttl: int = 300, category: str = "function_cache"):
    """Decorador para cache de resultados com categoria"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gerar chave baseada na função
            func_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Tentar buscar do cache
            cached = intelligent_cache.get(func_key, category)
            if cached is not None:
                return cached
            
            # Executar e cachear
            result = func(*args, **kwargs)
            intelligent_cache.set(func_key, result, category, ttl)
            
            return result
        return wrapper
    return decorator

# FUNÇÃO UTILITÁRIA PARA INTEGRAÇÃO FÁCIL
def cached_query(prefixo: str, ttl: int = 300):
    """
    Decorador simplificado para cachear consultas ao banco
    Exemplo de uso:
    
    @cached_query('entregas_assai', ttl=180)
    def buscar_entregas_assai(periodo_dias=30):
        return query_banco_dados()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gerar chave única
            chave = redis_cache._gerar_chave(prefixo, args=args, kwargs=kwargs)
            
            # Usar Cache-Aside pattern
            resultado, from_cache = cache_aside.get_or_set(
                chave, func, ttl, *args, **kwargs
            )
            
            # Adicionar informação se veio do cache
            if isinstance(resultado, dict):
                resultado['_from_cache'] = from_cache
            
            return resultado
        return wrapper
    return decorator 