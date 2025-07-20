#!/usr/bin/env python3
"""
Script para testar conexão PostgreSQL e identificar problema UTF-8
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def test_conexao_postgresql():
    """Testa conexão PostgreSQL com diferentes configurações"""
    
    print('🔍 INVESTIGAÇÃO: ERRO UTF-8 NAS MIGRAÇÕES')
    print('=' * 60)
    
    # Verificar DATABASE_URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print('❌ DATABASE_URL não encontrada')
        return False
    
    try:
        parsed = urlparse(database_url)
        print(f'Host: {parsed.hostname}')
        database_name = parsed.path[1:] if parsed.path else 'N/A'
        print(f'Database: {database_name}')
        print(f'User: {parsed.username}')
        print()
        
        # TESTE 1: Conexão direta simples
        print('📡 TESTE 1: Conexão direta simples...')
        try:
            conn1 = psycopg2.connect(database_url)
            cursor1 = conn1.cursor()
            cursor1.execute('SELECT version();')
            version = cursor1.fetchone()[0]
            print(f'✅ Conectado: {version[:50]}...')
            cursor1.close()
            conn1.close()
            print('✅ Teste 1 passou!')
        except Exception as e:
            print(f'❌ Teste 1 falhou: {e}')
            print(f'Tipo: {type(e).__name__}')
        
        print()
        
        # TESTE 2: Conexão com UTF-8 explícito
        print('📡 TESTE 2: Conexão com UTF-8 explícito...')
        try:
            conn2 = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=database_name,
                user=parsed.username,
                password=parsed.password,
                client_encoding='utf8'
            )
            cursor2 = conn2.cursor()
            cursor2.execute('SHOW client_encoding;')
            encoding = cursor2.fetchone()[0]
            print(f'✅ Encoding: {encoding}')
            
            # Testar caracteres especiais
            cursor2.execute("SELECT 'Teste com acentuação: ção, ã, é' as teste;")
            result = cursor2.fetchone()[0]
            print(f'✅ Teste acentos: {result}')
            
            cursor2.close()
            conn2.close()
            print('✅ Teste 2 passou!')
        except Exception as e:
            print(f'❌ Teste 2 falhou: {e}')
            print(f'Tipo: {type(e).__name__}')
        
        print()
        
        # TESTE 3: Simular o que o Alembic faz
        print('📡 TESTE 3: Simulando processo Alembic...')
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.pool import NullPool
            
            # Configurar engine como Alembic faz
            engine = create_engine(
                database_url,
                poolclass=NullPool,
                connect_args={'client_encoding': 'utf8'}
            )
            
            # Testar conexão
            with engine.connect() as connection:
                result = connection.execute('SELECT current_database();')
                db_name = result.fetchone()[0]
                print(f'✅ Database atual: {db_name}')
                
                # Testar inspect (usado pelo Alembic)
                from sqlalchemy import inspect
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                print(f'✅ Encontradas {len(tables)} tabelas')
                
            print('✅ Teste 3 passou!')
            
        except Exception as e:
            print(f'❌ Teste 3 falhou: {e}')
            print(f'Tipo: {type(e).__name__}')
            if 'utf-8' in str(e).lower():
                print('🎯 ENCONTRADO! Este é o erro UTF-8!')
                print(f'Detalhes completos: {e}')
        
        print()
        print('📊 RESULTADO DA INVESTIGAÇÃO:')
        print('=' * 60)
        
        return True
        
    except Exception as e:
        print(f'❌ Erro geral: {e}')
        return False

def investigar_migracoes_especificas():
    """Investigar arquivos de migração específicos que podem estar causando problema"""
    
    print('🔍 INVESTIGANDO MIGRAÇÕES ESPECÍFICAS:')
    print('=' * 60)
    
    # Verificar migração da PreSeparacaoItem
    migration_file = 'migrations/versions/76bbd63e3bed_adicionar_tabela_pre_separacao_itens.py'
    
    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f'✅ {migration_file}: OK')
        
        # Verificar se tem caracteres especiais
        if any(ord(c) > 127 for c in content):
            print('⚠️ Contém caracteres não-ASCII')
            for i, c in enumerate(content):
                if ord(c) > 127:
                    print(f'  Posição {i}: {repr(c)} (ord: {ord(c)})')
                    if i > 10:  # Limitar saída
                        break
        else:
            print('✅ Apenas caracteres ASCII')
            
    except Exception as e:
        print(f'❌ Erro: {e}')

if __name__ == "__main__":
    print('🚀 DIAGNÓSTICO COMPLETO DO ERRO UTF-8')
    print('=' * 60)
    
    # Testar conexões
    test_conexao_postgresql()
    
    print()
    
    # Investigar migrações específicas  
    investigar_migracoes_especificas()
    
    print()
    print('🎯 CONCLUSÕES E PRÓXIMOS PASSOS:')
    print('=' * 60)
    print('1. Se Teste 1 e 2 passaram: problema não é na conexão')
    print('2. Se Teste 3 falhou: problema é no SQLAlchemy/Alembic')
    print('3. Se encontrou caracteres especiais: problema na migração')
    print('4. Solução: Usar workaround ou corrigir encoding específico') 