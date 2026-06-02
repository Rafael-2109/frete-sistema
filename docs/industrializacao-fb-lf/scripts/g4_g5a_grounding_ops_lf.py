#!/usr/bin/env python3
"""G4 GROUNDING 2 (READ-ONLY) — operacoes de SAIDA company-LF + NF de retorno real.

Resolve 3 lacunas achadas no grounding 1:
  A) op 850 (5902) e' company FB, nao LF -> achar a operacao company-LF para
     5902/5903/5124 que a NF de retorno LF->FB usara, e seu l10n_br_tipo_pedido.
  B) nenhum tipo.pedido.diario aponta p/ j1003 PERDAS -> entender o fallback:
     ver uma NF de saida LF historica que caiu em j1003 (linhas + journal + tipo_pedido).
  D) operacao da linha 1124 entrada FB (3064/3134) + tipo_pedido_entrada (residuo NF mista).
NAO escreve nada.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
OP = 'l10n_br_ciel_it_account.operacao'


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

    opflds = ['id', 'name', 'l10n_br_tipo_operacao', 'l10n_br_movimento_estoque', 'l10n_br_gera_cpv',
              'l10n_br_tipo_pedido', 'l10n_br_tipo_pedido_entrada', 'l10n_br_intra_cfop_id', 'company_id']

    # ========================================================================
    print("\n" + "=" * 90)
    print("A — TODAS as operacoes SAIDA company-LF(5) c/ CFOP intra 5901/5902/5903/5124")
    print("=" * 90)
    allsai = rr(OP, [('l10n_br_tipo_operacao', '=', 'saida'), ('company_id', '=', 5)],
                opflds, limit=2000)
    alvo = [op for op in allsai if cf(op.get('l10n_br_intra_cfop_id')) in ('5901', '5902', '5903', '5124')]
    print(f"  {len(allsai)} ops saida LF no total; {len(alvo)} com CFOP alvo:")
    for op in sorted(alvo, key=lambda x: cf(x['l10n_br_intra_cfop_id'])):
        print(f"  op {op['id']:<5} cfop={cf(op['l10n_br_intra_cfop_id']):5} tipo_pedido={str(op.get('l10n_br_tipo_pedido')):24} "
              f"mov_estoque={str(op.get('l10n_br_movimento_estoque')):5} cpv={op.get('l10n_br_gera_cpv')} | {op['name'].strip()[:42]}")

    # tambem: existe alguma op company FALSE (compartilhada) p/ esses CFOPs?
    print("\n  -- ops 5902/5903/5124 com company VAZIA (compartilhada, qualquer empresa) --")
    allsh = rr(OP, [('l10n_br_tipo_operacao', '=', 'saida'), ('company_id', '=', False)], opflds, limit=2000)
    sh = [op for op in allsh if cf(op.get('l10n_br_intra_cfop_id')) in ('5902', '5903', '5124', '5901')]
    if not sh:
        print("     (nenhuma op de saida com company vazia nesses CFOPs)")
    for op in sh:
        print(f"     op {op['id']:<5} cfop={cf(op['l10n_br_intra_cfop_id']):5} tipo_pedido={op.get('l10n_br_tipo_pedido')} | {op['name'].strip()[:42]}")

    # ========================================================================
    print("\n" + "=" * 90)
    print("B — NF de SAIDA LF historica em j1003 PERDAS (mecanismo fallback) — ultimas 5")
    print("=" * 90)
    moves = rr('account.move', [('journal_id', '=', 1003), ('move_type', 'in', ['out_invoice', 'out_refund'])],
               ['id', 'name', 'state', 'move_type', 'date', 'company_id', 'journal_id', 'amount_total'],
               limit=5, order='id desc')
    print(f"  {len(moves)} NF em j1003 (out). amostra:")
    for mv in moves:
        print(f"\n  move {mv['id']} {mv['name']} state={mv['state']} type={mv['move_type']} date={mv.get('date')} total={mv.get('amount_total')}")
        lines = rr('account.move.line', [('move_id', '=', mv['id'])],
                   ['id', 'name', 'account_id', 'l10n_br_operacao_id', 'l10n_br_cfop_id', 'debit', 'credit', 'display_type'],
                   limit=40)
        for ln in lines:
            op = ln.get('l10n_br_operacao_id')
            cfop = ln.get('l10n_br_cfop_id')
            if ln.get('display_type') in ('line_section', 'line_note'):
                continue
            print(f"      L{ln['id']} acc={m2o(ln.get('account_id'))[:40]:40} op={m2o(op)[:28]:28} cfop={cf(cfop):6} D={ln.get('debit')} C={ln.get('credit')}")

    # ========================================================================
    print("\n" + "=" * 90)
    print("B2 — Como o tipo_pedido vira journal? campos de fallback no res.company (LF)")
    print("=" * 90)
    cf_fields = o.execute_kw('res.company', 'fields_get', [], {'attributes': ['string', 'type', 'relation'], 'context': CTX})
    interesse = {k: v for k, v in cf_fields.items()
                 if ('journal' in k.lower() or 'diario' in k.lower() or 'perda' in k.lower())
                 and v.get('type') == 'many2one'}
    comp5 = rd('res.company', [5], list(interesse.keys()) + ['id', 'name']) if interesse else []
    print(f"  campos many2one journal/diario/perda em res.company: {len(interesse)}")
    if comp5:
        for k in sorted(interesse.keys()):
            v = comp5[0].get(k)
            if v:
                print(f"    LF.{k} = {m2o(v)}  ({interesse[k].get('string')})")

    # ========================================================================
    print("\n" + "=" * 90)
    print("D — operacao da linha 1124 entrada FB (3064/3134) — residuo NF mista §5")
    print("=" * 90)
    for opid in (3064, 3134, 2807, 2027):
        try:
            op = rd(OP, [opid], opflds)
            if not op:
                print(f"  op {opid}: NAO ENCONTRADA")
                continue
            x = op[0]
            print(f"  op {x['id']:<5} cfop_intra={cf(x.get('l10n_br_intra_cfop_id')):6} tipo_oper={x.get('l10n_br_tipo_operacao')} "
                  f"mov_estoque={x.get('l10n_br_movimento_estoque')} tipo_ped_ent={x.get('l10n_br_tipo_pedido_entrada')} "
                  f"comp={m2o(x.get('company_id'))} | {x['name'].strip()[:38]}")
        except Exception as e:
            print(f"  op {opid}: ERRO {e}")

    # ========================================================================
    print("\n" + "=" * 90)
    print("E — entrada FB ground-truth ENTSI/2026/05/0126 (roteamento atual real)")
    print("=" * 90)
    gt = rr('account.move', [('name', 'like', 'ENTSI/2026/05/0126'), ('company_id', '=', 1)],
            ['id', 'name', 'state', 'journal_id', 'move_type', 'amount_total'], limit=3)
    for mv in gt:
        print(f"\n  move {mv['id']} {mv['name']} state={mv['state']} journal={m2o(mv['journal_id'])} total={mv.get('amount_total')}")
        lines = rr('account.move.line', [('move_id', '=', mv['id'])],
                   ['id', 'account_id', 'l10n_br_operacao_id', 'l10n_br_cfop_id', 'debit', 'credit', 'display_type'],
                   limit=60)
        for ln in lines:
            if ln.get('display_type') in ('line_section', 'line_note'):
                continue
            print(f"      L{ln['id']} acc={m2o(ln.get('account_id'))[:42]:42} op={m2o(ln.get('l10n_br_operacao_id'))[:26]:26} "
                  f"cfop={cf(ln.get('l10n_br_cfop_id')):6} D={ln.get('debit')} C={ln.get('credit')}")

    print("\n[FIM GROUNDING 2 READ-ONLY — nada foi escrito]")


if __name__ == '__main__':
    main()
