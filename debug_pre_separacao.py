#!/usr/bin/env python3
"""Debug script para verificar pré-separações com lote VCD"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.carteira.models import PreSeparacaoItem

app = create_app()

with app.app_context():
    # Buscar todas as pré-separações com lote VCD
    pre_seps = PreSeparacaoItem.query.filter(
        PreSeparacaoItem.separacao_lote_id.like('VCD%')
    ).all()
    
    if not pre_seps:
        print("❌ Nenhuma pré-separação encontrada com lote VCD")
    else:
        print(f"✅ Encontradas {len(pre_seps)} pré-separações com lote VCD")
        
        # Agrupar por lote
        lotes = {}
        for ps in pre_seps:
            if ps.separacao_lote_id not in lotes:
                lotes[ps.separacao_lote_id] = []
            lotes[ps.separacao_lote_id].append(ps)
        
        print(f"\nTotal de lotes VCD: {len(lotes)}")
        
        for lote_id, itens in lotes.items():
            print(f"\n📦 Lote: {lote_id}")
            print(f"   Itens: {len(itens)}")
            print(f"   Pedido: {itens[0].num_pedido if itens else 'N/A'}")
            
            # Verificar status
            status_list = [item.status for item in itens]
            status_unique = set(status_list)
            print(f"   Status: {status_unique}")
            
            if 'CRIADO' not in status_unique and 'RECOMPOSTO' not in status_unique:
                print(f"   ⚠️  AVISO: Lote sem status CRIADO ou RECOMPOSTO!")
            
            # Listar produtos
            for item in itens[:3]:  # Mostrar apenas os 3 primeiros
                print(f"      - {item.cod_produto}: Qtd {item.qtd_selecionada_usuario}, Status: {item.status}")
            
            if len(itens) > 3:
                print(f"      ... e mais {len(itens) - 3} itens")
    
    # Buscar especificamente o lote VCD2519539
    print("\n" + "="*50)
    print("Buscando lote específico: VCD2519539")
    
    lote_especifico = PreSeparacaoItem.query.filter(
        PreSeparacaoItem.separacao_lote_id == 'VCD2519539'
    ).all()
    
    if lote_especifico:
        print(f"✅ Lote VCD2519539 encontrado com {len(lote_especifico)} itens")
        for item in lote_especifico:
            print(f"   - Produto: {item.cod_produto}")
            print(f"     Status: {item.status}")
            print(f"     Quantidade: {item.qtd_selecionada_usuario}")
            print(f"     Pedido: {item.num_pedido}")
    else:
        print("❌ Lote VCD2519539 NÃO encontrado")