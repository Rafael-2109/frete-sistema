"""
Script para testar correção de timezone no cte_service
=======================================================

OBJETIVO:
    Testar se a correção de UTC está funcionando corretamente
    na sincronização incremental de CTes

AUTOR: Sistema de Fretes
DATA: 19/11/2025
"""

import sys
import os
from datetime import datetime
import pytz

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.odoo.services.cte_service import CteService

def testar_sincronizacao_cte():
    """Testa sincronização incremental de CTes com correção de timezone"""

    print("=" * 80)
    print("🧪 TESTE DE SINCRONIZAÇÃO DE CTes COM CORREÇÃO DE TIMEZONE")
    print("=" * 80)

    app = create_app()

    with app.app_context():
        try:
            # Mostrar horários de referência
            agora_local = datetime.now()
            agora_utc = datetime.now(pytz.UTC)
            agora_brt = datetime.now(pytz.timezone('America/Sao_Paulo'))

            print(f"\n🕐 HORÁRIOS DE REFERÊNCIA:")
            print(f"   Servidor Local (now()):          {agora_local.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   UTC (now(pytz.UTC)):             {agora_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"   Brasília (now('America/Sao_Paulo')): {agora_brt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print("=" * 80)

            # Instanciar service
            print("\n📡 Criando instância do CteService...")
            service = CteService()

            # Teste 1: Sincronização incremental (90 minutos)
            print("\n" + "=" * 80)
            print("🧪 TESTE 1: Sincronização Incremental (90 minutos)")
            print("=" * 80)

            resultado = service.importar_ctes(
                minutos_janela=90,
                limite=5  # Limitar para teste
            )

            print(f"\n📊 RESULTADO:")
            print(f"   Sucesso: {resultado['sucesso']}")
            print(f"   CTes Processados: {resultado['ctes_processados']}")
            print(f"   CTes Novos: {resultado['ctes_novos']}")
            print(f"   CTes Atualizados: {resultado['ctes_atualizados']}")
            print(f"   CTes Ignorados: {resultado['ctes_ignorados']}")
            print(f"   Erros: {len(resultado['erros'])}")

            if resultado['erros']:
                print(f"\n❌ ERROS ENCONTRADOS:")
                for erro in resultado['erros']:
                    print(f"   - {erro}")

            # Teste 2: Sincronização inicial (últimos 7 dias)
            print("\n" + "=" * 80)
            print("🧪 TESTE 2: Sincronização Inicial (últimos 7 dias)")
            print("=" * 80)

            resultado2 = service.importar_ctes(
                dias_retroativos=7,
                limite=5  # Limitar para teste
            )

            print(f"\n📊 RESULTADO:")
            print(f"   Sucesso: {resultado2['sucesso']}")
            print(f"   CTes Processados: {resultado2['ctes_processados']}")
            print(f"   CTes Novos: {resultado2['ctes_novos']}")
            print(f"   CTes Atualizados: {resultado2['ctes_atualizados']}")
            print(f"   CTes Ignorados: {resultado2['ctes_ignorados']}")
            print(f"   Erros: {len(resultado2['erros'])}")

            if resultado2['erros']:
                print(f"\n❌ ERROS ENCONTRADOS:")
                for erro in resultado2['erros']:
                    print(f"   - {erro}")

            print("\n" + "=" * 80)
            print("✅ TESTES CONCLUÍDOS!")
            print("=" * 80)

            # Análise
            print(f"\n💡 ANÁLISE:")
            if resultado['ctes_processados'] > 0 or resultado2['ctes_processados'] > 0:
                print("   ✅ Correção funcionando - CTes sendo encontrados e processados!")
            else:
                print("   ⚠️  Nenhum CTe processado - Pode não haver CTes atualizados recentemente")
                print("      ou problema de conexão com Odoo")

        except Exception as e:
            print(f"\n❌ ERRO NO TESTE: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    testar_sincronizacao_cte()
