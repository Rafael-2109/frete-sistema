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
    'BLOQUEADO_SERIAL',  # F2 v12-CR: produto tracking=serial, nao se moveu nada
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


def _escrever_csv_cleanup(path: str, cleanup_result: Dict[str, Any]) -> None:
    """S2 v12: CSV do cleanup (1 linha por quant tocado — reserved OU qty)."""
    p = Path(path)
    with p.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow([
            'quant_id', 'product_id', 'location_id', 'lot_id',
            'tipo', 'qty_antes', 'reserved_antes',
            'qty_depois', 'reserved_depois', 'status',
        ])
        # Reserveds zerados
        for q in cleanup_result.get('quants_reserved_negativo', []):
            res = cleanup_result.get('resultado_zerar_residual') or {}
            depois = (res.get('valores_depois') or {}).get(q['quant_id']) or {}
            w.writerow([
                q['quant_id'], q.get('product_id'), q.get('location_id'),
                q.get('lot_id'), 'RESERVED_NEG',
                q.get('quantity'), q.get('reserved_quantity'),
                depois.get('qty', q.get('quantity')),
                depois.get('reserved', 0 if res else q.get('reserved_quantity')),
                res.get('status', 'NAO_EXECUTADO'),
            ])
        # Qty negativos ajustados
        for aj in cleanup_result.get('resultados_ajustar_negativo', []):
            res_aj = aj.get('resultado') or {}
            w.writerow([
                aj['quant_id'], '', '', '',
                'QTY_NEG',
                aj.get('qty_antes'), '',
                res_aj.get('qty_apos', 0),
                '',
                res_aj.get('status', 'NAO_EXECUTADO'),
            ])


def _executar_cleanup_pos_bulk(
    odoo,
    product_ids: List[int],
    company_id: int,
    locs_origem: List[int],
    dry_run: bool,
) -> Dict[str, Any]:
    """S2 v12: cleanup automatico pos-bulk modo C.

    Lista quants em FB exceto Indisp dos product_ids processados e:
      1. Zera `reserved_quantity < 0` em quants `qty=0` (Skill 2.4 zerar_residual)
      2. Ajusta `quantity < 0` para 0 (Skill 1 ajustar_quant --valor-absoluto 0)

    Retorna dict estruturado com listas de quants encontrados e resultados das
    operacoes (zerar_residual + ajustes).

    NOTA: a chamada eh feita DENTRO do app_context do Flask, com o mesmo odoo
    do bulk. Reutiliza os services ja instanciados (StockReservaService +
    StockQuantAdjustmentService) ao inves de spawning subprocess.
    """
    from app.odoo.estoque.scripts.quant import StockQuantAdjustmentService
    from app.odoo.estoque.scripts.reserva import StockReservaService

    t0 = time.time()
    out: Dict[str, Any] = {
        'modo': 'dry-run' if dry_run else 'confirmado',
        'product_ids': product_ids,
        'company_id': company_id,
        'locs_origem': locs_origem,
        'quants_reserved_negativo': [],
        'quants_qty_negativo': [],
        'resultado_zerar_residual': None,
        'resultados_ajustar_negativo': [],
    }
    if not product_ids:
        out['status'] = 'CLEANUP_OK_VAZIO'
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # 1. Listar quants em FB exceto Indisp dos product_ids processados
    from app.odoo.constants.locations import LOCAIS_INDISPONIVEL
    loc_indisp = LOCAIS_INDISPONIVEL.get(company_id)
    excluir = [loc_indisp] if loc_indisp else []
    domain = [
        ['product_id', 'in', product_ids],
        ['company_id', '=', company_id],
        ['location_id', 'in', locs_origem],
    ]
    if excluir:
        domain.append(['location_id', 'not in', excluir])
    quants = odoo.search_read(
        'stock.quant', domain,
        ['id', 'product_id', 'lot_id', 'location_id',
         'quantity', 'reserved_quantity'],
    )

    # Classificar
    quants_reserved_neg = []
    quants_qty_neg = []
    TOL = 0.001
    for q in quants:
        qty = float(q.get('quantity') or 0)
        reserved = float(q.get('reserved_quantity') or 0)
        if qty < -TOL:
            quants_qty_neg.append(q)
        if reserved < -TOL:
            quants_reserved_neg.append(q)

    out['quants_reserved_negativo'] = [
        {'quant_id': q['id'],
         'product_id': q['product_id'][0] if q['product_id'] else None,
         'location_id': q['location_id'][0] if q['location_id'] else None,
         'lot_id': q['lot_id'][0] if q['lot_id'] else None,
         'quantity': float(q.get('quantity') or 0),
         'reserved_quantity': float(q.get('reserved_quantity') or 0)}
        for q in quants_reserved_neg
    ]
    out['quants_qty_negativo'] = [
        {'quant_id': q['id'],
         'product_id': q['product_id'][0] if q['product_id'] else None,
         'location_id': q['location_id'][0] if q['location_id'] else None,
         'lot_id': q['lot_id'][0] if q['lot_id'] else None,
         'quantity': float(q.get('quantity') or 0),
         'reserved_quantity': float(q.get('reserved_quantity') or 0)}
        for q in quants_qty_neg
    ]

    # 2. Zerar reserveds residuais — COM GUARD "MOs ativas"
    # (mitigacao S2-pre-mortem v12): se um quant com reserved<0 tem ML
    # ativa (state assigned/partially_available), pode ser reserva
    # LEGITIMA com sinal errado (raro mas possivel). Skill 9
    # `listar_move_lines_por_quant` faz cross-ref via tupla (G030).
    # Excluir esses quants do zerar_residual e reportar em
    # `quants_pulados_mo_ativa`.
    out['quants_pulados_mo_ativa'] = []
    qids_seguros: list = []  # F3 v12-CR: precisa visibilidade no escopo externo
    if quants_reserved_neg:
        from app.odoo.estoque.scripts.consulta_quant import (
            StockQuantQueryService,
        )
        query_svc = StockQuantQueryService(odoo=odoo)
        qids_candidatos = [q['id'] for q in quants_reserved_neg]
        # listar MLs vivas (assigned/partially_available default)
        ml_check = query_svc.listar_move_lines_por_quant(
            quant_ids=qids_candidatos,
        )
        mls_por_quant: Dict[int, list] = {}
        for ml in ml_check.get('move_lines', []):
            qid = ml.get('_quant_id_resolvido')
            if qid is None:
                continue
            mls_por_quant.setdefault(qid, []).append(ml)
        # Filtrar: zera SO os sem MLs ativas
        for q in quants_reserved_neg:
            mls = mls_por_quant.get(q['id'], [])
            if mls:
                out['quants_pulados_mo_ativa'].append({
                    'quant_id': q['id'],
                    'reserved_quantity': float(q.get('reserved_quantity') or 0),
                    'n_mls_ativas': len(mls),
                    'mls_sample_ids': [m['id'] for m in mls[:3]],
                    'motivo': (
                        f'quant tem {len(mls)} ML(s) viva(s) — reserved<0 '
                        f'pode ser legitimo. NAO zerar sem investigar via '
                        f'Skill 9 listar_pickings_por_quant.'
                    ),
                })
            else:
                qids_seguros.append(q['id'])
        if qids_seguros:
            reserva_svc = StockReservaService(odoo=odoo)
            res_zerar = reserva_svc.zerar_reserved_residual(
                quant_ids=qids_seguros, dry_run=dry_run,
            )
            out['resultado_zerar_residual'] = res_zerar
        else:
            out['resultado_zerar_residual'] = {
                'status': 'CLEANUP_OK_VAZIO',
                'acao': 'todos os quants com reserved<0 tem ML ativa — pulados',
            }

    # 3. Ajustar quants com qty<0 para 0 (apenas em modo real)
    if quants_qty_neg:
        quant_svc = StockQuantAdjustmentService(odoo=odoo)
        for q in quants_qty_neg:
            qty = float(q.get('quantity') or 0)
            res_aj = quant_svc.ajustar_quant(
                quant_id=q['id'],
                valor_absoluto=0.0,
                dry_run=dry_run,
            )
            out['resultados_ajustar_negativo'].append({
                'quant_id': q['id'],
                'qty_antes': qty,
                'delta_aplicado': -qty,  # +|qty| para ir de qty<0 a 0
                'resultado': res_aj,
            })

    # F3 v12-CR: contar SO os quants efetivamente zerados (excluindo os pulados
    # pelo GUARD de MO ativa). Antes contava len(quants_reserved_neg) o que
    # inflava o numero quando havia MLs vivas em algum quant.
    out['n_reserveds_zerados'] = len(qids_seguros)
    out['n_reserveds_pulados_mo_ativa'] = len(out['quants_pulados_mo_ativa'])
    out['n_qty_ajustados'] = len(quants_qty_neg)
    out['status'] = 'CLEANUP_OK' if (quants_reserved_neg or quants_qty_neg) else 'CLEANUP_OK_VAZIO'
    out['tempo_ms'] = int((time.time() - t0) * 1000)
    return out


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
    ap.add_argument('--cleanup-pos-bulk', action='store_true',
                    help='(S2 v12) Apos bulk, listar reserveds negativos e qty<0 nos cods '
                         'processados em FB exc Indisp; aplicar Skill 2.4 zerar_residual + '
                         'Skill 1 ajustar_quant valor_absoluto=0. Eh defensivo (NAO altera '
                         'saldo "vivo", so limpa fantasmas e zera negativos). Resultados '
                         'em payload.cleanup_pos_bulk e CSV separado (se --csv-cleanup). '
                         'Respeita --dry-run/--confirmar.')
    ap.add_argument('--csv-cleanup', help='CSV do cleanup (--cleanup-pos-bulk)')
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

        # 4.5 Cleanup pos-bulk (S2 v12) — dentro do app_context
        cleanup_result: Optional[Dict[str, Any]] = None
        if args.cleanup_pos_bulk:
            # Product_ids unicos dos cods que tiveram pelo menos 1 transferencia
            # (FALHA_PRODUTO/FALHA_SEM_QUANT nao geram cleanup util).
            product_ids = sorted({
                r['produto_id'] for r in resultados
                if r.get('produto_id') is not None
                and r.get('transferencias')  # so cods com transferencias executadas
            })
            # locs_origem efetivas (override OU default da company)
            from app.odoo.estoque.scripts.transfer import (
                LOCS_ORIGEM_INTERNAS_POR_COMPANY,
            )
            locs_eff = locs_origem or LOCS_ORIGEM_INTERNAS_POR_COMPANY.get(
                company_id, []
            )
            cleanup_result = _executar_cleanup_pos_bulk(
                odoo=odoo,
                product_ids=product_ids,
                company_id=company_id,
                locs_origem=locs_eff,
                dry_run=dry_run,
            )

    # 5. CSVs opcionais (fora do app_context — escrita disco pura)
    if args.csv_out:
        _escrever_csv_out(args.csv_out, resultados)
    if args.csv_pendencias:
        _escrever_csv_pendencias(args.csv_pendencias, resultados)
    if args.csv_cleanup and cleanup_result is not None:
        _escrever_csv_cleanup(args.csv_cleanup, cleanup_result)

    # F6 v12-CR: avisar quando --confirmar foi usado SEM --cleanup-pos-bulk.
    # A invariante do subagente diz "CLEANUP POS-BULK obrigatorio"; sem flag,
    # o operador (humano OU subagente) pode esquecer e deixar reserveds
    # fantasmas + saldos negativos no FB/Pre-Prod (licao v11). NUNCA aborta
    # o output JSON — so emite aviso em stderr.
    if not dry_run and not args.cleanup_pos_bulk:
        # So avisar se houve pelo menos 1 transferencia executada (caso
        # contrario nada para limpar).
        if any(r.get('transferencias') for r in resultados):
            print(
                '\nAVISO: --confirmar usado SEM --cleanup-pos-bulk. '
                'A invariante do subagente gestor-estoque-odoo diz cleanup '
                'obrigatorio. Verifique reserveds<0 e qty<0 nos cods '
                'processados via Skill 9 + Skill 2.4 zerar_residual + '
                'Skill 1 ajustar_quant. Para automatizar: adicionar '
                '--cleanup-pos-bulk na proxima execucao.\n',
                file=sys.stderr,
            )

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
    if cleanup_result is not None:
        payload['cleanup_pos_bulk'] = cleanup_result
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))

    # 7. Exit code
    n_falhas = sum(1 for r in resultados if r['status'] in _STATUS_FALHA)
    n_parciais = sum(1 for r in resultados if r['status'] in _STATUS_PARCIAL)
    n_total = len(resultados)
    n_ok_total = n_total - n_falhas - n_parciais

    # Cleanup pos-bulk (S2 v12) contribui para exit code se chamado
    # (mitigacao S2-pre-mortem): cleanup que falhou no Odoo (FALHA_ODOO)
    # NAO deve ser ignorado — eleva exit code para 1.
    cleanup_falhou = False
    if cleanup_result is not None:
        cleanup_status = cleanup_result.get('status', '')
        zr = cleanup_result.get('resultado_zerar_residual') or {}
        if cleanup_status not in ('CLEANUP_OK', 'CLEANUP_OK_VAZIO'):
            cleanup_falhou = True
        if zr.get('status', '').startswith('FALHA'):
            cleanup_falhou = True
        # Se algum ajuste de qty<0 falhou
        for aj in cleanup_result.get('resultados_ajustar_negativo', []):
            r_aj = aj.get('resultado') or {}
            if r_aj.get('status', '').startswith('FALHA'):
                cleanup_falhou = True
                break

    if dry_run:
        if n_falhas or cleanup_falhou:
            return 1
        if n_parciais:
            return 1  # dry-run parcial conta como falha (qty incompleta)
        return 4 if n_ok_total == n_total else 1
    # Real:
    if n_falhas or cleanup_falhou:
        return 1
    if n_parciais:
        return 1  # confirmado mas parcial = falha (algo nao moveu); CSV pendencias documenta
    return 0


if __name__ == '__main__':
    sys.exit(main())
