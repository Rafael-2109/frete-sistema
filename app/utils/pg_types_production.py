"""
Módulo para garantir registro correto de tipos PostgreSQL em produção
Este módulo é carregado ANTES de qualquer conexão com o banco
"""
import os
import sys

def registrar_tipos_postgresql_producao():
    """
    Registra tipos PostgreSQL de forma global para produção
    Deve ser chamado ANTES de criar qualquer conexão com o banco
    """
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
        
        print("✅ [PRODUÇÃO] Tipos PostgreSQL registrados globalmente com sucesso!")
        return True
        
    except Exception as e:
        print(f"⚠️ [PRODUÇÃO] Erro ao registrar tipos PostgreSQL: {e}")
        return False

# Registrar imediatamente ao importar o módulo
if 'postgres' in os.getenv('DATABASE_URL', ''):
    registrar_tipos_postgresql_producao()