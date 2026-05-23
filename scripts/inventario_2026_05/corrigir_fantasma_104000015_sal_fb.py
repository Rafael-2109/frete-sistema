"""Corrigir estoque fantasma do lote 027-098/26 SAL SEM IODO (104000015) na FB.

CONTEXTO (2026-05-21):
    O script consolidar_lote_104000015_sal_fb.py rodou. A Op2 (aumentar a grafia
    'MI 027-098/26' na Linha Salmoura, que estava NEGATIVA em -1203,94) acionou
    um comportamento defeituoso do action_apply_inventory do Odoo: ao aumentar um
    quant negativo, o saldo final ficou +877,175 acima do esperado (quant=+550,41
    quando deveria ser -326,76). O total do lote subiu de 3.676,28 -> 4.553,46
    (estoque fantasma). Confirmado: quant nao bate com a soma das proprias moves.

OBJETIVO (autorizado pelo usuario):
    Reduzir os quants da grafia MI aos valores corretos (REDUCAO de quant POSITIVO
    -> nao dispara o bug; nunca usa inventory_quantity negativo):
        - MI@Linha Salmoura: 550,41 -> 0
        - MI@FB/Estoque:     3879,50 -> 3552,74
    Resultado: total do lote volta a 3.676,28 (saldo pre-operacao), Linha zerada.

SEGURANCA:
    - Aborta se houver movimentacao de producao NOVA no lote desde a operacao
      (timestamp de corte) — para nao corrigir sobre estado alterado.
    - Aplica 1 reducao por vez e RELE o quant; aborta se nao bater o alvo
      (deteccao de reincidencia do bug).

Uso:
    python scripts/inventario_2026_05/corrigir_fantasma_104000015_sal_fb.py            # dry-run
    python scripts/inventario_2026_05/corrigir_fantasma_104000015_sal_fb.py --confirmar
"""
import argparse
import logging
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(level=logging.WARNING)

PROD_ID = 27918
COMPANY_ID = 1
LOT_MI = 53776                 # 'MI 027-098/26'
LOT_SEM = 57478                # '027-098/26'
FB_ESTOQUE = 8
LINHA_SALMOURA = 27458
TOTAL_ALVO_LOTE = 3676.2836    # snapshot pre-operacao (17:09 2026-05-21)
ALVO_LINHA = 0.0
CORTE_MOVES = '2026-05-21 17:09:39'   # apos a ultima move da consolidacao
TOL = 0.01


def banner(t, c='='):
    print(f'\n{c*78}\n  {t}\n{c*78}')


def buscar_quant(odoo, loc, lot):
    qs = odoo.search_read('stock.quant',
        [['product_id','=',PROD_ID],['company_id','=',COMPANY_ID],
         ['location_id','=',loc],['lot_id','=',lot]],
        ['id','quantity','reserved_quantity'])
    if not qs:
        return None
    return qs[0]


def soma_moves(odoo, loc, lot):
    mls = odoo.search_read('stock.move.line',
        [['product_id','=',PROD_ID],['lot_id','=',lot],['state','=','done'],
         '|',['location_id','=',loc],['location_dest_id','=',loc]],
        ['quantity','location_id','location_dest_id'], limit=500)
    s = 0.0
    for m in mls:
        src = m['location_id'][0] if m['location_id'] else 0
        dst = m['location_dest_id'][0] if m['location_dest_id'] else 0
        s += m['quantity'] if dst == loc else (-m['quantity'] if src == loc else 0)
    return round(s, 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true')
    args = ap.parse_args()
    dry = not args.confirmar

    banner('CORRIGIR FANTASMA — lote 027-098/26 SAL SEM IODO (104000015) FB')
    print(f'  Modo: {"DRY-RUN" if dry else ">>> EXECUTAR <<<"}')

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()

        # 1. CHECK producao concorrente
        novas = odoo.search_read('stock.move.line',
            [['product_id','=',PROD_ID],['lot_id','in',[LOT_MI,LOT_SEM]],
             ['state','=','done'],['date','>',CORTE_MOVES]],
            ['id','date','quantity','reference'], limit=20)
        if novas:
            print(f'\n!! {len(novas)} move(s) NOVA(s) desde {CORTE_MOVES} — producao mexeu no lote:')
            for m in novas:
                print(f"   {str(m['date'])[:19]} qty={m['quantity']} ref={m.get('reference')}")
            print('!! ABORTANDO — recalcular alvos antes de corrigir.')
            return 2
        print(f'  OK: nenhuma move nova desde {CORTE_MOVES} (estado estavel).')

        # 2. Estado fresco
        q_lin = buscar_quant(odoo, LINHA_SALMOURA, LOT_MI)
        q_est = buscar_quant(odoo, FB_ESTOQUE, LOT_MI)
        if not q_lin or not q_est:
            print('!! quant MI@Linha ou MI@Est nao encontrado — abortando.')
            return 3
        q_sem_est = buscar_quant(odoo, FB_ESTOQUE, LOT_SEM)
        q_sem_lin = buscar_quant(odoo, LINHA_SALMOURA, LOT_SEM)
        sem_total = (q_sem_est['quantity'] if q_sem_est else 0) + \
                    (q_sem_lin['quantity'] if q_sem_lin else 0)
        alvo_est = round(TOTAL_ALVO_LOTE - sem_total - ALVO_LINHA, 4)

        print('\n--- ESTADO ATUAL ---')
        print(f"  MI@Linha   : quant={q_lin['quantity']:.4f}  (soma_moves={soma_moves(odoo,LINHA_SALMOURA,LOT_MI):.4f})  -> ALVO {ALVO_LINHA:.4f}")
        print(f"  MI@Estoque : quant={q_est['quantity']:.4f}  (soma_moves={soma_moves(odoo,FB_ESTOQUE,LOT_MI):.4f})  -> ALVO {alvo_est:.4f}")
        print(f"  sem-MI total (reservas, intocado): {sem_total:.4f}")
        print(f"  TOTAL lote atual={q_lin['quantity']+q_est['quantity']+sem_total:.4f}  ALVO={TOTAL_ALVO_LOTE:.4f}")

        # Sanidade: ambos alvos devem ser REDUCOES de quant positivo e nao-negativos
        for nome, q, alvo in [('MI@Linha', q_lin, ALVO_LINHA), ('MI@Estoque', q_est, alvo_est)]:
            if alvo < -TOL:
                print(f'!! ALVO {nome} negativo ({alvo}) — abortando (nao usar inv_qty negativo).')
                return 3
            if q['quantity'] + TOL < alvo:
                print(f'!! {nome}: alvo {alvo} > atual {q["quantity"]} (seria AUMENTO) — abortando.')
                return 3

        if dry:
            banner('DRY-RUN — nada gravado. Rode com --confirmar.')
            return 0

        # 3. Reduzir MI@Linha -> 0  (com verificacao)
        banner('Passo 1 — MI@Linha Salmoura -> 0', '-')
        odoo.write('stock.quant', [q_lin['id']], {'inventory_quantity': ALVO_LINHA})
        odoo.execute_kw('stock.quant', 'action_apply_inventory', [[q_lin['id']]])
        v = buscar_quant(odoo, LINHA_SALMOURA, LOT_MI)
        vq = v['quantity'] if v else 0.0
        print(f'  pos-ajuste: quant={vq:.4f} (alvo {ALVO_LINHA:.4f})')
        if abs(vq - ALVO_LINHA) > TOL:
            print('!! BUG REINCIDIU — quant nao bate o alvo. ABORTANDO antes do passo 2.')
            return 4
        print('  OK.')

        # 4. Reduzir MI@Estoque -> alvo_est  (com verificacao)
        banner('Passo 2 — MI@FB/Estoque -> alvo', '-')
        odoo.write('stock.quant', [q_est['id']], {'inventory_quantity': alvo_est})
        odoo.execute_kw('stock.quant', 'action_apply_inventory', [[q_est['id']]])
        v = buscar_quant(odoo, FB_ESTOQUE, LOT_MI)
        vq = v['quantity'] if v else 0.0
        print(f'  pos-ajuste: quant={vq:.4f} (alvo {alvo_est:.4f})')
        if abs(vq - alvo_est) > TOL:
            print('!! quant nao bate o alvo. Verificar manualmente.')
            return 4
        print('  OK.')

        # 5. Validacao final
        banner('VALIDACAO FINAL')
        q_lin2 = buscar_quant(odoo, LINHA_SALMOURA, LOT_MI)
        q_est2 = buscar_quant(odoo, FB_ESTOQUE, LOT_MI)
        total = (q_lin2['quantity'] if q_lin2 else 0) + (q_est2['quantity'] if q_est2 else 0) + sem_total
        print(f"  MI@Linha={q_lin2['quantity'] if q_lin2 else 0:.4f}  MI@Est={q_est2['quantity'] if q_est2 else 0:.4f}  sem-MI={sem_total:.4f}")
        print(f"  TOTAL lote={total:.4f}  (alvo {TOTAL_ALVO_LOTE:.4f})  diff={total-TOTAL_ALVO_LOTE:+.4f}")
        if abs(total - TOTAL_ALVO_LOTE) <= TOL:
            print('  >> OK: fantasma removido, total do lote restaurado.')
        else:
            print('  >> ATENCAO: total ainda divergente — revisar.')
        return 0


if __name__ == '__main__':
    sys.exit(main())
