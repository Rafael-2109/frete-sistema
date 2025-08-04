"""
Sistema de Cache para Permissões
================================

Cache multi-nível otimizado para alta performance.
L1: Memória (LRU)
L2: Redis (se disponível)
L3: Banco de dados
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List
from collections import OrderedDict
from threading import Lock
from app import db
from app.permissions.models_unified import PermissionCache as DBCache
from app.utils.timezone import agora_brasil

logger = logging.getLogger(__name__)


class LRUCache:
    """Cache LRU thread-safe em memória"""
    
    def __init__(self, maxsize: int = 1000):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.lock = Lock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                # Move para o final (mais recente)
                self.cache.move_to_end(key)
                self.hits += 1
                return self.cache[key]['value']
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        with self.lock:
            # Remover se já existe
            if key in self.cache:
                del self.cache[key]
            
            # Adicionar no final
            self.cache[key] = {
                'value': value,
                'expires_at': datetime.utcnow() + timedelta(seconds=ttl)
            }
            
            # Remover mais antigo se exceder tamanho
            if len(self.cache) > self.maxsize:
                self.cache.popitem(last=False)
    
    def invalidate(self, pattern: Optional[str] = None):
        """Invalida cache por padrão ou tudo"""
        with self.lock:
            if pattern:
                keys_to_remove = [k for k in self.cache if pattern in k]
                for key in keys_to_remove:
                    del self.cache[key]
            else:
                self.cache.clear()
    
    def clean_expired(self):
        """Remove entradas expiradas"""
        with self.lock:
            now = datetime.utcnow()
            expired = [k for k, v in self.cache.items() if v['expires_at'] < now]
            for key in expired:
                del self.cache[key]
    
    def stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'size': len(self.cache),
            'maxsize': self.maxsize,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(hit_rate, 2)
        }


class PermissionCache:
    """
    Sistema de cache multi-nível para permissões.
    """
    
    # Instância singleton do cache L1
    _l1_cache = None
    _lock = Lock()
    
    def __init__(self):
        # Inicializar L1 cache (singleton)
        with self._lock:
            if PermissionCache._l1_cache is None:
                PermissionCache._l1_cache = LRUCache(maxsize=1000)
        
        self.l1 = PermissionCache._l1_cache
        
        # Tentar conectar ao Redis para L2
        self.redis = None
        try:
            from app.utils.redis_cache import redis_cache
            self.redis = redis_cache
            logger.info("Redis cache L2 habilitado para permissões")
        except ImportError:
            logger.info("Redis não disponível, usando apenas L1 e L3")
    
    def generate_key(
        self,
        user_id: int,
        category: Optional[str] = None,
        module: Optional[str] = None,
        submodule: Optional[str] = None,
        function: Optional[str] = None,
        action: str = 'view'
    ) -> str:
        """Gera chave única para o cache"""
        components = [
            str(user_id),
            category or '',
            module or '',
            submodule or function or '',
            action
        ]
        key_string = ':'.join(components)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]
        return f"perm:{key_hash}"
    
    def get(self, key: str) -> Optional[bool]:
        """
        Busca no cache multi-nível.
        L1 -> L2 -> L3
        """
        # L1: Memória
        result = self.l1.get(key)
        if result is not None:
            return result
        
        # L2: Redis
        if self.redis:
            try:
                cached = self.redis.get(key)
                if cached is not None:
                    result = json.loads(cached)
                    # Promover para L1
                    self.l1.set(key, result)
                    return result
            except Exception as e:
                logger.error(f"Erro ao buscar no Redis: {e}")
        
        # L3: Banco de dados
        try:
            db_cache = DBCache.query.filter_by(cache_key=key).first()
            if db_cache and db_cache.expires_at > agora_brasil():
                result = db_cache.permission_data.get('allowed', False)
                # Promover para L1 e L2
                self.l1.set(key, result)
                if self.redis:
                    ttl = int((db_cache.expires_at - agora_brasil()).total_seconds())
                    self.redis.set(key, json.dumps(result), ttl)
                return result
        except Exception as e:
            logger.error(f"Erro ao buscar no banco: {e}")
        
        return None
    
    def set(self, key: str, value: bool, ttl: int = 300):
        """
        Armazena no cache multi-nível.
        """
        # L1: Memória
        self.l1.set(key, value, ttl)
        
        # L2: Redis
        if self.redis:
            try:
                self.redis.set(key, json.dumps(value), ttl)
            except Exception as e:
                logger.error(f"Erro ao salvar no Redis: {e}")
        
        # L3: Banco de dados
        try:
            # Buscar ou criar entrada
            db_cache = DBCache.query.filter_by(cache_key=key).first()
            if not db_cache:
                db_cache = DBCache(cache_key=key)
            
            db_cache.permission_data = {'allowed': value}
            db_cache.expires_at = agora_brasil() + timedelta(seconds=ttl)
            db_cache.created_at = agora_brasil()
            
            db.session.add(db_cache)
            db.session.commit()
        except Exception as e:
            logger.error(f"Erro ao salvar no banco: {e}")
            db.session.rollback()
    
    def invalidate_user(self, user_id: int):
        """Invalida todo cache de um usuário"""
        pattern = f"perm:*{user_id}*"
        
        # L1: Memória
        self.l1.invalidate(pattern)
        
        # L2: Redis
        if self.redis:
            try:
                keys = self.redis.keys(pattern)
                if keys:
                    self.redis.delete(*keys)
            except Exception as e:
                logger.error(f"Erro ao invalidar Redis: {e}")
        
        # L3: Banco
        try:
            DBCache.query.filter_by(user_id=user_id).delete()
            db.session.commit()
        except Exception as e:
            logger.error(f"Erro ao invalidar banco: {e}")
            db.session.rollback()
    
    def invalidate_entity(
        self,
        entity_type: str,
        entity_id: int
    ):
        """Invalida cache relacionado a uma entidade"""
        # Por enquanto, invalidar todo o cache
        # TODO: Implementar invalidação seletiva mais eficiente
        self.invalidate_all()
    
    def invalidate_all(self):
        """Invalida todo o cache"""
        # L1
        self.l1.invalidate()
        
        # L2
        if self.redis:
            try:
                keys = self.redis.keys("perm:*")
                if keys:
                    self.redis.delete(*keys)
            except Exception as e:
                logger.error(f"Erro ao limpar Redis: {e}")
        
        # L3
        try:
            DBCache.query.delete()
            db.session.commit()
        except Exception as e:
            logger.error(f"Erro ao limpar banco: {e}")
            db.session.rollback()
    
    def clean_expired(self):
        """Remove entradas expiradas de todos os níveis"""
        # L1
        self.l1.clean_expired()
        
        # L3
        DBCache.clean_expired()
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        stats = {
            'l1': self.l1.stats(),
            'l2': {'available': self.redis is not None},
            'l3': {}
        }
        
        # Stats do L3
        try:
            total = DBCache.query.count()
            expired = DBCache.query.filter(
                DBCache.expires_at < agora_brasil()
            ).count()
            stats['l3'] = {
                'total': total,
                'expired': expired,
                'active': total - expired
            }
        except Exception:
            pass
        
        return stats


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def invalidate_user_permissions(user_id: int):
    """Invalida todas as permissões em cache de um usuário"""
    cache = PermissionCache()
    cache.invalidate_user(user_id)
    logger.info(f"Cache de permissões invalidado para usuário {user_id}")


def invalidate_entity_permissions(entity_type: str, entity_id: int):
    """Invalida permissões relacionadas a uma entidade"""
    cache = PermissionCache()
    cache.invalidate_entity(entity_type, entity_id)
    logger.info(f"Cache invalidado para {entity_type}:{entity_id}")


def warm_cache_for_user(user_id: int):
    """
    Pré-carrega cache de permissões para um usuário.
    Útil após login ou alterações em massa.
    """
    from app.permissions.utils_unified import get_user_permission_context
    
    try:
        # Buscar contexto completo
        context = get_user_permission_context(user_id)
        
        # Cachear principais permissões
        cache = PermissionCache()
        
        for category in context.get('categories', []):
            for module in category.get('modules', []):
                for submodule in module.get('submodules', []):
                    # Cachear cada combinação
                    for action in ['view', 'edit', 'delete', 'export']:
                        key = cache.generate_key(
                            user_id=user_id,
                            category=category['name'],
                            module=module['name'],
                            submodule=submodule['name'],
                            action=action
                        )
                        
                        has_permission = submodule['permissions'].get(f'can_{action}', False)
                        cache.set(key, has_permission, ttl=3600)  # 1 hora
        
        logger.info(f"Cache aquecido para usuário {user_id}")
        
    except Exception as e:
        logger.error(f"Erro ao aquecer cache: {e}")


def get_cache_stats() -> Dict[str, Any]:
    """Retorna estatísticas globais do cache"""
    cache = PermissionCache()
    return cache.get_stats()