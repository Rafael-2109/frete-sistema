#!/usr/bin/env python3
"""
Teste completo de importação para identificar o problema
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from datetime import datetime, timedelta
from app import create_app, db
from app.integracoes.tagplus.importador_v2 import ImportadorTagPlusV2

def testar_importacao():
    """Testa a importação e verifica o que está acontecendo"""

    app = create_app()
    with app.app_context():
        print("\n" + "="*60)
        print("🧪 TESTE DE IMPORTAÇÃO - DIAGNÓSTICO DO PROBLEMA")
        print("="*60)

        # Criar importador
        importador = ImportadorTagPlusV2()

        # Período
        data_fim = datetime.now().date()
        data_inicio = data_fim - timedelta(days=7)

        print(f"\n📅 Período: {data_inicio} até {data_fim}")

        # Testar conexão
        print("\n1️⃣ Testando conexão...")
        conexoes = importador.testar_conexoes()

        if not conexoes['notas']['sucesso']:
            print(f"❌ Erro: {conexoes['notas']['info']}")
            return

        print("✅ Conexão OK")

        # Listar NFs disponíveis
        print("\n2️⃣ Listando NFs disponíveis no período...")

        response = importador.oauth_notas.make_request(
            'GET',
            '/nfes',
            params={
                'since': data_inicio.strftime('%Y-%m-%d'),
                'until': data_fim.strftime('%Y-%m-%d'),
                'per_page': 10
            }
        )

        if response and response.status_code == 200:
            nfes = response.json()
            print(f"✅ {len(nfes)} NFs encontradas")

            print("\n📋 NFs disponíveis:")
            for nf in nfes[:5]:
                nf_id = nf.get('id')
                numero = nf.get('numero')

                # Buscar status detalhado
                detail_response = importador.oauth_notas.make_request('GET', f'/nfes/{nf_id}')
                status = '?'
                if detail_response and detail_response.status_code == 200:
                    nf_detail = detail_response.json()
                    status = nf_detail.get('status', '?')

                status_desc = {
                    'A': '✅ Ativa',
                    'S': '❌ Cancelada',
                    '2': '⛔ Denegada',
                    '4': '🚫 Inutilizada'
                }.get(status, f'❓ {status}')

                print(f"   - NF {numero} (ID: {nf_id}) - Status: {status_desc}")

            # Simular importação como a rota faz
            print("\n3️⃣ Simulando importação (igual à rota)...")
            print(f"   - Limite: {len(nfes)} NFs")
            print(f"   - Período: {data_inicio} até {data_fim}")

            # Importar
            resultado = importador.importar_nfs(
                data_inicio=data_inicio,
                data_fim=data_fim,
                limite=3,  # Limitar para teste
                verificar_cancelamentos=False  # Desabilitar para teste
            )

            print("\n" + "="*60)
            print("📊 RESULTADO DA IMPORTAÇÃO")
            print("="*60)

            if resultado:
                print(f"✅ NFs importadas: {resultado['nfs']['importadas']}")
                print(f"📦 Itens criados: {resultado['nfs']['itens']}")

                if resultado['nfs']['importadas'] == 0:
                    print("\n❌ PROBLEMA IDENTIFICADO: 0 NFs importadas!")
                    print("\nPossíveis causas:")
                    print("1. Todas as NFs já existem no banco")
                    print("2. Todas as NFs estão canceladas (status != 'A')")
                    print("3. Erro na busca ou processamento")

                    if resultado['nfs'].get('erros'):
                        print(f"\n⚠️ Erros encontrados:")
                        for erro in resultado['nfs']['erros']:
                            print(f"   - {erro}")

            # Verificar status das NFs
            print("\n4️⃣ Verificando status das NFs no banco...")
            from app.faturamento.models import FaturamentoProduto

            for nf in nfes[:3]:
                numero = nf.get('numero')
                existe = FaturamentoProduto.query.filter_by(numero_nf=str(numero)).first()
                if existe:
                    print(f"   - NF {numero}: ✅ JÁ EXISTE no banco (status: {existe.status_nf})")
                else:
                    print(f"   - NF {numero}: ❌ NÃO existe no banco")

        print("\n" + "="*60)
        print("🏁 DIAGNÓSTICO CONCLUÍDO")
        print("="*60)

if __name__ == "__main__":
    testar_importacao()