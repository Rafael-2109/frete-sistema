#!/usr/bin/env python3
"""
Debug do processamento limitado de NFs
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.faturamento.services.processar_faturamento import ProcessadorFaturamento
from app.faturamento.models import RelatorioFaturamentoImportado
from app.estoque.models import MovimentacaoEstoque

app = create_app()
with app.app_context():
    print("\n=== DEBUG PROCESSAMENTO LIMITADO ===\n")
    
    # Verificar especificamente a NF 137747 (onde parou)
    nf_137747 = RelatorioFaturamentoImportado.query.filter_by(numero_nf='137747').first()
    if nf_137747:
        print(f"NF 137747 encontrada:")
        print(f"  - Pedido: {nf_137747.origem}")
        print(f"  - CNPJ: {nf_137747.cnpj_cliente}")
        print(f"  - Status: {nf_137747.status_faturamento}")
        print(f"  - Ativo: {nf_137747.ativo}")
        
        # Verificar movimentações
        movs = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.observacao.like('%NF 137747%')
        ).all()
        print(f"\nMovimentações existentes: {len(movs)}")
        for mov in movs:
            print(f"  - {mov.observacao}")
    
    # Verificar a próxima NF (137746)
    print("\n" + "="*50 + "\n")
    nf_137746 = RelatorioFaturamentoImportado.query.filter_by(numero_nf='137746').first()
    if nf_137746:
        print(f"NF 137746 (próxima) encontrada:")
        print(f"  - Pedido: {nf_137746.origem}")
        print(f"  - CNPJ: {nf_137746.cnpj_cliente}")
        print(f"  - Status: {nf_137746.status_faturamento}")
        
        # Verificar se tem produtos
        from app.faturamento.models import FaturamentoProduto
        produtos = FaturamentoProduto.query.filter_by(numero_nf='137746').all()
        print(f"  - Produtos: {len(produtos)}")
        
        # Verificar se tem separações
        from app.separacao.models import Separacao
        separacoes = Separacao.query.filter_by(num_pedido=nf_137746.origem).all()
        print(f"  - Separações: {len(separacoes)}")
        
        # Verificar se tem EmbarqueItem
        from app.embarques.models import EmbarqueItem
        embarque_item = EmbarqueItem.query.filter_by(pedido=nf_137746.origem).first()
        print(f"  - EmbarqueItem: {'SIM' if embarque_item else 'NÃO'}")
        if embarque_item:
            print(f"    - NF preenchida: {embarque_item.nota_fiscal}")
            print(f"    - CNPJ: {embarque_item.cnpj_cliente}")
            print(f"    - Lote: {embarque_item.separacao_lote_id}")
    
    # Testar processamento manual da NF 137747
    print("\n" + "="*50 + "\n")
    print("Testando processamento manual da NF 137747...")
    
    processador = ProcessadorFaturamento()
    try:
        # Simular o processamento
        from app.faturamento.models import FaturamentoProduto
        produtos_137747 = FaturamentoProduto.query.filter_by(numero_nf='137747').all()
        print(f"Produtos da NF 137747: {len(produtos_137747)}")
        
        # Verificar separações
        from app.separacao.models import Separacao
        if nf_137747:
            separacoes_137747 = Separacao.query.filter_by(num_pedido=nf_137747.origem).all()
            print(f"Separações do pedido {nf_137747.origem}: {len(separacoes_137747)}")
            
            # Listar separações
            for sep in separacoes_137747[:5]:  # Primeiras 5
                print(f"  - Produto {sep.cod_produto}: Qtd {sep.qtd_separacao}, Saldo {sep.qtd_saldo}, Lote {sep.lote}")
    
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()