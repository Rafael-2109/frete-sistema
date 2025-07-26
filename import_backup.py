#!/usr/bin/env python3
"""Script para importar backup do PostgreSQL do Render"""
import os
import subprocess
import sys
from app import create_app
from sqlalchemy import text

def import_backup():
    """Importar backup do banco de dados"""
    print("=== IMPORTANDO BACKUP DO RENDER ===")
    
    # Configurar caminho do backup
    backup_path = "backups/render/2025-07-25T14:04Z/sistema_fretes"
    
    if not os.path.exists(backup_path):
        print(f"❌ Backup não encontrado em: {backup_path}")
        return
    
    # Obter configurações do banco
    app = create_app()
    with app.app_context():
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        
        # Extrair componentes da URL
        if 'postgresql://' in db_url:
            # Formato: postgresql://user:pass@host:port/dbname
            parts = db_url.replace('postgresql://', '').split('@')
            user_pass = parts[0].split(':')
            host_port_db = parts[1].split('/')
            host_port = host_port_db[0].split(':')
            
            db_user = user_pass[0]
            db_pass = user_pass[1] if len(user_pass) > 1 else ''
            db_host = host_port[0]
            db_port = host_port[1] if len(host_port) > 1 else '5432'
            db_name = host_port_db[1].split('?')[0]
            
            print(f"📊 Banco: {db_name} em {db_host}:{db_port}")
            
            # Configurar variáveis de ambiente
            env = os.environ.copy()
            env['PGPASSWORD'] = db_pass
            
            # Comando pg_restore
            cmd = [
                'pg_restore',
                '--host', db_host,
                '--port', db_port,
                '--username', db_user,
                '--dbname', db_name,
                '--no-owner',
                '--no-privileges',
                '--clean',
                '--if-exists',
                '--verbose',
                backup_path
            ]
            
            print("🔄 Executando pg_restore...")
            print(f"   Comando: {' '.join(cmd)}")
            
            try:
                # Executar restore
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("✅ Backup importado com sucesso!")
                else:
                    print(f"⚠️ Restore concluído com avisos:")
                    print(result.stderr[:1000])  # Primeiros 1000 caracteres de erro
                    
                # Verificar tabelas
                from app import db
                result = db.session.execute(text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                ))
                count = result.scalar()
                print(f"✅ {count} tabelas no banco de dados")
                
            except Exception as e:
                print(f"❌ Erro ao executar pg_restore: {str(e)}")
                print("💡 Certifique-se que o PostgreSQL client está instalado:")
                print("   sudo apt-get install postgresql-client")
                
        else:
            print("❌ Banco não é PostgreSQL. Este script só funciona com PostgreSQL.")

if __name__ == "__main__":
    import_backup()