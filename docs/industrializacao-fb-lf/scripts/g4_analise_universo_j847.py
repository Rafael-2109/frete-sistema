#!/usr/bin/env python3
"""G4 INVESTIGACAO (READ-ONLY) — universo do j847 VENDA PRODUCAO (LF sale).

Decide entre as 3 opcoes de G4 medindo:
  - quantas NFs em j847 sao RETORNO-INDUSTRIALIZACAO (tem linha 5902 insumos) vs
    VENDA PURA (so 5124 servico / sem 5902);
  - distribuicao por PARTNER (cliente) — so a FB encomendante, ou varios clientes?
    (decide se setar no_payment no j847 afeta vendas a terceiros)
  - quanto da PASSIVA (5101020001 LF) cada NF de retorno deveria baixar.
NAO escreve nada.
"""
import sys
from collections import Counter, defaultdict
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
OPS_5124 = [2702, 3039]            # servico (venda-industrializacao)
OPS_5902 = [2864, 2710]            # insumos consumidos (retorno)
OPS_5903 = [2711]                  # perda


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

    # 1) moves em j847 desde 2026-01-01
    moves = rr('account.move', [('journal_id', '=', 847), ('company_id', '=', 5),
                                ('state', '=', 'posted'), ('date', '>=', '2026-01-01'),
                                ('move_type', '=', 'out_invoice')],
               ['id', 'name', 'partner_id', 'amount_total'], limit=5000, order='id')
    print(f"\n  j847 out_invoice posted desde 2026-01-01: {len(moves)} NFs")
    move_ids = [m['id'] for m in moves]

    # 2) batch das linhas com operacao de retorno/servico
    all_ops = OPS_5124 + OPS_5902 + OPS_5903
    lines = []
    CHUNK = 200
    for i in range(0, len(move_ids), CHUNK):
        chunk = move_ids[i:i + CHUNK]
        lines += rr('account.move.line',
                    [('move_id', 'in', chunk), ('l10n_br_operacao_id', 'in', all_ops)],
                    ['move_id', 'l10n_br_operacao_id', 'l10n_br_cfop_id', 'credit', 'debit'], limit=20000)

    # 3) agrupar por move: quais familias de CFOP + valor 5902
    fam_by_move = defaultdict(set)
    val5902_by_move = defaultdict(float)
    for ln in lines:
        opid = ln['l10n_br_operacao_id'][0] if isinstance(ln.get('l10n_br_operacao_id'), list) else None
        if opid in OPS_5124:
            fam_by_move[ln['move_id'][0]].add('5124')
        elif opid in OPS_5902:
            fam_by_move[ln['move_id'][0]].add('5902')
            val5902_by_move[ln['move_id'][0]] += (ln.get('credit') or 0)
        elif opid in OPS_5903:
            fam_by_move[ln['move_id'][0]].add('5903')

    # 4) classificar cada NF
    cls_counter = Counter()
    partner_counter = Counter()
    partner_retorno = Counter()    # so NFs com 5902
    val5902_total = 0.0
    for m in moves:
        fams = fam_by_move.get(m['id'], set())
        partner = m2o(m.get('partner_id'))
        partner_counter[partner] += 1
        if '5902' in fams:
            cls = 'RETORNO (tem 5902)' + (' +5124' if '5124' in fams else '') + (' +5903' if '5903' in fams else '')
            partner_retorno[partner] += 1
            val5902_total += val5902_by_move.get(m['id'], 0)
        elif '5124' in fams:
            cls = 'SO SERVICO 5124 (sem 5902)'
        elif fams:
            cls = 'OUTRO: ' + '+'.join(sorted(fams))
        else:
            cls = 'SEM op de retorno/servico (venda comum?)'
        cls_counter[cls] += 1

    print("\n  === CLASSIFICACAO das NFs em j847 ===")
    for cls, n in cls_counter.most_common():
        print(f"    {n:5}x  {cls}")

    print("\n  === PARTNERS (clientes) das NFs em j847 ===")
    for p, n in partner_counter.most_common(15):
        ret = partner_retorno.get(p, 0)
        print(f"    {n:5}x (retorno:{ret:4})  {p}")

    print(f"\n  Valor total 5902 (insumos, credito) nas NFs de retorno desde 2026-01: R$ {val5902_total:,.2f}")
    print(f"  => esse e' o montante que HOJE NAO baixa a PASSIVA 5101020001 (fica em transitoria/recebivel)")

    # 5) quem e o partner FB visto pela LF? (para confirmar 'todos retorno sao p/ FB')
    print("\n  === resolvendo partners FB/encomendantes ===")
    fb_partners = rr('res.partner', ['|', ('vat', 'like', '61724241'), ('name', 'ilike', 'NACOM')],
                     ['id', 'name', 'vat'], limit=10)
    for p in fb_partners:
        print(f"    partner id={p['id']} vat={p.get('vat')} | {p['name']}")

    print("\n[FIM INVESTIGACAO G4 READ-ONLY — nada foi escrito]")


if __name__ == '__main__':
    main()
