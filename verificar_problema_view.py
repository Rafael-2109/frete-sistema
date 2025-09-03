#!/usr/bin/env python3
"""
Verificar por que novos registros ABERTO não aparecem na VIEW
"""

from app import create_app, db
app = create_app()
from sqlalchemy import text
from datetime import datetime, timedelta

def verificar():
    with app.app_context():
        print("=" * 80)
        print("DIAGNÓSTICO: NOVOS REGISTROS ABERTO NÃO APARECEM NA VIEW")
        print("=" * 80)
        
        # 1. Verificar registros ABERTO recentes
        print("\n1. SEPARAÇÕES COM STATUS 'ABERTO' (últimos 30 dias):")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT separacao_lote_id, num_pedido, status, 
                   criado_em, COUNT(*) as itens
            FROM separacao
            WHERE status = 'ABERTO'
              AND separacao_lote_id IS NOT NULL
              AND criado_em >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY separacao_lote_id, num_pedido, status, criado_em
            ORDER BY criado_em DESC
            LIMIT 10
        """))
        
        lotes_aberto_recentes = []
        for row in result:
            lotes_aberto_recentes.append(row.separacao_lote_id)
            print(f"Lote: {row.separacao_lote_id}")
            print(f"  Pedido: {row.num_pedido}")
            print(f"  Status: {row.status}")
            print(f"  Itens: {row.itens}")
            print(f"  Criado: {row.criado_em}")
            print()
        
        # 2. Verificar se aparecem na VIEW
        if lotes_aberto_recentes:
            print("\n2. VERIFICANDO SE APARECEM NA VIEW 'pedidos':")
            print("-" * 40)
            
            aparecem = 0
            nao_aparecem = 0
            
            for lote in lotes_aberto_recentes:
                result = db.session.execute(text("""
                    SELECT separacao_lote_id, status, num_pedido
                    FROM pedidos
                    WHERE separacao_lote_id = :lote
                """), {"lote": lote})
                
                pedido = result.first()
                if pedido:
                    aparecem += 1
                    print(f"✅ Lote {lote}: APARECE na VIEW")
                    print(f"   Status na VIEW: {pedido.status}")
                else:
                    nao_aparecem += 1
                    print(f"❌ Lote {lote}: NÃO APARECE na VIEW!")
            
            print(f"\nRESUMO: {aparecem} aparecem, {nao_aparecem} não aparecem")
        
        # 3. Verificar registros ABERTO antigos
        print("\n3. SEPARAÇÕES COM STATUS 'ABERTO' (mais de 30 dias):")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT separacao_lote_id, num_pedido, status, 
                   criado_em, COUNT(*) as itens
            FROM separacao
            WHERE status = 'ABERTO'
              AND separacao_lote_id IS NOT NULL
              AND criado_em < CURRENT_DATE - INTERVAL '30 days'
            GROUP BY separacao_lote_id, num_pedido, status, criado_em
            ORDER BY criado_em DESC
            LIMIT 5
        """))
        
        lotes_aberto_antigos = []
        for row in result:
            lotes_aberto_antigos.append(row.separacao_lote_id)
            print(f"Lote: {row.separacao_lote_id}")
            print(f"  Pedido: {row.num_pedido}")
            print(f"  Criado: {row.criado_em}")
        
        # 4. Verificar se antigos aparecem
        if lotes_aberto_antigos:
            print("\n4. VERIFICANDO SE ANTIGOS APARECEM NA VIEW:")
            print("-" * 40)
            
            for lote in lotes_aberto_antigos:
                result = db.session.execute(text("""
                    SELECT separacao_lote_id, status
                    FROM pedidos
                    WHERE separacao_lote_id = :lote
                """), {"lote": lote})
                
                pedido = result.first()
                if pedido:
                    print(f"✅ Lote {lote}: APARECE")
                else:
                    print(f"❌ Lote {lote}: NÃO APARECE!")
        
        # 5. Analisar mudanças de PREVISAO para ABERTO
        print("\n5. REGISTROS MUDADOS DE PREVISAO PARA ABERTO (últimos 7 dias):")
        print("-" * 40)
        
        # Não temos histórico, então vamos buscar registros ABERTO recém criados
        result = db.session.execute(text("""
            SELECT separacao_lote_id, num_pedido, status, criado_em
            FROM separacao
            WHERE status = 'ABERTO'
              AND separacao_lote_id IS NOT NULL
              AND criado_em >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY separacao_lote_id, num_pedido, status, criado_em
            ORDER BY criado_em DESC
            LIMIT 5
        """))
        
        for row in result:
            print(f"Lote: {row.separacao_lote_id}")
            print(f"  Pedido: {row.num_pedido}")
            print(f"  Criado: {row.criado_em}")
            
            # Verificar se aparece na VIEW
            result2 = db.session.execute(text("""
                SELECT 1 FROM pedidos WHERE separacao_lote_id = :lote
            """), {"lote": row.separacao_lote_id})
            
            if result2.first():
                print(f"  ✅ APARECE na VIEW")
            else:
                print(f"  ❌ NÃO APARECE na VIEW")
        
        # 6. Verificar a definição atual da VIEW
        print("\n6. DEFINIÇÃO ATUAL DA VIEW:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT definition 
            FROM pg_views 
            WHERE viewname = 'pedidos'
            AND schemaname = 'public'
        """))
        
        view_def = result.first()
        if view_def:
            print("VIEW está definida no banco")
            # Verificar se tem filtro de status
            if 'PREVISAO' in view_def.definition:
                print("⚠️ VIEW tem referência a PREVISAO")
            if 'WHERE' in view_def.definition and 'status' in view_def.definition:
                print("⚠️ VIEW tem filtro de status")
        else:
            print("❌ VIEW 'pedidos' não encontrada!")

if __name__ == "__main__":
    verificar()