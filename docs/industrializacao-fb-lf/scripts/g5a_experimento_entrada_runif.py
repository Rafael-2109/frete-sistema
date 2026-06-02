#!/usr/bin/env python3
"""G5a EXPERIMENTO ENTRADA (R-UNIF) — o no_payment baixa a ATIVA numa NF MISTA de ENTRADA?

ESPELHO do experimento de SAIDA validado (g4_experimento_no_payment / _op_devolucao),
agora no LADO ENTRADA (FB), para fechar a duvida R-UNIF (`ACHADOS §sessao 5` linha 223).

CONTEXTO REAL (verificado ao vivo 2026-06-02, /tmp/verif_entsi_linha.py):
  - 0 linhas em j1001 tocam a 5101010001 (ATIVA) -> a entrada NUNCA baixa a ATIVA hoje.
  - 490 ENTSI sao MISTA (1124 servico + 1902 insumos); 1060 pura-servico; 1 pura-insumos.
  - op real: 1124 -> 1917; 1902 -> 2027 (movimento_estoque=True; AUTOCANCELA em 1150100011).
  - o PILOTO roteia a 1902 por op 3252 (movimento_estoque=False) -> e' o que importa testar.

PERGUNTA DECISIVA: numa NF MISTA de entrada, com a 1902 em op 3252 (mov_estoque=False) e
account_no_payment_id=22800 (5101010001 ATIVA) no journal:
  -> a 1902 gera a contrapartida no_payment = C 5101010001 (baixa a ATIVA => G5a INDEPENDENTE)?
  -> ou o FORNECEDORES (payable da linha de servico 1124) ABSORVE a 1902 e o no_payment NAO
     materializa (=> R-UNIF CONFIRMADO: G5a converge com o G4 — ambos exigem doc separado)?

PREDICao (READ-only, alta confianca): R-UNIF CONFIRMADO (FORNECEDORES absorve), pois a estrutura
e' identica a' saida ja provada (CLIENTES absorveu a 5902). Este experimento da' a prova 100%.

METODO ISOLADO (postada+excluida, zero sujeira — identico ao da saida):
  1. cria/reusa journal de TESTE (purchase, FB(1), no_payment=22800 ATIVA) — arquivavel/deletavel.
  2. COPIA a menor ENTSI mista real p/ esse journal (draft).
  3. (variante op3252, DEFAULT) troca as linhas 1902 de op 2027 -> op 3252 + operacao_manual=True
     e recalcula (onchange_l10n_br_calcular_imposto_btn), como o robo faria no piloto.
  4. le as linhas em DRAFT.
  5. (--postar) action_post recomputa a contrapartida -> 1902 -> 5101010001 ou FORNECEDORES?
  6. (--cleanup) deleta a copia + arquiva/deleta o journal teste.
  ENTRADA (in_invoice) NAO transmite SEFAZ; copia avulsa NAO tem picking/DFe -> 0 stock.move.
  Reversivel por delete.

MODOS:
  (sem flag)            DRY-RUN: acha a ENTSI mista + MOSTRA o baseline real. NADA escrito.
  --confirmar          cria/reusa journal + copia + (op3252) troca op da 1902 + recalc + le draft
  --variante {op3252,as-is}  op3252 (default, fiel ao piloto) | as-is (mantem op 2027 historica)
  --modelo MOVEID      forca a NF-modelo (default = menor mista achada via linha)
  --postar MOVEID      action_post da copia + le linhas (a RESPOSTA aparece aqui)
  --cleanup MOVEID JID deleta a copia + arquiva/deleta o journal teste
  --del-journal JID    tenta DELETAR o journal de teste (fallback: mantem arquivado)
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
NO_PAY_ATIVA = 22800     # 5101010001 REMESSA INDUSTRIALIZACAO (ATIVA), company FB(1)
J1001 = 1001             # ENTSI FB (purchase)
TEST_JOURNAL_CODE = 'ZTG5A'
TEST_JOURNAL_NAME = 'ZZ TESTE G5a ENTRADA RUNIF — DELETAR'
CFOP_1124_ID = 11        # 1124 servico (gera FORNECEDORES = payable real)
CFOP_1902_ID = 102       # 1902 insumos simbolico CST51
OP_3252 = 3252           # 1902 simbolico mov_estoque=False (op do PILOTO)


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v is False or v is None else str(v)


def cf(v):
    return v[1].split(' - ')[0].strip() if isinstance(v, list) and v else '-'


def achar_entsi_mista_menor(rr):
    """menor ENTSI (in_invoice) posted em j1001 com linha 1124 E linha 1902 — via account.move.line."""
    base = [('journal_id', '=', J1001), ('company_id', '=', 1),
            ('parent_state', '=', 'posted'), ('move_id.move_type', '=', 'in_invoice')]
    l1124 = rr('account.move.line', base + [('l10n_br_cfop_id', '=', CFOP_1124_ID)], ['move_id'], limit=4000)
    l1902 = rr('account.move.line', base + [('l10n_br_cfop_id', '=', CFOP_1902_ID)], ['move_id'], limit=9000)
    m1124 = {l['move_id'][0] for l in l1124 if l.get('move_id')}
    m1902 = {l['move_id'][0] for l in l1902 if l.get('move_id')}
    mistas = list(m1124 & m1902)
    if not mistas:
        return None
    mv = rr('account.move', [('id', 'in', mistas)], ['id', 'name', 'amount_total', 'partner_id'],
            limit=5, order='amount_total asc')
    return mv[0] if mv else None


def ler_linhas(o, rr, move_id, titulo):
    print(f"\n  --- {titulo} (move {move_id}) ---")
    mv = o.execute_kw('account.move', 'read', [[move_id]],
                      {'fields': ['name', 'state', 'journal_id', 'move_type', 'amount_total'], 'context': CTX})[0]
    print(f"  name={mv['name']} state={mv['state']} type={mv.get('move_type')} "
          f"journal={m2o(mv['journal_id'])} total={mv.get('amount_total')}")
    lines = rr('account.move.line', [('move_id', '=', move_id)],
               ['account_id', 'l10n_br_operacao_id', 'l10n_br_cfop_id', 'l10n_br_tipo_pedido',
                'debit', 'credit', 'display_type'], limit=200)
    sum_ativa = sum((ln.get('credit') or 0) - (ln.get('debit') or 0)
                    for ln in lines if isinstance(ln.get('account_id'), list) and ln['account_id'][0] == NO_PAY_ATIVA)
    for ln in lines:
        if ln.get('display_type') in ('line_section', 'line_note'):
            continue
        acc = m2o(ln.get('account_id'))
        flag = ''
        if acc.startswith(f'{NO_PAY_ATIVA}|'):
            flag = '  <<< 5101010001 ATIVA (no_payment) — BAIXA OK => G5a INDEPENDENTE'
        elif acc.startswith('2120100001|') or 'FORNECEDOR' in acc.upper():
            flag = '  <<< FORNECEDORES (payable do servico) — se absorve a 1902 => R-UNIF'
        elif acc.startswith('1150100011|'):
            flag = '  <  transitoria RECEB FISICO FISCAL'
        elif acc.startswith(('1150100007|', '1150100001|', '1150100002|')):
            flag = '  <  estoque proprio'
        print(f"      acc={acc[:44]:44} op={m2o(ln.get('l10n_br_operacao_id'))[:18]:18} cfop={cf(ln.get('l10n_br_cfop_id')):6} "
              f"D={ln.get('debit')} C={ln.get('credit')}{flag}")
    print(f"  >>> NET na 5101010001 (ATIVA): C-D = {round(sum_ativa, 2)}  "
          f"({'BAIXOU a ATIVA => G5a independente' if abs(sum_ativa) > 0.001 else 'ZERO => no_payment NAO materializou (R-UNIF)'})")


def _find_test_journal(o):
    js = o.execute_kw('account.journal', 'search_read',
                      [[('code', '=', TEST_JOURNAL_CODE), ('company_id', '=', 1)]],
                      {'fields': ['id', 'name', 'active', 'account_no_payment_id'],
                       'context': dict(CTX, active_test=False)})
    return js[0] if js else None


def _trocar_1902_para_op3252(o, rr, move_id):
    linhas = rr('account.move.line', [('move_id', '=', move_id), ('l10n_br_cfop_id', '=', CFOP_1902_ID),
                                      ('product_id', '!=', False)], ['id'], limit=200)
    ids = [l['id'] for l in linhas]
    print(f"  linhas 1902 (cfop {CFOP_1902_ID}, produto) na copia: {len(ids)}")
    if ids:
        o.execute_kw('account.move.line', 'write', [ids, {'l10n_br_operacao_id': OP_3252,
                                                          'l10n_br_operacao_manual': True}], {'context': CTX})
        print(f"  -> trocadas p/ op {OP_3252} (mov_estoque=False, piloto) + operacao_manual=True")
    try:
        o.execute_kw('account.move', 'onchange_l10n_br_calcular_imposto_btn', [[move_id]], {'context': CTX})
        print("  -> recalculo de imposto chamado")
    except Exception as e:
        print(f"  AVISO recalculo: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true')
    ap.add_argument('--variante', choices=['op3252', 'as-is'], default='op3252')
    ap.add_argument('--modelo', type=int, metavar='MOVEID')
    ap.add_argument('--trocar-op', dest='trocar_op', type=int, metavar='MOVEID',
                    help='aplica a troca 1902->op3252 numa copia draft ja existente')
    ap.add_argument('--postar', type=int, metavar='MOVEID')
    ap.add_argument('--cleanup', nargs=2, type=int, metavar=('MOVEID', 'JID'))
    ap.add_argument('--del-journal', dest='del_journal', type=int, metavar='JID')
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
        print(f"CLEANUP: deletar move {mid} + arquivar/deletar journal {jid}")
        st = o.execute_kw('account.move', 'read', [[mid]], {'fields': ['state'], 'context': CTX})[0]['state']
        if st == 'posted':
            o.execute_kw('account.move', 'button_draft', [[mid]], {'context': CTX})
            print(f"  move {mid}: posted -> draft")
        try:
            o.execute_kw('account.move', 'unlink', [[mid]], {'context': CTX})
            print(f"  move {mid} DELETADO")
        except Exception as e:
            print(f"  unlink falhou ({e}); button_cancel como fallback")
            o.execute_kw('account.move', 'button_cancel', [[mid]], {'context': CTX})
            print(f"  move {mid} CANCELADO (state=cancel)")
        chk = o.execute_kw('account.move', 'search_read', [[('id', '=', mid)]],
                           {'fields': ['state'], 'context': CTX})
        print(f"  POS-CHECK move {mid}: {chk[0]['state'] if chk else 'NAO EXISTE MAIS (deletado)'}")
        nml = o.execute_kw('account.move.line', 'search_count', [[('journal_id', '=', jid)]],
                           {'context': dict(CTX, active_test=False)})
        if nml == 0:
            try:
                o.execute_kw('account.journal', 'unlink', [[jid]], {'context': CTX})
                print(f"  journal {jid} DELETADO")
                return
            except Exception as e:
                print(f"  unlink journal falhou ({e}); arquivando")
        else:
            print(f"  journal {jid} ainda tem {nml} linhas — arquivo")
        o.execute_kw('account.journal', 'write', [[jid], {'active': False}], {'context': CTX})
        jchk = o.execute_kw('account.journal', 'read', [[jid]], {'fields': ['active'], 'context': CTX})[0]
        print(f"  journal {jid} arquivado: active={jchk['active']}")
        return

    # ---------- DEL-JOURNAL ----------
    if args.del_journal:
        jid = args.del_journal
        j = o.execute_kw('account.journal', 'search_read', [[('id', '=', jid)]],
                         {'fields': ['id', 'name', 'active'], 'context': dict(CTX, active_test=False)})
        if not j:
            print(f"journal {jid} NAO existe (ja deletado).")
            return
        nml = o.execute_kw('account.move.line', 'search_count', [[('journal_id', '=', jid)]],
                           {'context': dict(CTX, active_test=False)})
        print(f"journal {jid} ({j[0]['name']}) active={j[0]['active']}; linhas vinculadas={nml}")
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

    # ---------- TROCAR-OP (numa copia draft existente) ----------
    if args.trocar_op:
        _trocar_1902_para_op3252(o, rr, args.trocar_op)
        ler_linhas(o, rr, args.trocar_op, "APOS TROCA 1902 -> op 3252 (DRAFT)")
        return

    # ---------- POSTAR ----------
    if args.postar:
        mid = args.postar
        print(f"POSTAR move {mid} (action_post) — recomputa a contrapartida (sem SEFAZ; reversivel por delete)")
        o.execute_kw('account.move', 'action_post', [[mid]], {'context': CTX})
        ler_linhas(o, rr, mid, "POS-POST — RESPOSTA R-UNIF (1902 -> ATIVA ou FORNECEDORES?)")
        return

    # ---------- achar/forcar ENTSI a copiar ----------
    if args.modelo:
        nf = o.execute_kw('account.move', 'read', [[args.modelo]],
                          {'fields': ['id', 'name', 'amount_total', 'partner_id'], 'context': CTX})[0]
    else:
        nf = achar_entsi_mista_menor(rr)
    assert nf, "nenhuma ENTSI mista (1124+1902) encontrada em j1001"
    print("=" * 92)
    print(f"PLANO DO EXPERIMENTO — G5a ENTRADA (R-UNIF)   variante={args.variante}")
    print("=" * 92)
    print(f"  ENTSI-modelo a copiar : move {nf['id']} {nf['name']} total={nf['amount_total']} "
          f"partner={m2o(nf.get('partner_id'))}")
    print(f"  journal de teste       : purchase/FB(1) code={TEST_JOURNAL_CODE} no_payment={NO_PAY_ATIVA} (5101010001 ATIVA)")
    jt = _find_test_journal(o)
    if jt:
        print(f"  (!) ja existe journal de teste id={jt['id']} active={jt['active']} — sera REUSADO no --confirmar")
    if args.variante == 'op3252':
        print(f"  troca                  : linhas 1902 (cfop 102) op 2027 -> op {OP_3252} (mov_estoque=False, piloto) + recalc")
    else:
        print(f"  troca                  : NENHUMA (mantem op 2027 historica — 1902 autocancela)")
    print(f"  efeito                 : 0 SEFAZ (entrada nao transmite), 0 stock.move (copia avulsa s/ picking), reversivel. cleanup ao final.")

    print("\n  --- BASELINE: linhas ATUAIS da ENTSI-modelo (hoje, j1001 real, no_payment VAZIO) ---")
    ler_linhas(o, rr, nf['id'], "BASELINE ENTSI-modelo (posted, j1001 real)")

    if not args.confirmar:
        print("\n  [DRY-RUN] nada escrito. Para executar: --confirmar (apos 'go' FRESCO do Rafael).")
        return

    # ---------- EXECUTAR: journal teste + copy (+ troca op) + ler draft ----------
    jt = _find_test_journal(o)
    if jt:
        jid = jt['id']
        if not jt['active']:
            o.execute_kw('account.journal', 'write', [[jid], {'active': True}], {'context': CTX})
        o.execute_kw('account.journal', 'write', [[jid], {'account_no_payment_id': NO_PAY_ATIVA}], {'context': CTX})
        print(f"\n  [1/4] journal de teste REUSADO: id={jid} (no_payment={NO_PAY_ATIVA})")
    else:
        jid = o.execute_kw('account.journal', 'create',
                           [{'name': TEST_JOURNAL_NAME, 'code': TEST_JOURNAL_CODE,
                             'type': 'purchase', 'company_id': 1,
                             'account_no_payment_id': NO_PAY_ATIVA}], {'context': CTX})
        print(f"\n  [1/4] journal de teste criado: id={jid}")

    copia_id = o.execute_kw('account.move', 'copy', [nf['id'], {'journal_id': jid}], {'context': CTX})
    if isinstance(copia_id, list):
        copia_id = copia_id[0]
    print(f"  [2/4] ENTSI copiada p/ journal teste: move {copia_id} (DRAFT)")

    if args.variante == 'op3252':
        print(f"  [3/4] trocando 1902 -> op {OP_3252}:")
        _trocar_1902_para_op3252(o, rr, copia_id)
    else:
        print(f"  [3/4] variante as-is — sem troca de op")

    print(f"  [4/4] lendo linhas da copia em DRAFT:")
    ler_linhas(o, rr, copia_id, "COPIA EM DRAFT (journal teste no_payment=22800)")

    print(f"\n  >>> Para a RESPOSTA R-UNIF (recompute no post): --postar {copia_id}")
    print(f"  >>> Cleanup ao final: --cleanup {copia_id} {jid}")


if __name__ == '__main__':
    main()
