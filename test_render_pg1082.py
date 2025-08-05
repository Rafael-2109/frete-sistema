#!/usr/bin/env python3
"""
Script para testar erro PG 1082 no Render
Execute este no shell do Render para diagnosticar o problema real
"""

import os
import sys

print("=" * 60)
print("TESTE ERRO PG 1082 - DIAGNÓSTICO COMPLETO")
print("=" * 60)

# 1. Verificar ambiente
print("\n1. AMBIENTE:")
print(f"DATABASE_URL existe: {'DATABASE_URL' in os.environ}")
print(f"Python: {sys.version}")

# 2. Testar importação e registro de tipos
print("\n2. TESTE DE IMPORTAÇÃO E REGISTRO:")
try:
    # Tentar importar a configuração de tipos
    from app.utils.pg_types_config import registrar_tipos_postgresql
    print("✅ Módulo pg_types_config importado com sucesso")
except ImportError as e:
    print(f"❌ Erro ao importar pg_types_config: {e}")
    
    # Fallback: registrar manualmente
    print("\n   Tentando registro manual...")
    try:
        import psycopg2
        from psycopg2 import extensions
        
        # Registrar tipos
        extensions.register_type(extensions.new_type((1082,), "DATE", extensions.DATE))
        extensions.register_type(extensions.new_type((1083,), "TIME", extensions.TIME))
        extensions.register_type(extensions.new_type((1114,), "TIMESTAMP", extensions.PYDATETIME))
        extensions.register_type(extensions.new_type((1184,), "TIMESTAMPTZ", extensions.PYDATETIME))
        
        print("   ✅ Tipos registrados manualmente")
    except Exception as e:
        print(f"   ❌ Erro no registro manual: {e}")

# 3. Testar query direta no banco
print("\n3. TESTE DE QUERY DIRETA:")
try:
    import psycopg2
    from psycopg2 import extensions
    
    # Verificar tipos registrados
    print(f"   Tipos registrados: {len(extensions.string_types)}")
    print(f"   Tipo 1082 registrado: {1082 in extensions.string_types}")
    
    # Conectar ao banco
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Teste 1: Query simples com date
        print("\n   3.1. Query simples com DATE:")
        cur.execute("SELECT CURRENT_DATE::date")
        result = cur.fetchone()
        print(f"   ✅ Resultado: {result[0]} (tipo: {type(result[0])})")
        
        # Teste 2: Query na tabela problemática
        print("\n   3.2. Query em projecao_estoque_cache:")
        try:
            cur.execute("""
                SELECT cod_produto, data_projecao, dia_offset 
                FROM projecao_estoque_cache 
                LIMIT 1
            """)
            result = cur.fetchone()
            if result:
                print(f"   ✅ Resultado: {result}")
                print(f"   Tipo do campo data_projecao: {type(result[1])}")
            else:
                print("   ⚠️ Tabela vazia")
        except Exception as e:
            print(f"   ❌ Erro na query: {e}")
            
            # Tentar com CAST
            print("\n   3.3. Tentando com CAST para string:")
            try:
                cur.execute("""
                    SELECT cod_produto, data_projecao::text, dia_offset 
                    FROM projecao_estoque_cache 
                    LIMIT 1
                """)
                result = cur.fetchone()
                if result:
                    print(f"   ✅ Com CAST funcionou: {result}")
            except Exception as e2:
                print(f"   ❌ Erro mesmo com CAST: {e2}")
        
        cur.close()
        conn.close()
except Exception as e:
    print(f"❌ Erro geral no teste direto: {e}")

# 4. Testar com SQLAlchemy
print("\n4. TESTE COM SQLALCHEMY:")
try:
    from app import create_app, db
    app = create_app()
    
    with app.app_context():
        # Verificar se tabela existe
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        if inspector.has_table('projecao_estoque_cache'):
            print("   ✅ Tabela projecao_estoque_cache existe")
            
            # Testar query via SQLAlchemy
            try:
                from app.estoque.models_cache import ProjecaoEstoqueCache
                
                # Query simples
                print("\n   4.1. Query simples:")
                proj = ProjecaoEstoqueCache.query.first()
                if proj:
                    print(f"   ✅ Query funcionou!")
                    print(f"   data_projecao: {proj.data_projecao} (tipo: {type(proj.data_projecao)})")
                else:
                    print("   ⚠️ Tabela vazia")
                    
            except Exception as e:
                print(f"   ❌ Erro na query SQLAlchemy: {e}")
                
                # Se erro for PG 1082, testar solução
                if "1082" in str(e):
                    print("\n   4.2. CONFIRMADO: Erro PG 1082 no SQLAlchemy")
                    print("\n   SOLUÇÃO PROPOSTA:")
                    print("   1. O tipo DATE não está sendo registrado antes da conexão SQLAlchemy")
                    print("   2. Precisamos garantir que pg_types_config seja importado ANTES do db")
        else:
            print("   ❌ Tabela projecao_estoque_cache não existe")
            
except Exception as e:
    print(f"❌ Erro no teste SQLAlchemy: {e}")

# 5. Verificar ordem de importação
print("\n5. VERIFICAÇÃO DE ORDEM DE IMPORTAÇÃO:")
print("   Para corrigir o erro, a ordem deve ser:")
print("   1. Importar pg_types_config")
print("   2. Importar/criar db (SQLAlchemy)")
print("   3. Criar app")

# 6. Solução proposta
print("\n6. SOLUÇÃO DEFINITIVA:")
print("   Editar app/__init__.py para garantir ordem correta:")
print("   - Mover importação de pg_types_config para ANTES de 'db = SQLAlchemy()'")
print("   - Garantir que tipos sejam registrados globalmente")

print("\n" + "=" * 60)
print("FIM DO DIAGNÓSTICO")
print("=" * 60)