"""Ajuste FB + Transf CD — transferencias Estoque <-> Indisponivel (D011, 2026-05-20).

Processa 2 planilhas com schema De-Local/De-Lote -> Para-Local/Para-Lote + qtd:

  AJUSTE FB.xlsx (2259 linhas, company 1):
    - FB/Estoque/<lote>     -> FB/Indisponivel/MIGRAÇÃO   (2146 — saida estoque)
    - FB/Indisponivel/MIGRAÇÃO -> FB/Estoque/<lote>       (113  — retorno estoque)

  TRANSF CD.xlsx (101 linhas, company 4):
    - CD/*  /<lote>         -> CD/Indisponivel/MIGRAÇÃO   (71 — wildcard: busca lote
                                                            em QUALQUER location interna
                                                            do CD exceto Indisponivel;
                                                            prateleiras R-XX nao usadas)
    - CD/Indisponivel/MIGRAÇÃO -> CD/Estoque/<lote>       (30 — retorno estoque)

Mecanismo: inventory adjustment em 2 passos (stock.quant.action_apply_inventory),
identico a mover_migracao_para_indisponivel.py + StockInternalTransferService.
Cada lado gera contraparte automatica no Estoque Virtual/Inventory adjustment;
o liquido e' apenas o deslocamento de saldo origem -> destino.

REGRAS DE RESOLUCAO:
  - Lote 'MIGRAÇÃO' (e variantes MIGRACAO/MIGRAÇAO): busca/cria lote do produto.
  - Lote vazio (NaN) com origem FB/Estoque: assume 'P-15/05' (regra confirmada —
    103/135 batem exato com saldo P-15/05).
  - Lote literal (inclui '-'): busca exato (StockLotService trata bug operador '=').
  - qty da planilha = quantidade a mover (sempre positiva).
  - CLAMP: se qty > saldo_livre por <= 0.001 (arredondamento), reduz ao saldo.
  - reserved_quantity > 0 que impede o saldo restante: PULA (nao cancela picking).

STATUS possiveis: EXECUTADO / DRY_RUN_OK / SEM_SALDO / RESERVADO /
  PRODUTO_NAO_ENCONTRADO / LOTE_ORIGEM_INEXISTENTE / PENDENTE_SEM_LOTE /
  QTD_MAIOR_QUE_PLANILHA(anomalia) / FALHA_ODOO.

Uso:
    python scripts/inventario_2026_05/ajuste_fb_cd_indisponivel.py                    # dry-run AMBOS
    python scripts/inventario_2026_05/ajuste_fb_cd_indisponivel.py --arquivo=CD       # so CD dry-run
    python scripts/inventario_2026_05/ajuste_fb_cd_indisponivel.py --arquivo=CD --confirmar
    python scripts/inventario_2026_05/ajuste_fb_cd_indisponivel.py --confirmar        # executa AMBOS
"""
import argparse
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

import pandas as pd  # noqa: E402

from app import create_app  # noqa: E402
from app.odoo.constants.locations import (  # noqa: E402
    get_local_indisponivel, get_location_id)
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('ajuste_fb_cd')

# ---- Constantes D011 (.claude/references/odoo/IDS_FIXOS.md) ----
LOC_FIXO = {
    'FB/Estoque': get_location_id(1),
    'FB/Indisponivel': get_local_indisponivel(1),
    'CD/Estoque': get_location_id(4),
    'CD/Indisponivel': get_local_indisponivel(4),
}
# Origens tratadas como WILDCARD: busca o lote em QUALQUER location interna da
# company (exceto Indisponivel). Motivo (confirmado pelo usuario 2026-05-20): o
# saldo do inventario fica espalhado nas "pastas" usadas (FB/Pré-Produção/Linha *,
# FB/Pós-Produção, CD/Estoque/*), nao na location raiz. Prateleiras nao sao usadas.
# Destino do RETORNO ('FB/Estoque'/'CD/Estoque' em Para-Local) usa loc fixo (LOC_FIXO).
LOC_WILDCARD = {'CD/*', 'FB/Estoque', 'CD/Estoque'}
COMPANY_INDISP = {c: get_local_indisponivel(c) for c in (1, 4)}
LOTE_MIGRACAO_VARIANTES = ['MIGRAÇÃO', 'MIGRACAO', 'MIGRAÇAO']
LOTE_MIGRACAO_CANONICO = 'MIGRAÇÃO'
LOTE_VAZIO_FB_ESTOQUE = 'P-15/05'
CASAS = 6
TOL = 0.001

ARQUIVOS = {
    'FB': {
        'path': '/mnt/c/Users/rafael.nascimento/Downloads/AJUSTE FB.xlsx',
        'col_cod': 'cod', 'col_qty': 'diff_qtd', 'company': 1,
    },
    'CD': {
        'path': '/mnt/c/Users/rafael.nascimento/Downloads/TRANSF CD.xlsx',
        'col_cod': 'CODIGO', 'col_qty': 'QTD', 'company': 4,
    },
}


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 92)
    print(f'  {t}')
    print(c * 92)


def cod_str(x) -> Optional[str]:
    if pd.isna(x):
        return None
    try:
        return str(int(float(x)))
    except (ValueError, TypeError):
        return str(x).strip()


def norm_txt(x) -> Optional[str]:
    if pd.isna(x):
        return None
    s = str(x).strip()
    return s if s and s.lower() != 'nan' else None


def is_migracao(lote: Optional[str]) -> bool:
    if not lote:
        return False
    return lote.strip().upper() in {v.upper() for v in LOTE_MIGRACAO_VARIANTES}


# ============================================================
# Carga das planilhas -> schema comum
# ============================================================
def carregar(filial: str) -> List[Dict]:
    cfg = ARQUIVOS[filial]
    df = pd.read_excel(cfg['path'])
    df.columns = [c.strip() for c in df.columns]
    out = []
    for idx, row in df.iterrows():
        out.append({
            'arquivo': filial,
            'idx': int(idx) + 1,
            'company': cfg['company'],
            'cod': cod_str(row[cfg['col_cod']]),
            'de_local': norm_txt(row['De - Local']),
            'de_lote': norm_txt(row['De- Lote']),
            'para_local': norm_txt(row['Para - Local']),
            'para_lote': norm_txt(row['Para - Lote']),
            'qty_planilha': round(float(row[cfg['col_qty']]), CASAS),
        })
    return out


# ============================================================
# Helpers Odoo
# ============================================================
def resolver_product_id(odoo, cod: str) -> Optional[int]:
    res = odoo.search_read('product.product', [['default_code', '=', cod]],
                           ['id', 'active'], limit=5)
    if not res:
        return None
    ativos = [r for r in res if r.get('active')]
    return (ativos[0] if ativos else res[0])['id']


def lotes_migracao_ids(odoo, pid: int, company: int) -> List[int]:
    """Todos os lotes MIGRAÇÃO (variantes com/sem acento) do produto.
    Produtos costumam ter 2: 'MIGRAÇÃO' e 'MIGRACAO' — o saldo fica em um deles."""
    return odoo.search('stock.lot', [
        ['name', 'in', LOTE_MIGRACAO_VARIANTES],
        ['product_id', '=', pid],
        ['company_id', '=', company],
    ])


def melhor_lote_migracao_na_loc(odoo, pid, company, loc):
    """Retorna (lot_id, todos_ids) do lote MIGRAÇÃO com MAIOR saldo na location `loc`.
    Se nenhuma variante tem saldo na loc, retorna o primeiro existente.
    Se nenhuma existe, (None, [])."""
    lids = lotes_migracao_ids(odoo, pid, company)
    if not lids:
        return None, []
    quants = odoo.search_read('stock.quant', [
        ['product_id', '=', pid], ['company_id', '=', company],
        ['location_id', '=', loc], ['lot_id', 'in', lids],
    ], ['lot_id', 'quantity'])
    com_saldo = sorted(
        [(q['lot_id'][0], float(q['quantity'])) for q in quants if abs(float(q['quantity'])) > 1e-9],
        key=lambda x: -x[1])
    if com_saldo:
        return com_saldo[0][0], lids
    return lids[0], lids


def resolver_lote_origem(odoo, lot_svc, lote_nome, pid, company, loc_origem):
    """(lot_id, nome, erro). MIGRAÇÃO -> lote com saldo na loc_origem; literal -> busca."""
    if is_migracao(lote_nome):
        lid, _ = melhor_lote_migracao_na_loc(odoo, pid, company, loc_origem)
        if lid:
            return lid, LOTE_MIGRACAO_CANONICO, None
        return None, LOTE_MIGRACAO_CANONICO, 'lote MIGRACAO inexistente'
    lid = lot_svc.buscar_por_nome(lote_nome, pid, company)
    if lid:
        return lid, lote_nome, None
    return None, lote_nome, f'lote {lote_nome!r} inexistente'


def resolver_lote_destino(odoo, lot_svc, lote_nome, pid, company, loc_destino):
    """(lot_id, nome, criado). MIGRAÇÃO -> consolida no lote com saldo na loc_destino
    (cria canonico se nenhum existe); literal -> criar_se_nao_existe."""
    if is_migracao(lote_nome):
        lid, lids = melhor_lote_migracao_na_loc(odoo, pid, company, loc_destino)
        if lid:
            return lid, LOTE_MIGRACAO_CANONICO, False
        novo = lot_svc.criar(LOTE_MIGRACAO_CANONICO, pid, company)
        return novo, LOTE_MIGRACAO_CANONICO, True
    lid, criado = lot_svc.criar_se_nao_existe(lote_nome, pid, company)
    return lid, lote_nome, criado


def buscar_quant(odoo, pid, company, loc, lot_id):
    qs = odoo.search_read('stock.quant', [
        ['product_id', '=', pid], ['company_id', '=', company],
        ['location_id', '=', loc], ['lot_id', '=', lot_id],
    ], ['id', 'quantity', 'reserved_quantity'], limit=1)
    return qs[0] if qs else None


def buscar_quants_wildcard(odoo, pid, company, lot_id, excluir_locs):
    """Quants do lote em locations internas (exceto excluir_locs) com qty>0.
    Ordenado por saldo livre DESC. CD/* = busca em todas as 'pastas' usadas
    (prateleiras nao usadas tem saldo zero, nao aparecem)."""
    qs = odoo.search_read('stock.quant', [
        ['product_id', '=', pid], ['company_id', '=', company],
        ['lot_id', '=', lot_id], ['quantity', '>', 0],
        ['location_id.usage', '=', 'internal'],
        ['location_id', 'not in', list(excluir_locs)],
    ], ['id', 'location_id', 'quantity', 'reserved_quantity'], limit=100)
    for q in qs:
        q['livre'] = float(q['quantity']) - float(q.get('reserved_quantity') or 0)
    qs.sort(key=lambda x: -x['livre'])
    return qs


def aplicar_ajuste(odoo, quant_id, nova_qty):
    odoo.write('stock.quant', [quant_id], {'inventory_quantity': nova_qty})
    odoo.execute_kw('stock.quant', 'action_apply_inventory', [[quant_id]])


def aumentar_destino(odoo, pid, company, loc_dest, lot_dest_id, qty):
    """Aumenta (ou cria) quant destino em qty. Retorna (quant_id, antes, apos)."""
    qd = buscar_quant(odoo, pid, company, loc_dest, lot_dest_id)
    if qd:
        antes = float(qd['quantity'])
        apos = antes + qty
        aplicar_ajuste(odoo, qd['id'], apos)
        return qd['id'], antes, apos
    novo = odoo.create('stock.quant', {
        'product_id': pid, 'company_id': company,
        'location_id': loc_dest, 'lot_id': lot_dest_id,
        'inventory_quantity': qty,
    })
    odoo.execute_kw('stock.quant', 'action_apply_inventory', [[novo]])
    return novo, 0.0, qty


# ============================================================
# Processamento de 1 linha
# ============================================================
def processar(odoo, lot_svc, item, dry_run) -> Dict:
    r = {**item, 'inicio': datetime.now().isoformat(timespec='seconds')}
    qty = item['qty_planilha']
    company = item['company']

    if qty <= 0:
        r['status'] = 'SKIP_QTD_ZERO'
        return r

    # 1. Produto
    pid = resolver_product_id(odoo, item['cod'])
    if not pid:
        r['status'] = 'PRODUTO_NAO_ENCONTRADO'
        r['erro'] = f'default_code {item["cod"]!r} nao existe no Odoo'
        return r
    r['product_id'] = pid

    # 2. Location destino (sempre fixa)
    loc_dest = LOC_FIXO.get(item['para_local'])
    if loc_dest is None:
        r['status'] = 'FALHA_PARA_LOCAL'
        r['erro'] = f'Para-Local {item["para_local"]!r} nao mapeado'
        return r
    r['loc_destino'] = loc_dest

    # 3. Location origem (fixa ou wildcard CD/*)
    wildcard = item['de_local'] in LOC_WILDCARD
    loc_org = None if wildcard else LOC_FIXO.get(item['de_local'])
    if not wildcard and loc_org is None:
        r['status'] = 'FALHA_DE_LOCAL'
        r['erro'] = f'De-Local {item["de_local"]!r} nao mapeado'
        return r

    # 4. Lote origem
    de_lote = item['de_lote']
    if de_lote is None:
        # De-Lote vazio em origem de estoque/wildcard (direcao SAIDA) -> assume P-15/05
        # (regra confirmada: saldo do inventario consolidado no lote P-15/05)
        if item['de_local'] in ('FB/Estoque', 'CD/Estoque') or wildcard:
            de_lote = LOTE_VAZIO_FB_ESTOQUE
            r['lote_origem_assumido'] = LOTE_VAZIO_FB_ESTOQUE
        else:
            r['status'] = 'PENDENTE_SEM_LOTE'
            r['erro'] = f'De-Lote vazio em {item["de_local"]} (regra indefinida)'
            return r
    # MIGRAÇÃO origem so vem de location fixa (Indisponivel); resolve o lote com saldo na loc
    lot_org_id, lote_org_nome, err = resolver_lote_origem(
        odoo, lot_svc, de_lote, pid, company, loc_org)
    if not lot_org_id:
        r['status'] = 'LOTE_ORIGEM_INEXISTENTE'
        r['erro'] = err
        r['lote_origem_buscado'] = de_lote
        return r
    r['lot_origem_id'] = lot_org_id
    r['lote_origem'] = lote_org_nome

    # 5. Buscar quants origem
    if wildcard:
        excluir = {COMPANY_INDISP[company]}
        quants_org = buscar_quants_wildcard(odoo, pid, company, lot_org_id, excluir)
    else:
        q = buscar_quant(odoo, pid, company, loc_org, lot_org_id)
        quants_org = []
        if q:
            q['location_id'] = [loc_org, item['de_local']]
            q['livre'] = float(q['quantity']) - float(q.get('reserved_quantity') or 0)
            quants_org = [q]

    livre_total = round(sum(q['livre'] for q in quants_org), CASAS)
    r['saldo_livre_origem'] = livre_total
    r['origem_locations'] = [
        {'loc': q['location_id'][0], 'name': q['location_id'][1] if q['location_id'] else '?',
         'qty': float(q['quantity']), 'reserv': float(q.get('reserved_quantity') or 0), 'livre': q['livre']}
        for q in quants_org
    ]

    if not quants_org or livre_total <= 0:
        r['status'] = 'SEM_SALDO'
        r['erro'] = f'qty={qty} mas saldo livre origem={livre_total}'
        return r

    # 5. Clamp / validacao de saldo
    qty_efetiva = qty
    if qty > livre_total:
        if qty - livre_total <= TOL:
            qty_efetiva = livre_total
            r['clamp_arredondamento'] = {'de': qty, 'para': qty_efetiva}
        else:
            # saldo insuficiente — transfere o que da, marca delta
            qty_efetiva = livre_total
            r['clamp_parcial'] = {
                'pedido': qty, 'disponivel': livre_total,
                'delta_nao_transferido': round(qty - livre_total, CASAS),
            }
    r['qty_efetiva'] = round(qty_efetiva, CASAS)

    # 6. DRY-RUN
    if dry_run:
        if is_migracao(item['para_lote']):
            lid, _ = melhor_lote_migracao_na_loc(odoo, pid, company, loc_dest)
        else:
            lid = lot_svc.buscar_por_nome(item['para_lote'], pid, company)
        r['lote_destino_acao'] = 'reused' if lid else 'will_create'
        r['status'] = 'DRY_RUN_OK'
        return r

    # 7. EXECUTAR
    t0 = time.time()
    try:
        # 7a. lote destino (consolida MIGRAÇÃO com saldo na loc / cria literal)
        lot_dest_id, _lote_dest_nome, criado = resolver_lote_destino(
            odoo, lot_svc, item['para_lote'], pid, company, loc_dest)
        r['lot_destino_id'] = lot_dest_id
        r['lote_destino_criado'] = criado

        # 7b. reduzir origem (1+ quants), respeitando reserva
        restante = qty_efetiva
        movido = 0.0
        reducoes = []
        for q in quants_org:
            if restante <= 0:
                break
            qtd_q = float(q['quantity'])
            reserv = float(q.get('reserved_quantity') or 0)
            livre_q = qtd_q - reserv
            consumir = min(restante, livre_q)
            if consumir <= 0:
                continue
            aplicar_ajuste(odoo, q['id'], qtd_q - consumir)
            reducoes.append({
                'quant_id': q['id'], 'loc': q['location_id'][0],
                'antes': qtd_q, 'apos': qtd_q - consumir, 'consumido': consumir,
            })
            movido += consumir
            restante -= consumir
        movido = round(movido, CASAS)
        r['reducoes_origem'] = reducoes
        r['qty_movida'] = movido
        if movido <= 0:
            r['status'] = 'RESERVADO'
            r['erro'] = 'todo saldo reservado em pickings ativos'
            return r

        # 7c. aumentar destino
        qd_id, antes, apos = aumentar_destino(odoo, pid, company, loc_dest, lot_dest_id, movido)
        r['quant_destino_id'] = qd_id
        r['destino_antes'] = antes
        r['destino_apos'] = apos
        r['status'] = 'EXECUTADO'
        r['tempo_ms'] = int((time.time() - t0) * 1000)
    except Exception as exc:
        r['status'] = 'FALHA_ODOO'
        r['erro'] = str(exc)
        r['tempo_ms'] = int((time.time() - t0) * 1000)
        logger.exception(f'idx={item["idx"]} cod={item["cod"]} falha')
    return r


def processar_resiliente(odoo, lot_svc, item, dry_run, max_retries=5):
    last = None
    for tent in range(1, max_retries + 1):
        try:
            return processar(odoo, lot_svc, item, dry_run)
        except Exception as exc:
            last = exc
            msg = str(exc).lower()
            transit = any(k in msg for k in
                          ['503', 'service unavailable', 'timeout', 'timed out',
                           'connection refused', 'connection reset']) or \
                'protocolerror' in str(type(exc)).lower()
            if not transit:
                return {**item, 'status': 'FALHA_ODOO', 'erro': f'(no retry) {exc}'}
            back = min(2 ** tent, 60)
            logger.warning(f'idx={item["idx"]} transitorio {tent}/{max_retries}: {exc} — {back}s')
            time.sleep(back)
    return {**item, 'status': 'FALHA_ODOO', 'erro': f'(esgotou retries) {last}'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true', help='executa real (default dry-run)')
    ap.add_argument('--arquivo', choices=['FB', 'CD', 'AMBOS'], default='AMBOS')
    ap.add_argument('--limite', type=int, default=0)
    ap.add_argument('--apenas-linhas', type=str, default='', help='idx 1-based csv (por arquivo)')
    ap.add_argument('--retomar-de', type=int, default=0,
                    help='Skip linhas com idx < N (retomada apos crash; usar 1 arquivo so)')
    ap.add_argument('--so-direcao', choices=['SAIDA', 'RETORNO'], default='',
                    help='SAIDA=->Indisponivel, RETORNO=->Estoque')
    ap.add_argument('--log-json', type=str, default='')
    args = ap.parse_args()
    dry_run = not args.confirmar

    filiais = ['FB', 'CD'] if args.arquivo == 'AMBOS' else [args.arquivo]
    registros: List[Dict] = []
    for f in filiais:
        registros.extend(carregar(f))

    if args.so_direcao == 'SAIDA':
        registros = [r for r in registros if r['para_local'] in ('FB/Indisponivel', 'CD/Indisponivel')]
    elif args.so_direcao == 'RETORNO':
        registros = [r for r in registros if r['para_local'] in ('FB/Estoque', 'CD/Estoque')]

    if args.apenas_linhas:
        apenas = {int(s) for s in args.apenas_linhas.split(',') if s.strip()}
        registros = [r for r in registros if r['idx'] in apenas]
    if args.retomar_de > 0:
        registros = [r for r in registros if r['idx'] >= args.retomar_de]
    if args.limite > 0:
        registros = registros[:args.limite]

    # log_path definido cedo p/ checkpoint incremental (resiliencia em runs longos)
    log_path = args.log_json
    if not log_path:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        modo = 'dryrun' if dry_run else 'real'
        log_path = str(_THIS.parent / 'auditoria' / f'log_ajuste_fb_cd_{"-".join(filiais)}_{modo}_{ts}.json')
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    def salvar_log(parcial=False):
        cont_ = Counter(r['status'] for r in resultados)
        soma_ = sum(r.get('qty_movida', r.get('qty_efetiva', 0)) for r in resultados
                    if r['status'] in ('EXECUTADO', 'DRY_RUN_OK'))
        with open(log_path, 'w', encoding='utf-8') as fh:
            json.dump({'args': vars(args), 'dry_run': dry_run, 'parcial': parcial,
                       'total': len(resultados), 'contagem': dict(cont_),
                       'soma_movida': soma_, 'resultados': resultados}, fh, indent=2, default=str)

    banner(f'AJUSTE FB + TRANSF CD — {"DRY-RUN" if dry_run else "EXECUCAO REAL"} '
           f'({len(registros)} linhas, arquivos={filiais})')

    app = create_app()
    resultados = []
    t0 = time.time()
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        for i, item in enumerate(registros, 1):
            r = processar_resiliente(odoo, lot_svc, item, dry_run)
            resultados.append(r)
            st = r['status']
            if st in ('EXECUTADO', 'DRY_RUN_OK'):
                if i % 50 == 0 or st == 'EXECUTADO':
                    logger.info(f'[{i}/{len(registros)}] {st} {item["arquivo"]}#{item["idx"]} '
                                f'cod={item["cod"]} {item["de_local"]}/{r.get("lote_origem")} '
                                f'-> {item["para_local"]}/{item["para_lote"]} '
                                f'qty={r.get("qty_efetiva")}')
            elif not st.startswith('SKIP'):
                logger.warning(f'[{i}/{len(registros)}] {st} {item["arquivo"]}#{item["idx"]} '
                               f'cod={item["cod"]}: {r.get("erro")}')
            if i % 100 == 0 and not dry_run:
                salvar_log(parcial=True)
                logger.info(f'  >>> checkpoint salvo ({i}/{len(registros)})')

    banner('RESUMO')
    cont = Counter(r['status'] for r in resultados)
    for st, n in cont.most_common():
        print(f'  {st:28s} {n:5d}  ({n/len(resultados)*100:5.1f}%)')
    print(f'  {"TOTAL":28s} {len(resultados):5d}')

    # Resumo por arquivo + direcao
    print('\n  Por arquivo/direcao:')
    for f in filiais:
        for dir_nome, dests in [('SAIDA->Indisp', ('FB/Indisponivel', 'CD/Indisponivel')),
                                ('RETORNO->Estoque', ('FB/Estoque', 'CD/Estoque'))]:
            sub = [r for r in resultados if r['arquivo'] == f and r['para_local'] in dests]
            if not sub:
                continue
            ok = sum(1 for r in sub if r['status'] in ('EXECUTADO', 'DRY_RUN_OK'))
            soma = sum(r.get('qty_efetiva', 0) for r in sub if r['status'] in ('EXECUTADO', 'DRY_RUN_OK'))
            print(f'    {f} {dir_nome:18s}: {ok}/{len(sub)} OK | soma {soma:,.4f} un')

    soma_total = sum(r.get('qty_movida', r.get('qty_efetiva', 0)) for r in resultados
                     if r['status'] in ('EXECUTADO', 'DRY_RUN_OK'))
    print(f'\n  Soma movida {"(DRY)" if dry_run else "EXECUTADA"}: {soma_total:,.4f} un')
    print(f'  Tempo: {time.time()-t0:.1f}s')

    salvar_log(parcial=False)
    print(f'\n  Log JSON: {log_path}')
    if dry_run:
        print('\n  DRY-RUN — nada gravado. Use --confirmar para executar.')

    falhas = sum(1 for r in resultados if r['status'].startswith('FALHA'))
    return 0 if falhas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
