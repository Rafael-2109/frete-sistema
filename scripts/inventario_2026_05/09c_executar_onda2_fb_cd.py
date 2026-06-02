# etapa: orquestrador
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""F9c — Executor Onda 2 TRANSFERIR_FB_CD via reuso RecebimentoLf (etapas 19-37).

Agrupa ate N ajustes PROPOSTO TRANSFERIR_FB_CD em 1 RecebimentoLf virtual,
pre-popula RecebimentoLfLote (agregando por cod+lote_origem) e dispara
processar_transfer_only que executa:
  Fase 6 (19-23): picking saida FB -> Parceiros/Clientes -> NF SEFAZ (CFOP 5152, Playwright)
  Fase 7 (24-37): upload XML como DFe no CD -> PO -> picking entrada -> invoice CD -> finaliza

Pos-execucao, marca os ajustes do batch como EXECUTADO (fase=FB_CD_OK) com
referencia ao recebimento_lf criado em external_id_operacao.

IMPORTANTE: ajustes com lote_origem == lote_destino sao 100% concluidos.
Ajustes com lote_destino divergente (ex: agregar 4 lotes destino em 1 NF)
ficam EXECUTADO mas precisam de pre-etapa CD interna posterior para
distribuir do lote chegado para os lotes destinos finais.

Flags:
    --batch-name=X       numero_nf identificador (default INV-FBC-YYYYMMDD-HHMM)
    --limite=N           max ajustes (default 10)
    --custo-zero-ok      permite incluir ajustes com custo_medio=0 (default: FALSE)
    --ids=171,172,...    forca executar IDs especificos (override auto-pick)
    --dry-run            (default) simula
    --confirmar          executa real
    --usuario X          auditoria

Uso:
    # Dry-run com auto-pick dos primeiros 10
    python scripts/inventario_2026_05/09c_executar_onda2_fb_cd.py --dry-run

    # Real, batch 1 (10 ajustes)
    python scripts/inventario_2026_05/09c_executar_onda2_fb_cd.py \\
        --confirmar --usuario=rafael

    # Real, IDs especificos
    python scripts/inventario_2026_05/09c_executar_onda2_fb_cd.py \\
        --ids=169974,169975,169976,169977,169978,169982,169985,169996,169998,169999 \\
        --confirmar --usuario=rafael

CRITICO:
- Etapa 23 transmite NF-e SEFAZ via Playwright (IRREVERSIVEL apos autorizada).
- Etapas 19-37 sao SINCRONAS aqui (pode demorar 5-30min total).
- Se falhar no meio, RecebimentoLf fica com transfer_status='erro' e pode
  ser retomado via job processar_transfer_fb_cd_job(recebimento_id).
"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402
from app.odoo.models import AjusteEstoqueInventario  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402
from app.recebimento.models import RecebimentoLf, RecebimentoLfLote  # noqa: E402
from app.recebimento.services.recebimento_lf_odoo_service import (  # noqa: E402
    RecebimentoLfOdooService,
)
from app.utils.timezone import agora_utc_naive  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('09c')

CICLO = 'INVENTARIO_2026_05'
CFOP_TRANSFER = '5152'  # Transferencia mercadoria mesmo titular (nao retorno)
COMPANY_FB = 1
COMPANY_CD = 4


def banner(titulo: str, char: str = '=') -> None:
    line = char * 78
    print(f'\n{line}\n  {titulo}\n{line}')


def buscar_ajustes(ids: Optional[List[int]], limite: int, custo_zero_ok: bool):
    """Busca ajustes PROPOSTO TRANSFERIR_FB_CD. Se ids fornecidos, usa-os
    diretamente; senao auto-pick os primeiros N com custo > 0 (a menos
    que custo_zero_ok=True)."""
    q = AjusteEstoqueInventario.query.filter_by(
        ciclo=CICLO, company_id=COMPANY_CD, status='PROPOSTO',
        acao_decidida='TRANSFERIR_FB_CD',
    )
    if ids:
        q = q.filter(AjusteEstoqueInventario.id.in_(ids))
        return q.order_by(AjusteEstoqueInventario.id).all()
    if not custo_zero_ok:
        q = q.filter(AjusteEstoqueInventario.custo_medio > 0)
    q = q.filter(AjusteEstoqueInventario.qtd_inventario > 0)
    return q.order_by(AjusteEstoqueInventario.id).limit(limite).all()


def validar_saldo_fb(odoo, ajustes_agg: List[Tuple[str, str, float]], margem_min: float = 1.5) -> Tuple[bool, List[str]]:
    """Para cada (cod, lote_origem, qty_agg), verifica saldo livre na FB.
    Retorna (ok_total, erros)."""
    erros = []
    cods = sorted({c for c, _, _ in ajustes_agg})
    prods = odoo.search_read('product.product',
        [['default_code', 'in', cods]], ['id', 'default_code', 'name', 'weight', 'standard_price'])
    info = {p['default_code']: p for p in prods}

    for cod, lote_origem, qty in ajustes_agg:
        if cod not in info:
            erros.append(f'cod={cod}: produto nao existe no Odoo')
            continue
        p = info[cod]
        if not p.get('weight') or float(p['weight']) <= 0:
            erros.append(f'cod={cod}: weight=0 (CIEL IT vai rejeitar)')
        if not p.get('standard_price') or float(p['standard_price']) <= 0:
            erros.append(f'cod={cod}: standard_price=0 (SEFAZ vai rejeitar)')
        # Saldo livre por lote_origem em FB/Estoque (id=8) APENAS
        # (picking saida FB usa location_id=8 — sublocations operacionais nao contam)
        lots = odoo.search_read('stock.lot',
            [['product_id', '=', p['id']],
             ['name', 'in', [lote_origem]],
             ['company_id', '=', COMPANY_FB]], ['id'])
        if lots:
            lot_ids = [L['id'] for L in lots]
            q_origem = odoo.search_read('stock.quant',
                [['product_id', '=', p['id']],
                 ['lot_id', 'in', lot_ids],
                 ['location_id', '=', 8],   # FB/Estoque
                 ['quantity', '>', 0]],
                ['quantity', 'reserved_quantity'])
        else:
            q_origem = odoo.search_read('stock.quant',
                [['product_id', '=', p['id']],
                 ['lot_id', '=', False],
                 ['location_id', '=', 8],
                 ['quantity', '>', 0]],
                ['quantity', 'reserved_quantity'])
        livre = sum(q['quantity'] - q['reserved_quantity'] for q in q_origem)
        # Exigir margem confortavel (>= 1.5x) para evitar bug step 21 de
        # consolidacao de move_lines quando saldo apertado.
        if livre < qty - 0.001:
            erros.append(
                f'cod={cod} lote={lote_origem!r}: pede {qty:.4f}, '
                f'FB/Estoque livre {livre:.4f} (FALTA {qty - livre:.4f})'
            )
        elif livre < qty * margem_min:
            erros.append(
                f'cod={cod} lote={lote_origem!r}: pede {qty:.4f}, '
                f'FB/Estoque livre {livre:.4f} — MARGEM_APERTADA '
                f'({livre/qty:.2f}x < {margem_min:.2f}x). Risco bug step 21.'
            )
    return (not erros, erros)


def agregar_por_cod_lote_origem(ajustes) -> Dict[Tuple[str, str], List]:
    """Agrupa ajustes por (cod_produto, lote_origem)."""
    agg: Dict[Tuple[str, str], List] = {}
    for aj in ajustes:
        k = (aj.cod_produto, aj.lote_origem or '')
        agg.setdefault(k, []).append(aj)
    return agg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch-name', default=None,
        help='numero_nf identificador (default INV-FBC-YYYYMMDD-HHMM)')
    parser.add_argument('--limite', type=int, default=10)
    parser.add_argument('--ids', default=None,
        help='Lista CSV de IDs especificos (override auto-pick)')
    parser.add_argument('--custo-zero-ok', action='store_true', default=False,
        help='Permite ajustes com custo_medio=0 (risco: SEFAZ rejeita)')
    parser.add_argument('--margem-min', type=float, default=1.5,
        help='Margem minima FB/Estoque livre / qty pedida (default 1.5x). Use 1.0 para aceitar saldo exato.')
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--confirmar', action='store_true')
    parser.add_argument('--usuario', default='09c_onda2')
    args = parser.parse_args()

    if args.confirmar:
        args.dry_run = False

    modo = 'DRY-RUN' if args.dry_run else 'REAL'
    ids_list = None
    if args.ids:
        ids_list = [int(x) for x in args.ids.split(',') if x.strip()]

    batch_name = args.batch_name or f'INV-FBC-{datetime.now().strftime("%Y%m%d-%H%M")}'

    app = create_app()
    with app.app_context():
        # SET application_name para audit trail
        db.session.execute(text(
            f"SET application_name = 'inventario-09c-{batch_name}'"
        ))

        banner(f'EXECUTOR ONDA 2 (FB->CD) | batch={batch_name} | modo={modo}')

        ajustes = buscar_ajustes(ids_list, args.limite, args.custo_zero_ok)
        if not ajustes:
            logger.info('Nenhum ajuste para processar. Encerrando.')
            return

        agg = agregar_por_cod_lote_origem(ajustes)
        ids_resumo = [a.id for a in ajustes]
        total_qty = sum(float(a.qtd_inventario) for a in ajustes)
        total_brl = sum(float(a.qtd_inventario) * float(a.custo_medio or 0) for a in ajustes)
        print(f'\nAjustes selecionados ({len(ajustes)}): {ids_resumo}')
        print(f'Total qty: {total_qty:.4f} | Total R$: {total_brl:.2f}')
        print(f'Linhas NF apos agregacao (cod+lote_origem): {len(agg)}\n')
        print(f"{'idx':<4}{'cod':<11}{'lote_origem':<16}{'qty_agg':>12}  ajustes")
        print('-' * 78)
        ajustes_agg_list = []
        for i, ((cod, lote_o), lista) in enumerate(agg.items(), 1):
            qty_agg = sum(float(x.qtd_inventario) for x in lista)
            ajustes_agg_list.append((cod, lote_o, qty_agg))
            ids_lista = ','.join(str(x.id) for x in lista)
            print(f"{i:<4}{cod:<11}{lote_o:<16}{qty_agg:>12.4f}  [{ids_lista}]")

        # Pre-check Odoo
        odoo = get_odoo_connection()
        ok, erros = validar_saldo_fb(odoo, ajustes_agg_list, margem_min=args.margem_min)
        if erros:
            print('\nERROS DE VALIDACAO PRE-EXECUCAO:')
            for e in erros:
                print(f'  - {e}')
            if not args.custo_zero_ok and any('standard_price=0' in e for e in erros):
                logger.error('Aborto: produtos sem standard_price. Use --custo-zero-ok (risco) ou corrija no Odoo.')
                return
            if not ok:
                logger.error('Aborto: saldo FB insuficiente. Marcar ajustes como FALHA ou usar batch menor.')
                return

        if args.dry_run:
            print('\nMODO DRY-RUN — nada criado. Use --confirmar para executar.')
            return

        # ====== EXECUCAO REAL ======
        print('\n>>> Criando RecebimentoLf virtual + Lotes...')

        # Buscar product_ids
        cods = sorted({c for c, _, _ in ajustes_agg_list})
        prods = odoo.search_read('product.product',
            [['default_code', 'in', cods]],
            ['id', 'default_code', 'name'])
        pid_by_cod = {p['default_code']: p['id'] for p in prods}
        name_by_cod = {p['default_code']: p['name'] for p in prods}

        rec = RecebimentoLf(
            numero_nf=batch_name,
            company_id=COMPANY_FB,
            status='processado',  # FB ja' "processou" (pula 1-18)
            fase_atual=5,
            etapa_atual=18,
            total_etapas=37,
            transfer_status='pendente',
            usuario=args.usuario,
            criado_em=agora_utc_naive(),
        )
        db.session.add(rec)
        db.session.flush()
        rec_id = rec.id
        print(f'  RecebimentoLf id={rec_id} numero_nf={batch_name!r} criado.')

        lotes_criados = 0
        for cod, lote_o, qty_agg in ajustes_agg_list:
            pid = pid_by_cod[cod]
            lt = RecebimentoLfLote(
                recebimento_lf_id=rec_id,
                odoo_product_id=pid,
                odoo_product_name=name_by_cod[cod],
                cfop=CFOP_TRANSFER,
                tipo='manual',
                lote_nome=lote_o,
                quantidade=qty_agg,
                produto_tracking='lot',
                processado=True,  # pre-marca; step_19 vai filtrar
            )
            db.session.add(lt)
            lotes_criados += 1

        # Vincular ajustes ao rec via external_id_operacao
        external_ref = f'FBC_REC_{rec_id}'
        for aj in ajustes:
            aj.external_id_operacao = external_ref
            aj.fase_pipeline = 'FB_CD_PROCESSANDO'

        db.session.commit()
        print(f'  {lotes_criados} RecebimentoLfLote criados, '
              f'{len(ajustes)} ajustes vinculados via {external_ref}')

        # ====== Chamar service.processar_transfer_only ======
        print('\n>>> Iniciando processar_transfer_only (sincrono, pode demorar 5-30min)...')
        service = RecebimentoLfOdooService()
        try:
            resultado = service.processar_transfer_only(rec_id)
            print(f'\n>>> Resultado: {resultado}')
        except TimeoutError as e:
            # Fallback bug step 27: service usa `purchase_id` (errado), CIEL IT preenche `purchase_fiscal_id`
            # PO foi criado mas service nao detectou. Buscar PO via purchase_fiscal_id e seguir manualmente.
            if 'Gerar PO CD' in str(e):
                print(f'\n>>> Step 27 timeout — checando se PO foi criado via purchase_fiscal_id...')
                rec = db.session.get(RecebimentoLf, rec_id)
                d = odoo.read('l10n_br_ciel_it_account.dfe', [rec.odoo_cd_dfe_id],
                              ['purchase_fiscal_id'])
                pfid = d[0].get('purchase_fiscal_id') if d else None
                if not pfid:
                    print(f'>>> PO NAO criado no DFe {rec.odoo_cd_dfe_id}. Robo CIEL IT realmente parado.')
                    raise
                po_id = pfid[0] if isinstance(pfid, (list, tuple)) else pfid
                po_name = pfid[1] if isinstance(pfid, (list, tuple)) and len(pfid) > 1 else None
                print(f'>>> PO CD detectado: id={po_id} name={po_name}. Retomando steps 28-37 direto.')
                rec.odoo_cd_po_id = po_id
                rec.odoo_cd_po_name = po_name
                rec.etapa_atual = 27
                rec.transfer_status = 'processando'
                rec.transfer_erro_mensagem = None
                db.session.commit()
                # Reinstancia service e chama steps 28-37 DIRETAMENTE (sem processar_transfer_only)
                svc = RecebimentoLfOdooService()
                svc._recebimento_id = rec_id
                for sn, fn in [
                    ('28', svc._step_28_configurar_po_cd),
                    ('29', svc._step_29_confirmar_po_cd),
                    ('30', svc._step_30_aprovar_po_cd),
                    ('31', svc._step_31_buscar_picking_cd),
                    ('32', svc._step_32_preencher_lotes_cd),
                    ('33', svc._step_33_aprovar_qc_cd),
                    ('34', svc._step_34_validar_picking_cd),
                    ('35', svc._step_35_criar_invoice_cd),
                    ('36', svc._step_36_configurar_postar_invoice_cd),
                    ('37', svc._step_37_finalizar_recebimento_cd),
                ]:
                    print(f'  step_{sn}...')
                    fn(odoo)
            else:
                raise

        # Re-buscar rec para ver estado final
        rec = db.session.get(RecebimentoLf, rec_id)
        if rec.transfer_status == 'concluido':
            # Marca ajustes EXECUTADO + cria split de lote_destino quando lote_origem != lote_destino
            ajustes_pais = AjusteEstoqueInventario.query.filter_by(
                external_id_operacao=external_ref).all()
            for aj in ajustes_pais:
                aj.status = 'EXECUTADO'
                aj.fase_pipeline = 'FB_CD_OK'
                aj.picking_id_odoo = rec.odoo_transfer_in_picking_id
                aj.invoice_id_odoo = rec.odoo_cd_invoice_id
                aj.erro_msg = (f'Onda 2 FB->CD via RecLf {rec_id} batch {batch_name} '
                               f'(NF saida={rec.odoo_transfer_invoice_name}, PO CD={rec.odoo_cd_po_name}, '
                               f'picking CD={rec.odoo_transfer_in_picking_name}, '
                               f'invoice CD={rec.odoo_cd_invoice_name})')
            # SPLIT lote_destino
            from datetime import datetime as _dt
            splits = []
            for pai in ajustes_pais:
                if pai.lote_origem == pai.lote_destino:
                    continue
                novo = AjusteEstoqueInventario(
                    ciclo=pai.ciclo, cod_produto=pai.cod_produto,
                    tipo_produto=pai.tipo_produto, company_id=4,
                    lote_odoo=pai.lote_origem, lote_origem=pai.lote_origem,
                    lote_destino=pai.lote_destino,
                    qtd_inventario=pai.qtd_inventario, qtd_odoo=pai.qtd_inventario,
                    qtd_ajuste=0, custo_medio=pai.custo_medio,
                    acao_decidida='AJUSTE_CD_TRANSF_INTERNA_POS', status='APROVADO',
                    aprovado_em=_dt.now(), aprovado_por='claude_code_split_pos_onda2',
                    criado_em=_dt.now(), criado_por='claude_code_split_pos_onda2',
                    external_id_operacao=f'SPLIT_REC{rec_id}_PAI_{pai.id}',
                    erro_msg=f'Split lote_destino pos-Onda2 RecLf{rec_id}. Pai: ajuste {pai.id}.',
                )
                db.session.add(novo)
                splits.append((pai.id, novo))
            db.session.commit()
            print(f'\nOK: {len(ajustes_pais)} ajustes EXECUTADO + {len(splits)} splits APROVADO criados.')

            # Split fica criado em status=APROVADO. Rodar 09b separadamente:
            #   python scripts/inventario_2026_05/09b_executar_pre_etapa.py \
            #       --company-id=4 --cod-produto=COD --confirmar --usuario=rafael
            if splits:
                cods_split = sorted({s[1].cod_produto for s in splits})
                print(f'\n>>> Splits APROVADO criados. Rodar 09b para cods: {cods_split}')
        else:
            # Marca ajustes FALHA com erro do rec
            AjusteEstoqueInventario.query.filter_by(
                external_id_operacao=external_ref
            ).update({
                'status': 'FALHA', 'fase_pipeline': 'FB_CD_FALHA',
                'erro_msg': f'RecLf {rec_id} transfer_status={rec.transfer_status}: {rec.transfer_erro_mensagem}',
            })
            db.session.commit()
            print(f'\nFALHA: rec.transfer_status={rec.transfer_status}')


if __name__ == '__main__':
    main()
