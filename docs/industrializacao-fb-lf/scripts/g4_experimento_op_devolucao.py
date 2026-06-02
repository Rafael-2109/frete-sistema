#!/usr/bin/env python3
"""G4 EXPERIMENTO 2 — a contrapartida SEGREGA por natureza de linha na MESMA NF?

Hipotese (Rafael): detectar por linha e lancar TUDO na mesma NF, porem com a
contrapartida SEGREGADA por tipo: 5124 (venda) -> CLIENTES; 5902 (DEVOLUCAO,
op 2710) -> no_payment (= 5101020001, baixa PASSIVA).

O R2 anterior testou a 5902 com op 2864 (venda-industrializacao) = mesma natureza
do servico -> CLIENTES agregou tudo. ESTE testa a 5902 com op 2710 (dev-industrializacao).
Indicio: SARET (op 2710) cai no no_payment; VND (op 2864) cai no CLIENTES.

METODO (isolado, postada+excluida, zero sujeira):
  1. cria journal de TESTE (sale, LF, no_payment=26667 PASSIVA).
  2. COPIA a menor NF mista real p/ o journal de teste (draft).
  3. TROCA a op das linhas 5902 de 2864 -> 2710 (dev-industrializacao) + operacao_manual=True.
  4. recalcula (onchange_l10n_br_calcular_imposto_btn) como o robo.
  5. (--postar) posta e LE as linhas -> a 5902 foi p/ 5101020001 (segregada) ou CLIENTES?
  6. (--cleanup) deleta a copia + arquiva o journal.

MODOS: (sem flag) dry-run | --confirmar (cria+copia+troca op+recalc, le draft) |
        --postar MOVEID | --cleanup MOVEID JID
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
NO_PAY_PASSIVA = 26667     # 5101020001 PASSIVA LF
OP_5902_VENDA = [2864]     # op atual da 5902 na NF mista (venda-industrializacao)
OP_5902_DEV = 2710         # op de DEVOLUCAO (dev-industrializacao)
OPS_5124 = [2702, 3039]
OPS_5902 = [2864, 2710]


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v is False or v is None else str(v)


def cf(v):
    return v[1].split(' - ')[0] if isinstance(v, list) and v else '-'


def achar_nf_mista_menor(rr):
    moves = rr('account.move', [('journal_id', '=', 847), ('company_id', '=', 5),
                                ('state', '=', 'posted'), ('move_type', '=', 'out_invoice'),
                                ('amount_total', '>', 0)],
               ['id', 'name', 'amount_total'], limit=200, order='amount_total asc')
    for mv in moves:
        lines = rr('account.move.line', [('move_id', '=', mv['id']),
                                         ('l10n_br_operacao_id', 'in', OPS_5124 + OPS_5902)],
                   ['l10n_br_operacao_id'], limit=50)
        ops = {ln['l10n_br_operacao_id'][0] for ln in lines if isinstance(ln.get('l10n_br_operacao_id'), list)}
        if (ops & set(OPS_5902)) and (ops & set(OPS_5124)):
            return mv
    return None


def ler_linhas(o, rr, move_id, titulo):
    print(f"\n  --- {titulo} (move {move_id}) ---")
    mv = o.execute_kw('account.move', 'read', [[move_id]],
                      {'fields': ['name', 'state', 'journal_id', 'amount_total'], 'context': CTX})[0]
    print(f"  state={mv['state']} journal={m2o(mv['journal_id'])} total={mv.get('amount_total')}")
    lines = rr('account.move.line', [('move_id', '=', move_id)],
               ['account_id', 'l10n_br_operacao_id', 'l10n_br_cfop_id', 'l10n_br_tipo_pedido', 'debit', 'credit', 'display_type'], limit=80)
    for ln in lines:
        if ln.get('display_type') in ('line_section', 'line_note'):
            continue
        acc = m2o(ln.get('account_id'))
        flag = ''
        if acc.startswith('26667|'):
            flag = '  <<< 5101020001 PASSIVA (SEGREGADO! baixa OK)'
        elif 'CLIENTES' in acc.upper():
            flag = '  <<< CLIENTES'
        print(f"      acc={acc[:40]:40} op={m2o(ln.get('l10n_br_operacao_id'))[:20]:20} cfop={cf(ln.get('l10n_br_cfop_id')):5} "
              f"tp={ln.get('l10n_br_tipo_pedido')} D={ln.get('debit')} C={ln.get('credit')}{flag}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true')
    ap.add_argument('--trocar-op', dest='trocar_op', type=int, metavar='MOVEID',
                    help='aplica a troca op 5902->2710 numa copia draft ja existente (filtro corrigido)')
    ap.add_argument('--postar', type=int, metavar='MOVEID')
    ap.add_argument('--cleanup', nargs=2, type=int, metavar=('MOVEID', 'JID'))
    args = ap.parse_args()

    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    if args.cleanup:
        mid, jid = args.cleanup
        print(f"CLEANUP move {mid} + journal {jid}")
        st = o.execute_kw('account.move', 'read', [[mid]], {'fields': ['state'], 'context': CTX})[0]['state']
        if st == 'posted':
            o.execute_kw('account.move', 'button_draft', [[mid]], {'context': CTX})
        try:
            o.execute_kw('account.move', 'unlink', [[mid]], {'context': CTX})
            print(f"  move {mid} DELETADO")
        except Exception as e:
            print(f"  unlink falhou ({e}); button_cancel")
            o.execute_kw('account.move', 'button_cancel', [[mid]], {'context': CTX})
        try:
            o.execute_kw('account.journal', 'unlink', [[jid]], {'context': CTX})
            print(f"  journal {jid} DELETADO")
        except Exception as e:
            o.execute_kw('account.journal', 'write', [[jid], {'active': False}], {'context': CTX})
            print(f"  journal {jid} arquivado (unlink falhou: {e})")
        return

    if args.trocar_op:
        mid = args.trocar_op
        # filtro CORRIGIDO: linhas de PRODUTO (product_id != False), nao display_type
        linhas = rr('account.move.line', [('move_id', '=', mid), ('l10n_br_operacao_id', 'in', OP_5902_VENDA),
                                          ('product_id', '!=', False)], ['id', 'l10n_br_cfop_id'], limit=80)
        ids = [l['id'] for l in linhas]
        print(f"linhas 5902 (op 2864, produto) na copia {mid}: {len(ids)}")
        if ids:
            o.execute_kw('account.move.line', 'write', [ids, {'l10n_br_operacao_id': OP_5902_DEV,
                                                              'l10n_br_operacao_manual': True}], {'context': CTX})
            print(f"  trocadas -> op {OP_5902_DEV} (dev-industrializacao) + operacao_manual=True")
        try:
            o.execute_kw('account.move', 'onchange_l10n_br_calcular_imposto_btn', [[mid]], {'context': CTX})
            print("  recalculo chamado")
        except Exception as e:
            print(f"  AVISO recalculo: {e}")
        ler_linhas(o, rr, mid, "APOS TROCA op 5902 -> 2710 (DRAFT)")
        return

    if args.postar:
        mid = args.postar
        print(f"POSTAR move {mid}")
        o.execute_kw('account.move', 'action_post', [[mid]], {'context': CTX})
        ler_linhas(o, rr, mid, "POS-POST (op 5902 = 2710 dev-industrializacao)")
        return

    nf = achar_nf_mista_menor(rr)
    assert nf, "nenhuma NF mista encontrada"
    print("=" * 84)
    print("PLANO — testar contrapartida SEGREGADA por natureza de linha")
    print("=" * 84)
    print(f"  NF-modelo : move {nf['id']} {nf['name']} total={nf['amount_total']}")
    print(f"  journal teste: sale/LF no_payment={NO_PAY_PASSIVA} (5101020001 PASSIVA)")
    print(f"  troca: linhas 5902 op 2864 (venda) -> 2710 (dev-industrializacao)")
    print(f"  hipotese: 5124->CLIENTES + 5902->5101020001 (segregado, 1 NF). 0 SEFAZ, draft.")

    if not args.confirmar:
        print("\n  [DRY-RUN] nada escrito. --confirmar para executar (apos go).")
        return

    jid = o.execute_kw('account.journal', 'create',
                       [{'name': 'ZZ TESTE G4 SEGREGA — DELETAR', 'code': 'ZTG4S',
                         'type': 'sale', 'company_id': 5, 'account_no_payment_id': NO_PAY_PASSIVA}],
                       {'context': CTX})
    print(f"\n  [1/4] journal teste criado: {jid}")
    copia = o.execute_kw('account.move', 'copy', [nf['id'], {'journal_id': jid}], {'context': CTX})
    copia = copia[0] if isinstance(copia, list) else copia
    print(f"  [2/4] NF copiada: move {copia} (draft)")
    # trocar op das linhas 5902 -> 2710
    linhas5902 = rr('account.move.line', [('move_id', '=', copia), ('l10n_br_operacao_id', 'in', OP_5902_VENDA),
                                          ('display_type', '=', False)], ['id'], limit=80)
    ids5902 = [l['id'] for l in linhas5902]
    if ids5902:
        o.execute_kw('account.move.line', 'write', [ids5902, {'l10n_br_operacao_id': OP_5902_DEV,
                                                              'l10n_br_operacao_manual': True}], {'context': CTX})
        print(f"  [3/4] {len(ids5902)} linhas 5902 -> op {OP_5902_DEV} (dev-industrializacao) + operacao_manual=True")
    else:
        print(f"  [3/4] AVISO: nenhuma linha 5902 (op 2864) encontrada na copia")
    # recalcular como o robo
    try:
        o.execute_kw('account.move', 'onchange_l10n_br_calcular_imposto_btn', [[copia]], {'context': CTX})
        print(f"  [4/4] recalculo de imposto chamado")
    except Exception as e:
        print(f"  [4/4] AVISO recalculo: {e}")
    ler_linhas(o, rr, copia, "COPIA EM DRAFT (5902 -> op 2710)")
    print(f"\n  >>> postar: --postar {copia}   | cleanup: --cleanup {copia} {jid}")


if __name__ == '__main__':
    main()
