"""auditar_cadastro_inventario.py — CLI wrapper da Skill C5.

Skill `auditando-cadastro-fiscal-odoo` — perfil V1 'inventario'. Roda
pre-flight de cadastro fiscal (G017/G018/G035/G014) + duplicacao pipeline
(D-OPS-2) + flag tracking='none' (D-OPS-3) ANTES de operacoes que tocam
SEFAZ (faturamento inventario, transferencia inter-company).

Entradas (mutuamente exclusivas):
  --produtos PID1,PID2     ids do Odoo
  --cods C1,C2             default_code do Odoo
  --ciclo NOME             le AjusteEstoqueInventario (status ATIVOS) do ciclo

Modo:
  --dry-run                default — apenas reporta (READ-only)
  --confirmar              autoriza WRITE (so' G035 auto-fix com --auto-corrigir-barcode)

Flags:
  --perfil inventario      (V1 — futuro: venda-cliente)
  --auto-corrigir-barcode  G035 auto-fix (limpa product.barcode invalido)
  --no-pipeline-check      skip D-OPS-2 (duplicacao pipeline ativo)
  --no-lote-vencido-check  skip G014

Exit codes:
  0 = PRE_FLIGHT_OK
  1 = PRE_FLIGHT_BLOQUEADO
  2 = PRE_FLIGHT_WARN
  3 = erro de uso

Output: JSON estruturado em stdout.

Exemplos:
  # ciclo inteiro (uso Skill 8)
  python auditar_cadastro_inventario.py --ciclo INVENTARIO_2026_05

  # cods + auto-fix barcode
  python auditar_cadastro_inventario.py --cods "102020600,4829046" \\
      --auto-corrigir-barcode --confirmar

  # ids sem pipeline check
  python auditar_cadastro_inventario.py --produtos 30629,30630 \\
      --no-pipeline-check
"""
import argparse
import json
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[4]))  # repo root


def _parse_int_list(s: str) -> list:
    return [int(x.strip()) for x in s.split(',') if x.strip()]


def _parse_str_list(s: str) -> list:
    return [x.strip() for x in s.split(',') if x.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument('--produtos', help='IDs Odoo product.product, csv')
    grupo.add_argument('--cods', help='default_code, csv')
    grupo.add_argument('--ciclo', help='Nome do ciclo (le AjusteEstoqueInventario)')

    parser.add_argument('--perfil', default='inventario',
                        choices=['inventario'],
                        help='Perfil de auditoria (V1: inventario)')
    parser.add_argument('--auto-corrigir-barcode', action='store_true',
                        help='G035: limpa product.barcode invalido (exige --confirmar)')
    parser.add_argument('--no-pipeline-check', action='store_true',
                        help='Skip D-OPS-2 (duplicacao pipeline ativo)')
    parser.add_argument('--no-lote-vencido-check', action='store_true',
                        help='Skip G014 (lote vencido com saldo)')
    parser.add_argument('--confirmar', action='store_true',
                        help='Autoriza WRITE (so G035 auto-fix; sem ele dry-run)')
    parser.add_argument('--json-out', help='Salva output em arquivo (alem de stdout)')

    args = parser.parse_args()

    dry_run = not args.confirmar

    # Imports tardios (apos sys.path setup)
    from app import create_app, db  # noqa: E402
    from app.odoo.estoque.scripts.cadastro_fiscal_audit import (  # noqa: E402
        CadastroFiscalAuditService,
    )
    from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

    odoo = get_odoo_connection()
    if odoo is None:
        print(json.dumps({
            'status_global': 'PRE_FLIGHT_BLOQUEADO',
            'pode_faturar': False,
            'erro': 'Sem conexao Odoo (env ODOO_* faltando?)',
        }, indent=2, ensure_ascii=False))
        sys.exit(3)

    app = create_app()
    with app.app_context():
        svc = CadastroFiscalAuditService(odoo=odoo, db_session=db.session)

        kwargs = {
            'auto_corrigir_barcode': args.auto_corrigir_barcode,
            'verificar_duplicacao_pipeline': not args.no_pipeline_check,
            'verificar_lote_vencido': not args.no_lote_vencido_check,
            'dry_run': dry_run,
        }
        if args.produtos:
            kwargs['produto_ids'] = _parse_int_list(args.produtos)
        elif args.cods:
            kwargs['cods_produto'] = _parse_str_list(args.cods)
        elif args.ciclo:
            kwargs['ciclo'] = args.ciclo

        res = svc.auditar_perfil_inventario(**kwargs)

    out_json = json.dumps(res, indent=2, ensure_ascii=False, default=str)
    print(out_json)
    if args.json_out:
        Path(args.json_out).write_text(out_json, encoding='utf-8')

    # Exit code
    if res['status_global'] == 'PRE_FLIGHT_OK':
        sys.exit(0)
    if res['status_global'] == 'PRE_FLIGHT_BLOQUEADO':
        sys.exit(1)
    if res['status_global'] == 'PRE_FLIGHT_WARN':
        sys.exit(2)
    sys.exit(3)


if __name__ == '__main__':
    main()
