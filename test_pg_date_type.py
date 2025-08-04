#!/usr/bin/env python3
"""
Script de teste para verificar erro "Unknown PG numeric type: 1082" no Render
Execute este script no Render shell para diagnosticar o problema
"""

import os
import sys

print("=" * 60)
print("TESTE: Unknown PG numeric type: 1082 (DATE)")
print("=" * 60)

# 1. Verificar versões
print("\n1. VERSÕES INSTALADAS:")
print(f"Python: {sys.version}")

try:
    import psycopg2
    print(f"psycopg2: {psycopg2.__version__}")
except ImportError:
    print("psycopg2: NÃO INSTALADO")

try:
    import sqlalchemy
    print(f"SQLAlchemy: {sqlalchemy.__version__}")
except ImportError:
    print("SQLAlchemy: NÃO INSTALADO")

# 2. Testar conexão direta
print("\n2. TESTE DE CONEXÃO DIRETA:")
try:
    import psycopg2
    from psycopg2 import extensions
    
    # Pegar DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL não encontrada!")
        sys.exit(1)
    
    # Conectar
    print(f"Conectando ao banco...")
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    # Testar query com data
    print("\n3. TESTE DE QUERY COM DATA:")
    cur.execute("SELECT CURRENT_DATE")
    result = cur.fetchone()
    print(f"✅ CURRENT_DATE: {result[0]} (tipo: {type(result[0])})")
    
    # Testar query que retorna tipo DATE
    print("\n4. TESTE COM CAMPO DATE DE TABELA:")
    try:
        # Testar com uma tabela que tem campo DATE
        cur.execute("""
            SELECT expedicao 
            FROM carteira_principal 
            WHERE expedicao IS NOT NULL 
            LIMIT 1
        """)
        result = cur.fetchone()
        if result:
            print(f"✅ Campo DATE retornado: {result[0]} (tipo: {type(result[0])})")
        else:
            print("⚠️ Nenhum registro com data encontrado")
    except Exception as e:
        print(f"❌ Erro ao buscar campo DATE: {e}")
    
    # Verificar tipos registrados
    print("\n5. TIPOS REGISTRADOS NO PSYCOPG2:")
    print(f"Tipos conhecidos: {len(extensions.string_types)}")
    
    # Verificar se o tipo 1082 está registrado
    if 1082 in extensions.string_types:
        print("✅ Tipo 1082 (DATE) está registrado")
    else:
        print("❌ Tipo 1082 (DATE) NÃO está registrado")
    
    # Tentar registrar o tipo
    print("\n6. TENTANDO REGISTRAR TIPO DATE:")
    try:
        DATE_OID = 1082
        DATE = psycopg2.extensions.new_type((DATE_OID,), "DATE", psycopg2.extensions.UNICODE)
        psycopg2.extensions.register_type(DATE)
        print("✅ Tipo DATE registrado com sucesso!")
        
        # Testar novamente
        cur.execute("SELECT CURRENT_DATE")
        result = cur.fetchone()
        print(f"✅ Teste após registro: {result[0]}")
        
    except Exception as e:
        print(f"❌ Erro ao registrar tipo: {e}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Erro geral: {e}")
    import traceback
    traceback.print_exc()

# 7. Testar com SQLAlchemy
print("\n7. TESTE COM SQLALCHEMY:")
try:
    from app import create_app, db
    from app.estoque.models import SaldoEstoque
    
    app = create_app()
    
    with app.app_context():
        # Testar query que pode gerar o erro
        print("Executando query de teste...")
        
        # Buscar um produto para teste
        from app.estoque.models import MovimentacaoEstoque
        produto = db.session.query(MovimentacaoEstoque.cod_produto).first()
        
        if produto:
            print(f"Testando com produto: {produto[0]}")
            try:
                resumo = SaldoEstoque.obter_resumo_produto(produto[0], "Produto Teste")
                if resumo:
                    print("✅ Query executada com sucesso!")
                    print(f"   Estoque inicial: {resumo.get('estoque_inicial', 0)}")
                else:
                    print("⚠️ Nenhum resultado retornado")
            except Exception as e:
                print(f"❌ Erro ao executar query: {e}")
                if "Unknown PG numeric type: 1082" in str(e):
                    print("\n🔴 CONFIRMADO: O erro 'Unknown PG numeric type: 1082' está ocorrendo!")
                    print("\nSOLUÇÕES:")
                    print("1. Atualizar psycopg2: pip install --upgrade psycopg2-binary")
                    print("2. Registrar o tipo DATE no início da aplicação")
                    print("3. Usar psycopg2.extras.register_default_json")
        else:
            print("⚠️ Nenhum produto encontrado para teste")
            
except Exception as e:
    print(f"❌ Erro ao testar com SQLAlchemy: {e}")

print("\n" + "=" * 60)
print("FIM DO TESTE")
print("=" * 60)