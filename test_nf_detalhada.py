#!/usr/bin/env python3
"""
Teste para buscar NF detalhada com produtos
"""
import requests
import json

# Token fornecido
ACCESS_TOKEN = "LJCz5oS99KYgjnv1D59vcb4TJHtw4eTK"
API_BASE = "https://api.tagplus.com.br"

# ID da primeira NF encontrada no teste anterior
NF_ID = 2659  # ou id_nota: 2686

print(f"\n🔍 Buscando detalhes completos da NF ID: {NF_ID}\n")

# Headers
headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'X-Api-Version': '2.0',
    'Accept': 'application/json'
}

# Tenta diferentes formatos de endpoint
endpoints = [
    f"/nfes/{NF_ID}",
    f"/nfe/{NF_ID}",
    f"/notas-fiscais/{NF_ID}",
    f"/nfes/{NF_ID}/completa"
]

for endpoint in endpoints:
    print(f"\n{'='*60}")
    print(f"📋 Tentando: {endpoint}")

    try:
        url = f"{API_BASE}{endpoint}"
        response = requests.get(url, headers=headers, timeout=30)

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            print(f"✅ SUCESSO! Endpoint funciona: {endpoint}")

            # Salva resposta completa
            with open('nf_completa.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)

            print(f"\n💾 NF completa salva em: nf_completa.json")

            # Analisa estrutura
            print(f"\n📊 Estrutura da resposta:")
            if isinstance(data, dict):
                print(f"  Chaves principais: {list(data.keys())[:20]}")

                # Procura por itens/produtos
                for key in ['itens', 'items', 'produtos', 'detalhes', 'item']:
                    if key in data:
                        itens = data[key]
                        if isinstance(itens, list):
                            print(f"\n✅ PRODUTOS ENCONTRADOS em '{key}': {len(itens)} itens")

                            if len(itens) > 0:
                                print(f"\n📦 Primeiro produto:")
                                primeiro = itens[0]

                                # Mostra campos do produto
                                for campo in ['codigo', 'descricao', 'nome', 'quantidade', 'qtd', 'valor_unitario', 'valor_total', 'preco']:
                                    if campo in primeiro:
                                        print(f"    {campo}: {primeiro[campo]}")

                                print(f"\n📋 Todos os campos do produto:")
                                for k in sorted(primeiro.keys()):
                                    v = primeiro[k]
                                    if v not in [None, '', [], {}]:
                                        print(f"    {k}: {type(v).__name__}")

                            # Mostra resumo de todos os produtos
                            print(f"\n📄 LISTA DE TODOS OS PRODUTOS:")
                            for i, item in enumerate(itens, 1):
                                codigo = item.get('codigo') or item.get('codigo_produto') or item.get('sku', 'N/A')
                                nome = item.get('descricao') or item.get('nome') or item.get('nome_produto', 'N/A')
                                qtd = item.get('quantidade') or item.get('qtd') or item.get('qtde', 0)
                                valor_unit = item.get('valor_unitario') or item.get('preco') or item.get('valor', 0)
                                valor_total = item.get('valor_total') or item.get('total', 0)

                                print(f"\n  {i}. Produto:")
                                print(f"     Código: {codigo}")
                                print(f"     Nome: {nome}")
                                print(f"     Quantidade: {qtd}")
                                print(f"     Valor Unit: R$ {valor_unit}")
                                print(f"     Valor Total: R$ {valor_total}")

                        break

                # Mostra também informações gerais da NF
                print(f"\n📋 INFORMAÇÕES DA NF:")
                print(f"  Número: {data.get('numero')}")
                print(f"  Valor Total: R$ {data.get('valor_nota') or data.get('valor_total', 0)}")

                destinatario = data.get('destinatario', {})
                if destinatario:
                    print(f"  Cliente: {destinatario.get('razao_social')}")
                    print(f"  CNPJ: {destinatario.get('cnpj')}")

            break  # Para no primeiro que funcionar

        elif response.status_code == 404:
            print(f"❌ NF não encontrada neste endpoint")
        else:
            print(f"❌ Erro: {response.text[:200]}")

    except Exception as e:
        print(f"❌ Erro: {e}")

print("\n" + "="*60)
print("\n🎯 RESUMO")
print("Verifique o arquivo nf_completa.json para ver a estrutura completa")