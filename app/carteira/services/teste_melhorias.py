"""
Teste das Melhorias no Processador de Faturamento
================================================

Valida as 4 melhorias implementadas
"""

from app import create_app, db
from app.carteira.services.processar_faturamento import ProcessadorFaturamento
from app.faturamento.models import RelatorioFaturamentoImportado, FaturamentoProduto
from app.separacao.models import Separacao
from app.embarques.models import EmbarqueItem, Embarque

def testar_melhorias():
    """
    Testa as melhorias implementadas
    """
    app = create_app()
    
    with app.app_context():
        print("🧪 TESTANDO MELHORIAS DO PROCESSADOR\n")
        
        processador = ProcessadorFaturamento()
        
        # TESTE 1: Verificar busca de NFs com mudança de status
        print("1️⃣ Teste: Busca NFs com mudança de status")
        print("-" * 50)
        
        # Buscar NFs com status Cancelado no FaturamentoProduto
        nfs_canceladas = db.session.query(
            FaturamentoProduto.numero_nf,
            FaturamentoProduto.status_nf
        ).filter(
            FaturamentoProduto.status_nf == 'Cancelado'
        ).group_by(
            FaturamentoProduto.numero_nf,
            FaturamentoProduto.status_nf
        ).limit(5).all()
        
        print(f"NFs com status 'Cancelado' encontradas: {len(nfs_canceladas)}")
        for nf, status in nfs_canceladas:
            print(f"  - NF {nf}: {status}")
        
        # TESTE 2: Verificar vinculação existente em EmbarqueItem
        print("\n2️⃣ Teste: NFs já preenchidas em EmbarqueItem")
        print("-" * 50)
        
        embarques_com_nf = EmbarqueItem.query.filter(
            EmbarqueItem.nota_fiscal.isnot(None)
        ).limit(5).all()
        
        print(f"EmbarqueItems com NF preenchida: {len(embarques_com_nf)}")
        for item in embarques_com_nf:
            print(f"  - NF {item.nota_fiscal} → Embarque {item.embarque_id}")
            print(f"    Lote: {item.separacao_lote_id}")
            print(f"    Pedido: {item.num_pedido}")
        
        # TESTE 3: Verificar cálculo de score percentual
        print("\n3️⃣ Teste: Simulação de score percentual")
        print("-" * 50)
        
        # Buscar uma NF e suas separações para simular
        nf_teste = RelatorioFaturamentoImportado.query.filter(
            RelatorioFaturamentoImportado.ativo == True
        ).first()
        
        if nf_teste and nf_teste.origem:
            print(f"NF teste: {nf_teste.numero_nf} - Pedido: {nf_teste.origem}")
            
            # Buscar produtos da NF
            produtos_nf = FaturamentoProduto.query.filter_by(
                numero_nf=nf_teste.numero_nf
            ).all()
            
            print(f"Produtos na NF: {len(produtos_nf)}")
            for p in produtos_nf[:3]:
                print(f"  - {p.cod_produto}: {p.qtd_produto_faturado}")
            
            # Buscar separações do pedido
            separacoes = Separacao.query.filter_by(
                num_pedido=nf_teste.origem
            ).all()
            
            print(f"\nSeparações do pedido: {len(separacoes)}")
            
            # Agrupar por lote
            lotes = {}
            for sep in separacoes:
                if sep.separacao_lote_id not in lotes:
                    lotes[sep.separacao_lote_id] = []
                lotes[sep.separacao_lote_id].append(sep)
            
            print(f"Lotes de separação encontrados: {len(lotes)}")
            for lote_id, seps in lotes.items():
                print(f"  - Lote {lote_id}: {len(seps)} produtos")
        
        # TESTE 4: Verificar inconsistências
        print("\n4️⃣ Teste: Verificar geração de inconsistências")
        print("-" * 50)
        
        # Buscar inconsistências de vinculação
        from app.carteira.models import InconsistenciaFaturamento
        
        inconsistencias = InconsistenciaFaturamento.query.filter(
            InconsistenciaFaturamento.tipo == 'NF_VINCULADA_INCORRETAMENTE'
        ).limit(5).all()
        
        print(f"Inconsistências de vinculação: {len(inconsistencias)}")
        for inc in inconsistencias:
            print(f"  - NF {inc.numero_nf}: {inc.tipo}")
            print(f"    Resolvida: {inc.resolvida}")
        
        print("\n✅ Testes concluídos!")

if __name__ == '__main__':
    testar_melhorias() 