"""
Script para debugar filtro Ag. Item
Simula EXATAMENTE o que acontece em routes.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from sqlalchemy import distinct, func

app = create_app()

with app.app_context():
    print("="*80)
    print("DEBUG: Filtro Ag. Item")
    print("="*80)

    # PASSO 1: Buscar lotes com falta_item (IGUAL routes.py)
    print("\n[PASSO 1] Buscar lotes com falta_item=True na Separacao...")
    lotes_falta_item_ids = [r[0] for r in db.session.query(Separacao.separacao_lote_id).filter(
        Separacao.falta_item == True,
        Separacao.sincronizado_nf == False
    ).distinct().all()]

    print(f"   ✅ Lotes encontrados: {len(lotes_falta_item_ids)}")
    for lote in lotes_falta_item_ids:
        print(f"      - {lote}")

    if not lotes_falta_item_ids:
        print("\n   ⚠️ NENHUM lote com falta_item encontrado!")
        sys.exit(0)

    # PASSO 2: Buscar pedidos na VIEW com esses lotes (IGUAL routes.py)
    print("\n[PASSO 2] Buscar pedidos na VIEW Pedido com esses lotes...")

    # Query base
    query = Pedido.query

    # Aplicar filtro (IGUAL routes.py linhas 280-285)
    query = query.filter(
        Pedido.separacao_lote_id.in_(lotes_falta_item_ids),
        Pedido.nf_cd == False,
        (Pedido.nf.is_(None)) | (Pedido.nf == "")
    )

    pedidos = query.all()

    print(f"   ✅ Pedidos encontrados: {len(pedidos)}")

    if not pedidos:
        print("\n   ⚠️ NENHUM pedido encontrado na VIEW!")
        print("\n   🔍 Investigando por que...")

        # Verificar se os lotes existem na VIEW sem filtros
        print("\n   [DEBUG] Verificando lotes na VIEW SEM filtros...")
        for lote_id in lotes_falta_item_ids:
            pedidos_lote = Pedido.query.filter(
                Pedido.separacao_lote_id == lote_id
            ).all()

            print(f"\n      Lote: {lote_id}")
            print(f"      Total de pedidos: {len(pedidos_lote)}")

            for p in pedidos_lote:
                print(f"         - Pedido: {p.num_pedido}")
                print(f"           Status: {p.status}")
                print(f"           NF: {p.nf}")
                print(f"           NF_CD: {p.nf_cd}")
                print(f"           Data Embarque: {p.data_embarque}")

        sys.exit(0)

    # PASSO 3: Mostrar pedidos encontrados
    print("\n[PASSO 3] Detalhes dos pedidos encontrados:")
    for p in pedidos:
        print(f"\n   Pedido: {p.num_pedido}")
        print(f"      Lote: {p.separacao_lote_id}")
        print(f"      Status: {p.status}")
        print(f"      NF: {p.nf}")
        print(f"      NF_CD: {p.nf_cd}")
        print(f"      Cliente: {p.raz_social_red}")
        print(f"      Cidade: {p.nome_cidade}")
        print(f"      Valor: R$ {p.valor_saldo_total}")

    print("\n" + "="*80)
    print("✅ FILTRO FUNCIONANDO CORRETAMENTE!")
    print("="*80)
