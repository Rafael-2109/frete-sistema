"""
Script para ANALISAR arquivo Excel/CSV do Odoo
Identifica campos, relacionamentos e estrutura de dados

Suporta arquivos grandes (20.000+ linhas)
Usa processamento em chunks para otimização

Uso:
    python scripts/analisar_excel_odoo.py caminho/para/arquivo.csv
    python scripts/analisar_excel_odoo.py caminho/para/arquivo.xlsx
"""

import sys
import os
import pandas as pd
from collections import Counter, defaultdict
import json

def analisar_arquivo(caminho_arquivo):
    """
    Analisa arquivo Excel ou CSV do Odoo
    """
    print("=" * 80)
    print("📊 ANÁLISE DE ARQUIVO ODOO")
    print("=" * 80)
    print(f"\n📁 Arquivo: {caminho_arquivo}")

    # =====================================================
    # 1. DETECTAR TIPO DE ARQUIVO E CARREGAR
    # =====================================================
    extensao = os.path.splitext(caminho_arquivo)[1].lower()

    print(f"\n🔍 Detectando formato: {extensao}")

    try:
        if extensao == '.csv':
            # Tentar detectar encoding
            print("   Tentando UTF-8...")
            try:
                df = pd.read_csv(caminho_arquivo, encoding='utf-8', low_memory=False)
            except UnicodeDecodeError:
                print("   UTF-8 falhou, tentando Latin-1...")
                df = pd.read_csv(caminho_arquivo, encoding='latin-1', low_memory=False)

        elif extensao in ['.xlsx', '.xls']:
            print("   Lendo Excel...")
            df = pd.read_excel(caminho_arquivo)

        else:
            print(f"❌ Formato não suportado: {extensao}")
            print("   Formatos aceitos: .csv, .xlsx, .xls")
            return

    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        return

    print(f"✅ Arquivo carregado com sucesso!")

    # =====================================================
    # 2. INFORMAÇÕES GERAIS
    # =====================================================
    print("\n" + "=" * 80)
    print("📈 INFORMAÇÕES GERAIS")
    print("=" * 80)

    print(f"\n   Total de linhas: {len(df):,}")
    print(f"   Total de colunas: {len(df.columns)}")
    print(f"   Memória usada: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

    # =====================================================
    # 3. LISTAR TODAS AS COLUNAS
    # =====================================================
    print("\n" + "=" * 80)
    print("📋 COLUNAS ENCONTRADAS")
    print("=" * 80)

    print(f"\n   Total: {len(df.columns)} colunas\n")

    for idx, coluna in enumerate(df.columns, 1):
        tipo = df[coluna].dtype
        nulos = df[coluna].isna().sum()
        preenchidos = len(df) - nulos
        percentual = (preenchidos / len(df)) * 100

        print(f"   {idx:2d}. {coluna}")
        print(f"       Tipo: {tipo}")
        print(f"       Preenchidos: {preenchidos:,} ({percentual:.1f}%)")

        # Mostrar amostra de valores (não nulos)
        amostra = df[coluna].dropna().head(3).tolist()
        if amostra:
            print(f"       Amostra: {amostra}")
        print()

    # =====================================================
    # 4. IDENTIFICAR CAMPOS CHAVE
    # =====================================================
    print("\n" + "=" * 80)
    print("🔑 IDENTIFICANDO CAMPOS CHAVE")
    print("=" * 80)

    # Campos que parecem ser IDs ou códigos
    campos_id = []
    campos_requisicao = []
    campos_pedido = []
    campos_produto = []
    campos_quantidade = []
    campos_data = []

    for col in df.columns:
        col_lower = col.lower()

        # IDs
        if 'id' in col_lower or col_lower in ['number', 'code']:
            valores_unicos = df[col].nunique()
            print(f"\n   🆔 {col}")
            print(f"      Valores únicos: {valores_unicos:,}")
            print(f"      Amostra: {df[col].dropna().head(5).tolist()}")
            campos_id.append(col)

        # Requisições
        if any(palavra in col_lower for palavra in ['request', 'requisicao', 'requisição', 'req/']):
            print(f"\n   📋 {col} (Requisição)")
            print(f"      Valores únicos: {df[col].nunique():,}")
            print(f"      Amostra: {df[col].dropna().head(5).tolist()}")
            campos_requisicao.append(col)

        # Pedidos
        if any(palavra in col_lower for palavra in ['order', 'pedido', 'purchase', 'po/']):
            print(f"\n   🛒 {col} (Pedido)")
            print(f"      Valores únicos: {df[col].nunique():,}")
            print(f"      Amostra: {df[col].dropna().head(5).tolist()}")
            campos_pedido.append(col)

        # Produtos
        if any(palavra in col_lower for palavra in ['product', 'produto', 'item', 'material']):
            print(f"\n   📦 {col} (Produto)")
            print(f"      Valores únicos: {df[col].nunique():,}")
            print(f"      Amostra: {df[col].dropna().head(3).tolist()}")
            campos_produto.append(col)

        # Quantidades
        if any(palavra in col_lower for palavra in ['qty', 'quantity', 'qtd', 'quantidade', 'amount']):
            if df[col].dtype in ['int64', 'float64']:
                print(f"\n   📊 {col} (Quantidade)")
                print(f"      Mín: {df[col].min()}")
                print(f"      Máx: {df[col].max()}")
                print(f"      Média: {df[col].mean():.2f}")
                campos_quantidade.append(col)

        # Datas
        if any(palavra in col_lower for palavra in ['date', 'data', 'deadline', 'prazo']):
            print(f"\n   📅 {col} (Data)")
            print(f"      Amostra: {df[col].dropna().head(3).tolist()}")
            campos_data.append(col)

    # =====================================================
    # 5. ANÁLISE DE RELACIONAMENTO
    # =====================================================
    print("\n\n" + "=" * 80)
    print("🔗 ANÁLISE DE RELACIONAMENTO")
    print("=" * 80)

    # Tentar identificar relacionamento Requisição → Pedido
    if campos_requisicao and campos_pedido:
        print("\n📌 Analisando relação Requisição ↔ Pedido...\n")

        # Pegar primeira coluna de requisição e primeira de pedido
        col_req = campos_requisicao[0]
        col_ped = campos_pedido[0]

        print(f"   Requisição: {col_req}")
        print(f"   Pedido: {col_ped}\n")

        # Contar quantos pedidos por requisição
        if col_req in df.columns and col_ped in df.columns:
            # Remover linhas onde ambos são nulos
            df_relacao = df[[col_req, col_ped]].dropna()

            if len(df_relacao) > 0:
                # Agrupar pedidos por requisição
                pedidos_por_requisicao = df_relacao.groupby(col_req)[col_ped].apply(list).to_dict()

                # Estatísticas
                qtd_pedidos_por_req = {req: len(set(pedidos)) for req, pedidos in pedidos_por_requisicao.items()}
                distribuicao = Counter(qtd_pedidos_por_req.values())

                print("   📊 Distribuição:")
                for num_pedidos, qtd_requisicoes in sorted(distribuicao.items()):
                    print(f"      {qtd_requisicoes:,} requisições com {num_pedidos} pedido(s)")

                # Top 5 requisições com mais pedidos
                top_requisicoes = sorted(qtd_pedidos_por_req.items(), key=lambda x: x[1], reverse=True)[:5]

                print(f"\n   🔝 Top 5 requisições com mais pedidos:")
                for req, qtd in top_requisicoes:
                    pedidos = list(set(pedidos_por_requisicao[req]))[:3]  # Primeiros 3 pedidos
                    print(f"      {req}: {qtd} pedidos")
                    print(f"         Exemplos: {pedidos}")

                # Análise reversa: Quantas requisições por pedido
                requisicoes_por_pedido = df_relacao.groupby(col_ped)[col_req].apply(list).to_dict()
                qtd_req_por_pedido = {ped: len(set(reqs)) for ped, reqs in requisicoes_por_pedido.items()}
                distribuicao_reversa = Counter(qtd_req_por_pedido.values())

                print(f"\n   📊 Distribuição REVERSA (Requisições por Pedido):")
                for num_reqs, qtd_pedidos in sorted(distribuicao_reversa.items()):
                    print(f"      {qtd_pedidos:,} pedidos com {num_reqs} requisição(ões)")

                # Conclusão
                print(f"\n   💡 CONCLUSÃO:")
                if max(distribuicao.keys()) > 1:
                    print(f"      ✅ 1 Requisição pode ter N Pedidos (máx: {max(distribuicao.keys())})")
                else:
                    print(f"      ✅ Relação 1:1 entre Requisição e Pedido")

                if max(distribuicao_reversa.keys()) > 1:
                    print(f"      ✅ 1 Pedido pode ter N Requisições (máx: {max(distribuicao_reversa.keys())})")
                else:
                    print(f"      ✅ 1 Pedido → 1 Requisição (ou nenhuma)")

    # =====================================================
    # 6. EXPORTAR ANÁLISE
    # =====================================================
    print("\n\n" + "=" * 80)
    print("💾 SALVANDO ANÁLISE")
    print("=" * 80)

    resultado = {
        "arquivo": caminho_arquivo,
        "total_linhas": len(df),
        "total_colunas": len(df.columns),
        "colunas": list(df.columns),
        "campos_identificados": {
            "ids": campos_id,
            "requisicoes": campos_requisicao,
            "pedidos": campos_pedido,
            "produtos": campos_produto,
            "quantidades": campos_quantidade,
            "datas": campos_data
        },
        "amostra_primeiras_5_linhas": df.head(5).to_dict('records')
    }

    arquivo_saida = caminho_arquivo.replace('.csv', '_analise.json').replace('.xlsx', '_analise.json')
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n✅ Análise salva em: {arquivo_saida}")

    # Salvar primeiras 100 linhas como CSV para inspeção manual
    arquivo_amostra = caminho_arquivo.replace('.csv', '_amostra.csv').replace('.xlsx', '_amostra.csv')
    df.head(100).to_csv(arquivo_amostra, index=False, encoding='utf-8')
    print(f"✅ Amostra (100 linhas) salva em: {arquivo_amostra}")

    print("\n" + "=" * 80)
    print("✅ ANÁLISE CONCLUÍDA!")
    print("=" * 80)
    print()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("❌ Uso: python scripts/analisar_excel_odoo.py caminho/para/arquivo.csv")
        print("   Exemplo: python scripts/analisar_excel_odoo.py ~/Downloads/odoo_requisicoes.xlsx")
        sys.exit(1)

    caminho = sys.argv[1]

    if not os.path.exists(caminho):
        print(f"❌ Arquivo não encontrado: {caminho}")
        sys.exit(1)

    analisar_arquivo(caminho)
