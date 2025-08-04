#!/usr/bin/env python3
"""
Debug do filtro de NFs pendentes
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.faturamento.models import RelatorioFaturamentoImportado, FaturamentoProduto
from app.estoque.models import MovimentacaoEstoque

app = create_app()
with app.app_context():
    print("\n=== DEBUG NFS PENDENTES ===\n")
    
    # Total de NFs ativas
    total_ativas = RelatorioFaturamentoImportado.query.filter_by(ativo=True).count()
    print(f"Total de NFs ativas: {total_ativas}")
    
    # NFs que têm produtos
    nfs_com_produtos = db.session.query(
        FaturamentoProduto.numero_nf
    ).distinct().subquery()
    
    nfs_com_produtos_count = db.session.query(nfs_com_produtos.c.numero_nf).count()
    print(f"NFs com produtos: {nfs_com_produtos_count}")
    
    # NFs ativas E com produtos  
    nfs_ativas_com_produtos = RelatorioFaturamentoImportado.query.filter(
        RelatorioFaturamentoImportado.ativo == True,
        RelatorioFaturamentoImportado.numero_nf.in_(
            db.session.query(nfs_com_produtos.c.numero_nf)
        )
    ).count()
    print(f"NFs ativas E com produtos: {nfs_ativas_com_produtos}")
    
    # Verificar NF 137723 especificamente
    print("\n--- NF 137723 ---")
    nf_137723 = RelatorioFaturamentoImportado.query.filter_by(numero_nf='137723').first()
    if nf_137723:
        print(f"Ativa: {nf_137723.ativo}")
        
        produtos_137723 = FaturamentoProduto.query.filter_by(numero_nf='137723').count()
        print(f"Produtos: {produtos_137723}")
        
        movs_137723 = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.observacao.like('%NF 137723%')
        ).count()
        print(f"Movimentações: {movs_137723}")
        
        # Está na lista de NFs com produtos?
        tem_produtos = db.session.query(nfs_com_produtos.c.numero_nf).filter(
            nfs_com_produtos.c.numero_nf == '137723'
        ).first()
        print(f"Está na subquery de NFs com produtos: {'SIM' if tem_produtos else 'NÃO'}")
    
    # Listar algumas NFs que estão sendo filtradas
    print("\n--- Primeiras 10 NFs ativas SEM produtos ---")
    nfs_sem_produtos = RelatorioFaturamentoImportado.query.filter(
        RelatorioFaturamentoImportado.ativo == True,
        ~RelatorioFaturamentoImportado.numero_nf.in_(
            db.session.query(nfs_com_produtos.c.numero_nf)
        )
    ).limit(10).all()
    
    for nf in nfs_sem_produtos:
        print(f"  NF {nf.numero_nf} - Pedido: {nf.origem}")