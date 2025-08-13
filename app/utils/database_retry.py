"""
Database Retry Decorator para Erros SSL
========================================

Implementa retry automático para operações de banco de dados
com tratamento especial para erros SSL do PostgreSQL.
"""

from functools import wraps
import time
import logging
from sqlalchemy.exc import OperationalError, DBAPIError, InterfaceError
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


def retry_on_ssl_error(max_retries: int = 3, initial_delay: float = 0.5, backoff_factor: float = 2) -> Callable:
    """
    Decorator que implementa retry automático para erros SSL de banco de dados.
    
    Trata especialmente:
    - SSL error: decryption failed or bad record mac
    - Connection reset/EOF errors
    - Idle transaction timeouts
    
    Args:
        max_retries: Número máximo de tentativas (padrão: 3)
        initial_delay: Delay inicial em segundos (padrão: 0.5)
        backoff_factor: Multiplicador do delay a cada tentativa (padrão: 2)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            from app import db
            
            last_exception = None
            delay = initial_delay
            
            for attempt in range(max_retries):
                try:
                    # Tenta executar a função
                    return func(*args, **kwargs)
                    
                except (OperationalError, DBAPIError, InterfaceError) as e:
                    error_msg = str(e).lower()
                    
                    # Verifica se é um erro SSL/conexão recuperável
                    ssl_errors = [
                        'ssl error',
                        'decryption failed',
                        'bad record mac',
                        'eof detected',
                        'broken pipe',
                        'connection reset',
                        'idle-in-transaction timeout',
                        'terminating connection',
                        'server closed the connection'
                    ]
                    
                    is_ssl_error = any(err in error_msg for err in ssl_errors)
                    
                    if is_ssl_error and attempt < max_retries - 1:
                        last_exception = e
                        logger.warning(
                            f"⚠️ Erro SSL na tentativa {attempt + 1}/{max_retries}: "
                            f"Aguardando {delay:.1f}s antes de tentar novamente..."
                        )
                        
                        # Força limpeza da sessão e reconexão
                        try:
                            db.session.rollback()
                            db.session.close()
                            # Força o pool a descartar conexões problemáticas
                            db.engine.dispose()
                            logger.debug("✅ Conexões do pool descartadas")
                        except Exception as cleanup_error:
                            logger.debug(f"Erro durante limpeza: {cleanup_error}")
                        
                        # Aguarda com backoff exponencial
                        time.sleep(delay)
                        delay *= backoff_factor
                        
                    else:
                        # Não é erro SSL ou é a última tentativa
                        if is_ssl_error:
                            logger.error(f"❌ Erro SSL após {max_retries} tentativas: {str(e)[:200]}")
                        raise
                        
                except Exception as e:
                    # Outros erros não relacionados - propaga sem retry
                    raise
            
            # Se chegou aqui, todas as tentativas falharam
            if last_exception:
                logger.error(f"❌ Todas as {max_retries} tentativas falharam")
                raise last_exception
                
        return wrapper
    return decorator


def commit_with_retry(session, max_retries: int = 3) -> bool:
    """
    Executa commit com retry automático em caso de erro SSL.
    
    Args:
        session: Sessão do SQLAlchemy
        max_retries: Número máximo de tentativas
        
    Returns:
        True se o commit foi bem sucedido, False caso contrário
    """
    from app import db
    
    delay = 0.5
    
    for attempt in range(max_retries):
        try:
            session.commit()
            return True
            
        except (OperationalError, DBAPIError) as e:
            error_msg = str(e).lower()
            
            if any(err in error_msg for err in ['ssl', 'decryption', 'bad record']):
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Erro SSL no commit, tentativa {attempt + 1}/{max_retries}")
                    try:
                        session.rollback()
                        session.close()
                        db.engine.dispose()
                    except:
                        pass
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error(f"❌ Erro SSL no commit após {max_retries} tentativas")
                    raise
            else:
                raise
                
    return False


def execute_in_chunks(items: list, chunk_size: int, operation: Callable, 
                      commit_after_each: bool = True) -> dict:
    """
    Executa operação em chunks menores para evitar timeout SSL.
    
    Args:
        items: Lista de items para processar
        chunk_size: Tamanho de cada chunk
        operation: Função que processa cada chunk
        commit_after_each: Se deve commitar após cada chunk
        
    Returns:
        Dict com estatísticas da execução
    """
    from app import db
    
    total = len(items)
    processed = 0
    failed = 0
    errors = []
    
    logger.info(f"📦 Processando {total} items em chunks de {chunk_size}")
    
    for i in range(0, total, chunk_size):
        chunk = items[i:i + chunk_size]
        chunk_num = (i // chunk_size) + 1
        total_chunks = (total + chunk_size - 1) // chunk_size
        
        try:
            # Processa o chunk
            operation(chunk)
            
            if commit_after_each:
                if commit_with_retry(db.session):
                    processed += len(chunk)
                    logger.debug(f"✅ Chunk {chunk_num}/{total_chunks} processado ({len(chunk)} items)")
                else:
                    failed += len(chunk)
                    errors.append(f"Chunk {chunk_num}: Falha no commit")
            else:
                processed += len(chunk)
                
        except Exception as e:
            failed += len(chunk)
            error_msg = f"Chunk {chunk_num}: {str(e)[:100]}"
            errors.append(error_msg)
            logger.error(f"❌ {error_msg}")
            
            # Tenta fazer rollback
            try:
                db.session.rollback()
            except:
                pass
    
    # Commit final se não estava commitando após cada chunk
    if not commit_after_each and processed > 0:
        try:
            commit_with_retry(db.session)
            logger.info(f"✅ Commit final realizado")
        except Exception as e:
            logger.error(f"❌ Erro no commit final: {e}")
            errors.append(f"Commit final: {str(e)[:100]}")
    
    return {
        'total': total,
        'processed': processed,
        'failed': failed,
        'errors': errors
    }