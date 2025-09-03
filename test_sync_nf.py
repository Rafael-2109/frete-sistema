#!/usr/bin/env python
"""
Script de teste rápido para verificar a sincronização
"""
import os
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = '0'

from app import create_app, db

app = create_app()
with app.app_context():
    from app.separacao.models import Separacao
    from app.faturamento.models import RelatorioFaturamentoImportado
    
    # Conta totais
    total_sep = Separacao.query.filter(
        Separacao.numero_nf.isnot(None),
        Separacao.numero_nf != ''
    ).count()
    
    nao_sync = Separacao.query.filter(
        Separacao.numero_nf.isnot(None),
        Separacao.numero_nf != '',
        Separacao.sincronizado_nf == False
    ).count()
    
    sync = Separacao.query.filter(
        Separacao.numero_nf.isnot(None),
        Separacao.numero_nf != '',
        Separacao.sincronizado_nf == True
    ).count()
    
    total_rel = RelatorioFaturamentoImportado.query.filter_by(ativo=True).count()
    
    print(f"Separações com NF: {total_sep}")
    print(f"  - Sincronizadas: {sync}")
    print(f"  - Não sincronizadas: {nao_sync}")
    print(f"Relatórios de faturamento ativos: {total_rel}")
    
    # Testa com 1 registro
    if nao_sync > 0:
        print("\nTestando com 1 registro...")
        sep = Separacao.query.filter(
            Separacao.numero_nf.isnot(None),
            Separacao.numero_nf != '',
            Separacao.sincronizado_nf == False
        ).first()
        
        print(f"  Pedido: {sep.num_pedido}")
        print(f"  NF: {sep.numero_nf}")
        print(f"  CNPJ: {sep.cnpj_cpf}")
        
        rel = RelatorioFaturamentoImportado.query.filter_by(
            numero_nf=sep.numero_nf,
            ativo=True
        ).first()
        
        if rel:
            print(f"  ✓ NF encontrada no relatório")
            print(f"    CNPJ relatório: {rel.cnpj_cliente}")
            
            cnpj_sep = (sep.cnpj_cpf or '').replace('.','').replace('-','').replace('/','').strip()
            cnpj_rel = (rel.cnpj_cliente or '').replace('.','').replace('-','').replace('/','').strip()
            
            if cnpj_sep == cnpj_rel:
                print(f"  ✓ CNPJ corresponde! Seria marcado como sincronizado.")
            else:
                print(f"  ✗ CNPJ divergente")
        else:
            print(f"  ✗ NF não encontrada no relatório")