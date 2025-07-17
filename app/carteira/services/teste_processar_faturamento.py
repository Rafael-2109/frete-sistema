"""
Teste do Processador de Faturamento
===================================

Script para testar se o processamento está funcionando corretamente
"""

from app import create_app, db
from app.carteira.services.processar_faturamento import ProcessadorFaturamento
from app.faturamento.models import RelatorioFaturamentoImportado, FaturamentoProduto
from app.separacao.models import Separacao
from app.estoque.models import MovimentacaoEstoque

def testar_processamento():
    """
    Testa o processamento de faturamento
    """
    app = create_app()
    
    with app.app_context():
        try:
            # Inicializar processador
            processador = ProcessadorFaturamento()
            
            # Verificar modelos
            print("✅ Verificando modelos...")
            print(f"- RelatorioFaturamentoImportado: OK")
            print(f"- FaturamentoProduto: OK")
            print(f"- Separacao: OK")
            print(f"- MovimentacaoEstoque: OK")
            
            # Buscar NFs pendentes
            print("\n📋 Buscando NFs pendentes...")
            nfs_pendentes = processador._buscar_nfs_pendentes()
            print(f"- Total de NFs pendentes: {len(nfs_pendentes)}")
            
            # Mostrar algumas NFs
            for i, nf in enumerate(nfs_pendentes[:5]):
                print(f"  {i+1}. NF {nf.numero_nf} - {nf.nome_cliente} - Pedido: {nf.origem}")
            
            # Buscar algumas separações
            print("\n📦 Verificando separações...")
            separacoes = Separacao.query.limit(5).all()
            print(f"- Total de separações encontradas: {len(separacoes)}")
            
            for sep in separacoes:
                print(f"  - Lote: {sep.separacao_lote_id} - Pedido: {sep.num_pedido} - Produto: {sep.cod_produto}")
            
            # Verificar movimentações existentes
            print("\n🔄 Verificando movimentações de estoque...")
            mov_faturamento = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO'
            ).limit(5).all()
            print(f"- Movimentações de faturamento existentes: {len(mov_faturamento)}")
            
            # Testar processamento (sem commit)
            print("\n🚀 Testando processamento (DRY RUN)...")
            if input("Deseja processar uma NF de teste? (s/n): ").lower() == 's':
                if nfs_pendentes:
                    nf_teste = nfs_pendentes[0]
                    print(f"\nProcessando NF {nf_teste.numero_nf}...")
                    
                    try:
                        caso = processador._processar_nf(nf_teste, 'TESTE')
                        print(f"✅ NF processada como Caso {caso}")
                        
                        # Rollback para não salvar
                        db.session.rollback()
                        print("⚠️ Rollback executado - nada foi salvo")
                    except Exception as e:
                        print(f"❌ Erro no processamento: {str(e)}")
                        db.session.rollback()
            
            print("\n✅ Teste concluído!")
            
        except Exception as e:
            print(f"\n❌ Erro durante teste: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    testar_processamento() 