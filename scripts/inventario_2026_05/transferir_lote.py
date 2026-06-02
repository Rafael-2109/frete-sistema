# etapa: orquestrador
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""transferir_lote.py — Transferencia (realocacao) de lote no MESMO local.

Planilha: filial | cod | nome_produto | lote | diff_qtd
    diff_qtd > 0  AUMENTA o lote ;  diff_qtd < 0  REDUZ o lote.
    Net-zero por (filial, produto): tira de uns lotes e poe em outros, no
    MESMO produto, MESMA empresa, MESMO local. Saldo TOTAL preservado.
    As alteracoes "casam" por (produto, local, qtd) — e uma transferencia
    de saldo entre lotes, NAO entrada/saida de estoque.

Diferencas vs `ajuste_estoque_lf_pasta17.py` (por isso e um orquestrador novo):
  - Lote LITERAL: `P-15/05` e tratado como nome de lote NORMAL (NAO "sem
    lote"). Nesta planilha `P-15/05` tem saldo REAL no local principal.
  - Multi-empresa: resolve company/local por linha via coluna `filial`
    (LF -> company 5 / loc 42 ; FB -> company 1 / loc 8 ; CD -> 4 / 32).
  - Mesmo local ESTRITO: reduz e aumenta SO no local principal da empresa.
    Nao consome de Pre-Producao nem de locais virtuais (38/39), salvo
    --incluir-preprod (LF: usa loc 53 como fonte secundaria de reducao).
  - Robusto a lotes DUPLICADOS (mesmo nome, varios stock.lot.id, ver
    [[stock_lot_search_bug]]): resolve TODOS os ids e consome/soma os quants
    correspondentes (operador 'in', nunca '=').

Seguranca (ATOMICO por produto): se QUALQUER reducao de um produto nao tem
    saldo suficiente no(s) local(is) de fonte, o produto INTEIRO e pulado —
    nao aplica os aumentos -> NAO infla estoque. Net-zero re-validado por
    produto (alerta se a planilha nao fechar em 0).

Mecanismo: inventory adjustment via primitiva
    `StockQuantAdjustmentService.ajustar_quant` (1 quant por chamada).
    Reducao usa `delta` negativo (relativo ao saldo real no momento da
    aplicacao -> robusto a alteracoes entre o plano e a execucao).

Uso:
    python scripts/inventario_2026_05/transferir_lote.py            # dry-run
    python scripts/inventario_2026_05/transferir_lote.py --confirmar  # real
    (opcional)
      --xlsx PATH
      --apenas-cods 104000014,104000015
      --incluir-preprod          (LF: tambem reduz de loc 53 apos esgotar 42)
      --log-json PATH
"""
import argparse
import json
import logging
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

import pandas as pd  # noqa: E402

from app import create_app  # noqa: E402
from app.odoo.constants.locations import COMPANY_LOCATIONS  # noqa: E402
from app.odoo.constants.operacoes_fiscais import CODIGO_PARA_COMPANY_ID  # noqa: E402
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.services.stock_quant_adjustment_service import (  # noqa: E402
    StockQuantAdjustmentService,
)
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('transferir_lote')

CASAS = 6
TOL = 0.001
# Locais de Pre-Producao por company (fonte secundaria opcional de reducao).
LOC_PREPROD = {5: 53}  # LF/Pre-Producao
DEFAULT_XLSX = '/mnt/c/Users/rafael.nascimento/Downloads/TRANSF-LOTE.xlsx'


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 80)
    print(f'  {t}')
    print(c * 80)


def _norm_cod(raw) -> str:
    s = str(raw).strip()
    return s[:-2] if s.endswith('.0') else s


def _norm_lote(raw) -> Optional[str]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s or s.lower() in ('nan', 'none'):
        return None
    return s[:-2] if s.endswith('.0') else s


# ============================================================
# Carga da planilha
# ============================================================

def carregar_planilha(path: str, col_qtd: str) -> List[Dict]:
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    col_qtd = col_qtd.strip().lower()
    need = {'filial', 'cod', 'lote', col_qtd}
    if not need.issubset(df.columns):
        raise ValueError(
            f'Planilha sem colunas {need}; presentes: {list(df.columns)}'
        )
    regs = []
    for idx, row in df.iterrows():
        diff_raw = row[col_qtd]
        if pd.isna(diff_raw) or str(diff_raw).strip() == '':
            diff = None
        else:
            try:
                diff = round(float(str(diff_raw).strip()), CASAS)
            except (TypeError, ValueError):
                diff = None
        regs.append({
            'idx': int(idx) + 1,
            'filial': str(row['filial']).strip(),
            'cod': _norm_cod(row['cod']),
            'nome_produto': str(row.get('nome_produto', '')).strip(),
            'lote': _norm_lote(row['lote']),
            'diff': diff,
            'diff_raw': str(diff_raw),
        })
    return regs


# ============================================================
# Resolucao batch (produto / lote / quant) — P4 batch fan-out
# ============================================================

def resolver_pids(odoo, cods: List[str]) -> Dict[str, Dict]:
    res = odoo.search_read(
        'product.product', [['default_code', 'in', cods]],
        ['id', 'default_code', 'active', 'tracking', 'name'], limit=0)
    out: Dict[str, Dict] = {}
    for p in res:
        c = p['default_code']
        if c not in out or p['active']:
            out[c] = {'pid': p['id'], 'tracking': p.get('tracking') or 'none',
                      'active': bool(p['active']), 'name': p.get('name')}
    return out


def resolver_lotids(odoo, pids: List[int], nomes: List[str]) -> Dict[Tuple[int, str], List[Dict]]:
    """(pid, nome) -> [{'id', 'company_id'}]. Operador 'in' (nunca '=').

    GUARDA company_id: o MESMO nome de lote pode existir em varias empresas
    (produto compartilhado). Filtrar pela empresa-alvo e obrigatorio — senao
    criar quant com lot de outra empresa => Odoo rejeita ('Empresas
    incompativeis'). Bug corrigido apos execucao 2026-05-20.
    """
    if not nomes:
        return {}
    lots = odoo.search_read(
        'stock.lot', [['product_id', 'in', pids], ['name', 'in', nomes]],
        ['id', 'name', 'product_id', 'company_id'], limit=0)
    out: Dict[Tuple[int, str], List[Dict]] = defaultdict(list)
    for lt in lots:
        cid = lt['company_id'][0] if lt['company_id'] else None
        out[(lt['product_id'][0], (lt['name'] or '').strip())].append(
            {'id': lt['id'], 'company_id': cid})
    return out


def carregar_quants(odoo, pids: List[int], locs: List[int]) -> List[Dict]:
    return odoo.search_read(
        'stock.quant',
        [['product_id', 'in', pids], ['location_id', 'in', locs]],
        ['id', 'product_id', 'location_id', 'lot_id', 'quantity',
         'reserved_quantity'], limit=0)


# ============================================================
# Planejamento de reducao (multi-quant, multi-local fonte)
# ============================================================

def planejar_reducao(
    quants_lote: List[Dict], qtd: float, locs_fonte: List[int],
) -> Dict:
    """Planeja consumir `qtd` (positivo) dos quants do lote, respeitando a
    ordem de `locs_fonte` (principal primeiro) e usando somente o LIVRE
    (quantity - reserved). NAO grava — so calcula os passos.
    """
    def ordem(q):
        loc = q['location_id'][0]
        livre = float(q['quantity']) - float(q.get('reserved_quantity') or 0)
        rank = locs_fonte.index(loc) if loc in locs_fonte else 99
        return (rank, -livre)

    restante = qtd
    passos = []
    for q in sorted(quants_lote, key=ordem):
        if restante <= TOL:
            break
        if q['location_id'][0] not in locs_fonte:
            continue
        livre = round(float(q['quantity']) - float(q.get('reserved_quantity') or 0), CASAS)
        if livre <= TOL:
            continue
        consumir = round(min(livre, restante), CASAS)
        passos.append({
            'quant_id': q['id'],
            'loc': q['location_id'][0],
            'lot_id': q['lot_id'][0] if q['lot_id'] else None,
            'qty_atual': round(float(q['quantity']), CASAS),
            'consumir': consumir,
        })
        restante = round(restante - consumir, CASAS)
    return {'passos': passos, 'restante': round(restante, CASAS),
            'cobriu': restante <= TOL}


# ============================================================
# Processamento atomico por (filial, produto)
# ============================================================

def processar_produto(
    *, svc, lot_svc, filial: str, cod: str, info: Dict,
    grupos: Dict[str, float], company_id: int, loc_principal: int,
    locs_fonte: List[int], quants_idx: Dict, lotids: Dict, dry: bool,
) -> List[Dict]:
    """ATOMICO: planeja TODAS as reducoes; se alguma nao cobre, aborta o
    produto inteiro (nada gravado -> nao infla). Depois aplica reducoes e
    aumentos via primitiva."""
    pid = info['pid']
    base = {'filial': filial, 'cod': cod, 'pid': pid,
            'produto': info.get('name')}

    # lot_ids do nome que pertencem A EMPRESA ALVO (filtra company — o mesmo
    # nome pode existir em outra empresa para produto compartilhado).
    def lotids_empresa(nome: Optional[str]) -> List[int]:
        if not nome:
            return []
        return [l['id'] for l in lotids.get((pid, nome), [])
                if l['company_id'] == company_id]

    # Quants do produto agrupados por nome de lote (resolve duplicados).
    def quants_do_lote(nome: Optional[str]) -> List[Dict]:
        ids = set(lotids_empresa(nome))
        if not ids:
            return []
        return [q for q in quants_idx.get(pid, []) if (q['lot_id'] and q['lot_id'][0] in ids)]

    reducoes = sorted([(n, d) for n, d in grupos.items() if d < -TOL], key=lambda kv: kv[1])
    aumentos = sorted([(n, d) for n, d in grupos.items() if d > TOL], key=lambda kv: -kv[1])

    # ---- FASE A: planejar reducoes (sem gravar) ----
    planos: List[Tuple[str, float, Dict]] = []
    for nome, delta in reducoes:
        quants_lote = quants_do_lote(nome)
        plano = planejar_reducao(quants_lote, abs(delta), locs_fonte)
        if not plano['cobriu']:
            disp = round(abs(delta) - plano['restante'], CASAS)
            return [{**base, 'op': 'PRODUTO', 'lote': nome, 'delta': delta,
                     'status': 'BLOQUEADO_REDUCAO_NAO_COBRE',
                     'erro': (f'reducao do lote {nome!r} precisa {abs(delta)} '
                              f'mas so ha {disp} livre em locs {locs_fonte} '
                              f'-> produto ABORTADO (nada gravado)')}]
        planos.append((nome, delta, plano))

    # ---- FASE B: aplicar reducoes (delta negativo, robusto) ----
    out: List[Dict] = []
    for nome, delta, plano in planos:
        for p in plano['passos']:
            res = svc.ajustar_quant(
                quant_id=p['quant_id'], delta=-p['consumir'],
                validar_nao_negativar=True, validar_nao_abaixo_reserva=True,
                casas_decimais=CASAS, dry_run=dry)
            out.append({**base, 'op': 'REDUCAO', 'lote': nome, 'delta': delta,
                        'loc': p['loc'], 'quant_id': p['quant_id'],
                        'consumir': p['consumir'],
                        'qty_antes': res.get('qty_antes'),
                        'qty_apos': res.get('qty_apos'),
                        'status': res.get('status'), 'erro': res.get('erro')})

    # ---- FASE C: aplicar aumentos (delta positivo no loc principal) ----
    for nome, delta in aumentos:
        # lot_id destino: preferir lot_id que JA tem quant no loc principal
        # (evita criar quant/lote redundante quando o lote ja existe la).
        # SO lotes da empresa-alvo (evita 'Empresas incompativeis' no Odoo).
        ids_nome = set(lotids_empresa(nome))
        lot_id = None
        melhor_qty = None
        for q in quants_idx.get(pid, []):
            if (q['location_id'][0] == loc_principal and q['lot_id']
                    and q['lot_id'][0] in ids_nome):
                qy = float(q['quantity'])
                if melhor_qty is None or qy > melhor_qty:
                    melhor_qty, lot_id = qy, q['lot_id'][0]
        lote_acao = 'reused_quant'
        if lot_id is None:
            # nenhum quant no loc principal: resolver/criar o lote
            existing = list(ids_nome)
            if existing:
                lot_id = existing[0]
                lote_acao = 'reused_lot'
            elif dry:
                lote_acao = 'will_create_lot'
            else:
                lot_id, criado = lot_svc.criar_se_nao_existe(
                    nome, pid, company_id, expiration_date=None)
                lote_acao = 'created_lot' if criado else 'reused_lot'

        if lot_id is None and dry:
            out.append({**base, 'op': 'AUMENTO', 'lote': nome, 'delta': delta,
                        'loc': loc_principal, 'lote_acao': lote_acao,
                        'qty_antes': 0.0, 'qty_apos': delta,
                        'status': 'DRY_RUN_OK'})
            continue

        res = svc.ajustar_quant(
            product_id=pid, company_id=company_id, location_id=loc_principal,
            lot_id=lot_id, delta=delta, criar_se_faltar=True,
            validar_nao_negativar=True, validar_nao_abaixo_reserva=True,
            casas_decimais=CASAS, dry_run=dry)
        out.append({**base, 'op': 'AUMENTO', 'lote': nome, 'delta': delta,
                    'loc': loc_principal, 'lote_acao': lote_acao,
                    'lot_id': lot_id, 'quant_id': res.get('quant_id'),
                    'qty_antes': res.get('qty_antes'),
                    'qty_apos': res.get('qty_apos'),
                    'status': res.get('status'), 'erro': res.get('erro')})
    return out


# ============================================================
# main
# ============================================================

def main():
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    ap.add_argument('--xlsx', default=DEFAULT_XLSX)
    ap.add_argument('--col-qtd', default='diff_qtd')
    ap.add_argument('--confirmar', action='store_true', default=False)
    ap.add_argument('--apenas-cods', default='')
    ap.add_argument('--incluir-preprod', action='store_true', default=False,
                    help='LF: reduz tambem de loc 53 (Pre-Producao) apos '
                         'esgotar o local principal')
    ap.add_argument('--log-json', default='')
    args = ap.parse_args()
    dry = not args.confirmar

    if not Path(args.xlsx).exists():
        logger.error(f'XLSX nao encontrado: {args.xlsx}')
        return 2

    regs = carregar_planilha(args.xlsx, args.col_qtd)
    if args.apenas_cods:
        alvo = {s.strip() for s in args.apenas_cods.split(',') if s.strip()}
        regs = [r for r in regs if r['cod'] in alvo]

    # Validar empresas conhecidas
    filiais = sorted({r['filial'] for r in regs})
    desconhecidas = [f for f in filiais if f not in CODIGO_PARA_COMPANY_ID]
    if desconhecidas:
        logger.error(f'Filiais desconhecidas (sem company_id): {desconhecidas}. '
                     f'Conhecidas: {sorted(CODIGO_PARA_COMPANY_ID)}')
        return 2

    # Agregar por (filial, cod) -> {lote_nome: soma_diff}; guarda metadados
    grupos: Dict[Tuple[str, str], Dict] = defaultdict(
        lambda: {'lotes': defaultdict(float), 'nome_produto': '', 'linhas_invalidas': []})
    for r in regs:
        g = grupos[(r['filial'], r['cod'])]
        g['nome_produto'] = r['nome_produto']
        if r['diff'] is None:
            g['linhas_invalidas'].append(r)
            continue
        # lote None (celula vazia) NAO esperado nesta planilha; registrar
        if not r['lote']:
            g['linhas_invalidas'].append(r)
            continue
        g['lotes'][r['lote']] = round(g['lotes'][r['lote']] + r['diff'], CASAS)

    cods = sorted({c for (_, c) in grupos})
    nomes = sorted({n for g in grupos.values() for n in g['lotes']})

    banner(f'TRANSFERIR LOTE (realocacao net-zero, mesmo local) — '
           f'{"DRY-RUN" if dry else "EXEC REAL"}')
    print(f'  XLSX            : {args.xlsx}')
    print(f'  Coluna qtd      : {args.col_qtd}')
    print(f'  Linhas          : {len(regs)}')
    print(f'  Grupos (fil,cod): {len(grupos)}  | filiais: {filiais}')
    print(f'  Incluir preprod : {args.incluir_preprod}')
    soma_total = sum(r['diff'] for r in regs if r['diff'] is not None)
    print(f'  Soma {args.col_qtd}: {soma_total:,.6f} (esperado ~0)')

    app = create_app()
    resultados: List[Dict] = []
    bloqueados: List[Dict] = []
    nao_netzero: List[Dict] = []
    t0 = time.time()
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        svc = StockQuantAdjustmentService(odoo=odoo, lot_svc=lot_svc)

        prodinfo = resolver_pids(odoo, cods)
        pids = [v['pid'] for v in prodinfo.values()]
        lotids = resolver_lotids(odoo, pids, nomes)

        # locais a observar: principais de todas as filiais + preprod (se LF)
        locs_obs = set()
        for f in filiais:
            cid = CODIGO_PARA_COMPANY_ID[f]
            locs_obs.add(COMPANY_LOCATIONS[cid])
            if args.incluir_preprod and cid in LOC_PREPROD:
                locs_obs.add(LOC_PREPROD[cid])
        quants = carregar_quants(odoo, pids, sorted(locs_obs))
        quants_idx: Dict[int, List[Dict]] = defaultdict(list)
        for q in quants:
            quants_idx[q['product_id'][0]].append(q)

        for (filial, cod) in sorted(grupos):
            g = grupos[(filial, cod)]
            info = prodinfo.get(cod)
            if not info:
                bloqueados.append({'filial': filial, 'cod': cod,
                                   'motivo': 'produto_inexistente'})
                continue
            if info['tracking'] != 'lot':
                bloqueados.append({'filial': filial, 'cod': cod,
                                   'motivo': f'tracking={info["tracking"]} (esperado lot)'})
                continue

            # net-zero check por produto
            soma_g = round(sum(g['lotes'].values()), CASAS)
            if abs(soma_g) > TOL:
                nao_netzero.append({'filial': filial, 'cod': cod, 'soma': soma_g})
                bloqueados.append({'filial': filial, 'cod': cod,
                                   'motivo': f'nao_net_zero (soma={soma_g})'})
                continue

            company_id = CODIGO_PARA_COMPANY_ID[filial]
            loc_principal = COMPANY_LOCATIONS[company_id]
            locs_fonte = [loc_principal]
            if args.incluir_preprod and company_id in LOC_PREPROD:
                locs_fonte.append(LOC_PREPROD[company_id])

            res = processar_produto(
                svc=svc, lot_svc=lot_svc, filial=filial, cod=cod,
                info=info, grupos=g['lotes'], company_id=company_id,
                loc_principal=loc_principal, locs_fonte=locs_fonte,
                quants_idx=quants_idx, lotids=lotids, dry=dry)

            if len(res) == 1 and res[0].get('op') == 'PRODUTO':
                bloqueados.append({'filial': filial, 'cod': cod,
                                   'motivo': res[0]['status'],
                                   'detalhe': res[0]['erro']})
            else:
                resultados.extend(res)
                for r in res:
                    if r['status'] in ('EXECUTADO', 'DRY_RUN_OK', 'NOOP'):
                        logger.info(
                            f"  {r['op']:8} [{filial}] cod={cod} "
                            f"lote={str(r['lote'])[:22]:>22} delta={r['delta']:+.4f} "
                            f"loc={r.get('loc')} qty {r.get('qty_antes')}->{r.get('qty_apos')}")
                    else:
                        logger.warning(
                            f"  {r['op']:8} [{filial}] cod={cod} lote={r['lote']} "
                            f"{r['status']}: {r.get('erro')}")

    # ---- RESUMO ----
    banner('RESUMO')
    cont = Counter((r['op'], r['status']) for r in resultados)
    for (op, st), n in cont.most_common():
        print(f'  {op:8} {st:30s} {n:4d}')
    produtos_ok = sorted({(r['filial'], r['cod']) for r in resultados})
    soma_red = sum(r['consumir'] for r in resultados
                   if r['op'] == 'REDUCAO' and r['status'] in ('EXECUTADO', 'DRY_RUN_OK'))
    soma_aum = sum(r['delta'] for r in resultados
                   if r['op'] == 'AUMENTO' and r['status'] in ('EXECUTADO', 'DRY_RUN_OK'))
    print(f'\n  Produtos aplicaveis : {len(produtos_ok)}')
    print(f'  Produtos bloqueados : {len(bloqueados)}')
    print(f'  Reducao total       : {soma_red:,.4f}')
    print(f'  Aumento total       : {soma_aum:,.4f}')
    print(f'  Net (aum - red)     : {soma_aum - soma_red:,.6f} (esperado ~0)')
    print(f'  Tempo               : {time.time() - t0:.1f}s')

    if bloqueados:
        banner('PRODUTOS BLOQUEADOS (nao aplicados)', c='-')
        for b in bloqueados:
            print(f"  [{b['filial']}] cod={b['cod']:>9} {b['motivo']}")
            if b.get('detalhe'):
                print(f"        {b['detalhe']}")

    falhas = [r for r in resultados if r['status'].startswith('FALHA')]
    if falhas:
        banner('FALHAS NA APLICACAO', c='!')
        for r in falhas:
            print(f"  {r['op']} [{r['filial']}] cod={r['cod']} lote={r['lote']}: {r.get('erro')}")

    # ---- LOG JSON ----
    log_path = args.log_json or str(
        _THIS.parent / 'auditoria' /
        f'log_transferir_lote_{"real" if not dry else "dryrun"}_'
        f'{datetime.now():%Y%m%d_%H%M%S}.json')
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            'args': vars(args), 'dry_run': dry,
            'linhas': len(regs), 'grupos': len(grupos),
            'soma_planilha': soma_total,
            'aplicaveis': len(produtos_ok), 'bloqueados': bloqueados,
            'nao_netzero': nao_netzero, 'resultados': resultados,
        }, f, indent=2, default=str, ensure_ascii=False)
    print(f'\n  Log JSON: {log_path}')
    if dry:
        print('\n  DRY-RUN — nada gravado. Revise e use --confirmar para aplicar.')

    return 0 if not falhas and not nao_netzero else 1


if __name__ == '__main__':
    sys.exit(main())
