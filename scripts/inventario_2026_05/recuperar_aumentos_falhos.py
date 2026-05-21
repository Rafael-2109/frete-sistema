"""recuperar_aumentos_falhos.py — Recupera AUMENTOS que falharam em
transferir_lote.py por 'Empresas incompativeis' (lot_id de outra empresa).

Contexto (2026-05-20): a execucao real de `transferir_lote.py --confirmar`
aplicou as 229 REDUCOES, mas 11 AUMENTOS falharam porque o lot_id escolhido
pertencia a empresa FB (nao LF). Resultado: ~320.547 un foram reduzidas mas
nao re-adicionadas -> estoque desbalanceado. Este script re-aplica SOMENTE
esses aumentos, resolvendo/criando o lote na EMPRESA CORRETA (a da filial).

Le os aumentos com status FALHA_* direto do log JSON da execucao real, para
auditoria (nao hardcoda). Aplica delta (+) no local principal da empresa via
primitiva StockQuantAdjustmentService.

NAO idempotente: rode UMA vez. Dry-run default; --confirmar aplica.

Uso:
    python scripts/inventario_2026_05/recuperar_aumentos_falhos.py --log PATH            # dry-run
    python scripts/inventario_2026_05/recuperar_aumentos_falhos.py --log PATH --confirmar
"""
import argparse
import glob
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app  # noqa: E402
from app.odoo.constants.locations import COMPANY_LOCATIONS  # noqa: E402
from app.odoo.constants.operacoes_fiscais import CODIGO_PARA_COMPANY_ID  # noqa: E402
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.services.stock_quant_adjustment_service import (  # noqa: E402
    StockQuantAdjustmentService,
)
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s')
logger = logging.getLogger('recuperar_aumentos')
CASAS = 6


def banner(t, c='='):
    print('\n' + c * 80 + f'\n  {t}\n' + c * 80)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', default='', help='log JSON da execucao real '
                    '(default: ultimo log_transferir_lote_real_*.json)')
    ap.add_argument('--confirmar', action='store_true', default=False)
    args = ap.parse_args()
    dry = not args.confirmar

    log_path = args.log
    if not log_path:
        cands = sorted(glob.glob(str(
            _THIS.parent / 'auditoria' / 'log_transferir_lote_real_*.json')))
        if not cands:
            logger.error('Nenhum log_transferir_lote_real_*.json encontrado')
            return 2
        log_path = cands[-1]

    d = json.load(open(log_path, encoding='utf-8'))
    falhos = [r for r in d['resultados']
              if r['op'] == 'AUMENTO' and str(r.get('status', '')).startswith('FALHA')]
    if not falhos:
        print('Nenhum aumento FALHA_* no log. Nada a recuperar.')
        return 0

    banner(f'RECUPERAR AUMENTOS FALHOS — {"DRY-RUN" if dry else "EXEC REAL"}')
    print(f'  Log origem : {log_path}')
    print(f'  Aumentos a recuperar: {len(falhos)}')
    total = sum(float(r['delta']) for r in falhos)
    print(f'  Soma a re-adicionar : {total:,.4f} un')

    app = create_app()
    resultados: List[Dict] = []
    t0 = time.time()
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        svc = StockQuantAdjustmentService(odoo=odoo, lot_svc=lot_svc)

        for r in falhos:
            filial = r['filial']
            cod = r['cod']
            nome = r['lote']
            delta = round(float(r['delta']), CASAS)
            company_id = CODIGO_PARA_COMPANY_ID[filial]
            loc = COMPANY_LOCATIONS[company_id]
            out = {'filial': filial, 'cod': cod, 'lote': nome, 'delta': delta,
                   'company_id': company_id, 'loc': loc}

            # resolver produto (default_code -> pid ativo)
            prods = odoo.search_read('product.product', [['default_code', '=', cod]],
                                     ['id', 'active'], limit=10)
            if not prods:
                out['status'] = 'FALHA_PRODUTO'
                out['erro'] = 'produto nao encontrado'
                resultados.append(out)
                logger.warning(f'  cod={cod}: produto nao encontrado')
                continue
            ativos = [p for p in prods if p['active']]
            pid = (ativos[0] if ativos else prods[0])['id']
            out['pid'] = pid

            # resolver/criar lot na EMPRESA CORRETA
            lot_id = lot_svc.buscar_por_nome(nome, pid, company_id)
            if lot_id:
                out['lote_acao'] = 'reused_lot_LF'
            elif dry:
                out['lote_acao'] = 'will_create_lot_LF'
            else:
                lot_id, criado = lot_svc.criar_se_nao_existe(
                    nome, pid, company_id, expiration_date=None)
                out['lote_acao'] = 'created_lot_LF' if criado else 'reused_lot_LF'
            out['lot_id'] = lot_id

            if lot_id is None and dry:
                out['status'] = 'DRY_RUN_OK'
                out['qty_antes'] = 0.0
                out['qty_apos'] = delta
                resultados.append(out)
                logger.info(f'  [{filial}] cod={cod} lote={nome!r} +{delta:.2f} '
                            f'-> {out["lote_acao"]} (lote sera criado na LF)')
                continue

            res = svc.ajustar_quant(
                product_id=pid, company_id=company_id, location_id=loc,
                lot_id=lot_id, delta=delta, criar_se_faltar=True,
                validar_nao_negativar=True, validar_nao_abaixo_reserva=True,
                casas_decimais=CASAS, dry_run=dry)
            out['status'] = res.get('status')
            out['qty_antes'] = res.get('qty_antes')
            out['qty_apos'] = res.get('qty_apos')
            out['quant_id'] = res.get('quant_id')
            out['erro'] = res.get('erro')
            resultados.append(out)
            if str(out['status']).startswith('FALHA'):
                logger.warning(f'  [{filial}] cod={cod} lote={nome!r} {out["status"]}: {out.get("erro")}')
            else:
                logger.info(f'  [{filial}] cod={cod} lote={nome!r} +{delta:.2f} '
                            f'loc={loc} qty {out.get("qty_antes")}->{out.get("qty_apos")} '
                            f'({out["lote_acao"]}, lot_id={lot_id})')

    banner('RESUMO')
    from collections import Counter
    cont = Counter(r['status'] for r in resultados)
    for st, n in cont.most_common():
        print(f'  {st:24s} {n:3d}')
    ok = sum(float(r['delta']) for r in resultados
             if r['status'] in ('EXECUTADO', 'DRY_RUN_OK'))
    print(f'\n  Re-adicionado OK: {ok:,.4f} un  | tempo {time.time()-t0:.1f}s')

    out_log = str(_THIS.parent / 'auditoria' /
                  f'log_recuperar_aumentos_{"real" if not dry else "dryrun"}_'
                  f'{time.strftime("%Y%m%d_%H%M%S")}.json')
    Path(out_log).parent.mkdir(parents=True, exist_ok=True)
    json.dump({'dry_run': dry, 'log_origem': log_path, 'resultados': resultados},
              open(out_log, 'w', encoding='utf-8'), indent=2, default=str, ensure_ascii=False)
    print(f'  Log JSON: {out_log}')
    if dry:
        print('\n  DRY-RUN — nada gravado. Use --confirmar para aplicar.')
    falhas = sum(1 for r in resultados if str(r['status']).startswith('FALHA'))
    return 0 if falhas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
