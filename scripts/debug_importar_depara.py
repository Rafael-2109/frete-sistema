#!/usr/bin/env python3
"""Script para debug da importação De-Para do Odoo."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from app.odoo.utils.connection import get_odoo_connection

odoo = get_odoo_connection()

print("="*60)
print("DEBUG: IMPORTAÇÃO DE-PARA DO ODOO")
print("="*60)

# 1. Testar filtro com OR
print("\n1. Testando filtro com OR (product_code AND (product_id OR product_tmpl_id))...")
domain = [
    ('product_code', '!=', False),
    '|',
    ('product_id', '!=', False),
    ('product_tmpl_id', '!=', False)
]
print(f"   Domain: {domain}")

try:
    ids = odoo.search('product.supplierinfo', domain, limit=20)
    print(f"   ✅ Encontrados: {len(ids)} registros")
except Exception as e:
    print(f"   ❌ Erro: {e}")
    ids = []

# 2. Se encontrou, ler os dados
if ids:
    print("\n2. Lendo dados dos supplierinfos...")
    dados = odoo.read('product.supplierinfo', ids[:5], [
        'id', 'partner_id', 'product_id', 'product_tmpl_id',
        'product_code', 'product_uom', 'price'
    ])
    for d in dados:
        print(f"   - ID {d['id']}: partner={d.get('partner_id')}, product_id={d.get('product_id')}, tmpl_id={d.get('product_tmpl_id')}, code={d.get('product_code')}")

    # 3. Verificar templates
    print("\n3. Verificando templates...")
    tmpl_ids = [d['product_tmpl_id'][0] for d in dados if d.get('product_tmpl_id') and d['product_tmpl_id']]
    if tmpl_ids:
        templates = odoo.read('product.template', tmpl_ids, ['id', 'default_code', 'name'])
        for t in templates:
            print(f"   - Template {t['id']}: default_code={t.get('default_code')}, name={t.get('name')[:50] if t.get('name') else 'N/A'}")
    else:
        print("   Nenhum template encontrado")

    # 4. Verificar partners
    print("\n4. Verificando partners (CNPJs)...")
    partner_ids = [d['partner_id'][0] for d in dados if d.get('partner_id') and d['partner_id']]
    if partner_ids:
        partners = odoo.read('res.partner', partner_ids, ['id', 'l10n_br_cnpj', 'name'])
        for p in partners:
            print(f"   - Partner {p['id']}: l10n_br_cnpj={p.get('l10n_br_cnpj')}, name={p.get('name')[:40] if p.get('name') else 'N/A'}")
    else:
        print("   Nenhum partner encontrado")

    # 5. Simular lógica de importação
    print("\n5. Simulando lógica de importação...")
    from app.recebimento.services.depara_service import DeParaService
    service = DeParaService()

    for si in dados:
        partner_id = si.get('partner_id', [None, None])[0] if si.get('partner_id') else None
        product_id = si.get('product_id', [None, None])[0] if si.get('product_id') else None
        tmpl_id = si.get('product_tmpl_id', [None, None])[0] if si.get('product_tmpl_id') else None

        print(f"\n   Supplierinfo {si['id']}:")
        print(f"      partner_id: {partner_id}")
        print(f"      product_id: {product_id}")
        print(f"      tmpl_id: {tmpl_id}")
        print(f"      product_code: {si.get('product_code')}")

        if not partner_id:
            print("      ❌ SKIP: sem partner_id")
            continue

        if not product_id and not tmpl_id:
            print("      ❌ SKIP: sem product_id e sem tmpl_id")
            continue

        # Buscar CNPJ do partner
        partner_data = odoo.read('res.partner', [partner_id], ['l10n_br_cnpj', 'name'])
        if partner_data:
            cnpj = service._limpar_cnpj(partner_data[0].get('l10n_br_cnpj', ''))
            print(f"      cnpj: {cnpj}")
            if not cnpj:
                print("      ❌ SKIP: partner sem CNPJ")
                continue

        # Buscar default_code
        if tmpl_id:
            tmpl_data = odoo.read('product.template', [tmpl_id], ['default_code', 'name'])
            if tmpl_data:
                default_code = tmpl_data[0].get('default_code')
                print(f"      default_code (template): {default_code}")
                if not default_code:
                    # Buscar variante
                    variant_ids = odoo.search('product.product', [('product_tmpl_id', '=', tmpl_id)], limit=1)
                    if variant_ids:
                        variant_data = odoo.read('product.product', variant_ids, ['default_code'])
                        if variant_data:
                            default_code = variant_data[0].get('default_code')
                            print(f"      default_code (variante): {default_code}")

                if not default_code:
                    print("      ❌ SKIP: produto sem default_code")
                    continue

        cod_fornecedor = si.get('product_code', '')
        if not cod_fornecedor:
            print("      ❌ SKIP: sem product_code")
            continue

        print(f"      ✅ IMPORTÁVEL: {cod_fornecedor} -> {default_code}")

else:
    print("\n⚠️ Nenhum supplierinfo encontrado com o filtro")

    # Testar filtros separados
    print("\nTestando filtros separados:")

    print("\n  a) Apenas product_code != False:")
    ids_code = odoo.search('product.supplierinfo', [('product_code', '!=', False)], limit=10)
    print(f"     Encontrados: {len(ids_code)}")

    print("\n  b) Apenas product_tmpl_id != False:")
    ids_tmpl = odoo.search('product.supplierinfo', [('product_tmpl_id', '!=', False)], limit=10)
    print(f"     Encontrados: {len(ids_tmpl)}")

    print("\n  c) product_code != False AND product_tmpl_id != False:")
    ids_both = odoo.search('product.supplierinfo', [
        ('product_code', '!=', False),
        ('product_tmpl_id', '!=', False)
    ], limit=10)
    print(f"     Encontrados: {len(ids_both)}")

    if ids_both:
        dados = odoo.read('product.supplierinfo', ids_both[:3], ['id', 'partner_id', 'product_code', 'product_tmpl_id'])
        for d in dados:
            print(f"     - {d}")

print("\n" + "="*60)
print("FIM DO DEBUG")
print("="*60)
