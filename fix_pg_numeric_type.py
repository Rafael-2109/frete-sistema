"""
Fix para erro "Unknown PG numeric type: 1082" no psycopg2
Este erro ocorre com tipos DATE do PostgreSQL em algumas versões do psycopg2
"""

import psycopg2
from psycopg2 import extensions
import psycopg2.extras

# Registrar o tipo DATE (1082) no psycopg2
def register_date_type():
    """Registra o tipo DATE do PostgreSQL no psycopg2"""
    try:
        # Registrar adaptador para o tipo DATE (OID 1082)
        DATE_OID = 1082
        
        # Criar um type caster para DATE
        DATE = psycopg2.extensions.new_type((DATE_OID,), "DATE", psycopg2.extensions.UNICODE)
        psycopg2.extensions.register_type(DATE)
        
        print("✅ Tipo DATE registrado com sucesso no psycopg2")
        
    except Exception as e:
        print(f"❌ Erro ao registrar tipo DATE: {e}")

if __name__ == "__main__":
    register_date_type()
    print("Execute este script antes de iniciar a aplicação se estiver tendo problemas com 'Unknown PG numeric type: 1082'")