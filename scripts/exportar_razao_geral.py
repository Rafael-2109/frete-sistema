"""
Exportar Relatório Razão Geral (General Ledger) do Odoo
========================================================

Gera arquivo Excel com o relatório completo de Razão Geral,
com coluna de conta contábil, saldo inicial para contas
patrimoniais e saldo acumulado progressivo.

Execute:
    source .venv/bin/activate && python scripts/exportar_razao_geral.py

Saída:
    exports/razao_geral_YYYYMMDD_YYYYMMDD.xlsx
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.odoo.utils.connection import get_odoo_connection
from app.relatorios_fiscais.services.razao_geral_service import (
    buscar_movimentos_razao,
    gerar_excel_razao,
    EMPRESAS_RAZAO_GERAL
)

# ============================================================
# CONFIGURAÇÕES
# ============================================================
DATA_INICIO = '2024-08-01'
DATA_FIM = '2024-08-31'
COMPANY_IDS = [4, 1, 3]


def main():
    """Função principal - orquestra todo o processo de exportação"""
    app = create_app()
    with app.app_context():
        try:
            empresas_nomes = [e['nome'] for e in EMPRESAS_RAZAO_GERAL if e['id'] in COMPANY_IDS]

            print("=" * 60)
            print("EXPORTAR RAZÃO GERAL (GENERAL LEDGER)")
            print(f"Período: {DATA_INICIO} a {DATA_FIM}")
            print(f"Empresas: {', '.join(empresas_nomes)}")
            print("=" * 60)

            # 1. Conectar ao Odoo
            print("\n[1/4] Conectando ao Odoo...")
            connection = get_odoo_connection()
            if not connection.authenticate():
                print("   ❌ Falha na autenticação com Odoo")
                return
            print("   ✓ Conectado ao Odoo")

            # 2. Buscar movimentos do período (ID-cursor + transformacao inline)
            print(f"\n[2/4] Buscando movimentos contábeis...")
            dados_agrupados, contas_info, saldos_iniciais, total_registros = buscar_movimentos_razao(
                connection, DATA_INICIO, DATA_FIM, COMPANY_IDS
            )

            if not total_registros:
                print("   ⚠️  Nenhum registro encontrado para o período.")
                return

            print(f"   ✓ {total_registros} linhas contábeis encontradas")
            print(f"   ✓ {len(contas_info)} contas com movimentos")
            print(f"   ✓ {len(saldos_iniciais)} contas com saldo inicial")

            # 3. Gerar Excel (xlsxwriter constant_memory)
            print(f"\n[3/4] Gerando arquivo Excel...")
            excel_buffer = gerar_excel_razao(
                dados_agrupados, contas_info, saldos_iniciais,
                data_ini=DATA_INICIO, data_fim=DATA_FIM, company_ids=COMPANY_IDS
            )

            # 4. Salvar arquivo
            print(f"\n[4/4] Salvando arquivo...")
            exports_dir = os.path.join(os.path.dirname(__file__), '..', 'exports')
            os.makedirs(exports_dir, exist_ok=True)

            data_ini_fmt = DATA_INICIO.replace('-', '')
            data_fim_fmt = DATA_FIM.replace('-', '')
            filepath = os.path.join(exports_dir, f'razao_geral_{data_ini_fmt}_{data_fim_fmt}.xlsx')

            with open(filepath, 'wb') as f:
                f.write(excel_buffer.read())

            print(f"   ✓ Excel salvo: {filepath}")

            # --- Resumo Final ---
            print("\n" + "=" * 60)
            print("✅ EXPORTAÇÃO CONCLUÍDA!")
            print(f"   - Período: {DATA_INICIO} a {DATA_FIM}")
            print(f"   - Linhas contábeis: {total_registros}")
            print(f"   - Contas: {len(contas_info)}")
            print(f"\n📁 Arquivo: {os.path.abspath(filepath)}")
            print("=" * 60)

            return filepath

        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == '__main__':
    main()
