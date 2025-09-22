#!/usr/bin/env python3
"""
Script de TESTE - Importação de NFs de apenas 1 dia para validar
================================================================
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    from app import create_app
    from app.odoo.utils.connection import get_odoo_connection

    # Testar com apenas 1 dia
    DATA_TESTE = date(2025, 9, 20)  # 20/09/2025 (sexta-feira)

    logger.info("="*60)
    logger.info("🧪 TESTE: Importação de NFs de 1 dia")
    logger.info(f"📅 Data: {DATA_TESTE.strftime('%d/%m/%Y')}")
    logger.info("="*60)

    app = create_app()

    with app.app_context():
        try:
            odoo = get_odoo_connection()

            # Buscar NFs do dia
            domain = [
                ('state', '=', 'posted'),
                ('move_type', '=', 'out_invoice'),
                ('invoice_date', '=', DATA_TESTE.strftime('%Y-%m-%d'))
            ]

            logger.info(f"Domain: {domain}")

            invoice_ids = odoo.models.execute_kw(
                'account.move',
                'search',
                [domain],
                {'limit': 100}
            )

            logger.info(f"✅ Encontradas {len(invoice_ids)} NFs em {DATA_TESTE.strftime('%d/%m/%Y')}")

            if invoice_ids:
                # Buscar algumas informações
                invoices = odoo.models.execute_kw(
                    'account.move',
                    'read',
                    [invoice_ids[:5]],  # Pegar apenas 5 para exemplo
                    {'fields': ['name', 'invoice_origin', 'amount_total', 'partner_id']}
                )

                logger.info("\n📋 Exemplos de NFs encontradas:")
                for inv in invoices:
                    logger.info(f"   - NF {inv['name']}: Pedido {inv.get('invoice_origin', 'N/A')}, " +
                              f"Valor R$ {inv.get('amount_total', 0):.2f}, " +
                              f"Cliente {inv['partner_id'][1] if inv.get('partner_id') else 'N/A'}")

            return 0

        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            return 1

if __name__ == '__main__':
    sys.exit(main())