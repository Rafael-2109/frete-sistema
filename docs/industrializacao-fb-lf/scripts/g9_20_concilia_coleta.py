#!/usr/bin/env python3
"""G9 COLETA+VALIDA (READ-ONLY) — batimento NF-a-NF FB<->LF pela chave de acesso.

Antes de gerar Excel: prova que o detalhe (NF a NF + pagamentos + ajustes) FECHA com
os saldos reais das contas 26085 (LF a-receber) e 11038 (FB a-pagar). Imprime a
decomposicao do gap em causa-geracao e causa-pagamento. NAO escreve nada no Odoo.
"""
import sys
from collections import defaultdict
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
ACC_LF, P_FB = 26085, 1    # CLIENTES LF (a receber da FB)
ACC_FB, P_LF = 11038, 35   # FORNECEDORES FB (a pagar a LF)
J_ENTSI = 1001             # ENTRADA SERVICO INDUSTRIALIZACAO (FB)
J_DIV_LF = 894             # ajuste G9 lado LF


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}\n")

    def sr(m, d, f, **k):
        kw = {'fields': f, 'context': CTX}; kw.update(k)
        return o.execute_kw(m, 'search_read', [d], kw)

    def rg(m, d, f, g=[]):
        return o.execute_kw(m, 'read_group', [d, f, g], {'context': CTX, 'lazy': False})

    def minfo(ids):
        out = {}
        for i in range(0, len(ids), 300):
            for m in o.execute_kw('account.move', 'read', [ids[i:i + 300]],
                                  {'fields': ['name', 'ref', 'l10n_br_chave_nf', 'l10n_br_numero_nf'], 'context': CTX}):
                out[m['id']] = m
        return out

    # ===== LADO LF: TODOS os debitos (a-receber gerado) na conta CLIENTES =====
    lf_l = sr('account.move.line', [('account_id', '=', ACC_LF), ('partner_id', '=', P_FB),
              ('parent_state', '=', 'posted'), ('debit', '>', 0)],
              ['move_id', 'debit', 'amount_residual', 'date'], limit=50000)
    lf_mv = defaultdict(lambda: {'debit': 0.0, 'resid': 0.0, 'date': None})
    for l in lf_l:
        m = l['move_id'][0]
        lf_mv[m]['debit'] += l['debit'] or 0
        lf_mv[m]['resid'] += l['amount_residual'] or 0
        lf_mv[m]['date'] = l['date']
    lf_info = minfo(list(lf_mv.keys()))

    def chave_of(info):
        return info.get('l10n_br_chave_nf') or (f"NUM:{info['l10n_br_numero_nf']}" if info.get('l10n_br_numero_nf') else f"MOVE:{info['name']}")

    lf_by_ch = {}
    for mid, agg in lf_mv.items():
        info = lf_info[mid]
        ch = chave_of(info)
        is_ind = bool(info.get('ref') and '/IND/' in info['ref'])
        lf_by_ch[ch] = {'name': info['name'], 'num': info.get('l10n_br_numero_nf'), 'date': agg['date'],
                        'areceber': agg['debit'], 'aberto': agg['resid'], 'ind': is_ind}

    # ===== LADO FB: ENTSI (a-pagar gerado) =====
    fb_l = sr('account.move.line', [('account_id', '=', ACC_FB), ('partner_id', '=', P_LF),
              ('parent_state', '=', 'posted'), ('journal_id', '=', J_ENTSI)],
              ['move_id', 'credit', 'amount_residual', 'date'], limit=50000)
    fb_mv = defaultdict(lambda: {'credit': 0.0, 'resid': 0.0, 'date': None})
    for l in fb_l:
        m = l['move_id'][0]
        fb_mv[m]['credit'] += l['credit'] or 0
        fb_mv[m]['resid'] += l['amount_residual'] or 0
        fb_mv[m]['date'] = l['date']
    fb_info = minfo(list(fb_mv.keys()))
    fb_by_ch = {}
    for mid, agg in fb_mv.items():
        info = fb_info[mid]
        ch = chave_of(info)
        fb_by_ch[ch] = {'name': info['name'], 'num': info.get('l10n_br_numero_nf'), 'date': agg['date'],
                        'apagar': agg['credit'], 'aberto': -agg['resid']}

    # ===== CRUZAMENTO por chave =====
    all_ch = set(lf_by_ch) | set(fb_by_ch)
    both = ok = divv = 0
    so_lf_ind = so_lf_naoind = so_fb = 0
    v_both_lf = v_both_fb = v_solf_ind = v_solf_naoind = v_sofb = 0.0
    delta_match = 0.0
    for ch in all_ch:
        L, F = lf_by_ch.get(ch), fb_by_ch.get(ch)
        if L and F:
            both += 1
            v_both_lf += L['areceber']; v_both_fb += F['apagar']
            d = L['areceber'] - F['apagar']; delta_match += d
            if abs(d) < 0.01:
                ok += 1
            else:
                divv += 1
        elif L:
            if L['ind']:
                so_lf_ind += 1; v_solf_ind += L['areceber']
            else:
                so_lf_naoind += 1; v_solf_naoind += L['areceber']
        else:
            so_fb += 1; v_sofb += F['apagar']

    # ===== AGREGADOS de controle (saldos reais) =====
    def saldo(acc, partner, sign_field):
        g = rg('account.move.line', [('account_id', '=', acc), ('partner_id', '=', partner), ('parent_state', '=', 'posted')], ['debit:sum', 'credit:sum'])
        return (g[0]['debit'] or 0) - (g[0]['credit'] or 0)

    saldo_lf = saldo(ACC_LF, P_FB, None)   # +a receber
    saldo_fb = saldo(ACC_FB, P_LF, None)   # -a pagar

    # baixas LF: creditos por origem (G9 DIV vs pagamento banco)
    g_div_lf = rg('account.move.line', [('account_id', '=', ACC_LF), ('partner_id', '=', P_FB), ('journal_id', '=', J_DIV_LF), ('parent_state', '=', 'posted')], ['credit:sum'])
    cred_g9 = g_div_lf[0]['credit'] or 0
    g_cred_lf = rg('account.move.line', [('account_id', '=', ACC_LF), ('partner_id', '=', P_FB), ('parent_state', '=', 'posted'), ('credit', '>', 0)], ['credit:sum'])
    cred_lf_tot = g_cred_lf[0]['credit'] or 0
    pag_recebido_lf = cred_lf_tot - cred_g9
    g_deb_lf = rg('account.move.line', [('account_id', '=', ACC_LF), ('partner_id', '=', P_FB), ('parent_state', '=', 'posted'), ('debit', '>', 0)], ['debit:sum'])
    areceber_ger_lf = g_deb_lf[0]['debit'] or 0

    # FB: a-pagar gerado (creditos) e pago (debitos)
    g_cred_fb = rg('account.move.line', [('account_id', '=', ACC_FB), ('partner_id', '=', P_LF), ('parent_state', '=', 'posted'), ('credit', '>', 0)], ['credit:sum'])
    apagar_ger_fb = g_cred_fb[0]['credit'] or 0
    g_deb_fb = rg('account.move.line', [('account_id', '=', ACC_FB), ('partner_id', '=', P_LF), ('parent_state', '=', 'posted'), ('debit', '>', 0)], ['debit:sum'])
    pago_fb = g_deb_fb[0]['debit'] or 0

    P = lambda x: f"{x:>16,.2f}"
    print("=" * 80)
    print("CRUZAMENTO NF-a-NF (chave de acesso)")
    print(f"  NFs em AMBOS os lados   : {both:5d}  | a-receber LF {P(v_both_lf)} | a-pagar FB {P(v_both_fb)} | Δ {P(v_both_lf - v_both_fb)}")
    print(f"     destes, batem (Δ~0)  : {ok:5d}")
    print(f"     destes, divergem     : {divv:5d}")
    print(f"  So LF c/ ref IND        : {so_lf_ind:5d}  | a-receber {P(v_solf_ind)}   (industrializacao SEM entrada FB)")
    print(f"  So LF SEM ref IND       : {so_lf_naoind:5d}  | a-receber {P(v_solf_naoind)}   (venda normal LF->FB, fora do escopo)")
    print(f"  So FB (ENTSI)           : {so_fb:5d}  | a-pagar   {P(v_sofb)}   (entrada FB sem a-receber LF)")
    print()
    print("=" * 80)
    print("FECHAMENTO vs saldos reais das contas")
    print(f"  [LF] a-receber gerado (Σdeb)      {P(areceber_ger_lf)}")
    print(f"  [LF] (-) ajuste G9 insumos (DIV)  {P(-cred_g9)}")
    print(f"  [LF] (-) pagamentos recebidos     {P(-pag_recebido_lf)}")
    print(f"  [LF] = SALDO A RECEBER            {P(areceber_ger_lf - cred_g9 - pag_recebido_lf)}  | conta real {P(saldo_lf)}")
    print(f"  [FB] a-pagar gerado (Σcred)       {P(apagar_ger_fb)}")
    print(f"  [FB] (-) pagamentos feitos        {P(-pago_fb)}")
    print(f"  [FB] = SALDO A PAGAR              {P(apagar_ger_fb - pago_fb)}  | conta real {P(saldo_fb)}")
    print()
    print("=" * 80)
    print("DECOMPOSICAO DO GAP (a-receber LF − a-pagar FB)")
    gap = saldo_lf - (-saldo_fb)  # saldo_fb e negativo (a pagar)
    print(f"  GAP total = {P(saldo_lf)} − {P(-saldo_fb)} = {P(gap)}")
    causa_ger = (areceber_ger_lf - cred_g9) - apagar_ger_fb   # serviço LF (já s/ insumos) − a-pagar FB
    causa_pag = pago_fb - pag_recebido_lf                      # FB pagou a mais que LF recebeu
    print(f"  (B) divergencia de GERACAO de serviço : LF {P(areceber_ger_lf - cred_g9)} − FB {P(apagar_ger_fb)} = {P(causa_ger)}")
    print(f"  (A) divergencia de PAGAMENTO          : FB pagou {P(pago_fb)} − LF recebeu {P(pag_recebido_lf)} = {P(causa_pag)}")
    print(f"  soma (B)+(A) = {P(causa_ger + causa_pag)}   (deve ≈ GAP {P(gap)})")


if __name__ == '__main__':
    main()
