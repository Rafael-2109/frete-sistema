#!/usr/bin/env python3
"""
Script para atualizar o campo status dos Pedidos baseado no status_calculado
Corrige pedidos que têm NF mas ainda estão como COTADO
"""

from app import create_app, db
from app.pedidos.models import Pedido

app = create_app()

with app.app_context():
    print("🔍 Buscando pedidos com status inconsistente...")
    
    # Buscar pedidos que têm NF mas não estão como FATURADO
    pedidos_inconsistentes = Pedido.query.filter(
        Pedido.nf.isnot(None),
        Pedido.nf != "",
        Pedido.status != 'FATURADO'
    ).all()
    
    print(f"📊 Encontrados {len(pedidos_inconsistentes)} pedidos inconsistentes")
    
    contador = 0
    for pedido in pedidos_inconsistentes:
        status_antigo = pedido.status
        status_novo = pedido.status_calculado
        
        if status_antigo != status_novo:
            print(f"  • Pedido {pedido.num_pedido}: '{status_antigo}' → '{status_novo}' (NF: {pedido.nf})")
            pedido.status = status_novo
            contador += 1
    
    if contador > 0:
        db.session.commit()
        print(f"\n✅ {contador} pedidos atualizados com sucesso!")
    else:
        print("\n✅ Nenhum pedido precisou ser atualizado")
    
    # Verificar resultado
    print("\n📊 VERIFICAÇÃO PÓS-ATUALIZAÇÃO:")
    
    # Contar por status
    from sqlalchemy import func
    
    contagem = db.session.query(
        Pedido.status,
        func.count(Pedido.id)
    ).group_by(
        Pedido.status
    ).all()
    
    for status, qtd in contagem:
        print(f"  • {status}: {qtd} pedidos")
    
    # Verificar se ainda há inconsistências
    ainda_inconsistentes = Pedido.query.filter(
        Pedido.nf.isnot(None),
        Pedido.nf != "",
        Pedido.status != 'FATURADO'
    ).count()
    
    if ainda_inconsistentes > 0:
        print(f"\n⚠️ ATENÇÃO: Ainda há {ainda_inconsistentes} pedidos com NF mas sem status FATURADO")
    else:
        print("\n✅ Todos os pedidos estão com status correto!")