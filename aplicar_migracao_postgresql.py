#!/usr/bin/env python3
"""
Script para aplicar migração do campo job_id no PostgreSQL local
"""

import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def aplicar_migracao():
    # Pegar URL do banco
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL não encontrada no .env!")
        print("   Configure a variável DATABASE_URL no arquivo .env")
        return False
    
    print(f"📂 Conectando ao banco de dados...")
    print(f"   URL: {database_url[:30]}...")  # Mostra só início da URL
    
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
            print("⚠️  Tabela portal_integracoes não existe ainda")
            print("   Execute as migrações do Flask primeiro:")
            print("   flask db upgrade")
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
        
        if cursor.fetchone()[0]:
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
        print("\n🔧 Criando índice...")
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
        
        cursor.execute("SELECT COUNT(*) FROM portal_integracoes WHERE status = 'erro'")
        erro = cursor.fetchone()[0]
        print(f"   Status erro: {erro}")
        
        # Verificar estrutura final
        print("\n📋 ESTRUTURA FINAL DOS CAMPOS:")
        print("-" * 40)
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'portal_integracoes'
            AND column_name IN ('job_id', 'status', 'protocolo')
            ORDER BY ordinal_position
        """)
        
        for row in cursor.fetchall():
            print(f"   {row[0]}: {row[1]}({row[2] or ''})")
        
        conn.close()
        
        print("\n" + "=" * 50)
        print("✅ MIGRAÇÃO POSTGRESQL LOCAL CONCLUÍDA!")
        print("=" * 50)
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. No WSL: sudo service redis start")
        print("2. Terminal 1: python worker_atacadao.py")
        print("3. Terminal 2: python app.py")
        print("4. Testar agendamento assíncrono")
        print("\n🎯 TESTE RÁPIDO:")
        print("   - Abra a aplicação")
        print("   - Clique em 'Agendar' em qualquer pedido")
        print("   - Deve aparecer loading assíncrono")
        print("   - Não trava o navegador!")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        print("\nDicas:")
        print("1. Verifique se o PostgreSQL está rodando")
        print("2. Verifique a DATABASE_URL no .env")
        print("3. Formato: postgresql://usuario:senha@localhost/frete_sistema")
        return False

if __name__ == "__main__":
    aplicar_migracao()