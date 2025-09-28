#!/usr/bin/env python3
"""
Teste de importação com IDs específicos - Validação da correção
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from datetime import datetime, timedelta
from app import create_app, db
from app.integracoes.tagplus.importador_v2 import ImportadorTagPlusV2

def testar_importacao_ids_especificos():
    """Testa a importação com IDs específicos de NFs"""

    app = create_app()
    with app.app_context():
        print("\n" + "="*60)
        print("🧪 TESTE DE IMPORTAÇÃO COM IDs ESPECÍFICOS")
        print("="*60)

        # Criar importador
        importador = ImportadorTagPlusV2()

        # Período
        data_fim = datetime.now().date()
        data_inicio = data_fim - timedelta(days=7)

        print(f"\n📅 Período: {data_inicio} até {data_fim}")

        # 1. Primeiro listar NFs disponíveis
        print("\n1️⃣ Buscando NFs disponíveis...")

        response = importador.oauth_notas.make_request(
            'GET',
            '/nfes',
            params={
                'since': data_inicio.strftime('%Y-%m-%d'),
                'until': data_fim.strftime('%Y-%m-%d'),
                'per_page': 10
            }
        )

        if not response or response.status_code != 200:
            print(f"❌ Erro ao buscar NFs: {response.status_code if response else 'Sem resposta'}")
            return

        nfes = response.json()
        print(f"✅ {len(nfes)} NFs encontradas")

        # Coletar IDs das primeiras 3 NFs ativas
        nf_ids_para_importar = []

        print("\n📋 Selecionando NFs ativas para teste:")
        for nf in nfes:
            nf_id = nf.get('id')
            numero = nf.get('numero')

            # Buscar detalhes para verificar status
            detail_response = importador.oauth_notas.make_request('GET', f'/nfes/{nf_id}')
            if detail_response and detail_response.status_code == 200:
                nf_detail = detail_response.json()
                status = nf_detail.get('status', '?')

                if status == 'A':  # Apenas NFs ativas
                    nf_ids_para_importar.append(nf_id)
                    print(f"   ✅ NF {numero} (ID: {nf_id}) - Status: Ativa - SELECIONADA")

                    if len(nf_ids_para_importar) >= 3:
                        break
                else:
                    status_desc = {
                        'S': '❌ Cancelada',
                        '2': '⛔ Denegada',
                        '4': '🚫 Inutilizada'
                    }.get(status, f'❓ {status}')
                    print(f"   - NF {numero} (ID: {nf_id}) - Status: {status_desc} - IGNORADA")

        if not nf_ids_para_importar:
            print("\n❌ Nenhuma NF ativa encontrada para importar!")
            return

        print(f"\n2️⃣ Importando {len(nf_ids_para_importar)} NFs específicas...")
        print(f"   IDs: {nf_ids_para_importar}")

        # Importar com IDs específicos
        resultado = importador.importar_nfs(
            data_inicio=data_inicio,
            data_fim=data_fim,
            limite=None,  # Sem limite quando usando IDs específicos
            verificar_cancelamentos=False,  # Não verificar outros cancelamentos
            nf_ids=nf_ids_para_importar  # PASSAR OS IDs ESPECÍFICOS
        )

        print("\n" + "="*60)
        print("📊 RESULTADO DA IMPORTAÇÃO COM IDs ESPECÍFICOS")
        print("="*60)

        if resultado:
            print(f"✅ NFs importadas: {resultado['nfs']['importadas']}")
            print(f"📦 Itens criados: {resultado['nfs']['itens']}")

            # Comparar com expectativa
            esperado = len(nf_ids_para_importar)
            importado = resultado['nfs']['importadas']

            if importado == esperado:
                print(f"\n✅ SUCESSO! Importou exatamente {importado} NF(s) como esperado!")
            elif importado < esperado:
                print(f"\n⚠️ PARCIAL: Importou {importado} de {esperado} NFs")
                print("Possíveis causas:")
                print("- Algumas NFs já existem no banco")
                print("- Algumas NFs mudaram de status")
            else:
                print(f"\n❓ INESPERADO: Importou {importado} NFs mas esperava {esperado}")

            if resultado['nfs'].get('erros'):
                print(f"\n⚠️ Erros encontrados:")
                for erro in resultado['nfs']['erros']:
                    print(f"   - {erro}")

            # Verificar processamento
            if resultado.get('processamento'):
                proc = resultado['processamento']
                print(f"\n📈 Processamento:")
                print(f"   - NFs processadas: {proc.get('nfs_processadas', 0)}")
                print(f"   - Movimentações criadas: {proc.get('movimentacoes_criadas', 0)}")
                print(f"   - Com embarque: {proc.get('com_embarque', 0)}")
                print(f"   - Sem separação: {proc.get('sem_separacao', 0)}")
        else:
            print("❌ Resultado vazio!")

        # 3. Verificar no banco se foram importadas
        print("\n3️⃣ Verificando no banco de dados...")
        from app.faturamento.models import FaturamentoProduto

        for nf_id in nf_ids_para_importar[:3]:
            # Buscar número da NF
            detail_response = importador.oauth_notas.make_request('GET', f'/nfes/{nf_id}')
            if detail_response and detail_response.status_code == 200:
                nf_detail = detail_response.json()
                numero = nf_detail.get('numero')

                existe = FaturamentoProduto.query.filter_by(numero_nf=str(numero)).first()
                if existe:
                    print(f"   ✅ NF {numero}: EXISTE no banco (status: {existe.status_nf})")
                else:
                    print(f"   ❌ NF {numero}: NÃO existe no banco")

        print("\n" + "="*60)
        print("🏁 TESTE COM IDs ESPECÍFICOS CONCLUÍDO")
        print("="*60)

if __name__ == "__main__":
    testar_importacao_ids_especificos()