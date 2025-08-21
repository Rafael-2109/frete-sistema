"""
Script para executar o SQL de criação das tabelas do portal
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app, db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def executar_sql():
    """Executa o script SQL para criar as tabelas do portal"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Ler o arquivo SQL
            sql_file = Path(__file__).parent / 'sql' / '001_criar_tabelas_portal.sql'
            
            if not sql_file.exists():
                logger.error(f"Arquivo SQL não encontrado: {sql_file}")
                return False
            
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Executar SQL diretamente
            from sqlalchemy import text
            
            # Dividir em comandos individuais (separados por ;)
            commands = []
            current_command = []
            in_function = False
            
            for line in sql_content.split('\n'):
                # Detectar início/fim de função
                if 'CREATE OR REPLACE FUNCTION' in line or 'CREATE FUNCTION' in line:
                    in_function = True
                elif line.strip() == "$$ language 'plpgsql';":
                    in_function = False
                    current_command.append(line)
                    commands.append('\n'.join(current_command))
                    current_command = []
                    continue
                
                current_command.append(line)
                
                # Se não estiver em função e linha terminar com ;
                if not in_function and line.strip().endswith(';'):
                    commands.append('\n'.join(current_command))
                    current_command = []
            
            # Adicionar último comando se houver
            if current_command:
                commands.append('\n'.join(current_command))
            
            # Executar cada comando
            success_count = 0
            error_count = 0
            
            for i, command in enumerate(commands, 1):
                command = command.strip()
                if not command or command.startswith('--'):
                    continue
                
                try:
                    # Pular comentários puros
                    if all(line.strip().startswith('--') or not line.strip() 
                          for line in command.split('\n')):
                        continue
                    
                    db.session.execute(text(command))
                    success_count += 1
                    
                    # Log de progresso para comandos importantes
                    if 'CREATE TABLE' in command:
                        table_name = command.split('CREATE TABLE IF NOT EXISTS ')[-1].split(' ')[0]
                        logger.info(f"✅ Tabela criada/verificada: {table_name}")
                    elif 'CREATE INDEX' in command:
                        index_name = command.split('CREATE INDEX IF NOT EXISTS ')[-1].split(' ')[0]
                        logger.info(f"📍 Índice criado/verificado: {index_name}")
                    elif 'CREATE TRIGGER' in command:
                        trigger_name = command.split('CREATE TRIGGER ')[-1].split(' ')[0]
                        logger.info(f"⚡ Trigger criado: {trigger_name}")
                    elif 'INSERT INTO' in command:
                        logger.info(f"➕ Dados inseridos")
                        
                except Exception as e:
                    error_count += 1
                    if 'already exists' not in str(e).lower():
                        logger.warning(f"⚠️ Erro no comando {i}: {str(e)[:100]}")
            
            # Commit das alterações
            db.session.commit()
            
            logger.info(f"""
========================================
📊 RESUMO DA EXECUÇÃO
========================================
✅ Comandos executados com sucesso: {success_count}
❌ Comandos com erro: {error_count}
========================================
            """)
            
            # Verificar tabelas criadas
            result = db.session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name LIKE 'portal_%'
                ORDER BY table_name
            """))
            
            tabelas = [row[0] for row in result]
            
            if tabelas:
                logger.info("📋 Tabelas do portal encontradas:")
                for tabela in tabelas:
                    logger.info(f"   - {tabela}")
            else:
                logger.warning("⚠️ Nenhuma tabela do portal encontrada!")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao executar SQL: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    if executar_sql():
        print("\n✅ Script SQL executado com sucesso!")
    else:
        print("\n❌ Erro ao executar script SQL!")
        sys.exit(1)