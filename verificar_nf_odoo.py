#!/usr/bin/env python3
"""
Script para verificar campos de uma NF específica no Odoo
Especialmente os campos de auditoria (create_date, write_date)
"""

import sys
from datetime import datetime
import pytz

def verificar_nf(numero_nf='132656'):
    """Verifica campos de uma NF específica no Odoo"""

    print("="*60)
    print(f"VERIFICAÇÃO DA NF {numero_nf} NO ODOO")
    print("="*60)

    try:
        from app import create_app
        from app.odoo.utils.connection import get_odoo_connection

        app = create_app()
        with app.app_context():
            # Conectar ao Odoo
            odoo = get_odoo_connection()

            print(f"\n1. Buscando account.move com NF {numero_nf}...")

            # Buscar a fatura (account.move)
            faturas = odoo.search_read(
                'account.move',
                [('l10n_br_numero_nota_fiscal', '=', numero_nf)],
                ['id', 'name', 'date', 'state', 'create_date', 'write_date',
                 'l10n_br_numero_nota_fiscal', 'invoice_date']
            )

            if not faturas:
                print(f"❌ NF {numero_nf} não encontrada no Odoo")
                return

            for fatura in faturas:
                print(f"\n✅ Fatura encontrada:")
                print(f"   - ID: {fatura.get('id')}")
                print(f"   - Nome: {fatura.get('name')}")
                print(f"   - Número NF: {fatura.get('l10n_br_numero_nota_fiscal')}")
                print(f"   - Estado: {fatura.get('state')}")
                print(f"   - Data Fatura: {fatura.get('invoice_date')}")
                print(f"   - Data Documento: {fatura.get('date')}")
                print(f"   - CREATE_DATE: {fatura.get('create_date')}")
                print(f"   - WRITE_DATE: {fatura.get('write_date')}")

                # Converter write_date para comparação
                if fatura.get('write_date'):
                    write_date_str = fatura.get('write_date')
                    print(f"\n📊 Análise do WRITE_DATE:")
                    print(f"   - Write Date: {write_date_str}")

                    # Calcular há quanto tempo foi modificada
                    from datetime import datetime, timedelta
                    import pytz

                    # Parse do write_date (assumindo UTC)
                    if isinstance(write_date_str, str):
                        write_date = datetime.strptime(write_date_str, '%Y-%m-%d %H:%M:%S')
                        write_date = pytz.UTC.localize(write_date)
                    else:
                        write_date = write_date_str

                    agora_utc = datetime.now(pytz.UTC)
                    diferenca = agora_utc - write_date

                    print(f"   - Hora atual UTC: {agora_utc.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   - Diferença: {diferenca.total_seconds() / 60:.1f} minutos")
                    print(f"   - Diferença: {diferenca.total_seconds() / 3600:.1f} horas")
                    print(f"   - Diferença: {diferenca.days} dias")

                    # Verificar se cairia em diferentes janelas
                    print(f"\n📌 Análise de Janelas:")
                    for minutos in [1, 40, 120, 1440, 10080]:
                        janela = agora_utc - timedelta(minutes=minutos)
                        if write_date >= janela:
                            print(f"   ✅ DENTRO da janela de {minutos} minutos")
                        else:
                            print(f"   ❌ FORA da janela de {minutos} minutos")

                # Buscar linhas da fatura
                print(f"\n2. Buscando account.move.line da fatura {fatura.get('id')}...")

                linhas = odoo.search_read(
                    'account.move.line',
                    [('move_id', '=', fatura.get('id'))],
                    ['id', 'product_id', 'quantity', 'create_date', 'write_date'],
                    limit=3  # Só mostrar 3 linhas como exemplo
                )

                print(f"   - Total de linhas: {len(linhas)} (mostrando até 3)")

                for i, linha in enumerate(linhas[:3], 1):
                    print(f"\n   Linha {i}:")
                    print(f"      - ID: {linha.get('id')}")
                    print(f"      - Produto: {linha.get('product_id')}")
                    print(f"      - CREATE_DATE: {linha.get('create_date')}")
                    print(f"      - WRITE_DATE: {linha.get('write_date')}")

    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    # Permitir passar o número da NF como argumento
    numero_nf = sys.argv[1] if len(sys.argv) > 1 else '132656'

    sucesso = verificar_nf(numero_nf)
    sys.exit(0 if sucesso else 1)