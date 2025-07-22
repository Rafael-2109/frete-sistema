#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine, text

def main():
    print("🔧 Corrigindo migration de forma segura...")
    
    # Conectar diretamente ao banco
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL não encontrada")
        return False
    
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Adicionar equipe_vendas se não existir
            try:
                conn.execute(text('ALTER TABLE relatorio_faturamento_importado ADD COLUMN equipe_vendas VARCHAR(100)'))
                print('✅ Campo adicionado em relatorio_faturamento_importado')
            except Exception as e:
                print(f'Campo já existe em relatorio_faturamento_importado: {str(e)[:50]}...')
            
            try:
                conn.execute(text('ALTER TABLE faturamento_produto ADD COLUMN equipe_vendas VARCHAR(100)'))
                print('✅ Campo adicionado em faturamento_produto')
            except Exception as e:
                print(f'Campo já existe em faturamento_produto: {str(e)[:50]}...')
            
            conn.commit()
            print("✅ Campos equipe_vendas adicionados com sucesso!")
            return True
            
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)