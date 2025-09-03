#!/usr/bin/env python
"""
Script simplificado para rodar no Render Shell
Sincroniza campo sincronizado_nf em Separacao
"""

from app import create_app, db
from datetime import datetime

app = create_app()

with app.app_context():
    from app.separacao.models import Separacao
    from app.faturamento.models import RelatorioFaturamentoImportado
    
    print("=" * 60)
    print("SINCRONIZAÇÃO NF - SEPARAÇÃO")
    print("=" * 60)
    
    # Busca separações com NF não sincronizadas
    separacoes = Separacao.query.filter(
        Separacao.numero_nf.isnot(None),
        Separacao.numero_nf != '',
        Separacao.sincronizado_nf == False
    ).all()
    
    print(f"Separações para verificar: {len(separacoes)}")
    
    sincronizadas = 0
    nao_encontradas = 0
    
    for sep in separacoes:
        # NOVA LÓGICA: Busca por numero_nf E origem (num_pedido)
        rel = RelatorioFaturamentoImportado.query.filter_by(
            numero_nf=sep.numero_nf,
            origem=sep.num_pedido  # Compara origem com num_pedido
        ).first()
        
        if rel:
            # Marca como sincronizado (sem validar CNPJ ou ativo)
            sep.sincronizado_nf = True
            sep.data_sincronizacao = datetime.now()
            sincronizadas += 1
            print(f"✅ Pedido {sep.num_pedido} | NF {sep.numero_nf}")
        else:
            nao_encontradas += 1
    
    if sincronizadas > 0:
        db.session.commit()
        print(f"\n✅ {sincronizadas} sincronizadas com sucesso!")
    
    if nao_encontradas > 0:
        print(f"⚠️ {nao_encontradas} não encontradas (NF+Pedido não batem)")
    
    print("=" * 60)