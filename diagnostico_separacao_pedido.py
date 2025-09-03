#!/usr/bin/env python3
"""
Diagnóstico: Por que Separação confirmada não aparece na VIEW Pedido
"""

from app import create_app, db
app = create_app()
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from sqlalchemy import text

def diagnosticar():
    with app.app_context():
        print("=" * 80)
        print("DIAGNÓSTICO: SEPARAÇÃO -> VIEW PEDIDO")
        print("=" * 80)
        
        # 1. Verificar separações existentes
        print("\n1. SEPARAÇÕES NA TABELA 'separacao':")
        print("-" * 40)
        
        # Total de separações
        total_sep = Separacao.query.count()
        print(f"Total de separações: {total_sep}")
        
        # Separações com lote_id
        sep_com_lote = Separacao.query.filter(
            Separacao.separacao_lote_id != None
        ).count()
        print(f"Separações COM separacao_lote_id: {sep_com_lote}")
        
        sep_sem_lote = Separacao.query.filter(
            Separacao.separacao_lote_id == None
        ).count()
        print(f"Separações SEM separacao_lote_id: {sep_sem_lote} ⚠️")
        
        # Distribuição por status
        print("\n2. DISTRIBUIÇÃO POR STATUS:")
        print("-" * 40)
        
        result = db.session.execute(text("""
            SELECT status, COUNT(*) as total, 
                   COUNT(CASE WHEN separacao_lote_id IS NOT NULL THEN 1 END) as com_lote,
                   COUNT(CASE WHEN separacao_lote_id IS NULL THEN 1 END) as sem_lote
            FROM separacao 
            GROUP BY status
            ORDER BY status
        """))
        
        for row in result:
            print(f"Status '{row.status}': Total={row.total}, Com Lote={row.com_lote}, Sem Lote={row.sem_lote}")
            if row.sem_lote > 0:
                print(f"  ⚠️ {row.sem_lote} registros sem lote_id NÃO aparecerão na VIEW!")
        
        # 3. Verificar VIEW pedidos
        print("\n3. PEDIDOS NA VIEW 'pedidos':")
        print("-" * 40)
        
        total_pedidos = Pedido.query.count()
        print(f"Total de pedidos na VIEW: {total_pedidos}")
        
        # Verificar diferença
        print("\n4. ANÁLISE DA DIFERENÇA:")
        print("-" * 40)
        
        if sep_com_lote != total_pedidos:
            print(f"❌ PROBLEMA DETECTADO!")
            print(f"   Separações com lote_id: {sep_com_lote}")
            print(f"   Pedidos na VIEW: {total_pedidos}")
            print(f"   Diferença: {sep_com_lote - total_pedidos} registros não aparecem na VIEW")
            
            # Buscar lotes que não estão na VIEW
            print("\n5. LOTES QUE NÃO APARECEM NA VIEW:")
            print("-" * 40)
            
            result = db.session.execute(text("""
                SELECT DISTINCT s.separacao_lote_id, s.status, s.num_pedido,
                       COUNT(*) as total_itens,
                       MIN(s.criado_em) as criado_em
                FROM separacao s
                WHERE s.separacao_lote_id IS NOT NULL
                  AND s.separacao_lote_id NOT IN (
                      SELECT DISTINCT separacao_lote_id FROM pedidos
                  )
                GROUP BY s.separacao_lote_id, s.status, s.num_pedido
                ORDER BY s.criado_em DESC
                LIMIT 10
            """))
            
            for row in result:
                print(f"Lote: {row.separacao_lote_id}")
                print(f"  Status: {row.status}")
                print(f"  Pedido: {row.num_pedido}")
                print(f"  Itens: {row.total_itens}")
                print(f"  Criado: {row.criado_em}")
                print()
        else:
            print("✅ Todos os registros com lote_id aparecem na VIEW")
        
        # 6. Verificar separações com cotacao_id
        print("\n6. SEPARAÇÕES COM COTAÇÃO:")
        print("-" * 40)
        
        sep_com_cotacao = Separacao.query.filter(
            Separacao.cotacao_id != None
        ).count()
        print(f"Separações com cotacao_id: {sep_com_cotacao}")
        
        # Status das separações com cotação
        result = db.session.execute(text("""
            SELECT status, COUNT(*) as total
            FROM separacao 
            WHERE cotacao_id IS NOT NULL
            GROUP BY status
        """))
        
        print("\nStatus das separações com cotação:")
        for row in result:
            print(f"  {row.status}: {row.total}")
            
        # 7. Exemplo de separação recente
        print("\n7. ÚLTIMA SEPARAÇÃO CRIADA:")
        print("-" * 40)
        
        ultima_sep = Separacao.query.order_by(Separacao.criado_em.desc()).first()
        if ultima_sep:
            print(f"ID: {ultima_sep.id}")
            print(f"Lote ID: {ultima_sep.separacao_lote_id or 'NULL ⚠️'}")
            print(f"Pedido: {ultima_sep.num_pedido}")
            print(f"Status: {ultima_sep.status}")
            print(f"Cotação ID: {ultima_sep.cotacao_id or 'NULL'}")
            print(f"Criado em: {ultima_sep.criado_em}")
            
            # Verificar se está na VIEW
            if ultima_sep.separacao_lote_id:
                pedido = Pedido.query.filter_by(
                    separacao_lote_id=ultima_sep.separacao_lote_id
                ).first()
                if pedido:
                    print(f"✅ Aparece na VIEW com status: {pedido.status}")
                else:
                    print(f"❌ NÃO aparece na VIEW!")
            else:
                print(f"❌ Sem lote_id, NÃO aparecerá na VIEW!")

if __name__ == "__main__":
    diagnosticar()