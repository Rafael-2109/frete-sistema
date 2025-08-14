#!/usr/bin/env python3
"""
Script para atualizar status de pedidos no Odoo em lote
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.odoo.utils.connection import get_odoo_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def listar_status_disponiveis():
    """Lista os status disponíveis no Odoo"""
    print("\n📋 STATUS DISPONÍVEIS NO ODOO:")
    print("-" * 40)
    print("draft      - Cotação/Rascunho")
    print("sent       - Cotação Enviada")
    print("sale       - Pedido de Venda Confirmado")
    print("done       - Bloqueado/Concluído")
    print("cancel     - Cancelado")
    print("-" * 40)

def buscar_pedidos_por_status(connection, status_atual):
    """Busca pedidos com um status específico"""
    try:
        domain = [('state', '=', status_atual)]
        campos = ['id', 'name', 'partner_id', 'amount_total', 'state', 'create_date']
        
        pedidos = connection.search_read('sale.order', domain, campos)
        return pedidos
    except Exception as e:
        logger.error(f"Erro ao buscar pedidos: {e}")
        return []

def buscar_pedidos_por_numeros(connection, numeros_pedidos):
    """Busca pedidos específicos por número"""
    try:
        domain = [('name', 'in', numeros_pedidos)]
        campos = ['id', 'name', 'partner_id', 'amount_total', 'state', 'create_date']
        
        pedidos = connection.search_read('sale.order', domain, campos)
        return pedidos
    except Exception as e:
        logger.error(f"Erro ao buscar pedidos: {e}")
        return []

def buscar_pedidos_duplicados(connection):
    """Busca possíveis pedidos duplicados (mesmo cliente, mesmo valor, criados hoje)"""
    try:
        from datetime import datetime, timedelta
        
        # Buscar pedidos criados nas últimas 24 horas
        data_inicio = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        
        domain = [
            ('create_date', '>=', data_inicio),
            ('state', 'in', ['draft', 'sent'])  # Apenas cotações
        ]
        campos = ['id', 'name', 'partner_id', 'amount_total', 'state', 'create_date']
        
        pedidos = connection.search_read('sale.order', domain, campos)
        
        # Agrupar por cliente e valor para identificar duplicatas
        grupos = {}
        for pedido in pedidos:
            if pedido.get('partner_id'):
                chave = (pedido['partner_id'][0], float(pedido.get('amount_total', 0)))
                if chave not in grupos:
                    grupos[chave] = []
                grupos[chave].append(pedido)
        
        # Filtrar apenas grupos com mais de 1 pedido (possíveis duplicatas)
        duplicados = {k: v for k, v in grupos.items() if len(v) > 1}
        
        return duplicados
    except Exception as e:
        logger.error(f"Erro ao buscar duplicados: {e}")
        return {}

def atualizar_status_pedidos(connection, pedido_ids, novo_status):
    """Atualiza o status de múltiplos pedidos"""
    try:
        sucesso = 0
        falhas = 0
        
        for pedido_id in pedido_ids:
            try:
                # Dependendo do novo status, pode ser necessário chamar métodos específicos
                if novo_status == 'sale':
                    # Confirmar pedido
                    connection.execute('sale.order', 'action_confirm', [pedido_id])
                elif novo_status == 'cancel':
                    # Cancelar pedido
                    connection.execute('sale.order', 'action_cancel', [pedido_id])
                elif novo_status == 'draft':
                    # Voltar para rascunho
                    connection.execute('sale.order', 'action_draft', [pedido_id])
                else:
                    # Atualizar diretamente o campo state
                    connection.write('sale.order', [pedido_id], {'state': novo_status})
                
                sucesso += 1
                logger.info(f"✅ Pedido ID {pedido_id} atualizado para {novo_status}")
                
            except Exception as e:
                falhas += 1
                logger.error(f"❌ Erro ao atualizar pedido ID {pedido_id}: {e}")
        
        return sucesso, falhas
        
    except Exception as e:
        logger.error(f"Erro geral na atualização: {e}")
        return 0, len(pedido_ids)

def menu_principal():
    """Menu interativo para atualização de status"""
    
    print("\n" + "=" * 60)
    print("ATUALIZAÇÃO DE STATUS DE PEDIDOS ODOO EM LOTE")
    print("=" * 60)
    
    connection = get_odoo_connection()
    if not connection:
        print("❌ Erro ao conectar com Odoo")
        return
    
    while True:
        print("\nEscolha uma opção:")
        print("1. Listar pedidos por status atual")
        print("2. Buscar pedidos específicos por número")
        print("3. Buscar possíveis pedidos duplicados (últimas 24h)")
        print("4. Atualizar status de pedidos selecionados")
        print("5. Cancelar pedidos duplicados em massa")
        print("0. Sair")
        
        opcao = input("\nOpção: ").strip()
        
        if opcao == '0':
            break
            
        elif opcao == '1':
            listar_status_disponiveis()
            status = input("\nDigite o status atual dos pedidos: ").strip().lower()
            
            pedidos = buscar_pedidos_por_status(connection, status)
            if pedidos:
                print(f"\n📋 Encontrados {len(pedidos)} pedidos com status '{status}':")
                for p in pedidos[:20]:  # Mostrar apenas os primeiros 20
                    print(f"  - {p['name']}: {p.get('partner_id', ['', 'Sem cliente'])[1]} - R$ {p.get('amount_total', 0):,.2f}")
                if len(pedidos) > 20:
                    print(f"  ... e mais {len(pedidos) - 20} pedidos")
            else:
                print(f"Nenhum pedido encontrado com status '{status}'")
                
        elif opcao == '2':
            numeros = input("\nDigite os números dos pedidos (separados por vírgula): ").strip()
            numeros_lista = [n.strip() for n in numeros.split(',')]
            
            pedidos = buscar_pedidos_por_numeros(connection, numeros_lista)
            if pedidos:
                print(f"\n📋 Encontrados {len(pedidos)} pedidos:")
                for p in pedidos:
                    print(f"  - {p['name']}: Status atual = {p['state']}")
            else:
                print("Nenhum pedido encontrado")
                
        elif opcao == '3':
            print("\n🔍 Buscando possíveis duplicados...")
            duplicados = buscar_pedidos_duplicados(connection)
            
            if duplicados:
                print(f"\n⚠️ Encontrados {len(duplicados)} grupos de possíveis duplicados:")
                for (cliente_id, valor), pedidos in duplicados.items():
                    print(f"\n  Cliente ID {cliente_id} - Valor R$ {valor:,.2f}:")
                    for p in pedidos:
                        print(f"    - {p['name']}: {p['state']} (criado em {p['create_date']})")
            else:
                print("✅ Nenhum pedido duplicado encontrado")
                
        elif opcao == '4':
            pedido_ids_str = input("\nDigite os IDs dos pedidos (separados por vírgula): ").strip()
            pedido_ids = [int(id.strip()) for id in pedido_ids_str.split(',') if id.strip().isdigit()]
            
            if not pedido_ids:
                print("❌ Nenhum ID válido fornecido")
                continue
            
            listar_status_disponiveis()
            novo_status = input("\nDigite o novo status: ").strip().lower()
            
            if novo_status not in ['draft', 'sent', 'sale', 'done', 'cancel']:
                print("❌ Status inválido")
                continue
            
            confirmar = input(f"\n⚠️ Confirma atualização de {len(pedido_ids)} pedidos para '{novo_status}'? (s/n): ")
            if confirmar.lower() == 's':
                sucesso, falhas = atualizar_status_pedidos(connection, pedido_ids, novo_status)
                print(f"\n📊 Resultado: {sucesso} sucessos, {falhas} falhas")
            else:
                print("Operação cancelada")
                
        elif opcao == '5':
            print("\n🔍 Buscando duplicados para cancelamento...")
            duplicados = buscar_pedidos_duplicados(connection)
            
            if not duplicados:
                print("✅ Nenhum duplicado encontrado")
                continue
            
            # Preparar lista de IDs para cancelar (manter apenas o primeiro de cada grupo)
            ids_cancelar = []
            for (cliente_id, valor), pedidos in duplicados.items():
                # Ordenar por data de criação e manter o mais antigo
                pedidos_ordenados = sorted(pedidos, key=lambda x: x['create_date'])
                # Cancelar todos exceto o primeiro
                for p in pedidos_ordenados[1:]:
                    ids_cancelar.append(p['id'])
                    print(f"  Marcado para cancelar: {p['name']}")
            
            if ids_cancelar:
                confirmar = input(f"\n⚠️ Confirma CANCELAMENTO de {len(ids_cancelar)} pedidos duplicados? (s/n): ")
                if confirmar.lower() == 's':
                    sucesso, falhas = atualizar_status_pedidos(connection, ids_cancelar, 'cancel')
                    print(f"\n📊 Resultado: {sucesso} cancelados, {falhas} falhas")
                else:
                    print("Operação cancelada")

if __name__ == "__main__":
    menu_principal()