#!/usr/bin/env python3
"""
Script para adicionar campo equipe_vendas de forma segura
"""

from app import create_app, db
import sys

def main():
    print("🔧 Iniciando correção do campo equipe_vendas...")
    
    app = create_app()
    with app.app_context():
        try:
            # Verificar se campos já existem
            print("\n1. Verificando campos existentes...")
            
            # Verificar relatorio_faturamento_importado
            try:
                db.engine.execute('SELECT equipe_vendas FROM relatorio_faturamento_importado LIMIT 1')
                print("✅ Campo equipe_vendas já existe em relatorio_faturamento_importado")
            except Exception:
                print("❌ Campo equipe_vendas não existe em relatorio_faturamento_importado")
                print("   Adicionando campo...")
                db.engine.execute('ALTER TABLE relatorio_faturamento_importado ADD COLUMN equipe_vendas VARCHAR(100)')
                print("✅ Campo adicionado com sucesso!")
            
            # Verificar faturamento_produto
            try:
                db.engine.execute('SELECT equipe_vendas FROM faturamento_produto LIMIT 1')
                print("✅ Campo equipe_vendas já existe em faturamento_produto")
            except Exception:
                print("❌ Campo equipe_vendas não existe em faturamento_produto")
                print("   Adicionando campo...")
                db.engine.execute('ALTER TABLE faturamento_produto ADD COLUMN equipe_vendas VARCHAR(100)')
                print("✅ Campo adicionado com sucesso!")
            
            # Verificar resultado final
            print("\n2. Verificação final...")
            result1 = db.engine.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'relatorio_faturamento_importado' AND column_name = 'equipe_vendas'")
            result2 = db.engine.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'faturamento_produto' AND column_name = 'equipe_vendas'")
            
            if result1.fetchone() and result2.fetchone():
                print("✅ SUCESSO: Ambos os campos foram criados corretamente!")
                return True
            else:
                print("❌ ERRO: Alguns campos não foram criados")
                return False
                
        except Exception as e:
            print(f"❌ ERRO GERAL: {e}")
            return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)