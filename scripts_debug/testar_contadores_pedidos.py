"""
Script para testar contadores de Ag. Pagamento e Ag. Item
Simula a lógica usada em app/pedidos/routes.py
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
    print("TESTE: Contadores de Ag. Pagamento e Ag. Item")
    print("="*80)

    # Lógica EXATA do routes.py (linhas 150-205)

    # 1. Ag. Item: Contar lotes com falta_item=True na Separacao
    print("\n[1] Testando contador Ag. Item...")
    try:
        lotes_falta_item = db.session.query(Separacao.separacao_lote_id).filter(
            Separacao.falta_item == True,
            Separacao.sincronizado_nf == False
        ).distinct().subquery()

        contador_ag_item = db.session.query(func.count(distinct(Pedido.separacao_lote_id))).filter(
            Pedido.separacao_lote_id.in_(db.session.query(lotes_falta_item)),
            Pedido.nf_cd == False,
            (Pedido.nf.is_(None)) | (Pedido.nf == "")
        ).scalar() or 0

        lotes_falta_item_ids = [r[0] for r in db.session.query(Separacao.separacao_lote_id).filter(
            Separacao.falta_item == True,
            Separacao.sincronizado_nf == False
        ).distinct().all()]

        print(f"   ✅ Contador Ag. Item: {contador_ag_item}")
        print(f"   📋 Lotes com falta_item: {lotes_falta_item_ids[:5] if lotes_falta_item_ids else 'Nenhum'}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        contador_ag_item = 0
        lotes_falta_item_ids = []

    # 2. Ag. Pagamento: Contar pedidos ANTECIPADOS com falta_pagamento=True
    print("\n[2] Testando contador Ag. Pagamento...")
    try:
        # Buscar pedidos com ANTECIPADO
        num_pedidos_antecipados = [r[0] for r in db.session.query(
            distinct(CarteiraPrincipal.num_pedido)
        ).filter(
            CarteiraPrincipal.cond_pgto_pedido.ilike('%ANTECIPADO%')
        ).all() if r[0]]

        print(f"   📝 Total de pedidos ANTECIPADOS: {len(num_pedidos_antecipados)}")

        if num_pedidos_antecipados:
            lotes_falta_pgto = db.session.query(Separacao.separacao_lote_id).filter(
                Separacao.num_pedido.in_(num_pedidos_antecipados),
                Separacao.falta_pagamento == True,
                Separacao.sincronizado_nf == False
            ).distinct().subquery()

            contador_ag_pagamento = db.session.query(func.count(distinct(Pedido.separacao_lote_id))).filter(
                Pedido.separacao_lote_id.in_(db.session.query(lotes_falta_pgto)),
                Pedido.nf_cd == False,
                (Pedido.nf.is_(None)) | (Pedido.nf == "")
            ).scalar() or 0

            lotes_falta_pagamento_ids = [r[0] for r in db.session.query(Separacao.separacao_lote_id).filter(
                Separacao.num_pedido.in_(num_pedidos_antecipados),
                Separacao.falta_pagamento == True,
                Separacao.sincronizado_nf == False
            ).distinct().all()]

            print(f"   ✅ Contador Ag. Pagamento: {contador_ag_pagamento}")
            print(f"   📋 Lotes com falta_pagamento: {lotes_falta_pagamento_ids[:5]}")
        else:
            contador_ag_pagamento = 0
            lotes_falta_pagamento_ids = []
            print(f"   ⚠️  Nenhum pedido ANTECIPADO encontrado")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        contador_ag_pagamento = 0
        lotes_falta_pagamento_ids = []

    # 3. Verificar se pedidos aparecem na VIEW
    print("\n[3] Verificando pedidos na VIEW Pedido...")

    if lotes_falta_pagamento_ids:
        pedidos_ag_pagamento = Pedido.query.filter(
            Pedido.separacao_lote_id.in_(lotes_falta_pagamento_ids),
            Pedido.nf_cd == False,
            (Pedido.nf.is_(None)) | (Pedido.nf == "")
        ).all()

        print(f"   ✅ Pedidos com Ag. Pagamento na VIEW: {len(pedidos_ag_pagamento)}")
        for p in pedidos_ag_pagamento[:3]:
            print(f"      - Pedido: {p.num_pedido} | Lote: {p.separacao_lote_id} | Status: {p.status}")
    else:
        print(f"   ⚠️  Nenhum lote com falta_pagamento para verificar")

    # 4. Resumo
    print("\n" + "="*80)
    print("RESUMO DOS CONTADORES:")
    print("="*80)
    print(f"   Ag. Item: {contador_ag_item}")
    print(f"   Ag. Pagamento: {contador_ag_pagamento}")
    print("\n✅ Se os contadores estão > 0, a lógica está funcionando!")
    print("="*80)
