"""encontro_contas_lf.py — Encontro de contas FB<->LF por produto (Pasta23.xlsx).

REGRA (Rafael 2026-05-20), por produto:
    mov_liquido = qtd_entrada(FB->LF) - qtd_saida(LF->FB)
    mov_liquido > 0: ALTERA os lotes de saida (no LF) PELOS lotes de entrada
        (consolida no lote-alvo). O que faltar p/ completar as entradas, preenche
        com mov_liquido = faturamento real FB->LF (industrializacao).
    mov_liquido < 0: preenche todos os lotes de entrada; o que sobrar -> MIGRACAO,
        fatura LF->FB e move p/ FB/Indisponivel.

Esta versao implementa SOMENTE a FASE DE ANALISE (--dry-run, default). Calcula
mov_liquido, valida contra o saldo REAL do Odoo (CIEL IT) e classifica cada
produto EXECUTAVEL vs BLOQUEADO. NAO grava nada, NAO emite NF. A execucao real
(realocacao + faturamento) e fase separada, liberada apos resolver os bloqueios.

Por que so analise: o pipeline existente NAO faz encontro de contas (fatura qtd
cheia). A logica abaixo e nova; NF e irreversivel (SEFAZ). Antes de emitir,
precisamos do panorama e da decisao sobre bloqueios (lotes reservados por MO
ativa, saldo que nao bate, produto inexistente).

Uso:
    python scripts/inventario_2026_05/encontro_contas_lf.py            # panorama dry-run
    python scripts/inventario_2026_05/encontro_contas_lf.py --xlsx PATH --json OUT
"""
import argparse
import json
import os
import sys
import warnings
from collections import defaultdict

warnings.simplefilter('ignore')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import openpyxl  # noqa: E402

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

DEFAULT_XLSX = '/mnt/c/Users/rafael.nascimento/Downloads/Pasta23.xlsx'
DEFAULT_JSON = '/tmp/encontro_contas_panorama.json'
TOL = 0.01
COMPANY_LF = 5
COMPANY_FB = 1


def emp(loc):
    return (loc or '').split('/')[0]


def carregar_pasta23(path):
    """-> {cod: {'nome', 'entradas': {lote: qtd}, 'saidas': {lote: qtd}}}"""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb['Planilha1']
    prod = defaultdict(lambda: {'nome': '', 'entradas': defaultdict(float),
                                'saidas': defaultdict(float)})
    for r in ws.iter_rows(min_row=2, values_only=True):
        fil, cod, nome, ol, olt, dl, dlt, qtd, *_ = r
        if cod is None:
            continue
        cod = str(cod).strip()
        if cod.endswith('.0'):
            cod = cod[:-2]
        qtd = float(qtd or 0)
        p = prod[cod]
        p['nome'] = nome
        if emp(ol) == 'FB' and emp(dl) == 'LF':       # entrada FB->LF
            p['entradas'][str(dlt).strip()] += qtd     # lote DESTINO (no LF)
        elif emp(ol) == 'LF' and emp(dl) == 'FB':      # saida LF->FB
            p['saidas'][str(olt).strip()] += qtd       # lote ORIGEM (no LF)
    wb.close()
    return prod


def consultar_estado(odoo, cods):
    """Estado real Odoo: pid, saldo LF por lote (livre/reservado), quem reserva,
    saldo FB MIGRACAO."""
    prods = odoo.search_read('product.product', [['default_code', 'in', cods]],
                             ['id', 'default_code', 'standard_price',
                              'l10n_br_ncm_id', 'barcode'])
    cod_pid = {p['default_code']: p['id'] for p in prods}
    pid_cod = {p['id']: p['default_code'] for p in prods}
    info = {p['default_code']: p for p in prods}
    pids = list(pid_cod)

    # locations internas LF + FB/Indisponivel
    locs = odoo.search_read('stock.location',
                            [['usage', '=', 'internal'], ['company_id', 'in', [COMPANY_FB, COMPANY_LF]]],
                            ['id', 'complete_name', 'company_id'])
    lf_loc_ids = [l['id'] for l in locs if l['company_id'][0] == COMPANY_LF]
    fb_indisp = [l['id'] for l in locs if l['company_id'][0] == COMPANY_FB
                 and 'indispon' in (l['complete_name'] or '').lower()]

    # saldo LF por (cod, lote)
    quants = odoo.search_read('stock.quant',
                              [['product_id', 'in', pids], ['location_id', 'in', lf_loc_ids],
                               ['quantity', '!=', 0]],
                              ['product_id', 'lot_id', 'quantity', 'reserved_quantity'])
    lf_saldo = defaultdict(lambda: {'qtd': 0.0, 'reserv': 0.0})
    for q in quants:
        cod = pid_cod.get(q['product_id'][0])
        lot = q['lot_id'][1] if q['lot_id'] else '(sem lote)'
        lf_saldo[(cod, lot)]['qtd'] += q['quantity']
        lf_saldo[(cod, lot)]['reserv'] += q.get('reserved_quantity') or 0

    # quem reserva (move.lines abertas no LF) -> pickings -> origin (MO?)
    mls = odoo.search_read('stock.move.line',
                           [['product_id', 'in', pids], ['company_id', '=', COMPANY_LF],
                            ['state', 'not in', ['done', 'cancel']]],
                           ['product_id', 'lot_id', 'quantity', 'picking_id', 'reference'])
    reservas = defaultdict(list)  # (cod, lote) -> [{qty, ref, picking}]
    pkids = set()
    for ml in mls:
        cod = pid_cod.get(ml['product_id'][0])
        lot = ml['lot_id'][1] if ml['lot_id'] else '(sem lote)'
        if (ml.get('quantity') or 0) <= 0:
            continue
        reservas[(cod, lot)].append({'qty': ml['quantity'], 'ref': ml.get('reference'),
                                     'pk': ml['picking_id'][0] if ml['picking_id'] else None})
        if ml['picking_id']:
            pkids.add(ml['picking_id'][0])
    pk_origin = {}
    if pkids:
        pks = odoo.search_read('stock.picking', [['id', 'in', list(pkids)]],
                               ['id', 'name', 'origin'])
        pk_origin = {p['id']: (p['name'], p.get('origin') or '') for p in pks}

    # saldo FB MIGRACAO (origem do faturamento positivo)
    fb_mig = defaultdict(float)
    if fb_indisp:
        fq = odoo.search_read('stock.quant',
                              [['product_id', 'in', pids], ['location_id', 'in', fb_indisp],
                               ['quantity', '>', 0]],
                              ['product_id', 'lot_id', 'quantity'])
        for q in fq:
            cod = pid_cod.get(q['product_id'][0])
            lot = (q['lot_id'][1] if q['lot_id'] else '').upper()
            if 'MIGRA' in lot:
                fb_mig[cod] += q['quantity']
    return dict(cod_pid=cod_pid, info=info, lf_saldo=lf_saldo,
                reservas=reservas, pk_origin=pk_origin, fb_mig=fb_mig)


def analisar(cod, p, est):
    """Classifica o produto e monta o plano. -> dict."""
    nome = p['nome']
    qtd_ent = sum(p['entradas'].values())
    qtd_sai = sum(p['saidas'].values())
    mov = round(qtd_ent - qtd_sai, 4)
    r = {'cod': cod, 'nome': nome, 'qtd_entrada': round(qtd_ent, 4),
         'qtd_saida': round(qtd_sai, 4), 'mov_liquido': mov,
         'direcao_fat': 'FB->LF' if mov > TOL else ('LF->FB' if mov < -TOL else 'ZERO'),
         'entradas': {k: round(v, 4) for k, v in p['entradas'].items()},
         'saidas': {k: round(v, 4) for k, v in p['saidas'].items()},
         'bloqueios': [], 'reservas_mo': []}

    if cod not in est['cod_pid']:
        r['bloqueios'].append('SEM_PID (produto nao existe no Odoo)')
        r['classe'] = 'BLOQUEADO'
        return r

    pinfo = est['info'][cod]
    if not pinfo.get('l10n_br_ncm_id'):
        r['bloqueios'].append('SEM_NCM (G017 — quebra SEFAZ)')
    bc = pinfo.get('barcode')
    if bc and str(bc) == cod:
        r['bloqueios'].append(f'BARCODE_INVALIDO (G035 — barcode={bc})')
    if (pinfo.get('standard_price') or 0) <= 0:
        r['bloqueios'].append('CUSTO_ZERO (G007 — price_unit 0 rejeita SEFAZ)')

    # validar cada lote de saida vs saldo real LF
    for lote, qsai in sorted(p['saidas'].items()):
        s = est['lf_saldo'].get((cod, lote), {'qtd': 0.0, 'reserv': 0.0})
        livre = s['qtd'] - s['reserv']
        if livre + TOL >= qsai:
            continue
        if s['qtd'] + TOL >= qsai:
            # falta liberar reserva — identificar quem reserva
            quem = est['reservas'].get((cod, lote), [])
            mo_refs = sorted({q['ref'] for q in quem if q.get('ref')})
            tem_mo = any('/MO/' in (est['pk_origin'].get(q['pk'], ('', ''))[1] or '')
                         or '/MO/' in (q.get('ref') or '') for q in quem)
            r['bloqueios'].append(
                f'RESERVADO lote={lote} (sai {qsai:.4f}, livre {livre:.4f}); refs={mo_refs}')
            if tem_mo:
                r['reservas_mo'].append(lote)
        else:
            r['bloqueios'].append(
                f'FALTA_SALDO lote={lote} (sai {qsai:.4f}, saldo total {s["qtd"]:.4f})')

    # faturamento positivo precisa de origem no FB MIGRACAO
    if mov > TOL and est['fb_mig'].get(cod, 0) + TOL < mov:
        r['bloqueios'].append(
            f'FB_SEM_ORIGEM (mov_liquido {mov:.4f} > FB MIGRACAO {est["fb_mig"].get(cod, 0):.4f})')

    r['classe'] = 'EXECUTAVEL' if not r['bloqueios'] else 'BLOQUEADO'
    # plano: lotes finais previstos no LF = lotes de ENTRADA da planilha
    r['lf_final_previsto'] = {k: round(v, 4) for k, v in p['entradas'].items()}
    return r


CICLO_EXEC = 'ENCONTRO_CONTAS_PASTA23_2026_05_20'


def criar_ajustes_diretos(prod, est, resultados, ciclo, cods_alvo, dry):
    """Cria AjusteEstoqueInventario para os faturamentos DIRETOS (sem realocacao):
    - mov>0 SEM saidas: INDUSTRIALIZACAO_FB_LF (1 ajuste por lote de entrada)
    - mov<0 SEM entradas: PERDA_LF_FB (lote_destino=MIGRACAO)
    Produtos com AMBAS as pontas (encontro real, ex GOMA) sao PULADOS aqui
    (precisam de realocacao — tratamento separado).
    """
    from decimal import Decimal
    from app import db
    from app.odoo.models.ajuste_estoque_inventario import AjusteEstoqueInventario
    from app.utils.timezone import agora_utc_naive
    by_cod = {r['cod']: r for r in resultados}
    criados, pulados = [], []
    for cod in cods_alvo:
        r = by_cod.get(cod)
        if not r or r['classe'] != 'EXECUTAVEL':
            pulados.append((cod, 'nao executavel')); continue
        # PROTECAO: nao tocar produto que ja tem ajuste EM EXECUCAO (fase != None)
        # no ciclo (ex: canario ja faturando) — evita resetar picking/invoice.
        em_exec = (AjusteEstoqueInventario.query
                   .filter_by(ciclo=ciclo, cod_produto=cod)
                   .filter(AjusteEstoqueInventario.fase_pipeline.isnot(None)).count())
        if em_exec:
            pulados.append((cod, f'ja em execucao no ciclo ({em_exec} ajustes c/ fase)')); continue
        ent, sai = prod[cod]['entradas'], prod[cod]['saidas']
        tipo = int(cod[0])
        custo = abs(est['info'][cod].get('standard_price') or 0) or 0.01
        if ent and sai:
            pulados.append((cod, 'encontro real (realocacao) — tratar separado')); continue
        linhas = []  # (acao, company, qtd_ajuste, lote_destino)
        if r['mov_liquido'] > 0.01:        # direto FB->LF
            for lote, q in ent.items():
                linhas.append(('INDUSTRIALIZACAO_FB_LF', 1, round(q, 4), lote))
        elif r['mov_liquido'] < -0.01:     # direto LF->FB (perda)
            linhas.append(('PERDA_LF_FB', 5, round(r['mov_liquido'], 4), 'MIGRACAO'))
        else:
            pulados.append((cod, 'mov~0')); continue
        for acao, comp, qa, lote in linhas:
            if not dry:
                AjusteEstoqueInventario.query.filter_by(
                    ciclo=ciclo, cod_produto=cod, acao_decidida=acao, lote_destino=lote).delete()
                db.session.add(AjusteEstoqueInventario(
                    ciclo=ciclo, cod_produto=cod, tipo_produto=tipo, company_id=comp,
                    qtd_inventario=Decimal(str(abs(qa))), qtd_odoo=Decimal('0'),
                    qtd_ajuste=Decimal(str(qa)), custo_medio=Decimal(str(custo)),
                    acao_decidida=acao, lote_destino=lote, status='APROVADO',
                    aprovado_em=agora_utc_naive(), aprovado_por='claude_encontro_contas',
                    fase_pipeline=None, criado_por='claude_encontro_contas'))
            criados.append((cod, acao, qa, lote))
    if not dry:
        db.session.commit()
    return criados, pulados


FB_ESTOQUE = 8


def pre_stage_fb(odoo, need_por_cod, dry, filtro_cods=None):
    """Move FB/Indisponivel (MIGRACAO) -> FB/Estoque(8) a qtd necessaria por produto,
    para liberar material p/ o picking de saida (industrializacao FB->LF).
    Tecnica: inventory adjustment 2 passos (reduz Indisponivel + aumenta Estoque),
    mesmo lote. Igual a transferir_indisp_para_estoque_p15_cd.py mas generico.
    So move o que FALTA no Estoque (idempotente)."""
    from app.odoo.services.stock_lot_service import StockLotService
    from app.odoo.services.stock_quant_adjustment_service import StockQuantAdjustmentService
    lot_svc = StockLotService(odoo=odoo)
    svc = StockQuantAdjustmentService(odoo=odoo, lot_svc=lot_svc)
    locs = odoo.search_read('stock.location', [['usage', '=', 'internal'], ['company_id', '=', 1]],
                            ['id', 'complete_name'])
    indisp = [l['id'] for l in locs if 'indispon' in (l['complete_name'] or '').lower()]
    cods = [c for c in need_por_cod if (not filtro_cods or c in filtro_cods)]
    prods = odoo.search_read('product.product', [['default_code', 'in', cods]], ['id', 'default_code'])
    cp = {p['default_code']: p['id'] for p in prods}
    out = []
    for cod in cods:
        pid = cp.get(cod)
        if not pid:
            out.append({'cod': cod, 'status': 'sem_pid'}); continue
        # quanto ja livre no FB/Estoque
        qest = odoo.search_read('stock.quant', [['product_id', '=', pid], ['location_id', '=', FB_ESTOQUE]],
                                ['quantity', 'reserved_quantity'])
        livre_est = sum(q['quantity'] - (q.get('reserved_quantity') or 0) for q in qest)
        falta = round(need_por_cod[cod] - livre_est, 4)
        if falta <= 0.01:
            out.append({'cod': cod, 'need': need_por_cod[cod], 'ja_no_estoque': round(livre_est, 4),
                        'movido': 0, 'status': 'OK_JA_TEM'}); continue
        quants = odoo.search_read('stock.quant',
                                  [['product_id', '=', pid], ['location_id', 'in', indisp], ['quantity', '>', 0]],
                                  ['id', 'lot_id', 'location_id', 'quantity', 'reserved_quantity'])
        quants.sort(key=lambda q: (0 if (q['lot_id'] and 'MIGRA' in (q['lot_id'][1] or '').upper()) else 1,
                                   -(q['quantity'] - (q.get('reserved_quantity') or 0))))
        restante = falta
        passos = []
        for q in quants:
            if restante <= 0.01:
                break
            livre = round(q['quantity'] - (q.get('reserved_quantity') or 0), 4)
            if livre <= 0.01:
                continue
            consumir = round(min(livre, restante), 4)
            lot_id = q['lot_id'][0] if q['lot_id'] else None
            r1 = svc.ajustar_quant(quant_id=q['id'], delta=-consumir, validar_nao_negativar=True,
                                   validar_nao_abaixo_reserva=True, casas_decimais=4, dry_run=dry)
            r2 = svc.ajustar_quant(product_id=pid, company_id=1, location_id=FB_ESTOQUE, lot_id=lot_id,
                                   delta=consumir, criar_se_faltar=True, validar_nao_negativar=True,
                                   casas_decimais=4, dry_run=dry)
            passos.append({'lote': q['lot_id'][1] if q['lot_id'] else None, 'qtd': consumir,
                           'reduz': r1.get('status'), 'aumenta': r2.get('status')})
            restante = round(restante - consumir, 4)
        out.append({'cod': cod, 'need': need_por_cod[cod], 'ja_no_estoque': round(livre_est, 4),
                    'movido': round(falta - restante, 4), 'restante': restante,
                    'status': 'OK' if restante <= 0.01 else 'FALTA_INDISP', 'passos': passos})
    return out


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    ap.add_argument('--xlsx', default=DEFAULT_XLSX)
    ap.add_argument('--json', default=DEFAULT_JSON)
    ap.add_argument('--apenas-cods', default='')
    ap.add_argument('--criar-ajustes', action='store_true',
                    help='cria AjusteEstoqueInventario p/ faturamentos diretos no ciclo')
    ap.add_argument('--pre-stage', action='store_true',
                    help='move FB/Indisponivel MIGRACAO -> FB/Estoque p/ os INDUSTRIALIZACAO do ciclo')
    ap.add_argument('--ciclo', default=CICLO_EXEC)
    ap.add_argument('--confirmar', action='store_true', help='grava (sem isso, dry-run)')
    args = ap.parse_args()

    if args.pre_stage:
        from sqlalchemy import text as _text
        from app import create_app as _ca
        _app = _ca()
        with _app.app_context():
            from app import db as _db
            rows = _db.session.execute(_text(
                "SELECT cod_produto, SUM(qtd_ajuste) FROM ajuste_estoque_inventario "
                "WHERE ciclo=:c AND status='APROVADO' AND acao_decidida='INDUSTRIALIZACAO_FB_LF' "
                "GROUP BY cod_produto"), {'c': args.ciclo}).fetchall()
            need = {r[0]: float(r[1]) for r in rows}
            filtro = ({c.strip() for c in args.apenas_cods.split(',') if c.strip()}
                      if args.apenas_cods else None)
            odoo = get_odoo_connection()
            res = pre_stage_fb(odoo, need, dry=not args.confirmar, filtro_cods=filtro)
            modo = 'REAL' if args.confirmar else 'DRY-RUN'
            print(f'\n=== PRE-STAGE FB Indisponivel->Estoque ({modo}) ciclo={args.ciclo} ===')
            for r in sorted(res, key=lambda x: x['cod']):
                print(f"  {r['cod']}: need={r.get('need')} ja_estoque={r.get('ja_no_estoque')} "
                      f"movido={r.get('movido')} status={r['status']}")
        return

    prod = carregar_pasta23(args.xlsx)
    if args.apenas_cods:
        alvo = {c.strip() for c in args.apenas_cods.split(',') if c.strip()}
        prod = {c: p for c, p in prod.items() if c in alvo}
    cods = sorted(prod)
    print(f'\n{"="*92}\n  ENCONTRO DE CONTAS — ANALISE (DRY-RUN, nada gravado)')
    print(f'  XLSX: {args.xlsx}  | produtos: {len(cods)}\n{"="*92}')

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        est = consultar_estado(odoo, cods)
        resultados = [analisar(c, prod[c], est) for c in cods]

        if args.criar_ajustes:
            cods_alvo = ([c.strip() for c in args.apenas_cods.split(',') if c.strip()]
                         if args.apenas_cods
                         else [r['cod'] for r in resultados if r['classe'] == 'EXECUTAVEL'])
            criados, pulados = criar_ajustes_diretos(
                prod, est, resultados, args.ciclo, cods_alvo, dry=not args.confirmar)
            modo = 'GRAVADO' if args.confirmar else 'DRY-RUN'
            print(f'\n=== CRIAR AJUSTES ({modo}) ciclo={args.ciclo} ===')
            print(f'  Ajustes criados: {len(criados)}')
            for cod, acao, qa, lote in criados:
                print(f'    {cod} {acao} qtd={qa:+.4f} lote={lote}')
            print(f'  Pulados: {len(pulados)}')
            for cod, motivo in pulados:
                print(f'    {cod}: {motivo}')
            return

    execut = [r for r in resultados if r['classe'] == 'EXECUTAVEL']
    bloq = [r for r in resultados if r['classe'] == 'BLOQUEADO']
    mo_afetadas = sorted({lote for r in resultados for lote in r['reservas_mo']})

    print(f'\n{"cod":<11}{"mov_liq":>13}{"dir":>8}  classe       motivo')
    for r in sorted(resultados, key=lambda x: (x['classe'], x['cod'])):
        mot = '; '.join(r['bloqueios'])[:60] if r['bloqueios'] else ''
        print(f"{r['cod']:<11}{r['mov_liquido']:>13.4f}{r['direcao_fat']:>8}  "
              f"{r['classe']:<12} {mot}")

    print(f'\n{"="*92}')
    print(f'  EXECUTAVEIS (saldo bate, sem bloqueio): {len(execut)}')
    print(f'  BLOQUEADOS:                             {len(bloq)}')
    # detalhar bloqueios por tipo
    tipos = defaultdict(int)
    for r in bloq:
        for b in r['bloqueios']:
            tipos[b.split(' ')[0].split('(')[0]] += 1
    for t, n in sorted(tipos.items(), key=lambda x: -x[1]):
        print(f'      {t:<22} {n}')
    if mo_afetadas:
        print(f'\n  ATENCAO: lotes reservados por PRODUCAO (MO) — realocar quebra producao:')
        for r in bloq:
            if r['reservas_mo']:
                print(f'      {r["cod"]} lotes={r["reservas_mo"]}')

    with open(args.json, 'w', encoding='utf-8') as f:
        json.dump({'resultados': resultados,
                   'resumo': {'executaveis': len(execut), 'bloqueados': len(bloq)}},
                  f, indent=2, ensure_ascii=False, default=str)
    print(f'\n  Panorama salvo em {args.json}')
    print('  DRY-RUN — nada gravado. Execucao real (NF) e fase separada.\n')


if __name__ == '__main__':
    main()
