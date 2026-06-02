"""Debug SEFAZ via Playwright para invoice 608607 (caso piloto 210030325 LF).

Wrapper com:
- max_tentativas=2 (rapido)
- intervalo_retry=15s (vs 120s default)
- Screenshots em /tmp/sefaz_debug/ a cada passo
- Logs verbose
- Snapshot do estado l10n_br_* antes e depois de cada tentativa

NAO commita no DB local — apenas chama transmitir_nfe_via_playwright e
imprime resultado. Para gravar chave_nfe + status=EXECUTADO no DB, use
o pipeline F5e via teste_210030325_lf.py apos validar.

Uso:
    python scripts/inventario_2026_05/debug_sefaz_608607.py --company-id=5
"""
import argparse
import logging
import os
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

# Carregar .env antes de importar app (ODOO_USERNAME / ODOO_PASSWORD)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(_THIS.parents[2] / '.env')
except Exception:
    pass

from app import create_app  # noqa: E402 # type: ignore
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402 # type: ignore
from app.recebimento.services.playwright_nfe_transmissao import (  # noqa: E402 # type: ignore
    transmitir_nfe_via_playwright,
)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-8s %(name)s | %(message)s',
)
logger = logging.getLogger('debug_sefaz')


def snapshot_invoice(odoo, invoice_id: int, label: str) -> dict:
    """Imprime estado l10n_br_* + state da invoice."""
    inv = odoo.execute_kw(
        'account.move', 'read', [[invoice_id]],
        {'fields': [
            'name', 'state', 'l10n_br_situacao_nf', 'l10n_br_chave_nf',
            'l10n_br_cstat_nf', 'l10n_br_xmotivo_nf',
        ]},
    )
    inv_data = inv[0] if inv else {}
    print(f'\n--- snapshot invoice {invoice_id} ({label}) ---')
    for k, v in inv_data.items():
        print(f'  {k} = {v!r}')
    return inv_data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--company-id', type=int, required=True,
                        choices=[1, 4, 5],
                        help='Empresa (1=FB, 4=CD, 5=LF). OBRIGATORIO.')
    parser.add_argument('--invoice-id', type=int, default=608607,
                        help='account.move.id (default: 608607 piloto)')
    parser.add_argument('--max-tentativas', type=int, default=2,
                        help='max tentativas (default: 2, rapido). '
                             'Apos validar: aumente para 15.')
    parser.add_argument('--intervalo-retry', type=int, default=15,
                        help='segundos entre tentativas (default: 15, rapido). '
                             'Apos validar: aumente para 120.')
    args = parser.parse_args()

    screenshots_dir = Path('/tmp/sefaz_debug')
    screenshots_dir.mkdir(exist_ok=True)
    print(f'Screenshots em: {screenshots_dir}/')
    print(f'env ODOO_URL: {os.getenv("ODOO_URL", "<NAO_SET>")[:60]}...')
    print(f'env ODOO_USERNAME: {os.getenv("ODOO_USERNAME", "<NAO_SET>")[:30]}')
    print(f'env ODOO_PASSWORD: {"<SET>" if os.getenv("ODOO_PASSWORD") else "<NAO_SET>"}')
    print(f'Company-id: {args.company_id}')
    print(f'Invoice-id: {args.invoice_id}')
    print(f'max_tentativas: {args.max_tentativas}  intervalo_retry: {args.intervalo_retry}s')

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        snapshot_invoice(odoo, args.invoice_id, 'ANTES')

        print('\n=== Rodando transmitir_nfe_via_playwright ===\n')
        resultado = transmitir_nfe_via_playwright(
            args.invoice_id, odoo, logger,
            max_tentativas=args.max_tentativas,
            intervalo_retry=args.intervalo_retry,
        )

        print(f'\n=== Resultado ===')
        for k, v in resultado.items():
            print(f'  {k} = {v!r}')

        snapshot_invoice(odoo, args.invoice_id, 'DEPOIS')

        # Listar screenshots gerados
        screenshots = sorted(screenshots_dir.glob('*.png'))
        if screenshots:
            print(f'\nScreenshots gerados ({len(screenshots)}):')
            for s in screenshots:
                size_kb = s.stat().st_size // 1024
                print(f'  {s.name} ({size_kb}KB)')


if __name__ == '__main__':
    main()
