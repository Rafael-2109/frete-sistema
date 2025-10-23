"""
Script para atualizar falta_pagamento em Separacoes existentes
Data: 23/10/2025

OBJETIVO:
- Atualizar separações existentes que são de pedidos ANTECIPADOS
- Marcar falta_pagamento=True onde aplicável
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.separacao.models import Separacao
from app.carteira.models import CarteiraPrincipal
from sqlalchemy import distinct

app = create_app()

with app.app_context():
    print("="*80)
    print("ATUALIZAÇÃO: falta_pagamento em Separacoes existentes")
    print("="*80)

    # 1. Buscar todos os pedidos ANTECIPADOS na CarteiraPrincipal
    print("\n[1] Buscando pedidos com condição ANTECIPADO...")
    pedidos_antecipados = db.session.query(
        distinct(CarteiraPrincipal.num_pedido)
    ).filter(
        CarteiraPrincipal.cond_pgto_pedido.ilike('%ANTECIPADO%')
    ).all()

    num_pedidos_antecipados = [r[0] for r in pedidos_antecipados if r[0]]
    print(f"   ✅ Encontrados {len(num_pedidos_antecipados)} pedidos ANTECIPADOS")

    if not num_pedidos_antecipados:
        print("\n⚠️ Nenhum pedido ANTECIPADO encontrado. Script finalizado.")
        sys.exit(0)

    # 2. Buscar separações desses pedidos que ainda não têm falta_pagamento=True
    print("\n[2] Buscando separações para atualizar...")
    separacoes_para_atualizar = Separacao.query.filter(
        Separacao.num_pedido.in_(num_pedidos_antecipados),
        Separacao.falta_pagamento == False,  # Apenas as que ainda são False
        Separacao.sincronizado_nf == False   # Apenas as que não foram faturadas
    ).all()

    print(f"   ✅ Encontradas {len(separacoes_para_atualizar)} separações para atualizar")

    if not separacoes_para_atualizar:
        print("\n✅ Todas as separações já estão atualizadas. Script finalizado.")
        sys.exit(0)

    # 3. Mostrar amostra
    print("\n[3] Amostra de separações que serão atualizadas:")
    for sep in separacoes_para_atualizar[:5]:
        print(f"   - ID: {sep.id} | Lote: {sep.separacao_lote_id} | Pedido: {sep.num_pedido}")

    # 4. Confirmar com usuário
    print("\n" + "="*80)
    print(f"⚠️  ATENÇÃO: {len(separacoes_para_atualizar)} separações serão marcadas com falta_pagamento=True")
    print("="*80)

    resposta = input("\nDeseja continuar? (S/n): ").strip().upper()

    if resposta not in ['S', 'SIM', '']:
        print("\n❌ Operação cancelada pelo usuário.")
        sys.exit(0)

    # 5. Atualizar
    print("\n[4] Atualizando separações...")
    contador = 0
    lotes_afetados = set()

    for sep in separacoes_para_atualizar:
        sep.falta_pagamento = True
        lotes_afetados.add(sep.separacao_lote_id)
        contador += 1

        if contador % 50 == 0:
            print(f"   Processadas: {contador}/{len(separacoes_para_atualizar)}")

    # 6. Commit
    print("\n[5] Salvando alterações no banco...")
    db.session.commit()

    print("\n" + "="*80)
    print("✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")
    print("="*80)
    print(f"   Total de separações atualizadas: {contador}")
    print(f"   Total de lotes afetados: {len(lotes_afetados)}")
    print(f"   Total de pedidos ANTECIPADOS: {len(num_pedidos_antecipados)}")
    print("\n💡 A partir de agora, novas separações serão marcadas automaticamente via event listener.")
    print("="*80)
