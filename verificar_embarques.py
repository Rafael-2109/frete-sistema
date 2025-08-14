#!/usr/bin/env python3
"""
Verifica EmbarqueItems e NFs vinculadas
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.embarques.models import EmbarqueItem, Embarque
from app.faturamento.models import RelatorioFaturamentoImportado
from sqlalchemy import func

def main():
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*80)
        print("📦 ANÁLISE DE EMBARQUEITEMS E NFs")
        print("="*80)
        
        # 1. Total de EmbarqueItems
        total_items = EmbarqueItem.query.count()
        print(f"\nTotal de EmbarqueItems: {total_items}")
        
        # 2. EmbarqueItems com NF preenchida
        items_com_nf = EmbarqueItem.query.filter(
            EmbarqueItem.nota_fiscal.isnot(None),
            EmbarqueItem.nota_fiscal != ''
        ).count()
        print(f"EmbarqueItems COM NF: {items_com_nf}")
        
        # 3. EmbarqueItems sem NF
        items_sem_nf = EmbarqueItem.query.filter(
            db.or_(
                EmbarqueItem.nota_fiscal.is_(None),
                EmbarqueItem.nota_fiscal == ''
            )
        ).count()
        print(f"EmbarqueItems SEM NF: {items_sem_nf}")
        
        # 4. EmbarqueItems ativos sem NF
        items_ativos_sem_nf = EmbarqueItem.query.join(
            Embarque, EmbarqueItem.embarque_id == Embarque.id
        ).filter(
            Embarque.status == 'ativo',
            EmbarqueItem.status == 'ativo',
            db.or_(
                EmbarqueItem.nota_fiscal.is_(None),
                EmbarqueItem.nota_fiscal == ''
            )
        ).count()
        print(f"EmbarqueItems ATIVOS sem NF: {items_ativos_sem_nf}")
        
        # 5. Verificar algumas NFs específicas
        print("\n" + "-"*50)
        print("VERIFICANDO NFs ESPECÍFICAS:")
        print("-"*50)
        
        # Pegar algumas NFs recentes
        nfs_recentes = RelatorioFaturamentoImportado.query.filter(
            RelatorioFaturamentoImportado.ativo == True
        ).order_by(
            RelatorioFaturamentoImportado.numero_nf.desc()
        ).limit(10).all()
        
        for nf in nfs_recentes:
            # Verificar se esta NF está em algum EmbarqueItem
            item = EmbarqueItem.query.filter_by(nota_fiscal=nf.numero_nf).first()
            if item:
                print(f"✅ NF {nf.numero_nf} (Pedido: {nf.origem}) -> EmbarqueItem ID: {item.id}, Lote: {item.separacao_lote_id}")
            else:
                # Verificar se o pedido tem EmbarqueItem
                item_pedido = EmbarqueItem.query.filter_by(pedido=nf.origem).first()
                if item_pedido:
                    print(f"⚠️  NF {nf.numero_nf} (Pedido: {nf.origem}) -> Pedido tem EmbarqueItem mas SEM NF vinculada")
                else:
                    print(f"❌ NF {nf.numero_nf} (Pedido: {nf.origem}) -> Sem EmbarqueItem")
        
        # 6. Estatísticas de embarques ativos
        print("\n" + "-"*50)
        print("ESTATÍSTICAS DE EMBARQUES ATIVOS:")
        print("-"*50)
        
        embarques_ativos = Embarque.query.filter_by(status='ativo').count()
        print(f"Total de Embarques ATIVOS: {embarques_ativos}")
        
        # Items por embarque ativo
        items_por_embarque = db.session.query(
            Embarque.numero,
            func.count(EmbarqueItem.id).label('total_items'),
            func.count(EmbarqueItem.nota_fiscal).label('items_com_nf')
        ).join(
            EmbarqueItem, Embarque.id == EmbarqueItem.embarque_id
        ).filter(
            Embarque.status == 'ativo'
        ).group_by(
            Embarque.numero
        ).limit(5).all()
        
        print("\nPrimeiros 5 embarques ativos:")
        for emb in items_por_embarque:
            percentual = (emb.items_com_nf / emb.total_items * 100) if emb.total_items > 0 else 0
            print(f"  Embarque {emb.numero}: {emb.items_com_nf}/{emb.total_items} items com NF ({percentual:.1f}%)")
        
        # 7. Verificar erros de validação
        print("\n" + "-"*50)
        print("ERROS DE VALIDAÇÃO:")
        print("-"*50)
        
        items_com_erro = EmbarqueItem.query.filter(
            EmbarqueItem.erro_validacao.isnot(None)
        ).count()
        
        print(f"EmbarqueItems com erro de validação: {items_com_erro}")
        
        # Tipos de erro
        erros = db.session.query(
            EmbarqueItem.erro_validacao,
            func.count(EmbarqueItem.id).label('total')
        ).filter(
            EmbarqueItem.erro_validacao.isnot(None)
        ).group_by(
            EmbarqueItem.erro_validacao
        ).all()
        
        if erros:
            print("\nTipos de erro:")
            for erro in erros:
                print(f"  {erro.erro_validacao}: {erro.total}")
        
        print("\n" + "="*80)
        print("✅ ANÁLISE CONCLUÍDA")
        print("="*80 + "\n")

if __name__ == "__main__":
    main()