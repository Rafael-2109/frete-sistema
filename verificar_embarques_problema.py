#!/usr/bin/env python3
"""
Script para verificar o estado dos EmbarqueItems e MovimentacaoEstoque
Identifica porque algumas NFs não geram MovimentacaoEstoque na primeira sincronização
"""

import sys
from datetime import datetime, timedelta
from run import app
from app import db
from app.embarques.models import Embarque, EmbarqueItem
from app.estoque.models import MovimentacaoEstoque
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado

def verificar_inconsistencias():
    """Verifica NFs que estão em FaturamentoProduto mas não em MovimentacaoEstoque"""
    
    with app.app_context():
        print("\n" + "="*80)
        print("VERIFICAÇÃO DE INCONSISTÊNCIAS DE FATURAMENTO")
        print("="*80)
        
        # 1. Buscar todas as NFs ativas dos últimos 7 dias
        data_limite = datetime.now().date() - timedelta(days=7)
        
        nfs_ativas = db.session.query(RelatorioFaturamentoImportado.numero_nf).filter(
            RelatorioFaturamentoImportado.ativo == True,
            RelatorioFaturamentoImportado.data_fatura >= data_limite
        ).all()
        
        print(f"\n📊 Total de NFs ativas nos últimos 7 dias: {len(nfs_ativas)}")
        
        nfs_sem_movimentacao = []
        nfs_com_movimentacao_sem_lote = []
        nfs_com_movimentacao_com_lote = []
        
        for (nf_numero,) in nfs_ativas:
            # Verificar se tem produtos
            tem_produtos = FaturamentoProduto.query.filter_by(numero_nf=nf_numero).first()
            
            if not tem_produtos:
                continue
                
            # Verificar movimentações
            mov_com_lote = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.observacao.like(f"%NF {nf_numero}%"),
                MovimentacaoEstoque.observacao.like("%lote separação%"),
                ~MovimentacaoEstoque.observacao.like("%Sem Separação%")
            ).first()
            
            mov_sem_lote = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.observacao.like(f"%NF {nf_numero}%"),
                MovimentacaoEstoque.observacao.like("%Sem Separação%")
            ).first()
            
            mov_qualquer = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.observacao.like(f"%NF {nf_numero}%")
            ).first()
            
            if mov_com_lote:
                nfs_com_movimentacao_com_lote.append(nf_numero)
            elif mov_sem_lote:
                nfs_com_movimentacao_sem_lote.append(nf_numero)
            elif not mov_qualquer:
                nfs_sem_movimentacao.append(nf_numero)
        
        print(f"\n✅ NFs COM movimentação COM lote: {len(nfs_com_movimentacao_com_lote)}")
        print(f"⚠️  NFs COM movimentação SEM lote: {len(nfs_com_movimentacao_sem_lote)}")
        print(f"❌ NFs SEM movimentação alguma: {len(nfs_sem_movimentacao)}")
        
        # Detalhar NFs sem movimentação
        if nfs_sem_movimentacao:
            print("\n" + "-"*40)
            print("DETALHES DAS NFs SEM MOVIMENTAÇÃO:")
            print("-"*40)
            
            for nf_numero in nfs_sem_movimentacao[:10]:  # Mostrar até 10
                nf = RelatorioFaturamentoImportado.query.filter_by(numero_nf=nf_numero).first()
                
                # Verificar se tem EmbarqueItem
                embarque_item = EmbarqueItem.query.filter_by(nota_fiscal=nf_numero).first()
                
                print(f"\nNF: {nf_numero}")
                print(f"  - Pedido (origem): {nf.origem if nf else 'N/A'}")
                print(f"  - Data Fatura: {nf.data_fatura if nf else 'N/A'}")
                print(f"  - Cliente: {nf.nome_cliente if nf else 'N/A'}")
                
                if embarque_item:
                    print(f"  - EmbarqueItem encontrado:")
                    print(f"    - Embarque ID: {embarque_item.embarque_id}")
                    print(f"    - Pedido no EmbarqueItem: {embarque_item.pedido}")
                    print(f"    - Lote: {embarque_item.separacao_lote_id}")
                    print(f"    - Erro validação: {embarque_item.erro_validacao}")
                    
                    # Verificar status do embarque
                    embarque = Embarque.query.get(embarque_item.embarque_id)
                    if embarque:
                        print(f"    - Status Embarque: {embarque.status}")
                else:
                    # Buscar por pedido
                    embarque_por_pedido = EmbarqueItem.query.filter_by(pedido=nf.origem).first() if nf else None
                    if embarque_por_pedido:
                        print(f"  - EmbarqueItem por pedido encontrado:")
                        print(f"    - NF no EmbarqueItem: {embarque_por_pedido.nota_fiscal}")
                        print(f"    - Lote: {embarque_por_pedido.separacao_lote_id}")
                        print(f"    - Erro validação: {embarque_por_pedido.erro_validacao}")
        
        # Detalhar NFs com movimentação sem lote
        if nfs_com_movimentacao_sem_lote:
            print("\n" + "-"*40)
            print("NFs COM MOVIMENTAÇÃO 'SEM SEPARAÇÃO':")
            print("-"*40)
            
            for nf_numero in nfs_com_movimentacao_sem_lote[:5]:  # Mostrar até 5
                nf = RelatorioFaturamentoImportado.query.filter_by(numero_nf=nf_numero).first()
                
                # Verificar se agora tem EmbarqueItem disponível
                embarque_item = EmbarqueItem.query.filter_by(pedido=nf.origem).first() if nf else None
                
                print(f"\nNF: {nf_numero}")
                print(f"  - Pedido: {nf.origem if nf else 'N/A'}")
                
                if embarque_item:
                    print(f"  - ⚠️ AGORA tem EmbarqueItem disponível!")
                    print(f"    - NF no item: {embarque_item.nota_fiscal}")
                    print(f"    - Lote: {embarque_item.separacao_lote_id}")
                    print(f"    - Erro: {embarque_item.erro_validacao}")
                    
                    if not embarque_item.nota_fiscal or embarque_item.erro_validacao:
                        print(f"    - 🔄 PODE SER REPROCESSADA na próxima sincronização!")

if __name__ == "__main__":
    verificar_inconsistencias()