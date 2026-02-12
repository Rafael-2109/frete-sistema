"""
Script de Teste de Performance - Batch vs Individual Queries
=============================================================

OBJETIVO:
    Comparar desempenho de 2 abordagens para buscar product_ids:

    ABORDAGEM 1: Buscar TODOS os movimentos primeiro (batch completo)
    ABORDAGEM 2: Buscar movimentos individualmente + batch parcial

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import sys
import os
import time
from typing import List, Dict, Set

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_utc_naive
from datetime import datetime, timedelta

print("=" * 80)
print("🧪 TESTE DE PERFORMANCE - BATCH QUERIES")
print("=" * 80)

# Inicializar app
app = create_app()

with app.app_context():
    # Conectar ao Odoo
    odoo = get_odoo_connection()

    # Buscar amostra real de pickings (últimos 7 dias)
    data_inicio = (agora_utc_naive() - timedelta(days=7)).strftime('%Y-%m-%d')

    print(f"\n📅 Buscando pickings desde {data_inicio}...")

    filtros = [
        ['picking_type_code', '=', 'incoming'],
        ['state', '=', 'done'],
        ['date_done', '>=', data_inicio]
    ]

    pickings = odoo.execute_kw(
        'stock.picking',
        'search_read',
        [filtros],
        {'fields': ['id', 'name', 'partner_id', 'move_ids_without_package'], 'limit': 50}
    )

    # Filtrar /DEV/ (teste do filtro também)
    pickings_originais = len(pickings)
    pickings = [p for p in pickings if '/DEV/' not in p.get('name', '')]
    pickings_filtrados = len(pickings)

    print(f"✅ Pickings encontrados: {pickings_originais}")
    print(f"🔍 Pickings após filtro /DEV/: {pickings_filtrados}")
    print(f"⏭️  Pickings ignorados: {pickings_originais - pickings_filtrados}")

    if not pickings:
        print("❌ Nenhum picking para testar!")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("🏁 ABORDAGEM 1: BUSCAR TODOS OS MOVIMENTOS PRIMEIRO (BATCH COMPLETO)")
    print("=" * 80)

    inicio_abordagem1 = time.time()

    # 1. Buscar TODOS os movimentos de UMA VEZ
    print("\n1️⃣ Buscando TODOS os movimentos de uma vez...")
    picking_ids = [p['id'] for p in pickings]

    inicio_movimentos_batch = time.time()
    movimentos_todos = odoo.execute_kw(
        'stock.move',
        'search_read',
        [[['picking_id', 'in', picking_ids]]],
        {'fields': ['id', 'picking_id', 'product_id']}
    )
    tempo_movimentos_batch = time.time() - inicio_movimentos_batch

    print(f"   ✅ Movimentos encontrados: {len(movimentos_todos)}")
    print(f"   ⏱️  Tempo: {tempo_movimentos_batch:.3f}s")

    # 2. Coletar product_ids únicos
    product_ids_set = set()
    for mov in movimentos_todos:
        if mov.get('product_id'):
            product_ids_set.add(mov['product_id'][0])

    print(f"   📦 Produtos únicos: {len(product_ids_set)}")

    # 3. Buscar códigos em BATCH
    print("\n2️⃣ Buscando códigos de produtos em batch...")
    inicio_codigos_batch = time.time()

    codigos_result = odoo.execute_kw(
        'product.product',
        'read',
        [list(product_ids_set)],
        {'fields': ['default_code']}
    )
    tempo_codigos_batch = time.time() - inicio_codigos_batch

    codigos_cache_1 = {r['id']: r.get('default_code') for r in codigos_result}
    print(f"   ✅ Códigos buscados: {len(codigos_cache_1)}")
    print(f"   ⏱️  Tempo: {tempo_codigos_batch:.3f}s")

    tempo_total_abordagem1 = time.time() - inicio_abordagem1

    print(f"\n⏱️  TEMPO TOTAL ABORDAGEM 1: {tempo_total_abordagem1:.3f}s")
    print(f"   - Buscar movimentos: {tempo_movimentos_batch:.3f}s")
    print(f"   - Buscar códigos: {tempo_codigos_batch:.3f}s")

    # =========================================================================

    print("\n" + "=" * 80)
    print("🏁 ABORDAGEM 2: BUSCAR MOVIMENTOS INDIVIDUALMENTE (BATCH PARCIAL)")
    print("=" * 80)

    inicio_abordagem2 = time.time()

    # 1. Buscar movimentos picking por picking (como no código atual)
    print("\n1️⃣ Buscando movimentos individualmente...")
    inicio_movimentos_individual = time.time()

    product_ids_set_2 = set()
    total_movimentos = 0
    queries_movimentos = 0

    for picking in pickings:
        picking_id = picking['id']

        # Query individual (como no código atual)
        movimentos = odoo.execute_kw(
            'stock.move',
            'search_read',
            [[['picking_id', '=', picking_id]]],
            {'fields': ['id', 'picking_id', 'product_id']}
        )
        queries_movimentos += 1
        total_movimentos += len(movimentos)

        for mov in movimentos:
            if mov.get('product_id'):
                product_ids_set_2.add(mov['product_id'][0])

    tempo_movimentos_individual = time.time() - inicio_movimentos_individual

    print(f"   ✅ Movimentos encontrados: {total_movimentos}")
    print(f"   🔄 Queries executadas: {queries_movimentos}")
    print(f"   ⏱️  Tempo: {tempo_movimentos_individual:.3f}s")
    print(f"   📦 Produtos únicos: {len(product_ids_set_2)}")

    # 2. Buscar códigos em BATCH (igual à abordagem 1)
    print("\n2️⃣ Buscando códigos de produtos em batch...")
    inicio_codigos_batch2 = time.time()

    codigos_result2 = odoo.execute_kw(
        'product.product',
        'read',
        [list(product_ids_set_2)],
        {'fields': ['default_code']}
    )
    tempo_codigos_batch2 = time.time() - inicio_codigos_batch2

    codigos_cache_2 = {r['id']: r.get('default_code') for r in codigos_result2}
    print(f"   ✅ Códigos buscados: {len(codigos_cache_2)}")
    print(f"   ⏱️  Tempo: {tempo_codigos_batch2:.3f}s")

    tempo_total_abordagem2 = time.time() - inicio_abordagem2

    print(f"\n⏱️  TEMPO TOTAL ABORDAGEM 2: {tempo_total_abordagem2:.3f}s")
    print(f"   - Buscar movimentos: {tempo_movimentos_individual:.3f}s ({queries_movimentos} queries)")
    print(f"   - Buscar códigos: {tempo_codigos_batch2:.3f}s")

    # =========================================================================

    print("\n" + "=" * 80)
    print("📊 ANÁLISE COMPARATIVA")
    print("=" * 80)

    diferenca = tempo_total_abordagem2 - tempo_total_abordagem1
    percentual = (diferenca / tempo_total_abordagem2) * 100

    print(f"\n⏱️  Abordagem 1 (Batch Completo):   {tempo_total_abordagem1:.3f}s")
    print(f"⏱️  Abordagem 2 (Batch Parcial):    {tempo_total_abordagem2:.3f}s")
    print(f"⚡ Diferença:                      {abs(diferenca):.3f}s ({abs(percentual):.1f}%)")

    if diferenca > 0:
        print(f"\n🏆 VENCEDOR: Abordagem 1 (Batch Completo)")
        print(f"   ✅ {percentual:.1f}% mais rápida")
        print(f"   📈 Ganho em escala: Com 100 pickings, economiza ~{diferenca * 2:.1f}s")
    else:
        print(f"\n🏆 VENCEDOR: Abordagem 2 (Batch Parcial)")
        print(f"   ✅ {abs(percentual):.1f}% mais rápida")
        print(f"   📈 Ganho em escala: Com 100 pickings, economiza ~{abs(diferenca) * 2:.1f}s")

    # =========================================================================

    print("\n" + "=" * 80)
    print("🔍 DETALHAMENTO DE QUERIES")
    print("=" * 80)

    print("\n📊 ABORDAGEM 1 (Batch Completo):")
    print(f"   - 1 query para buscar TODOS os movimentos")
    print(f"   - 1 query para buscar TODOS os códigos")
    print(f"   - TOTAL: 2 queries")

    print(f"\n📊 ABORDAGEM 2 (Batch Parcial):")
    print(f"   - {queries_movimentos} queries para buscar movimentos (1 por picking)")
    print(f"   - 1 query para buscar TODOS os códigos")
    print(f"   - TOTAL: {queries_movimentos + 1} queries")

    print("\n" + "=" * 80)
    print("💡 RECOMENDAÇÃO")
    print("=" * 80)

    if diferenca > 0.5:  # Se ganho > 0.5s
        print("\n✅ Usar ABORDAGEM 1 (Batch Completo)")
        print("   Motivo: Ganho significativo de performance")
        print("   Implementação: Buscar TODOS os movimentos com picking_id IN (...)")
    elif diferenca < -0.5:
        print("\n✅ Usar ABORDAGEM 2 (Batch Parcial)")
        print("   Motivo: Melhor performance com queries individuais")
        print("   Implementação: Manter busca individual de movimentos")
    else:
        print("\n⚖️  Desempenho EQUIVALENTE")
        print("   Motivo: Diferença < 0.5s")
        print("   Recomendação: Usar ABORDAGEM 1 por ser mais escalável")

print("\n" + "=" * 80)
print("✅ TESTE CONCLUÍDO")
print("=" * 80)
