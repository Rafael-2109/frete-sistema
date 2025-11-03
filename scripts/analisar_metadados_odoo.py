"""
Script para analisar METADADOS do Odoo (ir.model)
Extrai campos e relacionamentos de modelos específicos

Uso:
    python scripts/analisar_metadados_odoo.py "caminho/arquivo.xlsx"
"""

import sys
import pandas as pd

def analisar_metadados(caminho_arquivo):
    """Analisa metadados do Odoo para descobrir estrutura"""

    print("=" * 80)
    print("🔍 ANÁLISE DE METADADOS ODOO")
    print("=" * 80)

    # Carregar arquivo
    print(f"\n📁 Carregando: {caminho_arquivo}")
    df = pd.read_excel(caminho_arquivo)
    print(f"✅ {len(df):,} linhas carregadas")

    # =====================================================
    # FILTRAR MODELOS RELEVANTES
    # =====================================================
    print("\n" + "=" * 80)
    print("🎯 FILTRANDO MODELOS RELEVANTES")
    print("=" * 80)

    modelos_interesse = [
        'purchase.request',
        'purchase.request.line',
        'purchase.order',
        'purchase.order.line',
    ]

    # Filtrar por coluna "Modelo" ou "Campos/Nome do modelo"
    if 'Modelo' in df.columns:
        df_filtrado = df[df['Modelo'].isin(modelos_interesse)].copy()
    elif 'Campos/Nome do modelo' in df.columns:
        df_filtrado = df[df['Campos/Nome do modelo'].isin(modelos_interesse)].copy()
    else:
        print("❌ Não encontrei coluna com nome do modelo")
        return

    print(f"\n✅ Encontradas {len(df_filtrado):,} linhas dos modelos relevantes\n")

    # =====================================================
    # ANALISAR CADA MODELO
    # =====================================================
    for modelo in modelos_interesse:
        print("\n" + "=" * 80)
        print(f"📋 MODELO: {modelo}")
        print("=" * 80)

        if 'Modelo' in df.columns:
            df_modelo = df_filtrado[df_filtrado['Modelo'] == modelo].copy()
        else:
            df_modelo = df_filtrado[df_filtrado['Campos/Nome do modelo'] == modelo].copy()

        if len(df_modelo) == 0:
            print(f"   ⚠️  Nenhum campo encontrado para {modelo}")
            continue

        print(f"\n   Total de campos: {len(df_modelo)}")

        # Pegar coluna de nome do campo
        if 'Campos/Nome do campo' in df_modelo.columns:
            campos = df_modelo['Campos/Nome do campo'].dropna().unique()
        elif 'Campos' in df_modelo.columns:
            campos = df_modelo['Campos'].dropna().unique()
        else:
            print("   ⚠️  Não encontrei coluna com nomes de campos")
            continue

        print(f"\n   📝 CAMPOS PRINCIPAIS:\n")

        # Campos relacionados a IDs e relacionamentos
        campos_id = []
        campos_relacionamento = []
        campos_quantidade = []
        campos_data = []
        campos_status = []
        campos_outros = []

        for campo in sorted(campos):
            campo_lower = str(campo).lower()

            # IDs e relacionamentos
            if '_id' in campo_lower or '_ids' in campo_lower:
                if '_ids' in campo_lower:
                    campos_relacionamento.append(campo)
                else:
                    campos_id.append(campo)

            # Quantidades
            elif any(palavra in campo_lower for palavra in ['qty', 'quantity', 'amount']):
                campos_quantidade.append(campo)

            # Datas
            elif 'date' in campo_lower or 'deadline' in campo_lower:
                campos_data.append(campo)

            # Status
            elif 'state' in campo_lower or 'status' in campo_lower:
                campos_status.append(campo)

            # Outros
            else:
                campos_outros.append(campo)

        # Exibir por categoria
        if campos_id:
            print("   🔗 IDs e Referências:")
            for campo in campos_id[:20]:  # Primeiros 20
                print(f"      - {campo}")

        if campos_relacionamento:
            print("\n   🔗 Relacionamentos (One2Many/Many2Many):")
            for campo in campos_relacionamento[:20]:
                print(f"      - {campo}")

        if campos_quantidade:
            print("\n   📊 Quantidades:")
            for campo in campos_quantidade:
                print(f"      - {campo}")

        if campos_data:
            print("\n   📅 Datas:")
            for campo in campos_data[:10]:
                print(f"      - {campo}")

        if campos_status:
            print("\n   📋 Status:")
            for campo in campos_status:
                print(f"      - {campo}")

        # Campos críticos para relacionamento
        print("\n   🎯 CAMPOS CRÍTICOS PARA RELACIONAMENTO:")

        if modelo == 'purchase.request.line':
            campos_criticos = [c for c in campos if any(palavra in str(c).lower()
                for palavra in ['purchase', 'order', 'request_id', 'line'])]

            if campos_criticos:
                for campo in campos_criticos:
                    print(f"      ✅ {campo}")
            else:
                print("      ⚠️  Nenhum campo de relacionamento óbvio encontrado")

        elif modelo == 'purchase.order.line':
            campos_criticos = [c for c in campos if any(palavra in str(c).lower()
                for palavra in ['request', 'requisition', 'order_id'])]

            if campos_criticos:
                for campo in campos_criticos:
                    print(f"      ✅ {campo}")
            else:
                print("      ⚠️  Nenhum campo de relacionamento com requisição encontrado")

        # Amostra de dados (primeiras linhas)
        if 'Campos/Rótulo do campo' in df_modelo.columns:
            print("\n   📄 Amostra de Campos (com rótulos):")
            amostra = df_modelo[['Campos/Nome do campo', 'Campos/Rótulo do campo']].head(10)
            for idx, row in amostra.iterrows():
                print(f"      {row['Campos/Nome do campo']:30s} → {row['Campos/Rótulo do campo']}")

    # =====================================================
    # DESCOBRIR RELACIONAMENTOS
    # =====================================================
    print("\n\n" + "=" * 80)
    print("🔗 ANÁLISE DE RELACIONAMENTOS")
    print("=" * 80)

    # Buscar campos que conectam os modelos
    print("\n🔍 Buscando campos de relacionamento...\n")

    # purchase.request.line → purchase.order.line
    if 'Campos/Nome do campo' in df.columns and 'Campos/Nome do modelo' in df.columns:
        req_line = df[df['Campos/Nome do modelo'] == 'purchase.request.line']
        campos_req_line = req_line['Campos/Nome do campo'].tolist()

        # Procurar campos que mencionam "purchase" ou "order"
        campos_link_req = [c for c in campos_req_line if isinstance(c, str) and
            any(palavra in c.lower() for palavra in ['purchase_', 'order_'])]

        if campos_link_req:
            print("   📋 purchase.request.line → campos relacionados a pedidos:")
            for campo in set(campos_link_req):
                print(f"      ✅ {campo}")

        # purchase.order.line → purchase.request.line
        order_line = df[df['Campos/Nome do modelo'] == 'purchase.order.line']
        campos_order_line = order_line['Campos/Nome do campo'].tolist()

        campos_link_order = [c for c in campos_order_line if isinstance(c, str) and
            any(palavra in c.lower() for palavra in ['request_', 'requisition_'])]

        if campos_link_order:
            print("\n   🛒 purchase.order.line → campos relacionados a requisições:")
            for campo in set(campos_link_order):
                print(f"      ✅ {campo}")
        else:
            print("\n   ⚠️  purchase.order.line → NENHUM campo de requisição encontrado")
            print("      Isso confirma que o relacionamento é UNIDIRECIONAL!")

    print("\n" + "=" * 80)
    print("✅ ANÁLISE CONCLUÍDA")
    print("=" * 80)
    print()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("❌ Uso: python scripts/analisar_metadados_odoo.py 'caminho/arquivo.xlsx'")
        sys.exit(1)

    caminho = sys.argv[1]
    analisar_metadados(caminho)
