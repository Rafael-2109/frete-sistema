#!/usr/bin/env python3
"""
Verifica se o último processamento preencheu EmbarqueItems com NF
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.embarques.models import EmbarqueItem, Embarque
from app.faturamento.models import RelatorioFaturamentoImportado, FaturamentoProduto
from app.estoque.models import MovimentacaoEstoque
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_

def main():
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*80)
        print("🔍 VERIFICANDO SE O PROCESSAMENTO PREENCHEU EMBARQUEITEMS COM NF")
        print("="*80)
        
        # 1. Encontrar o horário da última execução (últimas movimentações criadas)
        ultima_mov = MovimentacaoEstoque.query.order_by(
            MovimentacaoEstoque.created_at.desc()
        ).first()
        
        if not ultima_mov:
            print("❌ Nenhuma movimentação encontrada")
            return
        
        tempo_processamento = ultima_mov.created_at
        tempo_inicio = tempo_processamento - timedelta(minutes=5)  # Janela de 5 minutos
        
        print(f"\n📅 Última execução detectada: {tempo_processamento.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Analisando janela: {tempo_inicio.strftime('%H:%M:%S')} até {tempo_processamento.strftime('%H:%M:%S')}")
        
        # 2. Buscar NFs processadas nesta janela
        nfs_processadas = db.session.query(
            MovimentacaoEstoque.numero_nf.distinct()
        ).filter(
            MovimentacaoEstoque.created_at >= tempo_inicio,
            MovimentacaoEstoque.created_at <= tempo_processamento
        ).all()
        
        nfs_lista = [nf[0] for nf in nfs_processadas if nf[0]]
        print(f"\n📊 NFs processadas nesta execução: {len(nfs_lista)}")
        
        if not nfs_lista:
            print("❌ Nenhuma NF encontrada no período")
            return
        
        # 3. Verificar EmbarqueItems que podem ter sido preenchidos
        print("\n" + "-"*50)
        print("VERIFICANDO PREENCHIMENTO DE EMBARQUEITEMS:")
        print("-"*50)
        
        preenchidos = []
        ja_preenchidos = []
        nao_encontrados = []
        
        for nf_num in nfs_lista[:20]:  # Verificar primeiras 20 NFs
            # Buscar a NF no RelatorioFaturamentoImportado
            nf = RelatorioFaturamentoImportado.query.filter_by(
                numero_nf=nf_num,
                ativo=True
            ).first()
            
            if not nf or not nf.origem:
                continue
            
            # Buscar EmbarqueItem pelo pedido
            item = EmbarqueItem.query.filter_by(pedido=nf.origem).first()
            
            if item:
                if item.nota_fiscal == nf_num:
                    # Verificar se foi preenchido recentemente
                    # Como não temos timestamp no EmbarqueItem, verificamos se o embarque é recente
                    embarque = Embarque.query.get(item.embarque_id)
                    if embarque and embarque.criado_em >= tempo_inicio:
                        preenchidos.append({
                            'nf': nf_num,
                            'pedido': nf.origem,
                            'item_id': item.id,
                            'embarque': embarque.numero,
                            'lote': item.separacao_lote_id
                        })
                    else:
                        ja_preenchidos.append({
                            'nf': nf_num,
                            'pedido': nf.origem,
                            'item_id': item.id,
                            'lote': item.separacao_lote_id
                        })
                elif not item.nota_fiscal:
                    # Item existe mas sem NF - verificar se deveria ter sido preenchido
                    nao_encontrados.append({
                        'nf': nf_num,
                        'pedido': nf.origem,
                        'item_id': item.id,
                        'lote': item.separacao_lote_id,
                        'motivo': 'Item sem NF'
                    })
        
        # 4. Método alternativo: verificar EmbarqueItems com NF que correspondem às NFs processadas
        items_com_nf = EmbarqueItem.query.filter(
            EmbarqueItem.nota_fiscal.in_(nfs_lista)
        ).all()
        
        print(f"\n✅ EmbarqueItems COM estas NFs: {len(items_com_nf)}")
        
        if items_com_nf:
            print("\nPrimeiros 10 EmbarqueItems preenchidos:")
            for item in items_com_nf[:10]:
                embarque = Embarque.query.get(item.embarque_id)
                status_emb = embarque.status if embarque else 'N/A'
                print(f"  → NF {item.nota_fiscal} | Pedido {item.pedido} | Lote {item.separacao_lote_id} | Embarque {embarque.numero if embarque else 'N/A'} ({status_emb})")
        
        # 5. Verificar quantos pedidos das NFs processadas têm EmbarqueItem
        print("\n" + "-"*50)
        print("ANÁLISE DE COBERTURA:")
        print("-"*50)
        
        # Buscar todos os pedidos das NFs processadas
        pedidos_nfs = db.session.query(
            RelatorioFaturamentoImportado.origem.distinct()
        ).filter(
            RelatorioFaturamentoImportado.numero_nf.in_(nfs_lista),
            RelatorioFaturamentoImportado.ativo == True,
            RelatorioFaturamentoImportado.origem.isnot(None)
        ).all()
        
        pedidos_lista = [p[0] for p in pedidos_nfs if p[0]]
        
        # Verificar quantos destes pedidos têm EmbarqueItem
        items_destes_pedidos = EmbarqueItem.query.filter(
            EmbarqueItem.pedido.in_(pedidos_lista)
        ).all()
        
        pedidos_com_item = set(item.pedido for item in items_destes_pedidos)
        pedidos_com_nf = set(item.pedido for item in items_destes_pedidos if item.nota_fiscal)
        
        print(f"\nTotal de pedidos nas NFs processadas: {len(pedidos_lista)}")
        print(f"Pedidos COM EmbarqueItem: {len(pedidos_com_item)}")
        print(f"Pedidos com EmbarqueItem E NF preenchida: {len(pedidos_com_nf)}")
        print(f"Pedidos SEM EmbarqueItem: {len(pedidos_lista) - len(pedidos_com_item)}")
        
        # 6. Verificar se há EmbarqueItems ativos esperando NF
        items_ativos_sem_nf = EmbarqueItem.query.join(
            Embarque
        ).filter(
            Embarque.status == 'ativo',
            EmbarqueItem.status == 'ativo',
            EmbarqueItem.pedido.in_(pedidos_lista),
            or_(
                EmbarqueItem.nota_fiscal.is_(None),
                EmbarqueItem.nota_fiscal == ''
            )
        ).all()
        
        if items_ativos_sem_nf:
            print(f"\n⚠️ {len(items_ativos_sem_nf)} EmbarqueItems ATIVOS sem NF para pedidos que têm NF:")
            for item in items_ativos_sem_nf[:5]:
                print(f"  → Pedido {item.pedido} | Lote {item.separacao_lote_id} | Embarque {item.embarque_id}")
        
        # 7. Conclusão
        print("\n" + "="*80)
        print("📊 RESUMO DO PREENCHIMENTO:")
        print("="*80)
        
        if len(items_com_nf) > 0:
            print(f"\n✅ SIM, {len(items_com_nf)} EmbarqueItems ESTÃO PREENCHIDOS com NFs desta execução")
            print(f"   Isso representa {len(items_com_nf)}/{len(nfs_lista)} das NFs processadas ({len(items_com_nf)*100/len(nfs_lista):.1f}%)")
        else:
            print("\n❌ NÃO foram encontrados EmbarqueItems preenchidos com as NFs desta execução")
        
        if items_ativos_sem_nf:
            print(f"\n⚠️ ATENÇÃO: {len(items_ativos_sem_nf)} EmbarqueItems ativos ainda precisam ser preenchidos")
        
        print("\n" + "="*80)

if __name__ == "__main__":
    main()