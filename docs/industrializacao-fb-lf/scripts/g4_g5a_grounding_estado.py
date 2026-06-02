#!/usr/bin/env python3
"""G4/G5a GROUNDING (READ-ONLY) — estado ao vivo de TUDO que a config do retorno vai tocar.

NAO escreve nada. Confirma os IDs documentados (PROPOSTA/ACHADOS) contra o PROD
ANTES de compor a dry-run das escritas. Contexto allowed_company_ids=[1,5] (FB+LF).

Cobre:
  G5a (FB): journal j1001 (no_payment hoje VAZIO?), conta 22800, op 3252,
            tipo.pedido.diario(FB, serv-industrializacao) LIVRE?
  G4  (LF): conta 26667, journal espelho j1047, journal PERDAS j1003,
            tipo.pedido.diario(LF, dev-industrializacao/perda) inexistentes?,
            ops 850/2711/849/2702, journal j847.
Estrutura: fields_get de tipo.pedido.diario (nomes exatos p/ o create).
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}  # FB=1 + LF=5 (G-ENT-1/4/7/8)
TPD = 'l10n_br_ciel_it_account.tipo.pedido.diario'
OP = 'l10n_br_ciel_it_account.operacao'


def m2o(v):
    """many2one -> 'id|name' ou '-'."""
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v is False or v is None else str(v)


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID autenticado: {o._uid}  (esperado 42=Rafael, company principal FB)")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [ids], {'fields': fields, 'context': CTX})

    # ========================================================================
    print("\n" + "=" * 90)
    print("1 — CONTAS (account.account) — confirmar IDs 22800(FB ATIVA) / 26667(LF PASSIVA)")
    print("=" * 90)
    for code, comp, rotulo in [
        ('5101010001', 1, 'FB ATIVA (esperado id 22800)'),
        ('5101010001', 5, 'LF ATIVA (esperado id 26652)'),
        ('5101020001', 1, 'FB PASSIVA (esperado id 22815)'),
        ('5101020001', 5, 'LF PASSIVA (esperado id 26667)'),
        ('5101010002', 1, 'FB RETORNO ATIVA (R$0)'),
        ('5101020002', 1, 'FB RETORNO PASSIVA (R$0)'),
    ]:
        a = rr('account.account', [('code', '=', code), ('company_id', '=', comp)],
               ['id', 'code', 'name', 'account_type', 'company_id'])
        for x in a:
            print(f"  {rotulo:34} code={x['code']} id={x['id']} type={x['account_type']} comp={m2o(x['company_id'])} | {x['name']}")
        if not a:
            print(f"  {rotulo:34} code={code} comp={comp}  >>> NAO ENCONTRADO <<<")

    # ========================================================================
    print("\n" + "=" * 90)
    print("2 — JOURNALS-CHAVE por ID (j1001/j1047/j1003/j847/j17/j1007)")
    print("=" * 90)
    jids = [1001, 1047, 1003, 847, 17, 1007]
    jflds = ['id', 'name', 'code', 'type', 'company_id', 'default_account_id', 'account_no_payment_id']
    try:
        js = rd('account.journal', jids, jflds)
        by = {j['id']: j for j in js}
    except Exception as e:
        print(f"  ERRO read journals por id: {e}")
        by = {}
    rotulos = {
        1001: 'G5a alvo: ENTRADA-SERVICO-IND FB (no_payment deve estar VAZIO hoje)',
        1047: 'G4 espelho: ENTRADA-REMESSA LF (no_payment esperado 26667 PASSIVA)',
        1003: 'G4 sair daqui: PERDAS LF (no_payment esperado 5101010001 ATIVA=26652)',
        847:  '5124 ja OK: VENDA PRODUCAO LF',
        17:   'ref remessa FB SAIDA (no_payment esperado 22800 ATIVA)',
        1007: 'FB ENTRADA-RETORNO (no_payment esperado 5101020002 PASSIVA RETORNO)',
    }
    for jid in jids:
        j = by.get(jid)
        if not j:
            print(f"  j{jid}: >>> NAO ENCONTRADO <<<  ({rotulos.get(jid,'')})")
            continue
        print(f"  j{j['id']:<5} type={j['type']:9} comp={m2o(j['company_id']):20} code={j.get('code')}")
        print(f"        default_account={m2o(j['default_account_id'])}")
        print(f"        no_payment    ={m2o(j['account_no_payment_id'])}")
        print(f"        nome={j['name']}  | {rotulos.get(jid,'')}")

    # ========================================================================
    print("\n" + "=" * 90)
    print(f"3 — ESTRUTURA do modelo {TPD} (nomes exatos de campo p/ o create)")
    print("=" * 90)
    try:
        fg = o.execute_kw(TPD, 'fields_get', [],
                          {'attributes': ['string', 'type', 'relation', 'selection', 'required'], 'context': CTX})
        for fname, meta in sorted(fg.items()):
            extra = ''
            if meta.get('relation'):
                extra = f" -> {meta['relation']}"
            if meta.get('selection'):
                extra = f" sel={meta['selection']}"
            req = '*' if meta.get('required') else ' '
            print(f"  {req} {fname:42} {meta.get('type'):10}{extra}")
    except Exception as e:
        print(f"  ERRO fields_get {TPD}: {e}")
        fg = {}

    # ========================================================================
    print("\n" + "=" * 90)
    print(f"4 — REGISTROS {TPD} — FB (company 1) e LF (company 5)")
    print("=" * 90)
    # traz todos os campos relevantes (filtra em python). Campos esperados:
    cand_fields = [f for f in (
        'id', 'name', 'company_id',
        'l10n_br_tipo_pedido', 'l10n_br_tipo_pedido_entrada',
        'journal_id', 'diario_id', 'account_journal_id',
        'l10n_br_diario_id', 'l10n_br_journal_id',
    ) if f in fg] or ['id', 'name', 'company_id']
    print(f"  campos lidos: {cand_fields}")
    for comp, lbl in [(1, 'FB'), (5, 'LF')]:
        regs = rr(TPD, [('company_id', '=', comp)], cand_fields, limit=500, order='id')
        print(f"\n  --- {lbl} (company {comp}): {len(regs)} registros ---")
        for r in regs:
            parts = [f"id={r['id']}"]
            for f in cand_fields:
                if f in ('id',):
                    continue
                v = r.get(f)
                parts.append(f"{f.replace('l10n_br_','')}={m2o(v) if isinstance(v,list) else v}")
            print("   " + "  ".join(parts))

    # ========================================================================
    print("\n" + "=" * 90)
    print("5 — OPERACOES de retorno (3252/850/2711/849/2702) — campos fiscais")
    print("=" * 90)
    opflds = ['id', 'name', 'l10n_br_tipo_operacao', 'l10n_br_movimento_estoque', 'l10n_br_gera_cpv',
              'l10n_br_tipo_pedido', 'l10n_br_tipo_pedido_entrada', 'l10n_br_intra_cfop_id', 'company_id']
    for opid, lbl in [(3252, '1902 simbolica FB (movimento_estoque deve ser False)'),
                      (850, '5902 dev-industrializacao LF'),
                      (2711, '5903 perda LF'),
                      (849, '5124 venda-industrializacao LF'),
                      (2702, '5124 venda-industrializacao LF (alt)')]:
        try:
            op = rd(OP, [opid], opflds)
            if not op:
                print(f"  op {opid}: >>> NAO ENCONTRADA <<< ({lbl})")
                continue
            x = op[0]
            print(f"  op {x['id']:<5} {lbl}")
            print(f"        tipo_oper={x.get('l10n_br_tipo_operacao')} mov_estoque={x.get('l10n_br_movimento_estoque')} "
                  f"cpv={x.get('l10n_br_gera_cpv')} cfop_intra={m2o(x.get('l10n_br_intra_cfop_id'))}")
            print(f"        tipo_pedido={x.get('l10n_br_tipo_pedido')} tipo_pedido_entrada={x.get('l10n_br_tipo_pedido_entrada')} "
                  f"comp={m2o(x.get('company_id'))}")
        except Exception as e:
            print(f"  op {opid}: ERRO {e}")

    # ========================================================================
    print("\n" + "=" * 90)
    print("6 — check_access_rights('create') em account.journal e tipo.pedido.diario (uid 42)")
    print("=" * 90)
    for model in ('account.journal', TPD):
        try:
            can = o.execute_kw(model, 'check_access_rights', ['create'],
                               {'raise_exception': False, 'context': CTX})
            print(f"  {model}: create={can}")
        except Exception as e:
            print(f"  {model}: ERRO check_access_rights {e}")

    print("\n[FIM GROUNDING READ-ONLY — nada foi escrito]")


if __name__ == '__main__':
    main()
