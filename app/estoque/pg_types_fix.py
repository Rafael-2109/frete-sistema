"""
Módulo para garantir registro de tipos PostgreSQL
DEVE ser importado ANTES de usar qualquer modelo
"""
import os

def force_register_types():
    """Força registro de tipos PostgreSQL"""
    if 'postgres' not in os.getenv('DATABASE_URL', ''):
        return
        
    try:
        import psycopg2
        from psycopg2 import extensions
        
        # Registrar globalmente
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
        
        print("✅ [PG_TYPES_FIX] Tipos PostgreSQL registrados com sucesso!")
        return True
        
    except Exception as e:
        print(f"⚠️ [PG_TYPES_FIX] Erro: {e}")
        return False

# Executar imediatamente
force_register_types()