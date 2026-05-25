"""ajustar_quant.py — skill `ajustando-quant-odoo`: ajuste atômico de 1 quant.

Expõe o átomo StockQuantAdjustmentService.ajustar_quant via CLI: soma/define/zera
o saldo de UM stock.quant via inventory adjustment (gera 1 stock.move auditável
'Physical Inventory'). `--dry-run` é o DEFAULT — sem `--confirmar` é só preview.

Premissas (produto, empresa->company/location) são resolvidas pelo gold-util
`app/odoo/estoque/_utils.py` (fonte única; o subagente pesquisa premissas dali).

Identificação do quant (mutuamente exclusiva):
  por chave:  --cod <default_code> --empresa <FB|CD|LF> [--local <id>] [--lote <nome>]
  direto:     --quant-id <id>      (ex.: quant fantasma conhecido)

Quantidade (mutuamente exclusiva, obrigatória):
  --delta <x>           soma ao saldo (+/-)
  --valor-absoluto <x>  define o saldo (0 = zerar)

Exemplos:
  # dry-run (default): somar 50 num lote da LF, criar lote/quant se faltar
  python ajustar_quant.py --cod 28239 --empresa LF --lote 26014 --delta 50 --criar-se-faltar
  # efetivar
  python ajustar_quant.py --cod 28239 --empresa LF --lote 26014 --delta 50 --criar-se-faltar --confirmar
  # zerar um quant fantasma por id (e corrigir reserva órfã)
  python ajustar_quant.py --quant-id 12073 --valor-absoluto 0 --resetar-reserva --confirmar

Exit: 0 efetivado (EXECUTADO/EXECUTADO_AUTO_CORRIGIDO/NOOP) · 4 dry-run OK (preview) · 1 falha/bloqueio · 2 uso.
"""
import argparse
import json
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[4]))  # .claude/skills/<skill>/scripts/<f> -> repo root

from app.odoo.estoque._cli_utils import (  # noqa: E402
    adicionar_args_padrao, setup_cli_completo,
)
from app.odoo.estoque._utils import EMPRESAS, resolver_empresa, resolver_produto  # noqa: E402
from app.odoo.estoque.scripts.quant import StockQuantAdjustmentService  # noqa: E402
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

CASAS_DECIMAIS = 6
_FALHAS = {
    'FALHA_PRODUTO', 'FALHA_LOCAL', 'BLOQUEADO_SERIAL', 'FALHA_LOTE',
    'FALHA_CRIAR_LOTE', 'FALHA_QUANT_VAZIO', 'FALHA_QUANT_NEGATIVO',
    'FALHA_RESERVADO', 'FALHA_DELTA_DIVERGENTE', 'FALHA_ODOO',
}


def _emitir(out: dict, dry_run: bool) -> int:
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    status = (out.get('resultado') or {}).get('status', out.get('status', ''))
    if status in _FALHAS:
        return 1
    if dry_run:
        return 4 if status == 'DRY_RUN_OK' else 1
    return 0 if status in ('EXECUTADO', 'EXECUTADO_AUTO_CORRIGIDO', 'NOOP') else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    ap.add_argument('--quant-id', type=int, help='quant direto (alternativa à chave)')
    ap.add_argument('--cod', help='default_code do produto (modo chave)')
    ap.add_argument('--empresa', choices=EMPRESAS, help='FB|CD|LF (modo chave)')
    ap.add_argument('--local', type=int,
                    help='location_id (default: COMPANY_LOCATIONS[company])')
    ap.add_argument('--lote', help='nome do lote (omitir = sem lote; obrigatório se tracking=lot)')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--delta', type=float, help='soma ao saldo (+/-)')
    g.add_argument('--valor-absoluto', type=float, help='define o saldo (0 = zerar)')
    ap.add_argument('--criar-se-faltar', action='store_true',
                    help='cria lote/quant se faltar (exige chave + --delta > 0)')
    ap.add_argument('--resetar-reserva', action='store_true',
                    help='zera reserved_quantity antes (corrige reserva órfã/negativa)')
    ap.add_argument('--delta-esperado', type=float, default=None,
                    help='pedido ORIGINAL de ajuste (recomendado em retomada de '
                         'FALHA com --resetar-reserva ou --valor-absoluto). '
                         'Aborta se |ajuste_aplicado - delta_esperado| > tolerancia. '
                         'Protege contra bug CICLAMATO 2026-05-23.')
    ap.add_argument('--tolerancia-delta', type=float, default=0.1,
                    help='tolerancia para --delta-esperado (default 0.1 un)')
    ap.add_argument('--corrigir-para-esperado', action='store_true',
                    help='quando divergente, APLICA delta_esperado em vez de bloquear '
                         '(status EXECUTADO_AUTO_CORRIGIDO). Sem esse flag, divergencia '
                         'gera FALHA_DELTA_DIVERGENTE.')
    ap.add_argument('--confirmar', action='store_true',
                    help='EFETIVA no Odoo. Sem isso = dry-run (preview).')
    adicionar_args_padrao(ap)  # --quiet + --forcar-concorrencia (v7)
    args = ap.parse_args()

    dry_run = not args.confirmar
    delta, valor_absoluto = args.delta, args.valor_absoluto
    criar = bool(args.criar_se_faltar) and (delta is not None and delta > 0)

    app = setup_cli_completo(__file__, args.quiet, args.forcar_concorrencia)
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        svc = StockQuantAdjustmentService(odoo=odoo, lot_svc=lot_svc)

        # ---- Modo direto (quant_id) ----
        if args.quant_id:
            res = svc.ajustar_quant(
                quant_id=args.quant_id, delta=delta, valor_absoluto=valor_absoluto,
                resetar_reserva=args.resetar_reserva, casas_decimais=CASAS_DECIMAIS,
                delta_esperado=args.delta_esperado,
                tolerancia_delta=args.tolerancia_delta,
                corrigir_para_esperado=args.corrigir_para_esperado,
                dry_run=dry_run,
            )
            return _emitir({'modo': 'dry-run' if dry_run else 'confirmado',
                            'chave': {'quant_id': args.quant_id}, 'resultado': res}, dry_run)

        # ---- Modo chave (cod + empresa) ----
        if not (args.cod and args.empresa):
            ap.error('sem --quant-id, informe --cod e --empresa')

        # Premissa: empresa -> company_id/location_id (gold-util _utils)
        try:
            prem = resolver_empresa(args.empresa, local=args.local)
        except ValueError as exc:
            return _emitir({'status': 'FALHA_LOCAL', 'erro': str(exc)}, dry_run)
        company_id, location_id = prem['company_id'], prem['location_id']

        # Premissa: default_code -> produto (gold-util _utils)
        prod = resolver_produto(odoo, args.cod)
        if not prod:
            return _emitir({'status': 'FALHA_PRODUTO',
                            'erro': f'default_code {args.cod!r} não encontrado'}, dry_run)

        chave = {'cod': args.cod, 'produto': prod['name'], 'tracking': prod['tracking'],
                 'company_id': company_id, 'location_id': location_id, 'lote': args.lote}
        if prod['n_matches'] > 1:
            chave['warning_multiplos_codigos'] = prod['n_matches']
        if not prod['active']:
            chave['warning_produto_inativo'] = True

        if prod['tracking'] == 'serial':
            return _emitir({'status': 'BLOQUEADO_SERIAL', 'chave': chave,
                            'erro': 'produto tracking=serial — ajuste por qtd não suportado'}, dry_run)

        # Premissa: lote (mesma regra do orquestrador: positivo cria, negativo exige)
        lot_id = None
        if prod['tracking'] == 'lot':
            if not args.lote:
                return _emitir({'status': 'FALHA_LOTE', 'chave': chave,
                                'erro': 'produto tracking=lot exige --lote'}, dry_run)
            lot_id = lot_svc.buscar_por_nome(args.lote, prod['pid'], company_id)
            if lot_id:
                chave['lote_acao'] = 'reused'
            elif not criar:
                return _emitir({'status': 'FALHA_LOTE', 'chave': chave, 'erro': (
                    f'lote {args.lote!r} não existe; use --criar-se-faltar com --delta > 0')}, dry_run)
            elif dry_run:
                chave['lote_acao'] = 'will_create'
                return _emitir({'status': 'DRY_RUN_OK', 'chave': chave, 'qty_antes': 0.0,
                                'qty_apos': delta, 'ajuste_aplicado': delta,
                                'quant_acao': 'will_create'}, dry_run)
            else:
                lot_id, criado = lot_svc.criar_se_nao_existe(
                    args.lote, prod['pid'], company_id, expiration_date=None)
                chave['lote_acao'] = 'created' if criado else 'reused'
        elif args.lote:
            chave['warning_lote_ignorado'] = f'tracking=none — lote {args.lote!r} ignorado'

        res = svc.ajustar_quant(
            product_id=prod['pid'], company_id=company_id, location_id=location_id,
            lot_id=lot_id, delta=delta, valor_absoluto=valor_absoluto,
            criar_se_faltar=criar, resetar_reserva=args.resetar_reserva,
            casas_decimais=CASAS_DECIMAIS,
            delta_esperado=args.delta_esperado,
            tolerancia_delta=args.tolerancia_delta,
            corrigir_para_esperado=args.corrigir_para_esperado,
            dry_run=dry_run,
        )
        return _emitir({'modo': 'dry-run' if dry_run else 'confirmado',
                        'chave': chave, 'resultado': res}, dry_run)


if __name__ == '__main__':
    sys.exit(main())
