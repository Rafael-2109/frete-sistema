#!/usr/bin/env python3
"""
Script para adicionar campos agendamento_confirmado nas tabelas
PreSeparacaoItem e Separacao
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Carregar variáveis de ambiente
load_dotenv()

def adicionar_colunas():
    """Adiciona as colunas agendamento_confirmado nas tabelas"""
    
    # Obter URL do banco de dados
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL não encontrada nas variáveis de ambiente")
        return False
    
    # Criar engine
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Iniciar transação
            trans = conn.begin()
            
            try:
                # Adicionar coluna em pre_separacao_item
                print("📝 Adicionando coluna agendamento_confirmado em pre_separacao_item...")
                conn.execute(text("""
                    ALTER TABLE pre_separacao_item 
                    ADD COLUMN IF NOT EXISTS agendamento_confirmado BOOLEAN DEFAULT FALSE
                """))
                print("✅ Coluna adicionada em pre_separacao_item")
                
                # Adicionar coluna em separacao
                print("📝 Adicionando coluna agendamento_confirmado em separacao...")
                conn.execute(text("""
                    ALTER TABLE separacao 
                    ADD COLUMN IF NOT EXISTS agendamento_confirmado BOOLEAN DEFAULT FALSE
                """))
                print("✅ Coluna adicionada em separacao")
                
                # Confirmar transação
                trans.commit()
                print("\n✅ Todas as alterações foram aplicadas com sucesso!")
                
                # Verificar se as colunas foram criadas
                print("\n🔍 Verificando colunas criadas...")
                
                # Verificar pre_separacao_item
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = 'pre_separacao_item' 
                    AND column_name = 'agendamento_confirmado'
                """))
                row = result.fetchone()
                if row:
                    print(f"✅ pre_separacao_item.agendamento_confirmado: {row[1]} {row[2]} default={row[3]}")
                else:
                    print("⚠️ Coluna não encontrada em pre_separacao_item")
                
                # Verificar separacao
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = 'separacao' 
                    AND column_name = 'agendamento_confirmado'
                """))
                row = result.fetchone()
                if row:
                    print(f"✅ separacao.agendamento_confirmado: {row[1]} {row[2]} default={row[3]}")
                else:
                    print("⚠️ Coluna não encontrada em separacao")
                
                return True
                
            except Exception as e:
                # Reverter em caso de erro
                trans.rollback()
                print(f"❌ Erro ao executar alterações: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco de dados: {e}")
        return False
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("🚀 Iniciando adição de colunas agendamento_confirmado...")
    print("=" * 60)
    
    if adicionar_colunas():
        print("\n✨ Script executado com sucesso!")
    else:
        print("\n❌ Script falhou. Verifique os erros acima.")
        sys.exit(1)