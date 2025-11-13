"""
Testar Download de PDF de Pedido Existente
===========================================

OBJETIVO: Buscar um pedido que já existe no banco E tem dfe_id no Odoo,
          então testar o download do PDF/XML

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402
from app.manufatura.models import PedidoCompras  # noqa: E402
from app.odoo.services.entrada_material_service import EntradaMaterialService  # noqa: E402

print("=" * 80)
print("🔍 TESTE - Download PDF de Pedido Existente")
print("=" * 80)

app = create_app()

with app.app_context():
    odoo = get_odoo_connection()
    service = EntradaMaterialService()

    # 1. Buscar pedido local com odoo_id
    print("\n1️⃣ Buscando pedido local...")

    pedido_local = PedidoCompras.query.filter(
        PedidoCompras.odoo_id.isnot(None)
    ).first()

    if not pedido_local:
        print("❌ Nenhum pedido local com odoo_id encontrado!")
        sys.exit(1)

    print(f"✅ Pedido encontrado: {pedido_local.num_pedido}")
    print(f"   odoo_id: {pedido_local.odoo_id}")
    print(f"   Fornecedor: {pedido_local.raz_social}")
    print(f"   CNPJ: {pedido_local.cnpj_fornecedor}")

    # 2. Buscar dfe_id no Odoo
    print("\n2️⃣ Buscando dfe_id no Odoo...")

    try:
        pedido_odoo = odoo.execute_kw(
            'purchase.order',
            'read',
            [[int(pedido_local.odoo_id)]],
            {'fields': ['id', 'name', 'dfe_id', 'partner_id']}
        )

        if not pedido_odoo or len(pedido_odoo) == 0:
            print(f"❌ Pedido {pedido_local.odoo_id} não encontrado no Odoo!")
            sys.exit(1)

        dfe_info = pedido_odoo[0].get('dfe_id')

        if not dfe_info:
            print("⚠️  Este pedido não tem dfe_id vinculado no Odoo")
            print("   Buscando outro pedido...")

            # Tentar encontrar algum com dfe_id
            pedidos_com_dfe = odoo.execute_kw(
                'purchase.order',
                'search_read',
                [[
                    ['dfe_id', '!=', False],
                    ['state', 'in', ['purchase', 'done']]
                ]],
                {'fields': ['id', 'name', 'dfe_id', 'partner_id'], 'limit': 1}
            )

            if not pedidos_com_dfe:
                print("❌ Nenhum pedido com dfe_id encontrado no Odoo!")
                sys.exit(1)

            # Buscar se existe localmente
            pedido_odoo_com_dfe = pedidos_com_dfe[0]
            odoo_id_str = str(pedido_odoo_com_dfe['id'])

            pedido_local = PedidoCompras.query.filter_by(odoo_id=odoo_id_str).first()

            if not pedido_local:
                print(f"⚠️  Pedido {pedido_odoo_com_dfe['name']} do Odoo não existe localmente")
                print("   Criando registro temporário para teste...")

                pedido_local = PedidoCompras(
                    num_pedido=pedido_odoo_com_dfe['name'],
                    odoo_id=odoo_id_str,
                    cnpj_fornecedor='00000000000000',
                    raz_social='Teste',
                    cod_produto='TESTE',
                    qtd_produto_pedido=1
                )
                db.session.add(pedido_local)
                db.session.flush()

            dfe_info = pedido_odoo_com_dfe.get('dfe_id')
            partner_info = pedido_odoo_com_dfe.get('partner_id')

        else:
            partner_info = pedido_odoo[0].get('partner_id')

        print(f"✅ DFe encontrado: {dfe_info}")

    except Exception as e:
        print(f"❌ Erro ao buscar no Odoo: {e}")
        sys.exit(1)

    # 3. Buscar CNPJ do fornecedor
    print("\n3️⃣ Buscando CNPJ do fornecedor...")

    if partner_info and len(partner_info) > 0:
        partner_id = partner_info[0]

        partner = odoo.execute_kw(
            'res.partner',
            'read',
            [[partner_id]],
            {'fields': ['l10n_br_cnpj']}
        )

        cnpj_fornecedor = partner[0].get('l10n_br_cnpj') if partner else None
        print(f"✅ CNPJ: {cnpj_fornecedor}")
    else:
        cnpj_fornecedor = pedido_local.cnpj_fornecedor or '00000000000000'
        print(f"⚠️  Usando CNPJ do banco: {cnpj_fornecedor}")

    # 4. Processar DFe e salvar arquivos
    print("\n4️⃣ Processando DFe e salvando PDF/XML...")
    print("=" * 80)

    sucesso = service._processar_dfe_e_salvar_arquivos(
        pedido_local=pedido_local,
        dfe_info=dfe_info,
        cnpj_fornecedor=cnpj_fornecedor
    )

    if sucesso:
        db.session.commit()
        print("\n" + "=" * 80)
        print("✅ SUCESSO! PDF/XML processados")
        print("=" * 80)

        print(f"\n📋 Dados do Pedido Atualizado:")
        print(f"   Pedido: {pedido_local.num_pedido}")
        print(f"   DFe ID: {pedido_local.dfe_id}")
        print(f"   NF Número: {pedido_local.nf_numero} - Série: {pedido_local.nf_serie}")
        print(f"   Chave Acesso: {pedido_local.nf_chave_acesso}")
        print(f"   Data Emissão: {pedido_local.nf_data_emissao}")
        print(f"   Valor Total: R$ {pedido_local.nf_valor_total}")
        print(f"   📄 PDF: {pedido_local.nf_pdf_path}")
        print(f"   📄 XML: {pedido_local.nf_xml_path}")

        # 5. Testar acesso
        print("\n5️⃣ Testando acesso aos arquivos...")
        from app.utils.file_storage import get_file_storage

        file_storage = get_file_storage()

        if pedido_local.nf_pdf_path:
            pdf_url = file_storage.get_file_url(pedido_local.nf_pdf_path)
            print(f"   ✅ URL do PDF: {pdf_url[:100] if pdf_url else 'ERRO'}...")

        if pedido_local.nf_xml_path:
            xml_url = file_storage.get_file_url(pedido_local.nf_xml_path)
            print(f"   ✅ URL do XML: {xml_url[:100] if xml_url else 'ERRO'}...")

    else:
        print("\n❌ Falha ao processar DFe")

    print("\n" + "=" * 80)
