"""
Módulo de configuração do banco de dados
Registra tipos PostgreSQL ANTES de qualquer uso
"""
import os

from app.utils.boot_log import boot_log

# REGISTRAR TIPOS POSTGRESQL IMEDIATAMENTE
if 'postgres' in os.getenv('DATABASE_URL', ''):
    try:
        import psycopg2
        from psycopg2 import extensions
        
        # Registrar tipos PostgreSQL globalmente
        DATE = extensions.new_type((1082,), "DATE", extensions.DATE)
        extensions.register_type(DATE)
        
        TIME = extensions.new_type((1083,), "TIME", extensions.TIME)
        extensions.register_type(TIME)
        
        TIMESTAMP = extensions.new_type((1114,), "TIMESTAMP", extensions.PYDATETIME)
        extensions.register_type(TIMESTAMP)
        
        TIMESTAMPTZ = extensions.new_type((1184,), "TIMESTAMPTZ", extensions.PYDATETIME)
        extensions.register_type(TIMESTAMPTZ)
        
        DATEARRAY = extensions.new_array_type((1182,), "DATEARRAY", DATE)
        extensions.register_type(DATEARRAY)
        
        # Registrar também para todas as conexões futuras
        extensions.register_type(DATE, None)
        extensions.register_type(TIME, None)
        extensions.register_type(TIMESTAMP, None)
        extensions.register_type(TIMESTAMPTZ, None)
        extensions.register_type(DATEARRAY, None)
        
        boot_log("✅ [DATABASE] Tipos PostgreSQL registrados no módulo database")

    except Exception as e:
        boot_log(f"⚠️ [DATABASE] Erro ao registrar tipos PostgreSQL: {e}", force=True)

# Importar db após registrar tipos
from app import db