#!/usr/bin/env python3
"""
Script para aplicar correção definitiva do erro PG 1082 no Render
Execute este script no shell do Render ANTES de reiniciar o serviço
"""

import os
import sys

print("APLICANDO CORREÇÃO DEFINITIVA PARA ERRO PG 1082")
print("=" * 50)

# 1. Registrar tipos globalmente
print("\n1. Registrando tipos PostgreSQL...")
try:
    import psycopg2
    from psycopg2 import extensions
    
    # Registrar todos os tipos necessários
    extensions.register_type(extensions.new_type((1082,), "DATE", extensions.DATE))
    extensions.register_type(extensions.new_type((1083,), "TIME", extensions.TIME))
    extensions.register_type(extensions.new_type((1114,), "TIMESTAMP", extensions.PYDATETIME))
    extensions.register_type(extensions.new_type((1184,), "TIMESTAMPTZ", extensions.PYDATETIME))
    
    # Arrays
    DATE = extensions.new_type((1082,), "DATE", extensions.DATE)
    DATEARRAY = extensions.new_array_type((1182,), "DATEARRAY", DATE)
    extensions.register_type(DATEARRAY)
    
    print("✅ Tipos registrados com sucesso!")
    
except Exception as e:
    print(f"❌ Erro ao registrar tipos: {e}")
    sys.exit(1)

# 2. Testar conexão
print("\n2. Testando conexão com banco...")
try:
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL não encontrada!")
        sys.exit(1)
        
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    # Teste simples
    cur.execute("SELECT CURRENT_DATE")
    result = cur.fetchone()
    print(f"✅ Conexão OK: {result[0]}")
    
    # Teste na tabela problemática
    print("\n3. Testando tabela projecao_estoque_cache...")
    try:
        cur.execute("""
            SELECT COUNT(*) FROM projecao_estoque_cache 
            WHERE data_projecao IS NOT NULL
        """)
        count = cur.fetchone()[0]
        print(f"✅ Query executada com sucesso! {count} registros com data")
    except Exception as e:
        print(f"⚠️ Erro na query (esperado se tabela não existir): {e}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Erro na conexão: {e}")

# 3. Instruções finais
print("\n" + "=" * 50)
print("PRÓXIMOS PASSOS:")
print("1. Faça deploy do código atualizado")
print("2. Reinicie o serviço no Render")
print("3. O erro PG 1082 deve estar resolvido!")
print("\nA correção agora registra os tipos ANTES do SQLAlchemy")
print("garantindo que todas as conexões usem os tipos corretos.")
print("=" * 50)