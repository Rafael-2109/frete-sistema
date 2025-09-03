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
    erros = 0
    
    for sep in separacoes:
        # Busca no RelatorioFaturamentoImportado
        rel = RelatorioFaturamentoImportado.query.filter_by(
            numero_nf=sep.numero_nf,
            ativo=True
        ).first()
        
        if rel:
            # Limpa CNPJs para comparação
            cnpj_sep = (sep.cnpj_cpf or '').replace('.','').replace('-','').replace('/','').strip()
            cnpj_rel = (rel.cnpj_cliente or '').replace('.','').replace('-','').replace('/','').strip()
            
            if cnpj_sep == cnpj_rel:
                sep.sincronizado_nf = True
                sep.data_sincronizacao = datetime.now()
                sincronizadas += 1
                print(f"✅ {sep.num_pedido} | NF {sep.numero_nf}")
            else:
                erros += 1
    
    if sincronizadas > 0:
        db.session.commit()
        print(f"\n✅ {sincronizadas} sincronizadas com sucesso!")
    
    if erros > 0:
        print(f"⚠️ {erros} com CNPJ divergente")
    
    print("=" * 60)