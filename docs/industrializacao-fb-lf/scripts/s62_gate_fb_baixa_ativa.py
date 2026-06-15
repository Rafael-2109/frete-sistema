#!/usr/bin/env python3
"""S62 — GATE-FB (R2.2): a ENTRADA no j1084 baixa a ATIVA 5101010001?

Espelho do GATE-0 da LF (que provou a baixa da PASSIVA na SAIDA). Aqui provo o
SINAL na ENTRADA: in_invoice no journal ENTRI (j1084, no_payment=22800) com 1
linha de insumo (op 3252 simbolica) -> post -> a contrapartida no_payment deve
CREDITAR 5101010001 (22800) = baixa. type (purchase) inverte o sinal vs a saida.

NF-teste pequena, postada e revertida/deletada (zero rabo). PRODUCAO (CIEL IT).

Modos:
  --plan       (DEFAULT) mostra o que sera montado (NAO escreve)
  --executar   monta + recompute + POST + mede Δ22800 + mostra move lines (deixa postado p/ inspecao)
  --cleanup ID button_draft + unlink + confirma saldo restaurado
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 1, 'lang': 'pt_BR'}
JOURNAL_ENTRI = 1084          # FB purchase no_payment=22800 (ATIVA)
CONTA_ATIVA = 22800           # 5101010001
PARTNER_LF = 35               # LF como fornecedor na FB
OP_3252 = 3252                # entrada 1902 simbolica (movimento_estoque=False)
NF2 = 791441                  # p/ pegar 1 produto real de insumo
SEP = '=' * 96


def saldo_conta(o, conta_id):
    """Soma balance das account.move.line POSTADAS na conta (company FB)."""
    rg = o.execute_kw('account.move.line', 'read_group',
                      [[('account_id', '=', conta_id), ('company_id', '=', 1),
                        ('parent_state', '=', 'posted')],
                       ['balance:sum'], []],
                      {'context': CTX})
    return round(rg[0].get('balance') or 0.0, 2) if rg else 0.0


def main():
    args = sys.argv[1:]
    o = get_odoo_connection()
    assert o.authenticate(), 'FALHA AUTH'

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    # ---- cleanup ----
    if '--cleanup' in args:
        mid = int(args[args.index('--cleanup') + 1])
        m = rd('account.move', [mid], ['name', 'state'])
        print(f'cleanup move {mid}: {m}')
        if m and m[0]['state'] == 'posted':
            o.execute_kw('account.move', 'button_draft', [[mid]], {'context': CTX})
            print('  -> draft')
        o.execute_kw('account.move', 'unlink', [[mid]], {'context': CTX})
        print('  -> unlink OK')
        print(f'  saldo 22800 agora: {saldo_conta(o, CONTA_ATIVA)}')
        return

    # TODAS as linhas product da NF-2 (16 insumos reais) — fidelidade + Δ limpo
    linhas = o.execute_kw('account.move.line', 'search_read',
                          [[('move_id', '=', NF2), ('display_type', '=', 'product')]],
                          {'fields': ['product_id', 'quantity', 'price_unit', 'price_subtotal'],
                           'context': CTX})
    assert linhas, 'sem linha product na NF-2'
    total = round(sum(l['price_subtotal'] for l in linhas), 2)
    inv_date = rd('account.move', [NF2], ['invoice_date'])[0]['invoice_date']

    print(SEP)
    print('S62 — GATE-FB (R2.2): entrada j1084 baixa a ATIVA 5101010001?')
    print(SEP)
    print(f"\n  journal      = {JOURNAL_ENTRI} (ENTRI, no_payment=22800)")
    print(f"  partner      = {PARTNER_LF} (LF)")
    print(f"  linhas       = {len(linhas)} insumos (replica a NF-2 791441)")
    print(f"  total        = {total}  (= untax NF-2 = 279,23 esperado)")
    print(f"  op linha     = {OP_3252} (1902 simbolica, movimento_estoque=False)")
    print(f"  saldo 22800 ATUAL (devedor=ATIVA): {saldo_conta(o, CONTA_ATIVA)}")
    print("\n  ESPERADO no post: a linha da conta 22800 (no_payment) vem como")
    print("                    CREDIT = total  => baixa da ATIVA 5101010001")

    if '--executar' not in args:
        print('\n  [PLAN] nada escrito. Para executar: --executar')
        print(SEP)
        return

    saldo_antes = saldo_conta(o, CONTA_ATIVA)
    print(f'\n  [EXECUTAR] saldo 22800 ANTES = {saldo_antes}')

    # montar in_invoice com as 16 linhas
    inv_lines = [(0, 0, {
        'product_id': l['product_id'][0],
        'quantity': l['quantity'],
        'price_unit': l['price_unit'],
        'l10n_br_operacao_id': OP_3252,
        'l10n_br_operacao_manual': True,  # senao onchange apaga a op (gotcha LF s24)
    }) for l in linhas]
    move_vals = {
        'move_type': 'in_invoice',
        'journal_id': JOURNAL_ENTRI,
        'company_id': 1,
        'partner_id': PARTNER_LF,
        'invoice_date': inv_date,            # obrigatorio p/ postar (gotcha)
        'l10n_br_calcular_imposto': False,   # retorno SEM imposto (igual NF real)
        'invoice_line_ids': inv_lines,
    }
    mid = o.execute_kw('account.move', 'create', [move_vals], {'context': CTX})
    print(f'  in_invoice draft criada id={mid} ({len(inv_lines)} linhas)')

    # post
    o.execute_kw('account.move', 'action_post', [[mid]], {'context': CTX})
    m = rd('account.move', [mid], ['name', 'state', 'amount_total', 'amount_untaxed'])
    print(f'  POST OK: {m}')

    # move lines do lancamento (agregar por conta)
    mls = o.execute_kw('account.move.line', 'search_read',
                       [[('move_id', '=', mid)]],
                       {'fields': ['account_id', 'name', 'debit', 'credit',
                                   'display_type'], 'context': CTX})
    agg = {}
    for ml in mls:
        acc = ml['account_id'][1] if ml.get('account_id') else '(sem conta)'
        d, c = agg.get(acc, (0, 0))
        agg[acc] = (round(d + ml['debit'], 2), round(c + ml['credit'], 2))
    print('\n  MOVE LINES (agregado por conta):')
    linha_ativa = None
    for acc, (d, c) in sorted(agg.items(), key=lambda x: -x[1][1]):
        flag = ''
        if str(CONTA_ATIVA) in acc or '5101010001' in acc:
            flag = '  <<< ATIVA (no_payment)'
            linha_ativa = (d, c)
        print(f"    {acc:50} D={d:>10} C={c:>10}{flag}")

    saldo_depois = saldo_conta(o, CONTA_ATIVA)
    delta = round(saldo_depois - saldo_antes, 2)
    print(f'\n  saldo global 22800: {saldo_antes} -> {saldo_depois}  (Δ = {delta:+})')
    if linha_ativa and linha_ativa[1] > 0 and delta < 0:
        print(f'  ✅ ATIVA 5101010001 BAIXOU: C={linha_ativa[1]} (Δglobal {delta}) — PROVADO')
    else:
        print(f'  ⚠️  conferir: linha ATIVA={linha_ativa}, Δ={delta}')
    print(f'\n  reverter: python {sys.argv[0]} --cleanup {mid}')
    print(SEP)


if __name__ == '__main__':
    main()
