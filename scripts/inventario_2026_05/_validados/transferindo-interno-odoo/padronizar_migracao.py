# etapa: validado
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""Padronizacao 'MIGRACAO' (sem cedilha) -> 'MIGRAÇÃO' (com cedilha + til).

Motivo: o piloto 210030325 LF (2026-05-18) criou na FB um lote NOVO
chamado 'MIGRACAO' (sem cedilha) com 66.532 un, ao lado do lote
'MIGRAÇÃO' (com cedilha) historico que ja tinha 162.819 un. Para
manter D005 ("MIGRAÇÃO consolida fantasmas — 1 lote por produto"),
toda referencia precisa apontar para 'MIGRAÇÃO' (forma com cedilha).

Acoes:
  1. Transferir 66.532 un do lot 56534 (MIGRACAO) → lot 30400 (MIGRAÇÃO)
     na FB/Estoque produto 28239 via StockInternalTransferService.
  2. UPDATE ajuste_estoque_inventario SET lote_destino='MIGRAÇÃO'
     WHERE lote_destino='MIGRACAO' AND ciclo='INVENTARIO_2026_05'.
     (1.236 linhas afetadas estimadas)
  3. UPDATE recebimento_lf_lote SET lote_nome='MIGRAÇÃO'
     WHERE lote_nome='MIGRACAO'.
     (1 linha — id=60 do piloto)
  4. (Manual via Edit) atualizar constantes em scripts/inventario_2026_05/*.py
     e docs/inventario-2026-05/00-decisoes/D005-...md

Idempotencia: re-executar e seguro (transferencia: 0 un se ja foi feita;
UPDATEs: 0 linhas se ja convertidos).

Flags:
  --dry-run    (default) mostra plano
  --confirmar  executa transferencia + UPDATEs

Uso:
  python scripts/inventario_2026_05/padronizar_migracao.py --dry-run
  python scripts/inventario_2026_05/padronizar_migracao.py --confirmar --usuario=rafael
"""
import argparse
import logging
import sys
from pathlib import Path

# Arquivado: este script vivia em scripts/inventario_2026_05/ — agora em _validados/transferindo-interno-odoo/
# Profundidade aumentou 2 niveis -> parents[4] (em vez de parents[2]).
# Script preservado como museum vivo (ainda executavel). Para fluxo novo, usar a skill:
#   .claude/skills/transferindo-interno-odoo/scripts/transferir.py
# LIMITACAO documentada: consolidacao de 2 grafias ESPECIFICAS de MIGRACAO (sem cedilha
# -> com cedilha, ambas literais e existentes) NAO e coberta pela skill atual via nomes —
# requer --lot-id (futuro). Use lot_id direto OU o service quant.py.
_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[4]))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402  # type: ignore
from app.odoo.services.stock_internal_transfer_service import (  # noqa: E402  # type: ignore
    StockInternalTransferService,
)
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('padronizar_migracao')

# Constantes piloto
PRODUCT_ID = 28239           # cod 210030325
COMPANY_FB = 1
LOC_FB_ESTOQUE = 8
LOT_ID_MIGRACAO_SEM = 56534  # MIGRACAO (criado pelo piloto, sem cedilha)
LOT_ID_MIGRACAO_COM = 30400  # MIGRAÇÃO (historico, com cedilha)
QTY_PILOTO = 66532.0


def banner(titulo: str, char: str = '='):
    print()
    print(char * 78)
    print(f'  {titulo}')
    print(char * 78)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--confirmar', action='store_true')
    parser.add_argument('--usuario', default='padronizar')
    args = parser.parse_args()
    dry_run = not args.confirmar

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        banner(f'PADRONIZAR MIGRAÇÃO (modo={"DRY-RUN" if dry_run else "REAL"})')

        # 1. Verificar estado atual dos quants
        banner('1. Estado atual dos lotes MIGRA* na FB (produto 28239)', '-')
        quants = odoo.search_read(
            'stock.quant',
            [
                ['product_id', '=', PRODUCT_ID],
                ['company_id', '=', COMPANY_FB],
                ['location_id', '=', LOC_FB_ESTOQUE],
                ['lot_id', 'in', [LOT_ID_MIGRACAO_SEM, LOT_ID_MIGRACAO_COM]],
            ],
            ['id', 'lot_id', 'quantity', 'reserved_quantity'],
        )
        for q in quants:
            lot_id = q['lot_id'][0] if q.get('lot_id') else None
            lot_name = q['lot_id'][1] if q.get('lot_id') else '?'
            print(f"  quant {q['id']:>6}  lot=[{lot_id}] {lot_name!r}  "
                  f"qty={q['quantity']:>10}  res={q['reserved_quantity']}")
        qty_sem = next(
            (q['quantity'] for q in quants
             if q.get('lot_id') and q['lot_id'][0] == LOT_ID_MIGRACAO_SEM),
            0,
        )
        qty_com = next(
            (q['quantity'] for q in quants
             if q.get('lot_id') and q['lot_id'][0] == LOT_ID_MIGRACAO_COM),
            0,
        )
        print(f'  MIGRACAO (sem cedilha, lot_id={LOT_ID_MIGRACAO_SEM}): {qty_sem} un')
        print(f'  MIGRAÇÃO (com cedilha, lot_id={LOT_ID_MIGRACAO_COM}): {qty_com} un')

        # 2. Contar UPDATEs pendentes em DB
        banner('2. UPDATEs pendentes no DB local', '-')
        n_aj = db.session.execute(text(
            "SELECT COUNT(*) FROM ajuste_estoque_inventario "
            "WHERE lote_destino = 'MIGRACAO' AND ciclo = 'INVENTARIO_2026_05'"
        )).scalar()
        print(f"  ajuste_estoque_inventario: {n_aj} linhas com lote_destino='MIGRACAO' "
              "(serao mudadas para 'MIGRAÇÃO')")

        n_aj_lote_origem = db.session.execute(text(
            "SELECT COUNT(*) FROM ajuste_estoque_inventario "
            "WHERE lote_origem = 'MIGRACAO' AND ciclo = 'INVENTARIO_2026_05'"
        )).scalar()
        print(f"  ajuste_estoque_inventario: {n_aj_lote_origem} linhas com "
              "lote_origem='MIGRACAO' (NAO seraosmudadas — sao referencias historicas a quant origem)")

        n_rec_lote = db.session.execute(text(
            "SELECT COUNT(*) FROM recebimento_lf_lote WHERE lote_nome = 'MIGRACAO'"
        )).scalar()
        print(f"  recebimento_lf_lote: {n_rec_lote} linhas com lote_nome='MIGRACAO' "
              "(serao mudadas para 'MIGRAÇÃO')")

        # 3. Plano
        banner('3. Plano', '-')
        print(f'  A. Odoo: transferir {qty_sem} un do lot {LOT_ID_MIGRACAO_SEM} '
              f'(MIGRACAO) -> lot {LOT_ID_MIGRACAO_COM} (MIGRAÇÃO) na FB/Estoque')
        print(f'     Resultado: lot {LOT_ID_MIGRACAO_COM} fica com {qty_com + qty_sem} un, '
              f'lot {LOT_ID_MIGRACAO_SEM} fica zerado')
        print(f'  B. DB: UPDATE ajuste_estoque_inventario SET lote_destino=\'MIGRAÇÃO\' '
              f'WHERE lote_destino=\'MIGRACAO\' AND ciclo=\'INVENTARIO_2026_05\' '
              f'({n_aj} linhas)')
        print(f'  C. DB: UPDATE recebimento_lf_lote SET lote_nome=\'MIGRAÇÃO\' '
              f'WHERE lote_nome=\'MIGRACAO\' ({n_rec_lote} linhas)')
        print(f'  D. (Pos-script, manual) Edit constantes em codigo .py + D005.md')

        if dry_run:
            print('\n  [DRY-RUN] nada sera alterado. Use --confirmar.')
            return

        # 4. Execucao
        banner('4. Executando', '-')

        # A. Transferencia Odoo
        if qty_sem > 0:
            print(f'  A. Transferindo {qty_sem} un no Odoo...')
            svc = StockInternalTransferService(odoo=odoo)
            res = svc.transferir_entre_lotes(
                product_id=PRODUCT_ID,
                company_id=COMPANY_FB,
                location_id=LOC_FB_ESTOQUE,
                qty=qty_sem,
                lot_id_origem=LOT_ID_MIGRACAO_SEM,
                lot_id_destino=LOT_ID_MIGRACAO_COM,
            )
            print(f'     OK. quant_origem {res["quant_origem_id"]}: '
                  f'{res["quant_origem_qty_antes"]} -> {res["quant_origem_qty_apos"]}')
            print(f'     quant_destino {res["quant_destino_id"]}: '
                  f'{res["quant_destino_qty_antes"]} -> {res["quant_destino_qty_apos"]}')
        else:
            print('  A. SKIP — qty_sem=0 (transferencia ja feita).')

        # B. UPDATE ajustes
        if n_aj:
            print(f'  B. UPDATE ajuste_estoque_inventario ({n_aj} linhas)...')
            r = db.session.execute(text(
                "UPDATE ajuste_estoque_inventario "
                "SET lote_destino = 'MIGRAÇÃO' "
                "WHERE lote_destino = 'MIGRACAO' AND ciclo = 'INVENTARIO_2026_05'"
            ))
            print(f'     {r.rowcount} linhas atualizadas')
        else:
            print('  B. SKIP — 0 linhas com lote_destino=MIGRACAO.')

        # C. UPDATE recebimento_lf_lote
        if n_rec_lote:
            print(f'  C. UPDATE recebimento_lf_lote ({n_rec_lote} linhas)...')
            r = db.session.execute(text(
                "UPDATE recebimento_lf_lote "
                "SET lote_nome = 'MIGRAÇÃO' "
                "WHERE lote_nome = 'MIGRACAO'"
            ))
            print(f'     {r.rowcount} linhas atualizadas')
        else:
            print('  C. SKIP — 0 linhas com lote_nome=MIGRACAO.')

        db.session.commit()

        # 5. Estado final
        banner('5. Estado final (validacao)', '=')
        quants_final = odoo.search_read(
            'stock.quant',
            [
                ['product_id', '=', PRODUCT_ID],
                ['company_id', '=', COMPANY_FB],
                ['location_id', '=', LOC_FB_ESTOQUE],
                ['lot_id', 'in', [LOT_ID_MIGRACAO_SEM, LOT_ID_MIGRACAO_COM]],
            ],
            ['id', 'lot_id', 'quantity'],
        )
        for q in quants_final:
            lot_id = q['lot_id'][0] if q.get('lot_id') else None
            lot_name = q['lot_id'][1] if q.get('lot_id') else '?'
            print(f"  quant {q['id']:>6}  lot=[{lot_id}] {lot_name!r}  qty={q['quantity']}")

        n_aj_pos = db.session.execute(text(
            "SELECT COUNT(*) FROM ajuste_estoque_inventario "
            "WHERE lote_destino = 'MIGRACAO' AND ciclo = 'INVENTARIO_2026_05'"
        )).scalar()
        n_aj_pos_com = db.session.execute(text(
            "SELECT COUNT(*) FROM ajuste_estoque_inventario "
            "WHERE lote_destino = 'MIGRAÇÃO' AND ciclo = 'INVENTARIO_2026_05'"
        )).scalar()
        print(f"\n  ajuste_estoque_inventario: lote_destino='MIGRACAO' {n_aj_pos} | "
              f"'MIGRAÇÃO' {n_aj_pos_com}")

        n_rec_pos = db.session.execute(text(
            "SELECT COUNT(*) FROM recebimento_lf_lote WHERE lote_nome = 'MIGRACAO'"
        )).scalar()
        n_rec_pos_com = db.session.execute(text(
            "SELECT COUNT(*) FROM recebimento_lf_lote WHERE lote_nome = 'MIGRAÇÃO'"
        )).scalar()
        print(f"  recebimento_lf_lote: lote_nome='MIGRACAO' {n_rec_pos} | "
              f"'MIGRAÇÃO' {n_rec_pos_com}")

        print('\n  Padronizacao Odoo+DB concluida. Falta apenas editar constantes no codigo.')


if __name__ == '__main__':
    main()
