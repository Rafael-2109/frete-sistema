#!/usr/bin/env python3
"""
Script de diagnóstico para verificar problemas na importação TagPlus
e processamento de movimentações de estoque
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from app.estoque.models import MovimentacaoEstoque
from app.embarques.models import Embarque, EmbarqueItem
from app.carteira.models import CarteiraCopia
from sqlalchemy import and_, func
from datetime import datetime, timedelta

def diagnosticar_importacao_tagplus():
    """Diagnóstico completo da importação TagPlus"""
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("DIAGNÓSTICO DE IMPORTAÇÃO TAGPLUS - MOVIMENTAÇÕES DE ESTOQUE")
        print("=" * 80)
        
        # 1. NFs importadas do TagPlus
        print("\n1. NFs IMPORTADAS DO TAGPLUS")
        print("-" * 40)
        
        nfs_tagplus = db.session.query(
            FaturamentoProduto.numero_nf,
            FaturamentoProduto.data_fatura,
            FaturamentoProduto.cnpj_cliente,
            FaturamentoProduto.nome_cliente,
            func.count(FaturamentoProduto.id).label('qtd_itens'),
            func.sum(FaturamentoProduto.qtd_produto_faturado).label('qtd_total')
        ).filter(
            FaturamentoProduto.created_by == 'ImportTagPlus'
        ).group_by(
            FaturamentoProduto.numero_nf,
            FaturamentoProduto.data_fatura,
            FaturamentoProduto.cnpj_cliente,
            FaturamentoProduto.nome_cliente
        ).order_by(
            FaturamentoProduto.data_fatura.desc()
        ).limit(10).all()
        
        if nfs_tagplus:
            print(f"Últimas 10 NFs importadas:")
            for nf in nfs_tagplus:
                print(f"  NF: {nf.numero_nf} | Data: {nf.data_fatura} | Cliente: {nf.nome_cliente[:30]}")
                print(f"     CNPJ: {nf.cnpj_cliente} | Itens: {nf.qtd_itens} | Qtd Total: {nf.qtd_total}")
        else:
            print("  ❌ Nenhuma NF TagPlus encontrada!")
        
        # 2. NFs processadas (consolidadas)
        print("\n2. NFs CONSOLIDADAS EM RELATORIO")
        print("-" * 40)
        
        nfs_consolidadas = db.session.query(
            RelatorioFaturamentoImportado.numero_nf
        ).filter(
            RelatorioFaturamentoImportado.origem.like('%TagPlus%')
        ).count()
        
        nfs_sem_consolidar = db.session.query(
            FaturamentoProduto.numero_nf
        ).filter(
            FaturamentoProduto.created_by == 'ImportTagPlus'
        ).filter(
            ~FaturamentoProduto.numero_nf.in_(
                db.session.query(RelatorioFaturamentoImportado.numero_nf)
            )
        ).distinct().count()
        
        print(f"  ✅ NFs consolidadas: {nfs_consolidadas}")
        print(f"  ⚠️  NFs sem consolidar: {nfs_sem_consolidar}")
        
        # 3. Movimentações de estoque
        print("\n3. MOVIMENTAÇÕES DE ESTOQUE TAGPLUS")
        print("-" * 40)
        
        mov_tagplus = db.session.query(
            func.count(MovimentacaoEstoque.id).label('total'),
            func.min(MovimentacaoEstoque.data_movimentacao).label('primeira'),
            func.max(MovimentacaoEstoque.data_movimentacao).label('ultima')
        ).filter(
            MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO TAGPLUS'
        ).first()
        
        if mov_tagplus and mov_tagplus.total > 0:
            print(f"  ✅ Total de movimentações: {mov_tagplus.total}")
            print(f"     Primeira: {mov_tagplus.primeira}")
            print(f"     Última: {mov_tagplus.ultima}")
            
            # Últimas movimentações
            ultimas_mov = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO TAGPLUS'
            ).order_by(MovimentacaoEstoque.created_at.desc()).limit(5).all()
            
            print("\n  Últimas 5 movimentações:")
            for mov in ultimas_mov:
                print(f"    - {mov.cod_produto} | Qtd: {mov.qtd_movimentacao} | {mov.observacao[:50]}")
        else:
            print("  ❌ Nenhuma movimentação FATURAMENTO TAGPLUS encontrada!")
        
        # 4. EmbarqueItems candidatos
        print("\n4. EMBARQUEITEMS CANDIDATOS PARA VINCULAÇÃO")
        print("-" * 40)
        
        # Pega um CNPJ de exemplo das NFs TagPlus
        exemplo_nf = FaturamentoProduto.query.filter_by(
            created_by='ImportTagPlus'
        ).first()
        
        if exemplo_nf:
            cnpj_limpo = exemplo_nf.cnpj_cliente.replace('.', '').replace('-', '').replace('/', '')
            
            candidatos = EmbarqueItem.query.join(
                Embarque,
                EmbarqueItem.embarque_id == Embarque.id
            ).join(
                CarteiraCopia,
                and_(
                    EmbarqueItem.num_pedido == CarteiraCopia.num_pedido,
                    EmbarqueItem.cod_produto == CarteiraCopia.cod_produto
                )
            ).filter(
                CarteiraCopia.cnpj_cpf.contains(cnpj_limpo),
                EmbarqueItem.numero_nf.is_(None),
                Embarque.status == 'ativo',
                EmbarqueItem.status == 'ativo',
                EmbarqueItem.erro_validacao.isnot(None)
            ).count()
            
            print(f"  Cliente exemplo: {exemplo_nf.nome_cliente}")
            print(f"  CNPJ: {exemplo_nf.cnpj_cliente}")
            print(f"  ✅ EmbarqueItems candidatos: {candidatos}")
        else:
            print("  ⚠️  Não há NFs TagPlus para verificar candidatos")
        
        # 5. Análise de problemas
        print("\n5. ANÁLISE DE POSSÍVEIS PROBLEMAS")
        print("-" * 40)
        
        # Verifica NFs sem movimentação
        nfs_sem_mov = db.session.query(
            FaturamentoProduto.numero_nf
        ).filter(
            FaturamentoProduto.created_by == 'ImportTagPlus'
        ).filter(
            ~FaturamentoProduto.numero_nf.in_(
                db.session.query(MovimentacaoEstoque.observacao).filter(
                    MovimentacaoEstoque.observacao.like('%NF%')
                ).subquery()
            )
        ).distinct().count()
        
        print(f"  ⚠️  NFs sem movimentação de estoque: {nfs_sem_mov}")
        
        # Verifica EmbarqueItems sem erro_validacao
        items_sem_erro = EmbarqueItem.query.join(
            Embarque
        ).filter(
            EmbarqueItem.numero_nf.is_(None),
            Embarque.status == 'ativo',
            EmbarqueItem.status == 'ativo',
            EmbarqueItem.erro_validacao.is_(None)
        ).count()
        
        print(f"  ℹ️  EmbarqueItems ativos sem erro_validacao: {items_sem_erro}")
        print("     (não são candidatos para vinculação)")
        
        # 6. Recomendações
        print("\n6. RECOMENDAÇÕES")
        print("-" * 40)
        
        if nfs_sem_mov > 0:
            print("  🔧 Execute o reprocessamento das NFs:")
            print("     from app.integracoes.tagplus.processador_faturamento_tagplus import ProcessadorFaturamentoTagPlus")
            print("     processador = ProcessadorFaturamentoTagPlus()")
            print("     resultado = processador.processar_lote_nfs()")
            print()
            print("  🔧 Ou reimporte com processamento completo ativado")
            print("     Marque o checkbox 'Processar vinculações e movimentações'")
        
        if items_sem_erro > 0:
            print()
            print("  ℹ️  Existem EmbarqueItems sem erro_validacao")
            print("     Estes itens não são considerados para vinculação automática")
            print("     Verifique o processo de validação dos embarques")

if __name__ == "__main__":
    diagnosticar_importacao_tagplus()