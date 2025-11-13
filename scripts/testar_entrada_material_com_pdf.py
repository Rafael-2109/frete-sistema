"""
Testar EntradaMaterialService com Download de PDFs/XMLs
========================================================

OBJETIVO: Testar o fluxo completo de importação incluindo:
          1. Busca de pickings
          2. Filtro /DEV/
          3. Batch queries otimizadas
          4. Download de PDFs/XMLs das NFs
          5. Armazenamento em S3/local via FileStorage

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db  # noqa: E402
from app.odoo.services.entrada_material_service import EntradaMaterialService  # noqa: E402
from app.manufatura.models import PedidoCompras  # noqa: E402
import logging

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("🧪 TESTE COMPLETO - ENTRADA MATERIAL COM PDFs/XMLs")
print("=" * 80)

app = create_app()

with app.app_context():
    print("\n1️⃣ Inicializando serviço...")
    service = EntradaMaterialService()

    print("\n2️⃣ Executando importação (últimos 7 dias, limite 5)...")
    print("=" * 80)

    resultado = service.importar_entradas(
        dias_retroativos=7,
        limite=5  # Poucos para teste
    )

    print("\n" + "=" * 80)
    print("📊 RESULTADO DA IMPORTAÇÃO")
    print("=" * 80)

    print(f"\n✅ Sucesso: {resultado['sucesso']}")
    print(f"📦 Entradas processadas: {resultado['entradas_processadas']}")
    print(f"✨ Entradas novas: {resultado['entradas_novas']}")
    print(f"🔄 Entradas atualizadas: {resultado['entradas_atualizadas']}")
    print(f"⏭️  Entradas ignoradas: {resultado['entradas_ignoradas']}")
    print(f"❌ Erros: {len(resultado['erros'])}")

    if resultado['erros']:
        print("\n⚠️  ERROS ENCONTRADOS:")
        for erro in resultado['erros']:
            print(f"   - {erro}")

    # 3. Verificar pedidos com PDFs salvos
    print("\n" + "=" * 80)
    print("3️⃣ Verificando pedidos com PDFs/XMLs salvos...")
    print("=" * 80)

    pedidos_com_nf = PedidoCompras.query.filter(
        PedidoCompras.nf_pdf_path.isnot(None)
    ).order_by(PedidoCompras.atualizado_em.desc()).limit(5).all()

    if pedidos_com_nf:
        print(f"\n✅ Encontrados {len(pedidos_com_nf)} pedido(s) com NF:\n")

        for pedido in pedidos_com_nf:
            print(f"   📋 Pedido: {pedido.num_pedido}")
            print(f"      Fornecedor: {pedido.raz_social}")
            print(f"      CNPJ: {pedido.cnpj_fornecedor}")
            print(f"      DFe ID: {pedido.dfe_id}")
            print(f"      NF Número: {pedido.nf_numero} - Série: {pedido.nf_serie}")
            print(f"      Chave Acesso: {pedido.nf_chave_acesso}")
            print(f"      Data Emissão: {pedido.nf_data_emissao}")
            print(f"      Valor Total: R$ {pedido.nf_valor_total}")
            print(f"      📄 PDF: {pedido.nf_pdf_path}")
            print(f"      📄 XML: {pedido.nf_xml_path}")
            print(f"      🕐 Atualizado: {pedido.atualizado_em}")
            print()

        # 4. Testar acesso ao PDF via FileStorage
        print("=" * 80)
        print("4️⃣ Testando acesso aos arquivos...")
        print("=" * 80)

        from app.utils.file_storage import get_file_storage

        file_storage = get_file_storage()

        pedido_teste = pedidos_com_nf[0]
        print(f"\n🔍 Testando pedido: {pedido_teste.num_pedido}\n")

        # Testar PDF
        if pedido_teste.nf_pdf_path:
            pdf_url = file_storage.get_file_url(pedido_teste.nf_pdf_path)
            if pdf_url:
                print(f"   ✅ URL do PDF gerada com sucesso!")
                print(f"      {pdf_url[:100]}...")
            else:
                print(f"   ⚠️  Erro ao gerar URL do PDF")

        # Testar XML
        if pedido_teste.nf_xml_path:
            xml_url = file_storage.get_file_url(pedido_teste.nf_xml_path)
            if xml_url:
                print(f"   ✅ URL do XML gerada com sucesso!")
                print(f"      {xml_url[:100]}...")
            else:
                print(f"   ⚠️  Erro ao gerar URL do XML")

    else:
        print("\n⚠️  Nenhum pedido com NF encontrado no banco")
        print("   Possíveis motivos:")
        print("   - Pickings não têm dfe_id vinculado no Odoo")
        print("   - Pedidos locais não foram encontrados")
        print("   - Erro ao processar DFe")

    print("\n" + "=" * 80)
    print("✅ TESTE CONCLUÍDO")
    print("=" * 80)

    print("\n📋 RESUMO FINAL:")
    print(f"   - Importação: {'✅ Sucesso' if resultado['sucesso'] else '❌ Falhou'}")
    print(f"   - Entradas processadas: {resultado['entradas_processadas']}")
    print(f"   - Pedidos com NF: {len(pedidos_com_nf) if pedidos_com_nf else 0}")
    print(f"   - PDFs salvos: {sum(1 for p in pedidos_com_nf if p.nf_pdf_path) if pedidos_com_nf else 0}")
    print(f"   - XMLs salvos: {sum(1 for p in pedidos_com_nf if p.nf_xml_path) if pedidos_com_nf else 0}")
    print("\n" + "=" * 80)
