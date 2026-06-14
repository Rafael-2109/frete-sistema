#!/usr/bin/env python3
"""S44 — READ-only: desenhar a automacao dos 2 gatilhos (Task #6).
  G1 (validacao do picking servico -> cria NF-2)  |  G2 (transmite NF-1 -> transmite NF-2)

Investiga:
  1. COMO o picking validado vira fatura: pt66 (invoice_move_type / tipo_pedido / auto-invoice)
     + o robo/cron 1512 (domain: quais pickings ele fatura?) -> onde "pendurar" o G1.
  2. DISCRIMINADOR do regime FB<->LF terceiros: partner + operacao(header) das NFs de retorno
     REAIS (709632/708286) vs o nosso piloto (789484); src do picking; universo do j847 por
     partner (FB=1 e' bom discriminador? quantas VND j847 sao p/ FB vs outros clientes?).
  3. METODO de transmissao (G2): campos/acao de gerar NFe + como detectar cstat=100.

READ-ONLY.
"""
import sys
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
PT66, J847 = 66, 847
NFS_REAIS = [709632, 708286]
NF_PILOTO = 789484


def m2o(v):
    return f"{v[0]}|{str(v[1])[:30]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)
    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    # ---- 1. mecanismo de faturamento ----
    print("=" * 94)
    print("### 1. COMO o picking validado vira fatura (onde pendurar o G1)")
    ptf = o.execute_kw('stock.picking.type', 'fields_get', [], {'attributes': ['string'], 'context': CTX})
    want = [f for f in ['invoice_move_type', 'l10n_br_tipo_pedido', 'l10n_br_gera_financeiro',
                        'create_invoice', 'auto_invoice', 'l10n_br_fatura_automatica'] if f in ptf]
    pt = rd('stock.picking.type', [PT66], ['name'] + want)[0]
    print(f"   pt66 {pt['name']}: " + " | ".join(f"{f}={pt.get(f)}" for f in want))
    # robos/SA que faturam (1512 + outros): buscar server actions com create_invoice/onshipping
    print("   server actions de faturamento (code com 'create_invoice'/'onshipping'/'liberado'):")
    sas = rr('ir.actions.server', [('state', '=', 'code')], ['id', 'name'], limit=400)
    hits = []
    for s in sas:
        if s['id'] in (1512,) or any(k in (s['name'] or '').lower() for k in ['fatur', 'robo', 'invoice', 'nfe', 'nf-e']):
            hits.append(s)
    for s in hits[:12]:
        print(f"      SA {s['id']}: {s['name'][:60]}")
    # crons que rodam essas SAs
    crons = rr('ir.cron', [('active', 'in', [True, False])], ['id', 'name', 'active', 'interval_number', 'interval_type'], limit=60)
    fat_crons = [c for c in crons if any(k in (c['name'] or '').lower() for k in ['fatur', 'robo', 'nfe', 'invoice', 'nf-e', 'transmit'])]
    print(f"   crons de faturamento/transmissao: {[(c['id'], c['name'][:34], c['active']) for c in fat_crons][:8]}")

    # ---- 2. discriminador ----
    print("\n" + "=" * 94)
    print("### 2. DISCRIMINADOR do regime (partner + operacao + src)")
    for nf in NFS_REAIS + [NF_PILOTO]:
        h = rd('account.move', [nf], ['name', 'partner_id', 'l10n_br_operacao_id', 'l10n_br_tipo_pedido', 'journal_id'])
        if not h:
            continue
        h = h[0]
        pk = rr('stock.picking', ['|', ('invoice_id', '=', nf), ('invoice_ids', 'in', [nf])],
                ['location_id'], limit=1)
        src = m2o(pk[0]['location_id']) if pk else '?'
        tag = 'PILOTO' if nf == NF_PILOTO else 'REAL'
        print(f"   [{tag}] NF {nf} {h['name']}: partner={m2o(h.get('partner_id'))} "
              f"op_header={m2o(h.get('l10n_br_operacao_id'))} src_picking={src}")
    # universo j847 por partner
    print(f"\n   universo j847 (VND servico industrializacao) por partner — FB=1 e' discriminador?")
    vnds = rr('account.move', [('journal_id', '=', J847), ('move_type', '=', 'out_invoice')],
              ['partner_id'], limit=200, order='id desc')
    parts = Counter(m2o(v.get('partner_id')) for v in vnds)
    print(f"      top partners (de {len(vnds)} VND recentes): {dict(parts.most_common(6))}")

    # ---- 3. metodo de transmissao (G2) ----
    print("\n" + "=" * 94)
    print("### 3. METODO de transmissao (G2: transmite NF-1 -> transmite NF-2)")
    mf = o.execute_kw('account.move', 'fields_get', [], {'attributes': ['string'], 'context': CTX})
    tx = sorted([f for f in mf if any(k in f.lower() for k in ['gerar_nfe', 'transmit', 'enviar_nfe', 'show_nfe', 'cstat'])])
    print(f"   campos transmissao: {tx}")
    print("   (transmissao = metodo que chama SEFAZ; G2 = detectar NF-1 cstat=100 -> chamar o mesmo na NF-2)")


if __name__ == '__main__':
    main()
