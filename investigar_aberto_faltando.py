#!/usr/bin/env python3
"""
Investigar por que pedidos ABERTO antigos não aparecem
"""

from app import create_app, db
app = create_app()
from sqlalchemy import text

def investigar():
    with app.app_context():
        print("=" * 80)
        print("INVESTIGAÇÃO: PEDIDOS ABERTO FALTANDO NA VIEW")
        print("=" * 80)
        
        # 1. Contar ABERTO na tabela separacao
        print("\n1. CONTAGEM NA TABELA SEPARACAO:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT COUNT(DISTINCT separacao_lote_id) as lotes_unicos,
                   COUNT(*) as total_registros
            FROM separacao
            WHERE status = 'ABERTO'
              AND separacao_lote_id IS NOT NULL
        """))
        
        row = result.first()
        print(f"Lotes únicos com status ABERTO: {row.lotes_unicos}")
        print(f"Total de registros ABERTO: {row.total_registros}")
        
        # 2. Contar ABERTO na VIEW
        print("\n2. CONTAGEM NA VIEW PEDIDOS:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT COUNT(*) as total
            FROM pedidos
            WHERE status = 'ABERTO'
        """))
        
        row = result.first()
        print(f"Total de pedidos ABERTO na VIEW: {row.total}")
        
        # 3. Buscar lotes ABERTO que NÃO aparecem na VIEW
        print("\n3. LOTES ABERTO QUE NÃO APARECEM NA VIEW:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT DISTINCT s.separacao_lote_id, 
                   s.num_pedido,
                   MIN(s.criado_em) as criado_em,
                   COUNT(*) as qtd_itens,
                   STRING_AGG(DISTINCT s.status, ', ') as status_todos
            FROM separacao s
            WHERE s.separacao_lote_id IS NOT NULL
              AND s.separacao_lote_id IN (
                  -- Lotes que têm pelo menos um registro ABERTO
                  SELECT DISTINCT separacao_lote_id 
                  FROM separacao 
                  WHERE status = 'ABERTO' 
                    AND separacao_lote_id IS NOT NULL
              )
              AND s.separacao_lote_id NOT IN (
                  -- Mas não aparecem na VIEW
                  SELECT separacao_lote_id FROM pedidos
              )
            GROUP BY s.separacao_lote_id, s.num_pedido
            ORDER BY criado_em DESC
            LIMIT 10
        """))
        
        count = 0
        for row in result:
            count += 1
            print(f"Lote: {row.separacao_lote_id}")
            print(f"  Pedido: {row.num_pedido}")
            print(f"  Criado: {row.criado_em}")
            print(f"  Itens: {row.qtd_itens}")
            print(f"  Status no lote: {row.status_todos}")
            print()
        
        if count == 0:
            print("✅ Todos os lotes ABERTO aparecem na VIEW!")
        else:
            print(f"❌ {count} lotes não aparecem na VIEW")
            
        # 4. Investigar se há mistura de status no mesmo lote
        print("\n4. VERIFICANDO MISTURA DE STATUS NO MESMO LOTE:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT separacao_lote_id,
                   STRING_AGG(DISTINCT status, ', ' ORDER BY status) as status_misturados,
                   COUNT(DISTINCT status) as qtd_status_diferentes,
                   COUNT(*) as total_itens
            FROM separacao
            WHERE separacao_lote_id IS NOT NULL
            GROUP BY separacao_lote_id
            HAVING COUNT(DISTINCT status) > 1
            ORDER BY qtd_status_diferentes DESC
            LIMIT 10
        """))
        
        count = 0
        problematicos = []
        for row in result:
            count += 1
            print(f"Lote: {row.separacao_lote_id}")
            print(f"  Status misturados: {row.status_misturados}")
            print(f"  Quantidade de status diferentes: {row.qtd_status_diferentes}")
            print(f"  Total de itens: {row.total_itens}")
            
            # Se tem PREVISAO misturado, é problemático
            if 'PREVISAO' in row.status_misturados:
                problematicos.append(row.separacao_lote_id)
                print(f"  ⚠️ PROBLEMA: Tem PREVISAO misturado com outros status!")
            print()
        
        if count > 0:
            print(f"⚠️ {count} lotes têm status misturados")
            
            if problematicos:
                print(f"\n❌ CAUSA DO PROBLEMA IDENTIFICADA!")
                print(f"   {len(problematicos)} lotes têm PREVISAO misturado com outros status")
                print(f"   A VIEW exclui TODO o lote se QUALQUER item tiver status='PREVISAO'")
                
                # Mostrar exemplo
                print(f"\n   Exemplo de lote problemático: {problematicos[0]}")
                result = db.session.execute(text("""
                    SELECT cod_produto, status, qtd_saldo
                    FROM separacao
                    WHERE separacao_lote_id = :lote
                    ORDER BY status, cod_produto
                    LIMIT 5
                """), {"lote": problematicos[0]})
                
                for row in result:
                    print(f"     - Produto {row.cod_produto}: Status={row.status}, Qtd={row.qtd_saldo}")
        
        # 5. Solução
        print("\n5. ANÁLISE E SOLUÇÃO:")
        print("-" * 40)
        print("O problema é que a VIEW está agrupando por lote_id e excluindo")
        print("TODOS os registros do lote se QUALQUER item tiver status='PREVISAO'.")
        print("\nISSO ESTÁ ERRADO! Deveria excluir apenas os ITENS com PREVISAO,")
        print("não o lote inteiro!")

if __name__ == "__main__":
    investigar()