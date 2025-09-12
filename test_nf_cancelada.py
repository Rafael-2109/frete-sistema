#!/usr/bin/env python3
"""
Script para testar processamento de NF cancelada específica (139272)
Verifica se a NF é detectada como cancelada e se altera os status corretamente
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.odoo.services.faturamento_service import FaturamentoService
from app.faturamento.models import FaturamentoProduto
from app.estoque.models import MovimentacaoEstoque
from app.separacao.models import Separacao
from datetime import datetime
import logging

# Configurar logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def testar_nf_cancelada(numero_nf='139272'):
    """Testa processamento de NF cancelada específica"""
    
    app = create_app()
    with app.app_context():
        try:
            print(f"\n{'='*60}")
            print(f"🔍 TESTE DE NF CANCELADA: {numero_nf}")
            print(f"{'='*60}\n")
            
            # 1. Conectar ao Odoo e buscar a NF
            print("1️⃣ Conectando ao Odoo...")
            service = FaturamentoService()
            
            # Buscar especificamente esta NF no Odoo
            print(f"2️⃣ Buscando NF {numero_nf} no Odoo...")
            
            # Buscar diretamente a fatura no Odoo
            connection = service.connection
            
            # Buscar a fatura pela NF
            faturas = connection.search_read(
                'account.move',
                [('l10n_br_numero_nota_fiscal', '=', numero_nf)],
                ['id', 'name', 'state', 'l10n_br_numero_nota_fiscal', 'invoice_origin', 
                 'date', 'partner_id', 'l10n_br_cnpj']
            )
            
            if not faturas:
                print(f"❌ NF {numero_nf} não encontrada no Odoo!")
                return
            
            fatura = faturas[0]
            print(f"\n✅ NF encontrada no Odoo:")
            print(f"   - ID Odoo: {fatura['id']}")
            print(f"   - Número: {fatura['l10n_br_numero_nota_fiscal']}")
            print(f"   - Estado: {fatura['state']} {'🚨 CANCELADA!' if fatura['state'] == 'cancel' else ''}")
            print(f"   - Data: {fatura['date']}")
            print(f"   - Cliente: {fatura['partner_id'][1] if fatura['partner_id'] else 'N/A'}")
            print(f"   - CNPJ: {fatura.get('l10n_br_cnpj', 'N/A')}")
            
            # 3. Verificar situação atual no banco
            print(f"\n3️⃣ Verificando situação atual no banco de dados...")
            
            # Verificar FaturamentoProduto
            faturamentos = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).all()
            print(f"\n📦 FaturamentoProduto: {len(faturamentos)} registros")
            for fat in faturamentos[:3]:  # Mostrar apenas 3 primeiros
                print(f"   - Produto: {fat.cod_produto}, Status: {fat.status_nf}")
            
            # Verificar MovimentacaoEstoque
            movimentacoes = MovimentacaoEstoque.query.filter_by(numero_nf=numero_nf).all()
            print(f"\n📊 MovimentacaoEstoque: {len(movimentacoes)} registros")
            for mov in movimentacoes[:3]:
                print(f"   - Produto: {mov.cod_produto}, Ativo: {mov.ativo}, Status: {mov.status_nf}")
            
            # 4. Processar a sincronização para esta NF
            print(f"\n4️⃣ Processando sincronização da NF {numero_nf}...")
            
            if fatura['state'] == 'cancel':
                print("   🚨 NF está CANCELADA no Odoo - processando cancelamento...")
                
                # Chamar diretamente o método de processar cancelamento
                resultado = service._processar_cancelamento_nf(numero_nf)
                
                if resultado:
                    print("   ✅ Cancelamento processado com sucesso!")
                else:
                    print("   ❌ Erro ao processar cancelamento")
                
                # Verificar mudanças após processamento
                print(f"\n5️⃣ Verificando alterações após processamento...")
                
                # Re-verificar FaturamentoProduto
                faturamentos_depois = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).all()
                print(f"\n📦 FaturamentoProduto DEPOIS:")
                mudancas_fat = False
                for fat in faturamentos_depois[:3]:
                    print(f"   - Produto: {fat.cod_produto}, Status: {fat.status_nf}")
                    if fat.status_nf == 'Cancelado':
                        mudancas_fat = True
                
                # Re-verificar MovimentacaoEstoque
                movimentacoes_depois = MovimentacaoEstoque.query.filter_by(numero_nf=numero_nf).all()
                print(f"\n📊 MovimentacaoEstoque DEPOIS:")
                mudancas_mov = False
                for mov in movimentacoes_depois[:3]:
                    print(f"   - Produto: {mov.cod_produto}, Ativo: {mov.ativo}, Status: {mov.status_nf}")
                    if not mov.ativo or mov.status_nf == 'CANCELADO':
                        mudancas_mov = True
                
                # Verificar Separacao
                separacoes = Separacao.query.filter_by(numero_nf=numero_nf).all()
                print(f"\n🚚 Separacao: {len(separacoes)} registros")
                for sep in separacoes[:3]:
                    print(f"   - Pedido: {sep.num_pedido}, Sincronizado: {sep.sincronizado_nf}")
                
                # Resumo das mudanças
                print(f"\n{'='*60}")
                print("📊 RESUMO DAS ALTERAÇÕES:")
                print(f"{'='*60}")
                print(f"✅ FaturamentoProduto alterado: {'SIM' if mudancas_fat else 'NÃO ❌'}")
                print(f"✅ MovimentacaoEstoque alterado: {'SIM' if mudancas_mov else 'NÃO ❌'}")
                print(f"✅ Separacao revertida: {'SIM' if len(separacoes) > 0 else 'N/A'}")
                
            else:
                print(f"   ℹ️ NF está com status '{fatura['state']}' no Odoo (não está cancelada)")
                
                # Mesmo assim, vamos sincronizar para testar
                print("\n   Executando sincronização incremental...")
                
                # Buscar linhas da fatura
                linhas = connection.search_read(
                    'account.move.line',
                    [('move_id', '=', fatura['id']), ('product_id', '!=', False)],
                    ['id', 'move_id', 'partner_id', 'product_id', 'quantity', 
                     'price_unit', 'price_total', 'l10n_br_total_nfe']
                )
                
                print(f"   Encontradas {len(linhas)} linhas de produtos")
                
                if linhas:
                    # Processar os dados
                    dados_processados = service._processar_dados_faturamento_com_multiplas_queries(linhas)
                    print(f"   Processados {len(dados_processados)} itens")
                    
                    # Inserir ou atualizar no banco
                    for item in dados_processados:
                        # Verificar se já existe
                        fat_existente = FaturamentoProduto.query.filter_by(
                            numero_nf=item.get('numero_nf'),
                            cod_produto=item.get('cod_produto')
                        ).first()
                        
                        if not fat_existente:
                            # Criar novo
                            novo_fat = FaturamentoProduto()
                            for key, value in item.items():
                                if hasattr(novo_fat, key) and key not in ['created_at', 'updated_at']:
                                    setattr(novo_fat, key, value)
                            novo_fat.created_by = 'Teste NF Cancelada'
                            db.session.add(novo_fat)
                            print(f"   ➕ Inserido produto {item.get('cod_produto')}")
                        else:
                            # Atualizar status se diferente
                            if fat_existente.status_nf != item.get('status_nf'):
                                fat_existente.status_nf = item.get('status_nf')
                                fat_existente.updated_by = 'Teste NF Cancelada'
                                print(f"   ✏️ Atualizado status do produto {item.get('cod_produto')}")
                    
                    db.session.commit()
                    print("   ✅ Dados salvos no banco")
            
            print(f"\n{'='*60}")
            print("🏁 TESTE CONCLUÍDO")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\n❌ ERRO NO TESTE: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == "__main__":
    numero_nf = sys.argv[1] if len(sys.argv) > 1 else '139272'
    testar_nf_cancelada(numero_nf)