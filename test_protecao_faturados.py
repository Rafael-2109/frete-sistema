#!/usr/bin/env python3
"""
Script de teste para verificar proteção de Separações de pedidos faturados.

Este script verifica se as proteções implementadas estão funcionando:
1. Pedidos com status FATURADO não devem ter suas Separações alteradas
2. Pedidos com status EMBARCADO não devem ter suas Separações alteradas
3. Apenas pedidos ABERTO ou COTADO podem ter Separações alteradas
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.carteira.models import CarteiraPrincipal
from app.odoo.services.ajuste_sincronizacao_service import AjusteSincronizacaoService
from datetime import datetime

def criar_cenario_teste():
    """Cria dados de teste para validação."""
    print("\n🔧 Criando cenário de teste...")
    
    # Limpar dados de teste anteriores
    Pedido.query.filter(Pedido.num_pedido.like('TEST%')).delete()
    Separacao.query.filter(Separacao.num_pedido.like('TEST%')).delete()
    CarteiraPrincipal.query.filter(CarteiraPrincipal.num_pedido.like('TEST%')).delete()
    db.session.commit()
    
    # Criar pedidos de teste com diferentes status
    pedidos_teste = [
        {'num': 'TEST001', 'status': 'ABERTO', 'lote': 'LOTE_TEST_001'},
        {'num': 'TEST002', 'status': 'COTADO', 'lote': 'LOTE_TEST_002'},
        {'num': 'TEST003', 'status': 'FATURADO', 'lote': 'LOTE_TEST_003'},
        {'num': 'TEST004', 'status': 'EMBARCADO', 'lote': 'LOTE_TEST_004'},
    ]
    
    for ped in pedidos_teste:
        # Criar Pedido
        pedido = Pedido(
            num_pedido=ped['num'],
            separacao_lote_id=ped['lote'],
            status=ped['status'],
            cnpj_cpf='00000000000000',
            raz_social_red='Empresa Teste',
            data_pedido=datetime.now().date()
        )
        db.session.add(pedido)
        
        # Criar Separacao
        separacao = Separacao(
            separacao_lote_id=ped['lote'],
            num_pedido=ped['num'],
            cod_produto='PROD001',
            nome_produto='Produto Teste',
            qtd_saldo=100.0,
            valor_saldo=1000.0,
            cnpj_cpf='00000000000000',
            raz_social_red='Empresa Teste',
            cod_uf='SP',
            nome_cidade='São Paulo'
        )
        db.session.add(separacao)
        
        # Criar item na carteira (simular sincronização)
        carteira = CarteiraPrincipal(
            num_pedido=ped['num'],
            cod_produto='PROD001',
            nome_produto='Produto Teste',
            qtd_produto_pedido=100.0,
            qtd_saldo_produto_pedido=100.0,
            cnpj_cpf='00000000000000',
            separacao_lote_id=ped['lote']
        )
        db.session.add(carteira)
    
    db.session.commit()
    print("✅ Cenário de teste criado com sucesso")
    return pedidos_teste

def testar_protecao_alteracoes():
    """Testa se as proteções estão funcionando."""
    print("\n🧪 Iniciando testes de proteção...")
    
    pedidos_teste = criar_cenario_teste()
    resultados = []
    
    for ped in pedidos_teste:
        print(f"\n📋 Testando pedido {ped['num']} (status: {ped['status']})...")
        
        # Simular alteração vinda do Odoo (redução de quantidade)
        itens_odoo = [{
            'num_pedido': ped['num'],
            'cod_produto': 'PROD001',
            'nome_produto': 'Produto Teste',
            'qtd_produto_pedido': 50.0,  # Reduzindo de 100 para 50
            'qtd_saldo_produto_pedido': 50.0,
            'preco_produto_pedido': 10.0,
            'peso_unitario_produto': 1.0
        }]
        
        # Contar separações antes
        qtd_antes = Separacao.query.filter_by(
            num_pedido=ped['num']
        ).count()
        
        qtd_saldo_antes = db.session.query(Separacao.qtd_saldo).filter_by(
            num_pedido=ped['num'],
            cod_produto='PROD001'
        ).scalar() or 0
        
        # Tentar processar alteração
        resultado = AjusteSincronizacaoService.processar_pedido_alterado(
            num_pedido=ped['num'],
            itens_odoo=itens_odoo
        )
        
        # Contar separações depois
        qtd_depois = Separacao.query.filter_by(
            num_pedido=ped['num']
        ).count()
        
        qtd_saldo_depois = db.session.query(Separacao.qtd_saldo).filter_by(
            num_pedido=ped['num'],
            cod_produto='PROD001'
        ).scalar() or 0
        
        # Verificar resultado
        if ped['status'] in ['ABERTO', 'COTADO']:
            # Deve ter processado a alteração
            esperado = 'ALTERADO'
            sucesso = qtd_saldo_depois != qtd_saldo_antes or resultado.get('tipo_processamento') != 'TODOS_PROTEGIDOS'
        else:
            # NÃO deve ter alterado
            esperado = 'PROTEGIDO'
            sucesso = qtd_saldo_depois == qtd_saldo_antes and qtd_depois == qtd_antes
        
        resultados.append({
            'pedido': ped['num'],
            'status': ped['status'],
            'esperado': esperado,
            'qtd_antes': qtd_antes,
            'qtd_depois': qtd_depois,
            'saldo_antes': qtd_saldo_antes,
            'saldo_depois': qtd_saldo_depois,
            'tipo_processamento': resultado.get('tipo_processamento', 'ERRO'),
            'sucesso': sucesso
        })
        
        # Imprimir resultado
        if sucesso:
            print(f"✅ PASSOU: {esperado} - Qtd antes: {qtd_saldo_antes}, depois: {qtd_saldo_depois}")
        else:
            print(f"❌ FALHOU: Esperava {esperado} mas qtd mudou de {qtd_saldo_antes} para {qtd_saldo_depois}")
        
        if resultado.get('lotes_protegidos'):
            print(f"   🛡️ Lotes protegidos: {resultado['lotes_protegidos']}")
        
        if resultado.get('alteracoes_aplicadas'):
            for alt in resultado['alteracoes_aplicadas']:
                if alt.get('tipo') == 'LOTE_PROTEGIDO':
                    print(f"   🔒 {alt.get('motivo', 'Lote protegido')}")
    
    # Resumo final
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES:")
    print("="*60)
    
    todos_passaram = True
    for res in resultados:
        status_icon = "✅" if res['sucesso'] else "❌"
        print(f"{status_icon} {res['pedido']} ({res['status']}): ", end="")
        
        if res['sucesso']:
            if res['esperado'] == 'PROTEGIDO':
                print(f"Corretamente PROTEGIDO (não alterado)")
            else:
                print(f"Corretamente ALTERADO ({res['saldo_antes']} → {res['saldo_depois']})")
        else:
            print(f"FALHOU - Esperava {res['esperado']}")
            todos_passaram = False
    
    print("\n" + "="*60)
    if todos_passaram:
        print("🎉 TODOS OS TESTES PASSARAM! As proteções estão funcionando.")
    else:
        print("⚠️ ALGUNS TESTES FALHARAM! Verificar implementação.")
    
    return todos_passaram

def main():
    """Função principal."""
    app = create_app()
    
    with app.app_context():
        try:
            print("="*60)
            print("TESTE DE PROTEÇÃO DE SEPARAÇÕES FATURADAS")
            print("="*60)
            
            sucesso = testar_protecao_alteracoes()
            
            # Limpar dados de teste
            print("\n🧹 Limpando dados de teste...")
            Pedido.query.filter(Pedido.num_pedido.like('TEST%')).delete()
            Separacao.query.filter(Separacao.num_pedido.like('TEST%')).delete()
            CarteiraPrincipal.query.filter(CarteiraPrincipal.num_pedido.like('TEST%')).delete()
            db.session.commit()
            print("✅ Dados de teste limpos")
            
            sys.exit(0 if sucesso else 1)
            
        except Exception as e:
            print(f"\n❌ Erro durante teste: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    main()