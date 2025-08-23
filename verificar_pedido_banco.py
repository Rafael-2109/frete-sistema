#!/usr/bin/env python3
"""
Script para verificar os dados do pedido VCD2520950 no banco
"""

import sys
import os
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.pedidos.models import Pedido

def main():
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("VERIFICANDO PEDIDO VCD2520950 NO BANCO DE DADOS")
        print("=" * 80)
        
        # 1. Buscar na CarteiraPrincipal
        print("\n1. BUSCANDO NA CARTEIRA PRINCIPAL:")
        print("-" * 40)
        
        itens_carteira = CarteiraPrincipal.query.filter_by(num_pedido='VCD2520950').all()
        
        if itens_carteira:
            print(f"✅ Encontrados {len(itens_carteira)} itens na CarteiraPrincipal")
            
            # Pegar primeiro item para ver os campos
            item = itens_carteira[0]
            
            print(f"\n📋 DADOS DO PEDIDO NA CARTEIRA:")
            print(f"   num_pedido: {item.num_pedido}")
            print(f"   pedido_cliente: {item.pedido_cliente}")
            print(f"   cnpj_cpf: {item.cnpj_cpf}")
            print(f"   raz_social_red: {item.raz_social_red}")
            print(f"   separacao_lote_id: {item.separacao_lote_id}")
            print(f"   expedicao: {item.expedicao}")
            print(f"   agendamento: {item.agendamento}")
            print(f"   hora_agendamento: {item.hora_agendamento}")
            print(f"   protocolo: {item.protocolo}")
            print(f"   agendamento_confirmado: {item.agendamento_confirmado}")
            print(f"   data_entrega: {item.data_entrega}")
            print(f"   data_entrega_pedido: {item.data_entrega_pedido}")
            
            # Somar quantidades
            qtd_total = sum(float(i.qtd_saldo_produto_pedido or 0) for i in itens_carteira)
            peso_total = sum(float(i.peso or 0) for i in itens_carteira if i.peso)
            
            print(f"\n📊 TOTAIS:")
            print(f"   Quantidade total: {qtd_total}")
            print(f"   Peso total: {peso_total} kg")
            
            # 2. Buscar na Separacao se tiver lote
            if item.separacao_lote_id:
                print(f"\n2. BUSCANDO NA SEPARAÇÃO (Lote: {item.separacao_lote_id}):")
                print("-" * 40)
                
                separacoes = Separacao.query.filter_by(
                    separacao_lote_id=item.separacao_lote_id
                ).all()
                
                if separacoes:
                    print(f"✅ Encontradas {len(separacoes)} separações")
                    
                    # Verificar pedido_cliente único
                    pedidos_cliente = set()
                    for sep in separacoes:
                        if hasattr(sep, 'pedido_cliente') and sep.pedido_cliente:
                            pedidos_cliente.add(sep.pedido_cliente)
                    
                    if pedidos_cliente:
                        print(f"\n📌 PEDIDO_CLIENTE na Separação: {', '.join(pedidos_cliente)}")
                    
                    # Pegar primeira separação para ver campos
                    sep = separacoes[0]
                    print(f"\n📋 DADOS DA SEPARAÇÃO:")
                    print(f"   separacao_lote_id: {sep.separacao_lote_id}")
                    print(f"   num_pedido: {sep.num_pedido}")
                    
                    # Verificar se existe campo pedido_cliente
                    if hasattr(sep, 'pedido_cliente'):
                        print(f"   pedido_cliente: {sep.pedido_cliente}")
                    else:
                        print(f"   ⚠️ Campo 'pedido_cliente' NÃO EXISTE na Separacao")
                    
                    print(f"   cnpj_cpf: {sep.cnpj_cpf}")
                    print(f"   expedicao: {sep.expedicao}")
                    print(f"   agendamento: {sep.agendamento}")
                    print(f"   protocolo: {sep.protocolo}")
                    print(f"   tipo_envio: {sep.tipo_envio}")
                    
                    # Somar totais
                    qtd_sep = sum(float(s.qtd_saldo or 0) for s in separacoes if s.qtd_saldo)
                    peso_sep = sum(float(s.peso or 0) for s in separacoes if s.peso)
                    
                    print(f"\n📊 TOTAIS DA SEPARAÇÃO:")
                    print(f"   Quantidade: {qtd_sep}")
                    print(f"   Peso: {peso_sep} kg")
                    
                else:
                    print("❌ Nenhuma separação encontrada para este lote")
            else:
                print("\n⚠️ Pedido não tem separacao_lote_id")
            
            # 3. Buscar no Pedido
            print(f"\n3. BUSCANDO NA TABELA PEDIDOS:")
            print("-" * 40)
            
            # Buscar por num_pedido
            pedido = Pedido.query.filter_by(num_pedido='VCD2520950').first()
            
            if pedido:
                print(f"✅ Pedido encontrado na tabela Pedidos")
                print(f"\n📋 DADOS DO PEDIDO:")
                print(f"   num_pedido: {pedido.num_pedido}")
                print(f"   separacao_lote_id: {pedido.separacao_lote_id}")
                
                # Verificar se existe campo pedido_cliente
                if hasattr(pedido, 'pedido_cliente'):
                    print(f"   pedido_cliente: {pedido.pedido_cliente}")
                else:
                    print(f"   ⚠️ Campo 'pedido_cliente' NÃO EXISTE em Pedido")
                    
                print(f"   status: {pedido.status}")
                print(f"   cnpj_cpf: {pedido.cnpj_cpf}")
                print(f"   expedicao: {pedido.expedicao}")
                print(f"   agendamento: {pedido.agendamento}")
                print(f"   protocolo: {pedido.protocolo}")
                print(f"   peso_total: {pedido.peso_total}")
                print(f"   valor_saldo_total: {pedido.valor_saldo_total}")
            else:
                # Tentar buscar por separacao_lote_id
                if item.separacao_lote_id:
                    pedido = Pedido.query.filter_by(separacao_lote_id=item.separacao_lote_id).first()
                    if pedido:
                        print(f"✅ Pedido encontrado pelo lote {item.separacao_lote_id}")
                        print(f"\n📋 DADOS DO PEDIDO:")
                        print(f"   num_pedido: {pedido.num_pedido}")
                        print(f"   separacao_lote_id: {pedido.separacao_lote_id}")
                        
                        # Verificar se existe campo pedido_cliente
                        if hasattr(pedido, 'pedido_cliente'):
                            print(f"   pedido_cliente: {pedido.pedido_cliente}")
                        else:
                            print(f"   ⚠️ Campo 'pedido_cliente' NÃO EXISTE em Pedido")
                            
                        print(f"   status: {pedido.status}")
                    else:
                        print("❌ Pedido não encontrado na tabela Pedidos")
                else:
                    print("❌ Pedido não encontrado na tabela Pedidos")
            
            # 4. Produtos do pedido
            print(f"\n4. PRODUTOS DO PEDIDO:")
            print("-" * 40)
            for idx, item in enumerate(itens_carteira, 1):
                print(f"\nProduto {idx}:")
                print(f"   Código: {item.cod_produto}")
                print(f"   Nome: {item.nome_produto}")
                print(f"   Quantidade: {item.qtd_saldo_produto_pedido}")
                print(f"   Peso: {item.peso}")
            
            # 5. RESUMO FINAL
            print("\n" + "=" * 80)
            print("RESUMO PARA AGENDAMENTO NO PORTAL:")
            print("=" * 80)
            
            print(f"\n📌 IDENTIFICADOR CORRETO:")
            if item.pedido_cliente:
                print(f"   pedido_cliente (CarteiraPrincipal): {item.pedido_cliente}")
            else:
                print(f"   ⚠️ pedido_cliente está VAZIO na CarteiraPrincipal")
            
            # Verificar se pedido_cliente é o que devemos usar no portal
            print(f"\n🔍 ANÁLISE:")
            print(f"   - O campo pedido_cliente na CarteiraPrincipal é: {item.pedido_cliente}")
            print(f"   - Este é o número que deve ser usado no portal Atacadão")
            print(f"   - Se estiver vazio, pode ser que o portal use outro identificador")
            
            if item.agendamento:
                print(f"\n⚠️ ATENÇÃO: Este pedido já tem agendamento:")
                print(f"   Data: {item.agendamento}")
                print(f"   Hora: {item.hora_agendamento}")
                print(f"   Protocolo: {item.protocolo}")
                print(f"   Confirmado: {item.agendamento_confirmado}")
            
        else:
            print("❌ Pedido VCD2520950 não encontrado na CarteiraPrincipal")

if __name__ == "__main__":
    main()