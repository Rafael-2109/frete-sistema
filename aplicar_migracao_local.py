#!/usr/bin/env python3
"""
Script para aplicar migração do campo job_id localmente
"""

import sqlite3
import os
from datetime import datetime

def aplicar_migracao():
    # Localizar banco de dados
    db_paths = [
        'instance/fretes.db',
        'fretes.db',
        '../instance/fretes.db'
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ Banco de dados não encontrado!")
        print("   Certifique-se de que a aplicação já foi executada ao menos uma vez")
        return False
    
    print(f"📂 Usando banco de dados: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n🔍 Verificando estrutura atual...")
        
        # Verificar se tabela existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='portal_integracoes'
        """)
        
        if not cursor.fetchone():
            print("⚠️  Tabela portal_integracoes não existe ainda")
            print("   Execute a aplicação primeiro para criar as tabelas")
            return False
        
        # Verificar se campo já existe
        cursor.execute("PRAGMA table_info(portal_integracoes)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'job_id' in column_names:
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
        
        conn.close()
        
        print("\n" + "=" * 50)
        print("✅ MIGRAÇÃO LOCAL CONCLUÍDA COM SUCESSO!")
        print("=" * 50)
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. No WSL: sudo service redis start")
        print("2. Terminal 1: python worker_atacadao.py")
        print("3. Terminal 2: python app.py")
        print("4. Testar agendamento assíncrono")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False

if __name__ == "__main__":
    aplicar_migracao()