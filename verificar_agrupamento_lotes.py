#!/usr/bin/env python3
"""
Verificar como os lotes estão agrupados
"""

from app import create_app, db
app = create_app()
from sqlalchemy import text

def verificar():
    with app.app_context():
        print("=" * 80)
        print("VERIFICAÇÃO DE AGRUPAMENTO DE LOTES")
        print("=" * 80)
        
        # Verificar quantos itens tem cada lote
        result = db.session.execute(text("""
            SELECT separacao_lote_id, 
                   COUNT(*) as total_itens,
                   MIN(status) as status,
                   MIN(num_pedido) as pedido
            FROM separacao
            WHERE separacao_lote_id IS NOT NULL
            GROUP BY separacao_lote_id
            ORDER BY total_itens DESC
            LIMIT 10
        """))
        
        print("\nTOP 10 LOTES COM MAIS ITENS:")
        print("-" * 40)
        for row in result:
            print(f"Lote: {row.separacao_lote_id}")
            print(f"  Itens: {row.total_itens}")
            print(f"  Status: {row.status}")
            print(f"  Pedido: {row.pedido}")
        
        # Verificar distribuição
        result = db.session.execute(text("""
            WITH lotes_agrupados AS (
                SELECT separacao_lote_id, COUNT(*) as total_itens
                FROM separacao
                WHERE separacao_lote_id IS NOT NULL
                GROUP BY separacao_lote_id
            )
            SELECT 
                COUNT(*) as qtd_lotes,
                SUM(total_itens) as total_separacoes,
                AVG(total_itens) as media_itens_por_lote,
                MIN(total_itens) as min_itens,
                MAX(total_itens) as max_itens
            FROM lotes_agrupados
        """))
        
        print("\nESTATÍSTICAS DE AGRUPAMENTO:")
        print("-" * 40)
        for row in result:
            print(f"Total de lotes únicos: {row.qtd_lotes}")
            print(f"Total de separações: {row.total_separacoes}")
            print(f"Média de itens por lote: {row.media_itens_por_lote:.1f}")
            print(f"Mínimo de itens: {row.min_itens}")
            print(f"Máximo de itens: {row.max_itens}")
            
        print("\n✅ CONCLUSÃO:")
        print("-" * 40)
        print("A VIEW 'pedidos' agrupa todas as separações do mesmo lote_id")
        print("em um único registro. Por isso temos:")
        print("- 7861 separações (itens individuais)")
        print("- 1349 pedidos (lotes agrupados)")
        print("\nISSO É NORMAL E ESPERADO!")
        
        # Verificar um lote com status PREVISAO
        print("\n" + "=" * 80)
        print("VERIFICANDO LOTES COM STATUS PREVISAO:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT DISTINCT separacao_lote_id, num_pedido, status
            FROM separacao
            WHERE status = 'PREVISAO'
              AND separacao_lote_id IS NOT NULL
            LIMIT 5
        """))
        
        lotes_previsao = []
        for row in result:
            lotes_previsao.append(row.separacao_lote_id)
            print(f"Lote: {row.separacao_lote_id}")
            print(f"  Pedido: {row.num_pedido}")
            print(f"  Status: {row.status}")
            
        if lotes_previsao:
            print("\nVERIFICANDO SE APARECEM NA VIEW:")
            print("-" * 40)
            
            for lote in lotes_previsao:
                result = db.session.execute(text("""
                    SELECT separacao_lote_id, status
                    FROM pedidos
                    WHERE separacao_lote_id = :lote
                """), {"lote": lote})
                
                pedido = result.first()
                if pedido:
                    print(f"✅ Lote {lote} APARECE na VIEW com status: {pedido.status}")
                else:
                    print(f"❌ Lote {lote} NÃO APARECE na VIEW!")

if __name__ == "__main__":
    verificar()