#!/usr/bin/env python3
"""
Script para verificar a presença do produto 4159301 em todas as tabelas relevantes
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Verificar se está no ambiente correto
try:
    from app import create_app, db
    from app.carteira.models import CarteiraPrincipal
    from app.producao.models import CadastroPalletizacao
    from app.estoque.models import MovimentacaoEstoque
    from app.separacao.models import Separacao
    from sqlalchemy import func
    import logging
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger(__name__)
    
    def verificar_produto():
        """Verifica a presença do produto 4159301 no sistema"""
        
        app = create_app()
        cod_produto = '4159301'
        
        with app.app_context():
            print("=" * 80)
            print(f"VERIFICAÇÃO DO PRODUTO {cod_produto}")
            print("=" * 80)
            
            # 1. Verificar na CarteiraPrincipal
            print("\n📋 CARTEIRA PRINCIPAL:")
            print("-" * 40)
            
            itens_carteira = CarteiraPrincipal.query.filter_by(
                cod_produto=cod_produto
            ).all()
            
            if itens_carteira:
                print(f"✅ ENCONTRADO: {len(itens_carteira)} registro(s)")
                for item in itens_carteira[:5]:  # Primeiros 5
                    print(f"   - Pedido: {item.num_pedido}")
                    print(f"     Nome: {item.nome_produto}")
                    print(f"     Qtd Saldo: {item.qtd_saldo_produto_pedido}")
                    print(f"     Ativo: {item.ativo}")
                    print(f"     Status: {item.status_pedido}")
                    print(f"     Created: {item.created_at}")
                    print()
            else:
                print("❌ NÃO ENCONTRADO na CarteiraPrincipal")
            
            # Verificar também itens inativos
            itens_inativos = CarteiraPrincipal.query.filter_by(
                cod_produto=cod_produto,
                ativo=False
            ).count()
            
            if itens_inativos > 0:
                print(f"⚠️ {itens_inativos} registro(s) INATIVO(S) encontrado(s)")
            
            # 2. Verificar no CadastroPalletizacao
            print("\n📦 CADASTRO PALLETIZAÇÃO:")
            print("-" * 40)
            
            cadastro_pallet = CadastroPalletizacao.query.filter_by(
                cod_produto=cod_produto
            ).first()
            
            if cadastro_pallet:
                print(f"✅ ENCONTRADO")
                print(f"   Nome: {cadastro_pallet.nome_produto}")
                print(f"   Palletização: {cadastro_pallet.palletizacao}")
                print(f"   Peso Bruto: {cadastro_pallet.peso_bruto}")
                print(f"   Ativo: {cadastro_pallet.ativo}")
                print(f"   Created by: {cadastro_pallet.created_by}")
                print(f"   Created at: {cadastro_pallet.created_at}")
            else:
                print("❌ NÃO ENCONTRADO no CadastroPalletizacao")
                print("   ⚠️ Isso impedirá o produto de aparecer corretamente na carteira!")
            
            # 3. Verificar na MovimentacaoEstoque
            print("\n📊 MOVIMENTAÇÃO ESTOQUE:")
            print("-" * 40)
            
            movimentacoes = MovimentacaoEstoque.query.filter_by(
                cod_produto=cod_produto
            ).count()
            
            if movimentacoes > 0:
                print(f"✅ ENCONTRADO: {movimentacoes} movimentação(ões)")
                
                # Calcular saldo
                saldo = db.session.query(
                    func.sum(MovimentacaoEstoque.qtd_movimentacao)
                ).filter(
                    MovimentacaoEstoque.cod_produto == cod_produto,
                    MovimentacaoEstoque.ativo == True
                ).scalar()
                
                print(f"   Saldo atual: {saldo or 0}")
            else:
                print("❌ NÃO ENCONTRADO na MovimentacaoEstoque")
                print("   ℹ️ Produto novo sem histórico de estoque")
            
            # 4. Verificar na Separacao
            print("\n📤 SEPARAÇÃO:")
            print("-" * 40)
            
            separacoes = Separacao.query.filter_by(
                cod_produto=cod_produto
            ).all()
            
            if separacoes:
                print(f"✅ ENCONTRADO: {len(separacoes)} separação(ões)")
                
                # Agrupar por status
                por_status = {}
                for sep in separacoes:
                    status = sep.status or 'SEM_STATUS'
                    por_status[status] = por_status.get(status, 0) + 1
                
                for status, count in por_status.items():
                    print(f"   - {status}: {count}")
            else:
                print("❌ NÃO ENCONTRADO na Separacao")
            
            # 5. DIAGNÓSTICO FINAL
            print("\n" + "=" * 80)
            print("DIAGNÓSTICO:")
            print("=" * 80)
            
            if not cadastro_pallet and itens_carteira:
                print("\n🔴 PROBLEMA IDENTIFICADO:")
                print("   O produto existe na CarteiraPrincipal mas NÃO tem CadastroPalletizacao!")
                print("   Isso fará com que o produto não apareça corretamente na carteira agrupada.")
                print("\n🔧 SOLUÇÃO:")
                print("   Execute o comando abaixo para criar o cadastro automaticamente:")
                print(f"   python verificar_produto_4159301.py --fix")
                return False
            elif itens_carteira and cadastro_pallet:
                if all(not item.ativo for item in itens_carteira):
                    print("\n⚠️ ATENÇÃO:")
                    print("   O produto existe mas todos os registros estão INATIVOS!")
                else:
                    print("\n✅ PRODUTO CONFIGURADO CORRETAMENTE")
                    print("   O produto deveria aparecer normalmente na carteira.")
                return True
            elif not itens_carteira:
                print("\n❌ PRODUTO NÃO EXISTE NA CARTEIRA")
                print("   O produto precisa ser importado do Odoo primeiro.")
                return False
            
            return True
    
    def corrigir_produto():
        """Cria CadastroPalletizacao para o produto se não existir"""
        
        app = create_app()
        cod_produto = '4159301'
        
        with app.app_context():
            print("\n🔧 TENTANDO CORRIGIR...")
            
            # Verificar se já existe
            existe = CadastroPalletizacao.query.filter_by(
                cod_produto=cod_produto
            ).first()
            
            if existe:
                print("ℹ️ Produto já existe no CadastroPalletizacao")
                return
            
            # Buscar nome do produto na CarteiraPrincipal
            item_carteira = CarteiraPrincipal.query.filter_by(
                cod_produto=cod_produto
            ).first()
            
            if not item_carteira:
                print("❌ Produto não encontrado na CarteiraPrincipal. Não é possível criar cadastro.")
                return
            
            # Criar cadastro
            novo_cadastro = CadastroPalletizacao(
                cod_produto=cod_produto,
                nome_produto=item_carteira.nome_produto or cod_produto,
                palletizacao=1.0,
                peso_bruto=1.0,
                ativo=True,
                created_by='CorrecaoManual',
                updated_by='CorrecaoManual'
            )
            
            db.session.add(novo_cadastro)
            db.session.commit()
            
            print(f"✅ CadastroPalletizacao criado com sucesso para o produto {cod_produto}")
            print(f"   Nome: {novo_cadastro.nome_produto}")
            print(f"   Palletização: {novo_cadastro.palletizacao}")
            print(f"   Peso Bruto: {novo_cadastro.peso_bruto}")
    
    if __name__ == '__main__':
        if len(sys.argv) > 1 and sys.argv[1] == '--fix':
            corrigir_produto()
        else:
            sucesso = verificar_produto()
            sys.exit(0 if sucesso else 1)
            
except ImportError as e:
    print(f"ERRO: {e}")
    print("\nCertifique-se de estar no ambiente virtual correto:")
    print("  source venv/bin/activate  # ou o comando apropriado para seu ambiente")
    sys.exit(1)