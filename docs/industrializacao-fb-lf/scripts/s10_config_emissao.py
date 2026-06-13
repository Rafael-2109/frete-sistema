#!/usr/bin/env python3
"""S10 — CONFIG da emissao 2-NF (pre-requisito do GATE 1). Cadastro Odoo, REVERSIVEL.

Cria/ajusta a base que o split (SOT §6.1) precisa, SEM tocar SEFAZ:
  1. JOURNAL RETIND (LF sale) — destino das linhas 5902 da NF-insumos:
       type=sale, company=5, l10n_br_no_payment=True, account_no_payment_id=26667
       (5101020001 PASSIVA), l10n_br_tipo_pedido=VAZIO (nos setamos o journal
       explicitamente no split; tipo_pedido vazio impede o robo de roteá-lo).
       Combinacao PROVADA no GATE 0 (s8d): baixa a PASSIVA no action_post.
  2. pt98 "Retorno Industrializacao (LF)" (31093→26489, 0 usos) — espelha do
       pt66 o que importa p/ o faturamento, mantendo src/dest de TERCEIROS:
       invoice_move_type='out_invoice' (wizard aceita o picking) +
       l10n_br_tipo_pedido='venda-industrializacao' (expansao da BoM via j847).

Anti-robo: pt98 tem 0 pickings hoje (setar e' seguro). No GATE 1 o picking do
piloto fica liberado_faturamento=False + picking.robo fora de 1..11.

MODOS:
  (sem flag)   dry-run: mostra o estado atual + o que sera criado/alterado
  --confirmar  cria o journal RETIND (idempotente) + configura o pt98
  --revert     deleta o RETIND (se sem linhas) + restaura pt98 (False/False)
  --validar    le de volta e confere os campos (anti-falso-sucesso)
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5}
LF = 5
NO_PAY_PASSIVA = 26667          # 5101020001 REMESSA INDUSTRIALIZACAO (PASSIVA) LF
PT98 = 98                       # Retorno Industrializacao (LF) 31093->26489
RETIND_CODE = 'RETIN'
RETIND_NAME = 'RETORNO INDUSTRIALIZACAO INSUMOS'
RETIND_VALS = {
    'name': RETIND_NAME, 'code': RETIND_CODE, 'type': 'sale', 'company_id': LF,
    'l10n_br_no_payment': True, 'account_no_payment_id': NO_PAY_PASSIVA,
    'l10n_br_tipo_pedido': False,
}
PT98_TARGET = {'invoice_move_type': 'out_invoice', 'l10n_br_tipo_pedido': 'venda-industrializacao'}
PT98_REVERT = {'invoice_move_type': False, 'l10n_br_tipo_pedido': False}


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true')
    ap.add_argument('--revert', action='store_true')
    ap.add_argument('--validar', action='store_true')
    args = ap.parse_args()

    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, domain, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kw2)
    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})
    def w(model, ids, vals):
        return o.execute_kw(model, 'write', [list(ids), vals], {'context': CTX})

    def find_retind():
        r = rr('account.journal', [('company_id', '=', LF), ('code', '=', RETIND_CODE)],
               ['id', 'name', 'type', 'l10n_br_no_payment', 'account_no_payment_id', 'l10n_br_tipo_pedido'])
        return r[0] if r else None

    pt98 = rd('stock.picking.type', [PT98],
              ['name', 'invoice_move_type', 'l10n_br_tipo_pedido', 'default_location_src_id',
               'default_location_dest_id'])[0]

    # ---------- VALIDAR ----------
    if args.validar:
        print("=== VALIDACAO ===")
        j = find_retind()
        ok_j = bool(j and j.get('l10n_br_no_payment') is True
                    and isinstance(j.get('account_no_payment_id'), list)
                    and j['account_no_payment_id'][0] == NO_PAY_PASSIVA
                    and not j.get('l10n_br_tipo_pedido'))
        print(f"  journal RETIND: {'OK' if ok_j else 'FALTA/DIVERGE'} -> {j}")
        ok_p = (pt98.get('invoice_move_type') == 'out_invoice'
                and pt98.get('l10n_br_tipo_pedido') == 'venda-industrializacao')
        print(f"  pt98 config:    {'OK' if ok_p else 'FALTA/DIVERGE'} -> "
              f"invoice_move_type={pt98.get('invoice_move_type')} tipo_pedido={pt98.get('l10n_br_tipo_pedido')}")
        print(f"\n  >>> CONFIG {'COMPLETA' if (ok_j and ok_p) else 'INCOMPLETA'}")
        return

    # ---------- REVERT ----------
    if args.revert:
        print("=== REVERT ===")
        j = find_retind()
        if j:
            nml = o.execute_kw('account.move.line', 'search_count',
                               [[('journal_id', '=', j['id'])]], {'context': dict(CTX, active_test=False)})
            if nml == 0:
                o.execute_kw('account.journal', 'unlink', [[j['id']]], {'context': CTX})
                print(f"  journal RETIND {j['id']} DELETADO (0 linhas)")
            else:
                w('account.journal', [j['id']], {'active': False})
                print(f"  journal RETIND {j['id']} ARQUIVADO ({nml} linhas)")
        else:
            print("  journal RETIND: nao existe")
        w('stock.picking.type', [PT98], PT98_REVERT)
        print(f"  pt98 revertido -> {PT98_REVERT}")
        return

    # ---------- DRY-RUN (preview) ----------
    j = find_retind()
    print("=" * 84)
    print("S10 CONFIG EMISSAO 2-NF — preview (cadastro, REVERSIVEL, sem SEFAZ)")
    print("=" * 84)
    print(f"\n[1] JOURNAL RETIND (code={RETIND_CODE}, LF sale)")
    if j:
        print(f"    JA EXISTE: id={j['id']} no_payment={j.get('l10n_br_no_payment')} "
              f"conta={m2o(j.get('account_no_payment_id'))} tipo_pedido={j.get('l10n_br_tipo_pedido')}")
    else:
        print(f"    CRIAR com: {RETIND_VALS}")
        print(f"    (conta {NO_PAY_PASSIVA} = 5101020001 PASSIVA; combinacao PROVADA no GATE 0)")
    print(f"\n[2] pt98 '{pt98['name']}' ({m2o(pt98.get('default_location_src_id'))} -> "
          f"{m2o(pt98.get('default_location_dest_id'))})")
    print(f"    ATUAL:  invoice_move_type={pt98.get('invoice_move_type')} "
          f"tipo_pedido={pt98.get('l10n_br_tipo_pedido')}")
    print(f"    ALVO:   {PT98_TARGET}")
    print(f"    (0 pickings pt98 hoje -> setar e' seguro; expoe ao robo so quando houver picking "
          f"liberado+robo 1..11)")

    if not args.confirmar:
        print("\n  [DRY-RUN] nada escrito. Com 'go': --confirmar  (reverte com --revert)")
        return

    # ---------- EXECUTAR ----------
    print("\n  [EXEC]")
    if j:
        print(f"    journal RETIND ja existe (id={j['id']}) — pulando create (idempotente)")
        jid = j['id']
    else:
        jid = o.execute_kw('account.journal', 'create', [RETIND_VALS], {'context': CTX})
        print(f"    journal RETIND CRIADO: id={jid}")
    w('stock.picking.type', [PT98], PT98_TARGET)
    print(f"    pt98 configurado -> {PT98_TARGET}")
    print(f"\n  >>> valide com: --validar")


if __name__ == '__main__':
    main()
