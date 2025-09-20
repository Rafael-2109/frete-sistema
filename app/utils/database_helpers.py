"""
Utilitários para operações de banco de dados com tratamento de erros e retry logic
"""
import time
import logging
from functools import wraps
from sqlalchemy.exc import OperationalError, DBAPIError, DisconnectionError
from sqlalchemy import create_engine, pool
from flask import current_app

logger = logging.getLogger(__name__)

def retry_on_ssl_error(max_retries=3, backoff_factor=1.0):
    """
    Decorator para retry automático em caso de erro SSL/conexão
    
    Args:
        max_retries: Número máximo de tentativas
        backoff_factor: Fator de multiplicação para o tempo de espera entre tentativas
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                    
                except (OperationalError, DBAPIError, DisconnectionError) as e:
                    last_exception = e
                    error_msg = str(e)
                    
                    # Verificar se é erro de SSL ou conexão
                    if any(err in error_msg.lower() for err in ['ssl', 'connection', 'closed', 'timeout']):
                        if attempt < max_retries - 1:
                            wait_time = backoff_factor * (2 ** attempt)
                            logger.warning(f"⚠️ Erro de conexão (tentativa {attempt + 1}/{max_retries}). "
                                         f"Aguardando {wait_time}s antes de tentar novamente...")
                            
                            # Tentar fazer rollback se possível
                            try:
                                from app import db
                                db.session.rollback()
                                # Forçar reconexão
                                db.session.close()
                                db.engine.dispose()
                            except Exception as e:
                                pass
                            
                            time.sleep(wait_time)
                        else:
                            logger.error(f"❌ Erro persistente após {max_retries} tentativas: {e}")
                            raise
                    else:
                        # Não é erro de conexão, propagar imediatamente
                        raise
                        
                except Exception as e:
                    # Outros erros não relacionados a conexão
                    logger.error(f"❌ Erro não relacionado a conexão: {e}")
                    raise
            
            # Se chegou aqui, todas as tentativas falharam
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def execute_in_chunks(query_func, items, chunk_size=100, description="items"):
    """
    Executa uma função de query em chunks para evitar timeout
    
    Args:
        query_func: Função que recebe uma lista de items e retorna resultados
        items: Lista de items para processar
        chunk_size: Tamanho de cada chunk
        description: Descrição para logging
        
    Returns:
        Lista com todos os resultados concatenados
    """
    if not items:
        return []
    
    total_items = len(items)
    results = []
    
    logger.info(f"📦 Processando {total_items} {description} em lotes de {chunk_size}...")
    
    for i in range(0, total_items, chunk_size):
        chunk = items[i:i + chunk_size]
        chunk_num = (i // chunk_size) + 1
        total_chunks = (total_items + chunk_size - 1) // chunk_size
        
        try:
            logger.debug(f"   Processando lote {chunk_num}/{total_chunks} ({len(chunk)} items)...")
            chunk_results = query_func(chunk)
            results.extend(chunk_results if chunk_results else [])
            
            # Pequena pausa entre chunks para não sobrecarregar
            if i + chunk_size < total_items:
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar lote {chunk_num}: {e}")
            # Continuar com os próximos chunks mesmo se um falhar
            continue
    
    logger.info(f"✅ {len(results)} resultados obtidos de {total_items} {description}")
    return results


def safe_db_operation(operation_func, *args, **kwargs):
    """
    Executa uma operação de banco de dados com tratamento de erros e retry
    
    Args:
        operation_func: Função a ser executada
        *args, **kwargs: Argumentos para a função
        
    Returns:
        Resultado da operação ou None em caso de erro
    """
    try:
        return retry_on_ssl_error()(operation_func)(*args, **kwargs)
    except Exception as e:
        logger.error(f"❌ Erro na operação de banco de dados: {e}")
        return None


def ensure_connection():
    """
    Garante que a conexão com o banco está ativa
    """
    try:
        from app import db
        from sqlalchemy import text
        
        # Testa a conexão
        db.session.execute(text('SELECT 1'))
        return True
        
    except (OperationalError, DBAPIError, DisconnectionError) as e:
        logger.warning(f"⚠️ Conexão perdida, tentando reconectar: {e}")
        
        try:
            # Fechar sessão atual
            db.session.rollback()
            db.session.close()
            
            # Descartar pool de conexões
            db.engine.dispose()
            
            # Testar nova conexão
            db.session.execute(text('SELECT 1'))
            logger.info("✅ Conexão restabelecida com sucesso")
            return True
            
        except Exception as reconnect_error:
            logger.error(f"❌ Falha ao reconectar: {reconnect_error}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao verificar conexão: {e}")
        return False


def create_resilient_engine(database_url=None):
    """
    Cria um engine SQLAlchemy com configurações otimizadas para resiliência
    
    Args:
        database_url: URL do banco de dados (usa a configuração padrão se não fornecida)
        
    Returns:
        Engine SQLAlchemy configurado
    """
    if not database_url:
        database_url = current_app.config.get('SQLALCHEMY_DATABASE_URI')
    
    # Configurações otimizadas para evitar timeout e erros SSL
    engine = create_engine(
        database_url,
        poolclass=pool.QueuePool,
        pool_size=10,                    # Tamanho do pool
        max_overflow=20,                 # Conexões extras permitidas
        pool_timeout=30,                 # Timeout para obter conexão do pool
        pool_recycle=3600,              # Reciclar conexões após 1 hora
        pool_pre_ping=True,             # Testar conexão antes de usar
        connect_args={
            'connect_timeout': 30,       # Timeout de conexão
            'keepalives': 1,            # Ativar keepalive
            'keepalives_idle': 30,      # Tempo idle antes do keepalive
            'keepalives_interval': 10,   # Intervalo entre keepalives
            'keepalives_count': 5        # Número de keepalives antes de desistir
        }
    )
    
    return engine