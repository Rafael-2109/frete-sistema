"""
Script para investigar inconsistências de status_pedido em itens do mesmo pedido
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from sqlalchemy import func
from collections import defaultdict

app = create_app()

def investigar_status_inconsistente():
    """Busca pedidos com status inconsistente entre seus itens"""
    with app.app_context():
        print("="*100)
        print(" 🔍 INVESTIGAÇÃO DE STATUS INCONSISTENTE")
        print("="*100)
        print()

        # Buscar todos os pedidos com múltiplos status
        print("📊 Buscando pedidos com status inconsistente...")

        # Query: agrupar por num_pedido e contar status diferentes
        query = db.session.query(
            CarteiraPrincipal.num_pedido,
            func.count(func.distinct(CarteiraPrincipal.status_pedido)).label('qtd_status_diferentes')
        ).group_by(
            CarteiraPrincipal.num_pedido
        ).having(
            func.count(func.distinct(CarteiraPrincipal.status_pedido)) > 1
        ).all()

        if not query:
            print("✅ Nenhum pedido com status inconsistente encontrado!")
            return

        print(f"\n⚠️  {len(query)} pedidos com status inconsistente encontrados!\n")
        print("="*100)

        # Analisar cada pedido inconsistente
        for num_pedido, qtd_status in query:
            print(f"\n📦 Pedido: {num_pedido}")
            print("─"*100)

            # Buscar todos os itens deste pedido
            itens = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).all()

            # Agrupar por status
            por_status = defaultdict(list)
            for item in itens:
                por_status[item.status_pedido].append({
                    'cod_produto': item.cod_produto,
                    'qtd_saldo': item.qtd_saldo_produto_pedido,
                    'expedicao': item.expedicao
                })

            # Mostrar resumo
            for status, items in sorted(por_status.items()):
                print(f"\n  🏷️  Status: '{status}' ({len(items)} itens)")
                for i in items[:5]:  # Mostrar apenas 5 primeiros
                    print(f"     - Produto: {i['cod_produto']:<15} Saldo: {i['qtd_saldo']:<10} Expedição: {i['expedicao']}")
                if len(items) > 5:
                    print(f"     ... e mais {len(items) - 5} itens")

        print("\n\n")
        print("="*100)
        print(" 🎯 POSSÍVEIS CAUSAS")
        print("="*100)
        print()
        print("1. **Pedido sendo editado durante sincronização**:")
        print("   - No Odoo, o pedido estava em 'draft' (Cotação)")
        print("   - Algumas linhas foram sincronizadas")
        print("   - Pedido foi confirmado (mudou para 'sale')")
        print("   - Linhas restantes foram sincronizadas com novo status")
        print()
        print("2. **Sincronização incremental não atualizou todos os itens**:")
        print("   - Sistema busca apenas registros alterados recentemente")
        print("   - Se apenas algumas linhas foram editadas, só elas vêm na sincronização")
        print("   - Status do pedido mudou mas linhas antigas não foram atualizadas")
        print()
        print("3. **Cache do Odoo desatualizado**:")
        print("   - Sistema busca pedidos em cache")
        print("   - Algumas linhas vêm com pedido antigo (status draft)")
        print("   - Outras linhas vêm com pedido novo (status sale)")
        print()
        print("="*100)
        print(" 🛠️  SOLUÇÕES")
        print("="*100)
        print()
        print("1. **Forçar sincronização completa (não incremental)**:")
        print("   - Usar modo_incremental=False")
        print("   - Buscar TODOS os pedidos do Odoo, não apenas alterados")
        print()
        print("2. **Adicionar atualização em massa de status por pedido**:")
        print("   - Após sincronizar, verificar se pedido tem status inconsistente")
        print("   - Buscar status correto no Odoo")
        print("   - Atualizar TODOS os itens daquele pedido")
        print()
        print("3. **Script de correção imediata**:")
        print("   - Buscar pedidos inconsistentes")
        print("   - Consultar status atual no Odoo")
        print("   - Atualizar todos os itens com status correto")
        print()

if __name__ == '__main__':
    try:
        investigar_status_inconsistente()
    except Exception as e:
        print(f"\n❌ Erro na investigação: {e}")
        import traceback
        traceback.print_exc()
