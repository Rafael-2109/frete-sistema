#!/usr/bin/env python3
"""
Teste definitivo para identificar por que o produto 4159301 não aparece na carteira
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

def testar_produto():
    app = create_app()
    cod_produto = '4159301'
    
    with app.app_context():
        print("=" * 80)
        print(f"TESTE DEFINITIVO - PRODUTO {cod_produto}")
        print("=" * 80)
        
        from app.carteira.models import CarteiraPrincipal, SaldoStandby
        from app.producao.models import CadastroPalletizacao
        from sqlalchemy import and_, exists, func
        
        # TESTE 1: Produto existe e está ativo?
        print("\n✅ TESTE 1: CarteiraPrincipal")
        itens = CarteiraPrincipal.query.filter_by(cod_produto=cod_produto).all()
        itens_ativos = [i for i in itens if i.ativo]
        
        print(f"Total de registros: {len(itens)}")
        print(f"Registros ativos: {len(itens_ativos)}")
        
        if not itens:
            print("❌ FALHOU: Produto não existe na CarteiraPrincipal")
            print("SOLUÇÃO: Importar o produto do Odoo")
            return False
        
        if not itens_ativos:
            print("❌ FALHOU: Todos os registros estão inativos")
            print("SOLUÇÃO: Ativar os registros do produto")
            return False
        
        print("✅ PASSOU: Produto existe e tem registros ativos")
        
        # Pegar pedidos únicos
        pedidos = list(set(i.num_pedido for i in itens_ativos))
        print(f"Pedidos: {', '.join(pedidos[:5])}")
        
        # TESTE 2: CadastroPalletizacao existe?
        print("\n✅ TESTE 2: CadastroPalletizacao")
        cadastro = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        
        if not cadastro:
            print("❌ FALHOU: Produto não tem CadastroPalletizacao")
            print("SOLUÇÃO: Execute 'python teste_produto_carteira.py --fix'")
            return False
        
        if not cadastro.ativo:
            print("❌ FALHOU: CadastroPalletizacao está inativo")
            print("SOLUÇÃO: Ativar o cadastro do produto")
            return False
        
        print("✅ PASSOU: CadastroPalletizacao existe e está ativo")
        print(f"   Nome: {cadastro.nome_produto}")
        print(f"   Palletização: {cadastro.palletizacao}")
        print(f"   Peso: {cadastro.peso_bruto}")
        
        # TESTE 3: Pedidos estão em Standby?
        print("\n✅ TESTE 3: Verificação de Standby")
        pedidos_standby = SaldoStandby.query.filter(
            SaldoStandby.num_pedido.in_(pedidos),
            SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
        ).all()
        
        if pedidos_standby:
            print(f"❌ FALHOU: {len(pedidos_standby)} pedido(s) em standby")
            for ps in pedidos_standby:
                print(f"   - {ps.num_pedido}: Status {ps.status_standby}")
            print("SOLUÇÃO: Remover pedidos do standby ou mudar status")
            return False
        
        print("✅ PASSOU: Nenhum pedido em standby bloqueante")
        
        # TESTE 4: Simular query do AgrupamentoService
        print("\n✅ TESTE 4: Query do AgrupamentoService")
        
        # Esta é a query exata usada no agrupamento
        resultado = db.session.query(
            CarteiraPrincipal.num_pedido,
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('qtd_total'),
            func.count(CarteiraPrincipal.id).label('total_itens')
        ).outerjoin(
            CadastroPalletizacao,
            and_(
                CarteiraPrincipal.cod_produto == CadastroPalletizacao.cod_produto,
                CadastroPalletizacao.ativo == True
            )
        ).filter(
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.ativo == True,
            ~exists().where(
                and_(
                    SaldoStandby.num_pedido == CarteiraPrincipal.num_pedido,
                    SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
                )
            )
        ).group_by(
            CarteiraPrincipal.num_pedido
        ).all()
        
        if resultado:
            print(f"✅ PASSOU: Query retornou {len(resultado)} pedido(s)")
            for r in resultado:
                print(f"   - {r.num_pedido}: {r.total_itens} itens, qtd: {r.qtd_total}")
        else:
            print("❌ FALHOU: Query não retornou nenhum resultado")
            print("Isso é estranho se todos os testes anteriores passaram!")
            
        # TESTE 5: Verificar se aparece na view final
        print("\n✅ TESTE 5: Teste completo do AgrupamentoService")
        
        from app.carteira.services.agrupamento_service import AgrupamentoService
        service = AgrupamentoService()
        
        # Buscar todos os pedidos agrupados
        todos_pedidos = service.obter_pedidos_agrupados()
        
        # Verificar se algum pedido contém nosso produto
        pedidos_com_produto = []
        for p in todos_pedidos:
            if p.get('num_pedido') in pedidos:
                pedidos_com_produto.append(p['num_pedido'])
        
        if pedidos_com_produto:
            print(f"✅ PASSOU: Produto aparece em {len(pedidos_com_produto)} pedido(s)")
            print(f"   Pedidos: {', '.join(pedidos_com_produto[:5])}")
        else:
            print("❌ FALHOU: Produto não aparece em nenhum pedido agrupado")
            print("Verificar se há algum filtro adicional no template ou JavaScript")
        
        print("\n" + "=" * 80)
        print("RESUMO FINAL:")
        print("=" * 80)
        
        if pedidos_com_produto:
            print("✅ O PRODUTO DEVERIA APARECER NA CARTEIRA!")
            print("\n💡 Se não está aparecendo, verifique:")
            print("  1. Cache do navegador (Ctrl+F5)")
            print("  2. Filtros no frontend (JavaScript)")
            print("  3. Reiniciar o servidor Flask")
        else:
            print("❌ O PRODUTO NÃO ESTÁ APARECENDO NA CARTEIRA")
            print("\nExecute com --fix para tentar corrigir automaticamente")
        
        return len(pedidos_com_produto) > 0

def corrigir_produto():
    app = create_app()
    cod_produto = '4159301'
    
    with app.app_context():
        from app.carteira.models import CarteiraPrincipal
        from app.producao.models import CadastroPalletizacao
        
        print("\n🔧 CORREÇÃO AUTOMÁTICA")
        print("-" * 60)
        
        # 1. Verificar CarteiraPrincipal
        itens = CarteiraPrincipal.query.filter_by(cod_produto=cod_produto).all()
        if not itens:
            print("❌ Produto não existe na CarteiraPrincipal. Não há o que corrigir.")
            print("   É necessário importar o produto do Odoo primeiro.")
            return
        
        # 2. Ativar registros inativos
        reativados = 0
        for item in itens:
            if not item.ativo:
                item.ativo = True
                reativados += 1
        
        if reativados > 0:
            print(f"✅ {reativados} registro(s) reativado(s) na CarteiraPrincipal")
        
        # 3. Criar/Ativar CadastroPalletizacao
        cadastro = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        
        if cadastro:
            if not cadastro.ativo:
                cadastro.ativo = True
                print("✅ CadastroPalletizacao reativado")
        else:
            # Criar novo
            nome = itens[0].nome_produto if itens else f'Produto {cod_produto}'
            cadastro = CadastroPalletizacao(
                cod_produto=cod_produto,
                nome_produto=nome,
                palletizacao=1.0,
                peso_bruto=1.0,
                ativo=True,
                created_by='CorrecaoAutomatica',
                updated_by='CorrecaoAutomatica'
            )
            db.session.add(cadastro)
            print("✅ CadastroPalletizacao criado")
        
        # 4. Commit
        db.session.commit()
        print("\n✅ Correções aplicadas com sucesso!")
        print("   Recarregue a página da carteira para ver o produto.")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--fix':
        corrigir_produto()
    else:
        sucesso = testar_produto()
        if not sucesso:
            print("\n💡 Execute com --fix para corrigir:")
            print("   python teste_produto_carteira.py --fix")
        sys.exit(0 if sucesso else 1)