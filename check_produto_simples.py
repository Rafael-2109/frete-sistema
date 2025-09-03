#!/usr/bin/env python3
"""
Verificação simples do produto 4159301 usando queries SQL diretas
"""

def verificar_produto_simples():
    import sqlite3
    import os
    import psycopg2
    from sqlalchemy import create_engine
    
    # Tentar descobrir o tipo de banco
    if os.path.exists('instance/frete.db'):
        # SQLite
        print("Usando SQLite...")
        conn = sqlite3.connect('instance/frete.db')
        cursor = conn.cursor()
        
        # Verificar CarteiraPrincipal
        cursor.execute("SELECT COUNT(*) FROM carteira_principal WHERE cod_produto = '4159301'")
        count_carteira = cursor.fetchone()[0]
        print(f"CarteiraPrincipal: {count_carteira} registros")
        
        # Verificar CadastroPalletizacao
        cursor.execute("SELECT COUNT(*) FROM cadastro_palletizacao WHERE cod_produto = '4159301'")
        count_pallet = cursor.fetchone()[0]
        print(f"CadastroPalletizacao: {count_pallet} registros")
        
        # Se existir na carteira, mostrar detalhes
        if count_carteira > 0:
            cursor.execute("""
                SELECT num_pedido, nome_produto, qtd_saldo_produto_pedido, ativo 
                FROM carteira_principal 
                WHERE cod_produto = '4159301' 
                LIMIT 5
            """)
            for row in cursor.fetchall():
                print(f"  Pedido: {row[0]}, Produto: {row[1]}, Qtd: {row[2]}, Ativo: {row[3]}")
        
        conn.close()
    else:
        print("Tentando conectar via DATABASE_URL...")
        # Tentar ler DATABASE_URL do ambiente ou arquivo .env
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            engine = create_engine(database_url)
            with engine.connect() as conn:
                # Verificar CarteiraPrincipal
                result = conn.execute("SELECT COUNT(*) FROM carteira_principal WHERE cod_produto = '4159301'")
                count_carteira = result.scalar()
                print(f"CarteiraPrincipal: {count_carteira} registros")
                
                # Verificar CadastroPalletizacao
                result = conn.execute("SELECT COUNT(*) FROM cadastro_palletizacao WHERE cod_produto = '4159301'")
                count_pallet = result.scalar()
                print(f"CadastroPalletizacao: {count_pallet} registros")
        else:
            print("DATABASE_URL não encontrada")

if __name__ == '__main__':
    try:
        verificar_produto_simples()
    except Exception as e:
        print(f"Erro: {e}")
        print("\nTentando método alternativo...")
        
        # Método alternativo: verificar via Flask shell
        print("\nExecute os seguintes comandos no Flask shell:")
        print("flask shell")
        print(">>> from app.carteira.models import CarteiraPrincipal")
        print(">>> from app.producao.models import CadastroPalletizacao")
        print(">>> CarteiraPrincipal.query.filter_by(cod_produto='4159301').count()")
        print(">>> CadastroPalletizacao.query.filter_by(cod_produto='4159301').count()")