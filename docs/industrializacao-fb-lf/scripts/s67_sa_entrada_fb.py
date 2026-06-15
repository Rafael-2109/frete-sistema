#!/usr/bin/env python3
"""S67 — SA da ENTRADA FB (piloto): monta NF-2 DIRETO + revalora PA + posta NF-1 + mede.

Implementa a LOGICA da server action da ENTRADA (espelho da saida s37/s54). O
gatilho e' a NF-1 (servico, ja em DRAFT via caminho A — s64). A SA faz server-side:
  (a) monta a NF-2 (insumos) DIRETO  (account.move in_invoice, estilo s62/GATE-FB)
                                      -> postar -> baixa a ATIVA 5101010001 (-279,23)
  (b) revalora o PA +Ic              (wizard stock.valuation.layer.revaluation,
                                      account_id = conta que SOBRA na NF-2 = 1150100011)
                                      -> D 1150100007 PA / C 1150100011 -> PA=Ic+S, transit zera
  (c) posta a NF-1 (servico)         -> PA fica com S (cruza SVL do picking C9)
  (d) vinculo R3                     (refNFe remessa + invoice_origin comum)
Mede o gate de sucesso.

POR QUE DIRETO (nao caminho A): s66 PROVOU que a NF-2 via PO/`criar_invoice` do robo
ganha TAX LINES ESPELHO (C na mesma conta das product lines) que auto-cancelam =>
o no_payment do j1084 NAO atua (Δ ATIVA = 0). O GATE-FB (s62) montou in_invoice
DIRETO com `l10n_br_calcular_imposto=False` (SEM tax lines espelho) e a ATIVA BAIXOU.

Modos (cada ESCRITA exige go FRESCO do Rafael; 1 comando por escrita):
  --plan         (DEFAULT, READ) verifica estado vivo + investiga vinculo + mostra plano
  --montar-nf2   monta a NF-2 in_invoice DRAFT (j1084, 16 insumos op 3252, precos remessa, vinculo R3)
  --postar-nf2   action_post da NF-2 -> mede Δ ATIVA + identifica a conta-transito que sobra
  --revalorar    wizard revaluation +Ic (account_id=transito) -> PA sobe, transito zera
  --postar-nf1   action_post da NF-1 792219 (servico)
  --medir        gate de sucesso (PA=Ic+S, ATIVA, transito, CMV/CPV, 26489, 30720)
  --reverter ID  revaloracao inversa + draft NF-1 + draft/unlink NF-2 (ID da NF-2 montada)

PRODUCAO (CIEL IT). j1084/j1001 hash=False (reversiveis). Nada postado sem go.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

# contextos
CTX = {'allowed_company_ids': [1, 5], 'company_id': 1, 'lang': 'pt_BR'}   # montar/postar (s62/s64)
CTX_FB = {'allowed_company_ids': [1], 'company_id': 1, 'lang': 'pt_BR'}   # revaloracao PA (s66)

# constantes do piloto 4870112
JOURNAL_ENTRI = 1084          # FB purchase, no_payment=22800 (ATIVA 5101010001)
PARTNER_LF = 35               # LF como fornecedor na FB
OP_3252 = 3252                # entrada 1902 simbolica (movimento_estoque=False)
REMESSA = 735679              # RPI/2026/00245 — fonte canonica dos precos (16 insumos)
DFE_NF2 = 44522               # DFe insumos (status 06, livre p/ vincular)
NF1 = 792219                  # servico, DRAFT (caminho A, s64) — gatilho da SA
PA = 27834                    # [4870112] MOLHO SHOYU PET
PICKING_PA = 325347           # picking C9 que trouxe o PA p/ FB (SVL 26,23)
PO_NF1 = 43464                # PO da NF-1 (servico)
NF2_CAMINHO_A = 791950        # NF-2 do caminho A (DEVE estar deletada por s66)
PO_NF2_CANCELADA = 43465      # PO do caminho A (DEVE estar cancelada por s66)
JOURNAL_REVAL = 8             # journal general ESTOQ (revaloracao)
ORIGIN = 'RET-IND-4870112-PILOTO'

# contas (id Odoo -> codigo contabil)
ACC = {
    'ATIVA':   (22800, '5101010001'),   # compensacao FB (no_payment do j1084)
    'TRANSIT': (26842, '1150100011'),   # RECEBIMENTO FISICO FISCAL (input PA + alvo da revaloracao)
    'PA':      (22294, '1150100007'),   # valoracao do PA (categ 193)
    'CMV':     (22611, '3202010001'),   # so p/ medir (caminho A debitava aqui)
    'CPV':     (22527, '3201000001'),   # so p/ medir (NF-1 servico)
}
LOC_26489 = 26489             # Em Transito Industrializacao (deve zerar)
LOC_30720 = 30720             # FB customer terceiros (deve zerar)
SEP = '=' * 96


def main():
    args = sys.argv[1:]
    o = get_odoo_connection()
    assert o.authenticate(), 'FALHA AUTH'

    def rd(model, ids, fields, ctx=CTX):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': ctx})

    def rr(model, dom, fields, ctx=CTX, **kw):
        kw2 = {'fields': fields, 'context': ctx}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    def saldo(conta_id, ctx=CTX):
        rg = o.execute_kw('account.move.line', 'read_group',
                          [[('account_id', '=', conta_id), ('company_id', '=', 1),
                            ('parent_state', '=', 'posted')], ['balance:sum'], []],
                          {'context': ctx})
        return round(rg[0].get('balance') or 0.0, 2) if rg else 0.0

    def move_lines(inv):
        mls = rr('account.move.line', [('move_id', '=', inv)],
                 ['account_id', 'debit', 'credit', 'display_type'])
        agg = {}
        for l in mls:
            a = l['account_id'][1] if l.get('account_id') else '(sem)'
            d, c = agg.get(a, (0, 0)); agg[a] = (round(d + l['debit'], 2), round(c + l['credit'], 2))
        return agg

    def existe(model, rid):
        try:
            return bool(o.execute_kw(model, 'search_count', [[('id', '=', rid)]], {'context': CTX}))
        except Exception:
            return False

    def pa_estado():
        p = rd('product.product', [PA], ['standard_price'], CTX_FB)[0]
        q = rr('stock.quant', [('product_id', '=', PA), ('location_id', '=', 8)],
               ['lot_id', 'quantity', 'value'], CTX_FB)
        return p['standard_price'], q

    # fonte canonica dos precos: 16 linhas product da remessa
    rem_lines = rr('account.move.line',
                   [('move_id', '=', REMESSA), ('display_type', '=', 'product')],
                   ['product_id', 'quantity', 'price_unit', 'price_subtotal'])
    ic_total = round(sum(l['price_subtotal'] for l in rem_lines), 2)

    # ============================ PLAN (READ) ============================
    if not any(a in args for a in ('--montar-nf2', '--postar-nf2', '--revalorar',
                                    '--postar-nf1', '--medir', '--reverter')):
        print(SEP); print('S67 — SA da ENTRADA FB (plan / READ-only)'); print(SEP)

        # 1) estado vivo (pre-condicoes)
        print('\n[1] ESTADO VIVO (pre-condicoes do piloto):')
        nf1 = rd('account.move', [NF1], ['name', 'state', 'journal_id', 'amount_untaxed',
                                         'amount_total', 'invoice_origin', 'invoice_date'])[0]
        print(f"  NF-1 servico {NF1}: {nf1['name']} state={nf1['state']} journal={nf1['journal_id']} "
              f"untax={nf1['amount_untaxed']} total={nf1['amount_total']} date={nf1['invoice_date']} origin={nf1['invoice_origin']}")
        pk = rd('stock.picking', [PICKING_PA], ['name', 'state'])[0]
        print(f"  picking PA {PICKING_PA}: {pk['name']} state={pk['state']}")
        po = rd('purchase.order', [PO_NF1], ['name', 'state', 'invoice_ids'])[0]
        print(f"  PO NF-1 {PO_NF1}: {po['name']} state={po['state']} invoices={po['invoice_ids']}")
        j = rd('account.journal', [JOURNAL_ENTRI],
               ['name', 'code', 'type', 'l10n_br_no_payment', 'account_no_payment_id',
                'restrict_mode_hash_table'])[0]
        print(f"  j1084 ENTRI: {j['code']} type={j['type']} no_payment={j['l10n_br_no_payment']} "
              f"conta_no_pay={j['account_no_payment_id']} hash={j['restrict_mode_hash_table']}")
        # NF-2 caminho A + PO devem estar limpas
        nf2a = existe('account.move', NF2_CAMINHO_A)
        poc = rd('purchase.order', [PO_NF2_CANCELADA], ['name', 'state'])[0] if existe('purchase.order', PO_NF2_CANCELADA) else None
        print(f"  NF-2 caminho A {NF2_CAMINHO_A}: {'AINDA EXISTE ⚠️' if nf2a else 'deletada ✅'}")
        print(f"  PO caminho A {PO_NF2_CANCELADA}: {(poc['state'] + (' ✅' if poc and poc['state']=='cancel' else ' ⚠️')) if poc else 'inexistente'}")

        # 2) DFe + como vincular a invoice (R2/R3)
        print('\n[2] DFe da NF-2 (insumos) + vinculo:')
        d = rd('l10n_br_ciel_it_account.dfe', [DFE_NF2],
               ['l10n_br_status', 'purchase_id', 'purchase_fiscal_id', 'company_id',
                'protnfe_infnfe_chnfe', 'move_id' if False else 'l10n_br_status'])[0]
        nlin = o.execute_kw('l10n_br_ciel_it_account.dfe.line', 'search_count',
                            [[('dfe_id', '=', DFE_NF2)]], {'context': CTX})
        print(f"  DFe {DFE_NF2}: status={d['l10n_br_status']} linhas={nlin} "
              f"purchase_id={d.get('purchase_id')} purchase_fiscal_id={d.get('purchase_fiscal_id')} company={d['company_id']}")
        dfe_fields = o.execute_kw('l10n_br_ciel_it_account.dfe', 'fields_get', [],
                                  {'attributes': ['string', 'relation'], 'context': CTX})
        dfe_move = {k: dfe_fields[k].get('relation') for k in dfe_fields
                    if 'move' in k or 'invoice' in k or 'fatura' in k}
        print(f"  DFe campos move/invoice: {dfe_move}")

        # 3) referencia_ids (refNFe) — modelo + template da NF-2 de SAIDA (791441, ja vinculada s59)
        print('\n[3] referencia_ids (refNFe) — modelo + template da saida:')
        am_fields = o.execute_kw('account.move', 'fields_get', [],
                                 {'attributes': ['string', 'relation', 'type'], 'context': CTX})
        ref_fields = {k: (am_fields[k].get('type'), am_fields[k].get('relation'))
                      for k in am_fields if 'referencia' in k.lower() or 'refnfe' in k.lower()
                      or 'ref_nfe' in k.lower() or 'nfe_ref' in k.lower()}
        print(f"  campos account.move c/ 'referencia/refNFe': {ref_fields}")
        rem_chave = rd('account.move', [REMESSA], ['l10n_br_chave_nf', 'name'])[0]
        print(f"  remessa {REMESSA}: {rem_chave.get('name')} chave={rem_chave.get('l10n_br_chave_nf')}")
        # tentar ler o template na NF-2 de saida 791441
        for refcampo in [k for k in ref_fields if ref_fields[k][0] in ('one2many', 'many2many')]:
            try:
                saida = rd('account.move', [791441], [refcampo])[0]
                ref_ids = saida.get(refcampo) or []
                print(f"  NF-2 saida 791441.{refcampo} = {ref_ids}")
                if ref_ids:
                    rel = ref_fields[refcampo][1]
                    rf = o.execute_kw(rel, 'fields_get', [], {'attributes': ['string'], 'context': CTX})
                    chave_field = [k for k in rf if 'chave' in k.lower() or 'refnfe' in k.lower() or 'chnfe' in k.lower()]
                    sample = rd(rel, [ref_ids[0]], list(rf.keys())[:25])[0]
                    print(f"    modelo {rel}: campos-chave={chave_field}")
                    print(f"    sample[0] = { {k: v for k, v in sample.items() if v} }")
            except Exception as e:
                print(f"    {refcampo}: erro lendo template ({str(e)[:80]})")

        # 4) saldos + PA + remessa
        print('\n[4] SALDOS (FB, posted) + PA + remessa:')
        for k, (cid, cod) in ACC.items():
            print(f"  {k:8} {cod} (id {cid}): {saldo(cid)}")
        std, q = pa_estado()
        print(f"  PA std_price={std} quant={q}")
        print(f"  Ic total (remessa untax, 16 insumos) = {ic_total}  (alvo da baixa ATIVA + da revaloracao)")
        print(f"  remessa produtos: {[(l['product_id'][0], round(l['price_subtotal'],2)) for l in rem_lines]}")
        loc26489 = rr('stock.quant', [('location_id', '=', LOC_26489), ('product_id', '=', PA)],
                      ['quantity'], CTX_FB)
        loc30720 = rr('stock.quant', [('location_id', '=', LOC_30720), ('product_id', '=', PA)],
                      ['quantity'], CTX_FB)
        print(f"  quant PA em 26489={loc26489} | 30720={loc30720} (devem zerar no fim)")

        # 5) plano
        print('\n[5] PLANO (cada passo = 1 go fresco):')
        print(f"  (a) --montar-nf2  : in_invoice DRAFT j1084, partner LF=35, date={nf1['invoice_date']},")
        print(f"                      16 linhas (op 3252 + operacao_manual=True, precos da remessa {REMESSA}),")
        print(f"                      l10n_br_calcular_imposto=False, NAO rodar onchange_..._btn,")
        print(f"                      vinculo R3 (refNFe remessa + invoice_origin='{ORIGIN}' + DFe {DFE_NF2} best-effort)")
        print(f"  (b) --postar-nf2  : action_post -> esperado D 1150100011 {ic_total} / C 5101010001 ATIVA {ic_total} (Δ -{ic_total})")
        print(f"  (c) --revalorar   : revaluation +{ic_total}, account_id=TRANSIT(26842) -> D PA / C 1150100011 -> PA=Ic+S, transit zera")
        print(f"  (d) --postar-nf1  : action_post {NF1} -> servico (cruza SVL picking C9)")
        print(f"  (e) --medir       : gate (PA~305,46, ATIVA baixada, transit=0, 26489=0, 30720=0)")
        print('\n  [PLAN] nada escrito. Proximo: --montar-nf2 (apos go).')
        print(SEP)
        return

    # ============================ MONTAR NF-2 (WRITE) ============================
    if '--montar-nf2' in args:
        # guard: NF-2 do caminho A nao pode estar viva (evita duplicacao)
        if existe('account.move', NF2_CAMINHO_A):
            print(f"  ⚠️ NF-2 caminho A {NF2_CAMINHO_A} AINDA EXISTE — limpar antes (s66 --cleanup). ABORT."); return
        nf1 = rd('account.move', [NF1], ['invoice_date'])[0]
        inv_date = nf1['invoice_date']
        # linhas: produtos da remessa (invariante 5902=5901), op 3252 simbolica
        inv_lines = [(0, 0, {
            'product_id': l['product_id'][0],
            'quantity': l['quantity'],
            'price_unit': l['price_unit'],
            'l10n_br_operacao_id': OP_3252,
            'l10n_br_operacao_manual': True,   # senao onchange apaga a op (gotcha s24/s62)
        }) for l in rem_lines]
        move_vals = {
            'move_type': 'in_invoice',
            'journal_id': JOURNAL_ENTRI,
            'company_id': 1,
            'partner_id': PARTNER_LF,
            'invoice_date': inv_date,
            'l10n_br_calcular_imposto': False,   # SEM tax lines espelho (a chave do GATE-FB)
            'invoice_origin': ORIGIN,            # R3: origin comum com a NF-1
            'invoice_line_ids': inv_lines,
        }
        mid = o.execute_kw('account.move', 'create', [move_vals], {'context': CTX})
        print(f"  NF-2 in_invoice DRAFT criada id={mid} ({len(inv_lines)} linhas, op {OP_3252}, calc_imposto=False)")

        # R3 best-effort: refNFe da remessa (campo descoberto no --plan)
        rem_chave = rd('account.move', [REMESSA], ['l10n_br_chave_nf'])[0].get('l10n_br_chave_nf')
        try:
            am_fields = o.execute_kw('account.move', 'fields_get', [],
                                     {'attributes': ['type', 'relation'], 'context': CTX})
            refcampo = next((k for k in am_fields if ('referencia' in k.lower() or 'refnfe' in k.lower())
                             and am_fields[k].get('type') in ('one2many', 'many2many')), None)
            if refcampo and rem_chave:
                rel = am_fields[refcampo].get('relation')
                rf = o.execute_kw(rel, 'fields_get', [], {'attributes': ['string'], 'context': CTX})
                chave_field = next((k for k in rf if 'chave' in k.lower() or 'refnfe' in k.lower()
                                    or 'chnfe' in k.lower()), None)
                if chave_field:
                    o.execute_kw('account.move', 'write',
                                 [[mid], {refcampo: [(0, 0, {chave_field: rem_chave})]}],
                                 {'context': CTX})
                    print(f"  R3 refNFe gravado: {refcampo}.{chave_field} = {rem_chave}")
                else:
                    print(f"  R3 refNFe: campo de chave nao identificado no modelo {rel} (best-effort skip)")
            else:
                print(f"  R3 refNFe: campo/chave indisponivel (refcampo={refcampo}, chave={bool(rem_chave)}) — skip")
        except Exception as e:
            print(f"  R3 refNFe best-effort falhou (nao critico): {str(e)[:120]}")

        # snapshot draft (untax) + conta esperada das product lines
        mls = rr('account.move.line', [('move_id', '=', mid), ('display_type', '=', 'product')],
                 ['account_id', 'price_subtotal'])
        untax = round(sum(l['price_subtotal'] for l in mls), 2)
        contas = sorted({l['account_id'][1] for l in mls if l.get('account_id')})
        print(f"  NF-2 draft untax={untax} (alvo {ic_total}); contas product lines (pre-post): {contas}")
        print(f"\n  Proximo: --postar-nf2  (apos go).  Reverter: --reverter {mid}")
        print(SEP)
        return

    # ============================ POSTAR NF-2 (WRITE) ============================
    if '--postar-nf2' in args:
        # localizar a NF-2 montada (origin + journal j1084, draft)
        cand = rr('account.move', [('journal_id', '=', JOURNAL_ENTRI),
                                   ('invoice_origin', '=', ORIGIN), ('move_type', '=', 'in_invoice')],
                  ['id', 'state', 'amount_untaxed'])
        if not cand:
            print('  NF-2 montada nao encontrada (rode --montar-nf2). ABORT'); return
        nf2 = cand[0]; mid = nf2['id']
        if nf2['state'] == 'posted':
            print(f"  NF-2 {mid} JA posted");
        a0 = saldo(ACC['ATIVA'][0])
        print(f"  ATIVA 5101010001 antes = {a0}")
        if nf2['state'] != 'posted':
            o.execute_kw('account.move', 'action_post', [[mid]], {'context': CTX})
        m = rd('account.move', [mid], ['name', 'state', 'amount_total', 'amount_untaxed'])[0]
        print(f"  NF-2 {mid} POST: {m['name']} state={m['state']} untax={m['amount_untaxed']} total={m['amount_total']}")
        agg = move_lines(mid)
        print(f"  lancamento NF-2: {agg}")
        a1 = saldo(ACC['ATIVA'][0])
        print(f"  ATIVA depois = {a1}  (Δ = {round(a1 - a0, 2)})  [esperado -{ic_total} = baixa]")
        # identificar a conta-transito que SOBRA em D (alvo da revaloracao)
        transit_cod = ACC['TRANSIT'][1]
        sobra = [acc for acc, dc in agg.items() if dc[0] > 0 and '5101010001' not in acc]
        print(f"  conta(s) em D (alvo revaloracao, esperado {transit_cod}): {sobra}")
        print(f"\n  Proximo: --revalorar (apos go). Reverter: --reverter {mid}")
        print(SEP)
        return

    # ============================ REVALORAR PA (WRITE) ============================
    if '--revalorar' in args:
        comp = rd('res.company', [1], ['currency_id'], CTX_FB)[0]
        cur = comp['currency_id'][0]
        t0 = saldo(ACC['TRANSIT'][0], CTX_FB); pstd0, pq0 = pa_estado()
        print(f"  antes: PA std={pstd0} quant={pq0} TRANSIT(1150100011)={t0}")
        wid = o.execute_kw('stock.valuation.layer.revaluation', 'create',
                           [{'company_id': 1, 'currency_id': cur, 'product_id': PA,
                             'added_value': ic_total, 'account_id': ACC['TRANSIT'][0],
                             'account_journal_id': JOURNAL_REVAL,
                             'reason': 'Ic industrializacao retorno PILOTO 4870112'}],
                           {'context': CTX_FB})
        print(f"  wizard revaluation criado id={wid} (added_value=+{ic_total}, account_id=TRANSIT)")
        o.execute_kw('stock.valuation.layer.revaluation', 'action_validate_revaluation',
                     [[wid]], {'context': CTX_FB})
        t1 = saldo(ACC['TRANSIT'][0], CTX_FB); pstd1, pq1 = pa_estado()
        print(f"  depois: PA std={pstd1} quant={pq1} TRANSIT={t1} (Δ TRANSIT={round(t1 - t0, 2)})")
        svl = rr('stock.valuation.layer', [('product_id', '=', PA)],
                 ['id', 'value', 'description'], CTX_FB, limit=2, order='id desc')
        print(f"  SVLs recentes do PA: {svl}")
        print(f"\n  Proximo: --postar-nf1 (apos go).")
        print(SEP)
        return

    # ============================ POSTAR NF-1 (WRITE) ============================
    if '--postar-nf1' in args:
        st = rd('account.move', [NF1], ['state'])[0]['state']
        print(f"  NF-1 {NF1} state={st}")
        if st == 'posted':
            print('  JA posted');
        else:
            t0 = saldo(ACC['TRANSIT'][0])
            o.execute_kw('account.move', 'action_post', [[NF1]], {'context': CTX})
            t1 = saldo(ACC['TRANSIT'][0])
            print(f"  TRANSIT 1150100011: {t0} -> {t1} (Δ {round(t1-t0,2)}; cruza SVL picking C9)")
        m = rd('account.move', [NF1], ['name', 'state', 'amount_total', 'amount_untaxed'])[0]
        print(f"  NF-1 POST: {m['name']} state={m['state']} untax={m['amount_untaxed']} total={m['amount_total']}")
        print(f"  lancamento NF-1: {move_lines(NF1)}")
        print(f"\n  Proximo: --medir.")
        print(SEP)
        return

    # ============================ MEDIR gate (READ) ============================
    if '--medir' in args:
        print(SEP); print('S67 — GATE DE SUCESSO (medicao)'); print(SEP)
        std, q = pa_estado()
        print(f"  PA std_price={std} quant={q}  (alvo Ic+S ~305,46)")
        for k, (cid, cod) in ACC.items():
            print(f"  {k:8} {cod}: saldo = {saldo(cid)}")
        loc26489 = rr('stock.quant', [('location_id', '=', LOC_26489), ('product_id', '=', PA)],
                      ['quantity'], CTX_FB)
        loc30720 = rr('stock.quant', [('location_id', '=', LOC_30720), ('product_id', '=', PA)],
                      ['quantity'], CTX_FB)
        print(f"  quant PA em 26489={loc26489} (alvo 0) | 30720={loc30720} (alvo 0)")
        cand = rr('account.move', [('invoice_origin', '=', ORIGIN)],
                  ['id', 'name', 'state', 'journal_id', 'amount_total'])
        for c in cand:
            print(f"  move {c['id']} {c['name']} state={c['state']} journal={c['journal_id']} total={c['amount_total']}")
            print(f"    lancamento: {move_lines(c['id'])}")
        print(SEP)
        return

    # ============================ REVERTER (WRITE) ============================
    if '--reverter' in args:
        idx = args.index('--reverter')
        nf2_id = int(args[idx + 1]) if idx + 1 < len(args) and args[idx + 1].isdigit() else None
        comp = rd('res.company', [1], ['currency_id'], CTX_FB)[0]; cur = comp['currency_id'][0]
        # 1) revaloracao inversa: zerar o LIQUIDO das revaloracoes do piloto (idempotente).
        #    NOTA: o AVCO dilui sobre o pool (std nao reflete o ajuste), por isso medir
        #    pelo somatorio dos SVLs de revaloracao, nao pelo std_price.
        reval_svls = o.execute_kw('stock.valuation.layer', 'search_read',
                                  [[('product_id', '=', PA), ('description', 'like', 'PILOTO 4870112')]],
                                  {'fields': ['value'], 'context': CTX_FB})
        liq = round(sum(s['value'] for s in reval_svls), 2)
        if abs(liq) > 0.005:
            wid = o.execute_kw('stock.valuation.layer.revaluation', 'create',
                               [{'company_id': 1, 'currency_id': cur, 'product_id': PA,
                                 'added_value': -liq, 'account_id': ACC['TRANSIT'][0],
                                 'account_journal_id': JOURNAL_REVAL,
                                 'reason': 'REVERTE Ic PILOTO 4870112'}],
                               {'context': CTX_FB})
            o.execute_kw('stock.valuation.layer.revaluation', 'action_validate_revaluation',
                         [[wid]], {'context': CTX_FB})
            print(f"  revaloracao inversa aplicada (wizard {wid}, -{liq})")
        else:
            print(f"  revaloracao ja neutra (liquido={liq}) — skip inversa")
        # 2) NF-1 -> draft
        st1 = rd('account.move', [NF1], ['state'])[0]['state']
        if st1 == 'posted':
            o.execute_kw('account.move', 'button_draft', [[NF1]], {'context': CTX})
            print(f"  NF-1 {NF1} -> draft")
        # 3) NF-2 montada -> draft + unlink
        if not nf2_id:
            cand = rr('account.move', [('journal_id', '=', JOURNAL_ENTRI),
                                       ('invoice_origin', '=', ORIGIN)], ['id'])
            nf2_id = cand[0]['id'] if cand else None
        if nf2_id:
            st2 = rd('account.move', [nf2_id], ['state'])[0]['state']
            if st2 == 'posted':
                o.execute_kw('account.move', 'button_draft', [[nf2_id]], {'context': CTX})
            o.execute_kw('account.move', 'unlink', [[nf2_id]], {'context': CTX})
            print(f"  NF-2 {nf2_id} -> draft + unlink")
        std2, q2 = pa_estado()
        print(f"  PA restaurado: std={std2} quant={q2}")
        print(f"  ATIVA={saldo(ACC['ATIVA'][0])} TRANSIT={saldo(ACC['TRANSIT'][0])}")
        print(SEP)
        return


if __name__ == '__main__':
    main()
