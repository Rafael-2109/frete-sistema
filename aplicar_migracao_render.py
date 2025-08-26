#!/usr/bin/env python3
"""
Script para aplicar migração do campo job_id no PostgreSQL do Render
Pode ser executado localmente ou no Render Shell
"""

import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import sys

# Carregar variáveis de ambiente
load_dotenv()

def aplicar_migracao_render():
    # URL do banco do Render
    # Primeiro tenta pegar do ambiente (quando executado no Render)
    # Depois tenta pegar do .env local (para executar remotamente)
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL não encontrada!")
        print("\nOpções:")
        print("1. Execute este script no Render Shell")
        print("2. Ou adicione a DATABASE_URL do Render no seu .env local")
        print("\nPara pegar a URL do Render:")
        print("- Vá no Dashboard do Render")
        print("- Clique no seu Database")
        print("- Copie a 'External Database URL'")
        print("- Cole no .env como: DATABASE_URL_RENDER=postgres://...")
        
        # Tentar URL alternativa
        database_url = os.environ.get('DATABASE_URL_RENDER')
        if not database_url:
            return False
    
    print(f"📂 Conectando ao banco de dados do Render...")
    print(f"   URL: {database_url[:30]}...")  # Mostra só início da URL por segurança
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("\n🔍 Verificando estrutura atual...")
        
        # Verificar se tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'portal_integracoes'
            )
        """)
        
        if not cursor.fetchone()[0]:
            print("⚠️  Tabela portal_integracoes não existe!")
            print("   Execute as migrações do Flask primeiro:")
            print("   No Render Shell: flask db upgrade")
            return False
        
        # Verificar se campo já existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'portal_integracoes' 
                AND column_name = 'job_id'
            )
        """)
        
        campo_existe = cursor.fetchone()[0]
        
        if campo_existe:
            print("✅ Campo job_id já existe na tabela!")
        else:
            print("📝 Adicionando campo job_id...")
            try:
                cursor.execute("""
                    ALTER TABLE portal_integracoes 
                    ADD COLUMN job_id VARCHAR(100)
                """)
                conn.commit()
                print("✅ Campo job_id adicionado com sucesso!")
            except Exception as e:
                print(f"❌ Erro ao adicionar campo: {e}")
                conn.rollback()
                return False
        
        # Criar índice
        print("\n🔧 Criando/verificando índice...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_portal_integracoes_job_id 
                ON portal_integracoes(job_id)
            """)
            conn.commit()
            print("✅ Índice criado/verificado!")
        except Exception as e:
            print(f"⚠️  Aviso ao criar índice: {e}")
            conn.rollback()
        
        # Adicionar comentário
        try:
            cursor.execute("""
                COMMENT ON COLUMN portal_integracoes.job_id IS 
                'ID do job no Redis Queue para processamento assíncrono'
            """)
            conn.commit()
        except:
            pass  # Comentário é opcional
        
        # Atualizar registros com status NULL
        cursor.execute("""
            UPDATE portal_integracoes 
            SET status = 'aguardando' 
            WHERE status IS NULL
        """)
        conn.commit()
        
        # Estatísticas
        print("\n📊 ESTATÍSTICAS DA TABELA:")
        print("-" * 40)
        
        cursor.execute("SELECT COUNT(*) FROM portal_integracoes")
        total = cursor.fetchone()[0]
        print(f"   Total de registros: {total}")
        
        cursor.execute("SELECT COUNT(*) FROM portal_integracoes WHERE job_id IS NOT NULL")
        com_job = cursor.fetchone()[0]
        print(f"   Registros com job_id: {com_job}")
        
        cursor.execute("SELECT COUNT(*) FROM portal_integracoes WHERE status = 'aguardando'")
        aguardando = cursor.fetchone()[0]
        print(f"   Status aguardando: {aguardando}")
        
        cursor.execute("SELECT COUNT(*) FROM portal_integracoes WHERE status = 'enfileirado'")
        enfileirado = cursor.fetchone()[0]
        print(f"   Status enfileirado: {enfileirado}")
        
        cursor.execute("SELECT COUNT(*) FROM portal_integracoes WHERE status = 'processando'")
        processando = cursor.fetchone()[0]
        print(f"   Status processando: {processando}")
        
        cursor.execute("SELECT COUNT(*) FROM portal_integracoes WHERE status = 'erro'")
        erro = cursor.fetchone()[0]
        print(f"   Status erro: {erro}")
        
        # Verificar estrutura final
        print("\n📋 ESTRUTURA FINAL DOS CAMPOS:")
        print("-" * 40)
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'portal_integracoes'
            AND column_name IN ('job_id', 'status', 'protocolo')
            ORDER BY ordinal_position
        """)
        
        for row in cursor.fetchall():
            nullable = "NULL" if row[3] == 'YES' else "NOT NULL"
            print(f"   {row[0]}: {row[1]}({row[2] or ''}) {nullable}")
        
        conn.close()
        
        print("\n" + "=" * 50)
        print("✅ MIGRAÇÃO NO RENDER CONCLUÍDA COM SUCESSO!")
        print("=" * 50)
        print("\n📋 PRÓXIMOS PASSOS NO RENDER:")
        print("1. Adicione a variável REDIS_URL nas Environment Variables")
        print("2. Crie um Background Worker com comando: python worker_atacadao.py")
        print("3. Faça deploy da aplicação")
        print("4. Teste o agendamento assíncrono")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        print("\nDicas:")
        print("1. Verifique se a DATABASE_URL está correta")
        print("2. Se estiver executando localmente, use a External Database URL")
        print("3. Certifique-se de que o IP está liberado no Render")
        return False

if __name__ == "__main__":
    # Se passar --render como argumento, usa URL do Render
    if len(sys.argv) > 1 and sys.argv[1] == '--render':
        # Forçar uso da URL do Render
        render_url = os.environ.get('DATABASE_URL_RENDER')
        if render_url:
            os.environ['DATABASE_URL'] = render_url
            print("🌐 Usando DATABASE_URL_RENDER para conexão remota")
    
    aplicar_migracao_render()