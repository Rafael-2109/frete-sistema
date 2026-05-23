#!/usr/bin/env python3
"""Desfaz ajustes de inventario que criaram estoque INDEVIDO na LF (La Famiglia).

CONTEXTO
--------
Em 09/04/2026 a usuaria Maria Aparecida (uid 1257) aplicou ajustes de inventario
(is_inventory=True, sem picking/origin) que CRIARAM saldo no lote 099/26 de
produtos LA FAMIGLIA em LF/Estoque (loc 42). Esse estoque nunca deveria existir
na LF. Tentativas posteriores de "expulsar" via remessa/retorno de
industrializacao (SAI/IND <-> RECEB/IND, 18-19/05) deixaram o saldo de volta.
O saldo liquido GLOBAL do lote ja e 0 (loc 42 positivo + loc 38 negativo).

Produtos alvo (default):
  4329301 [36476] AZEITONA VERDE FATIADA   POUCH 24X100 GR LF — ajuste 09/04: 336 (move 1047069)
  4369301 [36477] AZEITONA VERDE SEM CAROCO POUCH 24X100 GR LF — ajuste 09/04: 224+276=500 (1047057,1047060)

ACAO
----
Para cada produto, zerar TODO quant POSITIVO em LF/Estoque (child_of 41) via
inventory adjustment (valor_absoluto=0). O Odoo gera stock.move loc42 -> loc38;
a contrapartida virtual negativa (loc 38) sobe para 0. Resultado: produto sem
saldo na LF e contrapartida zerada.

SEGURANCA (gotcha SAL 104000015 — quant negativo)
- So REDUZIMOS quants POSITIVOS (LF/Estoque). Reduzir positivo e seguro.
- NUNCA aplicamos inventory adjustment sobre a loc 38 (negativa) — ela e apenas
  destino da move automatica (soma corretamente).
- Aborta o produto se houver reserva (>0) ou movimentacao pendente (nao-done).
- Valida pos-execucao: saldo LF do lote == 0 e contrapartida (loc 38) == 0.

Uso:
  python desfazer_ajustes_indevidos_lf.py                       # DRY-RUN (default)
  python desfazer_ajustes_indevidos_lf.py --executar            # aplica
  python desfazer_ajustes_indevidos_lf.py --produtos 4329301    # subconjunto
"""
import argparse
import sys

sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')

from app.odoo.utils.connection import get_odoo_connection
from app.odoo.services.stock_quant_adjustment_service import StockQuantAdjustmentService

COMPANY_LF = 5
LF_VIEW = 41
LOC_AJUSTE = 38          # Estoque Virtual/Ajuste de Estoque (contrapartida)
TOL = 0.001
PRODUTOS_DEFAULT = ['4329301', '4369301']
ESTADOS_PENDENTES = ['draft', 'waiting', 'confirmed', 'partially_available', 'assigned']


def m2o(v):
    return f"{v[0]}:{v[1]}" if (v and isinstance(v, (list, tuple))) else str(v)


def processar_produto(odoo, svc, cod, dry):
    print('\n' + '=' * 78)
    print(f'PRODUTO {cod}  ({"DRY-RUN" if dry else "EXECUCAO REAL"})')
    print('=' * 78)
    prods = odoo.search_read('product.product', [['default_code', '=', cod]],
                             ['id', 'name'])
    if not prods:
        print(f'  !! produto {cod} nao encontrado — pulando.')
        return {'cod': cod, 'status': 'NAO_ENCONTRADO'}
    pid = prods[0]['id']
    print(f'  id={pid} | {prods[0]["name"]}')

    # quants LF (child_of 41) e contrapartida (loc 38)
    quants_lf = odoo.search_read('stock.quant',
        [['product_id', '=', pid], ['location_id', 'child_of', LF_VIEW]],
        ['id', 'location_id', 'lot_id', 'quantity', 'reserved_quantity'])
    quants_aj = odoo.search_read('stock.quant',
        [['product_id', '=', pid], ['location_id', '=', LOC_AJUSTE]],
        ['id', 'location_id', 'lot_id', 'quantity'])

    print('  QUANTS LF:')
    for q in quants_lf:
        print(f'    {m2o(q["location_id"]):<40} lote={m2o(q.get("lot_id")):<14} '
              f'qty={q["quantity"]:>9.3f} reservado={q.get("reserved_quantity"):>7.3f}')
    print('  CONTRAPARTIDA (loc 38 Ajuste virtual):')
    for q in quants_aj:
        print(f'    lote={m2o(q.get("lot_id")):<14} qty={q["quantity"]:>9.3f}')

    # pendencias
    pend = odoo.search_read('stock.move',
        ['&', '&', ['product_id', '=', pid], ['state', 'in', ESTADOS_PENDENTES],
         '|', ['location_dest_id', 'child_of', LF_VIEW], ['location_id', 'child_of', LF_VIEW]],
        ['id', 'state', 'reference'])
    if pend:
        print(f'  !! {len(pend)} MOVE(S) PENDENTE(S) — ABORTANDO produto (risco de reserva):')
        for m in pend:
            print(f'      move={m["id"]} state={m["state"]} ref={m.get("reference")}')
        return {'cod': cod, 'status': 'ABORTADO_PENDENTE', 'pendentes': len(pend)}

    alvos = [q for q in quants_lf if q['quantity'] > TOL]
    com_reserva = [q for q in alvos if (q.get('reserved_quantity') or 0) > TOL]
    if com_reserva:
        print('  !! quant(s) com reserva > 0 — ABORTANDO produto (cancelar pickings antes):')
        for q in com_reserva:
            print(f'      quant={q["id"]} reservado={q["reserved_quantity"]}')
        return {'cod': cod, 'status': 'ABORTADO_RESERVA'}

    total_alvo = sum(q['quantity'] for q in alvos)
    print(f'  >>> A ZERAR: {len(alvos)} quant(s), total {total_alvo} un')

    resultados = []
    for q in alvos:
        res = svc.ajustar_quant(quant_id=q['id'], valor_absoluto=0,
                                validar_nao_negativar=True,
                                validar_nao_abaixo_reserva=True, dry_run=dry)
        print(f'    quant={q["id"]} lote={m2o(q.get("lot_id"))} '
              f'{q["quantity"]} -> 0 | status={res["status"]} '
              f'ajuste={res.get("ajuste_aplicado")}')
        resultados.append(res)

    # validacao pos
    if not dry:
        pos_lf = odoo.search_read('stock.quant',
            [['product_id', '=', pid], ['location_id', 'child_of', LF_VIEW]],
            ['location_id', 'lot_id', 'quantity'])
        pos_aj = odoo.search_read('stock.quant',
            [['product_id', '=', pid], ['location_id', '=', LOC_AJUSTE]],
            ['lot_id', 'quantity'])
        saldo_lf = sum(q['quantity'] for q in pos_lf)
        saldo_aj = sum(q['quantity'] for q in pos_aj)
        print(f'  POS: saldo LF={saldo_lf} (esperado 0) | contrapartida loc38={saldo_aj} (esperado 0)')
        ok = abs(saldo_lf) < TOL and abs(saldo_aj) < TOL
        print('  ✓ DESFEITO OK' if ok else '  !! NAO ZEROU — INVESTIGAR (possivel fantasma)')
        return {'cod': cod, 'status': 'EXECUTADO' if ok else 'POS_DIVERGENTE',
                'zerado': total_alvo, 'saldo_lf_pos': saldo_lf, 'saldo_aj_pos': saldo_aj}

    return {'cod': cod, 'status': 'DRY_RUN_OK', 'a_zerar': total_alvo}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--executar', action='store_true', help='aplica (sem flag = dry-run)')
    ap.add_argument('--produtos', nargs='+', default=PRODUTOS_DEFAULT,
                    help='default_codes (default: 4329301 4369301)')
    args = ap.parse_args()
    dry = not args.executar

    odoo = get_odoo_connection()
    if not odoo.authenticate():
        print('FALHA AUTH'); return 1
    svc = StockQuantAdjustmentService(odoo=odoo)

    print(f'### DESFAZER AJUSTES INDEVIDOS LF — {"DRY-RUN" if dry else "EXECUCAO REAL"} ###')
    print(f'### Produtos: {", ".join(args.produtos)}')
    resumo = [processar_produto(odoo, svc, cod, dry) for cod in args.produtos]

    print('\n' + '#' * 78)
    print('RESUMO')
    for r in resumo:
        print(f'  {r["cod"]}: {r["status"]} '
              + (f'(a_zerar={r.get("a_zerar")})' if dry else f'(zerado={r.get("zerado")})'))
    print('#' * 78)
    print('\n' + ('(DRY-RUN — nada escrito. Rode com --executar para aplicar.)'
                  if dry else 'EXECUCAO CONCLUIDA.'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
