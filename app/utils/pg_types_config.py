"""
Configuração limpa e definitiva para tipos PostgreSQL
Resolve o erro "Unknown PG numeric type: 1082" de forma simples e eficiente
"""

import psycopg2
from psycopg2 import extensions

def registrar_tipos_postgresql():
    """
    Registra tipos PostgreSQL de forma limpa e eficiente
    Deve ser chamado ANTES de criar qualquer conexão com o banco
    """
    try:
        # Registrar tipos PostgreSQL -> Python usando adaptadores nativos do psycopg2
        # DATE (OID 1082) - Converte para datetime.date
        DATE = extensions.new_type((1082,), "DATE", extensions.DATE)
        extensions.register_type(DATE)
        
        # TIME (OID 1083) - Converte para datetime.time
        TIME = extensions.new_type((1083,), "TIME", extensions.TIME) 
        extensions.register_type(TIME)
        
        # TIMESTAMP (OID 1114) - Converte para datetime.datetime
        TIMESTAMP = extensions.new_type((1114,), "TIMESTAMP", extensions.PYDATETIME)
        extensions.register_type(TIMESTAMP)
        
        # TIMESTAMPTZ (OID 1184) - Converte para datetime.datetime com timezone
        TIMESTAMPTZ = extensions.new_type((1184,), "TIMESTAMPTZ", extensions.PYDATETIME)
        extensions.register_type(TIMESTAMPTZ)
        
        # Arrays de data/hora
        DATEARRAY = extensions.new_array_type((1182,), "DATEARRAY", DATE)
        extensions.register_type(DATEARRAY)
        
        TIMEARRAY = extensions.new_array_type((1183,), "TIMEARRAY", TIME)
        extensions.register_type(TIMEARRAY)
        
        TIMESTAMPARRAY = extensions.new_array_type((1115,), "TIMESTAMPARRAY", TIMESTAMP)
        extensions.register_type(TIMESTAMPARRAY)
        
        TIMESTAMPTZARRAY = extensions.new_array_type((1185,), "TIMESTAMPTZARRAY", TIMESTAMPTZ)
        extensions.register_type(TIMESTAMPTZARRAY)
        
        print("✅ Tipos PostgreSQL registrados com sucesso (solução definitiva)")
        return True
        
    except Exception as e:
        print(f"⚠️ Erro ao registrar tipos PostgreSQL: {e}")
        return False

# Registrar ao importar o módulo
registrar_tipos_postgresql()