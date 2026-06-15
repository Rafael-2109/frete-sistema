# etapa: C3-orchestrator
# doc-dono: app/odoo/estoque/CLAUDE.md §3.1 + app/odoo/estoque/fluxos/1.2.4-entrada-retorno-industrializacao.md
"""WIRE do R2 — orchestrator C3 da ENTRADA do retorno de industrialização FB←LF.

Compõe o FLUXO L3 1.2.4 end-to-end, reproduzindo a receita provada pelo `s67`
(piloto 4870112, gate contábil fechado — `ACHADOS §"R2.3b"`). Disparado pela NF-1 de
serviço de SAÍDA da LF; escritura a entrada na FB: dá entrada do PA (NF-1 caminho A +
picking C9), baixa a conta de remessa (NF-2 montada-direto) e ajusta o custo do PA (Ic+S).

Constituição (`app/odoo/estoque/CLAUDE.md`):
  - §3.1 — orchestrator C3 SÓ COMPÕE átomos (Skill 7 + Skill 5 picking C9 + revaloração +
    descoberta); NÃO faz XML-RPC cru, NÃO usa `RecebimentoLfOdooService` (NÃO MEXER — fallback).
  - §7/§12 — fluxo perigoso = 2 níveis: cada ESCRITA é uma etapa dry-run-first, gated por
    `--confirmar` individual ("1 go fresco do Rafael por escrita Odoo"). O orchestrator NÃO
    auto-encadeia escritas entre etapas.

Átomos compostos (todos já testados isoladamente):
  - DescobertaIndustrializacaoService.descobrir_fonte_nf2 (READ)
  - EscrituracaoLfService: resolver_chave_remessa · buscar_dfe · garantir_purchase_team ·
    alinhar_dfe_lines_company · escriturar_dfe · gerar_po_from_dfe · preencher_po ·
    confirmar_po · criar_invoice_from_po · montar_invoice_entrada_direta · marcar_vinculo_r3 ·
    postar_invoice
  - StockPickingService.criar_picking_entrada_destino_manual (C9 — exceção D-V30-1)
  - RevaloracaoCustoService.revalorar_custo

Gate de sucesso (medir pelo CICLO via `invoice_origin`, NÃO saldo global — contas
compartilhadas pela empresa): ATIVA 5101010001=0 · transitória 1150100011=0 · conta PA
1150100007=+(Ic+S) · refNFe presente · 26489→0.
"""
import argparse
import logging
import sys
from typing import Any, Dict, List, Optional

from app.odoo.estoque.scripts.escrituracao import EscrituracaoLfService
from app.odoo.estoque.scripts.picking import StockPickingService
from app.odoo.estoque.scripts.revaloracao import RevaloracaoCustoService
from app.odoo.estoque.scripts.descoberta_industrializacao import DescobertaIndustrializacaoService

logger = logging.getLogger(__name__)

# ── CONSTANTS (piloto 4870112 — provados em PROD pelo s67/s63/s64) ────────────────
# 🔴 TODO FOCO 3 (consolidar em L0 `app/odoo/constants/` + IDS_FIXOS.md): account.account
#    é COMPANY-SPECIFIC — VERIFICAR CADA id contra o Odoo vivo antes de promover (Zero
#    Invenção). Hoje espelham os IDs já verificados no piloto (s67 ACC dict + s63 constants).
COMPANY_FB = 1
COMPANY_LF = 5
PARTNER_LF = 35                      # LF como fornecedor (partner) na entrada FB
UID_EXECUCAO_DEFAULT = 42            # Rafael — garantir_purchase_team (s63)

JOURNAL_ENTRI = 1084                 # NF-2: FB purchase, no_payment=22800 (ATIVA 5101010001)
OP_3252_ENTRADA = 3252               # NF-2: entrada 1902 simbólica (movimento_estoque=False)
TIPO_PEDIDO_NF1 = 'serv-industrializacao'   # DFe/PO da NF-1 serviço (whitelist escriturar_dfe)

JOURNAL_REVAL = 8                    # revaloração (general ESTOQ) — account_journal_id do wizard
ACC_TRANSIT_ID = 26842               # 1150100011 transitória — contrapartida da revaloração (NÃO CMV)

FB_PAYMENT_TERM = 2791               # 'A VISTA'
FB_PAYMENT_PROVIDER = 38             # 'SEM PAGAMENTO'
FB_PICKING_TYPE_PO = 52              # picking_type da PO (preencher_po) — Recebimentos Industrializacao FB
PT52_ENTRADA = 52                    # picking C9 (entrada manual do PA, src 26489)
LOC_SRC_26489 = 26489                # Em Transito Industrializacao (src do picking C9)
LOC_DST_FB = 8                       # FB/Estoque (dst do picking C9)
LOC_30720 = 30720                    # FB customer terceiros (deve zerar)

# Contas do GATE (id Odoo, código) — medição por CICLO (s67 ACC dict)
ACC_GATE = {
    'ATIVA':   (22800, '5101010001'),   # compensação FB (baixa na NF-2)
    'TRANSIT': (26842, '1150100011'),   # transitória (fecha na revaloração)
    'PA':      (22294, '1150100007'),   # estoque do PA (sobe +Ic+S)
}


class EntradaRetornoIndustrializacaoExecutor:
    """Orchestrator C3 do FLUXO L3 1.2.4. Services-átomos injetáveis (test-friendly)."""

    def __init__(
        self,
        odoo,
        *,
        escrit_svc: Optional[EscrituracaoLfService] = None,
        picking_svc: Optional[StockPickingService] = None,
        reval_svc: Optional[RevaloracaoCustoService] = None,
        descoberta_svc: Optional[DescobertaIndustrializacaoService] = None,
    ):
        self.odoo = odoo
        self.escrit = escrit_svc or EscrituracaoLfService(odoo=odoo)
        self.picking = picking_svc or StockPickingService(odoo=odoo)
        self.reval = reval_svc or RevaloracaoCustoService(odoo=odoo)
        self.descoberta = descoberta_svc or DescobertaIndustrializacaoService(odoo)

    # ── PLAN (READ) — pré-computa o spec do ciclo ────────────────────────────────
    def planejar(self, *, nf1_saida_lf_id: int, ciclo: Optional[str] = None) -> Dict[str, Any]:
        """READ — monta o `spec` do ciclo a partir da NF-1 de serviço de SAÍDA da LF.

        Pré-computa tudo que as etapas WRITE consomem (recomendação Rafael: orchestrator
        pré-computa via DescobertaIndustrializacaoService, menos dívida que server-side):
          - descoberta da fonte da NF-2 (componentes, total Ic, remessa, PA, lote, produção);
          - chave da remessa (R3) via referencia_ids da NF-1 de saída;
          - chave da NF-1 de saída → DFe da NF-1 na FB (caminho A).
        ZERO escrita.
        """
        desc = self.descoberta.descobrir_fonte_nf2(nf1_saida_lf_id)
        pa = desc['pa']
        ciclo = ciclo or f"RET-IND-{pa['product_id']}-{nf1_saida_lf_id}"

        # chave da remessa (R3) — referencia_ids da NF-1 de saída (vive na company LF)
        rem = self.escrit.resolver_chave_remessa(nf_saida_id=nf1_saida_lf_id, company_id=COMPANY_LF)
        chave_remessa = rem.get('chave')

        # chave da NF-1 de saída + data → localizar o DFe da NF-1 na FB
        nf1 = self.odoo.read('account.move', [nf1_saida_lf_id],
                             ['l10n_br_chave_nf', 'invoice_date'])
        nf1 = nf1[0] if nf1 else {}
        chave_nf1 = nf1.get('l10n_br_chave_nf')
        invoice_date = nf1.get('invoice_date')

        dfe_nf1_id = None
        dfe_nf1_status = None
        if chave_nf1:
            dfe = self.escrit.buscar_dfe(chave_nfe=chave_nf1, company_id=COMPANY_FB)
            dfe_nf1_id = dfe.get('dfe_id')
            dfe_nf1_status = dfe.get('status')

        # nome do lote do PA (para o picking C9 lot_dest_name) — best-effort
        pa_lote_nome = None
        if pa.get('lote'):
            try:
                lt = self.odoo.read('stock.lot', [pa['lote']], ['name'])
                pa_lote_nome = (lt[0].get('name') if lt else None)
            except Exception:
                pa_lote_nome = None

        return {
            'nf1_saida_lf_id': nf1_saida_lf_id,
            'ciclo': ciclo,
            'invoice_date': invoice_date,
            'pa_product_id': pa['product_id'],
            'pa_lote_id': pa.get('lote'),
            'pa_lote_nome': pa_lote_nome,
            'pa_qtd_faturada': pa.get('qtd_faturada'),
            'produzido_total': desc.get('produzido_total'),
            'componentes': desc['componentes'],
            'total_ic': desc['total'],
            'remessa': desc.get('remessa'),
            'chave_remessa': chave_remessa,
            'chave_nf1': chave_nf1,
            'dfe_nf1_id': dfe_nf1_id,
            'dfe_nf1_status': dfe_nf1_status,
        }

    # ── A) NF-1 serviço (caminho A) — sub-etapa 1: DFe → PO ───────────────────────
    def escriturar_nf1_po(self, spec: Dict[str, Any], *, dry_run: bool = True) -> Dict[str, Any]:
        """Compõe o caminho A até a PO: garantir team → alinhar dfe.lines → escriturar DFe →
        gerar PO. Cada átomo é dry-run-first (propaga dry_run). `alinhar_dfe_lines_company`
        NÃO tem dry_run (escreve sempre, idempotente por diff) — só é chamado no caminho WRITE."""
        passos: List[Dict[str, Any]] = []
        dfe_id = spec['dfe_nf1_id']
        team = self.escrit.garantir_purchase_team(
            user_id=UID_EXECUCAO_DEFAULT, company_id=COMPANY_FB, dry_run=dry_run)
        passos.append({'garantir_purchase_team': team})
        if not dfe_id:
            return {'status': 'FALHA', 'erro': 'dfe_nf1_id_ausente (rode planejar/buscar_dfe)',
                    'po_id': None, 'passos': passos}
        if not dry_run:
            passos.append({'alinhar_dfe_lines_company':
                           self.escrit.alinhar_dfe_lines_company(dfe_id=dfe_id, company_destino=COMPANY_FB)})
        esc = self.escrit.escriturar_dfe(dfe_id=dfe_id, l10n_br_tipo_pedido=TIPO_PEDIDO_NF1, dry_run=dry_run)
        passos.append({'escriturar_dfe': esc})
        po = self.escrit.gerar_po_from_dfe(dfe_id=dfe_id, dry_run=dry_run)
        passos.append({'gerar_po_from_dfe': po})
        return {'status': 'DRY_RUN_OK' if dry_run else po.get('status'),
                'po_id': po.get('po_id'), 'passos': passos}

    # ── A) NF-1 serviço — sub-etapa 2: PO → picking C9 → invoice ──────────────────
    def escriturar_nf1_invoice(self, spec: Dict[str, Any], *, po_id: int,
                               dry_run: bool = True) -> Dict[str, Any]:
        """Preenche/confirma a PO, cria o picking C9 do PA (exceção D-V30-1) e gera a invoice
        da NF-1 (DRAFT). O picking C9 (`criar_picking_entrada_destino_manual`) NÃO tem dry_run
        (escreve sempre) → só é chamado no caminho WRITE; em dry-run reporta o plano."""
        passos: List[Dict[str, Any]] = []
        team = self.escrit.garantir_purchase_team(
            user_id=UID_EXECUCAO_DEFAULT, company_id=COMPANY_FB, dry_run=dry_run)
        team_id = team.get('team_id')
        passos.append({'garantir_purchase_team': team})

        prep = self.escrit.preencher_po(
            po_id=po_id, team_id=team_id, payment_term_id=FB_PAYMENT_TERM,
            picking_type_id=FB_PICKING_TYPE_PO, company_id=COMPANY_FB,
            payment_provider_id=FB_PAYMENT_PROVIDER, l10n_br_tipo_pedido=TIPO_PEDIDO_NF1,
            dry_run=dry_run)
        passos.append({'preencher_po': prep})
        conf = self.escrit.confirmar_po(po_id=po_id, dry_run=dry_run)
        passos.append({'confirmar_po': conf})

        moves_data = [{
            'product_id': spec['pa_product_id'],
            'quantity': spec['pa_qtd_faturada'],
            'lot_dest_name': spec.get('pa_lote_nome') or str(spec.get('pa_lote_id')),
        }]
        if dry_run:
            passos.append({'picking_c9_PLANO': {
                'company_destino_id': COMPANY_FB, 'location_origem_id': LOC_SRC_26489,
                'location_destino_id': LOC_DST_FB, 'picking_type_id': PT52_ENTRADA,
                'partner_id': PARTNER_LF, 'origin': f"{spec['ciclo']}-PA",
                'moves_data': moves_data, 'nota': 'C9 não tem dry_run — só executa em --confirmar'}})
            inv = self.escrit.criar_invoice_from_po(po_id=po_id, dry_run=dry_run)
            passos.append({'criar_invoice_from_po': inv})
            return {'status': 'DRY_RUN_OK', 'nf1_invoice_id': inv.get('invoice_id'), 'passos': passos}

        # caminho WRITE: resolver po.line do PA → picking C9 vinculado → invoice
        po_line_id = self._resolver_po_line_do_pa(po_id, spec['pa_product_id'])
        moves_data[0]['purchase_line_id'] = po_line_id
        pick = self.picking.criar_picking_entrada_destino_manual(
            company_destino_id=COMPANY_FB, location_origem_id=LOC_SRC_26489,
            location_destino_id=LOC_DST_FB, moves_data=moves_data,
            picking_type_id=PT52_ENTRADA, origin=f"{spec['ciclo']}-PA", partner_id=PARTNER_LF)
        passos.append({'criar_picking_entrada_destino_manual': pick})
        inv = self.escrit.criar_invoice_from_po(po_id=po_id, dry_run=dry_run)
        passos.append({'criar_invoice_from_po': inv})
        return {'status': inv.get('status'), 'nf1_invoice_id': inv.get('invoice_id'),
                'po_line_id': po_line_id, 'passos': passos}

    # ── B) NF-2 insumos — MONTADA DIRETO ──────────────────────────────────────────
    def montar_nf2(self, spec: Dict[str, Any], *, dry_run: bool = True) -> Dict[str, Any]:
        """Monta a NF-2 (insumos 5902→1902) DIRETO (refuta caminho A — s66): j1084, op 3252,
        calcular_imposto=False, preços da remessa (componentes da descoberta), R3 refNFe."""
        linhas = [{
            'product_id': c['product_id'],
            'quantity': c['qty'],
            'price_unit': c['price_unit'],
        } for c in spec['componentes']]
        return self.escrit.montar_invoice_entrada_direta(
            journal_id=JOURNAL_ENTRI, partner_id=PARTNER_LF, company_id=COMPANY_FB,
            invoice_date=spec.get('invoice_date'), linhas=linhas, operacao_id=OP_3252_ENTRADA,
            move_type='in_invoice', calcular_imposto=False, invoice_origin=spec['ciclo'],
            refnfe_chave=spec.get('chave_remessa'), dry_run=dry_run)

    def postar_nf2(self, spec: Dict[str, Any], *, nf2_invoice_id: int,
                   dry_run: bool = True) -> Dict[str, Any]:
        """action_post da NF-2 → D 1150100011 / C 5101010001 ATIVA = a BAIXA da ATIVA."""
        return self.escrit.postar_invoice(invoice_id=nf2_invoice_id, company_id=COMPANY_FB, dry_run=dry_run)

    # ── C) Ajuste de custo do PA (G8 — Ic+S) ──────────────────────────────────────
    def revalorar(self, spec: Dict[str, Any], *, dry_run: bool = True) -> Dict[str, Any]:
        """Revaloração +Ic com account_id = transitória 1150100011 (NÃO CMV) → fecha a
        transitória e sobe a conta do PA. AVCO dilui no pool (gate medido pela CONTA)."""
        return self.reval.revalorar_custo(
            product_id=spec['pa_product_id'], added_value=spec['total_ic'],
            account_id=ACC_TRANSIT_ID, account_journal_id=JOURNAL_REVAL,
            company_id=COMPANY_FB, reason=f"Ic industrializacao retorno {spec['ciclo']}",
            dry_run=dry_run)

    def postar_nf1(self, spec: Dict[str, Any], *, nf1_invoice_id: int,
                   dry_run: bool = True) -> Dict[str, Any]:
        """Marca o R3 na NF-1 (invoice_origin + refNFe remessa) e posta a NF-1 (serviço)."""
        r3 = self.escrit.marcar_vinculo_r3(
            invoice_id=nf1_invoice_id, company_id=COMPANY_FB,
            invoice_origin=spec['ciclo'], refnfe_chave=spec.get('chave_remessa'), dry_run=dry_run)
        post = self.escrit.postar_invoice(invoice_id=nf1_invoice_id, company_id=COMPANY_FB, dry_run=dry_run)
        return {'status': 'DRY_RUN_OK' if dry_run else post.get('status'),
                'r3': r3, 'post': post}

    # ── GATE (READ) — medir pelo CICLO ────────────────────────────────────────────
    def medir(self, spec: Dict[str, Any], *, nf1_invoice_id: Optional[int] = None,
              nf2_invoice_id: Optional[int] = None) -> Dict[str, Any]:
        """READ — gate medido pelos LANÇAMENTOS DOS MOVES DO CICLO (NÃO saldo global —
        contas compartilhadas pela empresa, oscilam ~21M entre reads). Coleta os
        `account.move` do ciclo de 3 fontes e soma suas linhas por conta:
          - remessa: `l10n_br_chave_nf` == chave_remessa + `company_id` == FB (a busca por
            chave retorna 2 moves — FB saída + LF entrada; o filtro company isola o FB);
          - entradas: `invoice_origin` == ciclo + company FB (NF-1 e NF-2 de entrada) + ids
            explícitos passados pelas etapas;
          - revalorações: `stock.valuation.layer` do PA com o ciclo no `description` (o reason
            gravado inclui o ciclo) → `account_move_id`.

        Alvo (lote INTEIRO faturado): ATIVA=0 (remessa − entradas) · TRANSIT=0 · PA=+(Ic+S).
        Em fatura PARCIAL (rateio), a ATIVA NÃO zera — fica o saldo aberto dos PA ainda na LF
        (correto). O S do picking C9 entra no PA via SVL de entrada (conferir pelo quant).
        """
        ciclo = spec['ciclo']
        pa = spec['pa_product_id']
        move_ids, detalhe = self._coletar_moves_ciclo(
            ciclo=ciclo, pa_product_id=pa, chave_remessa=spec.get('chave_remessa'),
            extra_ids=[m for m in (nf1_invoice_id, nf2_invoice_id) if m])
        contas: Dict[str, float] = {}
        for nome, (acc_id, _cod) in ACC_GATE.items():
            contas[nome] = self._saldo_moves_conta(move_ids, acc_id)
        quants = {'26489': self._quant(LOC_SRC_26489, pa), '30720': self._quant(LOC_30720, pa)}
        return {
            'ciclo': ciclo,
            'pa_product_id': pa,
            'contas': contas,
            'quants': quants,
            'moves_incluidos': detalhe,
            'alvo': {'ATIVA': 0, 'TRANSIT': 0, 'PA_min': spec.get('total_ic'),
                     '26489': 0, '30720': 0},
            'nota': ('ATIVA zera só com o lote INTEIRO faturado (rateio parcial deixa saldo '
                     'aberto = correto). S do picking C9 entra no PA via SVL — conferir o quant.'),
        }

    # ── helpers de resolução (READ) ───────────────────────────────────────────────
    def _resolver_po_line_do_pa(self, po_id: int, product_id: int) -> Optional[int]:
        """READ — localiza a purchase.order.line do PA na PO (para vincular ao picking C9)."""
        try:
            rows = self.odoo.search_read(
                'purchase.order.line',
                [('order_id', '=', po_id), ('product_id', '=', product_id)], ['id'])
            return rows[0]['id'] if isinstance(rows, list) and rows else None
        except Exception as e:
            logger.warning(f'_resolver_po_line_do_pa falhou: {str(e)[:120]}')
            return None

    def _coletar_moves_ciclo(self, *, ciclo: str, pa_product_id: int,
                             chave_remessa: Optional[str],
                             extra_ids: Optional[List[int]] = None):
        """READ — coleta os account.move do ciclo (remessa + entradas + revalorações).
        Queries DIRECIONADAS (por chave/origin/produto) — nunca varre a conta inteira."""
        move_ids = set(extra_ids or [])
        detalhe: List[Dict[str, Any]] = []
        # remessa (NF de saída FB, por chave + company FB — isola do espelho LF)
        if chave_remessa:
            for r in self._sr('account.move',
                              [('l10n_br_chave_nf', '=', chave_remessa), ('company_id', '=', COMPANY_FB)],
                              ['id', 'name']):
                move_ids.add(r['id'])
                detalhe.append({'tipo': 'remessa', 'id': r['id'], 'name': r.get('name')})
        # entradas (NF-1 + NF-2 da FB, por invoice_origin)
        for e in self._sr('account.move',
                          [('invoice_origin', '=', ciclo), ('company_id', '=', COMPANY_FB)],
                          ['id', 'name']):
            move_ids.add(e['id'])
            detalhe.append({'tipo': 'entrada', 'id': e['id'], 'name': e.get('name')})
        # revalorações (SVL do PA com o ciclo no description → account.move)
        for s in self._sr('stock.valuation.layer',
                          [('product_id', '=', pa_product_id), ('description', 'like', ciclo)],
                          ['account_move_id', 'value']):
            am = s.get('account_move_id')
            amid = (am[0] if isinstance(am, list) else am) if am else None
            if amid:
                move_ids.add(amid)
                detalhe.append({'tipo': 'revaloracao', 'id': amid, 'value': s.get('value')})
        return move_ids, detalhe

    def _saldo_moves_conta(self, move_ids, account_id: int) -> float:
        """READ — soma debit-credit das linhas (moves do ciclo ∩ conta)."""
        if not move_ids:
            return 0.0
        ml = self._sr('account.move.line',
                      [('move_id', 'in', list(move_ids)), ('account_id', '=', account_id)],
                      ['debit', 'credit'])
        return round(sum((l.get('debit') or 0) - (l.get('credit') or 0) for l in ml), 2)

    def _quant(self, location_id: int, product_id: int) -> float:
        """READ — quantidade do produto numa location."""
        rows = self._sr('stock.quant',
                        [('location_id', '=', location_id), ('product_id', '=', product_id)],
                        ['quantity'])
        return round(sum(r.get('quantity') or 0 for r in rows), 3)

    def _sr(self, model: str, domain: list, fields: list) -> list:
        """search_read defensivo (retorna [] se não-lista — robusto a mock/erro)."""
        try:
            rows = self.odoo.search_read(model, domain, fields)
            return rows if isinstance(rows, list) else []
        except Exception as e:
            logger.warning(f'_sr {model} falhou: {str(e)[:120]}')
            return []


# ── CLI ───────────────────────────────────────────────────────────────────────────
_MODOS = ('plan', 'escriturar-nf1-po', 'escriturar-nf1-invoice',
          'montar-nf2', 'postar-nf2', 'revalorar', 'postar-nf1', 'medir')


def main(argv=None):
    ap = argparse.ArgumentParser(description='WIRE do R2 — entrada de retorno de industrialização (FLUXO L3 1.2.4)')
    ap.add_argument('modo', choices=_MODOS, help='etapa a executar')
    ap.add_argument('--nf1-saida-lf', type=int, required=True, help='account.move da NF-1 serviço de SAÍDA da LF')
    ap.add_argument('--ciclo', type=str, default=None, help="invoice_origin comum (ex.: 'RET-IND-4870112-PILOTO')")
    ap.add_argument('--po-id', type=int, default=None, help='PO da NF-1 (escriturar-nf1-invoice)')
    ap.add_argument('--nf1-invoice-id', type=int, default=None, help='invoice da NF-1 (postar-nf1)')
    ap.add_argument('--nf2-invoice-id', type=int, default=None, help='invoice da NF-2 (postar-nf2)')
    ap.add_argument('--confirmar', action='store_true', help='EXECUTA a escrita (default = dry-run)')
    args = ap.parse_args(argv)

    from app.odoo.utils.connection import get_odoo_connection
    import json
    odoo = get_odoo_connection()
    assert odoo.authenticate(), 'falha autenticacao Odoo'
    wire = EntradaRetornoIndustrializacaoExecutor(odoo)
    spec = wire.planejar(nf1_saida_lf_id=args.nf1_saida_lf, ciclo=args.ciclo)
    dry = not args.confirmar

    if args.modo == 'plan':
        out = spec
    elif args.modo == 'escriturar-nf1-po':
        out = wire.escriturar_nf1_po(spec, dry_run=dry)
    elif args.modo == 'escriturar-nf1-invoice':
        out = wire.escriturar_nf1_invoice(spec, po_id=args.po_id, dry_run=dry)
    elif args.modo == 'montar-nf2':
        out = wire.montar_nf2(spec, dry_run=dry)
    elif args.modo == 'postar-nf2':
        out = wire.postar_nf2(spec, nf2_invoice_id=args.nf2_invoice_id, dry_run=dry)
    elif args.modo == 'revalorar':
        out = wire.revalorar(spec, dry_run=dry)
    elif args.modo == 'postar-nf1':
        out = wire.postar_nf1(spec, nf1_invoice_id=args.nf1_invoice_id, dry_run=dry)
    elif args.modo == 'medir':
        out = wire.medir(spec)
    else:
        out = {'erro': f'modo desconhecido: {args.modo}'}

    print(json.dumps({'modo': args.modo, 'dry_run': dry, 'resultado': out},
                     default=str, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main(sys.argv[1:])
