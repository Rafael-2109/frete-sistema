"""fat_lf_04_executar.py — Driver de faturamento LF (ciclo FATURAMENTO_LF_2026_05_20).

Reutiliza as etapas TESTADAS de 09_executar_onda1_bulk.py (ETAPA B->C->D->E->F)
mas dirigidas pelos MEUS ajustes (ciclo isolado), sem tocar nos 1742 registros
de INVENTARIO_2026_05.

Pipeline por NF:
  B: cria picking (saida, max 30 produtos/NF, FIFO na location principal)
  C: aguarda robo CIEL IT criar invoice
  D: transmite SEFAZ via Playwright (irreversivel — exige --confirmar-sefaz)
  E: entrada FB para PERDA_LF_FB / DEV_LF_FB (RecebimentoLf pipeline 0-18, CFOP 1903/1949)
  F: entrada destino LF para INDUSTRIALIZACAO_FB_LF (Em Transito 26489 -> LF/Estoque 42)

Idempotente: pula ajustes ja em fase F5a..F5e (etapa B) e re-roda com seguranca.

Uso:
  # CANARIO (1 cod por acao) dry-run:
  python scripts/inventario_2026_05/fat_lf_04_executar.py --filtro-cod-produto 207210014
  # CANARIO real ate SEFAZ + entrada:
  python ... --filtro-cod-produto 207210014 --confirmar --confirmar-sefaz
  # BULK completo real:
  python ... --confirmar --confirmar-sefaz
  # So uma etapa:
  python ... --apenas-etapa B --confirmar
"""
import argparse
import importlib.util
import os
import sys
import warnings

warnings.simplefilter('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))

CICLO_FAT = 'FATURAMENTO_LF_2026_05_20'
ETAPAS_VALIDAS = ('B', 'C', 'D', 'E', 'F')
# fases ja concluidas (etapa B pula); usado tambem para carregar pendentes
FASES_PICKING_FEITO = ('F5a_PICKING_CRIADO', 'F5b_VALIDADO', 'F5c_LIBERADO',
                       'F5d_INVOICE_GERADA', 'F5e_SEFAZ_OK', 'F5f_ENTRADA_OK')


def _load_bulk():
    """Importa 09_executar_onda1_bulk.py (nome comeca com digito) via importlib."""
    path = os.path.join(HERE, '09_executar_onda1_bulk.py')
    spec = importlib.util.spec_from_file_location('bulk_onda1', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--filtro-cod-produto', default=None, help='CSV de cods (canario)')
    ap.add_argument('--ciclo', default=CICLO_FAT, help='ciclo do AjusteEstoqueInventario (default: %(default)s)')
    ap.add_argument('--apenas-etapa', default=None, choices=ETAPAS_VALIDAS)
    ap.add_argument('--ate-etapa', default=None, choices=ETAPAS_VALIDAS)
    ap.add_argument('--max-produtos-picking', type=int, default=30)
    ap.add_argument('--confirmar', action='store_true', help='executa de verdade (B/C/E/F)')
    ap.add_argument('--confirmar-sefaz', action='store_true', help='libera ETAPA D SEFAZ (irreversivel)')
    ap.add_argument('--usuario', default='claude_fat_lf')
    ap.add_argument('--validacao-fiscal', default='strict', choices=['strict', 'warn', 'skip'])
    ap.add_argument('--auto-fix-weight', type=float, default=0.001)
    args = ap.parse_args()

    dry_run = not args.confirmar
    if args.confirmar_sefaz and not args.confirmar:
        print('ERRO: --confirmar-sefaz exige --confirmar')
        sys.exit(2)

    if args.apenas_etapa:
        etapas = [args.apenas_etapa]
    else:
        idx = ETAPAS_VALIDAS.index(args.ate_etapa) if args.ate_etapa else len(ETAPAS_VALIDAS) - 1
        etapas = list(ETAPAS_VALIDAS[:idx + 1])

    filtro_cods = None
    if args.filtro_cod_produto:
        filtro_cods = [c.strip() for c in args.filtro_cod_produto.split(',') if c.strip()]

    ciclo = args.ciclo
    bulk = _load_bulk()
    # ISOLAMENTO: o origin dos pickings e ajustes compensatorios usa bulk.CICLO
    bulk.CICLO = ciclo

    from app import create_app, db  # noqa: E402
    from app.odoo.models.ajuste_estoque_inventario import AjusteEstoqueInventario  # noqa: E402
    from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

    def carregar():
        q = (AjusteEstoqueInventario.query
             .filter_by(ciclo=ciclo)
             .filter(AjusteEstoqueInventario.status.in_(('APROVADO', 'EXECUTADO'))))
        if filtro_cods:
            q = q.filter(AjusteEstoqueInventario.cod_produto.in_(filtro_cods))
        return q.order_by(AjusteEstoqueInventario.cod_produto, AjusteEstoqueInventario.id).all()

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        bulk.banner(f'FATURAMENTO LF — ciclo={ciclo} '
                    f'modo={"DRY-RUN" if dry_run else "REAL"} etapas={"".join(etapas)}')
        if filtro_cods:
            print(f'  FILTRO cods (canario): {filtro_cods}')

        ajustes = carregar()
        bulk.imprimir_resumo_ajustes(ajustes)
        if not ajustes:
            print('\n  Nenhum ajuste — encerrando.')
            return

        if 'B' in etapas:
            bulk.etapa_b_pickings(odoo, ajustes, dry_run=dry_run, executado_por=args.usuario,
                                  max_produtos_por_picking=args.max_produtos_picking,
                                  modo_validacao_fiscal=args.validacao_fiscal,
                                  auto_fix_weight=args.auto_fix_weight)
            db.session.expire_all(); ajustes = carregar()

        if 'C' in etapas:
            try:
                db.engine.dispose()
            except Exception:
                pass
            bulk.etapa_c_aguardar_invoices(odoo, ajustes, dry_run=dry_run, executado_por=args.usuario)
            db.session.expire_all(); ajustes = carregar()

        if 'D' in etapas:
            if not args.confirmar_sefaz and not dry_run:
                print('\n  ETAPA D requer --confirmar-sefaz (SEFAZ irreversivel). Pulando.')
            else:
                try:
                    db.engine.dispose()
                except Exception:
                    pass
                bulk.etapa_d_sefaz(odoo, ajustes, dry_run=dry_run, executado_por=args.usuario)
                db.session.expire_all(); ajustes = carregar()

        if 'E' in etapas:
            bulk.etapa_e_entrada_fb(odoo, ajustes, dry_run=dry_run, executado_por=args.usuario)
            db.session.expire_all(); ajustes = carregar()

        if 'F' in etapas:
            bulk.etapa_f_entrada_destino_manual(odoo, ajustes, dry_run=dry_run, executado_por=args.usuario)

        bulk.banner('FIM', '=')


if __name__ == '__main__':
    main()
