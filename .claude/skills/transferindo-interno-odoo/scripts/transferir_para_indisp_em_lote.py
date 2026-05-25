"""transferir_para_indisp_em_lote.py — orquestrador de planilha (cod, qty) -> Indisponivel.

Skill `transferindo-interno-odoo` — CAMADA DE ALTO NIVEL sobre o atomo
`transferir_para_indisponivel` (modo C). Para cada linha (cod, qty) da
planilha:
  1. Resolve product_id via default_code.
  2. Lista quants origem do produto/empresa em locs internas exceto Indisp
     (default por company: FB=[8,48,4066,4067,4068,27458] / CD=[32] / LF=[42]).
  3. Ordena quants por politica (`MIGRACAO_FIRST_FIFO` default).
  4. Greedy: drena quants ate atingir qty_solicitada. Cada chamada interna
     usa `transferir_para_indisponivel` (Modo C).
  5. Coleta resultados: qty_movida, qty_nao_movida, transferencias, quants
     pulados.

`--dry-run` e o DEFAULT — sem `--confirmar` so simula.

Demanda real 2026-05-25: 158 cods FB (planilha cod+qty so),
movimento para FB/Indisponivel consolidando MIGRAÇÃO POR PRODUTO.

INPUTS:
  --planilha CSV_PATH         CSV/TSV com colunas (cod, qty[, nome opcional])
                              OU
  --cods "C1=Q1,C2=Q2,..."   inline (debug; ate poucos cods)

  --empresa FB|CD|LF          required (resolve company_id + locs default)

POLITICAS / CUSTOMIZACAO:
  --politica POL              MIGRACAO_FIRST_FIFO (default) | FIFO | MAIOR_SALDO
  --locs-origem "id1,id2,..." override das locs default (csv numerico)
  --resetar-reserva-origem    aplica em CADA chamada interna (defensivo)
  --tolerancia-delta T        default 0.001
  --nome-lote-destino NOME    default 'MIGRAÇÃO' (consolidador no destino)

MODO:
  --dry-run                   default (preview)
  --confirmar                 EFETIVA no Odoo

OUTPUT:
  stdout                       JSON estruturado {cods: [...], sumario: {...}}
  --csv-out PATH               opcional — 1 linha por transferencia (audit)
  --csv-pendencias PATH        opcional — 1 linha por cod com parcial/falha

EXIT CODES:
  0 = tudo executado total (confirmado, sem falhas)
  4 = dry-run OK total (qty_solicitada coberta em simulacao para TODOS)
  1 = uma ou mais FALHAS (FALHA_PRE_COND, FALHA_SEM_QUANT, FALHA_PARCIAL_NAO_TOLERADO,
                          OU em real: EXECUTADO_PARCIAL sem tolerar)
  2 = erro de uso (argparse / planilha invalida)

EXEMPLOS:
  # planilha CSV, dry-run (default)
  python transferir_para_indisp_em_lote.py --planilha /tmp/demanda.csv --empresa FB

  # planilha CSV, real, com resetar-reserva
  python transferir_para_indisp_em_lote.py --planilha /tmp/demanda.csv --empresa FB \\
      --resetar-reserva-origem --confirmar \\
      --csv-out /tmp/audit.csv --csv-pendencias /tmp/pendencias.csv

  # inline (debug, 3 cods)
  python transferir_para_indisp_em_lote.py --cods "104000015=100,3800005=50" \\
      --empresa FB
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[4]))  # repo root

from app.odoo.estoque._cli_utils import (  # noqa: E402
    adicionar_args_padrao, setup_cli_completo,
)
from app.odoo.estoque._utils import EMPRESAS, resolver_empresa, resolver_produto  # noqa: E402
from app.odoo.estoque.scripts.transfer import (  # noqa: E402
    POLITICAS_VALIDAS, POLITICA_MIGRACAO_FIRST_FIFO,
    StockInternalTransferService,
)
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

CASAS_DECIMAIS = 6

# Status considerados FALHA para exit code (vs sucesso/dry-run).
_STATUS_FALHA = {
    'FALHA_PRE_COND', 'FALHA_SEM_QUANT', 'FALHA_PARCIAL_NAO_TOLERADO',
    'FALHA_PRODUTO',  # erro orquestrador (cod nao existe)
}
_STATUS_PARCIAL = {'EXECUTADO_PARCIAL', 'DRY_RUN_PARCIAL'}
_STATUS_OK_TOTAL = {'EXECUTADO_TOTAL', 'DRY_RUN_OK'}


def _carregar_planilha(path: str) -> List[Dict[str, Any]]:
    """Carrega CSV/TSV com colunas 'cod', 'qty', 'nome' (opcional).

    Aceita separador ',' ou TAB; detecta via sniffer. Coluna 'qty' pode
    usar ',' como decimal (PT-BR) ou '.' (EN). Linhas com qty<=0 ou
    cod vazio sao descartadas com aviso (stderr).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f'planilha nao encontrada: {path}')

    out: List[Dict[str, Any]] = []
    with p.open('r', encoding='utf-8') as f:
        sample = f.read(2048)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=',\t;|')
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        # Normalizar nomes de colunas (case-insensitive, trim)
        for idx, row in enumerate(reader, 1):
            cols = {(k or '').strip().lower(): (v or '').strip()
                    for k, v in row.items()}
            cod = cols.get('cod') or cols.get('codigo') or cols.get('default_code')
            qty_raw = cols.get('qty') or cols.get('quantidade') or cols.get('quantity')
            nome = cols.get('nome') or cols.get('produto') or cols.get('product')
            if not cod or not qty_raw:
                print(f'  AVISO: linha {idx} pulada (cod/qty vazio)', file=sys.stderr)
                continue
            # Normalizar qty (aceita PT-BR ',' como decimal)
            qty_norm = qty_raw.replace('.', '').replace(',', '.') if (',' in qty_raw and '.' in qty_raw) else qty_raw.replace(',', '.')
            try:
                qty = float(qty_norm)
            except ValueError:
                print(f'  AVISO: linha {idx} pulada (qty invalida: {qty_raw!r})',
                      file=sys.stderr)
                continue
            if qty <= 0:
                print(f'  AVISO: linha {idx} pulada (qty={qty} <= 0)',
                      file=sys.stderr)
                continue
            out.append({
                'cod': cod, 'qty': round(qty, CASAS_DECIMAIS), 'nome': nome,
                'linha_planilha': idx,
            })
    return out


def _parsear_cods_inline(raw: str) -> List[Dict[str, Any]]:
    """Parse '--cods C1=Q1,C2=Q2,...' -> lista de {cod, qty}."""
    out: List[Dict[str, Any]] = []
    for idx, pair in enumerate(raw.split(','), 1):
        pair = pair.strip()
        if not pair:
            continue
        if '=' not in pair:
            raise ValueError(f'formato invalido (esperado COD=QTY): {pair!r}')
        cod, qty_raw = pair.split('=', 1)
        cod = cod.strip()
        qty_raw = qty_raw.strip().replace(',', '.')
        try:
            qty = float(qty_raw)
        except ValueError as e:
            raise ValueError(f'qty invalida em {pair!r}: {e}') from e
        if qty <= 0:
            raise ValueError(f'qty deve ser > 0 (recebido {qty} em {pair!r})')
        out.append({'cod': cod, 'qty': round(qty, CASAS_DECIMAIS),
                    'nome': None, 'linha_planilha': idx})
    return out


def _processar_cod(
    svc: StockInternalTransferService,
    odoo,
    linha: Dict[str, Any],
    company_id: int,
    locs_origem: Optional[List[int]],
    politica: str,
    resetar_reserva: bool,
    tolerancia_delta: float,
    nome_lote_destino: str,
    dry_run: bool,
) -> Dict[str, Any]:
    """Processa 1 linha da planilha. Retorna dict pronto para JSON.

    Falha de produto = FALHA_PRODUTO (anomalia da planilha — produto
    inexistente). Resto delegado a distribuir_para_indisponivel.
    """
    cod = linha['cod']
    qty = linha['qty']
    inicio = time.time()

    # Resolver produto
    prod = resolver_produto(odoo, cod)
    if not prod:
        return {
            'cod': cod, 'qty_solicitada': qty,
            'nome_planilha': linha.get('nome'),
            'linha_planilha': linha['linha_planilha'],
            'status': 'FALHA_PRODUTO',
            'qty_movida': 0.0, 'qty_nao_movida': qty,
            'erro': f'default_code {cod!r} nao encontrado em product.product',
            'transferencias': [],
            'tempo_ms': int((time.time() - inicio) * 1000),
        }
    if prod['tracking'] == 'serial':
        return {
            'cod': cod, 'qty_solicitada': qty,
            'nome_planilha': linha.get('nome'),
            'linha_planilha': linha['linha_planilha'],
            'produto_id': prod['pid'], 'produto_nome': prod['name'],
            'status': 'BLOQUEADO_SERIAL',
            'qty_movida': 0.0, 'qty_nao_movida': qty,
            'erro': f'produto {cod} tracking=serial — transferencia por qtd nao suportada',
            'transferencias': [],
            'tempo_ms': int((time.time() - inicio) * 1000),
        }

    # Distribuir
    try:
        res = svc.distribuir_para_indisponivel(
            product_id=prod['pid'],
            company_id=company_id,
            qty_solicitada=qty,
            locs_origem=locs_origem,
            politica_ordem=politica,
            resetar_reserva_origem=resetar_reserva,
            tolerancia_delta=tolerancia_delta,
            nome_lote_destino=nome_lote_destino,
            dry_run=dry_run,
            tolerar_parcial=True,
        )
    except ValueError as exc:
        return {
            'cod': cod, 'qty_solicitada': qty,
            'nome_planilha': linha.get('nome'),
            'linha_planilha': linha['linha_planilha'],
            'produto_id': prod['pid'], 'produto_nome': prod['name'],
            'status': 'FALHA_PRE_COND',
            'qty_movida': 0.0, 'qty_nao_movida': qty,
            'erro': str(exc),
            'transferencias': [],
            'tempo_ms': int((time.time() - inicio) * 1000),
        }

    out = {
        'cod': cod, 'qty_solicitada': qty,
        'nome_planilha': linha.get('nome'),
        'linha_planilha': linha['linha_planilha'],
        'produto_id': prod['pid'], 'produto_nome': prod['name'],
        'status': res['status'],
        'qty_movida': res['qty_movida'],
        'qty_nao_movida': res['qty_nao_movida'],
        'transferencias': res['transferencias'],
        'quants_disponiveis': res['quants_disponiveis'],
        'quants_pulados': res['quants_pulados'],
        'politica_ordem': res['politica_ordem'],
        'locs_origem_usadas': res['locs_origem_usadas'],
        'erro': res['erro'],
        'tempo_ms': res['tempo_ms'],
    }
    return out


def _escrever_csv_out(path: str, resultados: List[Dict[str, Any]]) -> None:
    """1 linha por transferencia interna realizada (audit detalhado)."""
    p = Path(path)
    with p.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow([
            'cod', 'qty_solicitada', 'cod_status', 'transf_idx',
            'lot_id_origem', 'lote_origem_nome', 'location_id_origem',
            'qty_pretendida', 'qty_movida', 'transf_status',
            'tempo_ms_transf',
        ])
        for r in resultados:
            transfs = r.get('transferencias') or []
            if not transfs:
                w.writerow([r['cod'], r['qty_solicitada'], r['status'],
                            0, '', '', '', 0, 0, '(no transfer)', 0])
                continue
            for i, t in enumerate(transfs, 1):
                resultado_t = t.get('resultado', {}) or {}
                w.writerow([
                    r['cod'], r['qty_solicitada'], r['status'], i,
                    t.get('lot_id_origem'), t.get('lote_origem_nome'),
                    t.get('location_id_origem'),
                    t.get('qty_pretendida'), t.get('qty_movida'),
                    t.get('status'),
                    resultado_t.get('tempo_ms', 0),
                ])


def _escrever_csv_pendencias(
    path: str, resultados: List[Dict[str, Any]],
) -> None:
    """1 linha por cod que NAO atingiu 100% (parcial/falha)."""
    p = Path(path)
    with p.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow([
            'cod', 'qty_solicitada', 'qty_movida', 'qty_nao_movida',
            'status', 'erro', 'produto_id', 'produto_nome',
            'quants_disponiveis', 'transferencias_executadas',
            'linha_planilha',
        ])
        for r in resultados:
            if r['status'] in _STATUS_OK_TOTAL:
                continue
            w.writerow([
                r['cod'], r['qty_solicitada'], r.get('qty_movida', 0),
                r.get('qty_nao_movida', r['qty_solicitada']),
                r['status'], r.get('erro') or '',
                r.get('produto_id', ''), r.get('produto_nome', ''),
                r.get('quants_disponiveis', 0),
                len(r.get('transferencias') or []),
                r.get('linha_planilha', ''),
            ])


def _sumarizar(resultados: List[Dict[str, Any]], dry_run: bool) -> Dict[str, Any]:
    """Sumario macro para JSON de saida."""
    by_status: Dict[str, int] = {}
    qty_solicitada_total = 0.0
    qty_movida_total = 0.0
    qty_nao_movida_total = 0.0
    transferencias_total = 0
    for r in resultados:
        st = r['status']
        by_status[st] = by_status.get(st, 0) + 1
        qty_solicitada_total += r.get('qty_solicitada', 0)
        qty_movida_total += r.get('qty_movida', 0)
        qty_nao_movida_total += r.get('qty_nao_movida', 0)
        transferencias_total += len(r.get('transferencias') or [])
    return {
        'modo': 'dry-run' if dry_run else 'confirmado',
        'cods_total': len(resultados),
        'cods_por_status': by_status,
        'qty_solicitada_total': round(qty_solicitada_total, CASAS_DECIMAIS),
        'qty_movida_total': round(qty_movida_total, CASAS_DECIMAIS),
        'qty_nao_movida_total': round(qty_nao_movida_total, CASAS_DECIMAIS),
        'transferencias_executadas': transferencias_total,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    grp_in = ap.add_mutually_exclusive_group(required=True)
    grp_in.add_argument(
        '--planilha', type=str,
        help='CSV/TSV com colunas (cod, qty[, nome]). Decimal PT-BR ou EN.',
    )
    grp_in.add_argument(
        '--cods', type=str,
        help="inline 'C1=Q1,C2=Q2,...' (debug; ate poucos cods)",
    )
    ap.add_argument('--empresa', required=True, choices=EMPRESAS,
                    help='FB|CD|LF (resolve company_id + locs default)')
    ap.add_argument('--politica', default=POLITICA_MIGRACAO_FIRST_FIFO,
                    choices=POLITICAS_VALIDAS,
                    help='ordem de drenagem dos quants origem')
    ap.add_argument('--locs-origem',
                    help='override CSV numerico (ex.: "8,4067,4068"). '
                         'Default = LOCS_ORIGEM_INTERNAS_POR_COMPANY[empresa].')
    ap.add_argument('--resetar-reserva-origem', action='store_true',
                    help='zera reserved_quantity ANTES do ajuste (defensivo)')
    ap.add_argument('--tolerancia-delta', type=float, default=0.001)
    ap.add_argument('--nome-lote-destino', default='MIGRAÇÃO',
                    help='lote consolidador no destino (default MIGRAÇÃO)')
    ap.add_argument('--confirmar', action='store_true',
                    help='EFETIVA no Odoo. Sem isso = dry-run (preview).')
    ap.add_argument('--csv-out', help='CSV detalhado (1 linha por transferencia)')
    ap.add_argument('--csv-pendencias',
                    help='CSV de cods com parcial/falha (proximas sessoes)')
    adicionar_args_padrao(ap)
    args = ap.parse_args()

    dry_run = not args.confirmar

    # 1. Carregar planilha ou inline
    try:
        if args.planilha:
            linhas = _carregar_planilha(args.planilha)
        else:
            linhas = _parsear_cods_inline(args.cods)
    except (FileNotFoundError, ValueError) as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        return 2

    if not linhas:
        print('ERRO: nenhuma linha valida na entrada', file=sys.stderr)
        return 2

    # 2. Override locs_origem se passado
    locs_origem: Optional[List[int]] = None
    if args.locs_origem:
        try:
            locs_origem = [int(x.strip()) for x in args.locs_origem.split(',')
                           if x.strip()]
        except ValueError as exc:
            print(f'ERRO: --locs-origem invalido: {exc}', file=sys.stderr)
            return 2

    # 3. Setup Flask + Odoo
    app = setup_cli_completo(__file__, args.quiet, args.forcar_concorrencia)
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        svc = StockInternalTransferService(odoo=odoo, lot_svc=lot_svc)

        # Premissa: empresa -> company_id
        try:
            prem = resolver_empresa(args.empresa)
        except ValueError as exc:
            print(f'ERRO: empresa invalida: {exc}', file=sys.stderr)
            return 2
        company_id = prem['company_id']

        # 4. Processar cada linha
        resultados: List[Dict[str, Any]] = []
        for ln in linhas:
            res = _processar_cod(
                svc=svc, odoo=odoo, linha=ln,
                company_id=company_id,
                locs_origem=locs_origem,
                politica=args.politica,
                resetar_reserva=args.resetar_reserva_origem,
                tolerancia_delta=args.tolerancia_delta,
                nome_lote_destino=args.nome_lote_destino,
                dry_run=dry_run,
            )
            resultados.append(res)

    # 5. CSVs opcionais (fora do app_context — escrita disco pura)
    if args.csv_out:
        _escrever_csv_out(args.csv_out, resultados)
    if args.csv_pendencias:
        _escrever_csv_pendencias(args.csv_pendencias, resultados)

    # 6. JSON de saida
    sumario = _sumarizar(resultados, dry_run)
    payload = {
        'sumario': sumario,
        'empresa': args.empresa,
        'company_id': company_id,
        'politica_ordem': args.politica,
        'locs_origem_override': locs_origem,
        'nome_lote_destino': args.nome_lote_destino,
        'resetar_reserva_origem': args.resetar_reserva_origem,
        'cods': resultados,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))

    # 7. Exit code
    n_falhas = sum(1 for r in resultados if r['status'] in _STATUS_FALHA)
    n_parciais = sum(1 for r in resultados if r['status'] in _STATUS_PARCIAL)
    n_total = len(resultados)
    n_ok_total = n_total - n_falhas - n_parciais
    if dry_run:
        if n_falhas:
            return 1
        if n_parciais:
            return 1  # dry-run parcial conta como falha (qty incompleta)
        return 4 if n_ok_total == n_total else 1
    # Real:
    if n_falhas:
        return 1
    if n_parciais:
        return 1  # confirmado mas parcial = falha (algo nao moveu); CSV pendencias documenta
    return 0


if __name__ == '__main__':
    sys.exit(main())
