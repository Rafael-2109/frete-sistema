#!/usr/bin/env python3
"""
Script de teste para verificar registro de tipos PostgreSQL
"""
import os
import sys

print("=== TESTE DE TIPOS POSTGRESQL ===")

# 1. Tentar importar psycopg2
try:
    import psycopg2
    from psycopg2 import extensions
    print("✅ psycopg2 importado com sucesso")
except Exception as e:
    print(f"❌ Erro ao importar psycopg2: {e}")
    sys.exit(1)

# 2. Verificar tipos registrados
tipos_para_verificar = {
    1082: "DATE",
    1083: "TIME", 
    1114: "TIMESTAMP",
    1184: "TIMESTAMPTZ",
    1182: "DATEARRAY"
}

print("\n📋 Verificando tipos registrados:")
for oid, nome in tipos_para_verificar.items():
    try:
        tipo = extensions.string_types.get(oid)
        if tipo:
            print(f"  ✅ {nome} (OID {oid}): REGISTRADO")
        else:
            print(f"  ❌ {nome} (OID {oid}): NÃO REGISTRADO")
    except Exception as e:
        print(f"  ❌ {nome} (OID {oid}): ERRO - {e}")

# 3. Tentar registrar tipos
print("\n🔧 Tentando registrar tipos...")
try:
    import register_pg_types
    print("✅ Módulo register_pg_types executado")
except Exception as e:
    print(f"❌ Erro ao executar register_pg_types: {e}")

# 4. Verificar novamente após registro
print("\n📋 Verificando tipos após registro:")
for oid, nome in tipos_para_verificar.items():
    try:
        tipo = extensions.string_types.get(oid)
        if tipo:
            print(f"  ✅ {nome} (OID {oid}): REGISTRADO")
        else:
            print(f"  ❌ {nome} (OID {oid}): NÃO REGISTRADO")
    except Exception as e:
        print(f"  ❌ {nome} (OID {oid}): ERRO - {e}")

# 5. Testar conexão se DATABASE_URL existir
if os.getenv('DATABASE_URL'):
    print("\n🔌 Testando conexão com banco...")
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        # Testar query com DATE
        cur.execute("SELECT CURRENT_DATE as data, pg_typeof(CURRENT_DATE) as tipo")
        resultado = cur.fetchone()
        print(f"✅ Query executada: data={resultado[0]}, tipo={resultado[1]}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
else:
    print("\n⚠️ DATABASE_URL não configurada - pulando teste de conexão")

print("\n=== FIM DO TESTE ===")