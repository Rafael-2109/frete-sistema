#!/usr/bin/env python3
"""
Script para debugar por que algumas NFs não geram MovimentacaoEstoque
"""

import sys
from datetime import datetime, timedelta
from run import app
from app import db
from app.embarques.models import Embarque, EmbarqueItem
from app.estoque.models import MovimentacaoEstoque
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado

def debug_nfs_problema():
    """Debug detalhado do problema de NFs sem movimentação"""
    
    with app.app_context():
        print("\n" + "="*80)
        print("DEBUG: POR QUE ALGUMAS NFs NÃO GERAM MOVIMENTAÇÃO?")
        print("="*80)
        
        # 1. Verificar NFs recentes
        data_limite = datetime.now().date() - timedelta(days=2)
        
        print(f"\n📊 Analisando NFs dos últimos 2 dias...")
        
        # NFs em RelatorioFaturamentoImportado
        nfs_relatorio = db.session.query(
            RelatorioFaturamentoImportado.numero_nf,
            RelatorioFaturamentoImportado.origem,
            RelatorioFaturamentoImportado.ativo
        ).filter(
            RelatorioFaturamentoImportado.data_fatura >= data_limite
        ).all()
        
        print(f"Total em RelatorioFaturamentoImportado: {len(nfs_relatorio)}")
        
        # Para cada NF, verificar se tem produtos e movimentação
        nfs_sem_produtos = []
        nfs_sem_movimentacao = []
        nfs_ok = []
        
        for nf_numero, origem, ativo in nfs_relatorio:
            # Verificar se tem produtos
            tem_produtos = FaturamentoProduto.query.filter_by(numero_nf=nf_numero).first()
            
            # Verificar se tem movimentação
            tem_movimentacao = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.observacao.like(f"%NF {nf_numero}%")
            ).first()
            
            if not tem_produtos:
                nfs_sem_produtos.append((nf_numero, origem, ativo))
            elif not tem_movimentacao:
                nfs_sem_movimentacao.append((nf_numero, origem, ativo))
            else:
                nfs_ok.append((nf_numero, origem))
        
        print(f"\n✅ NFs OK (tem produtos e movimentação): {len(nfs_ok)}")
        print(f"⚠️ NFs SEM PRODUTOS em FaturamentoProduto: {len(nfs_sem_produtos)}")
        print(f"❌ NFs SEM MOVIMENTAÇÃO (mas tem produtos): {len(nfs_sem_movimentacao)}")
        
        # Detalhar NFs sem produtos
        if nfs_sem_produtos:
            print("\n" + "-"*60)
            print("NFs SEM PRODUTOS EM FaturamentoProduto:")
            print("-"*60)
            for nf, origem, ativo in nfs_sem_produtos[:10]:
                print(f"NF: {nf} | Origem: {origem} | Ativo: {ativo}")
                
                # Verificar se tem linhas no Odoo
                # Contar produtos que deveriam existir
                produtos_esperados = db.session.execute(
                    """
                    SELECT COUNT(*) 
                    FROM faturamento_produtos 
                    WHERE numero_nf = :nf
                    """,
                    {'nf': nf}
                ).scalar()
                
                print(f"  → Produtos encontrados: {produtos_esperados}")
        
        # Detalhar NFs sem movimentação
        if nfs_sem_movimentacao:
            print("\n" + "-"*60)
            print("NFs COM PRODUTOS MAS SEM MOVIMENTAÇÃO:")
            print("-"*60)
            for nf, origem, ativo in nfs_sem_movimentacao[:10]:
                print(f"\nNF: {nf} | Origem: {origem} | Ativo: {ativo}")
                
                # Contar produtos
                qtd_produtos = FaturamentoProduto.query.filter_by(numero_nf=nf).count()
                print(f"  → Qtd produtos: {qtd_produtos}")
                
                # Verificar se foi pulada por já estar processada
                primeiro_produto = FaturamentoProduto.query.filter_by(numero_nf=nf).first()
                if primeiro_produto:
                    print(f"  → Status NF: {primeiro_produto.status_nf}")
                    print(f"  → Data fatura: {primeiro_produto.data_fatura}")
        
        # Verificar o que o _buscar_nfs_pendentes retornaria
        print("\n" + "="*60)
        print("SIMULANDO _buscar_nfs_pendentes:")
        print("="*60)
        
        # Subquery para NFs que têm produtos
        nfs_com_produtos = db.session.query(FaturamentoProduto.numero_nf).distinct().subquery()
        
        # Buscar todas as NFs ativas com produtos
        nfs_pendentes = (
            RelatorioFaturamentoImportado.query.filter(
                RelatorioFaturamentoImportado.ativo == True,
                RelatorioFaturamentoImportado.numero_nf.in_(db.session.query(nfs_com_produtos.c.numero_nf)),
            )
            .order_by(RelatorioFaturamentoImportado.numero_nf.desc())
            .all()
        )
        
        print(f"Total que seria processado: {len(nfs_pendentes)}")
        
        # Verificar se as NFs sem movimentação estariam na lista
        nfs_pendentes_set = {nf.numero_nf for nf in nfs_pendentes}
        
        print("\nNFs sem movimentação que ESTARIAM na lista de pendentes:")
        for nf, origem, ativo in nfs_sem_movimentacao[:5]:
            if nf in nfs_pendentes_set:
                print(f"  ✅ {nf} - ESTARIA na lista")
            else:
                print(f"  ❌ {nf} - NÃO ESTARIA na lista")

if __name__ == "__main__":
    debug_nfs_problema()