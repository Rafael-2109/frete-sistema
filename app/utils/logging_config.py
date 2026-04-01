import logging
import re
import sys
from datetime import datetime
import traceback
from functools import wraps
import time
import psutil
import os


# ---------------------------------------------------------------------------
# SensitiveFilter — redacta credenciais em log records
# ---------------------------------------------------------------------------

class SensitiveFilter(logging.Filter):
    """Redacta credenciais e segredos em mensagens de log.

    Patterns redactados:
    - URLs com credenciais: ``redis://:password@host`` -> ``redis://***@host``
    - Pares chave=valor: ``password=abc``, ``api_key=xyz``, ``secret=...``, ``token=...``
    - Strings JSON-like: ``"api_key": "valor"``

    A classe e DEFENSIVA: qualquer excecao interna e engolida para jamais
    quebrar o pipeline de logging.
    """

    # URL com credenciais  (ex: redis://:senha@host, postgres://user:pass@host)
    _URL_CRED_RE = re.compile(
        r'(?P<scheme>[a-zA-Z][a-zA-Z0-9+\-.]*)://'   # scheme://
        r'(?P<userinfo>[^@]+)@',                       # userinfo@
    )

    # Pares chave=valor (query string ou log text, inclui JSON "key": "value")
    _KV_RE = re.compile(
        r'(?i)'
        r'(?P<key>password|passwd|api_key|apikey|secret|token|authorization|credential)'
        r'\s*[=:]\s*'
        r'(?P<quote>["\']?)(?P<value>.+?)(?=(?P=quote)[\s,;}\])]|(?P=quote)$|[\s,;}\])]+|$)',
    )

    # Authorization Bearer/Basic/Token pattern
    _AUTH_RE = re.compile(
        r'(?i)(?P<scheme>Bearer|Basic|Token)\s+(?P<credential>\S+)'
    )

    def _redact(self, text: str) -> str:
        """Aplica redacao a uma string."""
        # 1) URLs com credenciais  ->  scheme://***@host
        text = self._URL_CRED_RE.sub(
            lambda m: f"{m.group('scheme')}://***@",
            text,
        )
        # 2) Authorization headers  ->  Bearer ***
        text = self._AUTH_RE.sub(
            lambda m: f"{m.group('scheme')} ***",
            text,
        )
        # 3) Pares chave=valor  ->  key=***
        text = self._KV_RE.sub(
            lambda m: f"{m.group('key')}=***",
            text,
        )
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        """Modifica record.msg e record.args para remover credenciais.

        Retorna sempre ``True`` para que o record continue no pipeline.
        """
        try:
            # Redactar msg (pode ser str ou outro tipo — so processa str)
            if isinstance(record.msg, str):
                record.msg = self._redact(record.msg)

            # Redactar args (tupla ou dict usados em %-formatting)
            if isinstance(record.args, tuple):
                record.args = tuple(
                    self._redact(a) if isinstance(a, str) else a
                    for a in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: self._redact(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
        except Exception:
            # DEFENSIVO: nunca quebrar logging
            pass

        return True


# Configuração de logging
def setup_logging():
    """Configura o sistema de logging detalhado"""
    
    # Formato detalhado para logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Logger principal
    logger = logging.getLogger('sistema_fretes')
    logger.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # Capturar logs dos modulos app.* (routes, services, workers)
    # Sem isso, loggers com getLogger(__name__) propagam para root (default WARNING)
    # e INFO/DEBUG sao descartados silenciosamente em producao
    app_logger = logging.getLogger('app')
    app_logger.setLevel(logging.INFO)
    if not app_logger.handlers:
        app_logger.addHandler(console_handler)

    # Reduzir verbosidade de libs externas que ficam em INFO
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('xmlrpc').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    return logger

# Logger global
logger = setup_logging()

def log_performance(func):
    """Decorator para monitorar performance de funções"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        # Informações do sistema antes
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            result = func(*args, **kwargs)
            
            # Informações do sistema depois
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            execution_time = time.time() - start_time
            
            # Log de performance
            logger.info(f"🔄 {func.__name__} executado em {execution_time:.2f}s | "
                       f"Memória: {memory_before:.1f}MB → {memory_after:.1f}MB | "
                       f"Δ: {memory_after - memory_before:+.1f}MB")
            
            # Alerta se demorou muito
            if execution_time > 5:
                logger.warning(f"⚠️ {func.__name__} LENTO: {execution_time:.2f}s")
            
            # Alerta se consumiu muita memória
            if memory_after - memory_before > 50:
                logger.warning(f"⚠️ {func.__name__} MEMÓRIA ALTA: +{memory_after - memory_before:.1f}MB")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ ERRO em {func.__name__}: {str(e)}")
            logger.error(f"📍 Traceback: {traceback.format_exc()}")
            raise
            
    return wrapper

def log_system_status():
    """Log do status atual do sistema"""
    try:
        process = psutil.Process()
        
        # Informações de memória
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # Informações de CPU
        cpu_percent = process.cpu_percent()
        
        # Informações do sistema
        system_memory = psutil.virtual_memory()
        
        logger.info(f"💻 STATUS SISTEMA: "
                   f"CPU: {cpu_percent:.1f}% | "
                   f"Memória Processo: {memory_mb:.1f}MB | "
                   f"Memória Sistema: {system_memory.percent:.1f}% | "
                   f"PID: {os.getpid()}")
        
        # Alertas
        if memory_mb > 300:
            logger.warning(f"⚠️ MEMÓRIA ALTA: {memory_mb:.1f}MB")
            
        if cpu_percent > 80:
            logger.warning(f"⚠️ CPU ALTA: {cpu_percent:.1f}%")
            
    except Exception as e:
        logger.error(f"❌ Erro ao verificar status: {str(e)}")

def log_database_query(query_name, duration, row_count=None):
    """Log de queries do banco de dados"""
    logger.info(f"🗄️ DB {query_name}: {duration:.3f}s" + 
               (f" | {row_count} registros" if row_count else ""))
    
    if duration > 2:
        logger.warning(f"⚠️ QUERY LENTA {query_name}: {duration:.3f}s")

def log_request_info(request):
    """Log de informações da requisição"""
    # Ignorar logs para endpoints de polling frequente
    paths_ignorados = [
        '/portal/api/status-job/',
        '/monitoramento/historico_agendamentos',
        '/static/',
        '/favicon.ico'
    ]
    
    # Verificar se o path deve ser ignorado
    for path in paths_ignorados:
        if request.path.startswith(path):
            return  # Não logar
    
    # Logar normalmente outras requisições
    logger.info(f"🌐 {request.method} {request.path} | "
               f"User-Agent: {request.headers.get('User-Agent', 'Unknown')[:50]}...")

def log_error(error, context=""):
    """Log detalhado de erros"""
    logger.error(f"❌ ERRO{' - ' + context if context else ''}: {str(error)}")
    logger.error(f"📍 Traceback completo:\n{traceback.format_exc()}")
    
    # Log status do sistema no momento do erro
    log_system_status() 