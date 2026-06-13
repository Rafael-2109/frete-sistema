#!/usr/bin/env python3
"""S9 — GROUNDING do desenho E2E da emissao 2-NF (READ-only, sessao 9).

Responde as verificacoes do desenho ANTES do GATE 0 (p/ nao ser barrado depois):
  V2 — janela post->SEFAZ: campos de autorizacao na account.move + crons de
       transmissao + proporcao de VND j847 posted ja autorizadas (mede a corrida).
  V3 — valores da expansao: linhas 5902 da VND mista real (738097) vs custo atual
       dos produtos. Se price_unit ~= custo AVCO atual => a expansao valora por
       CUSTO, nao pela remessa => a NF-insumos precisa forcar price_unit = valores
       da remessa (invariante 5902 = 5901).
  V4 — precedente SEFAZ p/ NF simbolica: as SARET (total=0) tem chave/autorizacao?
  V5 — chave NFe disponivel pos-post (p/ referencia_ids/refNFe).

NAO escreve NADA. Salva /tmp/s9_grounding.txt.
"""
import sys
import io
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
CTX_LF = {'allowed_company_ids': [5], 'company_id': 5}
VND_MISTA_REF = 738097  # VND/2026/00359 (1x5124 + 9x5902) — ACHADOS §C sessao 7

_buf = io.StringIO()
def out(*a):
    s = ' '.join(str(x) for x in a); print(s); _buf.write(s + '\n')

def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"
    out(f"UID {o._uid}")

    def rr(model, domain, fields, ctx=None, **kw):
        kwargs = {'fields': fields, 'context': ctx or CTX}; kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)
    def cnt(model, domain):
        return o.execute_kw(model, 'search_count', [domain], {'context': CTX})
    def fg(model, *needles):
        f = o.execute_kw(model, 'fields_get', [], {'attributes': ['string', 'type'], 'context': CTX})
        return {k: v for k, v in f.items() if not needles or any(n in k.lower() for n in needles)}

    # ------------------------------------------------------------------
    out("\n" + "=" * 88)
    out("V2a) campos de NFe/SEFAZ/autorizacao em account.move (descoberta)")
    out("=" * 88)
    amf = fg('account.move', 'nfe', 'sefaz', 'protocolo', 'chave', 'autoriz', 'situacao', 'cstat', 'transmit')
    for k in sorted(amf):
        out(f"  {k:46} {amf[k]['type']:10} {amf[k]['string'][:40]}")

    # ------------------------------------------------------------------
    out("\n" + "=" * 88)
    out("V2b) crons ativos de faturamento/transmissao NFe (mede o automatismo)")
    out("=" * 88)
    crons = rr('ir.cron', ['|', '|', '|', ('name', 'ilike', 'fatura'), ('name', 'ilike', 'nfe'),
                           ('name', 'ilike', 'nf-e'), ('name', 'ilike', 'transmit')],
               ['id', 'name', 'active', 'interval_number', 'interval_type', 'nextcall'], limit=30)
    for c in crons:
        out(f"  cron{c['id']:5} active={c['active']} a cada {c['interval_number']} {c['interval_type']:8} | {c['name'][:60]}")

    # ------------------------------------------------------------------
    out("\n" + "=" * 88)
    out("V2c/V5) VND j847 posted 2026 — chave + situacao (proporcao autorizada; chave pos-post)")
    out("=" * 88)
    # campos candidatos lidos defensivamente (so os que existirem)
    cand = [f for f in ('l10n_br_chave_nf', 'l10n_br_situacao_nfe', 'l10n_br_protocolo_nfe',
                        'l10n_br_data_autorizacao', 'l10n_br_cstat_nfe', 'l10n_br_motivo_nfe') if f in amf]
    out(f"  campos lidos: {cand}")
    vnds = rr('account.move', [('journal_id', '=', 847), ('state', '=', 'posted'),
                               ('invoice_date', '>=', '2026-01-01')],
              ['id', 'name', 'invoice_date', 'create_date', 'amount_total'] + cand,
              limit=12, order='id desc')
    out(f"  ({cnt('account.move', [('journal_id', '=', 847), ('state', '=', 'posted'), ('invoice_date', '>=', '2026-01-01')])} VND posted 2026 no j847; mostrando 12)")
    for v in vnds:
        extra = ' '.join(f"{f.split('l10n_br_')[1]}={str(v.get(f))[:28]}" for f in cand)
        out(f"  {v['name']:18} dt={str(v.get('invoice_date'))[:10]} total={v['amount_total']:>10} {extra}")

    # ------------------------------------------------------------------
    out("\n" + "=" * 88)
    out("V3) VND mista 738097 — price_unit das 5902 vs custo atual (de onde vem o valor?)")
    out("=" * 88)
    nl = rr('account.move.line', [('move_id', '=', VND_MISTA_REF), ('display_type', '=', 'product')],
            ['product_id', 'quantity', 'price_unit', 'price_subtotal', 'l10n_br_cfop_codigo'], limit=50)
    pids = [ln['product_id'][0] for ln in nl if isinstance(ln.get('product_id'), list)]
    # custo no contexto LF (standard_price e company-dependent)
    prods = {p['id']: p for p in o.execute_kw('product.product', 'read', [pids],
             {'fields': ['default_code', 'standard_price'], 'context': CTX_LF})} if pids else {}
    out(f"  {'CFOP':5} {'produto':34} {'qty':>9} {'price_unit':>11} {'custo_LF':>10} {'pu~custo?':>9}")
    for ln in nl:
        pid = ln['product_id'][0] if isinstance(ln.get('product_id'), list) else None
        p = prods.get(pid, {})
        sp = p.get('standard_price')
        pu = ln.get('price_unit')
        aprox = '-'
        if sp not in (None, False) and pu not in (None, False):
            aprox = 'SIM' if abs(pu - sp) <= max(0.01, 0.02 * max(abs(sp), 0.01)) else 'NAO'
        out(f"  {str(ln.get('l10n_br_cfop_codigo')):5} [{p.get('default_code', '?')}] {m2o(ln.get('product_id'))[:28]:28} "
            f"{ln.get('quantity'):>9} {pu:>11} {sp if sp is not False else '-':>10} {aprox:>9}")

    # ------------------------------------------------------------------
    out("\n" + "=" * 88)
    out("V4) SARET (j1002, total=0) — foram a SEFAZ? (precedente NF simbolica autorizada)")
    out("=" * 88)
    sarets = rr('account.move', [('journal_id', '=', 1002), ('state', '=', 'posted')],
                ['id', 'name', 'invoice_date', 'amount_total'] + cand, limit=14, order='id desc')
    for s in sarets:
        extra = ' '.join(f"{f.split('l10n_br_')[1]}={str(s.get(f))[:28]}" for f in cand)
        out(f"  {s['name']:20} dt={str(s.get('invoice_date'))[:10]} total={s['amount_total']:>8} {extra}")

    out("\n[FIM s9_grounding_desenho — READ-only]")
    with open('/tmp/s9_grounding.txt', 'w') as f:
        f.write(_buf.getvalue())
    out(">>> salvo em /tmp/s9_grounding.txt")


if __name__ == '__main__':
    main()
