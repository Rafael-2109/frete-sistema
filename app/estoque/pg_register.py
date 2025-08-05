"""
Registro definitivo de tipos PostgreSQL para evitar erro PG 1082
Este módulo DEVE ser importado no __init__.py do app ANTES de criar o db
"""
import os
import logging

logger = logging.getLogger(__name__)

def register_pg_types_on_connection(dbapi_conn, connection_record):
    """
    Registra tipos PostgreSQL em CADA conexão criada
    Evita erro "Unknown PG numeric type: 1082"
    """
    try:
        import psycopg2
        from psycopg2 import extensions
        
        # Obter cursor da conexão
        cursor = dbapi_conn.cursor()
        
        # Registrar tipo DATE (1082) diretamente na conexão
        DATE = extensions.new_type((1082,), "DATE", extensions.DATE)
        extensions.register_type(DATE, cursor)
        
        # Registrar tipo TIME (1083)
        TIME = extensions.new_type((1083,), "TIME", extensions.TIME)
        extensions.register_type(TIME, cursor)
        
        # Registrar tipo TIMESTAMP (1114)
        TIMESTAMP = extensions.new_type((1114,), "TIMESTAMP", extensions.PYDATETIME)
        extensions.register_type(TIMESTAMP, cursor)
        
        # Registrar tipo TIMESTAMPTZ (1184)
        TIMESTAMPTZ = extensions.new_type((1184,), "TIMESTAMPTZ", extensions.PYDATETIME)
        extensions.register_type(TIMESTAMPTZ, cursor)
        
        # Registrar arrays de DATE (1182)
        DATEARRAY = extensions.new_array_type((1182,), "DATEARRAY", DATE)
        extensions.register_type(DATEARRAY, cursor)
        
        cursor.close()
        logger.debug("✅ Tipos PostgreSQL registrados na conexão")
        
    except Exception as e:
        logger.debug(f"⚠️ Registro de tipos PG: {e}")

def setup_pg_types(app):
    """
    Configura registro automático de tipos PostgreSQL no Flask app
    Deve ser chamado DEPOIS de criar o app e ANTES de usar o db
    """
    try:
        # Só aplicar se for PostgreSQL
        if 'postgres' not in os.getenv('DATABASE_URL', ''):
            return
            
        from sqlalchemy import event
        from sqlalchemy.pool import Pool
        
        # Registrar evento para CADA nova conexão
        event.listen(Pool, 'connect', register_pg_types_on_connection)
        
        logger.info("✅ Listener de tipos PostgreSQL configurado")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao configurar tipos PostgreSQL: {e}")
        return False

def force_register_global():
    """
    Força registro global de tipos (fallback)
    """
    if 'postgres' not in os.getenv('DATABASE_URL', ''):
        return
        
    try:
        import psycopg2
        from psycopg2 import extensions
        
        # Registrar globalmente (fallback)
        DATE = extensions.new_type((1082,), "DATE", extensions.DATE)
        extensions.register_type(DATE)
        extensions.register_type(DATE, None)
        
        TIME = extensions.new_type((1083,), "TIME", extensions.TIME)
        extensions.register_type(TIME)
        extensions.register_type(TIME, None)
        
        TIMESTAMP = extensions.new_type((1114,), "TIMESTAMP", extensions.PYDATETIME)
        extensions.register_type(TIMESTAMP)
        extensions.register_type(TIMESTAMP, None)
        
        TIMESTAMPTZ = extensions.new_type((1184,), "TIMESTAMPTZ", extensions.PYDATETIME)
        extensions.register_type(TIMESTAMPTZ)
        extensions.register_type(TIMESTAMPTZ, None)
        
        DATEARRAY = extensions.new_array_type((1182,), "DATEARRAY", DATE)
        extensions.register_type(DATEARRAY)
        extensions.register_type(DATEARRAY, None)
        
        logger.info("✅ Tipos PostgreSQL registrados globalmente")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Erro ao registrar tipos globalmente: {e}")
        return False