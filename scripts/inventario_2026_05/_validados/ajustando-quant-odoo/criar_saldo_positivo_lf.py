"""criar_saldo_positivo_lf.py — Ajuste de inventario POSITIVO PURO na LF.

Pedido do usuario 2026-05-20: "criar saldo" — NAO transferir de MIGRACAO.

Cria/aumenta saldo em LF/Estoque (loc 42, company_id=5) para cada
(cod, lote, qtd) da planilha, via inventory adjustment PURO (entrada do
nada; a contraparte e' o Estoque Virtual/Inventory adjustment gerado
automaticamente pelo Odoo ao aplicar o ajuste).

Diferenca vs 15r_transferencia_reversa.py:
- 15r: 2 passos (reduz MIGRACAO + aumenta destino)  = TRANSFERENCIA
- este: 1 passo  (so aumenta/cria o destino)         = CRIAR SALDO

Mecanismo (passo unico):
- busca quant em LF/Estoque(42) + (lote ou sem lote)
  - se existe : inventory_quantity = quantidade_atual + ajuste   (SOMA)
  - se nao    : create stock.quant com inventory_quantity = ajuste
- action_apply_inventory

Lote (decidido pelo tracking do produto):
- tracking='lot'  : busca/cria lote por nome (P-15/05 e' lote REAL aqui,
                    NAO proxy vazio — diferente do 15r)
- tracking='none' : lot_id=False (nome do lote ignorado, com aviso)
- tracking='serial': BLOQUEIA (qtd != 1 por serial — fora de escopo)

Planilha (Pasta16.xlsx, aba "AJUSTE POSITIVO"):
    colunas: EMP | COD | PROD | LOTE | AJUSTE POSITIVO

Uso:
    python scripts/inventario_2026_05/criar_saldo_positivo_lf.py            # dry-run
    python scripts/inventario_2026_05/criar_saldo_positivo_lf.py --confirmar  # real
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
# ARQUIVADO 2026-05-23 — movido para _validados/ajustando-quant-odoo/ (2 niveis abaixo).
# parents[2] (era repo root) → parents[4] após o move. Skill substituta: ajustando-quant-odoo.
sys.path.insert(0, str(_THIS.parents[4]))

import pandas as pd  # noqa: E402

from app import create_app  # noqa: E402
from app.odoo.constants.locations import COMPANY_LOCATIONS  # noqa: E402
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('criar_saldo_positivo_lf')

FILIAL_TO_COMPANY = {'FB': 1, 'CD': 4, 'LF': 5}
CASAS_DECIMAIS = 6
DEFAULT_XLSX = '/mnt/c/Users/rafael.nascimento/Downloads/Pasta16.xlsx'


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def _norm_cod(raw) -> str:
    s = str(raw).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s


def _norm_lote(raw) -> Optional[str]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s or s.lower() == 'nan':
        return None
    if s.endswith('.0'):  # lote numerico lido como float
        s = s[:-2]
    return s


def carregar_planilha(path: str) -> List[Dict]:
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.strip().upper() for c in df.columns]
    obrigatorias = {'EMP', 'COD', 'LOTE', 'AJUSTE POSITIVO'}
    if not obrigatorias.issubset(df.columns):
        raise ValueError(
            f'Planilha sem colunas {obrigatorias}; tem {list(df.columns)}'
        )
    registros = []
    for idx, row in df.iterrows():
        ajuste_raw = row['AJUSTE POSITIVO']
        ajuste = round(float(ajuste_raw), CASAS_DECIMAIS)
        registros.append({
            'idx': int(idx) + 1,
            'filial': str(row['EMP']).strip(),
            'cod': _norm_cod(row['COD']),
            'prod': str(row.get('PROD', '')).strip(),
            'lote_nome': _norm_lote(row['LOTE']),
            'ajuste': ajuste,
        })
    return registros


def resolver_produto(odoo, cod: str) -> Optional[Dict]:
    res = odoo.search_read(
        'product.product', [['default_code', '=', cod]],
        ['id', 'active', 'tracking', 'name'], limit=10,
    )
    if not res:
        return None
    ativos = [r for r in res if r.get('active')]
    escolhido = ativos[0] if ativos else res[0]
    return {
        'pid': escolhido['id'],
        'tracking': escolhido.get('tracking') or 'none',
        'name': escolhido.get('name'),
        'active': bool(escolhido.get('active')),
        'n_matches': len(res),
    }


def buscar_quant(odoo, pid: int, company_id: int, location_id: int, lot_id):
    domain = [
        ['product_id', '=', pid],
        ['company_id', '=', company_id],
        ['location_id', '=', location_id],
    ]
    if lot_id is False or lot_id is None:
        domain.append(['lot_id', '=', False])
    else:
        domain.append(['lot_id', '=', lot_id])
    qs = odoo.search_read(
        'stock.quant', domain,
        ['id', 'quantity', 'reserved_quantity'], limit=1,
    )
    return qs[0] if qs else None


def processar_item(odoo, lot_svc, item, dry_run: bool) -> Dict:
    r = {**item, 'inicio': datetime.now().isoformat(timespec='seconds')}

    company_id = FILIAL_TO_COMPANY.get(item['filial'])
    if not company_id:
        r['status'] = 'SKIP_FILIAL'
        r['erro'] = f'filial {item["filial"]!r} desconhecida (esperado LF)'
        return r
    if company_id != 5:
        r['status'] = 'SKIP_NAO_LF'
        r['erro'] = f'item nao e LF (company={company_id}) — script so faz LF'
        return r
    location_id = COMPANY_LOCATIONS[company_id]  # 42
    r['company_id'] = company_id
    r['location_id'] = location_id

    if item['ajuste'] <= 0:
        r['status'] = 'SKIP_QTD_NAO_POSITIVA'
        r['erro'] = f'ajuste={item["ajuste"]} <= 0'
        return r

    prod = resolver_produto(odoo, item['cod'])
    if not prod:
        r['status'] = 'FALHA_PRODUCT'
        r['erro'] = f'cod {item["cod"]!r} nao encontrado em product.product'
        return r
    pid = prod['pid']
    r['product_id'] = pid
    r['tracking'] = prod['tracking']
    r['produto_odoo'] = prod['name']
    if prod['n_matches'] > 1:
        r['warning_multiplos_codigos'] = prod['n_matches']
    if not prod['active']:
        r['warning_produto_inativo'] = True

    # Decidir lote conforme tracking
    if prod['tracking'] == 'serial':
        r['status'] = 'BLOQUEADO_SERIAL'
        r['erro'] = 'produto tracking=serial — ajuste por qtd nao suportado'
        return r

    lot_id = False
    if prod['tracking'] == 'lot':
        if not item['lote_nome']:
            r['status'] = 'FALHA_LOTE_OBRIGATORIO'
            r['erro'] = 'produto tracking=lot mas planilha sem LOTE'
            return r
        existente = lot_svc.buscar_por_nome(item['lote_nome'], pid, company_id)
        if existente:
            lot_id = existente
            r['lote_acao'] = 'reused'
        else:
            if dry_run:
                lot_id = None
                r['lote_acao'] = 'will_create'
            else:
                try:
                    lot_id, criado = lot_svc.criar_se_nao_existe(
                        item['lote_nome'], pid, company_id,
                        expiration_date=None,
                    )
                    r['lote_acao'] = 'created' if criado else 'reused'
                except Exception as exc:
                    r['status'] = 'FALHA_CRIAR_LOTE'
                    r['erro'] = f'criar lote {item["lote_nome"]!r}: {exc}'
                    return r
        r['lot_id'] = lot_id
    else:  # tracking='none'
        if item['lote_nome']:
            r['warning_lote_ignorado'] = (
                f'produto tracking=none — lote {item["lote_nome"]!r} ignorado'
            )
        r['lot_id'] = False

    # Quant atual em LF/Estoque (informativo + base da soma)
    q = None
    if not (prod['tracking'] == 'lot' and lot_id is None):
        q = buscar_quant(odoo, pid, company_id, location_id, lot_id)
    r['quant_atual'] = q
    qty_antes = float(q['quantity']) if q else 0.0
    r['qty_antes'] = qty_antes
    r['qty_apos'] = round(qty_antes + item['ajuste'], CASAS_DECIMAIS)

    if dry_run:
        r['status'] = 'DRY_RUN_OK'
        return r

    # ===================== EXECUCAO (criar saldo) =====================
    t0 = time.time()
    try:
        if q:
            odoo.write('stock.quant', [q['id']],
                       {'inventory_quantity': r['qty_apos']})
            odoo.execute_kw('stock.quant', 'action_apply_inventory',
                            [[q['id']]])
            r['quant_id'] = q['id']
            r['quant_acao'] = 'somado'
        else:
            payload = {
                'product_id': pid,
                'company_id': company_id,
                'location_id': location_id,
                'inventory_quantity': item['ajuste'],
            }
            if lot_id:
                payload['lot_id'] = lot_id
            qid = odoo.create('stock.quant', payload)
            odoo.execute_kw('stock.quant', 'action_apply_inventory', [[qid]])
            r['quant_id'] = qid
            r['quant_acao'] = 'criado'
        r['status'] = 'EXECUTADO'
        r['tempo_ms'] = int((time.time() - t0) * 1000)
    except Exception as exc:
        r['status'] = 'FALHA_ODOO'
        r['erro'] = str(exc)
        r['tempo_ms'] = int((time.time() - t0) * 1000)
        logger.exception(f'idx={item["idx"]} cod={item["cod"]} falha')
    return r


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--confirmar', action='store_true', default=False,
                        help='Executa de fato (default = dry-run)')
    parser.add_argument('--xlsx', type=str, default=DEFAULT_XLSX)
    parser.add_argument('--apenas-linhas', type=str, default='',
                        help='CSV de idx 1-based para filtrar: 1,5,7')
    parser.add_argument('--log-json', type=str, default='')
    args = parser.parse_args()

    dry_run = not args.confirmar

    if not Path(args.xlsx).exists():
        logger.error(f'XLSX nao encontrado: {args.xlsx}')
        return 2

    registros = carregar_planilha(args.xlsx)
    if args.apenas_linhas:
        alvo = {int(s) for s in args.apenas_linhas.split(',') if s.strip()}
        registros = [r for r in registros if r['idx'] in alvo]

    banner(
        f'CRIAR SALDO POSITIVO LF (loc 42) — '
        f'{"DRY-RUN" if dry_run else "EXEC REAL"} ({len(registros)} linhas)'
    )
    soma_planilha = sum(r['ajuste'] for r in registros)
    print(f'  Soma AJUSTE POSITIVO da planilha: {soma_planilha:,.6f} un')

    app = create_app()
    resultados = []
    t_global = time.time()
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        for item in registros:
            r = processar_item(odoo, lot_svc, item, dry_run)
            resultados.append(r)
            s = r['status']
            base = (f'[{r["idx"]:>2}/{len(registros)}] {s:18s} '
                    f'cod={item["cod"]:>9} lote={str(item["lote_nome"]):>14} '
                    f'+{item["ajuste"]}')
            if s in ('EXECUTADO', 'DRY_RUN_OK'):
                logger.info(
                    f'{base} | trk={r.get("tracking")} '
                    f'lote_acao={r.get("lote_acao","-")} '
                    f'qty {r.get("qty_antes")}->{r.get("qty_apos")}'
                )
            else:
                logger.warning(f'{base} | {r.get("erro")}')

    banner('RESUMO')
    cont = Counter(r['status'] for r in resultados)
    for status, n in cont.most_common():
        print(f'  {status:28s} {n:4d}')
    print(f'  {"TOTAL":28s} {len(resultados):4d}')

    soma_ok = sum(
        r['ajuste'] for r in resultados
        if r['status'] in ('EXECUTADO', 'DRY_RUN_OK')
    )
    print(f'\n  Soma a criar (status OK): {soma_ok:,.6f} un')
    print(f'  Tempo total: {time.time() - t_global:.1f}s')

    # avisos
    avisos = [r for r in resultados if any(
        k.startswith('warning') for k in r)]
    if avisos:
        banner('AVISOS', c='-')
        for r in avisos:
            ws = {k: v for k, v in r.items() if k.startswith('warning')}
            print(f'  cod={r["cod"]} lote={r.get("lote_nome")}: {ws}')

    log_path = args.log_json
    if not log_path:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        modo = 'real' if not dry_run else 'dryrun'
        log_path = str(
            _THIS.parent / 'auditoria' /
            f'log_criar_saldo_positivo_lf_{modo}_{ts}.json'
        )
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            'args': vars(args),
            'dry_run': dry_run,
            'total': len(resultados),
            'contagem_status': dict(cont),
            'soma_planilha': soma_planilha,
            'soma_ok': soma_ok,
            'resultados': resultados,
        }, f, indent=2, default=str, ensure_ascii=False)
    print(f'\n  Log JSON: {log_path}')

    if dry_run:
        print('\n  DRY-RUN — nada gravado. Use --confirmar para criar saldo.')

    falhas = sum(1 for r in resultados if r['status'].startswith('FALHA')
                 or r['status'].startswith('BLOQUEADO'))
    return 0 if falhas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
