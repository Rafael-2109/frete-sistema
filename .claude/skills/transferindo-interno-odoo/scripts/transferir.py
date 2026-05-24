"""transferir.py — skill `transferindo-interno-odoo`: atomo C2 de transferencia interna.

Expoe o atomo `StockInternalTransferService.transferir_entre_lotes_v2` ou
`transferir_entre_locations` via CLI: 2 inventory adjustments (reducao origem +
aumento destino) compostos, com `delta_esperado` propagado em CADA passo (herda
guard anti-bug CICLAMATO da Skill 1).

`--dry-run` e o DEFAULT — sem `--confirmar` e so preview.

Identificacao do produto/empresa (sempre):
  --cod <default_code>  --empresa <FB|CD|LF>  [--local <id>]

Modo (mutuamente exclusivo, obrigatorio):
  Modo A — lote -> lote (mesma location):
    --lote-origem <nome|VAZIO> --lote-destino <nome>
  Modo B — location -> location (mesmo lote):
    --loc-origem <id> --loc-destino <id> [--lote <nome|VAZIO>]

Quantidade:
  --qty <float positivo>

Comportamento:
  --resetar-reserva-origem  zera reserved_quantity da origem ANTES do ajuste
  --tolerancia-delta T      tolerancia para guard delta_esperado (default 0.001)
  --confirmar               EFETIVA no Odoo (sem isso = dry-run)

Exit: 0 efetivado (EXECUTADO) - 4 dry-run OK (preview) - 1 falha/bloqueio - 2 uso.

Exemplos:
  # 1) dry-run (default): mover 35 un de MIGRACAO -> 'MI 027-098/26' em FB/Estoque
  python transferir.py --cod 104000015 --empresa FB --qty 35.0 \\
      --lote-origem 'MIGRAÇÃO' --lote-destino 'MI 027-098/26'

  # 2) efetivar
  python transferir.py --cod 104000015 --empresa FB --qty 35.0 \\
      --lote-origem 'MIGRAÇÃO' --lote-destino 'MI 027-098/26' --confirmar

  # 3) mover mesmo lote MIGRACAO entre 2 locations (FB/Estoque -> FB/Indisponivel)
  python transferir.py --cod 104000015 --empresa FB --qty 1175.0 \\
      --lote 'MIGRAÇÃO' --loc-origem 8 --loc-destino 31088 --confirmar
"""
import argparse
import json
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[4]))  # .claude/skills/<skill>/scripts/<f> -> repo root

from app import create_app  # noqa: E402
from app.odoo.estoque._utils import EMPRESAS, resolver_empresa, resolver_produto  # noqa: E402
from app.odoo.estoque.scripts.transfer import StockInternalTransferService  # noqa: E402
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

CASAS_DECIMAIS = 6
_FALHAS = {
    'FALHA_PRODUTO', 'FALHA_LOCAL', 'FALHA_LOTE', 'FALHA_REDUCAO',
    'FALHA_AUMENTO', 'BLOQUEADO_SERIAL', 'FALHA_ODOO',
}


def _emitir(out: dict, dry_run: bool) -> int:
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    status = (out.get('resultado') or {}).get('status', out.get('status', ''))
    if status in _FALHAS:
        return 1
    if dry_run:
        return 4 if status == 'DRY_RUN_OK' else 1
    return 0 if status == 'EXECUTADO' else 1


def _resolver_lote_id(lot_svc, nome, pid, company_id, lado='origem'):
    """Resolve lote nome -> id; aceita None/'P-15/05' como sem-lote (lot_id=None).

    Returns (lot_id, label, erro|None). lot_id=None pode significar:
    - usuario pediu sem-lote (None/'P-15/05'): label='P-15/05(sem-lote)', erro=None
    - lote nao existe (literal): label=nome, erro!=None
    """
    if nome is None or (isinstance(nome, str) and nome.strip() in ('', 'P-15/05')):
        return None, 'P-15/05(sem-lote)', None
    lid = lot_svc.buscar_por_nome(nome.strip(), pid, company_id)
    if lid:
        return lid, nome.strip(), None
    return None, nome.strip(), (
        f'lote {nome!r} nao existe para product_id={pid} company_id={company_id}'
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    # Identificacao
    ap.add_argument('--cod', required=True, help='default_code do produto')
    ap.add_argument('--empresa', required=True, choices=EMPRESAS,
                    help='FB|CD|LF (resolve company_id + location default)')
    ap.add_argument('--local', type=int,
                    help='location_id (default: COMPANY_LOCATIONS[company]). '
                         'Usado em MODO A (lote -> lote). MODO B usa --loc-origem/--loc-destino.')

    # Quantidade
    ap.add_argument('--qty', required=True, type=float,
                    help='quantidade a transferir (positiva)')

    # Modo A (lote -> lote)
    ap.add_argument('--lote-origem',
                    help='[MODO A] nome do lote ORIGEM (VAZIO ou P-15/05 = sem lote)')
    ap.add_argument('--lote-destino',
                    help='[MODO A] nome do lote DESTINO (criado se faltar; '
                         'MIGRAÇÃO consolida com 3 variantes G022)')

    # Modo B (loc -> loc, mesmo lote)
    ap.add_argument('--loc-origem', type=int,
                    help='[MODO B] location_id origem')
    ap.add_argument('--loc-destino', type=int,
                    help='[MODO B] location_id destino')
    ap.add_argument('--lote',
                    help='[MODO B] nome do lote (mesmo nos 2 lados; default = sem lote)')

    # Comportamento
    ap.add_argument('--resetar-reserva-origem', action='store_true',
                    help='zera reserved_quantity da origem ANTES do ajuste '
                         '(NAO cancela picking; corrige reserva fantasma)')
    ap.add_argument('--tolerancia-delta', type=float, default=0.001,
                    help='tolerancia absoluta para guard delta_esperado (default 0.001)')
    ap.add_argument('--confirmar', action='store_true',
                    help='EFETIVA no Odoo. Sem isso = dry-run (preview).')
    args = ap.parse_args()

    dry_run = not args.confirmar

    if args.qty <= 0:
        ap.error(f'--qty deve ser > 0 (recebido {args.qty})')

    # Modo A detectado por: --lote-origem OU --lote-destino presentes (incluindo '' = proxy vazio P-15/05).
    # Modo B detectado por: --loc-origem ou --loc-destino com valor.
    # NB: argparse com nargs default permite `--lote-origem ''` (string vazia) — checar `is not None`,
    # NAO truthy, para nao bloquear o proxy P-15/05 (CR1#1, 2026-05-24 v2).
    modo_a = (args.lote_origem is not None) or (args.lote_destino is not None)
    modo_b = (args.loc_origem is not None) or (args.loc_destino is not None)
    if modo_a and modo_b:
        ap.error(
            'modos A (lote->lote) e B (loc->loc) sao mutuamente exclusivos. '
            'Use --lote-origem/--lote-destino OU --loc-origem/--loc-destino, nao ambos.'
        )
    if not modo_a and not modo_b:
        ap.error(
            'forneca um modo: A (--lote-origem + --lote-destino) ou '
            'B (--loc-origem + --loc-destino [--lote])'
        )
    if modo_a and not (args.lote_origem is not None and args.lote_destino is not None):
        ap.error('MODO A exige --lote-origem E --lote-destino (use "" para proxy vazio P-15/05 na origem)')
    if modo_b and not (args.loc_origem is not None and args.loc_destino is not None):
        ap.error('MODO B exige --loc-origem E --loc-destino')

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        svc = StockInternalTransferService(odoo=odoo, lot_svc=lot_svc)

        # Premissa: empresa -> company_id/location_id
        try:
            prem = resolver_empresa(args.empresa, local=args.local)
        except ValueError as exc:
            return _emitir({'status': 'FALHA_LOCAL', 'erro': str(exc)}, dry_run)
        company_id, location_default = prem['company_id'], prem['location_id']

        # Premissa: default_code -> produto
        prod = resolver_produto(odoo, args.cod)
        if not prod:
            return _emitir({'status': 'FALHA_PRODUTO',
                            'erro': f'default_code {args.cod!r} nao encontrado'}, dry_run)

        chave = {
            'cod': args.cod, 'produto': prod['name'],
            'tracking': prod['tracking'],
            'company_id': company_id, 'empresa': args.empresa,
        }
        if prod['n_matches'] > 1:
            chave['warning_multiplos_codigos'] = prod['n_matches']
        if not prod['active']:
            chave['warning_produto_inativo'] = True

        if prod['tracking'] == 'serial':
            return _emitir({'status': 'BLOQUEADO_SERIAL', 'chave': chave,
                            'erro': 'produto tracking=serial — transferencia por qtd nao suportada'},
                           dry_run)

        # ---- MODO A: lote -> lote (mesma location) ----
        if modo_a:
            location_id = args.local or location_default
            chave['modo'] = 'lote->lote'
            chave['location_id'] = location_id
            chave['lote_origem_nome'] = args.lote_origem
            chave['lote_destino_nome'] = args.lote_destino

            # Resolver lote origem (None aceita = sem lote / P-15/05 proxy)
            lot_origem_id, label_o, erro_o = _resolver_lote_id(
                lot_svc, args.lote_origem, prod['pid'], company_id, 'origem',
            )
            chave['lote_origem_label'] = label_o
            if erro_o:
                return _emitir({'status': 'FALHA_LOTE', 'chave': chave, 'erro': erro_o}, dry_run)

            # Resolver lote destino (cria se faltar via wrapper resolver_lote_destino do service)
            lot_destino_id, label_d, criado = svc.resolver_lote_destino(
                nome_lote=args.lote_destino,
                product_id=prod['pid'], company_id=company_id,
                location_id=location_id,
                criar_se_faltar=not dry_run,  # em dry-run nao cria — so simula
                expiration_date=None,
            )
            chave['lote_destino_label'] = label_d
            chave['lote_destino_acao'] = (
                'created' if criado else ('reused' if lot_destino_id else 'will_create')
            )
            if lot_destino_id is None:
                if dry_run:
                    # Vai criar no --confirmar; simular no nivel skill 1
                    return _emitir({
                        'modo': 'dry-run', 'chave': chave,
                        'status': 'DRY_RUN_OK',
                        'plano': f'Transferir {args.qty} un de lote {label_o!r} -> {label_d!r} '
                                 f'(destino sera criado no --confirmar)',
                    }, dry_run)
                return _emitir({
                    'status': 'FALHA_LOTE', 'chave': chave,
                    'erro': f'lote destino {args.lote_destino!r} nao pode ser resolvido nem criado',
                }, dry_run)
            if lot_origem_id == lot_destino_id:
                return _emitir({
                    'status': 'FALHA_LOTE', 'chave': chave,
                    'erro': f'lote origem == destino (id={lot_origem_id} {label_o!r})',
                }, dry_run)

            res = svc.transferir_entre_lotes_v2(
                product_id=prod['pid'], company_id=company_id,
                location_id=location_id,
                qty=args.qty,
                lot_id_origem=lot_origem_id,
                lot_id_destino=lot_destino_id,
                resetar_reserva_origem=args.resetar_reserva_origem,
                tolerancia_delta=args.tolerancia_delta,
                dry_run=dry_run,
            )
            return _emitir({'modo': 'dry-run' if dry_run else 'confirmado',
                            'chave': chave, 'resultado': res}, dry_run)

        # ---- MODO B: loc -> loc (mesmo lote) ----
        chave['modo'] = 'loc->loc'
        chave['location_id_origem'] = args.loc_origem
        chave['location_id_destino'] = args.loc_destino
        chave['lote_nome'] = args.lote or '(sem lote / P-15/05)'

        # Resolver lote (mesmo nos 2 lados) — None = sem lote
        lot_id, label, erro = _resolver_lote_id(
            lot_svc, args.lote, prod['pid'], company_id, 'lote',
        )
        chave['lote_label'] = label
        if erro:
            return _emitir({'status': 'FALHA_LOTE', 'chave': chave, 'erro': erro}, dry_run)

        res = svc.transferir_entre_locations(
            product_id=prod['pid'], company_id=company_id,
            lot_id=lot_id,
            qty=args.qty,
            location_id_origem=args.loc_origem,
            location_id_destino=args.loc_destino,
            resetar_reserva_origem=args.resetar_reserva_origem,
            tolerancia_delta=args.tolerancia_delta,
            dry_run=dry_run,
        )
        return _emitir({'modo': 'dry-run' if dry_run else 'confirmado',
                        'chave': chave, 'resultado': res}, dry_run)


if __name__ == '__main__':
    sys.exit(main())
