#!/usr/bin/env python3
"""G4/G5a GROUNDING 5 (READ-ONLY) — fecha os 3 GAPS pedidos pela verificacao adversarial.

(a) Distribuicao das ENTSI j1001 por operacao do HEADER + por op das linhas 1902:
    quantas sao retorno-real (op 1917 servico+insumos) vs simbolico-nao-retorno
    (op 2027/3214/3120). E checar se TODAS sao partner=35 (LF) — incl. historico.
(b) VALIDA C4 empiricamente: achar NF de ENTRADA real num journal purchase FB que
    JA TEM no_payment setado (j1011 rem-ind no_pay=22815; j868 transf no_pay=22827;
    j993 bonif no_pay=22817) e ver se o no_payment vira contrapartida (credito) SO
    das linhas simbolicas, deixando a linha de serviço/tributo em FORNECEDORES.
(c) Qual conta a op 3252 (movimento_estoque=False) DEBITA na 1902 sem stock.move:
    posicao fiscal + conta da operacao; e se ja existe NF que usou op 3252.
NAO escreve nada.
"""
import sys
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v is False or v is None else str(v)


def cf(v):
    return v[1].split(' - ')[0] if isinstance(v, list) and v else '-'


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [ids], {'fields': fields, 'context': CTX})

    # ====================================================================
    print("\n" + "=" * 90)
    print("(a) ENTSI j1001: distribuicao por operacao do HEADER + partner (desde 2026-01-01)")
    print("=" * 90)
    entsi = rr('account.move', [('journal_id', '=', 1001), ('state', '=', 'posted'),
                                ('date', '>=', '2026-01-01')],
               ['id', 'l10n_br_operacao_id', 'partner_id', 'amount_total'], limit=2000)
    op_counter = Counter()
    partner_counter = Counter()
    total_zero = 0
    for m in entsi:
        op_counter[m2o(m.get('l10n_br_operacao_id'))] += 1
        partner_counter[m2o(m.get('partner_id'))] += 1
        if (m.get('amount_total') or 0) == 0:
            total_zero += 1
    print(f"  {len(entsi)} ENTSI posted desde 2026-01-01. amount_total==0: {total_zero}")
    print("  por operacao do header:")
    for op, n in op_counter.most_common():
        print(f"    {n:5}x  {op}")
    print("  por partner:")
    for p, n in partner_counter.most_common(10):
        print(f"    {n:5}x  {p}")

    # checar TODO o historico j1001 por partner (so contar, sem trazer tudo)
    n_total = o.search_count('account.move', [('journal_id', '=', 1001), ('state', '=', 'posted')])
    n_p35 = o.search_count('account.move', [('journal_id', '=', 1001), ('state', '=', 'posted'),
                                            ('partner_id', '=', 35)])
    print(f"\n  HISTORICO COMPLETO j1001: {n_total} posted; partner=35(LF): {n_p35}; outros: {n_total - n_p35}")
    # quem sao os 'outros' (nao LF)?
    if n_total - n_p35 > 0:
        outros = rr('account.move', [('journal_id', '=', 1001), ('state', '=', 'posted'),
                                     ('partner_id', '!=', 35)],
                    ['id', 'name', 'partner_id', 'date', 'amount_total'], limit=15, order='id desc')
        print(f"  amostra dos NAO-LF em j1001:")
        for m in outros:
            print(f"    {m['name']:22} partner={m2o(m.get('partner_id'))[:30]:30} date={m.get('date')} total={m.get('amount_total')}")

    # ====================================================================
    print("\n" + "=" * 90)
    print("(b) VALIDA C4: NF de ENTRADA real em journal purchase FB COM no_payment setado")
    print("=" * 90)
    # j1011 rem-industrializacao no_pay=22815 PASSIVA; j868 transf no_pay=22827; j993 bonif no_pay=22817
    for jid, jlbl, nopay_id in [(1011, 'REMESSA P/ IND (rem-industrializacao)', 22815),
                                (868, 'TRANSF ENTRE FILIAIS (transf-filial)', 22827),
                                (993, 'ENTRADA BONIFICACAO (ent-bonificacao)', 22817)]:
        mv = rr('account.move', [('journal_id', '=', jid), ('state', '=', 'posted'),
                                 ('move_type', '=', 'in_invoice')],
                ['id', 'name', 'amount_total', 'l10n_br_operacao_id'], limit=1, order='id desc')
        if not mv:
            print(f"\n  j{jid} ({jlbl}): nenhuma in_invoice posted")
            continue
        m = mv[0]
        print(f"\n  j{jid} ({jlbl}) no_payment={nopay_id} | move {m['id']} {m['name']} total={m.get('amount_total')}")
        lines = rr('account.move.line', [('move_id', '=', m['id'])],
                   ['id', 'account_id', 'l10n_br_operacao_id', 'l10n_br_cfop_id', 'debit', 'credit', 'display_type'],
                   limit=40)
        for ln in lines:
            if ln.get('display_type') in ('line_section', 'line_note'):
                continue
            acc = m2o(ln.get('account_id'))
            flag = '  <<< NO_PAYMENT' if acc.startswith(f"{nopay_id}|") else ''
            print(f"      acc={acc[:44]:44} op={m2o(ln.get('l10n_br_operacao_id'))[:22]:22} "
                  f"cfop={cf(ln.get('l10n_br_cfop_id')):6} D={ln.get('debit')} C={ln.get('credit')}{flag}")

    # ====================================================================
    print("\n" + "=" * 90)
    print("(c) op 3252: posicao fiscal/conta + se ja foi usada em alguma NF")
    print("=" * 90)
    op = rd('l10n_br_ciel_it_account.operacao', [3252], None)
    if op:
        x = op[0]
        # campos que possam apontar conta/fp
        rel = {k: v for k, v in x.items() if any(t in k.lower() for t in ('account', 'conta', 'fiscal', 'posicao', 'fp_', 'position'))}
        print("  campos da op 3252 relacionados a conta/fp:")
        for k, v in rel.items():
            print(f"    {k} = {m2o(v) if isinstance(v, list) else v}")
        print(f"    cfop_intra = {m2o(x.get('l10n_br_intra_cfop_id'))}")
        print(f"    movimento_estoque = {x.get('l10n_br_movimento_estoque')}  tipo_pedido_entrada={x.get('l10n_br_tipo_pedido_entrada')}")
    # ja foi usada?
    n_uso = o.search_count('account.move.line', [('l10n_br_operacao_id', '=', 3252)])
    print(f"\n  account.move.line com op 3252: {n_uso}")
    if n_uso:
        uso = rr('account.move.line', [('l10n_br_operacao_id', '=', 3252)],
                 ['id', 'move_id', 'account_id', 'l10n_br_cfop_id', 'debit', 'credit', 'parent_state'], limit=10)
        for ln in uso:
            print(f"    move={m2o(ln.get('move_id'))[:24]:24} acc={m2o(ln.get('account_id'))[:40]:40} "
                  f"cfop={cf(ln.get('l10n_br_cfop_id')):6} D={ln.get('debit')} C={ln.get('credit')} state={ln.get('parent_state')}")

    # posicao fiscal que mapeia o CFOP 1902 na FB (para inferir a conta da linha 1902)
    print("\n  posicoes fiscais FB que remapeiam conta (account.fiscal.position.account):")
    fps = rr('account.fiscal.position', [('company_id', '=', 1)], ['id', 'name'], limit=200)
    fp_ind = [f for f in fps if any(k in f['name'].upper() for k in ('INDUSTRIALIZ', 'RETORNO', 'REMESSA'))]
    for f in fp_ind[:12]:
        print(f"    fp {f['id']:<5} {f['name']}")

    print("\n[FIM GROUNDING 5 READ-ONLY — nada foi escrito]")


if __name__ == '__main__':
    main()
