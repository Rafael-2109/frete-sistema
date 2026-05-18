"""Entrada FB do produto 210030325 — fecha o piloto via Recebimento LF.

A NF emitida pela LF (account.move id=608607, RETNA/2026/00029, CFOP 5903,
chave 35260518...086070) precisa virar entrada na FB pelo padrao XML
(igual recebimento de retorno de industrializacao normal):

  - XML autorizado da invoice LF -> DFe na FB
  - DFe -> PO -> picking entrada FB -> invoice in_invoice na FB

O fluxo ja existe: RecebimentoLfOdooService.processar_recebimento(rec_id)
executa 37 etapas. Para o piloto:
  - Fases 1-5 (etapas 0-18): cria DFe FB + PO + picking entrada + invoice in
  - Fases 6-7 (etapas 19-37): PULADAS automaticamente porque o lote tem
    cfop='5903' (em CFOPS_RETORNO), `transfer_status='sem_transferencia'`

Resultado esperado pos-execucao:
  - FB: 66.532 un de 210030325 lote `MIGRACAO` (lot_id=30400, ja existe)
    em FB/Estoque (loc=8). Soma com 162.819 ja existentes = 229.351 un.
  - LF: inalterado — 82.300 un lote 26014 (74.404 loc 42 + 7.896 loc 53).
  - DFe FB criado a partir do XML, PO confirmada/aprovada, picking
    entrada validado, invoice in_invoice posted.

Flags:
  --dry-run      (default) so' valida pre-requisitos e mostra plano
  --confirmar    cria RecebimentoLf + roda pipeline SINCRONO (sem RQ)
  --usuario X    auditoria

Uso:
  python scripts/inventario_2026_05/entrada_fb_piloto.py --dry-run
  python scripts/inventario_2026_05/entrada_fb_piloto.py --confirmar --usuario=rafael
"""
import argparse
import logging
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app, db  # noqa: E402  # type: ignore
from app.recebimento.models import RecebimentoLf, RecebimentoLfLote  # noqa: E402  # type: ignore
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('entrada_fb_piloto')

# Constantes do piloto (alinhadas com CHECKPOINT_2026_05_18_PILOTO_COMPLETO.md)
LF_INVOICE_ID = 608607
CHAVE_NFE = '35260518467441000163550010000131491006086070'
COD_PRODUTO = '210030325'
PRODUCT_ID = 28239
PRODUCT_NAME = '[210030325] ROTULO - MOLHO DE ALHO PET 150 ML - CAMPO BELO'
QTY_ENTRADA = 66532.0
LOTE_DESTINO = 'MIGRAÇÃO'  # Padronizado 2026-05-18 — com cedilha + til, lot_id=30400 FB
LOTE_DESTINO_ID = 30400
CFOP_RETORNO = '5903'
NUMERO_NF = '13149'  # nfe_infnfe_ide_nnf real no Odoo (name=RETNA/2026/00029)
CNPJ_LF = '18.467.441/0001-63'
COMPANY_FB = 1
COMPANY_LF = 5
LOC_FB_ESTOQUE = 8
LOC_LF_ESTOQUE = 42
LOC_LF_PRE_PROD = 53


def banner(titulo: str, char: str = '=') -> None:
    print()
    print(char * 78)
    print(f'  {titulo}')
    print(char * 78)


def consultar_estoque(odoo, company_id: int, label: str) -> float:
    """Lista quants internal e retorna total."""
    quants = odoo.search_read(
        'stock.quant',
        [
            ['product_id', '=', PRODUCT_ID],
            ['company_id', '=', company_id],
            ['location_id.usage', '=', 'internal'],
        ],
        ['id', 'lot_id', 'location_id', 'quantity', 'reserved_quantity'],
    )
    total = 0.0
    print(f'  {label} (cid={company_id}) — {len(quants)} quants:')
    for q in quants:
        lote = q['lot_id'][1] if q.get('lot_id') else '(sem lote)'
        loc = q['location_id'][1] if q.get('location_id') else '?'
        total += q['quantity']
        print(
            f"    quant {q['id']:>6}  loc=[{q['location_id'][0]}] {loc:<32} "
            f"lote={lote:<12}  qty={q['quantity']:>10}  res={q['reserved_quantity']}"
        )
    print(f'    TOTAL: {total}')
    return total


def validar_pre_requisitos(odoo) -> dict:
    """Valida que invoice 608607 tem XML autorizado + chave."""
    inv_data = odoo.execute_kw(
        'account.move', 'read', [[LF_INVOICE_ID]],
        {'fields': [
            'name', 'state', 'move_type', 'company_id', 'partner_id',
            'l10n_br_xml_aut_nfe', 'l10n_br_pdf_aut_nfe',
            'l10n_br_chave_nf', 'l10n_br_numero_nota_fiscal',
            'l10n_br_tipo_pedido',
        ]},
    )
    if not inv_data:
        raise RuntimeError(f'invoice LF {LF_INVOICE_ID} nao existe no Odoo')
    inv = inv_data[0]
    print(f'  invoice {LF_INVOICE_ID}: name={inv["name"]} state={inv["state"]}')
    print(f'    move_type={inv["move_type"]} (esperado out_invoice)')
    print(f'    company={inv["company_id"]} (esperado [5, LA FAMIGLIA])')
    print(f'    partner={inv["partner_id"]} (esperado [1, NACOM GOYA - FB])')
    print(f'    chave_nf={inv.get("l10n_br_chave_nf")}')
    print(f'    numero_nf={inv.get("l10n_br_numero_nota_fiscal")}')
    print(f'    tipo_pedido={inv.get("l10n_br_tipo_pedido")}')

    xml_b64 = inv.get('l10n_br_xml_aut_nfe')
    chave = str(inv.get('l10n_br_chave_nf', '') or '')
    if not xml_b64:
        raise RuntimeError('XML autorizado vazio — SEFAZ ainda nao autorizou ou nao baixou o XML')
    if not chave or len(chave) != 44:
        raise RuntimeError(f'chave NF-e invalida: {chave!r}')
    if chave != CHAVE_NFE:
        raise RuntimeError(
            f'chave NF-e divergente: invoice={chave!r} vs piloto={CHAVE_NFE!r}'
        )
    print(f'    XML presente ({len(xml_b64)} bytes b64), chave OK')

    # Verificar lote MIGRACAO ja existe na FB
    lote = odoo.search_read(
        'stock.lot',
        [
            ['id', '=', LOTE_DESTINO_ID],
            ['product_id', '=', PRODUCT_ID],
            ['company_id', '=', COMPANY_FB],
        ],
        ['id', 'name'],
        limit=1,
    )
    if not lote:
        print(f'  AVISO: lote {LOTE_DESTINO_ID} ({LOTE_DESTINO}) nao encontrado na FB '
              '— Odoo criara via _resolver_lote (auto).')
    else:
        print(f'  Lote {LOTE_DESTINO!r} OK na FB: lot_id={lote[0]["id"]}')

    return {'inv': inv, 'chave': chave}


def verificar_recebimento_existente():
    """Retorna RecebimentoLf existente para essa invoice (idempotencia) ou None."""
    return RecebimentoLf.query.filter_by(
        odoo_lf_invoice_id=LF_INVOICE_ID,
    ).order_by(RecebimentoLf.id.desc()).first()


def imprimir_plano() -> None:
    banner('PLANO — Entrada FB invoice 608607 (NF retorno CFOP 5903)', '-')
    print(f'  1. Criar RecebimentoLf:')
    print(f'       odoo_lf_invoice_id = {LF_INVOICE_ID}')
    print(f'       numero_nf          = {NUMERO_NF!r}')
    print(f'       chave_nfe          = {CHAVE_NFE}')
    print(f'       cnpj_emitente      = {CNPJ_LF!r}')
    print(f'       company_id         = {COMPANY_FB}  (FB recebe)')
    print(f'  2. Criar RecebimentoLfLote:')
    print(f'       odoo_product_id    = {PRODUCT_ID}  ({COD_PRODUTO})')
    print(f'       tipo               = "auto"  (CFOP retorno)')
    print(f'       cfop               = {CFOP_RETORNO!r}')
    print(f'       lote_nome          = {LOTE_DESTINO!r}')
    print(f'       quantidade         = {QTY_ENTRADA}')
    print(f'       produto_tracking   = "lot"')
    print(f'  3. RecebimentoLfOdooService.processar_recebimento(rec_id) — SINCRONO')
    print(f'     Etapas 0-18 (Fases 1-5): cria DFe FB a partir do XML autorizado,')
    print(f'       gera PO, valida picking entrada FB, cria invoice in_invoice posted.')
    print(f'     Etapas 19-37 (Fases 6-7): pulam automaticamente porque o lote tem')
    print(f'       cfop={CFOP_RETORNO!r} ∈ CFOPS_RETORNO → transfer_status="sem_transferencia".')
    print(f'  4. Apos sucesso: verificar quants LF (inalterado, 82.300) +')
    print(f'     FB (lote MIGRACAO +66.532 un = 229.351 total).')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='(default) so valida pre-requisitos e imprime plano')
    parser.add_argument('--confirmar', action='store_true',
                        help='executa: cria RecebimentoLf + roda pipeline sincrono')
    parser.add_argument('--usuario', default='entrada_fb_piloto')
    parser.add_argument('--reuse-existing', action='store_true',
                        help='se ja existe RecebimentoLf para essa invoice, retoma processamento')
    args = parser.parse_args()

    dry_run = not args.confirmar

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()

        banner(f'ENTRADA FB PILOTO — invoice {LF_INVOICE_ID} (modo='
               f'{"DRY-RUN" if dry_run else "REAL"})')
        print(f'  Usuario: {args.usuario}')
        print(f'  Produto: {COD_PRODUTO} (id={PRODUCT_ID}) {PRODUCT_NAME}')
        print(f'  Qty entrada FB: {QTY_ENTRADA} un, lote {LOTE_DESTINO!r}')

        # 1. Pre-requisitos
        banner('1. Pre-requisitos (XML, chave, lote)', '-')
        validar_pre_requisitos(odoo)

        # 2. Estoque ANTES
        banner('2. Estoque ANTES da entrada', '-')
        total_lf_antes = consultar_estoque(odoo, COMPANY_LF, 'LF')
        total_fb_antes = consultar_estoque(odoo, COMPANY_FB, 'FB')

        # 3. Idempotencia
        banner('3. Idempotencia — recebimento existente?', '-')
        existente = verificar_recebimento_existente()
        if existente:
            print(f'  RecebimentoLf JA EXISTE: id={existente.id}')
            print(f'    status={existente.status}  fase_atual={existente.fase_atual}')
            print(f'    etapa_atual={existente.etapa_atual}')
            print(f'    DFe={existente.odoo_dfe_id}  PO={existente.odoo_po_name}')
            print(f'    picking={existente.odoo_picking_name}')
            print(f'    invoice={existente.odoo_invoice_name}')
            print(f'    transfer_status={existente.transfer_status}')
            if existente.status == 'processado' and not args.reuse_existing:
                print('\n  Recebimento JA PROCESSADO. Use --reuse-existing para forcar reprocesso (no-op).')
        else:
            print('  Sem RecebimentoLf — criaremos um novo.')

        # 4. Plano + decisao
        imprimir_plano()

        if dry_run:
            print('\n  [DRY-RUN] nada sera criado/processado. Use --confirmar.')
            return

        # 5. Criar RecebimentoLf (ou retomar)
        banner('5. Criando RecebimentoLf + lote', '-')
        if existente:
            rec = existente
            print(f'  Reusando rec_id={rec.id} (status={rec.status})')
        else:
            rec = RecebimentoLf(
                odoo_lf_invoice_id=LF_INVOICE_ID,
                numero_nf=NUMERO_NF,
                chave_nfe=CHAVE_NFE,
                cnpj_emitente=CNPJ_LF,
                company_id=COMPANY_FB,
                status='pendente',
                usuario=args.usuario,
                total_etapas=37,
            )
            db.session.add(rec)
            db.session.flush()

            lote = RecebimentoLfLote(
                recebimento_lf_id=rec.id,
                odoo_product_id=PRODUCT_ID,
                odoo_product_name=PRODUCT_NAME,
                cfop=CFOP_RETORNO,
                tipo='auto',
                lote_nome=LOTE_DESTINO,
                quantidade=QTY_ENTRADA,
                produto_tracking='lot',
                processado=False,
            )
            db.session.add(lote)
            db.session.commit()
            print(f'  RecebimentoLf id={rec.id} criado (status=pendente)')
            print(f'  RecebimentoLfLote id={lote.id} (auto, {QTY_ENTRADA} un)')

        rec_id = rec.id

        # 6. Processar sincrono
        banner(f'6. Processando recebimento {rec_id} (SINCRONO)', '-')
        print('  Etapas 0-18 vao executar (Fase 1-5). Fase 6-7 pula (CFOP 5903 retorno).')
        print('  Etapa 13-15 (criar invoice in) pode demorar com robo CIEL IT...')

        from app.recebimento.services.recebimento_lf_odoo_service import (  # noqa: E402
            RecebimentoLfOdooService,
        )
        svc = RecebimentoLfOdooService()
        try:
            resultado = svc.processar_recebimento(rec_id, usuario_nome=args.usuario)
            print(f'\n  RESULTADO: {resultado}')
        except Exception as e:
            print(f'\n  ERRO no processamento: {e}')
            rec_final = RecebimentoLf.query.get(rec_id)
            if rec_final:
                print(f'  Estado final: status={rec_final.status} '
                      f'fase={rec_final.fase_atual} etapa={rec_final.etapa_atual}')
                print(f'  Erro: {rec_final.erro_mensagem}')
            raise

        # 7. Verificar estoque DEPOIS
        banner('7. Estoque DEPOIS da entrada', '-')
        total_lf_depois = consultar_estoque(odoo, COMPANY_LF, 'LF')
        total_fb_depois = consultar_estoque(odoo, COMPANY_FB, 'FB')

        banner('8. RESUMO', '=')
        print(f'  LF: {total_lf_antes} -> {total_lf_depois} (delta={total_lf_depois - total_lf_antes})')
        print(f'  FB: {total_fb_antes} -> {total_fb_depois} (delta={total_fb_depois - total_fb_antes})')
        print(f'  Esperado: LF inalterado, FB +{QTY_ENTRADA}')
        ok_lf = abs(total_lf_depois - total_lf_antes) < 0.01
        ok_fb = abs((total_fb_depois - total_fb_antes) - QTY_ENTRADA) < 0.01
        print(f'  LF inalterado: {"OK" if ok_lf else "FAIL"}')
        print(f'  FB delta esperado: {"OK" if ok_fb else "FAIL"}')

        rec_final = RecebimentoLf.query.get(rec_id)
        print(f'\n  RecebimentoLf id={rec_id}: status={rec_final.status} '
              f'fase={rec_final.fase_atual} etapa={rec_final.etapa_atual}/{rec_final.total_etapas}')
        print(f'    DFe FB={rec_final.odoo_dfe_id}  PO={rec_final.odoo_po_name}')
        print(f'    picking={rec_final.odoo_picking_name} (id={rec_final.odoo_picking_id})')
        print(f'    invoice FB={rec_final.odoo_invoice_name} (id={rec_final.odoo_invoice_id})')
        print(f'    transfer_status={rec_final.transfer_status}')


if __name__ == '__main__':
    main()
