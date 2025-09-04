#!/usr/bin/env python3
"""
Debug para descobrir por que pedidos não aparecem apesar do contador estar correto
"""

from app import create_app, db
from app.pedidos.models import Pedido
import time

def debug_query():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("DEBUG: LISTA_PEDIDOS QUERY")
        print("=" * 60)
        
        # Simular query de ABERTOS
        print("\n1. CONTANDO PEDIDOS ABERTOS:")
        start = time.time()
        
        count_query = Pedido.query.filter(
            Pedido.cotacao_id.is_(None),
            Pedido.nf_cd == False,
            (Pedido.nf.is_(None)) | (Pedido.nf == ""),
            Pedido.data_embarque.is_(None)
        )
        
        total_count = count_query.count()
        print(f"   Total (count): {total_count}")
        print(f"   Tempo count: {time.time() - start:.2f}s")
        
        # Tentar query.all()
        print("\n2. EXECUTANDO query.all():")
        start = time.time()
        
        try:
            pedidos = count_query.all()
            print(f"   ✅ query.all() retornou: {len(pedidos)} registros")
            print(f"   Tempo query.all(): {time.time() - start:.2f}s")
            
            # Verificar primeiros pedidos
            print("\n3. PRIMEIROS 5 PEDIDOS:")
            for p in pedidos[:5]:
                print(f"   - {p.separacao_lote_id} | {p.num_pedido} | {p.expedicao}")
            
        except Exception as e:
            print(f"   ❌ ERRO em query.all(): {e}")
            import traceback
            traceback.print_exc()
        
        # Testar com LIMIT
        print("\n4. TESTANDO COM LIMIT:")
        start = time.time()
        
        try:
            pedidos_limit = count_query.limit(100).all()
            print(f"   ✅ Com LIMIT 100: {len(pedidos_limit)} registros")
            print(f"   Tempo: {time.time() - start:.2f}s")
        except Exception as e:
            print(f"   ❌ ERRO com LIMIT: {e}")
        
        # Verificar pedidos específicos de hoje
        print("\n5. PEDIDOS DE HOJE (20250904):")
        pedidos_hoje = Pedido.query.filter(
            Pedido.separacao_lote_id.like('%20250904%'),
            Pedido.cotacao_id.is_(None),
            Pedido.nf_cd == False,
            (Pedido.nf.is_(None)) | (Pedido.nf == ""),
            Pedido.data_embarque.is_(None)
        ).all()
        
        print(f"   Pedidos de hoje que são ABERTOS: {len(pedidos_hoje)}")
        for p in pedidos_hoje[:3]:
            print(f"   - {p.separacao_lote_id} | {p.num_pedido}")
        
        # Verificar se é problema de memória/timeout
        print("\n6. TESTE DE PERFORMANCE:")
        
        # Contar total na VIEW
        from sqlalchemy import text
        result = db.session.execute(text("SELECT COUNT(*) FROM pedidos")).fetchone()
        print(f"   Total na VIEW pedidos: {result[0]}")
        
        # Contar ABERTOS via SQL
        result = db.session.execute(text("""
            SELECT COUNT(*) 
            FROM pedidos 
            WHERE cotacao_id IS NULL
              AND nf_cd = false
              AND (nf IS NULL OR nf = '')
              AND data_embarque IS NULL
        """)).fetchone()
        print(f"   ABERTOS via SQL: {result[0]}")
        
        print("\n" + "=" * 60)
        print("DIAGNÓSTICO:")
        if total_count > 0 and len(pedidos) == 0:
            print("❌ PROBLEMA: count() retorna valor mas all() retorna vazio!")
            print("   Possível causa: timeout, limite de memória ou erro no ORM")
        elif len(pedidos) != total_count:
            print(f"⚠️ INCONSISTÊNCIA: count={total_count} mas all={len(pedidos)}")
        else:
            print(f"✅ Query funcionando: {len(pedidos)} pedidos")

if __name__ == "__main__":
    debug_query()