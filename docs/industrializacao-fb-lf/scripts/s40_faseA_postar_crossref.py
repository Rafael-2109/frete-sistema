#!/usr/bin/env python3
"""S40 — FASE A (REVERSIVEL, PARA antes de transmitir): posta as 2 NFs do piloto +
completa o R3 (cross-refNFe NF-2 -> chave da NF-1) + mede a baixa da PASSIVA no contexto
das 2 NFs juntas. NAO transmite (cstat deve ficar vazio).

Ambos os journals (j847, RETIND 1083) tem restrict_mode_hash_table=False -> post REVERSIVEL.
Reverter: python s37_sa_gerar_retorno_2nf.py --cleanup 325344 789484 789485

Sequencia:
  1. action_post NF-1 (servico 789484) -> le chave/numero (a chave costuma vir no post)
  2. se NF-1 tem chave: NF-2.referencia_ids += chave NF-1 (cross-vinculo R3, completa o requisito)
  3. action_post NF-2 (insumos 789485) -> mede baixa PASSIVA 5101020001 (saldo antes/depois)
  4. valida: ambas posted, cstat VAZIO (NAO transmitido), baixa = Delta saldo
  >>> PARA aqui. Transmissao (IRREVERSIVEL, PRODUCAO) = passo seguinte, so com go duplo.

MODOS:
  (sem flag)   dry-run: pre-check hash + estado das 2 + saldo PASSIVA + plano
  --executar   posta as 2 + cross-refNFe + mede (PARA antes de transmitir)

IDs (defaults = piloto da sessao 2026-06-14; sobrescreve via --nf1/--nf2/--pick para
NFs novas geradas pelo s37 --gerar):
  --nf1 ID  --nf2 ID  --pick ID
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF1, NF2 = 789484, 789485     # servico, insumos (defaults; sobrescreve via --nf1/--nf2)
PICK = 325344
J847, RETIND = 847, 1083
ACC_PASSIVA = 26667           # 5101020001 PASSIVA LF
POST_CTX = dict(CTX, allowed_company_ids=[5])


def m2o(v):
    return f"{v[0]}|{str(v[1])[:24]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    global NF1, NF2, PICK
    ap = argparse.ArgumentParser()
    ap.add_argument('--executar', action='store_true')
    ap.add_argument('--nf1', type=int, help='ID da NF-1 (servico); default=piloto sessao')
    ap.add_argument('--nf2', type=int, help='ID da NF-2 (insumos); default=piloto sessao')
    ap.add_argument('--pick', type=int, help='ID do picking; default=piloto sessao')
    args = ap.parse_args()
    if args.nf1: NF1 = args.nf1
    if args.nf2: NF2 = args.nf2
    if args.pick: PICK = args.pick
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)
    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    def saldo_passiva():
        lns = rr('account.move.line', [('account_id', '=', ACC_PASSIVA),
                                       ('parent_state', '=', 'posted'), ('company_id', '=', 5)], ['balance'])
        return round(sum(l.get('balance') or 0 for l in lns), 2)

    SEFAZ = ['name', 'state', 'l10n_br_chave_nf', 'l10n_br_cstat_nf', 'l10n_br_numero_nf',
             'amount_total', 'l10n_br_total_nfe']

    # pre-check hash
    js = rd('account.journal', [J847, RETIND], ['name', 'restrict_mode_hash_table'])
    hashed = any(j.get('restrict_mode_hash_table') for j in js)
    print("=" * 90)
    print("S40 — FASE A (postar 2 NFs + cross-refNFe + medir baixa) — PARA antes de transmitir")
    print("=" * 90)
    for j in js:
        print(f"  journal {j['id']} {j['name'][:34]}: hash={j.get('restrict_mode_hash_table')} "
              f"{'⚠️ NAO reversivel' if j.get('restrict_mode_hash_table') else '✅ reversivel'}")
    for label, nf in [('NF-1 servico', NF1), ('NF-2 insumos', NF2)]:
        h = rd('account.move', [nf], SEFAZ)[0]
        print(f"  {label} {nf}: state={h['state']} chave={h.get('l10n_br_chave_nf') or '-'} "
              f"cstat={h.get('l10n_br_cstat_nf') or '-'} total={h.get('amount_total')} vNF={h.get('l10n_br_total_nfe')}")
    print(f"  saldo PASSIVA 5101020001 (LF) atual = {saldo_passiva()}")

    if not args.executar:
        print("\n  [DRY-RUN] nada escrito. Fase A: --executar (posta as 2, reversivel, PARA antes de transmitir)")
        return
    if hashed:
        print("\n  ❌ ABORTADO: algum journal tem hash=True (post nao reversivel). Nao executo a Fase A.")
        return

    saldo0 = saldo_passiva()
    # 1. postar NF-1
    print(f"\n  [1] action_post NF-1 {NF1} (servico)...")
    try:
        o.execute_kw('account.move', 'action_post', [[NF1]], {'context': POST_CTX})
    except Exception as e:
        print(f"      ❌ post NF-1 FALHOU: {str(e)[:240]}"); return
    h1 = rd('account.move', [NF1], SEFAZ)[0]
    chave1 = h1.get('l10n_br_chave_nf')
    print(f"      NF-1 posted: name={h1['name']} num={h1.get('l10n_br_numero_nf')} "
          f"chave={chave1 or '(sem chave no post)'} cstat={h1.get('l10n_br_cstat_nf') or '-'}")

    # 2. cross-refNFe NF-2 -> chave NF-1 (completa R3)
    if chave1:
        try:
            o.execute_kw('account.move', 'write', [[NF2], {
                'referencia_ids': [(0, 0, {'l10n_br_chave_nf': chave1, 'company_id': 5})]}],
                {'context': dict(CTX, check_move_validity=False)})
            print(f"  [2] cross-refNFe: NF-2 agora referencia a chave da NF-1 ✅ ({chave1})")
        except Exception as e:
            print(f"  [2] cross-refNFe FALHOU: {str(e)[:160]}")
    else:
        print(f"  [2] NF-1 sem chave no post -> cross-refNFe NF-2->NF-1 fica p/ pos-transmissao")

    # 3. postar NF-2
    print(f"\n  [3] action_post NF-2 {NF2} (insumos) — mede baixa PASSIVA...")
    try:
        o.execute_kw('account.move', 'action_post', [[NF2]], {'context': POST_CTX})
    except Exception as e:
        print(f"      ❌ post NF-2 FALHOU: {str(e)[:240]}"); return
    saldo1 = saldo_passiva()
    nfl = rr('account.move.line', [('move_id', '=', NF2), ('account_id', '=', ACC_PASSIVA)],
             ['debit', 'credit', 'display_type'])
    debito = round(sum(l.get('debit') or 0 for l in nfl), 2)
    h2 = rd('account.move', [NF2], SEFAZ)[0]
    print(f"      NF-2 posted: name={h2['name']} cstat={h2.get('l10n_br_cstat_nf') or '-'}")
    print(f"      saldo PASSIVA: {saldo0} -> {saldo1} | Δ = {round(saldo1-saldo0,2)} | D na conta 26667 = {debito}")

    # 4. validacao final
    print(f"\n  === VALIDACAO FASE A ===")
    f1 = rd('account.move', [NF1], SEFAZ)[0]; f2 = rd('account.move', [NF2], SEFAZ)[0]
    ref2 = rr('l10n_br_ciel_it_account.account.move.referencia', [('move_id', '=', NF2)], ['l10n_br_chave_nf'])
    print(f"    NF-1: state={f1['state']} cstat={f1.get('l10n_br_cstat_nf') or 'VAZIO (nao transmitido) ✅'}")
    print(f"    NF-2: state={f2['state']} cstat={f2.get('l10n_br_cstat_nf') or 'VAZIO (nao transmitido) ✅'}")
    print(f"    baixa PASSIVA: Δ={round(saldo1-saldo0,2)} == D conta {debito}: "
          f"{'✅' if abs((saldo1-saldo0)-debito) < 0.01 and debito > 0 else '⚠️'}")
    print(f"    R3 referencia_ids da NF-2 ({len(ref2)}): {[r['l10n_br_chave_nf'][-12:] for r in ref2]} "
          f"{'(remessa + NF-1 cross ✅)' if len(ref2) >= 2 else '(so remessa)'}")
    print(f"\n  >>> PAROU NA BEIRA. Ambas POSTED, NAO transmitidas. Transmissao (PRODUCAO, irreversivel) = proximo, go duplo.")
    print(f"  >>> reverter Fase A: python docs/industrializacao-fb-lf/scripts/s37_sa_gerar_retorno_2nf.py --cleanup {PICK} {NF1} {NF2}")


if __name__ == '__main__':
    main()
