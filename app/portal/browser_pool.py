"""
Browser Pool Manager
Pool de instâncias de browser para processamento paralelo
"""

import os
from queue import Queue, Empty
from threading import Lock, Thread
from datetime import datetime, timedelta
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class BrowserPool:
    """Pool de instâncias de browser para processamento paralelo"""
    
    def __init__(self, pool_size=3, max_age_minutes=30):
        self.pool_size = pool_size
        self.max_age_minutes = max_age_minutes
        self.available = Queue()
        self.in_use = {}
        self.lock = Lock()
        self._initialize_pool()
        
        # Thread para limpeza periódica
        self.cleanup_thread = Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
    
    def _initialize_pool(self):
        """Inicializa pool de browsers"""
        for i in range(self.pool_size):
            try:
                from .browser_manager_v2 import BrowserManagerV2
                browser = BrowserManagerV2()
                self.available.put({
                    'id': f'browser_{i}',
                    'browser': browser,
                    'created_at': datetime.utcnow(),
                    'last_used': datetime.utcnow(),
                    'usage_count': 0
                })
                logger.info(f"Browser {i} adicionado ao pool")
            except Exception as e:
                logger.error(f"Erro ao criar browser {i}: {e}")
    
    @contextmanager
    def get_browser(self, timeout=30):
        """Context manager para obter e liberar browser automaticamente"""
        browser_info = None
        try:
            browser_info = self.acquire(timeout)
            yield browser_info['browser']
        finally:
            if browser_info:
                self.release(browser_info)
    
    def acquire(self, timeout=30):
        """Obtém browser disponível do pool"""
        try:
            browser_info = self.available.get(timeout=timeout)
            
            with self.lock:
                browser_info['usage_count'] += 1
                self.in_use[browser_info['id']] = browser_info
            
            logger.info(f"Browser {browser_info['id']} adquirido (uso #{browser_info['usage_count']})")
            return browser_info
            
        except Empty:
            # Se não há browsers disponíveis, tentar criar um temporário
            logger.warning("Pool esgotado, criando browser temporário")
            from .browser_manager_v2 import BrowserManagerV2
            temp_browser = BrowserManagerV2()
            return {
                'id': f'temp_{datetime.utcnow().timestamp()}',
                'browser': temp_browser,
                'created_at': datetime.utcnow(),
                'last_used': datetime.utcnow(),
                'usage_count': 1,
                'temporary': True
            }
    
    def release(self, browser_info):
        """Devolve browser ao pool"""
        with self.lock:
            browser_id = browser_info['id']
            if browser_id in self.in_use:
                del self.in_use[browser_id]
            
            browser_info['last_used'] = datetime.utcnow()
            
            # Se é temporário ou muito usado, fechar
            if browser_info.get('temporary') or browser_info['usage_count'] > 50:
                logger.info(f"Fechando browser {browser_id} (temporário ou muito usado)")
                try:
                    browser_info['browser'].close()
                except Exception as e:
                    logger.error(f"Erro ao fechar browser: {e}")
                    pass
            else:
                # Devolver ao pool
                self.available.put(browser_info)
                logger.info(f"Browser {browser_id} devolvido ao pool")
    
    def _cleanup_worker(self):
        """Thread que limpa browsers antigos periodicamente"""
        import time
        while True:
            try:
                time.sleep(300)  # A cada 5 minutos
                self.cleanup_stale()
            except Exception as e:
                logger.error(f"Erro no cleanup: {e}")
    
    def cleanup_stale(self):
        """Remove browsers inativos há muito tempo"""
        threshold = datetime.utcnow() - timedelta(minutes=self.max_age_minutes)
        temp_items = []
        
        # Esvaziar fila temporariamente
        while not self.available.empty():
            try:
                item = self.available.get_nowait()
                temp_items.append(item)
            except Exception as e:
                logger.error(f"Erro ao processar item: {e}")
                break
        
        # Processar cada item
        for browser_info in temp_items:
            if browser_info['created_at'] < threshold:
                # Browser muito antigo, recriar
                logger.info(f"Reciclando browser {browser_info['id']} (idade > {self.max_age_minutes} min)")
                try:
                    browser_info['browser'].close()
                except Exception as e:
                    logger.error(f"Erro ao fechar browser: {e}")
                    pass
                
                # Criar novo
                try:
                    from .browser_manager_v2 import BrowserManagerV2
                    new_browser = BrowserManagerV2()
                    browser_info['browser'] = new_browser
                    browser_info['created_at'] = datetime.utcnow()
                    browser_info['usage_count'] = 0
                except Exception as e:
                    logger.error(f"Erro ao recriar browser: {e}")
                    continue
            
            # Devolver ao pool
            self.available.put(browser_info)
    
    def get_status(self):
        """Retorna status do pool para monitoramento"""
        with self.lock:
            return {
                'pool_size': self.pool_size,
                'available': self.available.qsize(),
                'in_use': len(self.in_use),
                'browsers': [
                    {
                        'id': b['id'],
                        'usage_count': b['usage_count'],
                        'age_minutes': (datetime.utcnow() - b['created_at']).total_seconds() / 60
                    }
                    for b in list(self.in_use.values())
                ]
            }
    
    def shutdown(self):
        """Fecha todos os browsers do pool"""
        logger.info("Encerrando pool de browsers")
        
        # Fechar browsers em uso
        with self.lock:
            for browser_info in self.in_use.values():
                try:
                    browser_info['browser'].close()
                except Exception as e:
                    logger.error(f"Erro ao fechar browser: {e}")
                    pass
        
        # Fechar browsers disponíveis
        while not self.available.empty():
            try:
                browser_info = self.available.get_nowait()
                browser_info['browser'].close()
            except Exception as e:
                logger.error(f"Erro ao fechar browser: {e}")
                break
        
        logger.info("Pool de browsers encerrado")

# Singleton global do pool
_browser_pool = None

def get_browser_pool():
    """Obtém instância singleton do pool"""
    global _browser_pool
    if _browser_pool is None:
        pool_size = int(os.environ.get('BROWSER_POOL_SIZE', 3))
        _browser_pool = BrowserPool(pool_size=pool_size)
    return _browser_pool