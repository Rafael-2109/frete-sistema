"""transferir_local_pasta22.py — Transferencia De/Para LOCAL+LOTE (Pasta22).

Planilha: filial | cod | nome_produto | DE - LOCAL | DE - LOTE | PARA - LOCAL | PARA - LOTE | QTD
Multi-empresa por linha (LF=5, FB=1, CD=4). Dois sentidos:
  SAIDA  : {EMP}/* (wildcard) <lote> -> {EMP}/Indisponivel / MIGRACAO  (envia p/ indisponivel)
  RETORNO: {EMP}/Indisponivel / MIGRACAO -> {EMP}/Estoque <lote>       (devolve ao estoque)

3 PREMISSAS de saldo (confirmadas pelo usuario 2026-05-20):
  1. QTD BRUTA: move o `quantity` cheio, resetando reserved_quantity (reservas
     tratadas como fantasmas). NAO desconta reserva.
  2. P-15/05 = lote nomeado 'P-15/05' + quant SEM LOTE (lot_id=False).
  3. TODOS OS LOCAIS internos da empresa (usage='internal') exceto Indisponivel
     (origem da SAIDA). Saldo espalhado em sub-locations.

ESCOPO desta execucao ("faca o que tiver saldo"): SOMENTE TRANSFERENCIAS REAIS.
  - SAIDA: move o saldo existente (clamp ao disponivel). Pula se nao houver.
  - RETORNO: transfere do MIGRACAO o que ele cobrir (apos a SAIDA encher).
  - NAO faz AJUSTE POSITIVO (criar saldo onde MIGRACAO esta vazio): o deficit
    fica PENDENTE e e reportado p/ o usuario validar via MONITOR e decidir.

Ordem: TODAS as SAIDAs primeiro (enchem MIGRACAO) -> depois RETORNOs.
Mecanismo: primitiva StockQuantAdjustmentService (delta +/- via inventory
adjustment). company_id SEMPRE da filial (evita 'Empresas incompativeis').

Uso:
    python scripts/inventario_2026_05/transferir_local_pasta22.py            # dry-run
    python scripts/inventario_2026_05/transferir_local_pasta22.py --confirmar
"""
import argparse
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

import pandas as pd  # noqa: E402

from app import create_app  # noqa: E402
from app.odoo.constants.locations import (  # noqa: E402
    get_local_indisponivel, get_location_id)
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.services.stock_quant_adjustment_service import (  # noqa: E402
    StockQuantAdjustmentService,
)
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s')
logger = logging.getLogger('transf_local_p22')

COMPANY = {'LF': 5, 'FB': 1, 'CD': 4}
ESTOQUE = {c: get_location_id(c) for c in (1, 4, 5)}        # central: COMPANY_LOCATIONS
INDISP = {c: get_local_indisponivel(c) for c in (1, 4, 5)}  # central: LOCAIS_INDISPONIVEL
LOTE_MIGRACAO_VARIANTES = ['MIGRAÇÃO', 'MIGRACAO', 'MIGRAÇAO']
LOTE_MIGRACAO_CANONICO = 'MIGRAÇÃO'
CASAS = 6
TOL = 0.01
DEFAULT_XLSX = '/mnt/c/Users/rafael.nascimento/Downloads/Pasta22.xlsx'


def banner(t, c='='):
    print('\n' + c * 92 + '\n  {}\n'.format(t) + c * 92)


def ncod(x):
    try:
        return str(int(float(x)))
    except (ValueError, TypeError):
        return str(x).strip()


def ntxt(x):
    if pd.isna(x):
        return None
    s = str(x).strip()
    return s if s and s.lower() != 'nan' else None


def is_migracao(lote):
    return bool(lote) and lote.strip().upper() in {v.upper() for v in LOTE_MIGRACAO_VARIANTES}


# ============================================================
# Resolucao
# ============================================================

def resolver_pid(odoo, cod):
    res = odoo.search_read('product.product', [['default_code', '=', cod]],
                           ['id', 'active'], limit=5)
    if not res:
        return None
    ativos = [r for r in res if r.get('active')]
    return (ativos[0] if ativos else res[0])['id']


def lotids_migracao(odoo, pid, company):
    return odoo.search('stock.lot', [['name', 'in', LOTE_MIGRACAO_VARIANTES],
                                     ['product_id', '=', pid], ['company_id', '=', company]])


def lotids_origem(odoo, pid, company, de_lote):
    """Resolve lot_ids do de_lote (premissa 2: P-15/05 inclui lot_id=False).
    Retorna (clauses_lote, label) onde clauses_lote e usado no dominio do quant.
    label e o nome para log. Para MIGRACAO retorna todos os lots MIGRACAO."""
    if is_migracao(de_lote):
        ids = lotids_migracao(odoo, pid, company)
        return ([['lot_id', 'in', ids]] if ids else None), LOTE_MIGRACAO_CANONICO
    ids = odoo.search('stock.lot', [['name', 'in', [de_lote]],
                                    ['product_id', '=', pid], ['company_id', '=', company]])
    if de_lote == 'P-15/05':
        # premissa 2: nomeado P-15/05 + sem-lote (lot_id=False)
        if ids:
            return ['|', ['lot_id', 'in', ids], ['lot_id', '=', False]], 'P-15/05(+sem-lote)'
        return [['lot_id', '=', False]], 'P-15/05(sem-lote)'
    if not ids:
        return None, de_lote
    return [['lot_id', 'in', ids]], de_lote


def buscar_quants_origem(odoo, pid, company, clauses_lote, locs_dominio):
    """Quants do lote (premissa 1: BRUTO; premissa 3: locais internos do dominio).
    `locs_dominio` e uma clausula de location (ex usage internal exc Indisp, ou loc fixo)."""
    dom = [['product_id', '=', pid], ['company_id', '=', company],
           ['quantity', '!=', 0]] + locs_dominio + clauses_lote
    qs = odoo.search_read('stock.quant', dom,
                          ['id', 'location_id', 'lot_id', 'quantity', 'reserved_quantity'], limit=0)
    qs.sort(key=lambda q: -float(q['quantity']))  # maior saldo primeiro
    return qs


def resolver_lote_destino(odoo, lot_svc, pid, company, loc_dest, para_lote):
    """lot_id destino. MIGRACAO -> consolida no de maior saldo na loc (cria se nenhum).
    Literal -> criar_se_nao_existe (filtra company -> evita 'Empresas incompativeis')."""
    if is_migracao(para_lote):
        ids = lotids_migracao(odoo, pid, company)
        if ids:
            qs = odoo.search_read('stock.quant',
                                  [['product_id', '=', pid], ['company_id', '=', company],
                                   ['location_id', '=', loc_dest], ['lot_id', 'in', ids]],
                                  ['lot_id', 'quantity'], limit=0)
            com_saldo = sorted([(q['lot_id'][0], float(q['quantity'])) for q in qs],
                               key=lambda x: -x[1])
            if com_saldo:
                return com_saldo[0][0], LOTE_MIGRACAO_CANONICO, False
            return ids[0], LOTE_MIGRACAO_CANONICO, False
        lid = lot_svc.criar(LOTE_MIGRACAO_CANONICO, pid, company)
        return lid, LOTE_MIGRACAO_CANONICO, True
    lid, criado = lot_svc.criar_se_nao_existe(para_lote, pid, company)
    return lid, para_lote, criado


# ============================================================
# Processar 1 linha
# ============================================================

def saldo_migracao_indisp(odoo, pid, company):
    ids = lotids_migracao(odoo, pid, company)
    if not ids:
        return 0.0
    qs = odoo.search_read('stock.quant',
                          [['product_id', '=', pid], ['company_id', '=', company],
                           ['location_id', '=', INDISP[company]], ['lot_id', 'in', ids]],
                          ['quantity'], limit=0)
    return round(sum(float(q['quantity']) for q in qs), CASAS)


def processar(odoo, lot_svc, svc, item, dry, mig_sim):
    """mig_sim: {(filial,cod): saldo MIGRACAO simulado em Indisp}. No DRY-RUN, a
    SAIDA enche e o RETORNO consome esse saldo (reflete a ordem real, ja que o
    Odoo nao e gravado no dry)."""
    r = {**item}
    qty = item['qty']
    if qty <= 0:
        r['status'] = 'SKIP_QTD_ZERO'
        return r
    company = COMPANY[item['filial']]
    pid = resolver_pid(odoo, item['cod'])
    if not pid:
        r['status'] = 'PRODUTO_INEXISTENTE'
        return r
    r['pid'] = pid
    saida = 'Indisp' in (item['para_local'] or '')
    key = (item['filial'], item['cod'])

    quants = []
    if saida:
        loc_dest = INDISP[company]
        locs_dominio = [['location_id.usage', '=', 'internal'], ['location_id', '!=', INDISP[company]]]
        clauses, label = lotids_origem(odoo, pid, company, item['de_lote'])
        r['lote_origem'] = label
        if clauses is None:
            r['status'] = 'LOTE_ORIGEM_INEXISTENTE'
            return r
        quants = buscar_quants_origem(odoo, pid, company, clauses, locs_dominio)
        bruto = round(sum(float(q['quantity']) for q in quants), CASAS)
    else:
        # RETORNO: origem = MIGRACAO em Indisponivel
        loc_dest = ESTOQUE[company]
        r['lote_origem'] = LOTE_MIGRACAO_CANONICO
        if dry:
            if key not in mig_sim:
                mig_sim[key] = saldo_migracao_indisp(odoo, pid, company)
            bruto = round(mig_sim[key], CASAS)
        else:
            clauses, _ = lotids_origem(odoo, pid, company, LOTE_MIGRACAO_CANONICO)
            quants = buscar_quants_origem(odoo, pid, company, clauses or [['id', '=', 0]],
                                          [['location_id', '=', INDISP[company]]]) if clauses else []
            bruto = round(sum(float(q['quantity']) for q in quants), CASAS)

    r['saldo_bruto_origem'] = bruto
    if bruto <= TOL:
        r['status'] = 'SEM_SALDO'
        return r

    mover = min(bruto, qty)
    r['mover'] = round(mover, CASAS)
    r['deficit'] = round(qty - mover, CASAS)  # RETORNO: deficit = ajuste positivo PENDENTE
    r['reserva_resetada'] = round(sum(float(q.get('reserved_quantity') or 0) for q in quants), CASAS)

    # destino
    lot_dest_id, dest_nome, criado = resolver_lote_destino(odoo, lot_svc, pid, company, loc_dest, item['para_lote'])
    r['lote_destino'] = dest_nome
    r['lote_destino_criado'] = criado

    if dry:
        if saida:  # enche MIGRACAO simulado
            if key not in mig_sim:
                mig_sim[key] = saldo_migracao_indisp(odoo, pid, company)
            mig_sim[key] = round(mig_sim[key] + mover, CASAS)
        else:  # RETORNO consome MIGRACAO simulado
            mig_sim[key] = round(bruto - mover, CASAS)
        r['status'] = 'DRY_RUN_OK' if r['deficit'] <= TOL else 'DRY_RUN_PARCIAL_DEFICIT'
        return r

    # --- reduzir origem (bruto: resetar reserva, mover quantity cheio ate `mover`) ---
    restante = mover
    reducoes = []
    for q in quants:
        if restante <= TOL:
            break
        consumir = min(float(q['quantity']), restante)
        res = svc.ajustar_quant(
            quant_id=q['id'], delta=-consumir,
            resetar_reserva=True, validar_nao_abaixo_reserva=False,
            validar_nao_negativar=True, casas_decimais=CASAS, dry_run=False)
        if res['status'] not in ('EXECUTADO', 'NOOP'):
            r['status'] = 'FALHA_REDUCAO'
            r['erro'] = res.get('erro')
            r['reducoes'] = reducoes
            return r
        reducoes.append({'quant_id': q['id'], 'loc': q['location_id'][0], 'consumido': round(consumir, CASAS)})
        restante = round(restante - consumir, CASAS)
    r['reducoes'] = reducoes
    movido = round(mover - restante, CASAS)
    r['movido'] = movido

    # --- aumentar destino ---
    res = svc.ajustar_quant(
        product_id=pid, company_id=company, location_id=loc_dest, lot_id=lot_dest_id,
        delta=movido, criar_se_faltar=True, validar_nao_negativar=True,
        validar_nao_abaixo_reserva=False, casas_decimais=CASAS, dry_run=False)
    r['destino_status'] = res['status']
    r['quant_destino_id'] = res.get('quant_id')
    if res['status'] not in ('EXECUTADO', 'NOOP'):
        r['status'] = 'FALHA_AUMENTO'
        r['erro'] = res.get('erro')
        return r
    r['status'] = 'EXECUTADO' if r['deficit'] <= TOL else 'EXECUTADO_PARCIAL_DEFICIT'
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xlsx', default=DEFAULT_XLSX)
    ap.add_argument('--confirmar', action='store_true', default=False)
    ap.add_argument('--log-json', default='')
    args = ap.parse_args()
    dry = not args.confirmar

    df = pd.read_excel(args.xlsx, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    regs = []
    for _, row in df.iterrows():
        regs.append({
            'filial': str(row['filial']).strip(), 'cod': ncod(row['cod']),
            'nome_produto': str(row.get('nome_produto', ''))[:40],
            'de_local': ntxt(row['DE - LOCAL']), 'de_lote': ntxt(row['DE - LOTE']),
            'para_local': ntxt(row['PARA - LOCAL']), 'para_lote': ntxt(row['PARA - LOTE']),
            'qty': round(float(row['QTD']), CASAS),
        })
    # ordem: SAIDA (->Indisp) antes de RETORNO (->Estoque)
    saidas = [r for r in regs if 'Indisp' in (r['para_local'] or '')]
    retornos = [r for r in regs if 'Indisp' not in (r['para_local'] or '')]
    ordem = saidas + retornos

    banner('TRANSFERIR LOCAL PASTA22 — {} ({} linhas: {} SAIDA + {} RETORNO)'.format(
        'DRY-RUN' if dry else 'EXEC REAL', len(ordem), len(saidas), len(retornos)))
    print('  Premissas: qty BRUTA (reset reserva) | P-15/05 = nomeado + sem-lote | todas internas')
    print('  Escopo: TRANSFERENCIAS REAIS (sem ajuste positivo; deficit fica pendente)')

    app = create_app()
    resultados = []
    t0 = time.time()
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        svc = StockQuantAdjustmentService(odoo=odoo, lot_svc=lot_svc)
        mig_sim = {}  # (filial,cod) -> saldo MIGRACAO simulado (dry-run reflete ordem SAIDA->RETORNO)
        for i, item in enumerate(ordem, 1):
            r = processar(odoo, lot_svc, svc, item, dry, mig_sim)
            resultados.append(r)
            st = r['status']
            tag = 'SAIDA' if 'Indisp' in (item['para_local'] or '') else 'RETORNO'
            if st in ('EXECUTADO', 'DRY_RUN_OK', 'EXECUTADO_PARCIAL_DEFICIT', 'DRY_RUN_PARCIAL_DEFICIT'):
                logger.info('[{}/{}] {:24} {} [{}] cod={} {}->{} mover={} deficit={}'.format(
                    i, len(ordem), st, tag, item['filial'], item['cod'],
                    r.get('lote_origem'), r.get('lote_destino'), r.get('mover'), r.get('deficit')))
            elif not st.startswith('SKIP'):
                logger.warning('[{}/{}] {:24} {} [{}] cod={} lote={}: {}'.format(
                    i, len(ordem), st, tag, item['filial'], item['cod'],
                    item['de_lote'], r.get('erro', r.get('saldo_bruto_origem'))))
            if i % 50 == 0 and not dry:
                _salvar(args, dry, resultados, parcial=True)

    banner('RESUMO')
    cont = Counter(r['status'] for r in resultados)
    for st, n in cont.most_common():
        print('  {:32s} {:4d}'.format(st, n))
    mov = sum(r.get('movido', r.get('mover', 0)) for r in resultados
              if r['status'].startswith('EXECUTADO') or r['status'].startswith('DRY_RUN'))
    defi = sum(r.get('deficit', 0) for r in resultados if r.get('deficit', 0) > TOL)
    print('\n  Total movido (transferencias): {:,.2f} un'.format(mov))
    print('  Deficit PENDENTE (ajuste positivo NAO feito, validar via MONITOR): {:,.2f} un'.format(defi))
    print('  Tempo: {:.1f}s'.format(time.time() - t0))

    pend = [r for r in resultados if r.get('deficit', 0) > TOL]
    if pend:
        banner('DEFICIT PENDENTE — ajuste positivo NAO aplicado (validar)', '-')
        for r in sorted(pend, key=lambda x: -x['deficit'])[:40]:
            print('  [{}] cod={} -> lote {!r}: faltou {:,.2f} (MIGRACAO insuficiente)'.format(
                r['filial'], r['cod'], r.get('lote_destino'), r['deficit']))
    semsaldo = [r for r in resultados if r['status'] in ('SEM_SALDO', 'PRODUTO_INEXISTENTE', 'LOTE_ORIGEM_INEXISTENTE')]
    if semsaldo:
        banner('SAIDAS SEM SALDO (puladas)', '-')
        for r in semsaldo:
            print('  [{}] cod={} de_lote={!r}: {}'.format(r['filial'], r['cod'], r['de_lote'], r['status']))

    _salvar(args, dry, resultados, parcial=False)
    if dry:
        print('\n  DRY-RUN — nada gravado. Use --confirmar para executar.')
    falhas = sum(1 for r in resultados if r['status'].startswith('FALHA'))
    return 0 if falhas == 0 else 1


def _salvar(args, dry, resultados, parcial):
    log_path = args.log_json or str(
        _THIS.parent / 'auditoria' / 'log_transf_local_p22_{}_{}.json'.format(
            'real' if not dry else 'dryrun', datetime.now().strftime('%Y%m%d_%H%M%S')))
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({'dry_run': dry, 'parcial': parcial, 'total': len(resultados),
                   'contagem': dict(Counter(r['status'] for r in resultados)),
                   'resultados': resultados}, f, indent=2, default=str, ensure_ascii=False)
    if not parcial:
        print('\n  Log JSON: {}'.format(log_path))


if __name__ == '__main__':
    sys.exit(main())
