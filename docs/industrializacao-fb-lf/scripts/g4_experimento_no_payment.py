#!/usr/bin/env python3
"""G4 EXPERIMENTO — onde cai a contrapartida da 5902 vs 5124 quando o journal tem no_payment?

Pergunta decisiva (granularidade): numa NF MISTA de retorno (5902 simbolica CST51 +
5124 servico c/ tributo), com account_no_payment_id=5101020001 (26667) no journal, a
linha 5902 vai p/ 5101020001 (baixa PASSIVA) e a 5124 p/ CLIENTES? (camada-journal
resolve) — ou o no_payment pega as duas? (precisaria de posicao fiscal por-linha).

METODO ISOLADO (nao toca j847/producao):
  1. cria journal de TESTE (sale, LF, no_payment=26667) — arquivavel.
  2. COPIA a menor NF de retorno mista real p/ dentro do journal de teste (copy com
     default journal_id=teste -> linhas reais do robo, conta computada no create).
  3. le as account.move.line da copia EM DRAFT (sem postar, sem stock.move, sem SEFAZ).
  Se a contrapartida ja aparece em draft -> responde. Senao -> --postar (reversivel).

MODOS:
  (sem flag)        dry-run: mostra o plano + acha a NF a copiar
  --confirmar       cria journal teste + copia NF + le linhas em DRAFT
  --postar MOVEID   action_post da copia + le linhas (2o go)
  --cleanup MOVEID JID  cancela/deleta a copia + arquiva o journal teste
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
NO_PAY_PASSIVA = 26667   # 5101020001 REMESSA INDUSTRIALIZAÇÃO (PASSIVA), LF
OPS_5124 = [2702, 3039]
OPS_5902 = [2864, 2710]


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v is False or v is None else str(v)


def cf(v):
    return v[1].split(' - ')[0] if isinstance(v, list) and v else '-'


def achar_nf_mista_menor(rr):
    """menor NF de retorno mista (5902+5124) posted em j847."""
    moves = rr('account.move', [('journal_id', '=', 847), ('company_id', '=', 5),
                                ('state', '=', 'posted'), ('move_type', '=', 'out_invoice'),
                                ('amount_total', '>', 0)],
               ['id', 'name', 'amount_total'], limit=200, order='amount_total asc')
    for mv in moves:
        lines = rr('account.move.line', [('move_id', '=', mv['id']),
                                         ('l10n_br_operacao_id', 'in', OPS_5124 + OPS_5902)],
                   ['l10n_br_operacao_id'], limit=50)
        ops = {ln['l10n_br_operacao_id'][0] for ln in lines if isinstance(ln.get('l10n_br_operacao_id'), list)}
        tem_5902 = bool(ops & set(OPS_5902))
        tem_5124 = bool(ops & set(OPS_5124))
        if tem_5902 and tem_5124:
            return mv
    return None


def ler_linhas(o, rr, move_id, titulo):
    print(f"\n  --- {titulo} (move {move_id}) ---")
    mv = o.execute_kw('account.move', 'read', [[move_id]],
                      {'fields': ['name', 'state', 'journal_id', 'amount_total'], 'context': CTX})[0]
    print(f"  state={mv['state']} journal={m2o(mv['journal_id'])} total={mv.get('amount_total')}")
    lines = rr('account.move.line', [('move_id', '=', move_id)],
               ['account_id', 'l10n_br_operacao_id', 'l10n_br_cfop_id', 'debit', 'credit', 'display_type'], limit=60)
    for ln in lines:
        if ln.get('display_type') in ('line_section', 'line_note'):
            continue
        acc = m2o(ln.get('account_id'))
        flag = ''
        if acc.startswith('26667|'):
            flag = '  <<< 5101020001 PASSIVA (no_payment) — BAIXA OK'
        elif 'CLIENTES' in acc.upper():
            flag = '  <<< CLIENTES'
        cfop = cf(ln.get('l10n_br_cfop_id'))
        print(f"      acc={acc[:42]:42} op={m2o(ln.get('l10n_br_operacao_id'))[:22]:22} cfop={cfop:6} "
              f"D={ln.get('debit')} C={ln.get('credit')}{flag}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true')
    ap.add_argument('--postar', type=int, metavar='MOVEID')
    ap.add_argument('--cleanup', nargs=2, type=int, metavar=('MOVEID', 'JID'))
    ap.add_argument('--del-journal', dest='del_journal', type=int, metavar='JID',
                    help='tenta DELETAR o journal de teste (fallback: mantem arquivado)')
    args = ap.parse_args()

    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    # ---------- CLEANUP ----------
    if args.cleanup:
        mid, jid = args.cleanup
        print(f"CLEANUP: cancelar/deletar move {mid} + arquivar journal {jid}")
        st = o.execute_kw('account.move', 'read', [[mid]], {'fields': ['state'], 'context': CTX})[0]['state']
        if st == 'posted':
            o.execute_kw('account.move', 'button_draft', [[mid]], {'context': CTX})
            print(f"  move {mid}: posted -> draft")
        # tentar DELETAR (mais limpo que cancelar); fallback = cancelar
        try:
            o.execute_kw('account.move', 'unlink', [[mid]], {'context': CTX})
            print(f"  move {mid} DELETADO")
        except Exception as e:
            print(f"  unlink falhou ({e}); fazendo button_cancel como fallback")
            o.execute_kw('account.move', 'button_cancel', [[mid]], {'context': CTX})
            print(f"  move {mid} CANCELADO (state=cancel)")
        # confirmar que sumiu/cancelou
        chk = o.execute_kw('account.move', 'search_read', [[('id', '=', mid)]],
                           {'fields': ['state'], 'context': CTX})
        print(f"  POS-CHECK move {mid}: {chk[0]['state'] if chk else 'NAO EXISTE MAIS (deletado)'}")
        o.execute_kw('account.journal', 'write', [[jid], {'active': False}], {'context': CTX})
        jchk = o.execute_kw('account.journal', 'read', [[jid]], {'fields': ['active'], 'context': CTX})[0]
        print(f"  journal {jid} arquivado: active={jchk['active']}")
        return

    # ---------- DEL-JOURNAL ----------
    if args.del_journal:
        jid = args.del_journal
        # buscar mesmo arquivado (active_test=False)
        j = o.execute_kw('account.journal', 'search_read', [[('id', '=', jid)]],
                         {'fields': ['id', 'name', 'active'], 'context': dict(CTX, active_test=False)})
        if not j:
            print(f"journal {jid} NAO existe (ja deletado).")
            return
        # nao deixar moves orfaos
        nml = o.execute_kw('account.move.line', 'search_count', [[('journal_id', '=', jid)]],
                           {'context': dict(CTX, active_test=False)})
        print(f"journal {jid} ({j[0]['name']}) active={j[0]['active']}; account.move.line vinculadas={nml}")
        if nml:
            print("  ABORT: ainda ha linhas vinculadas — nao deleto (deixo arquivado).")
            return
        try:
            o.execute_kw('account.journal', 'unlink', [[jid]], {'context': CTX})
            chk = o.execute_kw('account.journal', 'search_read', [[('id', '=', jid)]],
                               {'fields': ['id'], 'context': dict(CTX, active_test=False)})
            print(f"  journal {jid} DELETADO" if not chk else f"  ainda existe: {chk}")
        except Exception as e:
            print(f"  unlink do journal falhou ({e}) — fica ARQUIVADO (active=False), sem uso.")
        return

    # ---------- POSTAR ----------
    if args.postar:
        mid = args.postar
        print(f"POSTAR move {mid} (action_post) — gera lancamento contabil (sem SEFAZ; reversivel)")
        o.execute_kw('account.move', 'action_post', [[mid]], {'context': CTX})
        ler_linhas(o, rr, mid, "POS-POST")
        return

    # ---------- achar NF a copiar ----------
    nf = achar_nf_mista_menor(rr)
    assert nf, "nenhuma NF de retorno mista encontrada em j847"
    print("=" * 84)
    print("PLANO DO EXPERIMENTO")
    print("=" * 84)
    print(f"  NF-modelo a copiar : move {nf['id']} {nf['name']} total={nf['amount_total']} (a MENOR mista de j847)")
    print(f"  journal de teste   : sale/LF(5) no_payment={NO_PAY_PASSIVA} (5101020001 PASSIVA) — arquivavel")
    print(f"  passos             : criar journal teste -> copy NF p/ esse journal (DRAFT) -> ler linhas em DRAFT")
    print(f"  efeito             : 0 SEFAZ, 0 stock.move, 0 lancamento (fica DRAFT). cleanup ao final.")

    if not args.confirmar:
        print("\n  [DRY-RUN] nada escrito. Rode com --confirmar para executar (autorizado).")
        return

    # ---------- EXECUTAR: journal teste + copy + ler draft ----------
    jid = o.execute_kw('account.journal', 'create',
                       [{'name': 'ZZ TESTE G4 RETORNO — DELETAR', 'code': 'ZTG4',
                         'type': 'sale', 'company_id': 5,
                         'account_no_payment_id': NO_PAY_PASSIVA}], {'context': CTX})
    print(f"\n  [1/3] journal de teste criado: id={jid}")

    copia_id = o.execute_kw('account.move', 'copy', [nf['id'], {'journal_id': jid}], {'context': CTX})
    if isinstance(copia_id, list):
        copia_id = copia_id[0]
    print(f"  [2/3] NF copiada p/ journal teste: move {copia_id} (DRAFT)")

    print(f"  [3/3] lendo linhas da copia em DRAFT:")
    ler_linhas(o, rr, copia_id, "COPIA EM DRAFT (journal teste com no_payment)")

    print(f"\n  >>> Para inspecao pos-post (se draft nao mostrar contrapartida): "
          f"--postar {copia_id}")
    print(f"  >>> Cleanup ao final: --cleanup {copia_id} {jid}")


if __name__ == '__main__':
    main()
