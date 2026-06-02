# etapa: orquestrador
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""ajuste_estoque_lf_pasta17.py — Realocacao de lote na LF (ajustes +/-).

Pedido do usuario 2026-05-20 (Pasta17.xlsx, aba "alteracao lote"):
    colunas: filial | cod | nome_produto | lote | QTD
    QTD > 0 AUMENTA ; QTD < 0 REDUZ. Planilha e net-zero por produto
    (realocacao de saldo entre lotes; consolidacao em P-15/05).

Regras de lote (definidas pelo usuario, validadas no Odoo):
- celula vazia/NaN OU 'P-15/05'  -> "SEM LOTE": o saldo esta materializado
  como lote P-15/05 em LF/Estoque (e/ou lot_id=False). Aumento -> P-15/05;
  reducao -> consome P-15/05 e lot_id=False.
- lote com VIRGULA  -> COMPOSTO (2 lotes na celula). Verificado: componentes
  NAO tem saldo fisico (loc 42/53) -> BLOQUEADO (decisao manual).
- demais            -> nome de lote literal.

Decisoes (respostas do usuario 2026-05-20):
- Q1: reduzir buscando saldo em LF/Estoque(42) E LF/Pre-Producao(53).
  Positivos vao para LF/Estoque(42). NAO tocar locais virtuais (38/39).
- Q2: compostos so seriam divididos se fossem 2 lotes com saldo; nao sao.

Seguranca (net-zero por produto):
- So processa produtos cujos NEGATIVOS tem saldo fisico suficiente (loc42+53)
  e que NAO tem linha composta. Produto com qualquer pendencia e PULADO
  INTEIRO (nao aplica positivos sozinhos -> nao infla estoque).
- 125/147 produtos aplicaveis; 22 bloqueados (12 composto + 12 sem saldo).

Mecanismo: inventory adjustment (inventory_quantity + action_apply_inventory).
- Reducao multi-local: consome de loc 42 primeiro, depois loc 53.
- Aumento: aplica em loc 42 (cria lote/quant se preciso).

Uso:
    python scripts/inventario_2026_05/ajuste_estoque_lf_pasta17.py            # dry-run
    python scripts/inventario_2026_05/ajuste_estoque_lf_pasta17.py --confirmar  # real
    (opcional) --apenas-cods 105000028,104000001
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
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('ajuste_lf_p17')

COMPANY_LF = 5
LOC_ESTOQUE = 42       # LF/Estoque (aumento + 1a opcao reducao)
LOC_PREPROD = 53       # LF/Pre-Producao (2a opcao reducao)
LOC_PRODUCAO = 39      # Estoque Virtual/Producao (virtual)
LOC_AJUSTE = 38        # Estoque Virtual/Ajuste de Estoque (virtual)
# Padrao: so fisico. --incluir-virtual estende para 39/38 (consumo apos fisico).
LOCS_REDUCAO = [LOC_ESTOQUE, LOC_PREPROD]
LOTE_SEM = 'P-15/05'   # lote canonico para "sem lote" na LF
CASAS = 6
TOL = 0.001
DEFAULT_XLSX = '/mnt/c/Users/rafael.nascimento/Downloads/Pasta17.xlsx'


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def _norm_cod(raw) -> str:
    s = str(raw).strip()
    return s[:-2] if s.endswith('.0') else s


def classificar_lote(raw) -> Tuple[str, Optional[str]]:
    """('SEM_LOTE', None) | ('LOTE', nome).

    NOTA (2026-05-20): lotes com virgula (ex '10388, MIGRAÇÃO', '224,276')
    NAO sao split de 2 lotes — sao lotes LITERAIS reais no Odoo (CIEL IT cria
    assim). Confirmado: o lote literal tem o saldo fisico. Tratar como nome
    normal (sem split). Decisao do usuario: baixar do lote que tiver saldo.
    """
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ('SEM_LOTE', None)
    s = str(raw).strip()
    if not s or s.lower() in ('nan', 'none'):
        return ('SEM_LOTE', None)
    if s.endswith('.0'):
        s = s[:-2]
    if s == LOTE_SEM:
        return ('SEM_LOTE', None)
    return ('LOTE', s)


def carregar_planilha(path: str) -> List[Dict]:
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    need = {'filial', 'cod', 'lote', 'qtd'}
    if not need.issubset(df.columns):
        raise ValueError(f'Planilha sem colunas {need}; tem {list(df.columns)}')
    regs = []
    for idx, row in df.iterrows():
        regs.append({
            'idx': int(idx) + 1,
            'filial': str(row['filial']).strip(),
            'cod': _norm_cod(row['cod']),
            'nome_produto': str(row.get('nome_produto', '')).strip(),
            'lote_raw': None if pd.isna(row['lote']) else str(row['lote']).strip(),
            'qtd': round(float(row['qtd']), CASAS),
        })
    return regs


def resolver_pids(odoo, cods: List[str]) -> Dict[str, Dict]:
    res = odoo.search_read(
        'product.product', [['default_code', 'in', cods]],
        ['id', 'default_code', 'active', 'tracking'], limit=0)
    out: Dict[str, Dict] = {}
    for p in res:
        c = p['default_code']
        if c not in out or p['active']:
            out[c] = {'pid': p['id'], 'tracking': p.get('tracking') or 'none',
                      'active': bool(p['active'])}
    return out


def carregar_quants(odoo, pids: List[int]) -> Dict[int, List[Dict]]:
    quants = odoo.search_read(
        'stock.quant',
        [['product_id', 'in', pids], ['company_id', '=', COMPANY_LF]],
        ['product_id', 'location_id', 'lot_id', 'quantity', 'reserved_quantity'],
        limit=0)
    by: Dict[int, List[Dict]] = defaultdict(list)
    for q in quants:
        by[q['product_id'][0]].append(q)
    return by


def _match_lote(q, lote_nome: Optional[str]) -> bool:
    ln = q['lot_id'][1] if q['lot_id'] else None
    if lote_nome is None:  # sem lote = P-15/05 ou lot_id=False
        return ln is None or ln == LOTE_SEM
    return ln == lote_nome


def saldo_fisico(by_pid, pid, lote_nome) -> float:
    tot = 0.0
    for q in by_pid.get(pid, []):
        if _match_lote(q, lote_nome) and q['location_id'][0] in LOCS_REDUCAO:
            tot += float(q['quantity'])
    return round(tot, CASAS)


# ----------------- agregacao + classificacao de produtos -----------------

def agregar_por_produto(regs):
    """ {cod: {'linhas':[..], 'grupos': {lote_norm: delta}, 'composto':bool} } """
    out = defaultdict(lambda: {'linhas': [], 'grupos': defaultdict(float),
                               'composto': False, 'filial': None,
                               'nome_produto': ''})
    for r in regs:
        d = out[r['cod']]
        d['linhas'].append(r)
        d['filial'] = r['filial']
        d['nome_produto'] = r['nome_produto']
        tipo, val = classificar_lote(r['lote_raw'])
        if tipo == 'COMPOSTO':
            d['composto'] = True
            d['grupos_composto'] = d.get('grupos_composto', [])
            d['grupos_composto'].append(r)
            continue
        d['grupos'][val] = round(d['grupos'][val] + r['qtd'], CASAS)
    return out


def classificar_produto(cod, d, prodinfo, by_pid) -> Tuple[bool, List[str]]:
    motivos = []
    if d['filial'] != 'LF':
        motivos.append('nao_LF')
    if d['composto']:
        motivos.append('composto')
    pid = prodinfo.get(cod, {}).get('pid')
    if not pid:
        motivos.append('produto_inexistente')
    else:
        for lote_norm, delta in d['grupos'].items():
            if delta < -TOL:
                if saldo_fisico(by_pid, pid, lote_norm) + TOL < abs(delta):
                    motivos.append(f'neg_sem_saldo:{lote_norm or "<sem lote>"}')
    return (len(motivos) == 0, motivos)


# ----------------- execucao -----------------

def resolver_lot_ids(odoo, pid, nome) -> List[int]:
    """Todos os lot_ids com `nome` exato (operador 'in' evita bug do '=')."""
    res = odoo.search_read(
        'stock.lot', [['product_id', '=', pid], ['name', 'in', [nome]]],
        ['id', 'name'], limit=0)
    return [r['id'] for r in res if (r.get('name') or '').strip() == nome]


def buscar_quants_fresh(odoo, pid, lote_nome, locations):
    """lote_nome None => sem lote (P-15/05 [todos ids] + lot_id=False)."""
    base = [['product_id', '=', pid], ['company_id', '=', COMPANY_LF],
            ['location_id', 'in', locations]]
    if lote_nome is None:
        ids = resolver_lot_ids(odoo, pid, LOTE_SEM)
        if ids:
            dom = base + ['|', ['lot_id', 'in', ids], ['lot_id', '=', False]]
        else:
            dom = base + [['lot_id', '=', False]]
    else:
        ids = resolver_lot_ids(odoo, pid, lote_nome)
        if not ids:
            return []
        dom = base + [['lot_id', 'in', ids]]
    return odoo.search_read('stock.quant', dom,
                            ['id', 'location_id', 'lot_id', 'quantity',
                             'reserved_quantity'], limit=0)


def planejar_reducao(quants, qty) -> Dict:
    """Planeja consumo de qty (positivo) — loc42 antes loc53. NAO grava."""
    def ordem(q):
        loc = q['location_id'][0]
        livre = float(q['quantity']) - float(q.get('reserved_quantity') or 0)
        return (LOCS_REDUCAO.index(loc) if loc in LOCS_REDUCAO else 9, -livre)
    quants = sorted(quants, key=ordem)
    restante = qty
    passos = []
    for q in quants:
        if restante <= TOL:
            break
        livre = float(q['quantity']) - float(q.get('reserved_quantity') or 0)
        if livre <= TOL:
            continue
        consumir = min(livre, restante)
        nova = round(float(q['quantity']) - consumir, CASAS)
        passos.append({'quant_id': q['id'], 'loc': q['location_id'][0],
                       'lote': q['lot_id'][1] if q['lot_id'] else None,
                       'de': float(q['quantity']), 'para': nova,
                       'consumido': round(consumir, CASAS)})
        restante = round(restante - consumir, CASAS)
    return {'passos': passos, 'restante': restante, 'cobriu': restante <= TOL}


def aplicar_aumento(odoo, lot_svc, pid, lote_nome, qty, dry) -> Dict:
    """Aumenta/cria saldo em loc42. lote_nome None => P-15/05."""
    alvo_nome = LOTE_SEM if lote_nome is None else lote_nome
    lot_id = lot_svc.buscar_por_nome(alvo_nome, pid, COMPANY_LF)
    acao_lote = 'reused'
    if not lot_id:
        if dry:
            lot_id = None
            acao_lote = 'will_create'
        else:
            lot_id, criado = lot_svc.criar_se_nao_existe(
                alvo_nome, pid, COMPANY_LF, expiration_date=None)
            acao_lote = 'created' if criado else 'reused'
    # quant destino em loc42
    q = None
    if lot_id:
        qs = odoo.search_read('stock.quant',
                              [['product_id', '=', pid], ['company_id', '=', COMPANY_LF],
                               ['location_id', '=', LOC_ESTOQUE], ['lot_id', '=', lot_id]],
                              ['id', 'quantity'], limit=1)
        q = qs[0] if qs else None
    de = float(q['quantity']) if q else 0.0
    para = round(de + qty, CASAS)
    res = {'alvo_lote': alvo_nome, 'lot_id': lot_id, 'acao_lote': acao_lote,
           'loc': LOC_ESTOQUE, 'de': de, 'para': para}
    if dry:
        return res
    if q:
        odoo.write('stock.quant', [q['id']], {'inventory_quantity': para})
        odoo.execute_kw('stock.quant', 'action_apply_inventory', [[q['id']]])
        res['quant_id'] = q['id']
    else:
        payload = {'product_id': pid, 'company_id': COMPANY_LF,
                   'location_id': LOC_ESTOQUE, 'lot_id': lot_id,
                   'inventory_quantity': qty}
        qid = odoo.create('stock.quant', payload)
        odoo.execute_kw('stock.quant', 'action_apply_inventory', [[qid]])
        res['quant_id'] = qid
    return res


def processar_produto(odoo, lot_svc, cod, d, prodinfo, dry) -> List[Dict]:
    """ATOMICO por produto: planeja todas as reducoes; se alguma nao cobre,
    aborta o produto inteiro (nao grava nada -> nao infla)."""
    pid = prodinfo[cod]['pid']
    itens = sorted(d['grupos'].items(), key=lambda kv: kv[1])  # delta asc

    # ---- FASE A: planejar reducoes (sem gravar) ----
    planos: List[Tuple] = []
    for lote_norm, delta in itens:
        if abs(delta) < TOL:
            continue
        if delta < 0:
            quants = buscar_quants_fresh(odoo, pid, lote_norm, LOCS_REDUCAO)
            plano = planejar_reducao(quants, abs(delta))
            if not plano['cobriu']:
                disp = round(abs(delta) - plano['restante'], CASAS)
                return [{'cod': cod, 'op': 'PRODUTO',
                         'lote': lote_norm if lote_norm is not None else '<SEM LOTE>',
                         'delta': delta, 'status': 'BLOQUEADO_REDUCAO_NAO_COBRE',
                         'erro': (f'reducao {lote_norm or "<SEM LOTE>"} precisa '
                                  f'{abs(delta)} mas so ha {disp} em loc42/53 '
                                  f'-> produto ABORTADO (nada gravado)')}]
            planos.append(('RED', lote_norm, delta, plano))
        else:
            planos.append(('AUM', lote_norm, delta, None))

    # ---- FASE B: aplicar (reducoes ja vem primeiro por sort asc) ----
    out = []
    for tipo, lote_norm, delta, plano in planos:
        r = {'cod': cod, 'pid': pid, 'delta': delta,
             'lote': lote_norm if lote_norm is not None else '<SEM LOTE>'}
        try:
            if tipo == 'RED':
                for p in plano['passos']:
                    if not dry:
                        odoo.write('stock.quant', [p['quant_id']],
                                   {'inventory_quantity': p['para']})
                        odoo.execute_kw('stock.quant', 'action_apply_inventory',
                                        [[p['quant_id']]])
                r['op'] = 'REDUCAO'
                r['status'] = 'OK'
                r['passos'] = plano['passos']
                r['restante'] = plano['restante']
            else:
                rr = aplicar_aumento(odoo, lot_svc, pid, lote_norm, delta, dry)
                r.update(rr)
                r['op'] = 'AUMENTO'
                r['status'] = 'OK'
        except Exception as exc:
            r['op'] = tipo
            r['status'] = 'FALHA_ODOO'
            r['erro'] = str(exc)
            logger.exception(f'cod={cod} lote={lote_norm} falha')
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true', default=False)
    ap.add_argument('--xlsx', type=str, default=DEFAULT_XLSX)
    ap.add_argument('--apenas-cods', type=str, default='')
    ap.add_argument('--incluir-virtual', action='store_true', default=False,
                    help='Inclui loc 39 (Producao) e 38 (Ajuste) na reducao, '
                         'apos esgotar o fisico (42/53)')
    ap.add_argument('--log-json', type=str, default='')
    args = ap.parse_args()
    dry = not args.confirmar

    global LOCS_REDUCAO
    if args.incluir_virtual:
        LOCS_REDUCAO = [LOC_ESTOQUE, LOC_PREPROD, LOC_PRODUCAO, LOC_AJUSTE]
        logger.warning('--incluir-virtual ATIVO: reducao tambem de loc 39 '
                       '(Producao) e 38 (Ajuste de Estoque)')

    if not Path(args.xlsx).exists():
        logger.error(f'XLSX nao encontrado: {args.xlsx}')
        return 2

    regs = carregar_planilha(args.xlsx)
    if args.apenas_cods:
        alvo = {s.strip() for s in args.apenas_cods.split(',') if s.strip()}
        regs = [r for r in regs if r['cod'] in alvo]

    porprod = agregar_por_produto(regs)
    cods = sorted(porprod.keys())

    app = create_app()
    resultados = []
    bloqueados = []
    t0 = time.time()
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        prodinfo = resolver_pids(odoo, cods)
        by_pid = carregar_quants(odoo, [p['pid'] for p in prodinfo.values()])

        # classificar
        aplicaveis = []
        for cod in cods:
            d = porprod[cod]
            ok, motivos = classificar_produto(cod, d, prodinfo, by_pid)
            if ok:
                aplicaveis.append(cod)
            else:
                bloqueados.append({'cod': cod, 'motivos': motivos,
                                   'nome': d['nome_produto']})

        banner(f'AJUSTE +/- LF (realocacao) — {"DRY-RUN" if dry else "EXEC REAL"}')
        print(f'  Produtos na planilha : {len(cods)}')
        print(f'  APLICAVEIS           : {len(aplicaveis)}')
        print(f'  BLOQUEADOS           : {len(bloqueados)}')

        for cod in aplicaveis:
            res = processar_produto(odoo, lot_svc, cod, porprod[cod], prodinfo, dry)
            resultados.extend(res)
            for r in res:
                tag = r['status']
                if r['op'] == 'REDUCAO':
                    extra = (f"{len(r.get('passos', []))} passo(s) "
                             f"rest={r.get('restante')}")
                else:
                    extra = f"-> {r.get('alvo_lote')} {r.get('de')}->{r.get('para')}"
                if tag == 'OK':
                    logger.info(f"  {r['op']:8} cod={cod} lote={str(r['lote']):>20} "
                                f"delta={r['delta']:+} | {extra}")
                else:
                    logger.warning(f"  {r['op']:8} cod={cod} lote={r['lote']} "
                                   f"{tag}: {r.get('erro', extra)}")

    banner('RESUMO')
    cont = Counter((r['op'], r['status']) for r in resultados)
    for (op, st), n in cont.most_common():
        print(f'  {op:8} {st:20s} {n:4d}')
    soma_red = sum(r['delta'] for r in resultados if r['op'] == 'REDUCAO' and r['status'] == 'OK')
    soma_aum = sum(r['delta'] for r in resultados if r['op'] == 'AUMENTO' and r['status'] == 'OK')
    print(f"\n  Reducao OK: {soma_red:,.2f}   Aumento OK: {soma_aum:,.2f}   "
          f"net: {soma_red + soma_aum:,.4f}")
    print(f'  Produtos aplicados: {len(set(r["cod"] for r in resultados))}')
    print(f'  Tempo: {time.time() - t0:.1f}s')

    if bloqueados:
        banner('PRODUTOS BLOQUEADOS (nao aplicados)', c='-')
        for b in bloqueados:
            print(f"  cod={b['cod']:>9} {b['motivos']}")

    log_path = args.log_json or str(
        _THIS.parent / 'auditoria' /
        f'log_ajuste_lf_p17_{"real" if not dry else "dryrun"}_'
        f'{datetime.now():%Y%m%d_%H%M%S}.json')
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({'args': vars(args), 'dry_run': dry,
                   'aplicaveis': len(set(r['cod'] for r in resultados)),
                   'bloqueados': bloqueados, 'resultados': resultados},
                  f, indent=2, default=str, ensure_ascii=False)
    print(f'\n  Log JSON: {log_path}')
    if dry:
        print('\n  DRY-RUN — nada gravado. Revise e use --confirmar.')

    falhas = sum(1 for r in resultados if r['status'].startswith('FALHA'))
    return 0 if falhas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
