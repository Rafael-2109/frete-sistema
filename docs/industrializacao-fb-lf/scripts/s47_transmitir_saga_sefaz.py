#!/usr/bin/env python3
"""S47 — FASE B (IRREVERSIVEL, SEFAZ PRODUCAO tpAmb=1): saga de transmissao das 2 NFs do
piloto LF->FB. Espelha o trilho de recebimento_lf_odoo_service._step_23 (post via XML-RPC =
Fase A/s40; transmissao via Playwright UI — OBRIGATORIO porque XML-RPC deixa nfe_infnfe_*
stale -> SEFAZ 225 Schema).

PRE-CONDICAO: as 2 NFs ja POSTED (Fase A: s40 --executar) e NAO transmitidas (cstat vazio).

SAGA (cada transmissao = 1 escrita IRREVERSIVEL, go FRESCO proprio):
  1. transmitir NF-1 (servico 5124) via Playwright -> autorizado + chave (44 dig)
  2. cross-refNFe: grava a chave da NF-1 na NF-2.referencia_ids (completa o R3) ANTES de
     transmitir (senao o refNFe nao entra no XML da NF-2)
  3. transmitir NF-2 (insumos 5902) via Playwright -> autorizado + chave
  4. validar: cstat=100 nas 2 + chaves + baixa PASSIVA 5101020001 + refNFe

MODOS:
  (sem flag) NF1 NF2     dry-run READ: estado das 2 + tpAmb + pre-condicao + plano (NAO transmite)
  --transmitir-nf1 NF1   [ESCRITA SEFAZ IRREVERSIVEL] transmite SO a NF-1 -> obtem chave
  --transmitir-nf2 NF1 NF2  [ESCRITA SEFAZ IRREVERSIVEL] cross-refNFe (chave NF-1 -> NF-2) + transmite NF-2
  --validar NF1 NF2      READ: cstat/chave das 2 + baixa PASSIVA + refNFe -> FIRMAR LF

Opcoes: --max-tentativas N (default 10) --intervalo SEG (default 90)
"""
import sys
import argparse
import logging
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
# load_dotenv ANTES de qualquer import que leia os.environ em module-level
# (playwright_nfe_transmissao le ODOO_USERNAME/ODOO_PASSWORD no import do modulo).
from dotenv import load_dotenv
load_dotenv()
from app.odoo.utils.connection import get_odoo_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('s47')

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
LF = 5
ACC_PASSIVA = 26667          # 5101020001 PASSIVA LF
REF_MODEL = 'l10n_br_ciel_it_account.account.move.referencia'


def chave_ok(c):
    return bool(c) and len(str(c)) == 44


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('nfs', nargs='*', type=int, help='NF1 NF2 (para dry-run)')
    ap.add_argument('--transmitir-nf1', type=int, metavar='NF1_ID')
    ap.add_argument('--transmitir-nf2', nargs=2, type=int, metavar=('NF1_ID', 'NF2_ID'))
    ap.add_argument('--validar', nargs=2, type=int, metavar=('NF1_ID', 'NF2_ID'))
    ap.add_argument('--max-tentativas', type=int, default=10)
    ap.add_argument('--intervalo', type=int, default=90)
    args = ap.parse_args()

    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    SEFAZ = ['name', 'state', 'l10n_br_situacao_nf', 'l10n_br_chave_nf', 'l10n_br_cstat_nf',
             'l10n_br_xmotivo_nf', 'amount_total', 'l10n_br_total_nfe']

    def estado(nf):
        h = rd('account.move', [nf], SEFAZ)
        return h[0] if h else None

    def saldo_passiva():
        lns = rr('account.move.line', [('account_id', '=', ACC_PASSIVA),
                                       ('parent_state', '=', 'posted'), ('company_id', '=', LF)], ['balance'])
        return round(sum(l.get('balance') or 0 for l in lns), 2)

    def linha_estado(label, nf):
        h = estado(nf)
        if not h:
            print(f"  {label} {nf}: INEXISTENTE ❌"); return None
        print(f"  {label} {nf}: {h.get('name')} state={h['state']} "
              f"situacao={h.get('l10n_br_situacao_nf') or '-'} cstat={h.get('l10n_br_cstat_nf') or '-'} "
              f"chave={(h.get('l10n_br_chave_nf') or '-')} total={h.get('amount_total')} vNF={h.get('l10n_br_total_nfe')}")
        return h

    def tpamb():
        cfg = o.execute_kw('res.company', 'fields_get', [], {'attributes': ['type'], 'context': CTX})
        amb_f = [f for f in cfg if any(k in f.lower() for k in ['tpamb', 'ambiente', 'tipo_amb'])]
        if not amb_f:
            return None, []
        comp = rd('res.company', [LF], amb_f)
        vals = {f: comp[0].get(f) for f in amb_f if comp and comp[0].get(f) not in (False, None, '')}
        return vals, amb_f

    # ================= TRANSMITIR NF-1 =================
    if args.transmitir_nf1:
        nf1 = args.transmitir_nf1
        h = estado(nf1)
        assert h, f"NF-1 {nf1} inexistente"
        if h['state'] != 'posted':
            print(f"  ❌ ABORTADO: NF-1 {nf1} state={h['state']} (precisa posted — rode a Fase A primeiro)"); return
        if h.get('l10n_br_situacao_nf') == 'autorizado' and chave_ok(h.get('l10n_br_chave_nf')):
            print(f"  ✅ NF-1 {nf1} JA autorizada (idempotente): chave={h['l10n_br_chave_nf']}"); return
        print("=" * 92)
        print(f"### TRANSMITINDO NF-1 (servico) {nf1} {h.get('name')} — SEFAZ PRODUCAO, IRREVERSIVEL")
        print("=" * 92)
        from app.recebimento.services.playwright_nfe_transmissao import transmitir_nfe_via_playwright
        res = transmitir_nfe_via_playwright(invoice_id=nf1, odoo=o, logger=logger,
                                            max_tentativas=args.max_tentativas, intervalo_retry=args.intervalo)
        print(f"\n  RESULTADO NF-1: {res}")
        if res.get('sucesso'):
            print(f"  ✅ NF-1 AUTORIZADA — chave={res.get('chave_nf')} (tentativa {res.get('tentativa')})")
            print(f"  >>> proximo: --transmitir-nf2 {nf1} <NF2_ID>")
        else:
            print(f"  ❌ NF-1 NAO autorizada: {res.get('erro')} | ultimo_estado={res.get('ultimo_estado')}")
        return

    # ================= CROSS-REF + TRANSMITIR NF-2 =================
    if args.transmitir_nf2:
        nf1, nf2 = args.transmitir_nf2
        h1 = estado(nf1); h2 = estado(nf2)
        assert h1 and h2, "NF-1 ou NF-2 inexistente"
        chave1 = h1.get('l10n_br_chave_nf')
        if not (h1.get('l10n_br_situacao_nf') == 'autorizado' and chave_ok(chave1)):
            print(f"  ❌ ABORTADO: NF-1 {nf1} ainda nao autorizada (situacao={h1.get('l10n_br_situacao_nf')}, "
                  f"chave={chave1}). Transmita a NF-1 primeiro (--transmitir-nf1)."); return
        if h2['state'] != 'posted':
            print(f"  ❌ ABORTADO: NF-2 {nf2} state={h2['state']} (precisa posted)"); return
        if h2.get('l10n_br_situacao_nf') == 'autorizado' and chave_ok(h2.get('l10n_br_chave_nf')):
            print(f"  ✅ NF-2 {nf2} JA autorizada (idempotente): chave={h2['l10n_br_chave_nf']}"); return

        # 1) cross-refNFe: chave NF-1 -> NF-2.referencia_ids (idempotente) ANTES de transmitir
        refs = rr(REF_MODEL, [('move_id', '=', nf2)], ['l10n_br_chave_nf'])
        chaves_ja = {r.get('l10n_br_chave_nf') for r in refs}
        if chave1 in chaves_ja:
            print(f"  [cross-ref] chave da NF-1 JA presente na NF-2 ({len(refs)} refNFe) — ok")
        else:
            o.execute_kw('account.move', 'write', [[nf2], {
                'referencia_ids': [(0, 0, {'l10n_br_chave_nf': chave1, 'company_id': LF})]}],
                {'context': dict(CTX, check_move_validity=False)})
            refs2 = rr(REF_MODEL, [('move_id', '=', nf2)], ['l10n_br_chave_nf'])
            print(f"  [cross-ref] chave NF-1 gravada na NF-2 ✅ (agora {len(refs2)} refNFe: "
                  f"{[r['l10n_br_chave_nf'][-12:] for r in refs2]})")

        # 2) transmitir NF-2
        print("=" * 92)
        print(f"### TRANSMITINDO NF-2 (insumos) {nf2} {h2.get('name')} — SEFAZ PRODUCAO, IRREVERSIVEL")
        print("=" * 92)
        from app.recebimento.services.playwright_nfe_transmissao import transmitir_nfe_via_playwright
        res = transmitir_nfe_via_playwright(invoice_id=nf2, odoo=o, logger=logger,
                                            max_tentativas=args.max_tentativas, intervalo_retry=args.intervalo)
        print(f"\n  RESULTADO NF-2: {res}")
        if res.get('sucesso'):
            print(f"  ✅ NF-2 AUTORIZADA — chave={res.get('chave_nf')} (tentativa {res.get('tentativa')})")
            print(f"  >>> proximo: --validar {nf1} {nf2}")
        else:
            print(f"  ❌ NF-2 NAO autorizada: {res.get('erro')} | ultimo_estado={res.get('ultimo_estado')}")
        return

    # ================= VALIDAR (FIRMAR LF) =================
    if args.validar:
        nf1, nf2 = args.validar
        print("=" * 92)
        print("### VALIDACAO FINAL — FIRMAR a LF concluida")
        print("=" * 92)
        h1 = linha_estado('NF-1 servico', nf1)
        h2 = linha_estado('NF-2 insumos', nf2)
        if not (h1 and h2):
            return
        # baixa PASSIVA: debito da NF-2 na conta 26667
        nfl = rr('account.move.line', [('move_id', '=', nf2), ('account_id', '=', ACC_PASSIVA)], ['debit', 'credit'])
        debito = round(sum(l.get('debit') or 0 for l in nfl), 2)
        refs2 = rr(REF_MODEL, [('move_id', '=', nf2)], ['l10n_br_chave_nf'])
        ok1 = h1.get('l10n_br_cstat_nf') in (100, '100') and chave_ok(h1.get('l10n_br_chave_nf'))
        ok2 = h2.get('l10n_br_cstat_nf') in (100, '100') and chave_ok(h2.get('l10n_br_chave_nf'))
        chave1 = h1.get('l10n_br_chave_nf')
        cross_ok = any(r.get('l10n_br_chave_nf') == chave1 for r in refs2)
        print(f"\n  [A] NF-1 cstat=100 + chave 44d: {'✅' if ok1 else '❌'}")
        print(f"  [B] NF-2 cstat=100 + chave 44d: {'✅' if ok2 else '❌'}")
        print(f"  [C] baixa PASSIVA 5101020001 (D conta 26667 na NF-2) = {debito} {'✅' if debito > 0 else '❌'}")
        print(f"      saldo PASSIVA atual = {saldo_passiva()}")
        print(f"  [D] R3 refNFe da NF-2 ({len(refs2)}): {[r['l10n_br_chave_nf'][-12:] for r in refs2]} "
              f"| cross-ref NF-1 presente: {'✅' if cross_ok else '❌'}")
        firme = ok1 and ok2 and debito > 0 and cross_ok
        print(f"\n  >>> {'✅✅✅ LF CONCLUIDA (as 2 NFs autorizadas na SEFAZ + baixa + R3)' if firme else '⚠️ AINDA NAO firme — revisar itens acima'}")
        return

    # ================= DRY-RUN (default) =================
    if len(args.nfs) < 2:
        print("uso (dry-run): python s47_transmitir_saga_sefaz.py NF1_ID NF2_ID"); return
    nf1, nf2 = args.nfs[0], args.nfs[1]
    print("=" * 92)
    print("S47 — DRY-RUN: saga de transmissao SEFAZ das 2 NFs (NADA transmitido aqui)")
    print("=" * 92)
    h1 = linha_estado('NF-1 servico', nf1)
    h2 = linha_estado('NF-2 insumos', nf2)
    print()
    amb, amb_f = tpamb()
    if amb:
        print(f"  🔴 AMBIENTE SEFAZ (company LF): {amb}  — tpAmb=1=PRODUCAO => NFe FISCAL REAL, IRREVERSIVEL")
    else:
        print(f"  ⚠️ campo de ambiente nao encontrado em res.company (campos: {amb_f}); "
              f"FASE A ja confirmou tpAmb=1=PRODUCAO (s39)")
    print(f"\n  PRE-CONDICAO (Fase A): ambas posted + cstat vazio:")
    pc1 = h1 and h1['state'] == 'posted' and not h1.get('l10n_br_cstat_nf')
    pc2 = h2 and h2['state'] == 'posted' and not h2.get('l10n_br_cstat_nf')
    print(f"    NF-1 posted & nao-transmitida: {'✅' if pc1 else '❌ (' + (h1['state'] if h1 else '?') + ')'}")
    print(f"    NF-2 posted & nao-transmitida: {'✅' if pc2 else '❌ (' + (h2['state'] if h2 else '?') + ')'}")
    print(f"\n  PLANO (1 go FRESCO por transmissao):")
    print(f"    1) --transmitir-nf1 {nf1}        (SEFAZ, irreversivel) -> chave NF-1")
    print(f"    2) --transmitir-nf2 {nf1} {nf2}  (cross-ref + SEFAZ, irreversivel) -> chave NF-2")
    print(f"    3) --validar {nf1} {nf2}         (cstat=100 nas 2 + baixa PASSIVA + refNFe)")
    print(f"\n  [DRY-RUN] nada escrito.")


if __name__ == '__main__':
    main()
