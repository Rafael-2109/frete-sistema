#!/usr/bin/env python3
"""
Lista NFs do TagPlus com datas corretas (busca detalhes de cada uma)
"""

import requests
from datetime import datetime, timedelta

token = "7pwodl5ybldjAqcgBTfNrrjV1MSGI3uI"
headers = {
    'Authorization': f'Bearer {token}',
    'X-Api-Version': '2.0',
    'Accept': 'application/json'
}

print("\n" + "="*60)
print("📋 LISTANDO NFS COM DATAS COMPLETAS")
print("="*60)

# Período
data_fim = datetime.now().date()
data_inicio = data_fim - timedelta(days=7)

# Buscar lista de NFs
print(f"\nBuscando NFs de {data_inicio} até {data_fim}...")
response = requests.get(
    'https://api.tagplus.com.br/nfes',
    headers=headers,
    params={
        'since': data_inicio.strftime('%Y-%m-%d'),
        'until': data_fim.strftime('%Y-%m-%d'),
        'per_page': 100
    },
    timeout=30
)

if response.status_code == 200:
    nfes = response.json()
    print(f"✅ Encontradas {len(nfes)} NFs\n")

    print("-"*60)
    print(f"{'NF':<8} {'Data Emissão':<20} {'Cliente':<30} {'Valor':<15}")
    print("-"*60)

    for nfe in nfes[:5]:  # Limitar a 5 para não demorar muito
        nf_id = nfe.get('id')
        numero = nfe.get('numero')

        # Buscar detalhes para pegar a data
        detail_response = requests.get(
            f'https://api.tagplus.com.br/nfes/{nf_id}',
            headers=headers,
            timeout=30
        )

        data_emissao = 'N/A'
        if detail_response.status_code == 200:
            nf_detalhada = detail_response.json()
            data_emissao_raw = nf_detalhada.get('data_emissao', '')

            # Formatar data
            if data_emissao_raw:
                try:
                    # Converter "2025-09-24 16:02:42" para "24/09/2025"
                    dt = datetime.strptime(data_emissao_raw.split(' ')[0], '%Y-%m-%d')
                    data_emissao = dt.strftime('%d/%m/%Y')
                except Exception as e:
                    print(f"Erro ao formatar data: {e}")
                    data_emissao = data_emissao_raw

        # Dados do cliente
        destinatario = nfe.get('destinatario', {})
        cliente = destinatario.get('razao_social', 'N/A')[:28]
        valor = f"R$ {nfe.get('valor_nota', 0):,.2f}"

        print(f"{numero:<8} {data_emissao:<20} {cliente:<30} {valor:<15}")

    print("-"*60)
    print("\n✅ Dados completos obtidos!")
    print("\n💡 SOLUÇÃO: Para mostrar datas na interface, precisamos:")
    print("   1. Buscar detalhes de cada NF (mais lento)")
    print("   2. OU cachear as datas após primeira busca")
    print("   3. OU mostrar 'Carregando...' e buscar via AJAX")

else:
    print(f"❌ Erro: {response.status_code}")