"""
Script para verificar timezone dos CTes no Odoo
================================================

OBJETIVO:
    Verificar qual timezone o Odoo está usando no campo write_date
    dos CTes para corrigir problema de sincronização incremental

AUTOR: Sistema de Fretes
DATA: 19/11/2025
"""

import sys
import os
from datetime import datetime, timedelta
import pytz

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.odoo.utils.connection import get_odoo_connection

def verificar_timezone_ctes():
    """Verifica timezone dos CTes no Odoo"""

    print("=" * 80)
    print("🔍 VERIFICAÇÃO DE TIMEZONE DOS CTes NO ODOO")
    print("=" * 80)

    try:
        # Conectar ao Odoo
        print("\n📡 Conectando ao Odoo...")
        odoo = get_odoo_connection()

        if not odoo.authenticate():
            print("❌ Erro: Não foi possível autenticar no Odoo")
            return

        print("✅ Conectado com sucesso!")

        # Buscar últimos 5 CTes ordenados por write_date DESC
        print("\n📋 Buscando últimos 5 CTes (ordenados por write_date)...")

        filtros = [
            "&",
            ("active", "=", True),
            ("is_cte", "=", True)
        ]

        campos = [
            'id',
            'name',
            'nfe_infnfe_ide_nnf',  # Número do CTe
            'nfe_infnfe_ide_dhemi',  # Data de emissão
            'write_date',  # Data de atualização (CRÍTICO)
            'create_date',  # Data de criação
            'l10n_br_status'
        ]

        ctes = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe',
            'search_read',
            [filtros],
            {
                'fields': campos,
                'limit': 5,
                'order': 'write_date DESC'
            }
        )

        if not ctes:
            print("⚠️  Nenhum CTe encontrado!")
            return

        print(f"✅ Encontrados {len(ctes)} CTes")
        print("=" * 80)

        # Obter horário atual em diferentes timezones
        agora_local = datetime.now()
        agora_utc = datetime.now(pytz.UTC)
        agora_brt = datetime.now(pytz.timezone('America/Sao_Paulo'))

        print(f"\n🕐 HORÁRIOS DE REFERÊNCIA:")
        print(f"   Servidor Local (now()): {agora_local.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   UTC:                    {agora_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   Brasília (BRT/BRST):    {agora_brt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print("=" * 80)

        # Analisar cada CTe
        for idx, cte in enumerate(ctes, 1):
            print(f"\n📄 CTe #{idx}: {cte.get('nfe_infnfe_ide_nnf', 'N/A')}")
            print(f"   ID Odoo: {cte.get('id')}")
            print(f"   Name: {cte.get('name', 'N/A')}")
            print(f"   Status: {cte.get('l10n_br_status', 'N/A')}")
            print(f"\n   📅 DATAS:")
            print(f"      Emissão (dhemi):   {cte.get('nfe_infnfe_ide_dhemi', 'N/A')}")
            print(f"      Criação (create):  {cte.get('create_date', 'N/A')}")
            print(f"      Atualização (write): {cte.get('write_date', 'N/A')}")

            # Analisar write_date em detalhes
            write_date_str = cte.get('write_date')
            if write_date_str:
                # Parse da data (Odoo retorna no formato: 2025-11-19 14:30:00)
                try:
                    # Tentar parsear como naive datetime
                    write_date_naive = datetime.strptime(write_date_str, '%Y-%m-%d %H:%M:%S')

                    # Calcular diferença para agora em diferentes timezones
                    diff_local = agora_local - write_date_naive

                    # Se assumirmos que write_date é UTC
                    write_date_utc = pytz.UTC.localize(write_date_naive)
                    diff_utc = agora_utc - write_date_utc

                    # Se assumirmos que write_date é BRT
                    tz_brt = pytz.timezone('America/Sao_Paulo')
                    write_date_brt = tz_brt.localize(write_date_naive)
                    diff_brt = agora_brt - write_date_brt

                    print(f"\n   ⏱️  ANÁLISE DE DIFERENÇA DE TEMPO:")
                    print(f"      Se write_date for LOCAL (naive):  {diff_local}")
                    print(f"      Se write_date for UTC:            {diff_utc}")
                    print(f"      Se write_date for BRT/BRST:       {diff_brt}")

                    # Converter para minutos
                    minutos_local = diff_local.total_seconds() / 60
                    minutos_utc = diff_utc.total_seconds() / 60
                    minutos_brt = diff_brt.total_seconds() / 60

                    print(f"\n   📊 MINUTOS ATRÁS:")
                    print(f"      Interpretação LOCAL: {minutos_local:.1f} minutos")
                    print(f"      Interpretação UTC:   {minutos_utc:.1f} minutos")
                    print(f"      Interpretação BRT:   {minutos_brt:.1f} minutos")

                except Exception as e:
                    print(f"   ⚠️  Erro ao parsear write_date: {e}")

        print("\n" + "=" * 80)
        print("🧪 TESTE DE FILTRO INCREMENTAL (últimos 90 minutos)")
        print("=" * 80)

        # Testar busca com janela de 90 minutos em diferentes timezones
        print("\n🔬 TESTANDO DIFERENTES INTERPRETAÇÕES DE TIMEZONE:\n")

        # 1. Filtro usando datetime.now() (LOCAL/UTC dependendo do servidor)
        data_local_90min = (datetime.now() - timedelta(minutes=90)).strftime('%Y-%m-%d %H:%M:%S')
        ctes_local = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe',
            'search',
            [[
                "&",
                "&",
                ("active", "=", True),
                ("is_cte", "=", True),
                ("write_date", ">=", data_local_90min)
            ]]
        )
        print(f"1️⃣  Filtro LOCAL (now() - 90min): {data_local_90min}")
        print(f"   Resultado: {len(ctes_local) if ctes_local else 0} CTes encontrados")

        # 2. Filtro usando UTC explicitamente
        data_utc_90min = (agora_utc - timedelta(minutes=90)).strftime('%Y-%m-%d %H:%M:%S')
        ctes_utc = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe',
            'search',
            [[
                "&",
                "&",
                ("active", "=", True),
                ("is_cte", "=", True),
                ("write_date", ">=", data_utc_90min)
            ]]
        )
        print(f"\n2️⃣  Filtro UTC (utcnow() - 90min): {data_utc_90min}")
        print(f"   Resultado: {len(ctes_utc) if ctes_utc else 0} CTes encontrados")

        # 3. Filtro usando BRT explicitamente
        data_brt_90min = (agora_brt - timedelta(minutes=90)).strftime('%Y-%m-%d %H:%M:%S')
        ctes_brt = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe',
            'search',
            [[
                "&",
                "&",
                ("active", "=", True),
                ("is_cte", "=", True),
                ("write_date", ">=", data_brt_90min)
            ]]
        )
        print(f"\n3️⃣  Filtro BRT (now('America/Sao_Paulo') - 90min): {data_brt_90min}")
        print(f"   Resultado: {len(ctes_brt) if ctes_brt else 0} CTes encontrados")

        print("\n" + "=" * 80)
        print("📊 CONCLUSÃO:")
        print("=" * 80)

        # Análise dos resultados
        if len(ctes_local if ctes_local else []) > 0:
            print("✅ Filtro LOCAL funcionou - Odoo provavelmente usa timezone LOCAL/naive")
        if len(ctes_utc if ctes_utc else []) > 0:
            print("✅ Filtro UTC funcionou - Odoo provavelmente usa UTC")
        if len(ctes_brt if ctes_brt else []) > 0:
            print("✅ Filtro BRT funcionou - Odoo provavelmente usa horário de Brasília")

        if len(ctes_local if ctes_local else []) == 0 and len(ctes_utc if ctes_utc else []) == 0 and len(ctes_brt if ctes_brt else []) == 0:
            print("⚠️  NENHUM filtro funcionou - Pode não haver CTes atualizados nos últimos 90 minutos")
            print("    OU o timezone do Odoo é diferente de LOCAL/UTC/BRT")

        print("\n💡 RECOMENDAÇÃO:")
        max_results = max(
            len(ctes_local if ctes_local else []),
            len(ctes_utc if ctes_utc else []),
            len(ctes_brt if ctes_brt else [])
        )

        if len(ctes_local if ctes_local else []) == max_results:
            print("   Use datetime.now() para cálculos de janela incremental")
        elif len(ctes_utc if ctes_utc else []) == max_results:
            print("   Use datetime.now(pytz.UTC) para cálculos de janela incremental")
        elif len(ctes_brt if ctes_brt else []) == max_results:
            print("   Use datetime.now(pytz.timezone('America/Sao_Paulo')) para cálculos")

        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    verificar_timezone_ctes()
