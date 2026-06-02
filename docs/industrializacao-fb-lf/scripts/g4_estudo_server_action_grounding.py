#!/usr/bin/env python3
"""ESTUDO server action G4 (READ-ONLY) — fatos do ambiente que decidem viabilidade/integridade.

Pontos decisivos:
  A) PODEMOS criar server action / base.automation via XML-RPC (uid 42)? ou depende do CIEL IT?
  B) LOCK DATES contabeis (company FB/LF) — impedem ajuste/estorno retroativo?
  C) restrict_mode_hash_table nos journals (j847/j1001/j1002 + o de retorno) — impede redraft/edicao?
  D) como a NF de retorno NASCE: create_uid (robo?), state inicial, invoice_origin, ha SO/picking de origem?
  E) precedentes: quantas ir.actions.server / base.automation existem? alguma toca account.move?
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


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    def can(model, op):
        try:
            return o.execute_kw(model, 'check_access_rights', [op], {'raise_exception': False, 'context': CTX})
        except Exception as e:
            return f"ERRO {e}"

    # ====================================================================
    print("\n" + "=" * 84)
    print("A) PODEMOS criar/escrever server action / automacao (uid 42)?")
    print("=" * 84)
    for model in ('ir.actions.server', 'base.automation', 'ir.cron', 'account.move'):
        print(f"  {model}: create={can(model,'create')} write={can(model,'write')} unlink={can(model,'unlink')}")

    # ====================================================================
    print("\n" + "=" * 84)
    print("B) LOCK DATES contabeis (res.company FB=1 / LF=5)")
    print("=" * 84)
    lockf = ['id', 'name', 'fiscalyear_lock_date', 'period_lock_date', 'tax_lock_date']
    # alguns campos podem nao existir em todas versoes; tentar
    try:
        comps = o.execute_kw('res.company', 'read', [[1, 5]], {'fields': lockf, 'context': CTX})
    except Exception as e:
        print(f"  (campos lock padrao falharam: {e}; tentando fields_get)")
        fg = o.execute_kw('res.company', 'fields_get', [], {'attributes': ['string'], 'context': CTX})
        lockf = ['id', 'name'] + [k for k in fg if 'lock_date' in k]
        comps = o.execute_kw('res.company', 'read', [[1, 5]], {'fields': lockf, 'context': CTX})
    for c in comps:
        print(f"  company {c['id']} {c.get('name')}:")
        for k in lockf:
            if k in ('id', 'name'):
                continue
            print(f"      {k} = {c.get(k)}")

    # ====================================================================
    print("\n" + "=" * 84)
    print("C) restrict_mode_hash_table (trava de redraft/edicao) nos journals-chave")
    print("=" * 84)
    jflds = ['id', 'name', 'type', 'restrict_mode_hash_table']
    try:
        js = o.execute_kw('account.journal', 'read', [[847, 1001, 1002, 1003, 17, 1047]],
                          {'fields': jflds, 'context': CTX})
        for j in js:
            print(f"  j{j['id']:<5} {j['name'][:38]:38} type={j['type']:9} hash_table={j.get('restrict_mode_hash_table')}")
    except Exception as e:
        print(f"  ERRO: {e}")

    # ====================================================================
    print("\n" + "=" * 84)
    print("D) Como a NF de retorno NASCE (VND/2026/00359 move 738097)")
    print("=" * 84)
    mvflds = ['id', 'name', 'state', 'create_uid', 'create_date', 'invoice_origin',
              'move_type', 'journal_id', 'l10n_br_operacao_id', 'amount_total']
    mv = o.execute_kw('account.move', 'read', [[738097]], {'fields': mvflds, 'context': CTX})
    for m in mv:
        for k in mvflds:
            print(f"  {k} = {m2o(m.get(k)) if isinstance(m.get(k), list) else m.get(k)}")
    # quem cria as VND recentes? (robo?)
    vnd = rr('account.move', [('journal_id', '=', 847), ('company_id', '=', 5),
                              ('state', '=', 'posted'), ('date', '>=', '2026-05-01')],
             ['id', 'create_uid'], limit=80)
    creators = Counter(m2o(m.get('create_uid')) for m in vnd)
    print(f"\n  create_uid das {len(vnd)} VND recentes (quem emite o retorno):")
    for cr, n in creators.most_common():
        print(f"    {n:4}x {cr}")

    # ====================================================================
    print("\n" + "=" * 84)
    print("E) Precedentes: ir.actions.server / base.automation existentes")
    print("=" * 84)
    n_sa = o.execute_kw('ir.actions.server', 'search_count', [[]], {'context': CTX})
    n_ba = o.execute_kw('base.automation', 'search_count', [[]], {'context': CTX})
    print(f"  ir.actions.server total: {n_sa}; base.automation total: {n_ba}")
    # automacoes tocando account.move?
    try:
        ams = rr('base.automation', [], ['id', 'name', 'model_id', 'trigger', 'active'], limit=50)
        tocando = [a for a in ams if 'account.move' in m2o(a.get('model_id')).lower() or 'move' in m2o(a.get('model_id')).lower()]
        print(f"  base.automation (amostra) tocando *move*: {len(tocando)}")
        for a in tocando[:10]:
            print(f"    id={a['id']} model={m2o(a.get('model_id'))} trigger={a.get('trigger')} active={a.get('active')} | {a.get('name')}")
        print(f"  base.automation por modelo (top):")
        bymodel = Counter(m2o(a.get('model_id')) for a in ams)
        for md, n in bymodel.most_common(12):
            print(f"    {n:3}x {md}")
    except Exception as e:
        print(f"  ERRO base.automation: {e}")
    # server actions tocando account.move
    try:
        sas = rr('ir.actions.server', [('model_id.model', '=', 'account.move')],
                 ['id', 'name', 'state', 'usage'], limit=30)
        print(f"\n  ir.actions.server em account.move: {len(sas)}")
        for s in sas[:15]:
            print(f"    id={s['id']} state={s.get('state')} usage={s.get('usage')} | {s.get('name')}")
    except Exception as e:
        print(f"  ERRO ir.actions.server: {e}")

    print("\n[FIM grounding estudo server action — READ-only]")


if __name__ == '__main__':
    main()
