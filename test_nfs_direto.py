#!/usr/bin/env python3
"""
Teste direto com o token fornecido
"""
import requests
from datetime import datetime, timedelta
import json

# Token fornecido
ACCESS_TOKEN = "LJCz5oS99KYgjnv1D59vcb4TJHtw4eTK"

# URLs da API
API_BASE = "https://api.tagplus.com.br"

# Datas para busca
data_fim = datetime.now().date()
data_inicio = data_fim - timedelta(days=30)

print(f"\n🔍 Testando busca de NFs com token fornecido")
print(f"Período: {data_inicio} até {data_fim}\n")

# Headers
headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'X-Api-Version': '2.0',
    'Accept': 'application/json'
}

# Lista de tentativas com diferentes parâmetros
tentativas = [
    {
        "nome": "Teste 1: Com since/until",
        "params": {
            'since': data_inicio.strftime('%Y-%m-%d'),
            'until': data_fim.strftime('%Y-%m-%d'),
            'per_page': 10
        }
    },
    {
        "nome": "Teste 2: Sem filtros",
        "params": {
            'per_page': 10
        }
    },
    {
        "nome": "Teste 3: Com page/per_page",
        "params": {
            'page': 1,
            'per_page': 10
        }
    },
    {
        "nome": "Teste 4: Com limite",
        "params": {
            'limite': 10
        }
    }
]

for tentativa in tentativas:
    print(f"\n{'='*60}")
    print(f"📋 {tentativa['nome']}")
    print(f"Parâmetros: {tentativa['params']}")

    try:
        url = f"{API_BASE}/nfes"
        print(f"URL: {url}")

        response = requests.get(
            url,
            headers=headers,
            params=tentativa['params'],
            timeout=30
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            # Analisa tipo de resposta
            if isinstance(data, list):
                print(f"✅ Resposta é uma LISTA com {len(data)} NFs")

                if len(data) > 0:
                    print("\n📄 Primeira NF encontrada:")
                    nfe = data[0]

                    # Campos importantes
                    print(f"  ID: {nfe.get('id')}")
                    print(f"  Número: {nfe.get('numero')}")
                    print(f"  Data Emissão: {nfe.get('data_emissao')}")
                    print(f"  Status: {nfe.get('status')}")
                    print(f"  Valor Total: {nfe.get('valor_total')}")
                    print(f"  Valor Nota: {nfe.get('valor_nota')}")

                    # Cliente
                    cliente = nfe.get('cliente', {})
                    destinatario = nfe.get('destinatario', {})

                    if cliente:
                        print(f"\n  Cliente (objeto):")
                        if isinstance(cliente, dict):
                            print(f"    Chaves: {list(cliente.keys())[:10]}")
                            print(f"    Nome: {cliente.get('nome')}")
                            print(f"    Razão: {cliente.get('razao_social')}")
                            print(f"    CNPJ: {cliente.get('cnpj')}")
                            print(f"    CPF: {cliente.get('cpf')}")

                    if destinatario:
                        print(f"\n  Destinatário (objeto):")
                        if isinstance(destinatario, dict):
                            print(f"    Chaves: {list(destinatario.keys())[:10]}")
                            print(f"    Nome: {destinatario.get('nome')}")
                            print(f"    Razão: {destinatario.get('razao_social')}")
                            print(f"    CNPJ: {destinatario.get('cnpj')}")

                    # Salva exemplo completo
                    with open('exemplo_nfe_tagplus.json', 'w', encoding='utf-8') as f:
                        json.dump(nfe, f, indent=2, default=str, ensure_ascii=False)
                    print(f"\n💾 NF completa salva em: exemplo_nfe_tagplus.json")

                    # Mostra todas as chaves da primeira NF
                    print(f"\n📊 Todas as chaves da NF:")
                    for key in sorted(nfe.keys()):
                        value = nfe.get(key)
                        if value not in [None, '', [], {}]:
                            print(f"    {key}: {type(value).__name__}")

                    print(f"\n✅ TESTE BEM-SUCEDIDO! Use esses parâmetros: {tentativa['params']}")
                    break  # Para no primeiro teste bem-sucedido

            elif isinstance(data, dict):
                print(f"✅ Resposta é um OBJETO")
                print(f"  Chaves: {list(data.keys())}")

                # Procura NFs em diferentes lugares
                for key in ['data', 'nfes', 'items', 'results']:
                    if key in data:
                        items = data[key]
                        if isinstance(items, list):
                            print(f"  NFs encontradas em '{key}': {len(items)} itens")
                            if len(items) > 0:
                                with open('exemplo_resposta_tagplus.json', 'w', encoding='utf-8') as f:
                                    json.dump(data, f, indent=2, default=str, ensure_ascii=False)
                                print(f"\n💾 Resposta completa salva em: exemplo_resposta_tagplus.json")
                                break

        elif response.status_code == 401:
            print("❌ Token expirado ou inválido")
            break
        else:
            print(f"❌ Erro: {response.status_code}")
            print(f"Resposta: {response.text[:500]}")

    except Exception as e:
        print(f"❌ Erro na requisição: {e}")

print("\n" + "="*60)
print("\n🎯 RESUMO DO TESTE")
print("Verifique os resultados acima para ver qual formato funciona!")