"""
Adicione este código no início do arquivo app/__init__.py para corrigir o erro no Render
"""

# Fix para "Unknown PG numeric type: 1082" no Render
def fix_pg_date_type():
    """Registra o tipo DATE do PostgreSQL no psycopg2 para evitar erro no Render"""
    try:
        import psycopg2
        from psycopg2 import extensions
        
        # Verificar se já está registrado
        if 1082 not in extensions.string_types:
            # Registrar o tipo DATE (OID 1082)
            DATE = extensions.new_type((1082,), "DATE", extensions.UNICODE)
            extensions.register_type(DATE)
            
            # Registrar também DATEARRAY se necessário
            DATEARRAY = extensions.new_array_type((1182,), "DATEARRAY", DATE)
            extensions.register_type(DATEARRAY)
            
            print("✅ Tipo DATE do PostgreSQL registrado com sucesso")
    except Exception:
        # Ignorar se não estiver usando PostgreSQL
        pass

# Chamar a função logo após os imports
fix_pg_date_type()