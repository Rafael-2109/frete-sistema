"""
Script para marcar alguns itens com falta_item=True para teste
Data: 23/10/2025
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.separacao.models import Separacao

app = create_app()

with app.app_context():
    print("="*80)
    print("TESTE: Marcar itens com falta_item=True")
    print("="*80)

    # Buscar algumas separações para marcar
    print("\n[1] Buscando separações para teste...")
    separacoes = Separacao.query.filter(
        Separacao.sincronizado_nf == False,
        Separacao.falta_item == False
    ).limit(5).all()

    if not separacoes:
        print("   ⚠️ Nenhuma separação disponível para teste")
        sys.exit(0)

    print(f"   ✅ Encontradas {len(separacoes)} separações disponíveis")
    print("\n   Separações que serão marcadas:")
    for sep in separacoes:
        print(f"   - ID: {sep.id} | Lote: {sep.separacao_lote_id} | Pedido: {sep.num_pedido} | Produto: {sep.cod_produto}")

    # Confirmar
    resposta = input("\n   Marcar essas separações com falta_item=True? (S/n): ").strip().upper()

    if resposta not in ['S', 'SIM', '']:
        print("\n❌ Operação cancelada")
        sys.exit(0)

    # Marcar
    print("\n[2] Marcando separações...")
    for sep in separacoes:
        sep.falta_item = True

    db.session.commit()

    print(f"   ✅ {len(separacoes)} separações marcadas com falta_item=True")

    # Verificar contador
    print("\n[3] Verificando contador...")
    total_falta_item = Separacao.query.filter(
        Separacao.falta_item == True,
        Separacao.sincronizado_nf == False
    ).count()

    print(f"   ✅ Total de itens com falta_item=True: {total_falta_item}")

    # Lotes únicos
    lotes = db.session.query(Separacao.separacao_lote_id).filter(
        Separacao.falta_item == True,
        Separacao.sincronizado_nf == False
    ).distinct().all()

    print(f"   ✅ Total de lotes únicos: {len(lotes)}")

    print("\n" + "="*80)
    print("✅ TESTE CONCLUÍDO!")
    print("   Agora teste o filtro 'Ag. Item' na interface web")
    print("="*80)
