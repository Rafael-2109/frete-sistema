#!/usr/bin/env python3
"""S39 — PRE-FLIGHT de TRANSMISSAO SEFAZ (READ-only) das 2 NFs do piloto (789484 servico,
789485 insumos). Transmitir e' IRREVERSIVEL — este script CERTIFICA o que e' preciso ANTES:

  1. ESTADO das 2 NFs (draft? precisa action_post antes de transmitir) + estrutura/vNF.
  2. AMBIENTE SEFAZ (tpAmb: PRODUCAO=1 vs HOMOLOGACAO=2) — define se a NFe e' fiscal REAL.
  3. CADASTRO FISCAL dos produtos (PA + 16 insumos): NCM presente? origem? barcode==default_code
     (gotcha G035 -> SEFAZ Schema 225 reject)?
  4. METODO de transmissao (campos/acoes l10n_br: gerar_nfe / show_nfe_btn / status).
  5. SEQUENCIA proposta (saga SOT 6.1): postar NF-1 -> transmitir NF-1 -> obter chave ->
     cross-refNFe na NF-2 -> postar NF-2 -> transmitir NF-2.

READ-ONLY. NAO posta, NAO transmite.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF1, NF2 = 789484, 789485
LF_COMPANY = 5
REMESSA = 735679


def m2o(v):
    return f"{v[0]}|{str(v[1])[:26]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    fg = o.execute_kw('account.move', 'fields_get', [], {'attributes': ['string', 'type'], 'context': CTX})

    # ---- 1. estado das 2 NFs ----
    print("=" * 92)
    print("### 1. ESTADO das 2 NFs (precisa action_post antes de transmitir)")
    sefaz_cols = [c for c in ['l10n_br_chave_nf', 'l10n_br_cstat_nf', 'l10n_br_situacao_nf',
                              'l10n_br_total_nfe', 'l10n_br_numero_nf', 'l10n_br_serie_nf'] if c in fg]
    for label, nf in [('NF-1 servico', NF1), ('NF-2 insumos', NF2)]:
        h = rr('account.move', [('id', '=', nf)], ['name', 'state', 'amount_total'] + sefaz_cols)
        if not h:
            print(f"   {label} {nf}: INEXISTENTE"); continue
        h = h[0]
        print(f"   {label} {nf}: name={h.get('name')} state={h['state']} amount_total={h.get('amount_total')} "
              f"vNF={h.get('l10n_br_total_nfe')} chave={h.get('l10n_br_chave_nf') or '-'} "
              f"cstat={h.get('l10n_br_cstat_nf') or '-'} num={h.get('l10n_br_numero_nf') or '-'}")

    # ---- 2. ambiente SEFAZ ----
    print("\n" + "=" * 92)
    print("### 2. AMBIENTE SEFAZ (tpAmb) — PRODUCAO(1) vs HOMOLOGACAO(2)")
    cfg = o.execute_kw('res.company', 'fields_get', [], {'attributes': ['string', 'type'], 'context': CTX})
    amb_f = sorted([f for f in cfg if any(k in f.lower() for k in ['tpamb', 'ambiente', 'tipo_amb', 'sefaz'])])
    comp = rr('res.company', [('id', '=', LF_COMPANY)], ['name'] + amb_f) if amb_f else []
    if comp:
        print(f"   company LF: {comp[0].get('name')}")
        for f in amb_f:
            v = comp[0].get(f)
            if v not in (False, None, ''):
                print(f"      {f} = {v}")
    else:
        print("   (sem campo de ambiente na company — checar config CIEL IT)")

    # ---- 3. cadastro fiscal dos produtos ----
    print("\n" + "=" * 92)
    print("### 3. CADASTRO FISCAL dos produtos (PA + 16 insumos das NFs)")
    pids = set()
    for nf in [NF1, NF2]:
        for l in rr('account.move.line', [('move_id', '=', nf), ('display_type', '=', 'product')], ['product_id']):
            if l.get('product_id'):
                pids.add(l['product_id'][0])
    pfg = o.execute_kw('product.product', 'fields_get', [], {'attributes': ['type'], 'context': CTX})
    pcols = [c for c in ['default_code', 'name', 'barcode', 'l10n_br_ncm_id', 'ncm_id',
                         'l10n_br_source', 'l10n_br_fiscal_type', 'weight'] if c in pfg]
    prods = rr('product.product', [('id', 'in', list(pids))], pcols)
    sem_ncm, barcode_eq_code, sem_barcode = [], [], []
    ncm_field = 'l10n_br_ncm_id' if 'l10n_br_ncm_id' in pfg else ('ncm_id' if 'ncm_id' in pfg else None)
    for p in prods:
        ncm = p.get(ncm_field) if ncm_field else None
        if not ncm:
            sem_ncm.append(p.get('default_code'))
        bc = p.get('barcode')
        if bc and bc == p.get('default_code'):
            barcode_eq_code.append(p.get('default_code'))
        if not bc:
            sem_barcode.append(p.get('default_code'))
    print(f"   {len(prods)} produtos | campo NCM = {ncm_field}")
    print(f"   sem NCM: {sem_ncm or '✅ todos com NCM'}")
    print(f"   barcode == default_code (gotcha G035 -> reject): {barcode_eq_code or '✅ nenhum'}")
    print(f"   sem barcode: {sem_barcode or 'nenhum'} (info)")

    # ---- 4. metodo de transmissao ----
    print("\n" + "=" * 92)
    print("### 4. METODO de transmissao (campos/acoes l10n_br)")
    btn_f = sorted([f for f in fg if any(k in f.lower() for k in ['show_nfe', 'gerar_nfe', 'transmit', 'enviar_nfe'])])
    h1 = rr('account.move', [('id', '=', NF1)], btn_f) if btn_f else []
    for f in btn_f:
        if h1 and h1[0].get(f) not in (False, None, ''):
            print(f"   NF-1 {f} = {h1[0].get(f)}")
    # acoes server/buttons disponiveis no account.move
    print("   (transmissao tipica CIEL IT: action_post -> botao/metodo 'Gerar NF-e' que chama SEFAZ)")

    # ---- 5. sequencia ----
    print("\n" + "=" * 92)
    print("### 5. SEQUENCIA proposta (IRREVERSIVEL a partir da transmissao)")
    print("   a) action_post NF-1 (servico) -> lanca receita + PIS/COFINS")
    print("   b) transmitir NF-1 -> SEFAZ -> obtem chave/numero")
    print("   c) [R3 saga] adicionar refNFe da NF-1 na NF-2 (cross-vinculo) — opcional/decidir")
    print("   d) action_post NF-2 (insumos) -> baixa PASSIVA 5101020001")
    print("   e) transmitir NF-2 -> SEFAZ")
    print("   >>> cada transmissao e' IRREVERSIVEL (so cancelamento c/ janela / CC-e)")


if __name__ == '__main__':
    main()
