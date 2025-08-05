"""
REGISTRO FORÇADO DE TIPOS POSTGRESQL
Este arquivo DEVE ser importado ANTES de qualquer outro módulo
"""
import os
import sys

def force_register_pg_types():
    """
    Força o registro de tipos PostgreSQL ANTES de qualquer conexão
    """
    # Só executa se estiver usando PostgreSQL
    if 'postgres' not in os.getenv('DATABASE_URL', ''):
        return
    
    try:
        import psycopg2
        from psycopg2 import extensions
        
        # Registrar tipos PostgreSQL globalmente
        # DATE (OID 1082) - O tipo que está causando problemas
        DATE = extensions.new_type((1082,), "DATE", extensions.DATE)
        extensions.register_type(DATE)
        
        # TIME (OID 1083)
        TIME = extensions.new_type((1083,), "TIME", extensions.TIME)
        extensions.register_type(TIME)
        
        # TIMESTAMP (OID 1114)
        TIMESTAMP = extensions.new_type((1114,), "TIMESTAMP", extensions.PYDATETIME)
        extensions.register_type(TIMESTAMP)
        
        # TIMESTAMPTZ (OID 1184)
        TIMESTAMPTZ = extensions.new_type((1184,), "TIMESTAMPTZ", extensions.PYDATETIME)
        extensions.register_type(TIMESTAMPTZ)
        
        # Arrays de DATE (OID 1182)
        DATEARRAY = extensions.new_array_type((1182,), "DATEARRAY", DATE)
        extensions.register_type(DATEARRAY)
        
        print(f"✅ [FORÇA BRUTA] Tipos PostgreSQL registrados com sucesso!")
        print(f"✅ DATABASE_URL detectada: {os.getenv('DATABASE_URL', '')[:30]}...")
        
        # Registrar também em todas as conexões futuras
        extensions.register_type(DATE, None)
        extensions.register_type(TIME, None)
        extensions.register_type(TIMESTAMP, None)
        extensions.register_type(TIMESTAMPTZ, None)
        extensions.register_type(DATEARRAY, None)
        
        print("✅ [FORÇA BRUTA] Tipos registrados globalmente para TODAS as conexões!")
        
        return True
        
    except Exception as e:
        print(f"⚠️ [FORÇA BRUTA] Erro ao registrar tipos PostgreSQL: {e}")
        return False

# EXECUTAR IMEDIATAMENTE AO IMPORTAR
force_register_pg_types()