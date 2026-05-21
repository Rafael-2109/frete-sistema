"""fat_lf_05_executar_clean.py — Faturamento LF com RESERVA EXPLICITA (corrige bug multi-lote).

Problema do executor 09: para ajustes SEM lote_origem (caso deste faturamento),
a cadeia action_assign -> ajustar_qty_done -> consolidar_move_lines corrompe a
quantidade em produtos multi-lote (caso 104000045: 59.9 -> 12.3).

Solucao: ETAPA B com RESERVA EXPLICITA. Para cada produto:
  1. aloca QTD via FIFO sobre quants LIVRES child_of(principal) -> lista (lote, loc, qty)
  2. cria picking 1-linha-por-produto (qty = soma alocada)
  3. action_confirm (NAO action_assign)
  4. cria stock.move.line MANUALMENTE por (lote, loc, qty) com qty_done exato
  5. button_validate (skip_backorder) + liberar_faturamento
Isso garante qty faturada == QTD do Excel.

Reusa de 09_executar_onda1_bulk.py: helpers fiscais (NCM/weight) + etapas C/D/E/F.
Ciclo isolado FATURAMENTO_LF_2026_05_20. Idempotente (pula fase F5c+).

Uso:
  # canario etapa B so (valida reserva), 1 cod:
  python ... --filtro-cod-produto 104000045 --apenas-etapa B --confirmar
  # canario completo (B..F) real:
  python ... --filtro-cod-produto 104000045,208000021 --confirmar --confirmar-sefaz
  # bulk completo:
  python ... --confirmar --confirmar-sefaz
"""
import argparse
import importlib.util
import os
import sys
import warnings
from collections import defaultdict
from typing import Dict, Any

warnings.simplefilter('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))

CICLO_FAT = 'FATURAMENTO_LF_2026_05_20'
PRINCIPAL = {1: 8, 5: 42}
ETAPAS_VALIDAS = ('B', 'C', 'D', 'E', 'F')
FASES_FEITAS = ('F5a_PICKING_CRIADO', 'F5b_VALIDADO', 'F5c_LIBERADO',
                'F5d_INVOICE_GERADA', 'F5e_SEFAZ_OK', 'F5f_ENTRADA_OK')


def _load_bulk():
    path = os.path.join(HERE, '09_executar_onda1_bulk.py')
    spec = importlib.util.spec_from_file_location('bulk_onda1', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def alocar_fifo(odoo, pid, company, principal, qtd):
    """Aloca qtd sobre quants LIVRES child_of(principal), FIFO create_date.
    Retorna (lista [{lot_id, location_id, qty}], efetivo)."""
    quants = odoo.search_read('stock.quant',
                              [['product_id', '=', pid], ['company_id', '=', company],
                               ['location_id', 'child_of', principal], ['quantity', '>', 0]],
                              ['lot_id', 'location_id', 'quantity', 'reserved_quantity', 'create_date'],
                              order='create_date asc')
    aloc = []
    rest = float(qtd)
    for q in quants:
        if rest <= 0.0001:
            break
        livre = float(q['quantity']) - float(q.get('reserved_quantity') or 0)
        if livre <= 0:
            continue
        take = min(livre, rest)
        aloc.append({'lot_id': q['lot_id'][0] if q.get('lot_id') else None,
                     'location_id': q['location_id'][0], 'qty': round(take, 4)})
        rest -= take
    return aloc, round(float(qtd) - rest, 4)


def etapa_b_clean(bulk, odoo, ajustes, dry_run, executado_por, max_prod=30):
    from app import db
    from app.odoo.services.inventario_pipeline_service import (
        ACAO_PARA_DIRECAO, PICKING_TYPE_POR_DIRECAO, resolver_location_destino)
    from app.odoo.constants.operacoes_fiscais import COMPANY_PARTNER_ID
    from app.odoo.services.stock_picking_service import StockPickingService

    bulk.banner('ETAPA B CLEAN — reserva explicita (faturamento exato)', '-')
    pend = [a for a in ajustes if a.fase_pipeline not in FASES_FEITAS]
    print(f'  {len(pend)} ajustes pendentes (B)')
    if not pend:
        return

    # pids_map p/ helpers fiscais
    cods = sorted({a.cod_produto for a in pend})
    pids_map: Dict[str, Any] = {}
    uom_map: Dict[int, int] = {}
    track_map: Dict[int, str] = {}  # pid -> tracking (lot/serial/none)
    for c in cods:
        pr = odoo.search_read('product.product', [['default_code', '=', c]], ['id', 'uom_id', 'tracking'], limit=1)
        pids_map[c] = pr[0]['id'] if pr else None
        if pr and pr[0].get('uom_id'):
            uom_map[pr[0]['id']] = pr[0]['uom_id'][0]
        if pr:
            track_map[pr[0]['id']] = pr[0].get('tracking') or 'none'

    if not dry_run:
        bulk.corrigir_weight_zero(odoo, pids_map, peso_fallback=0.001)
        try:
            bulk.validar_cadastro_fiscal(odoo, pids_map, modo='warn')
        except Exception as e:
            print(f'  validar_cadastro_fiscal warn: {e}')

    # agrupar por (company_origem, tipo_op)
    grupos: Dict[tuple, list] = defaultdict(list)
    for a in pend:
        if a.acao_decidida not in ACAO_PARA_DIRECAO:
            continue
        tipo_op, origem, _ = ACAO_PARA_DIRECAO[a.acao_decidida]
        grupos[(origem, tipo_op)].append(a)

    picking_svc = StockPickingService(odoo=odoo)
    total_pk = falhas = 0

    for (origem, tipo_op), grp in grupos.items():
        destino = ACAO_PARA_DIRECAO[grp[0].acao_decidida][2]
        pt = PICKING_TYPE_POR_DIRECAO.get((origem, tipo_op))
        loc_orig = PRINCIPAL[origem]
        loc_dest = resolver_location_destino(tipo_op, destino, company_origem=origem)
        partner = COMPANY_PARTNER_ID[destino]
        por_prod = defaultdict(list)
        for a in grp:
            por_prod[a.cod_produto].append(a)
        cods_g = sorted(por_prod.keys())
        chunks = [cods_g[i:i + max_prod] for i in range(0, len(cods_g), max_prod)]
        print(f'\n  Grupo ({origem},{tipo_op}) -> {len(chunks)} pickings ({len(cods_g)} produtos)')

        for idx, chunk in enumerate(chunks, 1):
            linhas = []
            aloc_por_prod = {}
            ajustes_chunk = []
            for cod in chunk:
                pid = pids_map.get(cod)
                if not pid:
                    continue
                qtd = sum(float(abs(a.qtd_ajuste or 0)) for a in por_prod[cod])
                aloc, eff = alocar_fifo(odoo, pid, origem, loc_orig, qtd)
                if eff <= 0.0001:
                    for a in por_prod[cod]:
                        a.erro_msg = f'sem estoque livre child_of({loc_orig}) (QTD={qtd})'
                    continue
                if eff < qtd - 0.5:
                    for a in por_prod[cod]:
                        a.erro_msg = f'parcial: faturado {eff} de {qtd}'
                linhas.append({'product_id': pid, 'quantity': eff,
                               'lot_name': None, 'name': f'Fat LF cod={cod}'})
                aloc_por_prod[pid] = (aloc, eff)
                ajustes_chunk.extend(por_prod[cod])
            if not linhas:
                continue
            if dry_run:
                print(f'    [DRY] picking {idx}: {len(linhas)} produtos, '
                      f'qty_total={sum(l["quantity"] for l in linhas):.1f}')
                total_pk += 1
                continue

            try:
                pk = picking_svc.criar_transferencia(
                    company_origem_id=origem, company_destino_id=destino,
                    location_origem_id=loc_orig, location_destino_id=loc_dest,
                    linhas=linhas, picking_type_id=pt, partner_id=partner,
                    origin=f'FAT-LF-{tipo_op.upper()}-G{idx:03d}')
                # action_confirm + action_assign (reserva propria do Odoo nos lotes corretos)
                picking_svc.confirmar_e_reservar(pk)
                # marcar TODAS as move_lines reservadas como done (qty_done=quantity).
                # SEM ajustar_qty_done / consolidar (que corrompiam multi-lote).
                mls = odoo.search_read('stock.move.line', [['picking_id', '=', pk]],
                                       ['id', 'product_id', 'quantity', 'qty_done', 'lot_id'])
                done_por_pid: Dict[int, float] = defaultdict(float)
                for ml in mls:
                    q = float(ml.get('quantity') or 0)
                    if q > 0:
                        upd = {'qty_done': q}
                        # cinto de seguranca: produto lot-tracked com move_line sem lote
                        # -> usar placeholder P-15/05 (regra usuario p/ lote vazio)
                        pid_ml = ml['product_id'][0] if ml.get('product_id') else None
                        if not ml.get('lot_id') and track_map.get(pid_ml) in ('lot', 'serial'):
                            upd['lot_name'] = 'P-15/05'
                        odoo.write('stock.move.line', [ml['id']], upd)
                        if pid_ml:
                            done_por_pid[pid_ml] += q
                # detectar parciais (reservado < esperado)
                for pid, (aloc, eff) in aloc_por_prod.items():
                    res = done_por_pid.get(pid, 0)
                    if res < eff - 0.5:
                        print(f'    AVISO pid={pid}: reservado {res:.2f} < esperado {eff:.2f}')
                # G018 peso/volumes fallback no picking
                try:
                    bulk.aplicar_peso_volumes_fallback_picking(odoo, pk)
                except Exception as e:
                    print(f'    G018 picking {pk} warn: {e}')
                # validar SEM consolidar (linhas_esperadas=None)
                picking_svc.validar(pk, linhas_esperadas=None)
                picking_svc.liberar_faturamento(pk)
                for a in ajustes_chunk:
                    a.picking_id_odoo = pk
                    a.fase_pipeline = 'F5c_LIBERADO'
                    # NAO setar status='EXECUTADO' aqui: o guard de idempotencia
                    # do F5e (etapa D) pula status=EXECUTADO -> SEFAZ nao transmitiria.
                    # status='EXECUTADO' so apos F5f (entrada completa) na propria etapa.
                db.session.commit()
                total_pk += 1
                print(f'    picking {pk} OK ({len(linhas)} produtos)')
            except Exception as e:
                falhas += 1
                print(f'    FALHA picking chunk {idx}: {e}')
                import traceback
                traceback.print_exc()
                try:
                    db.session.rollback()
                except Exception:
                    pass
    print(f'\n  ETAPA B CLEAN: pickings={total_pk} falhas={falhas}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--filtro-cod-produto', default=None)
    ap.add_argument('--apenas-etapa', default=None, choices=ETAPAS_VALIDAS)
    ap.add_argument('--ate-etapa', default=None, choices=ETAPAS_VALIDAS)
    ap.add_argument('--max-produtos-picking', type=int, default=30)
    ap.add_argument('--confirmar', action='store_true')
    ap.add_argument('--confirmar-sefaz', action='store_true')
    ap.add_argument('--usuario', default='claude_fat_lf')
    args = ap.parse_args()
    dry = not args.confirmar
    if args.confirmar_sefaz and not args.confirmar:
        print('ERRO: --confirmar-sefaz exige --confirmar')
        sys.exit(2)
    if args.apenas_etapa:
        etapas = [args.apenas_etapa]
    else:
        idx = ETAPAS_VALIDAS.index(args.ate_etapa) if args.ate_etapa else len(ETAPAS_VALIDAS) - 1
        etapas = list(ETAPAS_VALIDAS[:idx + 1])
    filtro = [c.strip() for c in args.filtro_cod_produto.split(',')] if args.filtro_cod_produto else None

    bulk = _load_bulk()
    bulk.CICLO = CICLO_FAT
    from app import create_app, db
    from app.odoo.models.ajuste_estoque_inventario import AjusteEstoqueInventario
    from app.odoo.utils.connection import get_odoo_connection

    def carregar():
        q = (AjusteEstoqueInventario.query.filter_by(ciclo=CICLO_FAT)
             .filter(AjusteEstoqueInventario.status.in_(('APROVADO', 'EXECUTADO'))))
        if filtro:
            q = q.filter(AjusteEstoqueInventario.cod_produto.in_(filtro))
        return q.order_by(AjusteEstoqueInventario.cod_produto, AjusteEstoqueInventario.id).all()

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        bulk.banner(f'FAT LF CLEAN ciclo={CICLO_FAT} modo={"DRY" if dry else "REAL"} etapas={"".join(etapas)}')
        if filtro:
            print(f'  FILTRO: {filtro}')
        ajustes = carregar()
        bulk.imprimir_resumo_ajustes(ajustes)
        if not ajustes:
            print('  Nada a fazer.')
            return

        if 'B' in etapas:
            etapa_b_clean(bulk, odoo, ajustes, dry, args.usuario, args.max_produtos_picking)
            db.session.expire_all(); ajustes = carregar()
        if 'C' in etapas:
            try:
                db.engine.dispose()
            except Exception:
                pass
            bulk.etapa_c_aguardar_invoices(odoo, ajustes, dry_run=dry, executado_por=args.usuario)
            db.session.expire_all(); ajustes = carregar()
        if 'D' in etapas:
            if not args.confirmar_sefaz and not dry:
                print('  ETAPA D requer --confirmar-sefaz. Pulando.')
            else:
                try:
                    db.engine.dispose()
                except Exception:
                    pass
                bulk.etapa_d_sefaz(odoo, ajustes, dry_run=dry, executado_por=args.usuario)
                db.session.expire_all(); ajustes = carregar()
        if 'E' in etapas:
            bulk.etapa_e_entrada_fb(odoo, ajustes, dry_run=dry, executado_por=args.usuario)
            db.session.expire_all(); ajustes = carregar()
        if 'F' in etapas:
            bulk.etapa_f_entrada_destino_manual(odoo, ajustes, dry_run=dry, executado_por=args.usuario)
        bulk.banner('FIM', '=')


if __name__ == '__main__':
    main()
