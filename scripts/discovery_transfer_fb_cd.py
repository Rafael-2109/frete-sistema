"""
Discovery: IDs necessarios para Transferencia FB -> CD
======================================================

Consulta Odoo para encontrar:
1. Picking Type de SAIDA da FB (stock.picking.type, code='outgoing', company_id=1)
2. Partner ID do CD na FB (res.partner, CNPJ 61724241000330, company_id=1)
3. Operacao Fiscal de Transferencia entre filiais (l10n_br.fiscal.operation)
4. Localizacoes de estoque (stock.location) — confirmar IDs
5. Pickings existentes FB→CD como referencia
6. Modulo inter-company instalado?
7. Automation rules (robo de fatura)

Uso:
    source .venv/bin/activate
    python scripts/discovery_transfer_fb_cd.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app

app = create_app()

with app.app_context():
    from app.odoo.utils.connection import get_odoo_connection

    odoo = get_odoo_connection()

    resultados = {}

    # ==========================================
    # 1. Picking Types de SAIDA da FB
    # ==========================================
    print("\n" + "=" * 60)
    print("1. PICKING TYPES DE SAIDA DA FB (company_id=1, code=outgoing)")
    print("=" * 60)

    try:
        picking_types = odoo.search_read(
            'stock.picking.type',
            [['company_id', '=', 1], ['code', '=', 'outgoing']],
            fields=['id', 'name', 'warehouse_id', 'default_location_src_id',
                    'default_location_dest_id', 'sequence_code'],
        )
        resultados['picking_types_saida_fb'] = picking_types
        for pt in picking_types:
            print(f"  ID={pt['id']} | {pt['name']} | warehouse={pt.get('warehouse_id')} "
                  f"| src={pt.get('default_location_src_id')} "
                  f"| dest={pt.get('default_location_dest_id')} "
                  f"| seq={pt.get('sequence_code')}")
        if not picking_types:
            print("  NENHUM encontrado!")
    except Exception as e:
        print(f"  ERRO: {e}")

    # Tambem buscar TODOS os picking types da FB para referencia
    print("\n  --- Todos picking types da FB ---")
    try:
        all_pt_fb = odoo.search_read(
            'stock.picking.type',
            [['company_id', '=', 1]],
            fields=['id', 'name', 'code', 'warehouse_id',
                    'default_location_src_id', 'default_location_dest_id'],
        )
        resultados['all_picking_types_fb'] = all_pt_fb
        for pt in all_pt_fb:
            print(f"  ID={pt['id']} | code={pt['code']} | {pt['name']} "
                  f"| src={pt.get('default_location_src_id')} "
                  f"| dest={pt.get('default_location_dest_id')}")
    except Exception as e:
        print(f"  ERRO: {e}")

    # ==========================================
    # 2. Partner ID do CD na FB
    # ==========================================
    print("\n" + "=" * 60)
    print("2. PARTNER ID DO CD NA FB (CNPJ 61724241000330)")
    print("=" * 60)

    try:
        partners_cd = odoo.search_read(
            'res.partner',
            [['l10n_br_cnpj_cpf', 'ilike', '61724241000330']],
            fields=['id', 'name', 'l10n_br_cnpj_cpf', 'company_id', 'is_company'],
        )
        resultados['partners_cd'] = partners_cd
        for p in partners_cd:
            print(f"  ID={p['id']} | {p['name']} | CNPJ={p.get('l10n_br_cnpj_cpf')} "
                  f"| company={p.get('company_id')} | is_company={p.get('is_company')}")
        if not partners_cd:
            print("  NENHUM encontrado!")
    except Exception as e:
        print(f"  ERRO: {e}")

    # Tambem buscar partner da FB no CD (para picking de entrada no CD)
    print("\n  --- Partner FB no CD (CNPJ 61724241000178) ---")
    try:
        partners_fb = odoo.search_read(
            'res.partner',
            [['l10n_br_cnpj_cpf', 'ilike', '61724241000178']],
            fields=['id', 'name', 'l10n_br_cnpj_cpf', 'company_id', 'is_company'],
        )
        resultados['partners_fb'] = partners_fb
        for p in partners_fb:
            print(f"  ID={p['id']} | {p['name']} | CNPJ={p.get('l10n_br_cnpj_cpf')} "
                  f"| company={p.get('company_id')} | is_company={p.get('is_company')}")
    except Exception as e:
        print(f"  ERRO: {e}")

    # ==========================================
    # 3. Operacao Fiscal de Transferencia
    # ==========================================
    print("\n" + "=" * 60)
    print("3. OPERACOES FISCAIS DE TRANSFERENCIA")
    print("=" * 60)

    try:
        ops_transfer = odoo.search_read(
            'l10n_br_fiscal.operation',
            [['name', 'ilike', 'transfer']],
            fields=['id', 'name', 'fiscal_type', 'company_id', 'state'],
        )
        resultados['ops_transfer'] = ops_transfer
        for op in ops_transfer:
            print(f"  ID={op['id']} | {op['name']} | tipo={op.get('fiscal_type')} "
                  f"| company={op.get('company_id')} | state={op.get('state')}")
        if not ops_transfer:
            print("  NENHUM com 'transfer' no nome. Buscando 'remessa'...")
    except Exception as e:
        print(f"  ERRO: {e}")

    # Buscar alternativas
    for termo in ['remessa', 'venda', 'saida', 'transferencia']:
        try:
            ops = odoo.search_read(
                'l10n_br_fiscal.operation',
                [['name', 'ilike', termo], ['company_id', 'in', [1, False]]],
                fields=['id', 'name', 'fiscal_type', 'company_id'],
                limit=10,
            )
            if ops:
                print(f"\n  --- Operacoes com '{termo}' (company 1 ou global) ---")
                for op in ops:
                    print(f"  ID={op['id']} | {op['name']} | tipo={op.get('fiscal_type')} "
                          f"| company={op.get('company_id')}")
        except Exception:
            pass

    # ==========================================
    # 4. Localizacoes de Estoque
    # ==========================================
    print("\n" + "=" * 60)
    print("4. LOCALIZACOES DE ESTOQUE (FB e CD)")
    print("=" * 60)

    for comp_id, comp_nome in [(1, 'FB'), (4, 'CD')]:
        print(f"\n  --- {comp_nome} (company {comp_id}) ---")
        try:
            locs = odoo.search_read(
                'stock.location',
                [['company_id', '=', comp_id],
                 ['usage', 'in', ['internal', 'transit', 'customer']]],
                fields=['id', 'name', 'complete_name', 'usage'],
            )
            resultados[f'locations_{comp_nome.lower()}'] = locs
            for loc in locs:
                print(f"  ID={loc['id']} | {loc.get('complete_name') or loc['name']} "
                      f"| usage={loc['usage']}")
        except Exception as e:
            print(f"  ERRO: {e}")

    # Location Partners/Customers (sem company)
    print("\n  --- Parceiros/Clientes (sem company) ---")
    try:
        locs_customer = odoo.search_read(
            'stock.location',
            [['usage', '=', 'customer']],
            fields=['id', 'name', 'complete_name', 'company_id'],
            limit=5,
        )
        for loc in locs_customer:
            print(f"  ID={loc['id']} | {loc.get('complete_name') or loc['name']} "
                  f"| company={loc.get('company_id')}")
    except Exception as e:
        print(f"  ERRO: {e}")

    # ==========================================
    # 5. Pickings Existentes FB → CD
    # ==========================================
    print("\n" + "=" * 60)
    print("5. PICKINGS EXISTENTES FB → CD (referencia)")
    print("=" * 60)

    try:
        pickings_fb_cd = odoo.search_read(
            'stock.picking',
            [['company_id', '=', 1],
             ['picking_type_code', '=', 'outgoing'],
             ['state', '=', 'done']],
            fields=['id', 'name', 'picking_type_id', 'partner_id',
                    'location_id', 'location_dest_id', 'origin',
                    'carrier_id'],
            limit=10,
            order='id desc',
        )
        resultados['pickings_fb_saida'] = pickings_fb_cd
        for pk in pickings_fb_cd:
            partner_name = pk.get('partner_id', [None, ''])[1] if isinstance(pk.get('partner_id'), (list, tuple)) else pk.get('partner_id')
            print(f"  ID={pk['id']} | {pk['name']} | type={pk.get('picking_type_id')} "
                  f"| partner={partner_name} "
                  f"| src={pk.get('location_id')} | dest={pk.get('location_dest_id')} "
                  f"| origin={pk.get('origin')}")
        if not pickings_fb_cd:
            print("  NENHUM picking de saida encontrado na FB!")
    except Exception as e:
        print(f"  ERRO: {e}")

    # ==========================================
    # 6. Modulo Inter-Company
    # ==========================================
    print("\n" + "=" * 60)
    print("6. MODULO INTER-COMPANY")
    print("=" * 60)

    try:
        modules_ic = odoo.search_read(
            'ir.module.module',
            [['name', 'ilike', 'inter_company'], ['state', '=', 'installed']],
            fields=['id', 'name', 'shortdesc', 'state'],
        )
        resultados['modulos_inter_company'] = modules_ic
        for m in modules_ic:
            print(f"  ID={m['id']} | {m['name']} | {m.get('shortdesc')} | state={m['state']}")
        if not modules_ic:
            print("  Nenhum modulo inter-company instalado")
    except Exception as e:
        print(f"  ERRO: {e}")

    # Config inter-company nas companies
    try:
        companies = odoo.search_read(
            'res.company',
            [['id', 'in', [1, 4]]],
            fields=['id', 'name'],
        )
        for c in companies:
            print(f"  Company {c['id']}: {c['name']}")
    except Exception as e:
        print(f"  ERRO: {e}")

    # ==========================================
    # 7. NFs Existentes FB → CD (account.move)
    # ==========================================
    print("\n" + "=" * 60)
    print("7. INVOICES/NFS FB → CD (referencia)")
    print("=" * 60)

    try:
        invoices_fb_cd = odoo.search_read(
            'account.move',
            [['company_id', '=', 1],
             ['move_type', '=', 'out_invoice'],
             ['state', '=', 'posted']],
            fields=['id', 'name', 'partner_id', 'l10n_br_edoc_purpose',
                    'fiscal_operation_id', 'invoice_origin'],
            limit=10,
            order='id desc',
        )
        resultados['invoices_fb_saida'] = invoices_fb_cd
        for inv in invoices_fb_cd:
            partner_name = inv.get('partner_id', [None, ''])[1] if isinstance(inv.get('partner_id'), (list, tuple)) else inv.get('partner_id')
            print(f"  ID={inv['id']} | {inv['name']} | partner={partner_name} "
                  f"| op_fiscal={inv.get('fiscal_operation_id')} "
                  f"| purpose={inv.get('l10n_br_edoc_purpose')} "
                  f"| origin={inv.get('invoice_origin')}")
        if not invoices_fb_cd:
            print("  NENHUMA invoice de saida encontrada na FB!")
    except Exception as e:
        print(f"  ERRO: {e}")

    # ==========================================
    # 8. Automation Rules (robo de fatura)
    # ==========================================
    print("\n" + "=" * 60)
    print("8. AUTOMATION RULES (ROBO DE FATURA)")
    print("=" * 60)

    try:
        automations = odoo.search_read(
            'base.automation',
            [['model_id.model', '=', 'stock.picking'], ['active', '=', True]],
            fields=['id', 'name', 'trigger', 'action_server_ids'],
        )
        resultados['automations_picking'] = automations
        for a in automations:
            print(f"  ID={a['id']} | {a['name']} | trigger={a.get('trigger')} "
                  f"| actions={a.get('action_server_ids')}")
        if not automations:
            print("  Nenhuma automation rule para stock.picking")
    except Exception as e:
        print(f"  ERRO: {e}")

    # ==========================================
    # RESUMO
    # ==========================================
    print("\n" + "=" * 60)
    print("RESUMO — IDs PARA CONFIGURAR")
    print("=" * 60)

    # Salvar resultados completos em JSON
    output_path = os.path.join(
        os.path.dirname(__file__),
        'discovery_transfer_fb_cd_resultado.json'
    )
    with open(output_path, 'w') as f:
        json.dump(resultados, f, indent=2, default=str)
    print(f"\nResultados completos salvos em: {output_path}")

    print("\nPreencha as constantes em recebimento_lf_odoo_service.py:")
    print("  PICKING_TYPE_OUT_FB = ???")
    print("  PARTNER_CD_IN_FB = ???")
    print("  OPERACAO_TRANSFERENCIA_ID = ???")
    print("\nVerifique os resultados acima e atualize o service.")
