"""
Script de investigação: Ag. Pagamento e Ag. Item
Objetivo: Descobrir por que contadores estão zerados e filtros não funcionam
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.separacao.models import Separacao
from app.carteira.models import CarteiraPrincipal
from app.pedidos.models import Pedido
from sqlalchemy import distinct, func

app = create_app()

with app.app_context():
    print("="*80)
    print("INVESTIGAÇÃO: Ag. Pagamento e Ag. Item")
    print("="*80)

    # 1. Verificar se existem registros com falta_item=True
    print("\n[1] Verificando registros com falta_item=True na Separacao:")
    itens_falta_item = Separacao.query.filter(
        Separacao.falta_item == True,
        Separacao.sincronizado_nf == False
    ).all()

    print(f"   Total de itens com falta_item=True: {len(itens_falta_item)}")

    if itens_falta_item:
        print("\n   Primeiros 5 registros:")
        for item in itens_falta_item[:5]:
            print(f"   - Lote: {item.separacao_lote_id} | Pedido: {item.num_pedido} | Produto: {item.cod_produto}")
    else:
        print("   ⚠️ NENHUM registro encontrado com falta_item=True!")

    # 2. Verificar lotes únicos com falta_item
    print("\n[2] Lotes únicos com falta_item=True:")
    lotes_falta_item = db.session.query(Separacao.separacao_lote_id).filter(
        Separacao.falta_item == True,
        Separacao.sincronizado_nf == False
    ).distinct().all()

    lotes_falta_item_ids = [r[0] for r in lotes_falta_item]
    print(f"   Total de lotes únicos: {len(lotes_falta_item_ids)}")
    if lotes_falta_item_ids:
        print(f"   Primeiros 5 lotes: {lotes_falta_item_ids[:5]}")

    # 3. Verificar pedidos ANTECIPADOS na CarteiraPrincipal
    print("\n[3] Verificando pedidos com condição de pagamento ANTECIPADO:")
    pedidos_antecipados = db.session.query(
        distinct(CarteiraPrincipal.num_pedido),
        CarteiraPrincipal.cond_pgto_pedido
    ).filter(
        CarteiraPrincipal.cond_pgto_pedido.ilike('%ANTECIPADO%')
    ).all()

    print(f"   Total de pedidos ANTECIPADOS: {len(pedidos_antecipados)}")

    if pedidos_antecipados:
        print("\n   Primeiros 5 pedidos ANTECIPADOS:")
        for num_pedido, cond_pgto in pedidos_antecipados[:5]:
            print(f"   - Pedido: {num_pedido} | Condição: {cond_pgto}")
    else:
        print("   ⚠️ NENHUM pedido com ANTECIPADO encontrado na CarteiraPrincipal!")

    num_pedidos_antecipados = [r[0] for r in pedidos_antecipados if r[0]]

    # 4. Verificar registros com falta_pagamento=True
    print("\n[4] Verificando registros com falta_pagamento=True na Separacao:")
    itens_falta_pagamento = Separacao.query.filter(
        Separacao.falta_pagamento == True,
        Separacao.sincronizado_nf == False
    ).all()

    print(f"   Total de itens com falta_pagamento=True: {len(itens_falta_pagamento)}")

    if itens_falta_pagamento:
        print("\n   Primeiros 5 registros:")
        for item in itens_falta_pagamento[:5]:
            print(f"   - Lote: {item.separacao_lote_id} | Pedido: {item.num_pedido} | Produto: {item.cod_produto}")
    else:
        print("   ⚠️ NENHUM registro encontrado com falta_pagamento=True!")

    # 5. Verificar cruzamento: Pedidos ANTECIPADOS + falta_pagamento=True
    if num_pedidos_antecipados:
        print("\n[5] Cruzando pedidos ANTECIPADOS com falta_pagamento=True:")
        lotes_falta_pgto = Separacao.query.filter(
            Separacao.num_pedido.in_(num_pedidos_antecipados),
            Separacao.falta_pagamento == True,
            Separacao.sincronizado_nf == False
        ).all()

        print(f"   Total de itens com ANTECIPADO + falta_pagamento=True: {len(lotes_falta_pgto)}")

        if lotes_falta_pgto:
            print("\n   Primeiros 5 registros:")
            for item in lotes_falta_pgto[:5]:
                print(f"   - Lote: {item.separacao_lote_id} | Pedido: {item.num_pedido}")
        else:
            print("   ⚠️ NENHUM item ANTECIPADO tem falta_pagamento=True!")
    else:
        print("\n[5] ⚠️ Pulando cruzamento - não há pedidos ANTECIPADOS")

    # 6. Verificar VIEW Pedido para ver se lotes aparecem
    print("\n[6] Verificando se lotes com falta aparecem na VIEW Pedido:")

    if lotes_falta_item_ids:
        pedidos_com_falta_item = Pedido.query.filter(
            Pedido.separacao_lote_id.in_(lotes_falta_item_ids),
            Pedido.nf_cd == False,
            (Pedido.nf.is_(None)) | (Pedido.nf == "")
        ).all()

        print(f"   Pedidos na VIEW com falta_item: {len(pedidos_com_falta_item)}")
        if pedidos_com_falta_item:
            print(f"   Primeiros 3: {[p.num_pedido for p in pedidos_com_falta_item[:3]]}")
    else:
        print("   ⚠️ Não há lotes com falta_item para verificar na VIEW")

    # 7. DIAGNÓSTICO FINAL
    print("\n" + "="*80)
    print("DIAGNÓSTICO:")
    print("="*80)

    problemas = []

    if len(itens_falta_item) == 0:
        problemas.append("❌ Nenhum item com falta_item=True na tabela Separacao")

    if len(itens_falta_pagamento) == 0:
        problemas.append("❌ Nenhum item com falta_pagamento=True na tabela Separacao")

    if len(pedidos_antecipados) == 0:
        problemas.append("❌ Nenhum pedido com condição ANTECIPADO na CarteiraPrincipal")

    if problemas:
        print("\n🔴 PROBLEMAS ENCONTRADOS:")
        for p in problemas:
            print(f"   {p}")
        print("\n💡 CAUSA RAIZ:")
        print("   Os contadores estão zerados porque NÃO EXISTEM dados com essas flags marcadas!")
        print("   A lógica do código está CORRETA, mas as flags não estão sendo setadas.")
        print("\n🔧 PRÓXIMO PASSO:")
        print("   Verificar ONDE e QUANDO essas flags deveriam ser marcadas.")
    else:
        print("\n✅ Dados encontrados! O problema pode estar na query ou na VIEW.")

    print("\n" + "="*80)
