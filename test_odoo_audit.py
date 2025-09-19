#!/usr/bin/env python3
"""
Script para buscar campos de auditoria de um pedido no Odoo
"""

from app.odoo.utils.connection import get_odoo_connection
from datetime import datetime
import json
from decimal import Decimal

def buscar_auditoria_pedido(num_pedido):
    """
    Busca todos os campos de auditoria e informações relevantes de um pedido no Odoo
    """

    print(f"\n{'='*80}")
    print(f"BUSCANDO AUDITORIA DO PEDIDO: {num_pedido}")
    print(f"{'='*80}\n")

    try:
        # Obter conexão com Odoo
        connection = get_odoo_connection()
        if not connection:
            print("❌ Erro: Não foi possível conectar ao Odoo")
            return None

        print("✅ Conectado ao Odoo")

        # Campos de auditoria e outros relevantes
        campos_buscar = [
            # Identificação
            'name',
            'state',
            'invoice_status',

            # Datas de auditoria
            'create_date',
            'create_uid',
            'write_date',
            'write_uid',

            # Datas do pedido
            'date_order',
            # 'confirmation_date',  # Removido - não existe nesta versão
            'commitment_date',
            # 'expected_date',  # Pode não existir
            # 'effective_date',  # Pode não existir

            # Valores
            'amount_total',
            'amount_untaxed',
            'amount_tax',

            # Cliente
            'partner_id',

            # Outros campos úteis
            'l10n_br_pedido_compra',  # Pedido de compra do cliente
            'carrier_id',              # Transportadora
            'incoterm',               # Incoterm
            'picking_policy',         # Política de entrega
            'warehouse_id',           # Armazém

            # Campos de entrega/faturamento (podem não existir)
            # 'delivery_count',
            # 'invoice_count',

            # Observações
            'note',
            # 'fiscal_position_id',
        ]

        print(f"Buscando pedido {num_pedido} com {len(campos_buscar)} campos...")

        # Buscar pedido
        pedidos = connection.search_read(
            'sale.order',
            [('name', '=', num_pedido)],
            campos_buscar,
            limit=1
        )

        if not pedidos:
            print(f"❌ Pedido {num_pedido} não encontrado no Odoo")
            return None

        pedido = pedidos[0]

        print("\n" + "="*60)
        print("DADOS DO PEDIDO")
        print("="*60)

        # Exibir informações formatadas
        print("\n📋 IDENTIFICAÇÃO:")
        print(f"  - Número: {pedido.get('name')}")
        print(f"  - Estado: {pedido.get('state')}")
        print(f"  - Status Faturamento: {pedido.get('invoice_status')}")

        print("\n📅 AUDITORIA:")

        # Datas de criação
        create_date = pedido.get('create_date')
        if create_date:
            print(f"  - Data Criação: {create_date}")

        create_uid = pedido.get('create_uid')
        if create_uid:
            if isinstance(create_uid, (list, tuple)):
                print(f"  - Criado por: {create_uid[1]} (ID: {create_uid[0]})")
            else:
                print(f"  - Criado por ID: {create_uid}")

        # Datas de modificação
        write_date = pedido.get('write_date')
        if write_date:
            print(f"  - Última Modificação: {write_date}")

            # Calcular tempo desde última modificação
            if isinstance(write_date, str):
                try:
                    write_dt = datetime.fromisoformat(write_date.replace('Z', '+00:00'))
                    tempo_decorrido = datetime.now(write_dt.tzinfo) - write_dt
                    print(f"    (há {tempo_decorrido.days} dias e {tempo_decorrido.seconds//3600} horas)")
                except:
                    pass

        write_uid = pedido.get('write_uid')
        if write_uid:
            if isinstance(write_uid, (list, tuple)):
                print(f"  - Modificado por: {write_uid[1]} (ID: {write_uid[0]})")
            else:
                print(f"  - Modificado por ID: {write_uid}")

        print("\n📆 DATAS DO PEDIDO:")
        if pedido.get('date_order'):
            print(f"  - Data do Pedido: {pedido.get('date_order')}")
        if pedido.get('confirmation_date'):
            print(f"  - Data Confirmação: {pedido.get('confirmation_date')}")
        if pedido.get('commitment_date'):
            print(f"  - Data Compromisso: {pedido.get('commitment_date')}")
        if pedido.get('expected_date'):
            print(f"  - Data Esperada: {pedido.get('expected_date')}")
        if pedido.get('effective_date'):
            print(f"  - Data Efetiva: {pedido.get('effective_date')}")

        print("\n💰 VALORES:")
        print(f"  - Valor Total: R$ {pedido.get('amount_total', 0):,.2f}")
        print(f"  - Valor sem Impostos: R$ {pedido.get('amount_untaxed', 0):,.2f}")
        print(f"  - Impostos: R$ {pedido.get('amount_tax', 0):,.2f}")

        print("\n📦 INFORMAÇÕES ADICIONAIS:")

        # Cliente
        partner = pedido.get('partner_id')
        if partner:
            if isinstance(partner, (list, tuple)):
                print(f"  - Cliente: {partner[1]} (ID: {partner[0]})")
            else:
                print(f"  - Cliente ID: {partner}")

        # Pedido de compra do cliente
        if pedido.get('l10n_br_pedido_compra'):
            print(f"  - Pedido Cliente: {pedido.get('l10n_br_pedido_compra')}")

        # Transportadora
        carrier = pedido.get('carrier_id')
        if carrier:
            if isinstance(carrier, (list, tuple)):
                print(f"  - Transportadora: {carrier[1]}")
            else:
                print(f"  - Transportadora ID: {carrier}")

        # Incoterm
        incoterm = pedido.get('incoterm')
        if incoterm:
            if isinstance(incoterm, (list, tuple)):
                print(f"  - Incoterm: {incoterm[1]}")
            else:
                print(f"  - Incoterm: {incoterm}")

        # Política de entrega
        if pedido.get('picking_policy'):
            print(f"  - Política Entrega: {pedido.get('picking_policy')}")

        # Armazém
        warehouse = pedido.get('warehouse_id')
        if warehouse:
            if isinstance(warehouse, (list, tuple)):
                print(f"  - Armazém: {warehouse[1]}")
            else:
                print(f"  - Armazém ID: {warehouse}")

        # Contadores
        if pedido.get('delivery_count') is not None:
            print(f"  - Entregas: {pedido.get('delivery_count')}")
        if pedido.get('invoice_count') is not None:
            print(f"  - Faturas: {pedido.get('invoice_count')}")

        # Observações
        if pedido.get('note'):
            print(f"\n📝 OBSERVAÇÕES:")
            print(f"  {pedido.get('note')[:200]}{'...' if len(str(pedido.get('note', ''))) > 200 else ''}")

        # Agora buscar as linhas do pedido para ver os produtos
        print("\n" + "="*60)
        print("BUSCANDO LINHAS DO PEDIDO")
        print("="*60)

        # Buscar linhas do pedido
        pedido_id = pedido.get('id')
        if pedido_id:
            linhas = connection.search_read(
                'sale.order.line',
                [('order_id', '=', pedido_id)],
                ['product_id', 'name', 'product_uom_qty', 'qty_delivered', 'qty_invoiced',
                 'price_unit', 'price_subtotal', 'state', 'create_date', 'write_date'],
                limit=100
            )

            print(f"\n📦 PRODUTOS ({len(linhas)} itens):")

            total_calculado = 0
            for i, linha in enumerate(linhas, 1):
                produto = linha.get('product_id')
                if isinstance(produto, (list, tuple)):
                    produto_nome = produto[1]
                else:
                    produto_nome = linha.get('name', 'Produto')

                qtd = linha.get('product_uom_qty', 0)
                preco = linha.get('price_unit', 0)
                subtotal = linha.get('price_subtotal', 0)
                total_calculado += subtotal

                print(f"\n  {i}. {produto_nome[:50]}...")
                print(f"     - Qtd Pedida: {qtd}")
                print(f"     - Qtd Entregue: {linha.get('qty_delivered', 0)}")
                print(f"     - Qtd Faturada: {linha.get('qty_invoiced', 0)}")
                print(f"     - Preço Unit: R$ {preco:,.2f}")
                print(f"     - Subtotal: R$ {subtotal:,.2f}")

                # Auditoria da linha
                if linha.get('write_date'):
                    print(f"     - Última Modif. Linha: {linha.get('write_date')}")

            print(f"\n💰 TOTAL CALCULADO DAS LINHAS: R$ {total_calculado:,.2f}")
            print(f"💰 TOTAL DO PEDIDO (CABEÇALHO): R$ {pedido.get('amount_total', 0):,.2f}")

            diferenca = abs(pedido.get('amount_total', 0) - total_calculado)
            if diferenca > 0.01:
                print(f"⚠️  DIFERENÇA DETECTADA: R$ {diferenca:,.2f}")

        # Salvar JSON completo
        filename = f"audit_odoo_{num_pedido}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            # Converter para formato serializável
            def converter(obj):
                if isinstance(obj, (list, tuple)) and len(obj) == 2:
                    return {"id": obj[0], "name": obj[1]}
                return str(obj)

            json.dump(pedido, f, ensure_ascii=False, indent=2, default=converter)

        print(f"\n💾 Dados completos salvos em: {filename}")

        return pedido

    except Exception as e:
        print(f"❌ Erro ao buscar pedido: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Buscar o pedido solicitado
    pedido = buscar_auditoria_pedido('VCD2563651')

    if pedido:
        print("\n" + "="*80)
        print("✅ BUSCA CONCLUÍDA COM SUCESSO")
        print("="*80)