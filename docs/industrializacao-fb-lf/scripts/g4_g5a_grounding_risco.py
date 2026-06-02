#!/usr/bin/env python3
"""G4/G5a GROUNDING 4 (READ-ONLY) — roteamento por-journal + RISCO GLOBAL.

Fecha o quadro p/ decisao do Rafael:
  A) Journals FB(1) purchase: quais l10n_br_tipo_pedido_entrada + no_payment
     -> j1001 e' o UNICO com serv-industrializacao? (roteamento univoco?)
  B) Journals LF(5) sale: mapa l10n_br_tipo_pedido -> journal + no_payment
     (venda-industrializacao=j847? perda? dev-industrializacao livre?)
  C) VOLUME j1001 (FB) ult. 60d -> magnitude do efeito GLOBAL de setar no_payment.
  D) VOLUME j847 (LF) ult. 60d -> risco de mexer no journal de venda producao.
NAO escreve nada.
"""
import sys
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

    jflds = ['id', 'name', 'code', 'type', 'company_id', 'l10n_br_tipo_pedido',
             'l10n_br_tipo_pedido_entrada', 'account_no_payment_id', 'l10n_br_no_payment']

    print("\n" + "=" * 90)
    print("A — Journals FB(1) PURCHASE com l10n_br_tipo_pedido_entrada setado")
    print("=" * 90)
    jfb = rr('account.journal', [('company_id', '=', 1), ('type', '=', 'purchase'),
                                 ('l10n_br_tipo_pedido_entrada', '!=', False)], jflds, limit=200)
    serv = [j for j in jfb if j.get('l10n_br_tipo_pedido_entrada') == 'serv-industrializacao']
    print(f"  {len(jfb)} journals FB purchase com tipo_pedido_entrada setado; "
          f"{len(serv)} com 'serv-industrializacao':")
    for j in sorted(jfb, key=lambda x: str(x.get('l10n_br_tipo_pedido_entrada'))):
        flag = '  <<< serv-ind' if j.get('l10n_br_tipo_pedido_entrada') == 'serv-industrializacao' else ''
        print(f"    j{j['id']:<5} tpe={str(j.get('l10n_br_tipo_pedido_entrada')):24} "
              f"no_pay={m2o(j.get('account_no_payment_id'))[:26]:26} | {j['name'][:34]}{flag}")

    print("\n" + "=" * 90)
    print("B — Journals LF(5) SALE: mapa l10n_br_tipo_pedido -> journal + no_payment")
    print("=" * 90)
    jlf = rr('account.journal', [('company_id', '=', 5), ('type', '=', 'sale')], jflds, limit=200)
    print(f"  {len(jlf)} journals LF sale:")
    for j in sorted(jlf, key=lambda x: str(x.get('l10n_br_tipo_pedido'))):
        print(f"    j{j['id']:<5} tp={str(j.get('l10n_br_tipo_pedido')):26} "
              f"no_pay={m2o(j.get('account_no_payment_id'))[:30]:30} | {j['name'][:30]}")
    for alvo in ('venda-industrializacao', 'dev-industrializacao', 'perda'):
        match = [j for j in jlf if j.get('l10n_br_tipo_pedido') == alvo]
        print(f"  -> tipo '{alvo}': {len(match)} journal(s) {[ 'j'+str(j['id']) for j in match]}")

    print("\n" + "=" * 90)
    print("C/D — VOLUME (account.move postados) — efeito global de mexer no journal")
    print("=" * 90)
    # janela: usar date range fixo (sem now() — regra timezone). ultimos meses 2026.
    for jid, lbl in [(1001, 'j1001 FB ENTSI (G5a: setar no_payment afeta TODAS)'),
                     (847, 'j847 LF VENDA PRODUCAO (G4 risco se mexer aqui)'),
                     (1003, 'j1003 LF PERDAS (G4: hoje recebe perda 5903)')]:
        n_total = o.search_count('account.move', [('journal_id', '=', jid), ('state', '=', 'posted')])
        n_2026 = o.search_count('account.move', [('journal_id', '=', jid), ('state', '=', 'posted'),
                                                 ('date', '>=', '2026-04-01')])
        print(f"  {lbl}")
        print(f"      postados TOTAL={n_total}  | desde 2026-04-01={n_2026}")

    print("\n" + "=" * 90)
    print("E — j1001: amostra das ENTSI recentes (que TIPO de entrada usa j1001 hoje?)")
    print("=" * 90)
    mv = rr('account.move', [('journal_id', '=', 1001), ('state', '=', 'posted'), ('date', '>=', '2026-05-01')],
            ['id', 'name', 'l10n_br_tipo_pedido_entrada', 'l10n_br_operacao_id', 'amount_total', 'partner_id'],
            limit=15, order='id desc')
    print(f"  {len(mv)} ENTSI desde 2026-05-01 (amostra):")
    for m in mv:
        print(f"    {m['name']:20} tpe={str(m.get('l10n_br_tipo_pedido_entrada')):22} "
              f"op_hdr={m2o(m.get('l10n_br_operacao_id'))[:30]:30} total={m.get('amount_total')} partner={m2o(m.get('partner_id'))[:22]}")

    print("\n[FIM GROUNDING 4 READ-ONLY — nada foi escrito]")


if __name__ == '__main__':
    main()
