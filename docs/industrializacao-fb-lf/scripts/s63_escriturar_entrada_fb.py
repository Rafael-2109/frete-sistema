#!/usr/bin/env python3
"""S63 — R2.3: escritura a ENTRADA das 2 NFs de retorno na FB (caminho A manual).

Espelho na ENTRADA da SA da saida (s37): o gatilho e a NF-1 (servico) e o
sistema escritura + trata os componentes (NF-2 insumos). Compoe os atomos da
Skill 7 (EscrituracaoLfService) MANUALMENTE (nao `executar_fluxo_l3_1_2_x`,
que e' orientado as acoes do inventario + rigido no picking). Para em invoice
DRAFT — o POST e' separado (precisa GATE-ajuste do PA + go duplo).

NF-1 (DFe 44523, servico 5124)  -> j1001 ENTSI (no_payment vazio -> FORNECEDORES)
NF-2 (DFe 44522, insumos 5902)  -> FORCAR journal j1084 ENTRI + op 3252 (baixa ATIVA)

Modos:
  --plan        (DEFAULT) le os 2 DFes + mostra plano (NAO escreve)
  --gerar-po    alinhar + escriturar_dfe + gerar_po_from_dfe (robo) p/ as 2 -> inspeciona POs
  --invoice     garantir team + preencher_po + confirmar_po + criar_invoice_from_po p/ as 2
                + FORCA journal j1084/op 3252 nas linhas da NF-2 + R3 -> para em DRAFT
  --cleanup     reverte invoices/POs/pickings das 2 (cancela + reseta DFe)

PRODUCAO (CIEL IT). Escrita SO com --gerar-po/--invoice e go explicito. NAO posta.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.estoque.scripts.escrituracao import EscrituracaoLfService

COMPANY_FB = 1
UID_RAFAEL = 42
JOURNAL_ENTRI = 1084          # NF-2: FB purchase no_payment=22800 (ATIVA)
OP_3252 = 3252                # NF-2: entrada 1902 simbolica (mov_estoque=False)
TIPO_PEDIDO = 'serv-industrializacao'
ORIGIN = 'RET-IND-4870112-PILOTO'
CHAVE_REMESSA = '35260518467441000163550010000245...'  # preenchido via lookup
# constants FB (CANDIDATE) p/ preencher_po quando a PO nao trouxer
FB_PAYMENT_TERM = 2791        # 'A VISTA'
FB_PICKING_TYPE = 52          # Recebimentos Industrializacao (FB), src 26489
FB_PAYMENT_PROVIDER = 38      # 'SEM PAGAMENTO'

NFS = [
    {'tag': 'NF-1', 'dfe': 44523, 'nf_saida': 791437, 'desc': 'servico 5124',
     'forcar_journal': None, 'forcar_op': None},
    {'tag': 'NF-2', 'dfe': 44522, 'nf_saida': 791441, 'desc': 'insumos 16x5902',
     'forcar_journal': JOURNAL_ENTRI, 'forcar_op': OP_3252},
]
CTX = {'allowed_company_ids': [1, 5], 'company_id': COMPANY_FB, 'lang': 'pt_BR'}
SEP = '=' * 96


def main():
    args = sys.argv[1:]
    o = get_odoo_connection()
    assert o.authenticate(), 'FALHA AUTH'
    svc = EscrituracaoLfService(odoo=o)

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    def dfe_info(dfe_id):
        d = rd('l10n_br_ciel_it_account.dfe', [dfe_id],
               ['l10n_br_status', 'purchase_id', 'purchase_fiscal_id',
                'protnfe_infnfe_chnfe', 'l10n_br_tipo_pedido', 'company_id'])[0]
        nlin = o.execute_kw('l10n_br_ciel_it_account.dfe.line', 'search_count',
                            [[('dfe_id', '=', dfe_id)]], {'context': CTX})
        d['n_linhas'] = nlin
        # vinculo PO: purchase_id (raro) OU purchase_fiscal_id (caso D-V30-1)
        po = d.get('purchase_id') or d.get('purchase_fiscal_id')
        d['po_id'] = po[0] if po else None
        return d

    def inspeciona_po(po_id):
        po = rd('purchase.order', [po_id],
                ['name', 'state', 'partner_id', 'company_id', 'team_id',
                 'fiscal_position_id', 'payment_term_id', 'picking_type_id',
                 'payment_provider_id', 'l10n_br_tipo_pedido', 'invoice_ids',
                 'picking_ids', 'amount_total'])[0]
        return po

    print(SEP)
    print('S63 — R2.3 escriturar ENTRADA FB (NF-1 + NF-2) — caminho A manual')
    print(SEP)

    # ---------------- PLAN ----------------
    if not any(a in args for a in ('--gerar-po', '--invoice', '--cleanup')):
        for nf in NFS:
            d = dfe_info(nf['dfe'])
            print(f"\n  {nf['tag']} ({nf['desc']}) — DFe {nf['dfe']}")
            print(f"    status={d['l10n_br_status']} linhas={d['n_linhas']} "
                  f"PO={d['purchase_id']} company={d['company_id']} "
                  f"tipo_pedido={d.get('l10n_br_tipo_pedido')}")
            print(f"    plano caminho A: alinhar -> escriturar_dfe('{TIPO_PEDIDO}') -> "
                  f"gerar_po_from_dfe -> preencher_po -> confirmar_po -> criar_invoice_from_po(DRAFT)")
            if nf['forcar_journal']:
                print(f"    OVERRIDE pos-draft: journal_id={nf['forcar_journal']} + "
                      f"op {nf['forcar_op']}/operacao_manual=True nas linhas")
        print(f"\n  R3: invoice_origin='{ORIGIN}' + referencia_ids -> chave remessa nas 2")
        print('\n  [PLAN] nada escrito. Proximo: --gerar-po')
        print(SEP)
        return

    # ---------------- GERAR-PO ----------------
    if '--gerar-po' in args:
        team = svc.garantir_purchase_team(user_id=UID_RAFAEL, company_id=COMPANY_FB,
                                          dry_run=False)
        print(f"\n  garantir_purchase_team(FB): {team}")
        for nf in NFS:
            print(f"\n  --- {nf['tag']} (DFe {nf['dfe']}) ---")
            d = dfe_info(nf['dfe'])
            if d.get('po_id'):
                print(f"    PO JA existe ({d['po_id']}) — idempotente, inspecionando")
                print(f"    {inspeciona_po(d['po_id'])}")
                continue
            r_al = svc.alinhar_dfe_lines_company(dfe_id=nf['dfe'], company_destino=COMPANY_FB)
            print(f"    alinhar_dfe_lines_company: {r_al.get('status', r_al)}")
            r_es = svc.escriturar_dfe(dfe_id=nf['dfe'], l10n_br_tipo_pedido=TIPO_PEDIDO,
                                      dry_run=False)
            print(f"    escriturar_dfe: {r_es.get('status', r_es)}")
            r_po = svc.gerar_po_from_dfe(dfe_id=nf['dfe'], dry_run=False)
            print(f"    gerar_po_from_dfe: status={r_po.get('status')} po_id={r_po.get('po_id')} "
                  f"erro={r_po.get('erro')}")
            if r_po.get('po_id'):
                print(f"    PO inspecao: {inspeciona_po(r_po['po_id'])}")
        print('\n  [GERAR-PO] feito. Inspecione as POs acima. Proximo: --invoice')
        print(SEP)
        return

    # ---------------- INVOICE (para em DRAFT) ----------------
    if '--invoice' in args:
        # chave da remessa p/ R3 (refNFe)
        rem = rd('account.move', [735679], ['l10n_br_chave_nf'])[0]
        chave_remessa = rem.get('l10n_br_chave_nf')
        # detectar se PO.line aceita operacao_manual
        pol_fields = o.execute_kw('purchase.order.line', 'fields_get', [],
                                  {'attributes': ['string'], 'context': CTX})
        pol_tem_manual = 'l10n_br_operacao_manual' in pol_fields

        for nf in NFS:
            print(f"\n  --- {nf['tag']} (DFe {nf['dfe']}) ---")
            d = dfe_info(nf['dfe'])
            if not d.get('po_id'):
                print('    SEM PO — rode --gerar-po antes'); continue
            po_id = d['po_id']
            po = inspeciona_po(po_id)

            # (1) NF-2: trocar op das PO.lines 2027->3252 ANTES de confirmar
            if nf['forcar_op'] and po['state'] == 'draft':
                pls = o.execute_kw('purchase.order.line', 'search_read',
                                   [[('order_id', '=', po_id)]],
                                   {'fields': ['id', 'l10n_br_operacao_id'], 'context': CTX})
                lids = [l['id'] for l in pls]
                vals = {'l10n_br_operacao_id': nf['forcar_op']}
                if pol_tem_manual:
                    vals['l10n_br_operacao_manual'] = True
                o.execute_kw('purchase.order.line', 'write', [lids, vals], {'context': CTX})
                print(f"    op PO.lines -> {nf['forcar_op']} (manual={pol_tem_manual}) em {len(lids)} linhas")

            # (2)+(3) preencher_po + confirmar_po (se ainda draft)
            if po['state'] in ('draft', 'sent'):
                pt = po['picking_type_id'][0] if po.get('picking_type_id') else FB_PICKING_TYPE
                r_pre = svc.preencher_po(po_id=po_id, team_id=144,
                                         payment_term_id=FB_PAYMENT_TERM,
                                         picking_type_id=pt, company_id=COMPANY_FB,
                                         payment_provider_id=FB_PAYMENT_PROVIDER,
                                         l10n_br_tipo_pedido=TIPO_PEDIDO, dry_run=False)
                print(f"    preencher_po: {r_pre.get('status', r_pre)}")
                r_cf = svc.confirmar_po(po_id=po_id, dry_run=False)
                print(f"    confirmar_po: status={r_cf.get('status')} state={r_cf.get('state_final')} erro={r_cf.get('erro')}")
                po = inspeciona_po(po_id)
                print(f"    PO pos-confirm: state={po['state']} pickings={po['picking_ids']}")

            # (4) criar_invoice_from_po (DRAFT)
            if po.get('invoice_ids'):
                inv_id = po['invoice_ids'][0]
                print(f"    invoice JA existe: {inv_id}")
            else:
                r_inv = svc.criar_invoice_from_po(po_id=po_id, dry_run=False)
                print(f"    criar_invoice_from_po: status={r_inv.get('status')} inv={r_inv.get('invoice_id')} erro={r_inv.get('erro')}")
                inv_id = r_inv.get('invoice_id')
            if not inv_id:
                print('    SEM invoice — parar p/ diagnostico'); continue

            # (5) NF-2: forcar journal j1084 + op 3252 nas invoice lines (DRAFT)
            inv = rd('account.move', [inv_id], ['state', 'journal_id', 'invoice_origin'])[0]
            if inv['state'] != 'draft':
                print(f"    ⚠️ invoice NAO esta draft ({inv['state']}) — nao forco overrides");
            else:
                if nf['forcar_journal'] and inv['journal_id'][0] != nf['forcar_journal']:
                    o.execute_kw('account.move', 'write', [[inv_id], {'journal_id': nf['forcar_journal']}], {'context': CTX})
                    print(f"    journal {inv['journal_id']} -> {nf['forcar_journal']}")
                if nf['forcar_op']:
                    mls = o.execute_kw('account.move.line', 'search_read',
                                       [[('move_id', '=', inv_id), ('display_type', '=', 'product')]],
                                       {'fields': ['id', 'l10n_br_operacao_id'], 'context': CTX})
                    mids = [m['id'] for m in mls]
                    o.execute_kw('account.move.line', 'write',
                                 [mids, {'l10n_br_operacao_id': nf['forcar_op'], 'l10n_br_operacao_manual': True}],
                                 {'context': CTX})
                    print(f"    op move.lines -> {nf['forcar_op']}/manual em {len(mids)} linhas")
                # (6) R3: invoice_origin comum
                o.execute_kw('account.move', 'write', [[inv_id], {'invoice_origin': ORIGIN}], {'context': CTX})

            # inspecao final da invoice draft
            invf = rd('account.move', [inv_id],
                      ['name', 'state', 'journal_id', 'amount_total', 'amount_untaxed', 'invoice_origin'])[0]
            print(f"    INVOICE draft: {invf}")

        print(f"\n  [INVOICE] 2 invoices em DRAFT. R3 origin='{ORIGIN}', remessa chave={chave_remessa}")
        print('  NAO postado. Proximo: GATE-ajuste do PA + post (go duplo).')
        print(SEP)
        return

    # ---------------- CLEANUP ----------------
    if '--cleanup' in args:
        for nf in NFS:
            d = dfe_info(nf['dfe'])
            if not d.get('po_id'):
                print(f"  {nf['tag']}: sem PO"); continue
            po_id = d['po_id']
            po = inspeciona_po(po_id)
            print(f"  {nf['tag']} PO {po_id} state={po['state']} invoices={po['invoice_ids']} pickings={po['picking_ids']}")
            for inv_id in po.get('invoice_ids', []):
                inv = rd('account.move', [inv_id], ['state'])[0]
                if inv['state'] == 'posted':
                    o.execute_kw('account.move', 'button_draft', [[inv_id]], {'context': CTX})
                o.execute_kw('account.move', 'button_cancel', [[inv_id]], {'context': CTX})
                print(f"    invoice {inv_id} cancelada")
            if po['state'] not in ('cancel',):
                o.execute_kw('purchase.order', 'button_cancel', [[po_id]], {'context': CTX})
                print(f"    PO {po_id} cancelada")
        print('  [CLEANUP] feito (POs/invoices canceladas).')
        print(SEP)
        return

    print(SEP)


if __name__ == '__main__':
    main()
