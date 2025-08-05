#!/usr/bin/env python3
"""
Script de teste para verificar se o erro PG 1082 foi resolvido
"""
import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Forçar registro de tipos PostgreSQL ANTES de tudo
import register_pg_types

# Agora importar o app
from app import create_app, db
from app.estoque.models import SaldoEstoque

def test_pg1082_fix():
    """Testa se o erro PG 1082 foi resolvido"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("TESTE DE CORREÇÃO DO ERRO PG 1082")
        print("="*60)
        
        # Testar produtos que estavam dando erro
        test_products = [
            ('4860112', 'Produto Teste 1'),
            ('4759598', 'Produto Teste 2'),
            ('4360114', 'Produto Teste 3')
        ]
        
        for cod_produto, nome_produto in test_products:
            print(f"\n🔍 Testando produto: {cod_produto}")
            try:
                # Tentar obter resumo do produto (onde ocorria o erro)
                resumo = SaldoEstoque.obter_resumo_produto(cod_produto, nome_produto)
                
                if resumo:
                    print(f"✅ Sucesso! Dados obtidos:")
                    print(f"   - Estoque inicial: {resumo.get('estoque_inicial', 0)}")
                    print(f"   - Status ruptura: {resumo.get('status_ruptura', 'OK')}")
                    print(f"   - Projeções: {len(resumo.get('projecao_29_dias', []))} dias")
                else:
                    print(f"⚠️ Nenhum dado retornado (produto pode não existir)")
                    
            except Exception as e:
                if "1082" in str(e):
                    print(f"❌ ERRO PG 1082 ainda presente: {e}")
                else:
                    print(f"❌ Erro diferente: {e}")
        
        # Testar query direta no cache
        print("\n" + "-"*60)
        print("TESTE DIRETO NA TABELA DE CACHE")
        print("-"*60)
        
        try:
            from sqlalchemy import text
            
            # Query com TO_CHAR para evitar erro
            result = db.session.execute(text("""
                SELECT 
                    cod_produto,
                    TO_CHAR(data_projecao, 'YYYY-MM-DD') as data_str,
                    dia_offset,
                    estoque_inicial
                FROM projecao_estoque_cache
                WHERE cod_produto = :cod
                LIMIT 5
            """), {'cod': '4860112'})
            
            rows = result.fetchall()
            if rows:
                print("✅ Query com TO_CHAR funcionou!")
                for row in rows:
                    print(f"   Dia {row[2]}: {row[1]} - Estoque: {row[3]}")
            else:
                print("⚠️ Nenhum dado no cache de projeção")
                
        except Exception as e:
            if "1082" in str(e):
                print(f"❌ Erro PG 1082 na query direta: {e}")
            else:
                print(f"❌ Erro na query: {e}")
        
        print("\n" + "="*60)
        print("FIM DO TESTE")
        print("="*60)

if __name__ == "__main__":
    test_pg1082_fix()