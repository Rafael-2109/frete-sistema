"""
Script STANDALONE para buscar CTes com tipo_pedido = 'serv-industrializacao'
no período de 01/09/2025 até 17/11/2025

NÃO importa nada do app/ - funciona independente

OBJETIVO:
    Identificar pedidos de compras (purchase.order) originados de CTes
    com tipo_pedido='serv-industrializacao' no período especificado
"""

import xmlrpc.client
import ssl
import json
from datetime import datetime

# Configuração Odoo (hardcoded para funcionar standalone)
ODOO_CONFIG = {
    'url': 'https://odoo.nacomgoya.com.br',
    'database': 'odoo-17-ee-nacomgoya-prd',
    'username': 'rafael@conservascampobelo.com.br',
    'api_key': '67705b0986ff5c052e657f1c0ffd96ceb191af69',
}

def buscar_ctes_serv_industrializacao():
    """
    Busca CTes com tipo_pedido='serv-industrializacao' no período 01/09/2025 - 17/11/2025
    e identifica os Purchase Orders relacionados
    """

    # Credenciais do Odoo
    url = ODOO_CONFIG['url']
    db = ODOO_CONFIG['database']
    username = ODOO_CONFIG['username']
    password = ODOO_CONFIG['api_key']

    print("=" * 120)
    print("🔍 BUSCA DE CTes COM TIPO PEDIDO = 'serv-industrializacao'")
    print("=" * 120)
    print(f"Período: 01/09/2025 até 17/11/2025")
    print(f"Odoo URL: {url}")
    print(f"Odoo DB: {db}")
    print()

    try:
        # SSL Context
        ssl_context = ssl.create_default_context()
        if 'localhost' in url or '127.0.0.1' in url:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        # Conectar ao Odoo
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl_context)
        uid = common.authenticate(db, username, password, {})

        if not uid:
            print("❌ Falha na autenticação do Odoo")
            return

        print(f"✅ Autenticado no Odoo - UID: {uid}")
        print()

        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl_context)

        # ================================================
        # ETAPA 1: Buscar CTes (DFes com is_cte=True)
        # ================================================
        print("📊 ETAPA 1: BUSCANDO CTes NO ODOO:")
        print("-" * 120)

        # Filtro para CTes com tipo_pedido='serv-industrializacao' no período
        filtros_cte = [
            '&',
            '&',
            '&',
            ('active', '=', True),  # Apenas ativos
            ('is_cte', '=', True),  # Apenas CTes
            ('l10n_br_tipo_pedido', '=', 'serv-industrializacao'),  # Tipo específico
            '&',
            ('nfe_infnfe_ide_dhemi', '>=', '2025-09-01'),  # Data início
            ('nfe_infnfe_ide_dhemi', '<=', '2025-11-17')   # Data fim
        ]

        campos_cte = [
            'id', 'name', 'active', 'is_cte',
            'l10n_br_status', 'l10n_br_tipo_pedido',
            'protnfe_infnfe_chnfe',  # Chave
            'nfe_infnfe_ide_nnf',     # Número CTe
            'nfe_infnfe_ide_serie',   # Série
            'nfe_infnfe_ide_dhemi',   # Data emissão
            'nfe_infnfe_total_icmstot_vnf',  # Valor total
            'nfe_infnfe_emit_cnpj',   # CNPJ transportadora
            'nfe_infnfe_emit_xnome',  # Nome transportadora
            'purchase_fiscal_id',     # ID do Purchase Order
            'write_date'
        ]

        print(f"🔍 Filtro aplicado:")
        print(f"   - is_cte = True")
        print(f"   - l10n_br_tipo_pedido = 'serv-industrializacao'")
        print(f"   - Data emissão entre 01/09/2025 e 17/11/2025")
        print()

        ctes = models.execute_kw(
            db, uid, password,
            'l10n_br_ciel_it_account.dfe', 'search_read',
            [filtros_cte],
            {'fields': campos_cte, 'order': 'nfe_infnfe_ide_dhemi desc'}
        )

        if not ctes:
            print("⚠️ NENHUM CTe encontrado com os critérios especificados!")
            print()
            return

        print(f"✅ Encontrados {len(ctes)} CTes")
        print()

        # ================================================
        # ETAPA 2: Para cada CTe, buscar Purchase Order
        # ================================================
        print("=" * 120)
        print("📊 ETAPA 2: BUSCANDO PURCHASE ORDERS RELACIONADOS:")
        print("-" * 120)
        print()

        # Coletar IDs dos Purchase Orders
        purchase_order_ids = []
        for cte in ctes:
            if cte.get('purchase_fiscal_id'):
                # purchase_fiscal_id vem como [id, 'nome']
                po_id = cte['purchase_fiscal_id'][0] if isinstance(cte['purchase_fiscal_id'], list) else cte['purchase_fiscal_id']
                purchase_order_ids.append(po_id)

        # Remover duplicatas
        purchase_order_ids = list(set(purchase_order_ids))

        print(f"📦 {len(purchase_order_ids)} Purchase Orders únicos identificados")
        print()

        # Buscar detalhes dos Purchase Orders
        purchase_orders = {}
        if purchase_order_ids:
            campos_po = [
                'id', 'name', 'state', 'date_order',
                'partner_id', 'amount_total', 'currency_id',
                'l10n_br_tipo_pedido', 'create_date', 'write_date'
            ]

            pos = models.execute_kw(
                db, uid, password,
                'purchase.order', 'read',
                [purchase_order_ids],
                {'fields': campos_po}
            )

            # Criar mapa {po_id: po_data}
            for po in pos:
                purchase_orders[po['id']] = po

        # ================================================
        # ETAPA 3: Exibir resultados
        # ================================================
        print("=" * 120)
        print("📋 RESULTADOS:")
        print("=" * 120)
        print()

        for idx, cte in enumerate(ctes, 1):
            print(f"{'='*120}")
            print(f"🧾 CTe #{idx}")
            print(f"{'='*120}")
            print(f"  DFe ID (Odoo): {cte['id']}")
            print(f"  Número CTe: {cte.get('nfe_infnfe_ide_nnf')}/{cte.get('nfe_infnfe_ide_serie')}")
            print(f"  Chave: {cte.get('protnfe_infnfe_chnfe')}")
            print(f"  Data Emissão: {cte.get('nfe_infnfe_ide_dhemi')}")
            print(f"  Tipo Pedido: {cte.get('l10n_br_tipo_pedido')}")
            print(f"  Status Odoo: {cte.get('l10n_br_status')}")
            print(f"  Valor Total: R$ {cte.get('nfe_infnfe_total_icmstot_vnf', 0):.2f}")
            print(f"  Transportadora: {cte.get('nfe_infnfe_emit_xnome')} ({cte.get('nfe_infnfe_emit_cnpj')})")
            print()

            # Purchase Order relacionado
            if cte.get('purchase_fiscal_id'):
                po_id = cte['purchase_fiscal_id'][0] if isinstance(cte['purchase_fiscal_id'], list) else cte['purchase_fiscal_id']
                po_name = cte['purchase_fiscal_id'][1] if isinstance(cte['purchase_fiscal_id'], list) and len(cte['purchase_fiscal_id']) > 1 else f"PO-{po_id}"

                print(f"  🔗 PURCHASE ORDER RELACIONADO:")
                print(f"     ID: {po_id}")
                print(f"     Nome: {po_name}")

                # Detalhes do PO (se buscamos)
                if po_id in purchase_orders:
                    po = purchase_orders[po_id]
                    print(f"     Estado: {po.get('state')}")
                    print(f"     Data Pedido: {po.get('date_order')}")
                    print(f"     Valor Total: {po.get('amount_total')} {po.get('currency_id', ['', 'N/A'])[1] if isinstance(po.get('currency_id'), list) else 'N/A'}")
                    print(f"     Fornecedor: {po.get('partner_id', ['', 'N/A'])[1] if isinstance(po.get('partner_id'), list) else 'N/A'}")
                    print(f"     Tipo Pedido PO: {po.get('l10n_br_tipo_pedido')}")
            else:
                print(f"  ⚠️ Purchase Order: NÃO VINCULADO")

            print()

        # ================================================
        # RESUMO
        # ================================================
        print("=" * 120)
        print("📊 RESUMO:")
        print("=" * 120)
        print(f"  Total CTes encontrados: {len(ctes)}")
        print(f"  CTes com Purchase Order: {sum(1 for c in ctes if c.get('purchase_fiscal_id'))}")
        print(f"  CTes sem Purchase Order: {sum(1 for c in ctes if not c.get('purchase_fiscal_id'))}")
        print(f"  Purchase Orders únicos: {len(purchase_order_ids)}")
        print("=" * 120)

    except Exception as e:
        print(f"❌ Erro durante a busca: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    buscar_ctes_serv_industrializacao()
